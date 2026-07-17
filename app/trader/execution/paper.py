"""PaperBroker: honest, always-adverse fill simulation for the dry run.

Every fill executes at the given candle's OPEN pushed against us by
(half_spread_bps + slippage_bps): a LONG entry buys higher, its exit sells
lower; SHORT mirrors. Fill prices are tick-quantized; costs stay
full-precision Decimal money (config floats cross into Decimal via str()).

Cost semantics (verified): config stt_pct / exchange_pct are PERCENTS of
turnover (stt_pct 0.025 means 0.025% => multiplier 0.00025). NSE intraday
equity STT applies to the SELL leg only (LONG exit / SHORT entry);
exchange_pct (txn charges + GST + stamp duty approx) applies both legs:
costs = brokerage_flat + (sell? stt_pct + exchange_pct : exchange_pct) / 100 * price * qty.
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
        self._half = Decimal(str(f.half_spread_bps)) / 10000
        self._adverse = self._half + Decimal(str(f.slippage_bps)) / 10000
        self._flat = Decimal(str(f.costs.brokerage_flat))
        self._exch = Decimal(str(f.costs.exchange_pct)) / 100
        self._stt = Decimal(str(f.costs.stt_pct)) / 100

    def entry_fill(self, plan: TradePlan, next_candle: Candle) -> Fill:
        """Fill the whole plan at next_candle.open, adverse in trade direction."""
        return self._fill(next_candle.open, next_candle.ts, plan.qty,
                          plan.direction.value, self._adverse)

    def exit_fill(self, position: Position, candle: Candle, qty: int,
                  price: Decimal | None = None) -> Fill:
        """Exit qty at candle.open, adverse against the position (reversed).
        ``price`` = limit fill AT that price (target exits): half-spread
        adverse only, no slippage -- limit orders don't slip."""
        sign = -position.plan.direction.value
        return (self._fill(candle.open, candle.ts, qty, sign, self._adverse)
                if price is None
                else self._fill(price, candle.ts, qty, sign, self._half))

    def _fill(self, base: Decimal, ts, qty: int, sign: int, rate: Decimal) -> Fill:
        """sign +1 pays up (LONG buy / SHORT cover), -1 receives down (a SELL
        -- STT applies)."""
        price = self.spec.quantize(base * (1 + sign * rate))
        pct = self._exch + (self._stt if sign < 0 else 0)
        return Fill(price=price, qty=qty, ts=ts,
                    costs=self._flat + pct * price * qty)
