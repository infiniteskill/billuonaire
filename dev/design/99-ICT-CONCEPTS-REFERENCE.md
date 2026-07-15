# 📊 ICT/SMC Concepts Complete Reference

> **Purpose**: Definitive reference for all manipulation concepts we're implementing
> **Critical**: Every concept here MUST be implemented with precision

---

## 🎯 CORE PHILOSOPHY

### The Market Truth

```
1. Price is DELIVERED, not discovered
2. Every move is DESIGNED to trap retail
3. Liquidity is the FUEL for price movement
4. Time windows matter (institutional activity)
5. Higher timeframes control lower timeframes
```

### The Manipulation Cycle

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│     1. ACCUMULATION           2. MANIPULATION                   │
│     (Range, boring)           (Sweep, trap)                     │
│                                                                  │
│     ████████████████          ████                              │
│     ████████████████               ████                         │
│     ████████████████                    ████                    │
│     ████████████████              ████████████                  │
│                                                                  │
│                                                                  │
│     3. DISTRIBUTION           4. CONTINUATION                   │
│     (Real move)               (Trend)                           │
│                                                                  │
│                    ████████████████████████████████████        │
│               ████████████████████████████████████████        │
│          ████████████████████████████████████████████        │
│     ████████████████████████████████████████████████        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📐 STRUCTURE CONCEPTS

### 1. Swing Points

**Definition**: Local price extremes used for structure analysis.

```
SWING HIGH:
- Candle high is HIGHER than N candles on left AND right
- Default N = 3 (ICT uses 2-5 based on context)

     HIGH
      /\
     /  \
    /    \
───/──────\───
  L        R
(lower)  (lower)

SWING LOW:
- Candle low is LOWER than N candles on left AND right

───\──────/───
    \    /
     \  /
      \/
      LOW
```

**Implementation**:
```python
def detect_swing_high(candles: List[Candle], index: int, lookback: int = 3) -> bool:
    if index < lookback or index >= len(candles) - lookback:
        return False
    
    current_high = candles[index].high
    
    # Check left side
    for i in range(1, lookback + 1):
        if candles[index - i].high >= current_high:
            return False
    
    # Check right side
    for i in range(1, lookback + 1):
        if candles[index + i].high >= current_high:
            return False
    
    return True
```

---

### 2. Market Structure

**BOS (Break of Structure)**:
- Price closes BEYOND previous swing point
- Confirms trend continuation

```
BULLISH BOS:
                          New HH
                           /\
                          /  \
              HH        /    
              /\      /      
             /  \   /        
            /    \ /         
       ────/──────X──────────── BOS Line (previous HH)
          /
         /  HL
        /\
       /  \
      /    
     LH
```

**CHoCH (Change of Character)**:
- First indication of potential reversal
- Price breaks opposite swing in existing trend

```
BEARISH CHoCH in uptrend:
                          HH
                          /\
                         /  \
                        /    \
              HH      /      \
              /\    /         \
             /  \ /            \
            /    X              \
           /                     \
          /  HL                   \ 
         /\                        \
        /  \                        \ CHoCH Line (breaks HL)
       /    \                        \
──────/──────\────────────────────────X──────
              HL                       |
                                  CHoCH (bearish shift)
```

**Implementation**:
```python
@dataclass
class StructureEvent:
    timestamp: datetime
    type: Literal["BOS", "CHOCH"]
    direction: Literal["BULLISH", "BEARISH"]
    broken_level: PriceLevel
    confirmation_candle: Candle
    
def detect_bos(swings: List[SwingPoint], candle: Candle, current_trend: str) -> Optional[StructureEvent]:
    """
    BOS = price closes beyond swing IN DIRECTION of trend
    """
    if current_trend == "BULLISH":
        # Look for previous swing high
        prev_swing_high = find_last_swing_high(swings)
        if candle.close > prev_swing_high.level:
            return StructureEvent(
                timestamp=candle.timestamp,
                type="BOS",
                direction="BULLISH",
                broken_level=prev_swing_high.level,
                confirmation_candle=candle
            )
    # Similar for BEARISH...
    
def detect_choch(swings: List[SwingPoint], candle: Candle, current_trend: str) -> Optional[StructureEvent]:
    """
    CHoCH = price closes beyond swing AGAINST direction of trend
    """
    if current_trend == "BULLISH":
        # Look for previous swing LOW (not high!)
        prev_swing_low = find_last_swing_low(swings)
        if candle.close < prev_swing_low.level:
            return StructureEvent(
                timestamp=candle.timestamp,
                type="CHOCH",
                direction="BEARISH",  # Shift to bearish
                broken_level=prev_swing_low.level,
                confirmation_candle=candle
            )
    # Similar for BEARISH trend...
```

