"""PaperBroker: honest, always-adverse fill simulation for the dry run.

Every market-style fill executes at the given candle's OPEN pushed against
us by (half_spread_bps + slippage_bps): a LONG entry buys higher, its exit
sells lower; SHORT mirrors. A resting LIMIT traded through (explicit
``price``) fills AT its price exactly -- a real limit order can never fill
worse than its limit. Fill prices are tick-quantized; costs stay
full-precision Decimal money (config floats cross into Decimal via str()).

Cost semantics (verified): config stt_pct / exchange_pct are PERCENTS of
turnover (stt_pct 0.025 means 0.025% => multiplier 0.00025). NSE intraday
equity STT applies to the SELL leg only (LONG exit / SHORT entry);
exchange_pct (txn charges + GST + stamp duty approx) applies both legs:
costs = brokerage_flat + (sell? stt_pct + exchange_pct : exchange_pct) / 100 * price * qty.
"""

from __future__ import annotations

from decimal import Decimal

from trader.config import CostsCfg, Settings
from trader.models.candle import Candle
from trader.models.position import Fill, Position
from trader.models.signal import TradePlan


def leg_cost(c: CostsCfg, price: Decimal, qty: int, sell: bool) -> Decimal:
    """ONE leg's cost at price x qty: brokerage_flat + pct-of-turnover.
    STT hits the SELL leg only; exchange_pct both legs. The single costing
    truth, shared by PaperBroker fills and the entry viability gate."""
    pct = (Decimal(str(c.stt_pct)) if sell else Decimal(0)) + Decimal(str(c.exchange_pct))
    return Decimal(str(c.brokerage_flat)) + pct / 100 * price * qty


def round_trip_cost(c: CostsCfg, price: Decimal, qty: int) -> Decimal:
    """Entry + exit estimate, both legs priced at ``price``: whichever side
    sells, STT is charged exactly once per round trip."""
    return leg_cost(c, price, qty, True) + leg_cost(c, price, qty, False)


def trade_cost(c: CostsCfg, price: Decimal, qty: int, exits: int = 1) -> Decimal:
    """Full-trade estimate: entry + ``exits`` exit tranches (manager ladder),
    all priced at ``price``. Percentage costs are turnover-proportional so
    splitting the exit changes nothing there (STT still one full sell side),
    but EVERY extra order pays brokerage_flat again."""
    return round_trip_cost(c, price, qty) \
        + (exits - 1) * Decimal(str(c.brokerage_flat))


class PaperBroker:
    def __init__(self, settings: Settings):
        f = settings.fills
        self.spec = settings.market_spec()
        self._adverse = (Decimal(str(f.half_spread_bps))
                         + Decimal(str(f.slippage_bps))) / 10000
        self._costs = f.costs

    def entry_fill(self, plan: TradePlan, candle: Candle,
                   price: Decimal | None = None) -> Fill:
        """Fill the whole plan at candle.open, adverse in trade direction.
        ``price`` = resting limit traded through: fill AT it exactly -- a
        limit order can never fill worse than its price."""
        return self._fill(candle.open if price is None else price, candle.ts,
                          plan.qty, plan.direction.value,
                          self._adverse if price is None else Decimal(0))

    def exit_fill(self, position: Position, candle: Candle, qty: int,
                  price: Decimal | None = None) -> Fill:
        """Exit qty at candle.open, adverse against the position (reversed).
        ``price`` = limit fill AT that price exactly (target exits) -- a
        limit order can never fill worse than its price."""
        sign = -position.plan.direction.value
        return (self._fill(candle.open, candle.ts, qty, sign, self._adverse)
                if price is None
                else self._fill(price, candle.ts, qty, sign, Decimal(0)))

    def _fill(self, base: Decimal, ts, qty: int, sign: int, rate: Decimal) -> Fill:
        """sign +1 pays up (LONG buy / SHORT cover), -1 receives down (a SELL
        -- STT applies)."""
        price = self.spec.quantize(base * (1 + sign * rate))
        return Fill(price=price, qty=qty, ts=ts,
                    costs=leg_cost(self._costs, price, qty, sign < 0))
