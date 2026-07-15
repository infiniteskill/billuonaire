# 💧 Liquidity Mapper Service Design

> **Service**: `liquidity-mapper`
> **Purpose**: Map liquidity pools, key levels, and track sweeps
> **Independence**: Consumes swing data, produces liquidity map

---

## 🎯 Responsibilities

1. Identify equal highs/lows (EQH/EQL)
2. Track PDH/PDL, PWH/PWL, PMH/PML
3. Detect round number levels
4. Calculate liquidity strength scores
5. Track when pools are swept
6. Emit events on new pools and sweeps

---

## 📐 API Contract

```yaml
GET /api/v1/pools/{symbol}:
  parameters:
    symbol: string
    timeframe: string (default: "15m")
    include_swept: bool (default: false)
  response:
    symbol: "NIFTY 50"
    current_price: 22450.50
    pools:
      - type: "PDH"
        level: 22520.00
        strength: 0.95
        touch_count: 1
        last_touch: "2025-01-30T15:30:00+05:30"
        swept: false
        distance_percent: 0.31
        
      - type: "EQL"
        level: 22380.00
        strength: 0.82
        touch_count: 3
        last_touch: "2025-01-31T10:15:00+05:30"
        swept: false
        distance_percent: -0.31
        
      - type: "ROUND"
        level: 22500.00
        strength: 0.60
        touch_count: 0
        swept: false
        distance_percent: 0.22

GET /api/v1/key-levels/{symbol}:
  response:
    pdh: 22520.00
    pdl: 22340.00
    pwh: 22650.00
    pwl: 22180.00
    pmh: 22890.00
    pml: 21950.00
    round_numbers: [22000, 22500, 23000]
    asian_session_high: 22485.00
    asian_session_low: 22410.00

GET /api/v1/heat-map/{symbol}:
  description: Liquidity density at price levels
  response:
    levels:
      - price: 22520.00
        density: 0.95
        sources: ["PDH", "SWING_HIGH"]
      - price: 22500.00
        density: 0.75
        sources: ["ROUND", "EQH"]
      - price: 22380.00
        density: 0.82
        sources: ["EQL", "OB"]
```

---

## 📊 Data Models

```python
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, date
from typing import List, Optional, Dict
from enum import Enum

class LiquidityType(Enum):
    # Key daily/weekly/monthly levels
    PDH = "PDH"   # Previous Day High
    PDL = "PDL"   # Previous Day Low
    PWH = "PWH"   # Previous Week High
    PWL = "PWL"   # Previous Week Low
    PMH = "PMH"   # Previous Month High
    PML = "PML"   # Previous Month Low
    
    # Session levels
    ASIAN_HIGH = "ASIAN_HIGH"
    ASIAN_LOW = "ASIAN_LOW"
    LONDON_HIGH = "LONDON_HIGH"
    LONDON_LOW = "LONDON_LOW"
    
    # Equal levels
    EQH = "EQH"   # Equal Highs
    EQL = "EQL"   # Equal Lows
    
    # Swing points
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"
    
    # Technical
    ROUND = "ROUND"  # Round numbers (22000, 22500, etc.)
    GAP = "GAP"      # Gap levels

@dataclass
class LiquidityPool:
    """A single liquidity pool"""
    type: LiquidityType
    level: Decimal
    strength: float          # 0-1, how much liquidity likely there
    touch_count: int         # Times price touched this level
    last_touch: datetime
    formation_time: datetime
    
    # Sweep tracking
    swept: bool = False
    swept_at: Optional[datetime] = None
    sweep_candle_index: Optional[int] = None
    
    # Metadata
    source_swings: List[int] = field(default_factory=list)  # Swing indices
    notes: str = ""
    
    def distance_from(self, price: Decimal) -> Decimal:
        """Distance in points"""
        return self.level - price
    
    def distance_percent(self, price: Decimal) -> float:
        """Distance as percentage"""
        return float((self.level - price) / price * 100)

@dataclass
class KeyLevels:
    """Key levels for a symbol"""
    symbol: str
    as_of: datetime
    
    # Daily
    pdh: Optional[Decimal] = None
    pdl: Optional[Decimal] = None
    today_high: Optional[Decimal] = None
    today_low: Optional[Decimal] = None
    
    # Weekly
    pwh: Optional[Decimal] = None
    pwl: Optional[Decimal] = None
    
    # Monthly
    pmh: Optional[Decimal] = None
    pml: Optional[Decimal] = None
    
    # Session (Indian market)
    opening_range_high: Optional[Decimal] = None  # First 15-30 min
    opening_range_low: Optional[Decimal] = None
    
    # Round numbers near current price
    round_numbers: List[Decimal] = field(default_factory=list)

@dataclass
class LiquidityHeatMap:
    """Density map of liquidity at price levels"""
    symbol: str
    generated_at: datetime
    
    levels: List[Dict]  # [{price, density, sources}]
    
    def get_nearest_liquidity_above(self, price: Decimal) -> Optional[Dict]:
        """Find nearest liquidity pool above price"""
        above = [l for l in self.levels if l['price'] > price]
        return min(above, key=lambda x: x['price']) if above else None
    
    def get_nearest_liquidity_below(self, price: Decimal) -> Optional[Dict]:
        """Find nearest liquidity pool below price"""
        below = [l for l in self.levels if l['price'] < price]
        return max(below, key=lambda x: x['price']) if below else None
```

