"""TradePlan: the immutable trade intent an EntryFSM hands to execution.

All prices are tick-quantized Decimals. ``meta`` carries the score
decomposition (zone final + multipliers) plus entry/risk audit strings.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from trader.models.evidence import Direction


@dataclass(frozen=True)
class TradePlan:
    symbol: str
    direction: Direction
    entry_zone: tuple[Decimal, Decimal]
    stop: Decimal
    targets: list[Decimal]                  # [T1, T2, T3]
    qty: int
    score: float                            # ScoredZone.final at arm time
    created: datetime
    meta: dict = field(default_factory=dict)
