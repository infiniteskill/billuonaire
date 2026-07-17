"""SymbolPipeline + Orchestrator: the engine spine, shared by live and replay.

One SymbolPipeline per symbol owns every per-symbol stateful component
(registry, levels + LevelEngine, classifier, confluence, gates, EntryFSM,
DayState -- reset on a new session date -- and the evidence history, pruned
to the last 200). The Orchestrator routes FeedEvents to pipelines, processes
the index pipeline FIRST within each timestamp batch so stocks see a fresh
IndexView, shares ONE RiskState across all symbols, and returns a summary.

Timing: an M5 close is detected when an M1 crosses the bucket boundary; the
closed-M5 flow (LevelEngine -> detectors -> template -> confluence -> gates/
FSM -> manager) decides, and any resulting entry/exit fills execute at the
OPEN of that boundary-crossing M1 -- the next M1 open, no lookahead.
"""

from __future__ import annotations

import importlib
import pkgutil
from datetime import timedelta
from decimal import Decimal
from itertools import groupby
from pathlib import Path

import trader.detectors
from trader.config import Settings
from trader.detectors.base import DetectorRegistry
from trader.detectors.wyckoff import WyckoffDetector
from trader.engine.confluence import ConfluenceEngine
from trader.engine.context import DayState, IndexView, StockContext
from trader.engine.entry import EntryFSM, EntryState
from trader.engine.gates import GateChain, RiskState
from trader.engine.levels import LevelEngine
from trader.engine.template import TemplateClassifier
from trader.execution.manager import PositionManager
from trader.execution.paper import PaperBroker
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction
from trader.models.level import TERMINAL, LevelKind
from trader.models.market import _minutes, is_expiry
from trader.models.position import Position, PositionStatus
from trader.store.candles import CandleStore, _bucket_start
from trader.store.journal import Journal

for _m in pkgutil.iter_modules(trader.detectors.__path__):    # @register all
    importlib.import_module(f"trader.detectors.{_m.name}")

_M5 = timedelta(minutes=5)
_VERDICT_MIN = 3.0
_CARRY = frozenset({LevelKind.PDH, LevelKind.PDL, LevelKind.EQH,
                    LevelKind.EQL, LevelKind.ROUND})  # cross-day liquidity


