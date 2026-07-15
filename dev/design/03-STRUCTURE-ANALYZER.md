# 📐 Structure Analyzer Service Design

> **Service**: `structure-analyzer`
> **Purpose**: Detect swings, BOS, CHoCH, Fibonacci levels
> **Independence**: Depends only on candle data (from data-feed)

---

## 🎯 Responsibilities

1. Detect swing highs and swing lows
2. Track market structure (BOS, CHoCH)
3. Calculate Fibonacci retracements with OTE zone
4. Maintain structure state across multiple timeframes
5. Emit events on structure changes

---

## 📐 API Contract

### REST Endpoints

```yaml
GET /api/v1/swings/{symbol}:
  parameters:
    symbol: string (required)
    timeframe: string (default: "15m")
    lookback_candles: int (default: 100)
    swing_strength: int (default: 3)  # Candles on each side
  response:
    symbol: "NIFTY 50"
    timeframe: "15m"
    swings:
      - type: "HIGH"
        level: 22480.50
        timestamp: "2025-01-31T10:30:00+05:30"
        strength: 3
        broken: false
      - type: "LOW"
        level: 22350.00
        timestamp: "2025-01-31T09:45:00+05:30"
        strength: 3
        broken: true
        broken_at: "2025-01-31T11:00:00+05:30"

GET /api/v1/structure/{symbol}:
  parameters:
    symbol: string (required)
    timeframe: string (default: "15m")
  response:
    symbol: "NIFTY 50"
    timeframe: "15m"
    current_trend: "BULLISH"
    last_bos:
      type: "BULLISH"
      level: 22420.00
      timestamp: "2025-01-31T11:15:00+05:30"
    last_choch: null
    swing_highs:
      - level: 22480.50
        timestamp: "2025-01-31T10:30:00+05:30"
    swing_lows:
      - level: 22350.00
        timestamp: "2025-01-31T09:45:00+05:30"

GET /api/v1/fibonacci/{symbol}:
  parameters:
    symbol: string (required)
    timeframe: string (default: "15m")
    swing_high: float (optional)  # Auto-detect if not provided
    swing_low: float (optional)
  response:
    symbol: "NIFTY 50"
    timeframe: "15m"
    direction: "BULLISH"  # Measuring from low to high
    swing_high: 22480.50
    swing_low: 22350.00
    range: 130.50
    levels:
      - name: "0%"
        ratio: 0.0
        price: 22480.50
        is_ote: false
      - name: "23.6%"
        ratio: 0.236
        price: 22449.70
        is_ote: false
      - name: "38.2%"
        ratio: 0.382
        price: 22430.63
        is_ote: false
      - name: "50%"
        ratio: 0.5
        price: 22415.25
        is_ote: false
      - name: "61.8%"
        ratio: 0.618
        price: 22399.87  # OTE START
        is_ote: true
      - name: "70.5%"
        ratio: 0.705
        price: 22388.50  # OTE SWEET SPOT
        is_ote: true
      - name: "79%"
        ratio: 0.79
        price: 22377.41  # OTE END
        is_ote: true
      - name: "88.6%"
        ratio: 0.886
        price: 22364.87
        is_ote: false
      - name: "100%"
        ratio: 1.0
        price: 22350.00
        is_ote: false
    ote_zone:
      high: 22399.87
      low: 22377.41
      sweet_spot: 22388.50
    current_price_in_ote: true
    price_position: "IN_OTE"  # ABOVE_OTE, IN_OTE, BELOW_OTE

POST /api/v1/analyze:
  description: Trigger full structure analysis
  body:
    symbol: "NIFTY 50"
    candles: [...]  # Array of candle objects
  response:
    swings: [...]
    structure: {...}
    fibonacci: {...}
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  STRUCTURE-ANALYZER SERVICE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    API LAYER (FastAPI)                       ││
│  │  /swings/{symbol}  /structure/{symbol}  /fibonacci/{symbol} ││
│  └───────────────────────────┬─────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │                  STRUCTURE MANAGER                           ││
│  │                                                              ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       ││
│  │  │ Swing        │  │ Structure    │  │ Fibonacci    │       ││
│  │  │ Detector     │  │ Tracker      │  │ Calculator   │       ││
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       ││
│  │         │                 │                 │                ││
│  │         └─────────────────┴─────────────────┘                ││
│  │                           │                                   ││
│  │  ┌───────────────────────────────────────────────────────┐  ││
│  │  │              STRUCTURE STATE STORE                     │  ││
│  │  │  Per-symbol, per-timeframe state                      │  ││
│  │  └───────────────────────────────────────────────────────┘  ││
│  │                                                              ││
│  └──────────────────────────────────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │                    EVENT LISTENER                            ││
│  │  Subscribes to: data.candle.new, data.candle.closed          ││
│  └──────────────────────────────────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │                    EVENT EMITTER                             ││
│  │  Publishes: structure.swing.new, structure.bos.detected     ││
│  │             structure.choch.detected, structure.fib.updated  ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Models

```python
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal, List
from enum import Enum

