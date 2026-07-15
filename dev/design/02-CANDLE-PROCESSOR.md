# 🕯️ Candle Processor Service Design

> **Service**: `candle-processor`
> **Purpose**: Normalize, validate, and aggregate candles across timeframes
> **Independence**: Takes raw candles, outputs processed candles

---

## 🎯 Responsibilities

1. Validate OHLC relationships
2. Normalize timestamps to candle boundaries
3. Aggregate lower timeframe to higher timeframe
4. Calculate candle metrics (body, wicks, ATR)
5. Detect candle patterns (engulfing, doji, etc.)
6. Emit processed candle events

---

## 📐 API Contract

```yaml
POST /api/v1/process:
  description: Process raw candles
  body:
    candles: [...]  # Raw OHLC data
    source_timeframe: "1m"
  response:
    processed_candles: [...]
    validation_errors: []
    metrics:
      atr_14: 45.50
      avg_body: 12.30
      avg_range: 25.60

GET /api/v1/aggregate/{symbol}:
  parameters:
    symbol: string
    source_timeframe: "1m"
    target_timeframe: "15m"
    from_date: datetime
    to_date: datetime
  response:
    aggregated_candles: [...]
    source_count: 450
    target_count: 30

GET /api/v1/patterns/{symbol}:
  parameters:
    symbol: string
    timeframe: "15m"
    lookback: 50
  response:
    patterns:
      - type: "BULLISH_ENGULFING"
        candle_index: 45
        timestamp: "2025-01-31T11:30:00+05:30"
        quality: 0.85
      - type: "DOJI"
        candle_index: 48
        timestamp: "2025-01-31T12:15:00+05:30"
        quality: 0.72
```

---

## 📊 Data Models

```python
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import List, Optional
from enum import Enum

class CandlePattern(Enum):
    # Bullish patterns
    BULLISH_ENGULFING = "BULLISH_ENGULFING"
    HAMMER = "HAMMER"
    MORNING_STAR = "MORNING_STAR"
    BULLISH_MARUBOZU = "BULLISH_MARUBOZU"
    
    # Bearish patterns
    BEARISH_ENGULFING = "BEARISH_ENGULFING"
    SHOOTING_STAR = "SHOOTING_STAR"
    EVENING_STAR = "EVENING_STAR"
    BEARISH_MARUBOZU = "BEARISH_MARUBOZU"
    
    # Indecision
    DOJI = "DOJI"
    SPINNING_TOP = "SPINNING_TOP"
    INSIDE_BAR = "INSIDE_BAR"

@dataclass
class ProcessedCandle:
    """Candle with computed metrics"""
    # Base OHLC
    symbol: str
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    
    # Computed metrics
    body: Decimal          # |close - open|
    upper_wick: Decimal    # high - max(open, close)
    lower_wick: Decimal    # min(open, close) - low
    range: Decimal         # high - low
    body_percent: Decimal  # body / range * 100
    
    # Classification
    is_bullish: bool
    is_bearish: bool
    is_doji: bool          # body < 10% of range
    
    # Patterns detected on this candle
    patterns: List[CandlePattern] = None

@dataclass
class CandleMetrics:
    """Aggregate metrics over candle series"""
    symbol: str
    timeframe: str
    period: int  # Number of candles
    
    # ATR (Average True Range)
    atr: Decimal
    
    # Averages
    avg_body: Decimal
    avg_range: Decimal
    avg_volume: int
    
    # Volatility
    range_std_dev: Decimal
    
    # Trend metrics
    bullish_candle_percent: Decimal
    bearish_candle_percent: Decimal

@dataclass
class PatternDetection:
    """Detected candle pattern"""
    pattern: CandlePattern
    candle_index: int
    timestamp: datetime
    quality: float  # 0-1
    candles_involved: List[int]  # Indices of candles forming pattern
```

---

## 🔧 Implementation

### CandleValidator

```python
class CandleValidator:
    """Validate OHLC data integrity"""
    
    def validate(self, candle: dict) -> Tuple[bool, List[str]]:
        errors = []
        
        o, h, l, c = candle['open'], candle['high'], candle['low'], candle['close']
        
        # Rule 1: High must be highest
        if h < o or h < c:
            errors.append(f"High {h} is not highest (O:{o}, C:{c})")
        
        # Rule 2: Low must be lowest
        if l > o or l > c:
            errors.append(f"Low {l} is not lowest (O:{o}, C:{c})")
        
        # Rule 3: High >= Low
        if h < l:
            errors.append(f"High {h} < Low {l}")
        
        # Rule 4: All values positive
        if any(v <= 0 for v in [o, h, l, c]):
            errors.append("OHLC values must be positive")
        
        return len(errors) == 0, errors
```

