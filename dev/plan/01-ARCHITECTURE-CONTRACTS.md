# Architecture & Contracts

Modular monolith. One Python package, in-process. No Docker/Redis/microservices/web.

## Package Layout (`app/`)

```
app/
├── pyproject.toml                # python 3.11+, deps: typer, rich, pydantic, pandas, pyarrow, pytest
├── config/
│   ├── config.json               # all runtime knobs (committed template)
│   └── stocks.json               # watchlist
├── trader/
│   ├── cli.py                    # typer entrypoint: init/list/watch/status/journal/replay/report
│   ├── config.py                 # pydantic Settings; loads+validates config.json
│   ├── models/
│   │   ├── candle.py             # Candle, Timeframe
│   │   ├── level.py              # Level + LevelState state machine
│   │   ├── evidence.py           # Evidence, Direction
│   │   ├── signal.py             # TradePlan
│   │   └── position.py           # Position, Fill, ExitReason
│   ├── feed/
│   │   ├── base.py               # DataFeed ABC + FeedEvent
│   │   ├── mock.py               # ScenarioFeed: scripted ground-truth days
│   │   ├── file.py               # CSV/parquet historical feed
│   │   └── kite.py               # PHASE 6 — thin adapter, nothing else changes
│   ├── store/
│   │   ├── candles.py            # CandleStore: parquet cache, multi-TF aggregation
│   │   ├── levels.py             # LevelStore: persisted levels survive restarts
│   │   └── journal.py            # Journal: JSONL trades + skips + evidence snapshots
│   ├── detectors/
│   │   ├── base.py               # Detector ABC + DetectorRegistry
│   │   ├── swings.py structure.py orderblock.py breaker.py fvg.py
│   │   ├── liquidity.py sweep.py wyckoff.py volume.py cage.py timestats.py
│   ├── engine/
│   │   ├── context.py            # StockContext: everything a detector may read
│   │   ├── pipeline.py           # per-stock loop; identical for live/replay
│   │   ├── confluence.py         # weight renormalization + direction consensus
│   │   ├── gates.py              # Gate ABC + risk/time/regime/psychology gates
│   │   └── template.py           # day template classifier
│   ├── risk/
│   │   ├── sizing.py             # qty from risk budget + stop distance
│   │   └── limits.py             # daily counters, loss caps, consecutive-loss lock
│   ├── execution/
│   │   ├── broker.py             # Broker ABC
│   │   ├── paper.py              # PaperBroker: fills + costs + slippage model
│   │   └── manager.py            # PositionManager: stealth stop, trail, partials, squareoff
│   ├── replay/
│   │   ├── engine.py             # bar-by-bar driver, zero lookahead
│   │   └── metrics.py            # WR/PF/DD/per-template/per-gate, day-clustered
│   └── learn/
│       └── calibrate.py          # weekly weight recalibration from journal
└── tests/                        # mirrors package; scenario-based detector tests
```

## Core Contracts (exact signatures — all tasks build against these)

