from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum, auto
from trader.models.candle import Timeframe

class LevelKind(Enum):
    PDH = auto(); PDL = auto(); PWH = auto(); PWL = auto()
    EQH = auto(); EQL = auto(); SWING_H = auto(); SWING_L = auto()
    OB_BULL = auto(); OB_BEAR = auto(); FVG_BULL = auto(); FVG_BEAR = auto()
    ROUND = auto(); OI_WALL_CE = auto(); OI_WALL_PE = auto()
    OPEN_RANGE_H = auto(); OPEN_RANGE_L = auto()

class LevelState(Enum):
    ACTIVE = auto(); TESTED = auto(); SWEPT = auto(); RECLAIMED = auto()
    INVERTED = auto(); MITIGATED = auto(); DEAD = auto()

@dataclass
class Level:
    id: str
    symbol: str
    kind: LevelKind
    zone: tuple[Decimal, Decimal]
    born: datetime
    tf: Timeframe | None
    state: LevelState = LevelState.ACTIVE
    touches: int = 0
    state_history: list[tuple[datetime, LevelState]] = field(default_factory=list)

    def record_state(self, ts: datetime, state: LevelState) -> None:
        self.state = state
        self.state_history.append((ts, state))