### TimeframeAggregator

```python
class TimeframeAggregator:
    """Aggregate candles from lower to higher timeframe"""
    
    TIMEFRAME_MINUTES = {
        "1m": 1, "5m": 5, "15m": 15, "30m": 30,
        "1h": 60, "4h": 240, "1d": 1440
    }
    
    def aggregate(
        self, 
        candles: List[Candle], 
        source_tf: str, 
        target_tf: str
    ) -> List[Candle]:
        source_mins = self.TIMEFRAME_MINUTES[source_tf]
        target_mins = self.TIMEFRAME_MINUTES[target_tf]
        
        if target_mins <= source_mins:
            raise ValueError("Target timeframe must be larger than source")
        
        ratio = target_mins // source_mins
        aggregated = []
        
        # Group candles by target timeframe boundary
        groups = self._group_by_boundary(candles, target_mins)
        
        for boundary_time, group in groups.items():
            if len(group) == 0:
                continue
            
            agg_candle = Candle(
                symbol=group[0].symbol,
                timeframe=target_tf,
                timestamp=boundary_time,
                open=group[0].open,
                high=max(c.high for c in group),
                low=min(c.low for c in group),
                close=group[-1].close,
                volume=sum(c.volume for c in group),
                is_closed=group[-1].is_closed
            )
            aggregated.append(agg_candle)
        
        return aggregated
    
    def _group_by_boundary(self, candles, target_mins):
        """Group candles by their target timeframe boundary"""
        groups = defaultdict(list)
        
        for candle in candles:
            # Round down to nearest boundary
            boundary = self._get_boundary(candle.timestamp, target_mins)
            groups[boundary].append(candle)
        
        return dict(sorted(groups.items()))
    
    def _get_boundary(self, ts: datetime, interval_mins: int) -> datetime:
        """Get the start of the timeframe containing this timestamp"""
        total_mins = ts.hour * 60 + ts.minute
        boundary_mins = (total_mins // interval_mins) * interval_mins
        
        return ts.replace(
            hour=boundary_mins // 60,
            minute=boundary_mins % 60,
            second=0,
            microsecond=0
        )
```

### PatternDetector