---

### 3. Fibonacci Retracements

**ICT OTE (Optimal Trade Entry)**:
- Zone between 61.8% and 79% retracement
- "Sweet spot" at 70.5% (halfway between 61.8 and 79)

```
BULLISH SWING FIBONACCI:

Swing High ─────────────────────────── 0% (100% extension)
                                      
                                       23.6%
                                      
                                       38.2%
                                      
                                       50%
                                      
                    ┌───────────────── 61.8% (OTE BOTTOM)
     OTE ZONE ──────┤                  70.5% (SWEET SPOT)
                    └───────────────── 79% (OTE TOP)
                                      
                                       88.6%
                                      
Swing Low ──────────────────────────── 100%
                                      
                                       -27.2% (127.2% ext)
                                       -61.8% (161.8% ext)
```

**Implementation**:
```python
@dataclass
class FibonacciLevel:
    ratio: Decimal
    price: PriceLevel
    name: str
    is_ote: bool = False
    
class FibonacciCalculator:
    """Precise Fibonacci calculations with OTE zone"""
    
    RETRACEMENT_LEVELS = [
        ('0', Decimal('0')),
        ('23.6', Decimal('0.236')),
        ('38.2', Decimal('0.382')),
        ('50', Decimal('0.5')),
        ('61.8', Decimal('0.618')),     # OTE START
        ('70.5', Decimal('0.705')),     # OTE SWEET SPOT
        ('79', Decimal('0.79')),         # OTE END
        ('88.6', Decimal('0.886')),
        ('100', Decimal('1.0')),
    ]
    
    EXTENSION_LEVELS = [
        ('-27.2', Decimal('1.272')),
        ('-61.8', Decimal('1.618')),
        ('-100', Decimal('2.0')),
    ]
    
    def __init__(self, swing_high: PriceLevel, swing_low: PriceLevel, direction: str):
        self.high = swing_high
        self.low = swing_low
        self.direction = direction  # "BULLISH" or "BEARISH"
        self.range = self.high.value - self.low.value
    
    def get_all_levels(self) -> List[FibonacciLevel]:
        levels = []
        
        for name, ratio in self.RETRACEMENT_LEVELS:
            if self.direction == "BULLISH":
                # Measuring from high, down
                price = PriceLevel(self.high.value - (self.range * ratio))
            else:
                # Measuring from low, up
                price = PriceLevel(self.low.value + (self.range * ratio))
            
            is_ote = ratio >= Decimal('0.618') and ratio <= Decimal('0.79')
            levels.append(FibonacciLevel(ratio, price, name, is_ote))
        
        return levels
    
    def get_ote_zone(self) -> Tuple[PriceLevel, PriceLevel]:
        """Return OTE zone (61.8% to 79%)"""
        levels = self.get_all_levels()
        ote_levels = [l for l in levels if l.is_ote]
        prices = [l.price.value for l in ote_levels]
        return PriceLevel(min(prices)), PriceLevel(max(prices))
    
    def is_price_in_ote(self, price: PriceLevel) -> bool:
        ote_low, ote_high = self.get_ote_zone()
        return ote_low.value <= price.value <= ote_high.value
    
    def get_sweet_spot(self) -> PriceLevel:
        """Return 70.5% level (ICT sweet spot)"""
        levels = self.get_all_levels()
        return next(l.price for l in levels if l.name == '70.5')
```

