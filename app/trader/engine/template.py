"""Day-template classifier (00-DESIGN-SPEC "Day Templates" table).

Fed once per closed M5 candle via ``update(ctx)``; returns the current
template and mirrors it onto ``ctx.day.template``. Until session_open +
``lock_min`` (default 135 => 11:30 NSE) the answer is provisional and
re-derived every tick; the first update at/after that instant evaluates one
last time and LOCKS -- later ticks return the locked value unchanged, no
matter what the evidence does. A new ``ctx.day.session_date`` resets the
lock (one classifier instance can serve consecutive sessions).

Rule table, evaluated top-down against the session's OPEN_RANGE_H/L levels
(this symbol only) and ``ctx.evidence_history``. An edge counts as *swept*
if its state_history ever recorded SWEPT or RECLAIMED (a reclaim implies
the sweep even if the SWEPT row predates level persistence):

    DOUBLE_TRAP    both OR edges swept
    TRAP_REVERSAL  exactly one edge swept AND that edge reached RECLAIMED
                   AND any structure CHoCH evidence exists
    TREND          no OR edge ever RECLAIMED AND >=2 structure BOS evidence
                   in the same direction (a swept-but-unreclaimed edge is
                   fine: trend days may blow through an edge)
    RANGE_PIN      no edge swept AND fewer than 2 BOS total
    UNCLASSIFIED   anything else

Gap fade-bias (axiom 18): a session opening with |gap| > 1xATR vs the prev
session close records ``ctx.day.gap_dir``; BOS activity in the gap
direction below the TREND bar (>=2 same-direction BOS) is a suspected gap
trap and classifies UNCLASSIFIED instead of RANGE_PIN.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from trader.engine.context import StockContext, live_evidence
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState
from trader.models.market import MarketSpec

_DEFAULTS = {"lock_min": 135}
_SWEPT_STATES = (LevelState.SWEPT, LevelState.RECLAIMED)


def _swept(level: Level | None) -> bool:
    return level is not None and any(
        st in _SWEPT_STATES for _, st in level.state_history)


def _reclaimed(level: Level | None) -> bool:
    return level is not None and any(
        st is LevelState.RECLAIMED for _, st in level.state_history)


def _structure(history: list[Evidence], event: str) -> list[Evidence]:
    return [e for e in history
            if e.detector == "structure" and e.meta.get("event") == event]


class TemplateClassifier:
    """One instance per symbol; call ``update`` at every M5 close."""

    def __init__(self, spec: MarketSpec, params: dict | None = None):
        p = {**_DEFAULTS, **(params or {})}
        self.spec = spec
        self.lock_min = int(p["lock_min"])
        self._locked: str | None = None
        self._session: date | None = None
        self._gap_done = False

    def update(self, ctx: StockContext) -> str:
        if ctx.day.session_date != self._session:      # new day: fresh lock
            self._session = ctx.day.session_date
            self._locked, self._gap_done = None, False
        if not self._gap_done:
            self._detect_gap(ctx)
        if self._locked is not None:
            template = self._locked
        else:
            template = self._classify(ctx)
            lock_at = (self.spec.session_open_dt(ctx.now)
                       + timedelta(minutes=self.lock_min))
            if ctx.now >= lock_at:
                self._locked = template
        ctx.day.template = template
        return template

    # ------------------------------------------------------------- internals

    def _detect_gap(self, ctx: StockContext) -> None:
        """Once per session, at the first data-complete tick: record the gap
        direction when |open - prev close| > 1xATR (axiom 18)."""
        if ctx.candles is None:
            return
        today = ctx.candles.today(Timeframe.M5)
        prev = ctx.candles.prev_day(Timeframe.M5)
        atr = ctx.atr(Timeframe.M5)
        if not (today and prev and atr):
            return
        self._gap_done = True
        gap = today[0].open - prev[-1].close
        if abs(gap) > atr:
            ctx.day.gap_dir = Direction.LONG if gap > 0 else Direction.SHORT

    def _classify(self, ctx: StockContext) -> str:
        edges = {lv.kind: lv for lv in ctx.levels
                 if lv.symbol == ctx.symbol
                 and lv.kind in (LevelKind.OPEN_RANGE_H, LevelKind.OPEN_RANGE_L)}
        orh = edges.get(LevelKind.OPEN_RANGE_H)
        orl = edges.get(LevelKind.OPEN_RANGE_L)
        swept_high, swept_low = _swept(orh), _swept(orl)

        history = live_evidence(ctx.evidence_history,      # this session only
                                session_date=ctx.day.session_date)
        bos = _structure(history, "BOS")
        dirs = Counter(e.direction for e in bos)
        bos_same = max(dirs.values(), default=0)

        if swept_high and swept_low:
            return "DOUBLE_TRAP"
        if swept_high != swept_low:
            edge = orh if swept_high else orl
            if _reclaimed(edge) and _structure(history, "CHOCH"):
                return "TRAP_REVERSAL"
        if not _reclaimed(orh) and not _reclaimed(orl) and bos_same >= 2:
            return "TREND"
        gd = ctx.day.gap_dir
        if gd is not None and dirs.get(gd, 0):     # gap-direction drive short
            return "UNCLASSIFIED"                  # of TREND proof: gap trap
        if not swept_high and not swept_low and len(bos) < 2:
            return "RANGE_PIN"
        return "UNCLASSIFIED"