```python
class PatternDetector:
    """Detect candlestick patterns"""
    
    def detect_all(self, candles: List[ProcessedCandle]) -> List[PatternDetection]:
        patterns = []
        
        for i in range(len(candles)):
            # Single candle patterns
            patterns.extend(self._detect_single(candles, i))
            
            # Two candle patterns
            if i >= 1:
                patterns.extend(self._detect_double(candles, i))
            
            # Three candle patterns
            if i >= 2:
                patterns.extend(self._detect_triple(candles, i))
        
        return patterns
    
    def _detect_single(self, candles, i) -> List[PatternDetection]:
        patterns = []
        c = candles[i]
        
        # Doji: body < 10% of range
        if c.range > 0 and c.body_percent < Decimal("10"):
            patterns.append(PatternDetection(
                pattern=CandlePattern.DOJI,
                candle_index=i,
                timestamp=c.timestamp,
                quality=1 - float(c.body_percent / 10),
                candles_involved=[i]
            ))
        
        # Hammer: small body at top, long lower wick (2x body)
        if c.is_bullish and c.lower_wick >= c.body * 2 and c.upper_wick < c.body:
            patterns.append(PatternDetection(
                pattern=CandlePattern.HAMMER,
                candle_index=i,
                timestamp=c.timestamp,
                quality=min(1.0, float(c.lower_wick / c.body) / 3),
                candles_involved=[i]
            ))
        
        # Shooting Star: small body at bottom, long upper wick
        if c.is_bearish and c.upper_wick >= c.body * 2 and c.lower_wick < c.body:
            patterns.append(PatternDetection(
                pattern=CandlePattern.SHOOTING_STAR,
                candle_index=i,
                timestamp=c.timestamp,
                quality=min(1.0, float(c.upper_wick / c.body) / 3),
                candles_involved=[i]
            ))
        
        return patterns
    
    def _detect_double(self, candles, i) -> List[PatternDetection]:
        patterns = []
        prev, curr = candles[i-1], candles[i]
        
        # Bullish Engulfing: bearish → bullish that engulfs
        if prev.is_bearish and curr.is_bullish:
            if curr.open <= prev.close and curr.close >= prev.open:
                quality = float(curr.body / prev.body) / 2 if prev.body > 0 else 0.5
                patterns.append(PatternDetection(
                    pattern=CandlePattern.BULLISH_ENGULFING,
                    candle_index=i,
                    timestamp=curr.timestamp,
                    quality=min(1.0, quality),
                    candles_involved=[i-1, i]
                ))
        
        # Bearish Engulfing: bullish → bearish that engulfs
        if prev.is_bullish and curr.is_bearish:
            if curr.open >= prev.close and curr.close <= prev.open:
                quality = float(curr.body / prev.body) / 2 if prev.body > 0 else 0.5
                patterns.append(PatternDetection(
                    pattern=CandlePattern.BEARISH_ENGULFING,
                    candle_index=i,
                    timestamp=curr.timestamp,
                    quality=min(1.0, quality),
                    candles_involved=[i-1, i]
                ))
        
        # Inside Bar: current candle entirely within previous
        if curr.high <= prev.high and curr.low >= prev.low:
            patterns.append(PatternDetection(
                pattern=CandlePattern.INSIDE_BAR,
                candle_index=i,
                timestamp=curr.timestamp,
                quality=0.7,
                candles_involved=[i-1, i]
            ))
        
        return patterns
    
    def _detect_triple(self, candles, i) -> List[PatternDetection]:
        patterns = []
        c1, c2, c3 = candles[i-2], candles[i-1], candles[i]
        
        # Morning Star: bearish, small/doji, bullish
        if c1.is_bearish and c2.is_doji and c3.is_bullish:
            if c3.close > (c1.open + c1.close) / 2:
                patterns.append(PatternDetection(
                    pattern=CandlePattern.MORNING_STAR,
                    candle_index=i,
                    timestamp=c3.timestamp,
                    quality=0.8,
                    candles_involved=[i-2, i-1, i]
                ))
        
        # Evening Star: bullish, small/doji, bearish
        if c1.is_bullish and c2.is_doji and c3.is_bearish:
            if c3.close < (c1.open + c1.close) / 2:
                patterns.append(PatternDetection(
                    pattern=CandlePattern.EVENING_STAR,
                    candle_index=i,
                    timestamp=c3.timestamp,
                    quality=0.8,
                    candles_involved=[i-2, i-1, i]
                ))
        
        return patterns
```

### ATRCalculator

```python
class ATRCalculator:
    """Calculate Average True Range"""
    
    def calculate(self, candles: List[Candle], period: int = 14) -> Decimal:
        if len(candles) < period + 1:
            raise ValueError(f"Need at least {period + 1} candles for ATR")
        
        true_ranges = []
        
        for i in range(1, len(candles)):
            prev_close = candles[i-1].close
            curr = candles[i]
            
            # True Range = max of:
            # 1. Current High - Current Low
            # 2. |Current High - Previous Close|
            # 3. |Current Low - Previous Close|
            tr = max(
                curr.high - curr.low,
                abs(curr.high - prev_close),
                abs(curr.low - prev_close)
            )
            true_ranges.append(tr)
        
        # ATR = SMA of True Ranges
        recent_tr = true_ranges[-period:]
        atr = sum(recent_tr) / len(recent_tr)
        
        return Decimal(str(atr)).quantize(Decimal("0.01"))
```

---

## 📤 Events Published

```python
@dataclass
class CandleProcessedEvent:
    event_type: str = "candle.processed"
    symbol: str
    timeframe: str
    candle: ProcessedCandle
    metrics: CandleMetrics
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PatternDetectedEvent:
    event_type: str = "candle.pattern.detected"
    symbol: str
    timeframe: str
    pattern: PatternDetection
    timestamp: datetime = field(default_factory=datetime.now)
```

---

## ✅ Acceptance Criteria

- [ ] Validates all OHLC relationships
- [ ] Aggregates 1m → 5m → 15m → 1h → 4h → 1d
- [ ] Calculates ATR accurately
- [ ] Detects all standard candlestick patterns
- [ ] Computes candle metrics (body, wicks, percentages)
- [ ] All prices use Decimal
- [ ] Publishes events for downstream services