---

## 🔧 Implementation

### EqualLevelDetector

```python
class EqualLevelDetector:
    """Detect equal highs and equal lows"""
    
    def __init__(self, tolerance_percent: float = 0.001):
        """
        Args:
            tolerance_percent: Prices within this % are considered "equal"
                             0.001 = 0.1% = ~22 points at 22000
        """
        self.tolerance = tolerance_percent
    
    def find_equal_highs(self, swings: List[SwingPoint]) -> List[LiquidityPool]:
        """Find clusters of equal swing highs"""
        pools = []
        highs = [s for s in swings if s.type == SwingType.HIGH]
        
        # Group by price level
        groups = self._group_by_level(highs)
        
        for level, swing_group in groups.items():
            if len(swing_group) >= 2:  # Need at least 2 touches
                pools.append(LiquidityPool(
                    type=LiquidityType.EQH,
                    level=Decimal(str(level)),
                    strength=self._calculate_strength(swing_group),
                    touch_count=len(swing_group),
                    last_touch=max(s.timestamp for s in swing_group),
                    formation_time=min(s.timestamp for s in swing_group),
                    source_swings=[s.candle_index for s in swing_group]
                ))
        
        return pools
    
    def find_equal_lows(self, swings: List[SwingPoint]) -> List[LiquidityPool]:
        """Find clusters of equal swing lows"""
        pools = []
        lows = [s for s in swings if s.type == SwingType.LOW]
        
        groups = self._group_by_level(lows)
        
        for level, swing_group in groups.items():
            if len(swing_group) >= 2:
                pools.append(LiquidityPool(
                    type=LiquidityType.EQL,
                    level=Decimal(str(level)),
                    strength=self._calculate_strength(swing_group),
                    touch_count=len(swing_group),
                    last_touch=max(s.timestamp for s in swing_group),
                    formation_time=min(s.timestamp for s in swing_group),
                    source_swings=[s.candle_index for s in swing_group]
                ))
        
        return pools
    
    def _group_by_level(self, swings: List[SwingPoint]) -> Dict[float, List[SwingPoint]]:
        """Group swings by approximate level"""
        groups = defaultdict(list)
        
        for swing in swings:
            level = float(swing.level)
            # Find existing group within tolerance
            matched = False
            for existing_level in list(groups.keys()):
                if abs(level - existing_level) / existing_level < self.tolerance:
                    groups[existing_level].append(swing)
                    matched = True
                    break
            
            if not matched:
                groups[level].append(swing)
        
        return groups
    
    def _calculate_strength(self, swings: List[SwingPoint]) -> float:
        """Calculate liquidity strength based on touches and recency"""
        base_strength = min(len(swings) / 5, 1.0)  # More touches = stronger, max at 5
        
        # Recency bonus
        latest = max(s.timestamp for s in swings)
        age_hours = (datetime.now() - latest).total_seconds() / 3600
        recency_factor = max(0, 1 - age_hours / 48)  # Decay over 48 hours
        
        return min(1.0, base_strength * 0.7 + recency_factor * 0.3)
```