---

## 💧 LIQUIDITY CONCEPTS

### 1. Liquidity Pools

**Definition**: Clusters of stop losses and pending orders.

```
TYPES OF LIQUIDITY:

1. EQUAL HIGHS (EQH):
   ═══════════════════ Same price level touched multiple times
       │  │  │
       │  │  │  ← Retail stops just above
       
2. EQUAL LOWS (EQL):
       │  │  │  ← Retail stops just below
       │  │  │
   ═══════════════════

3. SWING HIGHS/LOWS:
   Any swing point has stops beyond it
   
4. ROUND NUMBERS:
   22000, 22500, 23000, etc.
   
5. PDH/PDL (Previous Day High/Low):
   Obvious targets for morning hunts
   
6. PWH/PWL (Previous Week High/Low):
   Major targets for weekly moves
```

**Implementation**:
```python
@dataclass
class LiquidityPool:
    level: PriceLevel
    type: Literal["EQH", "EQL", "SWING_HIGH", "SWING_LOW", "PDH", "PDL", "PWH", "PWL", "ROUND"]
    touch_count: int  # How many times touched
    last_touch: datetime
    strength: float  # 0-1, based on touches and recency
    swept: bool = False
    swept_at: Optional[datetime] = None
    
class LiquidityMapper:
    def __init__(self, tolerance_percent: float = 0.001):
        self.tolerance = tolerance_percent  # Prices within 0.1% are "equal"
        self.pools: List[LiquidityPool] = []
    
    def find_equal_levels(self, swings: List[SwingPoint]) -> List[LiquidityPool]:
        """Find equal highs and equal lows"""
        pools = []
        
        # Group swing highs by price level
        high_levels = defaultdict(list)
        for swing in swings:
            if swing.type == "HIGH":
                # Round to tolerance
                rounded = self._round_to_tolerance(swing.level)
                high_levels[rounded].append(swing)
        
        # If 2+ touches, it's a liquidity pool
        for level, touches in high_levels.items():
            if len(touches) >= 2:
                pools.append(LiquidityPool(
                    level=PriceLevel(level),
                    type="EQH",
                    touch_count=len(touches),
                    last_touch=max(t.timestamp for t in touches),
                    strength=self._calculate_strength(len(touches), touches)
                ))
        
        # Similar for lows...
        return pools
    
    def add_key_levels(self, candles: List[Candle]) -> None:
        """Add PDH, PDL, PWH, PWL, round numbers"""
        
        # Get previous day data
        yesterday = self._get_previous_day(candles)
        if yesterday:
            self.pools.append(LiquidityPool(
                level=PriceLevel(max(c.high for c in yesterday)),
                type="PDH",
                touch_count=1,
                last_touch=yesterday[-1].timestamp,
                strength=0.9  # PDH/PDL are strong
            ))
            self.pools.append(LiquidityPool(
                level=PriceLevel(min(c.low for c in yesterday)),
                type="PDL",
                touch_count=1,
                last_touch=yesterday[-1].timestamp,
                strength=0.9
            ))
        
        # Add round numbers near current price
        current_price = candles[-1].close
        self._add_round_numbers(current_price)
```

---

### 2. Liquidity Sweeps

**Definition**: Price raids liquidity pool, then reverses.

```
BULLISH SWEEP (raid lows, go up):

              After sweep
             ████████████
            ██          
           ██           
          ██            
═════════════════════════ Liquidity level (stops here)
         ▼ │
         ▼ │ ← Sweep (wick below)
         ▼ │
           │
    Price fills orders,
    triggers stops,
    then REVERSES UP
    
BEARISH SWEEP (raid highs, go down):

           │
         ▲ │ ← Sweep (wick above)
         ▲ │
═════════════════════════ Liquidity level (stops here)
          ██            
           ██           
            ██          
             ████████████
              After sweep
```

