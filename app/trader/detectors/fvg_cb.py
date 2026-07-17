"""fvg_cb detector ("fvg_cb"): the validated LuxAlgo dedicated close-beyond
FVG, ported faithfully from the measured winner (scratchpad fvg2.py,
``gaps(...,"luxded")`` + ``cehold`` + ``retest``). A 3-candle gap (bull:
c3.low > c1.high; bear: c3.high < c1.low) only becomes a level when (a) the
middle candle c2 CLOSES beyond the origin edge (displacement) and (b) the
gap size as a % of the origin edge exceeds an auto threshold: the running
mean bar-range% over EVERY closed tf candle seen so far (recomputed fresh
each tick from ``ctx.candles.last``, so it naturally spans sessions exactly
like fvg2.py's un-reset ``cum/(i+1)``; ``thr_mult`` scales it, default 1.0
reproduces the source exactly). Creates an FVG_BULL/FVG_BEAR Level, zone =
the gap (bull: (c1.high, c3.low); bear: (c3.high, c1.low)), born = c2.ts;
id is namespaced with the detector name so it coexists with ``fvg``'s own
FVG_BULL/FVG_BEAR levels without colliding.

Two ONE-SHOT events per level, eligible strictly after c3 (matching fvg2.py's
``range(born+1, ...)``; no re-firing on re-entry, unlike ``fvg``'s episode
model):
- FVG_RETEST (0.6): first candle whose range overlaps the zone -- UNLESS a
  candle first breaks the zone's far edge intrabar (wick), which silences it
  with no event.
- FVG_CE_HOLD (0.75, primary): first candle that CLOSES inside the zone on
  the gap side of the CE (midpoint) -- UNLESS a candle first CLOSES beyond
  the zone, which silences it with no event.
Each is an independent race (retest breaks on wick, CE-hold breaks on
close); both may fire, once each, over a level's life. Strength constants
are this port's choice -- fvg2.py is a boolean event study with no scoring
of its own."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind

_DEFAULTS = {"tf": "5m", "thr_mult": 1.0}
_FVG_KINDS = (LevelKind.FVG_BULL, LevelKind.FVG_BEAR)
_ALL = 1_000_000  # sentinel: fetch every closed candle (cross-session cum)


@register
class FvgCbDetector(Detector):
    name = "fvg_cb"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._retest_done: set[str] = set()
        self._ce_done: set[str] = set()

    def on_session_end(self) -> None:
        self._retest_done.clear()
        self._ce_done.clear()

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        atr = ctx.atr(tf)
        full = ctx.candles.last(_ALL, tf)
        if atr is None or atr <= 0 or len(full) < 3:
            return []
        self._create(ctx, tf, full)
        return self._events(ctx, tf, full[-1])

    def _create(self, ctx: StockContext, tf: Timeframe, full: list[Candle]) -> None:
        c1, c2, c3 = full[-3], full[-2], full[-1]
        thr = float(self.params["thr_mult"]) * self._cum(full) / len(full)
        for kind, zone, disp in (
            (LevelKind.FVG_BULL, (c1.high, c3.low), c2.close > c1.high),
            (LevelKind.FVG_BEAR, (c3.high, c1.low), c2.close < c1.low),
        ):
            lo, hi = zone
            if hi <= lo or not disp or float((hi - lo) / lo) <= thr:
                continue
            level_id = f"{ctx.symbol}-{kind.name}-{tf.value}-{self.name}-{c2.ts.isoformat()}"
            if any(lv.id == level_id for lv in ctx.levels):
                continue
            ctx.levels.append(Level(id=level_id, symbol=ctx.symbol, kind=kind,
                                    zone=zone, born=c2.ts, tf=tf))

    @staticmethod
    def _cum(full: list[Candle]) -> float:
        return sum((float(c.high - c.low) / float(c.low)) if c.low else 0.0
                   for c in full[2:])

    def _events(self, ctx: StockContext, tf: Timeframe, last: Candle) -> list[Evidence]:
        out = []
        for lv in ctx.levels:
            if lv.kind not in _FVG_KINDS or f"-{self.name}-" not in lv.id:
                continue
            if last.ts <= lv.born + timedelta(minutes=tf.minutes):  # born+1: c3 itself excluded
                continue
            bull = lv.kind is LevelKind.FVG_BULL
            lo, hi = lv.zone
            out += self._retest(lv, last, lo, hi, bull, ctx.now)
            out += self._cehold(lv, last, lo, hi, bull, ctx.now)
        return out

    def _retest(self, lv: Level, last: Candle, lo: Decimal, hi: Decimal,
                bull: bool, now) -> list[Evidence]:
        if lv.id in self._retest_done:
            return []
        broke = last.low < lo if bull else last.high > hi
        touch = last.low <= hi and last.high >= lo
        if not (broke or touch):
            return []
        self._retest_done.add(lv.id)
        if broke:
            return []
        return [Evidence(detector=self.name,
                         direction=Direction.LONG if bull else Direction.SHORT,
                         strength=0.6, zone=lv.zone, ts=now, ttl_candles=6,
                         meta={"level_id": lv.id, "event": "FVG_RETEST"})]

    def _cehold(self, lv: Level, last: Candle, lo: Decimal, hi: Decimal,
               bull: bool, now) -> list[Evidence]:
        if lv.id in self._ce_done:
            return []
        mid = (lo + hi) / 2
        broke = last.close < lo if bull else last.close > hi
        hold = lo <= last.close <= hi and (
            last.close >= mid if bull else last.close <= mid)
        if not (broke or hold):
            return []
        self._ce_done.add(lv.id)
        if not hold:
            return []
        return [Evidence(detector=self.name,
                         direction=Direction.LONG if bull else Direction.SHORT,
                         strength=0.75, zone=lv.zone, ts=now, ttl_candles=6,
                         meta={"level_id": lv.id, "event": "FVG_CE_HOLD"})]