class SwingType(Enum):
    HIGH = "HIGH"
    LOW = "LOW"

class TrendDirection(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    RANGING = "RANGING"

class StructureEventType(Enum):
    BOS = "BOS"      # Break of Structure
    CHOCH = "CHOCH"  # Change of Character

@dataclass
class SwingPoint:
    """A swing high or swing low"""
    type: SwingType
    level: Decimal
    timestamp: datetime
    candle_index: int
    strength: int  # Number of candles on each side confirming the swing
    
    # State tracking
    broken: bool = False
    broken_at: Optional[datetime] = None
    broken_by_candle_index: Optional[int] = None
    
    def __hash__(self):
        return hash((self.type, self.level, self.timestamp))

@dataclass
class StructureEvent:
    """BOS or CHoCH event"""
    type: StructureEventType
    direction: TrendDirection  # Direction AFTER the event
    broken_level: Decimal
    broken_swing: SwingPoint
    confirmation_candle_index: int
    timestamp: datetime
    
@dataclass
class FibonacciLevel:
    """Single Fibonacci level"""
    name: str           # "61.8%", "70.5%", etc.
    ratio: Decimal      # 0.618, 0.705, etc.
    price: Decimal      # Actual price level
    is_ote: bool        # Part of Optimal Trade Entry zone
    
@dataclass
class FibonacciRetracement:
    """Complete Fibonacci retracement analysis"""
    direction: TrendDirection  # BULLISH = measuring from low to high
    swing_high: SwingPoint
    swing_low: SwingPoint
    range: Decimal
    levels: List[FibonacciLevel]
    
    # OTE Zone (61.8% - 79%)
    ote_high: Decimal
    ote_low: Decimal
    ote_sweet_spot: Decimal  # 70.5%
    
    def is_price_in_ote(self, price: Decimal) -> bool:
        """Check if price is in the OTE zone"""
        return self.ote_low <= price <= self.ote_high
    
    def get_price_position(self, price: Decimal) -> str:
        """Get price position relative to OTE"""
        if price > self.ote_high:
            return "ABOVE_OTE"
        elif price < self.ote_low:
            return "BELOW_OTE"
        else:
            return "IN_OTE"

@dataclass
class StructureState:
    """Current structure state for a symbol/timeframe"""
    symbol: str
    timeframe: str
    
    # Current trend
    trend: TrendDirection
    trend_established_at: datetime
    
    # Swing points (most recent first)
    swing_highs: List[SwingPoint] = field(default_factory=list)
    swing_lows: List[SwingPoint] = field(default_factory=list)
    
    # Structure events
    last_bos: Optional[StructureEvent] = None
    last_choch: Optional[StructureEvent] = None
    
    # Fibonacci (calculated from most recent swings)
    fibonacci: Optional[FibonacciRetracement] = None
    
    # Key levels
    current_higher_high: Optional[SwingPoint] = None
    current_higher_low: Optional[SwingPoint] = None
    current_lower_high: Optional[SwingPoint] = None
    current_lower_low: Optional[SwingPoint] = None
```

---

## 🔧 Implementation

### SwingDetector

```python
from typing import List, Optional
from decimal import Decimal

class SwingDetector:
    """
    Detect swing highs and lows using configurable lookback.
    
    A swing high is confirmed when N candles on left AND right have lower highs.
    A swing low is confirmed when N candles on left AND right have higher lows.
    """
    
    def __init__(self, strength: int = 3):
        """
        Args:
            strength: Number of candles required on each side (default: 3)
        """
        self.strength = strength
    
    def detect_swings(self, candles: List[Candle]) -> List[SwingPoint]:
        """Detect all swing points in candle series"""
        swings = []
        
        # Need at least strength * 2 + 1 candles
        if len(candles) < self.strength * 2 + 1:
            return swings
        
        for i in range(self.strength, len(candles) - self.strength):
            # Check for swing high
            if self._is_swing_high(candles, i):
                swings.append(SwingPoint(
                    type=SwingType.HIGH,
                    level=candles[i].high,
                    timestamp=candles[i].timestamp,
                    candle_index=i,
                    strength=self.strength
                ))
            
            # Check for swing low
            if self._is_swing_low(candles, i):
                swings.append(SwingPoint(
                    type=SwingType.LOW,
                    level=candles[i].low,
                    timestamp=candles[i].timestamp,
                    candle_index=i,
                    strength=self.strength
                ))
        
        return sorted(swings, key=lambda s: s.timestamp)
    
    def _is_swing_high(self, candles: List[Candle], index: int) -> bool:
        """Check if candle at index is a swing high"""
        current_high = candles[index].high
        
        # Check left side
        for i in range(1, self.strength + 1):
            if candles[index - i].high >= current_high:
                return False
        
        # Check right side
        for i in range(1, self.strength + 1):
            if candles[index + i].high >= current_high:
                return False
        
        return True
    
    def _is_swing_low(self, candles: List[Candle], index: int) -> bool:
        """Check if candle at index is a swing low"""
        current_low = candles[index].low
        
        # Check left side
        for i in range(1, self.strength + 1):
            if candles[index - i].low <= current_low:
                return False
        
        # Check right side
        for i in range(1, self.strength + 1):
            if candles[index + i].low <= current_low:
                return False
        
        return True
    
    def update_swing_breaks(
        self, swings: List[SwingPoint], candles: List[Candle]
    ) -> List[SwingPoint]:
        """Update broken status for all swings"""
        for swing in swings:
            if swing.broken:
                continue
            
            # Check candles after the swing
            for i in range(swing.candle_index + 1, len(candles)):
                candle = candles[i]
                
                if swing.type == SwingType.HIGH:
                    # Swing high broken if any candle closes above
                    if candle.close > swing.level:
                        swing.broken = True
                        swing.broken_at = candle.timestamp
                        swing.broken_by_candle_index = i
                        break
                else:
                    # Swing low broken if any candle closes below
                    if candle.close < swing.level:
                        swing.broken = True
                        swing.broken_at = candle.timestamp
                        swing.broken_by_candle_index = i
                        break
        
        return swings
```

### StructureTracker

```python
class StructureTracker:
    """
    Track market structure: trend, BOS, CHoCH.
    
    Rules:
    - BOS: Price closes beyond swing IN DIRECTION of trend
    - CHoCH: Price closes beyond swing AGAINST direction of trend
    """
    
    def __init__(self):
        self.states: Dict[str, StructureState] = {}
    
    def get_state(self, symbol: str, timeframe: str) -> StructureState:
        """Get or create structure state for symbol/timeframe"""
        key = f"{symbol}:{timeframe}"
        if key not in self.states:
            self.states[key] = StructureState(
                symbol=symbol,
                timeframe=timeframe,
                trend=TrendDirection.RANGING,
                trend_established_at=datetime.now()
            )
        return self.states[key]
    
    def analyze_structure(
        self, 
        candles: List[Candle], 
        swings: List[SwingPoint],
        symbol: str,
        timeframe: str
    ) -> Tuple[StructureState, List[StructureEvent]]:
        """
        Analyze market structure and detect BOS/CHoCH.
        
        Returns updated state and list of new structure events.
        """
        state = self.get_state(symbol, timeframe)
        events = []
        
        # Separate highs and lows
        highs = [s for s in swings if s.type == SwingType.HIGH]
        lows = [s for s in swings if s.type == SwingType.LOW]
        
        state.swing_highs = sorted(highs, key=lambda s: s.timestamp, reverse=True)
        state.swing_lows = sorted(lows, key=lambda s: s.timestamp, reverse=True)
        
        if len(highs) < 2 or len(lows) < 2:
            return state, events
        
        # Determine current trend based on swing sequence
        state.trend = self._determine_trend(highs, lows)
        
        # Check for structure breaks in recent candles
        recent_candles = candles[-20:]  # Last 20 candles
        
        for candle in recent_candles:
            event = self._check_structure_break(candle, state)
            if event:
                events.append(event)
                
                # Update state based on event
                if event.type == StructureEventType.BOS:
                    state.last_bos = event
                elif event.type == StructureEventType.CHOCH:
                    state.last_choch = event
                    state.trend = event.direction
                    state.trend_established_at = event.timestamp
        
        # Update Fibonacci
        state.fibonacci = self._calculate_fibonacci(state)
        
        return state, events
    
    def _determine_trend(
        self, highs: List[SwingPoint], lows: List[SwingPoint]
    ) -> TrendDirection:
        """
        Determine trend from swing sequence.
        
        Bullish: Higher Highs + Higher Lows
        Bearish: Lower Highs + Lower Lows
        Ranging: Mixed pattern
        """
        if len(highs) < 2 or len(lows) < 2:
            return TrendDirection.RANGING
        
        # Compare most recent swings
        hh = highs[0].level > highs[1].level  # Higher High
        hl = lows[0].level > lows[1].level    # Higher Low
        lh = highs[0].level < highs[1].level  # Lower High
        ll = lows[0].level < lows[1].level    # Lower Low
        
        if hh and hl:
            return TrendDirection.BULLISH
        elif lh and ll:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.RANGING
    
    def _check_structure_break(
        self, candle: Candle, state: StructureState
    ) -> Optional[StructureEvent]:
        """Check if candle breaks structure"""
        
        if state.trend == TrendDirection.BULLISH:
            # In bullish trend, look for:
            # - BOS: Close above previous swing HIGH (continuation)
            # - CHoCH: Close below previous swing LOW (reversal)
            
            # Check for BOS (break swing high)
            for swing in state.swing_highs[1:]:  # Skip most recent
                if not swing.broken and candle.close > swing.level:
                    return StructureEvent(
                        type=StructureEventType.BOS,
                        direction=TrendDirection.BULLISH,
                        broken_level=swing.level,
                        broken_swing=swing,
                        confirmation_candle_index=-1,
                        timestamp=candle.timestamp
                    )
            
            # Check for CHoCH (break swing low)
            for swing in state.swing_lows:
                if not swing.broken and candle.close < swing.level:
                    return StructureEvent(
                        type=StructureEventType.CHOCH,
                        direction=TrendDirection.BEARISH,  # Shift to bearish
                        broken_level=swing.level,
                        broken_swing=swing,
                        confirmation_candle_index=-1,
                        timestamp=candle.timestamp
                    )
        
        elif state.trend == TrendDirection.BEARISH:
            # In bearish trend, look for:
            # - BOS: Close below previous swing LOW (continuation)
            # - CHoCH: Close above previous swing HIGH (reversal)
            
            # Check for BOS (break swing low)
            for swing in state.swing_lows[1:]:
                if not swing.broken and candle.close < swing.level:
                    return StructureEvent(
                        type=StructureEventType.BOS,
                        direction=TrendDirection.BEARISH,
                        broken_level=swing.level,
                        broken_swing=swing,
                        confirmation_candle_index=-1,
                        timestamp=candle.timestamp
                    )
            
            # Check for CHoCH (break swing high)
            for swing in state.swing_highs:
                if not swing.broken and candle.close > swing.level:
                    return StructureEvent(
                        type=StructureEventType.CHOCH,
                        direction=TrendDirection.BULLISH,  # Shift to bullish
                        broken_level=swing.level,
                        broken_swing=swing,
                        confirmation_candle_index=-1,
                        timestamp=candle.timestamp
                    )
        
        return None
    
    def _calculate_fibonacci(self, state: StructureState) -> Optional[FibonacciRetracement]:
        """Calculate Fibonacci from most recent valid swing pair"""
        if not state.swing_highs or not state.swing_lows:
            return None
        
        # Get most recent unbroken swing high and low
        swing_high = state.swing_highs[0]
        swing_low = state.swing_lows[0]
        
        return FibonacciCalculator(
            swing_high=swing_high,
            swing_low=swing_low,
            direction=state.trend
        ).calculate()
```

### FibonacciCalculator

```python
class FibonacciCalculator:
    """
    Calculate precise Fibonacci retracement levels.
    
    Special focus on OTE zone (61.8% - 79%) for ICT methodology.
    """
    
    # Standard Fibonacci ratios
    LEVELS = [
        ("0%", Decimal("0")),
        ("23.6%", Decimal("0.236")),
        ("38.2%", Decimal("0.382")),
        ("50%", Decimal("0.5")),
        ("61.8%", Decimal("0.618")),    # OTE Start
        ("70.5%", Decimal("0.705")),    # OTE Sweet Spot (ICT)
        ("79%", Decimal("0.79")),        # OTE End
        ("88.6%", Decimal("0.886")),
        ("100%", Decimal("1.0")),
    ]
    
    # Extension levels
    EXTENSIONS = [
        ("-27.2%", Decimal("1.272")),
        ("-61.8%", Decimal("1.618")),
        ("-100%", Decimal("2.0")),
    ]
    
    def __init__(
        self, 
        swing_high: SwingPoint, 
        swing_low: SwingPoint,
        direction: TrendDirection
    ):
        self.swing_high = swing_high
        self.swing_low = swing_low
        self.direction = direction
        self.range = swing_high.level - swing_low.level
    
    def calculate(self) -> FibonacciRetracement:
        """Calculate all Fibonacci levels"""
        levels = []
        
        for name, ratio in self.LEVELS:
            if self.direction == TrendDirection.BULLISH:
                # Bullish: measuring retracement from high DOWN
                # 0% = swing high, 100% = swing low
                price = self.swing_high.level - (self.range * ratio)
            else:
                # Bearish: measuring retracement from low UP
                # 0% = swing low, 100% = swing high
                price = self.swing_low.level + (self.range * ratio)
            
            is_ote = ratio >= Decimal("0.618") and ratio <= Decimal("0.79")
            
            levels.append(FibonacciLevel(
                name=name,
                ratio=ratio,
                price=price.quantize(Decimal("0.05")),  # NSE tick size
                is_ote=is_ote
            ))
        
        # Calculate OTE zone
        ote_levels = [l for l in levels if l.is_ote]
        ote_prices = [l.price for l in ote_levels]
        
        return FibonacciRetracement(
            direction=self.direction,
            swing_high=self.swing_high,
            swing_low=self.swing_low,
            range=self.range,
            levels=levels,
            ote_high=max(ote_prices),
            ote_low=min(ote_prices),
            ote_sweet_spot=next(l.price for l in levels if l.name == "70.5%")
        )
    
    def calculate_extensions(self) -> List[FibonacciLevel]:
        """Calculate extension levels (for take profit)"""
        extensions = []
        
        for name, ratio in self.EXTENSIONS:
            if self.direction == TrendDirection.BULLISH:
                # Extension above swing high
                price = self.swing_low.level + (self.range * ratio)
            else:
                # Extension below swing low
                price = self.swing_high.level - (self.range * ratio)
            
            extensions.append(FibonacciLevel(
                name=name,
                ratio=ratio,
                price=price.quantize(Decimal("0.05")),
                is_ote=False
            ))
        
        return extensions
```

---

## 📤 Events Published

```python
# Published when new swing detected
@dataclass
class SwingEvent:
    event_type: str = "structure.swing.new"
    symbol: str
    timeframe: str
    swing: SwingPoint
    timestamp: datetime = field(default_factory=datetime.now)

# Published on Break of Structure
@dataclass
class BOSEvent:
    event_type: str = "structure.bos.detected"
    symbol: str
    timeframe: str
    direction: str  # BULLISH or BEARISH
    broken_level: Decimal
    timestamp: datetime = field(default_factory=datetime.now)

# Published on Change of Character
@dataclass
class CHoCHEvent:
    event_type: str = "structure.choch.detected"
    symbol: str
    timeframe: str
    new_direction: str  # Direction AFTER the choch
    broken_level: Decimal
    timestamp: datetime = field(default_factory=datetime.now)

# Published when Fibonacci levels updated
@dataclass
class FibonacciEvent:
    event_type: str = "structure.fib.updated"
    symbol: str
    timeframe: str
    ote_zone: Dict[str, Decimal]  # {high, low, sweet_spot}
    current_price_in_ote: bool
    timestamp: datetime = field(default_factory=datetime.now)
```

---

## ⚠️ Error Handling

```python
class StructureError(Exception):
    """Base error for structure analyzer"""
    
    INSUFFICIENT_DATA = "STRUCT_001"
    INVALID_CANDLES = "STRUCT_002"
    CALCULATION_ERROR = "STRUCT_003"
    STATE_CORRUPTION = "STRUCT_004"
```

---

## 🧪 Testing

```python
class TestSwingDetector:
    def test_detect_swing_high(self):
        """Test swing high detection"""
        # Create candles with clear swing high
        candles = [
            make_candle(high=100),
            make_candle(high=102),
            make_candle(high=105),  # This should be swing high
            make_candle(high=103),
            make_candle(high=101),
        ]
        
        detector = SwingDetector(strength=2)
        swings = detector.detect_swings(candles)
        
        assert len(swings) == 1
        assert swings[0].type == SwingType.HIGH
        assert swings[0].level == Decimal("105")
    
    def test_fibonacci_ote_zone(self):
        """Test OTE zone calculation"""
        calc = FibonacciCalculator(
            swing_high=SwingPoint(SwingType.HIGH, Decimal("22500"), datetime.now(), 0, 3),
            swing_low=SwingPoint(SwingType.LOW, Decimal("22000"), datetime.now(), 0, 3),
            direction=TrendDirection.BULLISH
        )
        
        fib = calc.calculate()
        
        # OTE should be 61.8% to 79% of the range
        # Range = 500
        # 61.8% = 22500 - 500*0.618 = 22191
        # 79% = 22500 - 500*0.79 = 22105
        assert fib.ote_high == Decimal("22191.00") or fib.ote_high == Decimal("22191")
        assert fib.is_price_in_ote(Decimal("22150"))
        assert not fib.is_price_in_ote(Decimal("22300"))

class TestStructureTracker:
    def test_detect_bullish_bos(self):
        """Test BOS detection in bullish trend"""
        # Setup bullish structure
        state = StructureState(
            symbol="NIFTY",
            timeframe="15m",
            trend=TrendDirection.BULLISH,
            trend_established_at=datetime.now(),
            swing_highs=[
                SwingPoint(SwingType.HIGH, Decimal("22500"), datetime.now(), 10, 3),
                SwingPoint(SwingType.HIGH, Decimal("22400"), datetime.now(), 5, 3),
            ],
            swing_lows=[]
        )
        
        # Candle that breaks the lower swing high
        candle = Candle(
            symbol="NIFTY",
            timeframe=Timeframe.M15,
            timestamp=datetime.now(),
            open=Decimal("22380"),
            high=Decimal("22420"),
            low=Decimal("22370"),
            close=Decimal("22410"),  # Closes above 22400
        )
        
        tracker = StructureTracker()
        event = tracker._check_structure_break(candle, state)
        
        assert event is not None
        assert event.type == StructureEventType.BOS
        assert event.direction == TrendDirection.BULLISH
```

---

## ✅ Acceptance Criteria

- [ ] Accurately detects swing highs and lows
- [ ] Configurable swing strength (N candles confirmation)
- [ ] Correctly identifies BOS events
- [ ] Correctly identifies CHoCH events (trend reversals)
- [ ] Calculates Fibonacci levels with precision
- [ ] OTE zone clearly defined (61.8% - 79%)
- [ ] Sweet spot calculated at 70.5%
- [ ] Maintains state across updates
- [ ] Publishes events on structure changes
- [ ] Uses Decimal for all price calculations
- [ ] Comprehensive test coverage