**Quality Score**:
```python
@dataclass
class Sweep:
    pool: LiquidityPool
    sweep_candle: Candle
    direction: Literal["BULLISH", "BEARISH"]  # Direction AFTER sweep
    penetration_depth: Decimal  # How far past the level
    close_position: Literal["ABOVE", "BELOW", "AT"]  # Where candle closed
    quality_score: float  # 0-1
    
class SweepDetector:
    def detect_sweep(self, candle: Candle, pool: LiquidityPool) -> Optional[Sweep]:
        """Detect if candle sweeps a liquidity pool"""
        
        if pool.type in ["EQL", "PDL", "PWL", "SWING_LOW"]:
            # Bullish sweep: wick below, close above
            if candle.low < pool.level.value:  # Pierced the level
                penetration = pool.level.value - candle.low
                
                # Quality factors
                quality = 0.0
                
                # 1. Closed above the level? (+40%)
                if candle.close > pool.level.value:
                    quality += 0.4
                
                # 2. Closed in upper 50% of candle? (+20%)
                candle_range = candle.high - candle.low
                if candle_range > 0:
                    close_position = (candle.close - candle.low) / candle_range
                    if close_position > 0.5:
                        quality += 0.2
                
                # 3. Pool touched multiple times? (+20%)
                if pool.touch_count >= 3:
                    quality += 0.2
                elif pool.touch_count >= 2:
                    quality += 0.1
                
                # 4. Is this a major level (PDL, PWL)? (+20%)
                if pool.type in ["PDL", "PWL"]:
                    quality += 0.2
                elif pool.type == "EQL":
                    quality += 0.15
                
                return Sweep(
                    pool=pool,
                    sweep_candle=candle,
                    direction="BULLISH",
                    penetration_depth=Decimal(str(penetration)),
                    close_position="ABOVE" if candle.close > pool.level.value else "BELOW",
                    quality_score=min(quality, 1.0)
                )
        
        # Similar for bearish sweep (EQH, PDH, PWH, SWING_HIGH)...
        return None
```

---

## 📦 ORDER BLOCKS & FAIR VALUE GAPS

### 1. Order Blocks (OB)

**Definition**: Last opposite-direction candle before significant move (displacement).

```
BULLISH OB:

                        ████████ Displacement (big bullish move)
                      ██
                    ██
               ║══════════════════║ ← 4H/Daily OB zone
           ████║  Last bearish   ║
               ║   candle before ║
               ║    the move     ║
               ║══════════════════║

BEARISH OB:

           ████║══════════════════║
               ║  Last bullish   ║
               ║   candle before ║
               ║    the move     ║
               ║══════════════════║
                    ██
                      ██
                        ████████ Displacement (big bearish move)
```

**Displacement = 2+ big candles in same direction, or single huge candle**