### KeyLevelCalculator

```python
class KeyLevelCalculator:
    """Calculate PDH/PDL, PWH/PWL, etc."""
    
    def calculate(self, candles: List[Candle], symbol: str) -> KeyLevels:
        """Calculate all key levels from candle data"""
        
        # Group candles by date
        by_date = self._group_by_date(candles)
        by_week = self._group_by_week(candles)
        by_month = self._group_by_month(candles)
        
        today = datetime.now().date()
        
        # PDH/PDL
        yesterday = today - timedelta(days=1)
        while yesterday not in by_date and yesterday > today - timedelta(days=7):
            yesterday -= timedelta(days=1)
        
        pdh = max(c.high for c in by_date[yesterday]) if yesterday in by_date else None
        pdl = min(c.low for c in by_date[yesterday]) if yesterday in by_date else None
        
        # PWH/PWL
        this_week = self._get_week_key(today)
        last_week = self._get_week_key(today - timedelta(days=7))
        
        pwh = max(c.high for c in by_week[last_week]) if last_week in by_week else None
        pwl = min(c.low for c in by_week[last_week]) if last_week in by_week else None
        
        # PMH/PML
        this_month = (today.year, today.month)
        last_month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
        
        pmh = max(c.high for c in by_month[last_month]) if last_month in by_month else None
        pml = min(c.low for c in by_month[last_month]) if last_month in by_month else None
        
        # Today's range
        today_candles = by_date.get(today, [])
        today_high = max(c.high for c in today_candles) if today_candles else None
        today_low = min(c.low for c in today_candles) if today_candles else None
        
        # Opening range (first 15 minutes)
        or_candles = [c for c in today_candles if c.timestamp.hour == 9 and c.timestamp.minute < 30]
        or_high = max(c.high for c in or_candles) if or_candles else None
        or_low = min(c.low for c in or_candles) if or_candles else None
        
        # Round numbers
        current_price = candles[-1].close if candles else Decimal("0")
        round_numbers = self._get_round_numbers(current_price)
        
        return KeyLevels(
            symbol=symbol,
            as_of=datetime.now(),
            pdh=pdh,
            pdl=pdl,
            today_high=today_high,
            today_low=today_low,
            pwh=pwh,
            pwl=pwl,
            pmh=pmh,
            pml=pml,
            opening_range_high=or_high,
            opening_range_low=or_low,
            round_numbers=round_numbers
        )
    
    def _get_round_numbers(self, price: Decimal, range_percent: float = 2.0) -> List[Decimal]:
        """Get round numbers within range of price"""
        rounds = []
        
        # Round to nearest 100
        base = int(price / 100) * 100
        for offset in range(-5, 6):
            level = base + offset * 100
            if abs(level - float(price)) / float(price) < range_percent / 100:
                rounds.append(Decimal(str(level)))
        
        # Add 500s if significant
        base_500 = int(price / 500) * 500
        for offset in range(-2, 3):
            level = base_500 + offset * 500
            if abs(level - float(price)) / float(price) < range_percent / 100:
                if Decimal(str(level)) not in rounds:
                    rounds.append(Decimal(str(level)))
        
        return sorted(rounds)
    
    def _group_by_date(self, candles):
        groups = defaultdict(list)
        for c in candles:
            groups[c.timestamp.date()].append(c)
        return groups
    
    def _group_by_week(self, candles):
        groups = defaultdict(list)
        for c in candles:
            groups[self._get_week_key(c.timestamp.date())].append(c)
        return groups
    
    def _get_week_key(self, d):
        return d.isocalendar()[:2]  # (year, week)
    
    def _group_by_month(self, candles):
        groups = defaultdict(list)
        for c in candles:
            groups[(c.timestamp.year, c.timestamp.month)].append(c)
        return groups
```

