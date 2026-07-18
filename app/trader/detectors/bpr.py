"""BPR detector ("bpr"): validated balanced-price-range overlap (ict_pieces.py
``bpr``/``find_gaps``, measured best ICT piece, +0.31R@3R). A live bull FVG
overlapping a live bear FVG forms a Balanced Price Range; the first close
back INSIDE the overlap fires in the direction of the NEWER (later-born)
gap, sl = overlap lo (LONG) / hi (SHORT). A gap dies when a close breaks its
far edge (bull: close < zone lo; bear: close > zone hi) -- only pairs still
live at the touch bar qualify.

Pure signal-emitter: gaps are internal instance memory (no persistent
Level), rediscovered incrementally each tick from the latest closed 3-candle
window -- same creation rule as trader/detectors/fvg.py (3-candle gap >=
gap_atr * ATR), just not upserted into ctx.levels.

CONTINUUM: the 3-candle window is ``ctx.candles.last(3)`` -- continuous
multi-day history, never session-scoped -- and live gaps carry across
sessions. That is how the edge was VALIDATED (ict_pieces.py ran one
concatenated series): a day-1 FVG can pair with a day-2 FVG.

Emission hygiene (``_collapse``): two different bull/bear gap pairs can
straddle the SAME touch close in one tick (their overlap zones overlap each
other, or share an sl) -- one physical price event should fire once, so
same-direction clashes within a single ``detect()`` call collapse to the
single strongest Evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "gap_atr": 0.3, "sl_atr_floor": 0.15}


@dataclass
class _Gap:
    born: datetime
    lo: Decimal
    hi: Decimal
    bull: bool
    dead: bool = False


def _collapse(evs: list[Evidence], tick: Decimal) -> list[Evidence]:
    """Per-tick emission hygiene: two DIFFERENT bull/bear pairs can straddle
    the SAME physical touch close (their overlap zones overlap each other,
    or their sl sits within one tick) -- collapse same-direction clashes to
    the single strongest (max strength; tie -> tightest zone)."""
    kept: list[Evidence] = []
    for e in evs:
        j = next((k for k, o in enumerate(kept) if o.direction is e.direction and
                  (o.zone[0] <= e.zone[1] and e.zone[0] <= o.zone[1] or
                   abs(Decimal(o.meta["sl"]) - Decimal(e.meta["sl"])) <= tick)), None)
        if j is None:
            kept.append(e)
        elif (e.strength, e.zone[0] - e.zone[1]) > (kept[j].strength, kept[j].zone[0] - kept[j].zone[1]):
            kept[j] = e
    return kept


@register
class BprDetector(Detector):
    name = "bpr"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._gaps: list[_Gap] = []
        self._fired: set[tuple[datetime, datetime]] = set()  # (bull.born, bear.born)

    def on_session_end(self) -> None:
        # Continuum: live gaps are structure and carry across days. Prune
        # only dead gaps and fired pairs referencing a pruned gap -- neither
        # can ever signal again (bounded memory, no behavior change).
        self._gaps = [g for g in self._gaps if not g.dead]
        born = {g.born for g in self._gaps}
        self._fired = {k for k in self._fired if k[0] in born and k[1] in born}

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        window = ctx.candles.last(3, tf)
        if not window:
            return []
        atr = ctx.atr(tf)
        if len(window) == 3 and atr:
            self._find_gap(window, atr)
        floor = Decimal(str(self.params["sl_atr_floor"])) * atr if atr else Decimal(0)
        last = window[-1]
        for g in self._gaps:
            if not g.dead and (last.close < g.lo if g.bull else last.close > g.hi):
                g.dead = True
        return _collapse(self._overlaps(ctx, last, floor), ctx.spec.tick_size)

    def _find_gap(self, window: list[Candle], atr: Decimal) -> None:
        c1, c2, c3 = window
        need = Decimal(str(self.params["gap_atr"])) * atr
        if (c3.low > c1.high and c3.low - c1.high >= need
                and not self._has(c2.ts, True)):
            self._gaps.append(_Gap(c2.ts, c1.high, c3.low, True))
        if (c3.high < c1.low and c1.low - c3.high >= need
                and not self._has(c2.ts, False)):
            self._gaps.append(_Gap(c2.ts, c3.high, c1.low, False))

    def _has(self, born: datetime, bull: bool) -> bool:
        return any(g.born == born and g.bull == bull for g in self._gaps)

    def _overlaps(self, ctx: StockContext, last: Candle,
                  floor: Decimal) -> list[Evidence]:
        bulls = [g for g in self._gaps if g.bull and not g.dead]
        bears = [g for g in self._gaps if not g.bull and not g.dead]
        out = []
        for b in bulls:
            for r in bears:
                key = (b.born, r.born)
                lo, hi = max(b.lo, r.lo), min(b.hi, r.hi)
                if key in self._fired or lo > hi or not lo <= last.close <= hi:
                    continue
                self._fired.add(key)
                long_ = b.born > r.born  # newer gap decides direction
                sl = lo if long_ else hi
                out.append(Evidence(
                    detector=self.name,
                    direction=Direction.LONG if long_ else Direction.SHORT,
                    strength=0.8, zone=(lo, hi), ts=ctx.now, ttl_candles=4,
                    meta={"event": "BPR", "sl": str(sl), "sl_floor": str(floor)}))
        return out