**Implementation**:
```python
@dataclass
class OrderBlock:
    timeframe: str
    type: Literal["BULLISH", "BEARISH"]
    high: PriceLevel
    low: PriceLevel
    formation_time: datetime
    formation_candle: Candle
    displacement_size: Decimal  # ATR multiple
    valid: bool = True
    mitigated: bool = False
    mitigated_at: Optional[datetime] = None
    
class OrderBlockDetector:
    def __init__(self, min_displacement_atr: float = 1.5):
        self.min_displacement = min_displacement_atr
    
    def detect_orderblock(self, candles: List[Candle], atr: Decimal) -> Optional[OrderBlock]:
        """
        Look for last opposite candle before displacement.
        Displacement = move of 1.5+ ATR
        """
        if len(candles) < 5:
            return None
        
        # Check recent candles for displacement
        for i in range(len(candles) - 3, 0, -1):
            # Calculate displacement
            displacement = self._calculate_displacement(candles[i:i+3])
            
            if abs(displacement) >= self.min_displacement * float(atr):
                displacement_direction = "UP" if displacement > 0 else "DOWN"
                
                # Find last opposite candle before displacement
                for j in range(i - 1, max(0, i - 5), -1):
                    candidate = candles[j]
                    
                    if displacement_direction == "UP":
                        # Looking for last BEARISH candle
                        if candidate.close < candidate.open:
                            return OrderBlock(
                                timeframe="15M",  # Set based on candle source
                                type="BULLISH",
                                high=PriceLevel(candidate.high),
                                low=PriceLevel(candidate.low),
                                formation_time=candidate.timestamp,
                                formation_candle=candidate,
                                displacement_size=Decimal(str(displacement / float(atr)))
                            )
                    else:
                        # Looking for last BULLISH candle
                        if candidate.close > candidate.open:
                            return OrderBlock(
                                timeframe="15M",
                                type="BEARISH",
                                high=PriceLevel(candidate.high),
                                low=PriceLevel(candidate.low),
                                formation_time=candidate.timestamp,
                                formation_candle=candidate,
                                displacement_size=Decimal(str(abs(displacement) / float(atr)))
                            )
        
        return None
    
    def check_mitigation(self, ob: OrderBlock, candle: Candle) -> bool:
        """Check if price has returned to and touched the OB"""
        if ob.mitigated:
            return True
        
        if ob.type == "BULLISH":
            # Price must come down to touch OB zone
            if candle.low <= ob.high.value:
                ob.mitigated = True
                ob.mitigated_at = candle.timestamp
                return True
        else:
            # Price must come up to touch OB zone
            if candle.high >= ob.low.value:
                ob.mitigated = True
                ob.mitigated_at = candle.timestamp
                return True
        
        return False
```

---

### 2. Fair Value Gaps (FVG)

**Definition**: Price imbalance where middle candle's body doesn't overlap with adjacent wicks.

```
BULLISH FVG (gap up):

           ████████   Candle 3 (low above candle 1's high)
           ████████
                     
           ════════   GAP (FVG ZONE)
                     
    ██████████████   Candle 2 (big body, creates gap)
    ██████████████
                     
████████            Candle 1 (high below candle 3's low)
████████

BEARISH FVG (gap down):

████████            Candle 1 (low above candle 3's high)
████████
                     
    ██████████████   Candle 2 (big body, creates gap)
    ██████████████
                     
           ════════   GAP (FVG ZONE)
                     
           ████████   Candle 3 (high below candle 1's low)
           ████████
```

**Implementation**:
```python
@dataclass
class FairValueGap:
    type: Literal["BULLISH", "BEARISH"]
    high: PriceLevel  # Top of gap
    low: PriceLevel   # Bottom of gap
    formation_time: datetime
    candles: Tuple[Candle, Candle, Candle]  # The 3 candles
    size: Decimal  # Gap size in points
    filled: bool = False
    filled_at: Optional[datetime] = None
    fill_percentage: float = 0.0
    
class FVGDetector:
    def detect_fvg(self, candles: List[Candle]) -> Optional[FairValueGap]:
        """Detect Fair Value Gap in last 3 candles"""
        if len(candles) < 3:
            return None
        
        c1, c2, c3 = candles[-3], candles[-2], candles[-1]
        
        # Bullish FVG: C3's low > C1's high
        if c3.low > c1.high:
            return FairValueGap(
                type="BULLISH",
                high=PriceLevel(c3.low),
                low=PriceLevel(c1.high),
                formation_time=c2.timestamp,
                candles=(c1, c2, c3),
                size=Decimal(str(c3.low - c1.high))
            )
        
        # Bearish FVG: C3's high < C1's low
        if c3.high < c1.low:
            return FairValueGap(
                type="BEARISH",
                high=PriceLevel(c1.low),
                low=PriceLevel(c3.high),
                formation_time=c2.timestamp,
                candles=(c1, c2, c3),
                size=Decimal(str(c1.low - c3.high))
            )
        
        return None
    
    def check_fill(self, fvg: FairValueGap, candle: Candle) -> float:
        """Check if and how much the FVG has been filled"""
        if fvg.filled:
            return 1.0
        
        gap_size = float(fvg.high.value - fvg.low.value)
        
        if fvg.type == "BULLISH":
            # Price must come DOWN to fill bullish FVG
            if candle.low <= fvg.high.value:
                penetration = fvg.high.value - candle.low
                fill_pct = min(float(penetration) / gap_size, 1.0)
                
                if candle.low <= fvg.low.value:
                    fvg.filled = True
                    fvg.filled_at = candle.timestamp
                    fill_pct = 1.0
                
                fvg.fill_percentage = fill_pct
                return fill_pct
        else:
            # Price must come UP to fill bearish FVG
            if candle.high >= fvg.low.value:
                penetration = candle.high - fvg.low.value
                fill_pct = min(float(penetration) / gap_size, 1.0)
                
                if candle.high >= fvg.high.value:
                    fvg.filled = True
                    fvg.filled_at = candle.timestamp
                    fill_pct = 1.0
                
                fvg.fill_percentage = fill_pct
                return fill_pct
        
        return 0.0
```

