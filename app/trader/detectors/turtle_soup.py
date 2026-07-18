"""Turtle-soup detector ("turtle_soup"): faithful port of liq_hunt.py's
turtle_soup(m5, atrs, mins, N=20) -- a new N-bar low that closes back above
the prior N-bar low (failed breakdown) is FADED long, sl = the swept low;
mirror for a new N-bar high closing back below the prior N-bar high (failed
breakout) -> fade short, sl = the swept high. Measured +8.6% hit-edge,
sign-stable across holdouts, but RR ~breakeven standalone -- CONFLUENCE-ONLY
contributor (the confluence engine sets its low weight); built here as a
pure signal-emitter, no Levels.

Window: the last N+1 closed candles (N prior bars + the qualifying bar),
taken from CONTINUOUS multi-day history (``ctx.candles.last``) -- never
session-scoped: liq_hunt.py::turtle_soup was VALIDATED on one concatenated
multi-day series, so the N-bar window legitimately spans the overnight gap.
Rule uses only the prior window's *first* bar (L[i-N]/H[i-N]) as the reclaim
reference, not the min/max of the whole prior window -- matches the source.
Strength: how much of the qualifying bar's range reclaimed past that
reference (bounded in (0, 1) by construction, since the reference always
sits strictly between the swept extreme and the close)."""

from __future__ import annotations

from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence

_DEFAULTS = {"tf": "5m", "N": 20, "sl_atr_floor": 0.15}


@register
class TurtleSoupDetector(Detector):
    name = "turtle_soup"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})
        self._emitted: set = set()  # qualifying candle ts already fired

    def on_session_end(self) -> None:
        # Continuum: dedupe survives the boundary (day 1's last bar is still
        # the qualifying bar until day 2's first close). Prune by age -- only
        # the newest fired ts can ever be window[-1] again.
        if self._emitted:
            self._emitted = {max(self._emitted)}

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        N = int(self.params["N"])
        window = ctx.candles.last(N + 2, tf)
        if len(window) < N + 1:
            return []
        c = window[-1]
        if c.ts in self._emitted:
            return []
        prior = window[-1 - N:-1]
        ref_lo, ref_hi = prior[0].low, prior[0].high
        if c.low < min(x.low for x in prior) and c.close > ref_lo:
            sl, direction = c.low, Direction.LONG
            strength = min(1.0, float((c.close - ref_lo) / c.range))
        elif c.high > max(x.high for x in prior) and c.close < ref_hi:
            sl, direction = c.high, Direction.SHORT
            strength = min(1.0, float((ref_hi - c.close) / c.range))
        else:
            return []
        self._emitted.add(c.ts)
        T = ctx.spec.tick_size
        atr = ctx.atr(tf)
        floor = Decimal(str(self.params["sl_atr_floor"])) * atr if atr else Decimal(0)
        return [Evidence(detector=self.name, direction=direction, strength=strength,
                         zone=(sl - T, sl + T), ts=ctx.now, ttl_candles=3,
                         meta={"event": "TURTLE_SOUP", "sl": str(sl),
                               "sl_floor": str(floor)})]