```python
# models/candle.py
class Timeframe(Enum): M1="1m"; M5="5m"; M15="15m"; H1="1h"; D1="1d"
@dataclass(frozen=True)
class Candle:
    symbol: str; tf: Timeframe; ts: datetime          # IST, candle open time
    open: Decimal; high: Decimal; low: Decimal; close: Decimal; volume: int
    # properties: body, range, upper_wick, lower_wick, is_bullish

# models/evidence.py
class Direction(Enum): LONG=1; SHORT=-1; NEUTRAL=0
@dataclass(frozen=True)
class Evidence:
    detector: str                  # registry name, e.g. "orderblock"
    direction: Direction
    strength: float                # 0.0–1.0, detector-local quality
    zone: tuple[Decimal, Decimal]  # (low, high) price zone it applies to
    ts: datetime                   # when produced
    ttl_candles: int               # expiry in M5 candles; 0 = this-candle only
    meta: dict                     # detector-specific detail (audit/journal)

# models/level.py — the Level State Machine (heart of the system)
class LevelKind(Enum): PDH; PDL; PWH; PWL; EQH; EQL; SWING_H; SWING_L; \
    OB_BULL; OB_BEAR; FVG_BULL; FVG_BEAR; ROUND; OI_WALL_CE; OI_WALL_PE; OPEN_RANGE_H; OPEN_RANGE_L
class LevelState(Enum): ACTIVE; TESTED; SWEPT; RECLAIMED; INVERTED; MITIGATED; DEAD
@dataclass
class Level:
    id: str; symbol: str; kind: LevelKind
    zone: tuple[Decimal, Decimal]; born: datetime; tf: Timeframe
    state: LevelState; touches: int; state_history: list[tuple[datetime, LevelState]]
    def transition(self, candle: Candle) -> LevelState | None   # pure rules, unit-tested

# feed/base.py
@dataclass(frozen=True)
class FeedEvent:                   # ONE event type for live AND replay
    candle: Candle                 # closed candle (M1 granularity upward-aggregated by store)
class DataFeed(ABC):
    def subscribe(self, symbols: list[str]) -> None
    def events(self) -> Iterator[FeedEvent]                 # blocking iterator
    def historical(self, symbol: str, tf: Timeframe,
                   start: date, end: date) -> list[Candle]

# detectors/base.py
class Detector(ABC):
    name: str                                  # registry key = config key
    requires: set[str] = set()                 # data needs, e.g. {"options_chain"}
    def detect(self, ctx: "StockContext") -> list[Evidence]
class DetectorRegistry:
    def __init__(self, settings: Settings)     # instantiates ONLY enabled detectors
    def run_all(self, ctx: StockContext) -> list[Evidence]
    # detector raising exception → logged, skipped, others unaffected

# engine/context.py — read-only view handed to detectors
@dataclass
class StockContext:
    symbol: str; now: datetime
    candles: CandleView            # .last(n, tf), .today(tf), .prev_day(tf) — NO future access
    levels: list[Level]
    evidence_history: list[Evidence]
    day: DayState                  # template, phase, trap status, session flags
    options: OptionsSnapshot | None    # None when no data → cage detector returns []

# engine/confluence.py
@dataclass
class ConfluenceResult:
    direction: Direction; score: float          # 0–100 over ENABLED detectors, renormalized
    contributions: dict[str, float]             # per-detector, for journal
def score(evidence: list[Evidence], weights: dict[str, float],
          price: Decimal) -> ConfluenceResult
# weights from config; missing/disabled detector keys renormalize to sum 100

# engine/gates.py
@dataclass(frozen=True)
class Verdict: allow: bool; gate: str; reason: str
class Gate(ABC):
    name: str
    def check(self, ctx: StockContext, plan: "TradePlan|None") -> Verdict
# gates: TimeWindowGate, RiskBudgetGate, RegimeVetoGate, PsychologyGate, TemplateGate
# ALL gates must pass. Gates veto; detectors never do.

# models/signal.py
@dataclass(frozen=True)
class TradePlan:
    symbol: str; direction: Direction
    entry_zone: tuple[Decimal, Decimal]; stop: Decimal
    targets: list[Decimal]                      # 1.5R / 2.5R / 4R
    qty: int; confluence: ConfluenceResult; created: datetime

# execution/broker.py
class Broker(ABC):
    def place_market(self, symbol: str, direction: Direction, qty: int) -> Fill
    def positions(self) -> list[Position]
# PaperBroker fill model: next-candle open ± half_spread + slippage_bps; costs applied
# KiteBroker (later) implements same ABC. PositionManager doesn't know which.

# execution/manager.py — stealth stop lives HERE, never at broker
class PositionManager:
    def on_candle(self, pos: Position, ctx: StockContext) -> list[Action]
    # Actions: EXIT_STOP (close-confirmed breach), PARTIAL(1R/2R), TRAIL(structure),
    #          SQUAREOFF(15:10), BREAKEVEN(at 1R). NEVER widens stop.

# replay/engine.py
def run_replay(symbols: list[str], start: date, end: date,
               settings: Settings) -> ReplayReport
# constructs FileFeed → same pipeline.step() as live → metrics day-clustered
```

## config.json (shape)

```json
{
  "capital": 100000,
  "risk": {"per_trade_pct": 0.5, "daily_loss_pct": 1.5, "max_trades_day": 3,
           "max_per_stock": 1, "consecutive_loss_stop": 2, "expiry_size_mult": 0.5},
  "time": {"observe_until": "10:45", "no_entry_after": "14:30", "squareoff": "15:10"},
  "stops": {"atr_buffer": 0.25, "wick_tolerance_candles": 1, "round_offset_ticks": 3},
  "confluence": {"threshold": 65,
    "weights": {"sweep": 20, "structure": 15, "orderblock": 12, "breaker": 10,
                "fvg": 8, "liquidity": 10, "wyckoff": 10, "cage": 10, "timestats": 5}},
  "detectors": {"enabled": ["swings","structure","orderblock","breaker","fvg",
                "liquidity","sweep","wyckoff","volume","timestats"],
                "disabled": ["cage"]},
  "fills": {"slippage_bps": 3, "half_spread_bps": 2,
            "costs": {"brokerage_flat": 20, "stt_pct": 0.025, "exchange_pct": 0.00297}}
}
```

Disable any detector → its weight redistributes proportionally → system unaffected.
`cage` disabled by default until options data exists (`requires={"options_chain"}` auto-inerts it anyway).

## Event Flow — Live vs Replay (identical middle)

```
LIVE:   KiteFeed/MockFeed ─┐
                            ├→ CandleStore → pipeline.step(ctx) → verdict → PaperBroker → Journal
REPLAY: FileFeed (bar-by-bar)┘        (same)         (same)          (same)      (same)
```

`pipeline.step` is pure w.r.t. its inputs: takes StockContext, returns verdict + actions.
No wall-clock reads inside — `ctx.now` injected. This is what makes replay honest.