---

## ⏰ TIME-BASED CONCEPTS

### 1. Kill Zones (Indian Market)

```
INDIAN MARKET KILL ZONES:

09:15 ═══════════════════════ MARKET OPEN
      ║                     ║
      ║   MORNING HUNT      ║ ← MAXIMUM DANGER
      ║   9:15 - 10:30      ║    Most manipulation
      ║                     ║    Avoid entries
10:30 ═══════════════════════
      │                     │
      │   POST-HUNT ZONE    │ ← Order blocks form
      │   10:30 - 11:00     │    Wait for setup
11:00 │                     │
      │   EXECUTION ZONE 1  │ ← SAFEST ENTRIES
      │   11:00 - 12:30     │    Trade OB reactions
12:30 │                     │
      │   LUNCH LULL        │ ← Reduced activity
      │   12:30 - 13:30     │    Wait or scale out
13:30 ═══════════════════════
      ║                     ║
      ║   LUNCH SWEEP       ║ ← Secondary hunt
      ║   13:30 - 14:00     ║    Be alert
14:00 ═══════════════════════
      │                     │
      │   EXECUTION ZONE 2  │ ← Second safe window
      │   14:00 - 14:45     │    Trade if setup exists
14:45 │                     │
      ║                     ║
      ║   CLOSING CHAOS     ║ ← Final manipulation
      ║   14:45 - 15:30     ║    Avoid new entries
15:30 ═══════════════════════ MARKET CLOSE
```

### 2. Power of 3 (AMD)

```
ACCUMULATION → MANIPULATION → DISTRIBUTION

MORNING (Day Scale):
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  09:15-10:00    10:00-10:30         10:30-15:30             │
│  ════════════   ════════════════    ════════════════════    │
│                                                              │
│  ACCUMULATION   MANIPULATION        DISTRIBUTION            │
│                                                              │
│  ████████████      │                                        │
│  ████████████      │ Sweep           ████████████████████   │
│  ████████████      ▼                 ████████████████████   │
│  ████████████   ─────────         ███████████████████████   │
│              ███████████     ████████████████████████████   │
│                         █████████████████████████████████   │
│                                                              │
│  Range forms   Hunt stops    Real move begins               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ IMPLEMENTATION CHECKLIST

### Must Implement (MVP)

- [ ] Swing point detection (configurable lookback)
- [ ] BOS detection
- [ ] CHoCH detection
- [ ] Fibonacci retracements with OTE zone
- [ ] Equal highs/lows detection
- [ ] PDH/PDL/PWH/PWL tracking
- [ ] Liquidity sweep detection with quality score
- [ ] Order block detection
- [ ] Fair Value Gap detection
- [ ] Kill zone time mapping
- [ ] Power of 3 phase detection

### Post-MVP

- [ ] SMT Divergence
- [ ] Breaker blocks
- [ ] Mitigation tracking
- [ ] ICT Macros
- [ ] Silver Bullet time
- [ ] IPDA cycles

---

> **This document is the BIBLE for ICT concepts. Every detection algorithm MUST reference this.**