### SweepTracker

```python
class SweepTracker:
    """Track when liquidity pools are swept"""
    
    def check_sweep(self, pool: LiquidityPool, candle: Candle) -> Optional[Dict]:
        """Check if candle sweeps the pool"""
        
        if pool.swept:
            return None
        
        if pool.type in [LiquidityType.EQL, LiquidityType.PDL, LiquidityType.PWL, 
                         LiquidityType.PML, LiquidityType.SWING_LOW]:
            # Bullish sweep: wick below, close above
            if candle.low < pool.level:
                quality = self._calculate_sweep_quality(pool, candle, "BULLISH")
                
                return {
                    "type": "BULLISH_SWEEP",
                    "pool": pool,
                    "sweep_candle": candle,
                    "penetration": float(pool.level - candle.low),
                    "closed_above": candle.close > pool.level,
                    "quality": quality
                }
        
        elif pool.type in [LiquidityType.EQH, LiquidityType.PDH, LiquidityType.PWH,
                          LiquidityType.PMH, LiquidityType.SWING_HIGH]:
            # Bearish sweep: wick above, close below
            if candle.high > pool.level:
                quality = self._calculate_sweep_quality(pool, candle, "BEARISH")
                
                return {
                    "type": "BEARISH_SWEEP",
                    "pool": pool,
                    "sweep_candle": candle,
                    "penetration": float(candle.high - pool.level),
                    "closed_below": candle.close < pool.level,
                    "quality": quality
                }
        
        return None
    
    def _calculate_sweep_quality(self, pool: LiquidityPool, candle: Candle, direction: str) -> float:
        quality = 0.0
        
        # 1. Closed on correct side (+40%)
        if direction == "BULLISH" and candle.close > pool.level:
            quality += 0.4
        elif direction == "BEARISH" and candle.close < pool.level:
            quality += 0.4
        
        # 2. Pool was strong (+25%)
        quality += pool.strength * 0.25
        
        # 3. Multiple touches (+20%)
        if pool.touch_count >= 3:
            quality += 0.2
        elif pool.touch_count >= 2:
            quality += 0.1
        
        # 4. Key level type (+15%)
        if pool.type in [LiquidityType.PDH, LiquidityType.PDL, 
                         LiquidityType.PWH, LiquidityType.PWL]:
            quality += 0.15
        
        return min(1.0, quality)
```

---

## 📤 Events Published

```python
@dataclass
class LiquidityPoolEvent:
    event_type: str = "liquidity.pool.new"
    symbol: str
    pool: LiquidityPool
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class SweepEvent:
    event_type: str = "liquidity.sweep.detected"
    symbol: str
    sweep_type: str  # BULLISH_SWEEP or BEARISH_SWEEP
    level: Decimal
    quality: float
    pool_type: str
    timestamp: datetime = field(default_factory=datetime.now)
```

---

## ✅ Acceptance Criteria

- [ ] Correctly identifies equal highs/lows with tolerance
- [ ] Calculates PDH/PDL, PWH/PWL, PMH/PML
- [ ] Tracks today's high/low and opening range
- [ ] Identifies round number levels
- [ ] Calculates liquidity strength scores
- [ ] Detects sweeps with quality scoring
- [ ] Updates pool status when swept
- [ ] Generates liquidity heat map
- [ ] All prices use Decimal
- [ ] Publishes events for downstream
