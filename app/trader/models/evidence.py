from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

class Direction(Enum):
    LONG = 1; SHORT = -1; NEUTRAL = 0

@dataclass(frozen=True)
class Evidence:
    detector: str
    direction: Direction
    strength: float
    zone: tuple[Decimal, Decimal]
    ts: datetime
    ttl_candles: int
    meta: dict = field(default_factory=dict)
