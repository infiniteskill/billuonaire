"""PaperBroker: honest, always-adverse fill simulation for the dry run.

Every fill executes at the given candle's OPEN pushed against us by
(half_spread_bps + slippage_bps): a LONG entry buys higher, its exit sells
lower; SHORT mirrors. Fill prices are tick-quantized; costs stay
full-precision Decimal money (config floats cross into Decimal via str()).

Cost semantics (verified): config stt_pct / exchange_pct are PERCENTS of
turnover (stt_pct 0.025 means 0.025% => multiplier 0.00025), so
costs = brokerage_flat + (stt_pct + exchange_pct) / 100 * price * qty.
"""

from __future__ import annotations

from decimal import Decimal

from trader.config import Settings
from trader.models.candle import Candle
from trader.models.position import Fill, Position
from trader.models.signal import TradePlan


class PaperBroker:
    def __init__(self, settings: Settings):
        f = settings.fills
        self.spec = settings.market_spec()
        self._adverse = (Decimal(str(f.half_spread_bps))
                         + Decimal(str(f.slippage_bps))) / 10000
        self._flat = Decimal(str(f.costs.brokerage_flat))
        self._pct = (Decimal(str(f.costs.stt_pct))
                     + Decimal(str(f.costs.exchange_pct))) / 100

    def entry_fill(self, plan: TradePlan, next_candle: Candle) -> Fill:
        """Fill the whole plan at next_candle.open, adverse in trade direction."""
        return self._fill(next_candle, plan.qty, plan.direction.value)

    def exit_fill(self, position: Position, candle: Candle, qty: int) -> Fill:
        """Exit qty at candle.open, adverse against the position (reversed)."""
        return self._fill(candle, qty, -position.plan.direction.value)

    def _fill(self, candle: Candle, qty: int, sign: int) -> Fill:
        """sign +1 pays up (LONG buy / SHORT cover), -1 receives down."""
        price = self.spec.quantize(candle.open * (1 + sign * self._adverse))
        return Fill(price=price, qty=qty, ts=candle.ts,
                    costs=self._flat + self._pct * price * qty)
