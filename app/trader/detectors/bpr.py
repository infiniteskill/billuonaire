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
gap_atr * ATR), just not upserted into ctx.levels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "gap_atr": 0.3}


@dataclass
class _Gap:
    born: datetime
    lo: Decimal
    hi: Decimal
    bull: bool
    dead: bool = False


@register
class BprDetector(Detector):
    name = "bpr"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._gaps: list[_Gap] = []
        self._fired: set[tuple[datetime, datetime]] = set()  # (bull.born, bear.born)

    def on_session_end(self) -> None:
        self._gaps.clear()
        self._fired.clear()

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        window = ctx.candles.today(tf)[-3:]
        if not window:
            return []
        atr = ctx.atr(tf)
        if len(window) == 3 and atr:
            self._find_gap(window, atr)
        last = window[-1]
        for g in self._gaps:
            if not g.dead and (last.close < g.lo if g.bull else last.close > g.hi):
                g.dead = True
        return self._overlaps(ctx, last)

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

    def _overlaps(self, ctx: StockContext, last: Candle) -> list[Evidence]:
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
                    meta={"event": "BPR", "sl": sl}))
        return out
