# 🎯 RADAR: Master System Architecture

> **Project Codename**: RADAR (Retail Anti-Deception Algorithmic Reader)
> **Mission**: Build the most precise manipulation detection and prediction system
> **Philosophy**: Modular, Independent, Precise, Extensible

---

## 🔴 CRITICAL PRINCIPLES

### 1. Financial Precision
```
NO TOLERANCE FOR:
- Off-by-one errors in price levels
- Missed manipulation patterns
- False signals that could cause losses
- Race conditions in real-time data
- Silent failures

EVERY calculation must be:
- Double-checked
- Logged for audit
- Validated against edge cases
```

### 2. Modular Independence
```
Each app/module MUST:
- Run standalone
- Have its own API
- Not break if others fail
- Be testable in isolation
- Have clear input/output contracts
```

### 3. Real-Time Ready
```
Design for:
- Sub-second updates
- WebSocket streaming
- Event-driven architecture
- No blocking operations
```

---

## 🏗️ SYSTEM ARCHITECTURE

### Microservices Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          RADAR SYSTEM - MICROSERVICES                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ╔═══════════════════════════════════════════════════════════════════════════╗ │
│  ║                           API GATEWAY (FastAPI)                            ║ │
│  ║  /api/v1/*  →  Routes to appropriate service                               ║ │
│  ╚═══════════════════════════════════════════════════════════════════════════╝ │
│                                      │                                          │
│         ┌────────────────────────────┼────────────────────────────┐             │
│         │                            │                            │             │
│         ▼                            ▼                            ▼             │
│  ┌─────────────┐            ┌─────────────────┐           ┌─────────────────┐  │
│  │ DATA-FEED   │            │ ANALYSIS-ENGINE │           │ PREDICTION-     │  │
│  │ SERVICE     │───────────▶│ SERVICE         │──────────▶│ ENGINE          │  │
│  │             │  raw data  │                 │ detections│ SERVICE         │  │
│  │ • jugaad-data│           │ • Structure     │           │                 │  │
│  │ • Real-time │            │ • Sweeps        │           │ • Markov        │  │
│  │ • Historical│            │ • OB/FVG        │           │ • Confluence    │  │
│  │ • Multi-sym │            │ • Fibonacci     │           │ • Projection    │  │
│  └─────────────┘            └─────────────────┘           └─────────────────┘  │
│         │                            │                            │             │
│         │                            │                            │             │
│         ▼                            ▼                            ▼             │
│  ┌─────────────┐            ┌─────────────────┐           ┌─────────────────┐  │
│  │ LEARNING    │◀───────────│ CONTEXT-ENGINE  │◀──────────│ SIGNAL-         │  │
│  │ SERVICE     │  outcomes  │ SERVICE         │  signals  │ GENERATOR       │  │
│  │             │            │                 │           │ SERVICE         │  │
│  │ • Time prob │            │ • Multi-TF      │           │                 │  │
│  │ • Pattern   │            │ • HTF bias      │           │ • Entry/SL/TP   │  │
│  │ • Calibrate │            │ • Kill zones    │           │ • Risk mgmt     │  │
│  └─────────────┘            └─────────────────┘           └─────────────────┘  │
│         │                            │                            │             │
│         └────────────────────────────┴────────────────────────────┘             │
│                                      │                                          │
│                                      ▼                                          │
│  ╔═══════════════════════════════════════════════════════════════════════════╗ │
│  ║                           PROTECTION-LAYER                                 ║ │
│  ║  • Speed alerts  • Emotion detection  • Pattern trap scoring               ║ │
│  ╚═══════════════════════════════════════════════════════════════════════════╝ │
│                                      │                                          │
│                                      ▼                                          │
│  ╔═══════════════════════════════════════════════════════════════════════════╗ │
│  ║                           WEB DASHBOARD (React/Vue)                        ║ │
│  ║  • Interactive charts  • Real-time updates  • Symbol switching             ║ │
│  ╚═══════════════════════════════════════════════════════════════════════════╝ │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 MODULE BREAKDOWN

### Core Services (8 Independent Apps)

| # | Service | Purpose | Design Doc |
|---|---------|---------|------------|
| 1 | **data-feed** | Fetch OHLC from jugaad-data, real-time streaming | [01-DATA-FEED.md](file:///home/doom/Public/People/Me/2026/design/01-DATA-FEED.md) |
| 2 | **candle-processor** | Normalize, aggregate, multi-TF | [02-CANDLE-PROCESSOR.md](file:///home/doom/Public/People/Me/2026/design/02-CANDLE-PROCESSOR.md) |
| 3 | **structure-analyzer** | Swings, BOS, CHoCH, Fibonacci | [03-STRUCTURE-ANALYZER.md](file:///home/doom/Public/People/Me/2026/design/03-STRUCTURE-ANALYZER.md) |
| 4 | **liquidity-mapper** | Pools, equal H/L, PDH/PDL | [04-LIQUIDITY-MAPPER.md](file:///home/doom/Public/People/Me/2026/design/04-LIQUIDITY-MAPPER.md) |
| 5 | **detection-engine** | Sweeps, OBs, FVGs, traps | [05-DETECTION-ENGINE.md](file:///home/doom/Public/People/Me/2026/design/05-DETECTION-ENGINE.md) |
| 6 | **context-engine** | Multi-TF, kill zones, phases | [06-CONTEXT-ENGINE.md](file:///home/doom/Public/People/Me/2026/design/06-CONTEXT-ENGINE.md) |
| 7 | **prediction-engine** | Markov, scenarios, projections | [07-PREDICTION-ENGINE.md](file:///home/doom/Public/People/Me/2026/design/07-PREDICTION-ENGINE.md) |
| 8 | **signal-generator** | Entry/SL/TP, confluence scoring | [08-SIGNAL-GENERATOR.md](file:///home/doom/Public/People/Me/2026/design/08-SIGNAL-GENERATOR.md) |

### Support Services (4 Independent Apps)

| # | Service | Purpose | Design Doc |
|---|---------|---------|------------|
| 9 | **learning-engine** | Time probs, pattern stats | [09-LEARNING-ENGINE.md](file:///home/doom/Public/People/Me/2026/design/09-LEARNING-ENGINE.md) |
| 10 | **protection-layer** | Speed/emotion alerts | [10-PROTECTION-LAYER.md](file:///home/doom/Public/People/Me/2026/design/10-PROTECTION-LAYER.md) |
| 11 | **replay-engine** | Historical testing, backtesting | [11-REPLAY-ENGINE.md](file:///home/doom/Public/People/Me/2026/design/11-REPLAY-ENGINE.md) |
| 12 | **web-dashboard** | Frontend, charts, UI | [12-WEB-DASHBOARD.md](file:///home/doom/Public/People/Me/2026/design/12-WEB-DASHBOARD.md) |

### Infrastructure (2 Apps)

| # | Service | Purpose | Design Doc |
|---|---------|---------|------------|
| 13 | **api-gateway** | Route, aggregate, WebSocket | [13-API-GATEWAY.md](file:///home/doom/Public/People/Me/2026/design/13-API-GATEWAY.md) |
| 14 | **event-bus** | Inter-service communication | [14-EVENT-BUS.md](file:///home/doom/Public/People/Me/2026/design/14-EVENT-BUS.md) |

---

## 🔗 SERVICE COMMUNICATION

### Event-Driven Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EVENT BUS (Redis Pub/Sub)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EVENTS:                                                                     │
│  ══════                                                                      │
│                                                                              │
│  data.candle.new        → New candle received                               │
│  data.symbol.changed    → User switched symbol                              │
│                                                                              │
│  structure.swing.new    → New swing point detected                          │
│  structure.bos.detected → Break of structure                                │
│  structure.choch.detected → Change of character                             │
│                                                                              │
│  liquidity.pool.new     → New liquidity pool mapped                         │
│  liquidity.sweep.detected → Sweep occurred                                  │
│                                                                              │
│  detection.ob.new       → Order block formed                                │
│  detection.fvg.new      → Fair value gap formed                             │
│  detection.trap.alert   → Trap chain detected                               │
│                                                                              │
│  context.updated        → Context state changed                             │
│  context.killzone.active → Kill zone started                                │
│  context.phase.changed  → Manipulation phase changed                        │
│                                                                              │
│  prediction.scenario.new → New projection generated                         │
│  prediction.updated     → Projection probabilities updated                  │
│                                                                              │
│  signal.entry.ready     → Entry signal generated                            │
│  signal.alert.triggered → Protection alert fired                            │
│                                                                              │
│  learning.outcome.logged → Trade result recorded                            │
│  learning.calibrated    → Probabilities updated                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### API Contracts

```
Each service exposes:
  
  /health          → Liveness check
  /ready           → Readiness check
  /metrics         → Performance metrics
  /api/v1/*        → Service-specific endpoints

Example (detection-engine):
  
  GET  /api/v1/sweeps/{symbol}          → List detected sweeps
  GET  /api/v1/orderblocks/{symbol}     → List order blocks
  GET  /api/v1/fvgs/{symbol}            → List fair value gaps
  POST /api/v1/analyze                  → Trigger full analysis
```

---

## 📐 DATA FLOW

### Real-Time Flow

```
USER OPENS DASHBOARD
        │
        ▼
┌───────────────┐     ┌───────────────┐
│ web-dashboard │────▶│ api-gateway   │
│ (WebSocket)   │     │ (subscribe)   │
└───────────────┘     └───────┬───────┘
                              │
                              ▼
                    ┌───────────────┐
                    │ data-feed     │ ← Starts streaming for symbol
                    │ (jugaad-data) │
                    └───────┬───────┘
                            │ EMIT: data.candle.new
                            ▼
              ┌─────────────────────────────┐
              │         EVENT BUS           │
              └─────────────────────────────┘
                   │         │         │
                   ▼         ▼         ▼
            ┌──────────┐ ┌──────────┐ ┌──────────┐
            │ candle-  │ │ structure│ │ liquidity│
            │ processor│ │ -analyzer│ │ -mapper  │
            └────┬─────┘ └────┬─────┘ └────┬─────┘
                 │            │            │
                 │ EMIT: candle.processed  │
                 │ EMIT: swing.new         │
                 │ EMIT: liquidity.pool.new│
                 └────────────┬────────────┘
                              │
                              ▼
                    ┌───────────────┐
                    │ detection-    │
                    │ engine        │
                    └───────┬───────┘
                            │ EMIT: sweep.detected
                            │ EMIT: ob.new
                            ▼
                    ┌───────────────┐
                    │ context-      │
                    │ engine        │
                    └───────┬───────┘
                            │ EMIT: context.updated
                            ▼
                    ┌───────────────┐
                    │ prediction-   │
                    │ engine        │
                    └───────┬───────┘
                            │ EMIT: prediction.scenario.new
                            ▼
                    ┌───────────────┐
                    │ signal-       │
                    │ generator     │
                    └───────┬───────┘
                            │ EMIT: signal.entry.ready
                            ▼
              ┌─────────────────────────────┐
              │         API GATEWAY         │
              │    (WebSocket broadcast)    │
              └─────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ web-dashboard │ ← UI updates in real-time
                    │ (displays)    │
                    └───────────────┘
```

---

## 📁 PROJECT STRUCTURE

```
radar/
├── design/                              # Design documents (YOU ARE HERE)
│   ├── 00-MASTER-ARCHITECTURE.md        # This file
│   ├── 01-DATA-FEED.md                  # Data feed service design
│   ├── 02-CANDLE-PROCESSOR.md           # Candle processing design
│   ├── 03-STRUCTURE-ANALYZER.md         # Structure analysis design
│   ├── 04-LIQUIDITY-MAPPER.md           # Liquidity mapping design
│   ├── 05-DETECTION-ENGINE.md           # Detection engine design
│   ├── 06-CONTEXT-ENGINE.md             # Context engine design
│   ├── 07-PREDICTION-ENGINE.md          # Prediction engine design
│   ├── 08-SIGNAL-GENERATOR.md           # Signal generator design
│   ├── 09-LEARNING-ENGINE.md            # Learning engine design
│   ├── 10-PROTECTION-LAYER.md           # Protection layer design
│   ├── 11-REPLAY-ENGINE.md              # Replay engine design
│   ├── 12-WEB-DASHBOARD.md              # Web dashboard design
│   ├── 13-API-GATEWAY.md                # API gateway design
│   ├── 14-EVENT-BUS.md                  # Event bus design
│   └── 99-ICT-CONCEPTS-REFERENCE.md     # ICT/SMC complete reference
│
├── services/                            # Service implementations
│   ├── data-feed/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── README.md
│   ├── candle-processor/
│   ├── structure-analyzer/
│   ├── liquidity-mapper/
│   ├── detection-engine/
│   ├── context-engine/
│   ├── prediction-engine/
│   ├── signal-generator/
│   ├── learning-engine/
│   ├── protection-layer/
│   ├── replay-engine/
│   ├── api-gateway/
│   └── event-bus/
│
├── web/                                 # Web dashboard
│   ├── src/
│   ├── public/
│   └── package.json
│
├── shared/                              # Shared code/types
│   ├── models/                          # Data models (Candle, OB, etc.)
│   ├── events/                          # Event definitions
│   └── utils/                           # Shared utilities
│
├── docker-compose.yml                   # Run all services
├── docker-compose.dev.yml               # Development mode
└── README.md                            # Project documentation
```

---

## 🎓 ICT CONCEPTS TO IMPLEMENT

### Must-Have (MVP)

| Concept | Description | Service |
|---------|-------------|---------|
| **Swing Points** | Local highs/lows | structure-analyzer |
| **BOS** | Break of Structure | structure-analyzer |
| **CHoCH** | Change of Character | structure-analyzer |
| **Fibonacci OTE** | 61.8% - 79% optimal entry | structure-analyzer |
| **Order Blocks** | Last opposite candle before displacement | detection-engine |
| **Fair Value Gaps** | Imbalanced price areas | detection-engine |
| **Liquidity Pools** | Stop clusters, equal H/L | liquidity-mapper |
| **Sweeps** | Liquidity raids | detection-engine |
| **PDH/PDL** | Previous day high/low | liquidity-mapper |
| **PWH/PWL** | Previous week high/low | liquidity-mapper |
| **Kill Zones** | High manipulation time windows | context-engine |
| **Power of 3** | Accumulation → Manipulation → Distribution | context-engine |

### Advanced (Post-MVP)

| Concept | Description | Service |
|---------|-------------|---------|
| **SMT Divergence** | Smart Money Technique | detection-engine |
| **Mitigation** | OB touch and reaction | detection-engine |
| **Breaker Blocks** | Failed OB becomes opposite | detection-engine |
| **IPDA** | Interbank Price Delivery Algorithm | prediction-engine |
| **Judas Swing** | Fake initial move | detection-engine |
| **Silver Bullet** | Specific time entries | context-engine |
| **ICT Macros** | Time-based patterns | context-engine |

---

## 🔒 PRECISION REQUIREMENTS

### Price Calculations

```python
# NEVER use float for money!
from decimal import Decimal, ROUND_HALF_UP

class PriceLevel:
    """Immutable, precise price level"""
    
    def __init__(self, value: Union[float, str, Decimal]):
        self.value = Decimal(str(value)).quantize(
            Decimal('0.05'),  # NSE tick size
            rounding=ROUND_HALF_UP
        )
    
    def __eq__(self, other):
        return self.value == other.value
    
    def distance_from(self, other: 'PriceLevel') -> Decimal:
        return abs(self.value - other.value)
    
    def percentage_from(self, other: 'PriceLevel') -> Decimal:
        return (self.value - other.value) / other.value * 100
```

### Fibonacci Calculations

```python
class FibonacciLevels:
    """Precise Fibonacci retracement/extension levels"""
    
    LEVELS = {
        'OTE_HIGH': Decimal('0.79'),   # OTE zone top
        'OTE_MID': Decimal('0.705'),   # OTE zone middle (ICT sweet spot)
        'OTE_LOW': Decimal('0.618'),   # OTE zone bottom
        'HALF': Decimal('0.5'),        # 50% level
        'SHALLOW': Decimal('0.382'),   # Shallow retracement
        'DEEP': Decimal('0.886'),      # Deep retracement
        'EXTENSION_1': Decimal('1.0'), # Full extension
        'EXTENSION_2': Decimal('1.272'), # 127.2% extension
        'EXTENSION_3': Decimal('1.618'), # Golden ratio extension
    }
    
    def __init__(self, swing_high: PriceLevel, swing_low: PriceLevel):
        self.high = swing_high
        self.low = swing_low
        self.range = swing_high.value - swing_low.value
        
    def retracement_level(self, level_name: str) -> PriceLevel:
        """Calculate retracement level for bullish swing"""
        ratio = self.LEVELS[level_name]
        price = self.high.value - (self.range * ratio)
        return PriceLevel(price)
    
    def extension_level(self, level_name: str) -> PriceLevel:
        """Calculate extension level"""
        ratio = self.LEVELS[level_name]
        price = self.low.value + (self.range * ratio)
        return PriceLevel(price)
    
    def get_ote_zone(self) -> Tuple[PriceLevel, PriceLevel]:
        """Get optimal trade entry zone (61.8% - 79%)"""
        return (
            self.retracement_level('OTE_LOW'),
            self.retracement_level('OTE_HIGH')
        )
    
    def is_in_ote(self, price: PriceLevel) -> bool:
        """Check if price is in optimal entry zone"""
        ote_low, ote_high = self.get_ote_zone()
        return ote_low.value <= price.value <= ote_high.value
```

---

## ⚠️ ERROR HANDLING

### Every Service Must

```python
class ServiceError(Exception):
    """Base error for all services"""
    def __init__(self, message: str, code: str, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        
    def to_dict(self):
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp.isoformat()
            }
        }

# Error codes per service
class DataFeedError(ServiceError):
    SYMBOL_NOT_FOUND = "DATA_001"
    CONNECTION_FAILED = "DATA_002"
    RATE_LIMITED = "DATA_003"
    INVALID_DATE_RANGE = "DATA_004"

class DetectionError(ServiceError):
    INSUFFICIENT_DATA = "DETECT_001"
    INVALID_CANDLES = "DETECT_002"
    CALCULATION_ERROR = "DETECT_003"
```

### Logging Standard

```python
import structlog

logger = structlog.get_logger()

# Every operation must log:
logger.info(
    "sweep_detected",
    symbol="NIFTY",
    direction="BULLISH",
    level=22350.50,
    quality_score=0.85,
    timestamp="2025-01-31T10:45:00+05:30"
)

# Every error must log:
logger.error(
    "detection_failed",
    symbol="BANKNIFTY",
    error_code="DETECT_002",
    error_message="Insufficient candle data",
    candles_received=5,
    candles_required=20
)
```

---

## ✅ NEXT STEPS

1. **Create individual design documents** (01-14)
2. **Define exact data models** in each design doc
3. **Define exact API contracts** for each service
4. **Define exact event schemas** for event bus
5. **Review and approve** before implementation

---

> **This is the foundation. Each design document will go deeper into its specific module. No code until ALL designs are reviewed and approved.**