class SymbolPipeline:
    """All per-symbol state + the closed-M5 flow (see module docstring)."""

    def __init__(self, symbol: str, settings: Settings, store: CandleStore,
                 journal: Journal, broker: PaperBroker, manager: PositionManager,
                 risk: RiskState, max_qty: int, is_index: bool = False):
        self.symbol, self.s, self.spec = symbol, settings, settings.market_spec()
        self.store, self.journal, self.broker = store, journal, broker
        self.manager, self.risk, self.max_qty = manager, risk, max_qty
        self.is_index, self.index_view = is_index, None
        self.registry = DetectorRegistry(settings)
        self.level_engine = LevelEngine(settings.detectors.params.get("levels", {}))
        self.classifier = TemplateClassifier(self.spec)
        self.confluence = ConfluenceEngine(settings)
        self.gates, self.fsm = GateChain(settings), EntryFSM(settings, self.spec)
        self.wyckoff = WyckoffDetector(settings.detectors.params.get("wyckoff", {}))
        self.levels, self.evidence_history = [], []
        self.day: DayState | None = None
        self.position: Position | None = None
        self.closed: list[Position] = []
        self.n_trades = self.n_skips = 0
        self._last_bucket = self._last_c5 = self._pending_plan = None
        self._pending_exits, self._hunt_logged = [], False
        self._cutoff = _minutes(settings.time.no_entry_after)

    def on_m1(self, candle: Candle, index: IndexView | None = None) -> None:
        bucket = _bucket_start(candle.ts, Timeframe.M5, self.spec)
        if self._last_bucket is not None and bucket != self._last_bucket:
            # gap-safe: close EVERY missed boundary in order, clamped to the
            # old bucket's session close (overnight jumps end there)
            t = self._last_bucket + _M5
            stop = min(bucket, self.spec.session_open_dt(self._last_bucket)
                       + timedelta(minutes=self.spec.session_minutes))
            while t <= stop:
                self._on_m5_close(t, index)
                t += _M5
        if self.day is not None and candle.ts.date() != self.day.session_date:
            self._end_session(candle.ts)    # no stale intent across the gap
        self._fill_pending(candle)          # fills at this M1's open
        self.store.add(candle)
        self._last_bucket = bucket

    def _end_session(self, ts) -> None:
        """New session: a pending plan or armed FSM carries day-old stops
        and targets across the overnight gap -- drop both, journal skips.
        Prune levels to live cross-day liquidity kinds: terminal states and
        intraday micro-structure (swings, OB/FVG, OR) must not block or bias
        the new day (liquidity re-creates fresh PDH/PDL/OR per session)."""
        self.levels[:] = [lv for lv in self.levels
                          if lv.kind in _CARRY and lv.state not in TERMINAL]
        if self._pending_plan is not None:
            self._pending_plan = None
            self._skip(ts, "fill", "session_end")
        if self.fsm.state is not EntryState.IDLE:
            self.fsm._disarm("session_end")
            self._skip(ts, "fsm_disarm", "session_end")

    # -------------------------------------------------------- closed-M5 flow

    def _on_m5_close(self, now, index: IndexView | None) -> None:
        view = self.store.view(self.symbol, now)
        if not (last := view.last(1, Timeframe.M5)):
            return
        c5 = last[-1]
        if self.day is None or c5.ts.date() != self.day.session_date:
            self.day = DayState(session_date=c5.ts.date(),  # fresh po3 dict too
                                prev_template=self.day.template if self.day else None)
        ctx = StockContext(self.symbol, now, view, self.levels,
                           self.evidence_history, self.day,
                           index=index, spec=self.spec)
        if c5.ts != self._last_c5:               # bar-scoped stages once per bar
            self._last_c5 = c5.ts                # (gap buckets only tick time)
            self.level_engine.update(self.levels, c5, ctx.atr(Timeframe.M5))
            evidence = self.registry.run_all(ctx)
            self.evidence_history.extend(evidence)   # after run_all: 1-tick lag ok
            del self.evidence_history[:-200]
            self.classifier.update(ctx)
        else:
            evidence = []
        if self.is_index:
            self.wyckoff.detect(ctx)  # prime spring/upthrust memory so phase() can reach ACC/DIST
            self.index_view = IndexView(self._m15_trend(),
                                        *self.wyckoff.phase(ctx))
            return
        htf = self.wyckoff.htf_phase(ctx)
        zones = self.confluence.score(ctx, self.evidence_history, htf,
                                      self._m15_trend())
        # verdicts are OBSERVATIONS: journal any zone scoring >= 3, raw or
        # final (final is forced 0 below min_zone_detectors; near-misses and
        # armed zones alike must land in the journal, so the bar sits far
        # below the arm threshold)
        if zones and any(max(z.final, z.raw) >= _VERDICT_MIN for z in zones):
            z = zones[0]
            self._log("verdict", at=ctx.now, zone=list(z.zone), mults=z.mults,
                      direction=z.direction, final=z.final, raw=z.raw,
                      distinct=z.distinct, template=self.day.template)
        if self.position is not None:
            self._manage(ctx, zones)
        else:
            self._entry_flow(ctx, zones, htf, evidence)

    def _entry_flow(self, ctx, zones, htf, evidence) -> None:
        top = zones[0] if zones else None
        if (self.fsm.state is EntryState.IDLE and top is not None
                and top.final >= self.s.confluence.threshold):
            verdict = self.gates.check(ctx, top.direction, top.zone, htf[0],
                                       self.risk)
            if not verdict.allow:
                self._skip(ctx.now, verdict.gate, verdict.reason)
            else:
                opps = [z for z in zones
                        if z.direction.value == -top.direction.value]
                res = self.fsm.arm(top, ctx, self._eff_qty(), opps)
                if not res.armed:
                    self._skip(ctx.now, "fsm_arm", res.reason)
        step = self.fsm.step(ctx, evidence)      # this-candle evidence
        if step.action == "disarm":
            self._skip(ctx.now, "fsm_disarm", step.reason)
        elif step.action == "fill":
            self._pending_plan = step.plan       # fills at next M1 open

    def _manage(self, ctx, zones) -> None:
        pos = self.position
        counter = max((z.final for z in zones
                       if z.direction.value == -pos.plan.direction.value),
                      default=None)              # best opposing zone this candle
        self._pending_exits += self.manager.on_candle(pos, ctx, counter)
        if pos.hunt_survived and not self._hunt_logged:
            self._hunt_logged = True
            self._log("hunt_survived", at=ctx.now, stop=pos.stop)

    # ----------------------------------------------------- broker execution

    def _fill_pending(self, candle: Candle) -> None:
        if self._pending_plan is not None:
            plan, self._pending_plan = self._pending_plan, None
            if candle.ts.hour * 60 + candle.ts.minute >= self._cutoff:
                self._skip(candle.ts, "fill", "too_late")  # past no_entry_after
            else:
                fill = self.broker.entry_fill(plan, candle)
                self.position = Position(plan, fill, plan.qty, plan.stop,
                                         realized=-fill.costs)
                self._hunt_logged = False
                self.risk.record_open(self.symbol)
                self.n_trades += 1
                self._log("trade_open", at=fill.ts, direction=plan.direction,
                          qty=plan.qty, price=fill.price, stop=plan.stop,
                          targets=plan.targets, costs=fill.costs, plan=plan.meta)
        pos = self.position
        for a in self._pending_exits:
            if pos is None:
                break
            qty = min(a.qty or pos.remaining_qty, pos.remaining_qty)
            if qty <= 0:
                continue
            fill = self.broker.exit_fill(pos, candle, qty, a.price)
            pos.realized += ((fill.price - pos.entry.price)
                             * pos.plan.direction.value * qty - fill.costs)
            pos.remaining_qty -= qty
            if a.kind != "PARTIAL":              # full exit: close remainder
                pos.status = PositionStatus.CLOSED
                r = float(pos.realized / (pos.risk_pts * pos.plan.qty))
                self.risk.record_close(r)
                self.closed.append(pos)
                self._log("trade_close", at=fill.ts, reason=a.kind, why=a.reason,
                          pnl=pos.realized, r=round(r, 3), exit_price=fill.price,
                          costs=fill.costs)
                self.position = pos = None
            else:
                self._log("trade_partial", at=fill.ts, reason=a.reason, qty=qty,
                          price=fill.price, costs=fill.costs)
        self._pending_exits.clear()

    # --------------------------------------------------------------- helpers

    def _m15_trend(self) -> Direction:
        """Real M15 structure: HH+HL / LH+LL over the last 4 confirmed M15
        swing levels (swings detector writes them; pruned at session end)."""
        swings = sorted((lv for lv in self.levels if lv.tf is Timeframe.M15
                         and lv.kind in (LevelKind.SWING_H, LevelKind.SWING_L)),
                        key=lambda lv: lv.born)[-4:]
        hs = [lv.zone[0] for lv in swings if lv.kind is LevelKind.SWING_H]
        ls = [lv.zone[0] for lv in swings if lv.kind is LevelKind.SWING_L]
        if len(hs) >= 2 and len(ls) >= 2:
            if hs[-1] > hs[-2] and ls[-1] > ls[-2]:
                return Direction.LONG
            if hs[-1] < hs[-2] and ls[-1] < ls[-2]:
                return Direction.SHORT
        return Direction.NEUTRAL

    def _eff_qty(self) -> int:
        """Size throttles: expiry-day (B7) x day-after-TREND (B5, axiom 16)."""
        m = 1.0
        if is_expiry(self.day.session_date, self.spec):
            m *= self.s.risk.expiry_size_mult
        if self.day.prev_template == "TREND":
            m *= self.s.risk.day_after_trend_mult
        return int(self.max_qty * m)

    def _skip(self, at, gate: str, reason: str) -> None:
        self.n_skips += 1
        self._log("skip", at=at, gate=gate, reason=reason)

    def _log(self, kind: str, **payload) -> None:
        if kind in ("skip", "verdict") and is_expiry(self.day.session_date, self.spec):
            payload["expiry"] = True
        self.journal.log(kind, {"symbol": self.symbol, **payload},
                         day=self.day.session_date, ts=payload.get("at"))


