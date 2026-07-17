"""Fill + Position: execution-side trade state.

A Position is born from a TradePlan plus its entry Fill. ``stop`` is the
only price that ever moves (breakeven / trailing, ratchet-only -- never
widened), ``partials`` marks which R-ladder rungs already fired
("1R"/"2R"/"3R"), and ``hunt_survived`` journals a stop wick-through whose
candle closed back on our side (stealth stops never exit on wicks).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto

from trader.models.signal import TradePlan


class PositionStatus(Enum):
    OPEN = auto(); CLOSED = auto()


class ExitReason(Enum):
    STOP = "EXIT_STOP"; COUNTER = "EXIT_COUNTER"
    STALL = "EXIT_STALL"; EOD = "EXIT_EOD"; TARGET = "EXIT_TARGET"


@dataclass(frozen=True)
class Fill:
    price: Decimal
    qty: int
    ts: datetime
    costs: Decimal        # brokerage + statutory, full-precision money


@dataclass
class Position:
    plan: TradePlan
    entry: Fill
    remaining_qty: int
    stop: Decimal                        # live stop; plan.stop stays original
    realized: Decimal = Decimal("0")
    status: PositionStatus = PositionStatus.OPEN
    partials: set[str] = field(default_factory=set)
    hunt_survived: bool = False
    opened_ts: datetime | None = None    # defaults to entry fill ts

    def __post_init__(self) -> None:
        if self.opened_ts is None:
            self.opened_ts = self.entry.ts

    @property
    def risk_pts(self) -> Decimal:
        """Initial risk |entry fill - planned stop|: the fixed R denominator."""
        return abs(self.entry.price - self.plan.stop)

    def r_multiple(self, price: Decimal) -> Decimal:
        """Signed R at price: (price - entry)/risk for LONG, mirrored SHORT."""
        return (price - self.entry.price) * self.plan.direction.value / self.risk_pts
