from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

from trader.models.market import NSE

TICK = NSE.tick_size  # deprecated: use MarketSpec.tick_size

def tick(value) -> Decimal:
    return NSE.quantize(value)  # deprecated NSE-default wrapper; use MarketSpec.quantize

class Timeframe(Enum):
    M1 = "1m"; M5 = "5m"; M15 = "15m"; H1 = "1h"; D1 = "1d"

    @property
    def minutes(self) -> int:
        if self is Timeframe.D1:
            raise ValueError("D1 duration is market-dependent; use MarketSpec.session_minutes")
        return {"1m": 1, "5m": 5, "15m": 15, "1h": 60}[self.value]

@dataclass(frozen=True)
class Candle:
    symbol: str
    tf: Timeframe
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int

    def __post_init__(self):
        if self.ts.tzinfo is None:
            raise ValueError("candle timestamp must be timezone-aware")
        if not (self.high >= max(self.open, self.close)
                and self.low <= min(self.open, self.close)
                and self.high >= self.low):
            raise ValueError(f"invalid OHLC {self.open}/{self.high}/{self.low}/{self.close}")

    @property
    def body(self) -> Decimal: return abs(self.close - self.open)
    @property
    def range(self) -> Decimal: return self.high - self.low
    @property
    def upper_wick(self) -> Decimal: return self.high - max(self.open, self.close)
    @property
    def lower_wick(self) -> Decimal: return min(self.open, self.close) - self.low
    @property
    def is_bullish(self) -> bool: return self.close > self.open
