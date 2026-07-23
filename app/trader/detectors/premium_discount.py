"""Premium/Discount detector ("premium_discount"): a directional-permission
GATE from the master EXT dealing range -- NOT a trade signal. Encodes the
taught rule "trade at extremes, never at the mid".

Range = [lowest master EXT_L low, highest master EXT_H high] on ``tf`` (the
taught anchor from extremes.py, master pivots only); EQ = mid; range_pos =
(price - lo) / (hi - lo). Emits ONE NEUTRAL context Evidence per bar carrying
{lo, hi, eq, range_pos, side, ote, permits} in meta:
  side = "discount" (range_pos <= 0.5 - deadband/2) -> permits LONG
       = "premium"  (range_pos >= 0.5 + deadband/2) -> permits SHORT
       = "mid"      (inside the EQ deadband)         -> permits nothing
strength = |range_pos - 0.5| * 2 (conviction we are AT an extreme, 0 at EQ,
1 at either boundary). ``ote`` flags the OTE retracement bands (discount
0.21-0.38 / premium 0.62-0.79).

Anti-fragility (RETHINK B5): requires a confirmed master EXT_H+EXT_L pair AND
range height >= min_range_atr * ATR(tf); a tiny/absent range emits nothing
(never a fragile fixed-window side). direction is NEUTRAL by design -- the
gate licenses a side via meta.permits, it does not itself push a trade.
"""
from __future__ import annotations

from decimal import Decimal

from trader.detectors.base import Detector, register
from trader.engine.context import StockContext
from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import LevelKind, LevelState

_ACTIVE = (LevelState.ACTIVE, LevelState.TESTED)
_DEFAULTS = {"tf": "1h", "min_range_atr": 8.0, "eq_deadband": 0.10}
_PERMITS = {"discount": "LONG", "premium": "SHORT", "mid": None}


@register
class PremiumDiscountDetector(Detector):
    name = "premium_discount"

    def __init__(self, params: dict):
        super().__init__({**_DEFAULTS, **params})

    def detect(self, ctx: StockContext) -> list[Evidence]:
        tf = Timeframe(self.params["tf"])
        masters = [lv for lv in ctx.levels
                   if lv.state in _ACTIVE and lv.meta.get("master")
                   and (lv.tf is tf or lv.tf is None)]
        highs = [lv for lv in masters if lv.kind is LevelKind.EXT_H]
        lows = [lv for lv in masters if lv.kind is LevelKind.EXT_L]
        if not highs or not lows:
            return []
        hi = max(h.zone[1] for h in highs)
        lo = min(l.zone[0] for l in lows)
        if hi <= lo:
            return []
        atr = ctx.atr(tf) or ctx.atr(Timeframe.M5)
        if atr is None or (hi - lo) < Decimal(str(self.params["min_range_atr"])) * atr:
            return []
        last = ctx.candles.last(1, Timeframe.M1)
        if not last:
            return []
        pos = float((last[-1].close - lo) / (hi - lo))
        dead = float(self.params["eq_deadband"]) / 2
        side = ("discount" if pos <= 0.5 - dead
                else "premium" if pos >= 0.5 + dead else "mid")
        return [Evidence(
            detector=self.name, direction=Direction.NEUTRAL,
            strength=min(1.0, abs(pos - 0.5) * 2), zone=(lo, hi),
            ts=ctx.now, ttl_candles=1,
            meta={"lo": str(lo), "hi": str(hi), "eq": str((lo + hi) / 2),
                  "range_pos": round(pos, 3), "side": side,
                  "ote": 0.21 <= pos <= 0.38 or 0.62 <= pos <= 0.79,
                  "permits": _PERMITS[side]})]
