"""SymbolPipeline + Orchestrator: the engine spine, shared by live and replay.

One SymbolPipeline per symbol owns every per-symbol stateful component
(registry, levels + LevelEngine, classifier, confluence, gates, EntryFSM,
DayState -- reset on a new session date -- and the evidence history, pruned
to the last 200). The Orchestrator routes FeedEvents to pipelines, processes
the index pipeline FIRST within each timestamp batch so stocks see a fresh
IndexView, shares ONE RiskState across all symbols, and returns a summary.

Timing: an M5 close is detected when an M1 crosses the bucket boundary; the
closed-M5 flow (LevelEngine -> detectors -> template -> confluence -> gates/
FSM -> manager) decides. Exits execute at the OPEN of that boundary-crossing
M1 -- the next M1 open, no lookahead. A triggered ENTRY rests as a LIMIT at
the plan entry (traded-zone CE): it fills when a later M1 trades through it
(AT the limit, half-spread only -- no chase), and expires unfilled after
entry.fill_ttl_candles M5 (journal skip "unfilled").
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from itertools import groupby
from pathlib import Path

import trader.detectors
from trader.config import Settings
from trader.detectors.base import DetectorRegistry
from trader.detectors.timestats import bucket_index
from trader.detectors.wyckoff import WyckoffDetector
from trader.engine.confluence import ConfluenceEngine
from trader.engine.context import DayState, IndexView, StockContext
from trader.engine.entry import EntryFSM, EntryState
from trader.engine.gates import GateChain, RiskState
from trader.engine.levels import LevelEngine, LevelStore
from trader.engine.template import TemplateClassifier
from trader.execution.manager import Action, PositionManager
from trader.execution.paper import PaperBroker
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction
from trader.models.level import TERMINAL, LevelKind, LevelState
from trader.models.market import _minutes, is_expiry
from trader.models.position import ExitReason, Position, PositionStatus
from trader.store.candles import CandleStore, _bucket_start
from trader.store.journal import Journal

for _m in pkgutil.iter_modules(trader.detectors.__path__):    # @register all
    importlib.import_module(f"trader.detectors.{_m.name}")

_M5 = timedelta(minutes=5)
_VERDICT_MIN = 3.0
_CARRY = frozenset({LevelKind.PDH, LevelKind.PDL, LevelKind.PWH, LevelKind.PWL,
                    LevelKind.EQH, LevelKind.EQL, LevelKind.ROUND})  # cross-day
_DATED = (LevelKind.PDH, LevelKind.PDL, LevelKind.PWH, LevelKind.PWL)
_ZONES = frozenset({LevelKind.OB_BULL, LevelKind.OB_BEAR,
                    LevelKind.FVG_BULL, LevelKind.FVG_BEAR})  # SMC continuum


def _sessions_old(born, ref) -> int:
    """Weekday sessions strictly after ``born`` up to ``ref`` (holiday-blind:
    an NSE holiday counts as a session, so a stale zone prunes a touch early
    -- conservative, and stateless across restarts)."""
    if ref is None or ref <= born:
        return 0
    return sum((born + timedelta(days=i)).weekday() < 5
               for i in range(1, (ref - born).days + 1))


class SymbolPipeline:
    """All per-symbol state + the closed-M5 flow (see module docstring)."""

    def __init__(self, symbol: str, settings: Settings, store: CandleStore,
                 journal: Journal, broker: PaperBroker, manager: PositionManager,
                 risk: RiskState, max_qty: int, is_index: bool = False,
                 level_store: LevelStore | None = None,
                 timestats_dir: Path | None = None):
        self.symbol, self.s, self.spec = symbol, settings, settings.market_spec()
        self.store, self.journal, self.broker = store, journal, broker
        self.manager, self.risk, self.max_qty = manager, risk, max_qty
        self.is_index, self.index_view = is_index, None
        self.registry = DetectorRegistry(settings)
        lvp = settings.detectors.params.get("levels", {})
        self.level_engine = LevelEngine(lvp)
        self._zone_max_age = int(lvp.get("max_age_sessions", 5))
        self.classifier = TemplateClassifier(self.spec)
        self.confluence = ConfluenceEngine(
            settings, settings.detectors.params.get("confluence"))
        self.gates, self.fsm = GateChain(settings), EntryFSM(settings, self.spec)
        self.wyckoff = WyckoffDetector(settings.detectors.params.get("wyckoff", {}))
        self.level_store = level_store        # optional: cross-run level persistence
        self.levels = level_store.load(symbol) if level_store else []
        self.timestats = self.registry.get("timestats")  # learning hook
        if self.timestats is not None and timestats_dir is not None:
            self.timestats.params["path"] = str(timestats_dir)
            self.timestats.load(symbol)
        self.evidence_history = []
        self.day: DayState | None = None
        self.position: Position | None = None
        self.closed: list[Position] = []
        self.n_trades = self.n_skips = 0
        self._last_bucket = self._last_c5 = self._pending_plan = None
        self._pending_since = None
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
        Prune levels to live cross-day liquidity kinds + unmitigated OB/FVG
        zones (SMC continuum): terminal states, aged-out zones and intraday
        micro-structure (swings, OR) must not block or bias the new day
        (liquidity re-creates fresh PDH/PDL/OR per session). Carried zones
        arrive on day 2 with clean engine memory (on_session_end below) and
        cleared detector _quality maps -- their evidence strength falls back
        to 0.5 until a rescan re-derives it; acceptable.
        Persist the pruned set (if a level_store is wired) so it survives
        into the next run. Detector instance memories (ts/level-keyed dedupe
        sets) are pruned via the registry hook -- C10 memory bound. An open
        position is force-closed same-day (no overnight gap risk) and the
        LevelEngine's per-run windows reset (no cross-gap trap resolution)."""
        self.registry.end_session()
        self.wyckoff.on_session_end()   # pipeline's own instance, not in registry
        self.level_engine.on_session_end()   # reset reclaim/break/invert windows
        self._force_close_eod(ts)            # no position/exit survives the gap
        self._prune_levels()
        self._save_levels()
        self._save_timestats()
        if self._pending_plan is not None:
            self._pending_plan = None
            self._skip(ts, "fill", "session_end")
        if self.fsm.state is not EntryState.IDLE:
            self.fsm._disarm("session_end")
            self._skip(ts, "fsm_disarm", "session_end")

    def _force_close_eod(self, ts, why: str = "session_end") -> None:
        """Session boundary with an open position: the next real M1 is next
        day's candle, so a queued stop/EOD exit would fill against the
        overnight gap (a price never reachable same-day) -- overnight risk and
        misstated P&L. Force-close same-day AT the last observed price and drop
        any queued exits so none can price off a different-date candle."""
        self._pending_exits = []
        if self.position is None:
            return
        last = self.store.view(self.symbol, ts).last(1, Timeframe.M1)
        if not last:
            return
        c = last[-1]                    # last same-day M1: close is last price
        self._pending_exits = [Action(ExitReason.EOD.value, None, why)]
        self._run_exits(replace(c, open=c.close))

    def _carry_over(self) -> list:
        """Cross-day-safe subset: live liquidity kinds, non-terminal. Dated
        pair kinds (PDH/PDL, PWH/PWL) carry only their NEWEST generation:
        older ones are stale pools that widen stops, fake sweep evidence and
        grow one pair per session (measured 22 of 26 carried levels after a
        22-session replay before this prune). OB/FVG zones (continuum:
        yesterday's unmitigated zone is a live trade location today) carry
        with state/touches/history intact until terminal -- LevelEngine kills
        them on close-beyond-far-edge / 2nd test, the fvg detectors on full
        fill -- or older than max_age_sessions weekday sessions (stale-zone
        hygiene + bounded memory; day count is None-safe pre-first-session)."""
        ref = self.day.session_date if self.day else None
        live = [lv for lv in self.levels if lv.state not in TERMINAL
                and (lv.kind in _CARRY or
                     (lv.kind in _ZONES and
                      _sessions_old(lv.born.date(), ref) < self._zone_max_age))]
        top = {k: max((lv.born for lv in live if lv.kind is k), default=None)
               for k in _DATED}
        return [lv for lv in live
                if lv.kind not in _DATED or lv.born == top[lv.kind]]

    def _prune_levels(self) -> None:
        self.levels[:] = self._carry_over()

    def _save_levels(self) -> None:
        if self.level_store is not None:
            self.level_store.save(self.symbol, self.levels)

    def _save_timestats(self) -> None:
        if self.timestats is not None:
            self.timestats.save(self.symbol)   # no-op without a path

    def finalize(self) -> None:
        """Called once when the feed is exhausted (Orchestrator.run end):
        persist the cross-day-safe subset so it survives into the next run,
        WITHOUT mutating in-memory levels -- unlike _end_session, no new
        session actually started, so intraday state stays live for callers
        that inspect the pipeline right after run(). A truncated feed can
        strand an open position (no EOD candle ever arrived): force-close it
        at the last known same-day price -- journaled "feed_end", risk ledger
        released -- and flush queued exits, so nothing dangles unreported."""
        if self._last_bucket is not None:
            self._force_close_eod(self._last_bucket + _M5, why="feed_end")
        if self.level_store is not None:
            self.level_store.save(self.symbol, self._carry_over())
        self._save_timestats()

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
            trans = self.level_engine.update(self.levels, c5, ctx.atr(Timeframe.M5))
            if self.timestats is not None:       # learn: sweep outcome per bar
                self.timestats.record(
                    self.symbol,
                    bucket_index(now, self.spec, self.timestats.params["bucket_min"]),
                    swept=any(t.new is LevelState.SWEPT for t in trans))
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
                      distinct=z.distinct, template=self.day.template,
                      members=z.members)    # (detector, event, strength): calibration food
        if self.position is not None:
            self._manage(ctx, zones)
        elif self._pending_plan is None:     # resting limit blocks re-arming
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
        elif step.action == "fill":              # resting LIMIT at plan entry
            self._pending_plan, self._pending_since = step.plan, ctx.now

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
            plan = self._pending_plan
            up = plan.direction is Direction.LONG
            limit = self.spec.quantize(sum(plan.entry_zone) / 2)  # plan entry CE
            if candle.ts.hour * 60 + candle.ts.minute >= self._cutoff:
                self._pending_plan = None
                self._skip(candle.ts, "fill", "too_late")  # past no_entry_after
            elif (self._pending_since is not None
                  and candle.ts - self._pending_since
                  >= self.s.entry.fill_ttl_candles * _M5):
                self._pending_plan = None
                self._skip(candle.ts, "fill", "unfilled")  # limit never traded
            elif candle.low <= limit if up else candle.high >= limit:
                self._pending_plan = None
                fill = self.broker.entry_fill(plan, candle, limit)
                self.position = Position(plan, fill, plan.qty, plan.stop,
                                         realized=-fill.costs)
                self._hunt_logged = False
                self.risk.record_open(self.symbol,
                                      self.position.risk_pts * plan.qty,
                                      plan.direction)
                self.n_trades += 1
                self._log("trade_open", at=fill.ts, direction=plan.direction,
                          qty=plan.qty, price=fill.price, stop=plan.stop,
                          zone=list(plan.entry_zone), targets=plan.targets,
                          costs=fill.costs, plan=plan.meta)
        self._run_exits(candle)

    def _run_exits(self, candle: Candle) -> None:
        """Execute queued exits against ``candle``. Guard: never price an exit
        off a candle whose date differs from the position's session -- an
        overnight-gap M1 would fill a same-day stop/EOD at next day's open
        (_end_session force-closes same-day before that candle is reached)."""
        pos = self.position
        if pos is not None and candle.ts.date() != pos.entry.ts.date():
            return
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
                # effective R: denominator = FILL->stop risk (pos.risk_pts),
                # never the plan-CE risk -- limit fills make them converge
                r = float(pos.realized / (pos.risk_pts * pos.plan.qty))
                self.risk.record_close(r, self.symbol, fill.ts)
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
        """Size throttles, composed multiplicatively: expiry-day (B7) x
        day-after-TREND (B5, axiom 16) x RANGE_PIN half-size (fade edges
        half-size: score stays full, discipline lives here)."""
        m = 1.0
        if is_expiry(self.day.session_date, self.spec):
            m *= self.s.risk.expiry_size_mult
        if self.day.prev_template == "TREND":
            m *= self.s.risk.day_after_trend_mult
        if self.day.template == "RANGE_PIN":
            m *= self.s.risk.range_pin_size_mult
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
    """Routes the feed to per-symbol pipelines; index first per ts batch.

    ``store``/``level_dir``/``timestats_dir`` wire cross-run persistence for
    candles/levels/time-bucket sweep stats. Positions and RiskState stay
    memory-only (see RiskState docstring)."""

    def __init__(self, settings: Settings, feed, symbols: list[str],
                 index_symbol: str | None = None, *, capital: float | None = None,
                 max_qty: int, journal_dir: Path, store: CandleStore | None = None,
                 level_dir: Path | None = None, timestats_dir: Path | None = None):
        if capital is not None:
            settings = settings.model_copy(update={"capital": float(capital)},
                                           deep=True)
        self.feed, self.index_symbol = feed, index_symbol
        self.journal = Journal(Path(journal_dir))
        self.risk = RiskState(settings)          # ONE ledger, all symbols
        spec = settings.market_spec()
        self.store = store if store is not None else CandleStore(
            Path(journal_dir) / "candles", spec)
        level_store = LevelStore(level_dir) if level_dir is not None else None
        broker, manager = PaperBroker(settings), PositionManager(settings, spec)
        mk = lambda sym, idx=False: SymbolPipeline(       # noqa: E731
            sym, settings, self.store, self.journal, broker, manager, self.risk,
            max_qty, idx, level_store=level_store, timestats_dir=timestats_dir)
        self.pipelines = {sym: mk(sym) for sym in symbols}
        self.index_pipe = mk(index_symbol, True) if index_symbol else None
        self._all = ([self.index_pipe] if self.index_pipe else []) \
            + list(self.pipelines.values())               # index first
        self._session = None

    def run(self) -> dict:
        self.feed.subscribe(list(self.pipelines)
                            + ([self.index_symbol] if self.index_pipe else []))
        for _ts, batch in groupby(self.feed.events(), key=lambda e: e.candle.ts):
            for ev in sorted(batch,                       # index first
                             key=lambda e: e.candle.symbol != self.index_symbol):
                c = ev.candle
                if self._session != c.ts.date():
                    if self._session is not None:  # settle the outgoing session
                        for p in self._all:        # FIRST: a previous-day open
                            p._force_close_eod(c.ts)  # position must release
                    self._session = c.ts.date()       # into the OLD day's ledger
                    self.risk.reset_day()             # -- reset on a clean slate
                if self.index_pipe and c.symbol == self.index_symbol:
                    self.index_pipe.on_m1(c)
                elif c.symbol in self.pipelines:
                    self.pipelines[c.symbol].on_m1(
                        c, self.index_pipe.index_view if self.index_pipe else None)
        for p in self._all:
            p.finalize()                      # flush levels: state survives across runs
        pipes = self.pipelines.values()
        closed = [p for pipe in pipes for p in pipe.closed]
        return {"trades": sum(p.n_trades for p in pipes),
                "wins": sum(1 for p in closed if p.realized > 0),
                "losses": sum(1 for p in closed if p.realized < 0),
                "pnl": sum((p.realized for p in closed), Decimal(0)),
                "skips": sum(p.n_skips for p in pipes),
                # 0 after finalize by construction; nonzero = loud anomaly
                "open_positions": sum(p.position is not None for p in pipes)}