class Orchestrator:
    """Routes the feed to per-symbol pipelines; index first per ts batch."""

    def __init__(self, settings: Settings, feed, symbols: list[str],
                 index_symbol: str | None = None, *, capital: float | None = None,
                 max_qty: int, journal_dir: Path):
        if capital is not None:
            settings = settings.model_copy(update={"capital": float(capital)},
                                           deep=True)
        self.feed, self.index_symbol = feed, index_symbol
        self.journal = Journal(Path(journal_dir))
        self.risk = RiskState(settings)          # ONE ledger, all symbols
        spec = settings.market_spec()
        store = CandleStore(Path(journal_dir) / "candles", spec)
        broker, manager = PaperBroker(settings), PositionManager(settings, spec)
        mk = lambda sym, idx=False: SymbolPipeline(       # noqa: E731
            sym, settings, store, self.journal, broker, manager, self.risk,
            max_qty, idx)
        self.pipelines = {sym: mk(sym) for sym in symbols}
        self.index_pipe = mk(index_symbol, True) if index_symbol else None
        self._session = None

    def run(self) -> dict:
        self.feed.subscribe(list(self.pipelines)
                            + ([self.index_symbol] if self.index_pipe else []))
        for _ts, batch in groupby(self.feed.events(), key=lambda e: e.candle.ts):
            for ev in sorted(batch,                       # index first
                             key=lambda e: e.candle.symbol != self.index_symbol):
                c = ev.candle
                if self._session != c.ts.date():
                    self._session = c.ts.date()
                    self.risk.reset_day()
                if self.index_pipe and c.symbol == self.index_symbol:
                    self.index_pipe.on_m1(c)
                elif c.symbol in self.pipelines:
                    self.pipelines[c.symbol].on_m1(
                        c, self.index_pipe.index_view if self.index_pipe else None)
        pipes = self.pipelines.values()
        closed = [p for pipe in pipes for p in pipe.closed]
        return {"trades": sum(p.n_trades for p in pipes),
                "wins": sum(1 for p in closed if p.realized > 0),
                "losses": sum(1 for p in closed if p.realized < 0),
                "pnl": sum((p.realized for p in closed), Decimal(0)),
                "skips": sum(p.n_skips for p in pipes)}
