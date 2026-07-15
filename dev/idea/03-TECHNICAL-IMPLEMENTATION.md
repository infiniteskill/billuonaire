# 🔧 Technical Implementation Strategy

> This document outlines HOW to build the Manipulation Detection System.
> Language-agnostic principles, adaptable to Python, TypeScript, or any language.

---

## 📐 SYSTEM COMPONENTS

### Component Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                         MANIPULATION RADAR                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    MARKET DATA ADAPTER                      │ │
│  │  TradingView │ NSE/BSE API │ Broker API │ CSV Historical   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    CANDLE PROCESSOR                         │ │
│  │  OHLC normalization │ Multi-TF aggregation │ Gap detection │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────┬─────────────────┬─────────────────┐       │
│  │  STRUCTURE      │  LIQUIDITY      │  PATTERN        │       │
│  │  ANALYZER       │  DETECTOR       │  RECOGNIZER     │       │
│  │                 │                 │                 │       │
│  │ • Swing Points  │ • Pool Mapping  │ • OB Detection  │       │
│  │ • BOS/CHoCH     │ • Sweep Detect  │ • FVG Detection │       │
│  │ • Trend State   │ • Hunt Tracking │ • Trap Chains   │       │
│  └─────────────────┴─────────────────┴─────────────────┘       │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    CONFLUENCE ENGINE                        │ │
│  │  Score Calculation │ Entry Validation │ Time Filter        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    LEARNING MODULE                          │ │
│  │  Time Stats │ Pattern Success │ Self-Calibration           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    ALERT & EXECUTION                        │ │
│  │  Signal Generation │ Risk Calc │ Trade Management          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 DATA STRUCTURES

### Core Candle Structure
```python
@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    timeframe: str  # "1m", "5m", "15m", "1h", "4h", "1d"

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def range(self) -> float:
        return self.high - self.low
```

### Swing Point Structure
```python
@dataclass
class SwingPoint:
    type: Literal["SWING_HIGH", "SWING_LOW"]
    price: float
    timestamp: datetime
    timeframe: str
    strength: int  # Number of candles on each side confirming
    status: Literal["ACTIVE", "BROKEN", "SWEPT"]
    swept_at: Optional[datetime] = None

    def distance_from(self, current_price: float) -> float:
        return abs(current_price - self.price)

    def is_equal_to(self, other: 'SwingPoint', tolerance: float = 0.001) -> bool:
        """Check if two swing points form equal highs/lows"""
        if self.type != other.type:
            return False
        price_diff = abs(self.price - other.price) / self.price
        return price_diff <= tolerance
```

### Liquidity Pool Structure
```python
@dataclass
class LiquidityPool:
    type: Literal["BSL", "SSL"]  # Buy-side (above) or Sell-side (below)
    price_level: float
    price_range: Tuple[float, float]  # Exact zone
    strength: int  # Number of touches/swing points
    formation_time: datetime
    timeframe: str
    status: Literal["ACTIVE", "SWEPT", "EXPIRED"]
    source: Literal["EQUAL_HL", "PDH", "PDL", "PWH", "PWL", "SWING", "OPENING_RANGE"]
    swept_at: Optional[datetime] = None

    @property
    def priority(self) -> int:
        """Higher = more important to track"""
        source_priority = {
            "PWH": 10, "PWL": 10,
            "PDH": 8, "PDL": 8,
            "EQUAL_HL": 7,
            "SWING": 5,
            "OPENING_RANGE": 6
        }
        return source_priority.get(self.source, 3) + self.strength
```

### Order Block Structure
```python
@dataclass
class OrderBlock:
    type: Literal["BULLISH", "BEARISH"]
    price_range: Tuple[float, float]  # (low, high) of OB zone
    formation_time: datetime
    timeframe: str
    status: Literal["VALID", "MITIGATED", "INVALIDATED"]
    formed_during_hunt: bool  # True if 9:15-10:30 IST
    mitigation_count: int = 0
    last_test_time: Optional[datetime] = None

    @property
    def midpoint(self) -> float:
        return (self.price_range[0] + self.price_range[1]) / 2

    @property
    def fifty_percent(self) -> float:
        """50% of OB - common entry point"""
        return self.midpoint

    def contains_price(self, price: float) -> bool:
        return self.price_range[0] <= price <= self.price_range[1]

    def is_stale(self, current_time: datetime, max_age_days: int = 5) -> bool:
        age = (current_time - self.formation_time).days
        return age > max_age_days
```

### Fair Value Gap Structure
```python
@dataclass
class FairValueGap:
    type: Literal["BULLISH", "BEARISH"]
    price_range: Tuple[float, float]  # Gap zone
    formation_time: datetime
    timeframe: str
    filled: bool = False
    fill_percentage: float = 0.0

    @property
    def size(self) -> float:
        return abs(self.price_range[1] - self.price_range[0])

    def update_fill(self, high: float, low: float) -> None:
        if self.type == "BULLISH":
            # Bullish FVG: price needs to drop to fill gap
            if low <= self.price_range[1]:
                fill_depth = max(0, self.price_range[1] - low)
                self.fill_percentage = min(100, (fill_depth / self.size) * 100)
                if low <= self.price_range[0]:
                    self.filled = True
        else:
            # Bearish FVG: price needs to rise to fill gap
            if high >= self.price_range[0]:
                fill_depth = max(0, high - self.price_range[0])
                self.fill_percentage = min(100, (fill_depth / self.size) * 100)
                if high >= self.price_range[1]:
                    self.filled = True
```

### Structure State
```python
@dataclass
class MarketStructure:
    timeframe: str
    trend: Literal["BULLISH", "BEARISH", "RANGING"]
    last_swing_high: SwingPoint
    last_swing_low: SwingPoint
    last_bos: Optional[Tuple[str, datetime, float]]  # (type, time, price)
    last_choch: Optional[Tuple[str, datetime, float]]
    swing_history: List[SwingPoint]

    def update_structure(self, new_swing: SwingPoint) -> Optional[str]:
        """Returns 'BOS' or 'CHoCH' if structure change detected"""
        if new_swing.type == "SWING_HIGH":
            if self.trend == "BULLISH" and new_swing.price > self.last_swing_high.price:
                return "BOS"  # Continuation
            elif self.trend == "BEARISH" and new_swing.price > self.last_swing_high.price:
                return "CHoCH"  # Potential reversal
        elif new_swing.type == "SWING_LOW":
            if self.trend == "BEARISH" and new_swing.price < self.last_swing_low.price:
                return "BOS"
            elif self.trend == "BULLISH" and new_swing.price < self.last_swing_low.price:
                return "CHoCH"
        return None
```

### Trade Setup Structure
```python
@dataclass
class TradeSetup:
    id: str
    symbol: str
    direction: Literal["LONG", "SHORT"]
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: Optional[float]
    risk_reward: float
    confluence_score: int  # 0-100
    setup_type: str  # "SWEEP_CHOCH_OB", "FVG_FILL", etc.
    formation_time: datetime
    valid_until: datetime
    htf_bias: Literal["BULLISH", "BEARISH"]
    sweep_confirmed: bool
    structure_confirmed: bool
    ob_present: bool
    fvg_present: bool
    time_filter_passed: bool

    @property
    def sl_distance(self) -> float:
        return abs(self.entry_price - self.stop_loss)

    @property
    def risk_percent_for_account(self) -> Callable[[float, float], float]:
        """Returns position size calculator"""
        def calc(account_size: float, risk_percent: float) -> float:
            risk_amount = account_size * (risk_percent / 100)
            return risk_amount / self.sl_distance
        return calc
```

### Learning Data Structures
```python
@dataclass
class TradeOutcome:
    setup_id: str
    symbol: str
    direction: str
    entry_time: datetime
    exit_time: datetime
    day_of_week: int  # 0=Monday
    time_of_day: time
    minutes_from_open: int
    setup_type: str
    confluence_score: int
    outcome: Literal["WIN", "LOSS", "BE"]
    rr_achieved: float
    pnl: float
    notes: str = ""

@dataclass
class TimeProbabilityEntry:
    day: int  # 0-4 (Mon-Fri)
    hour: int
    minute_bucket: int  # 0=00-15, 1=15-30, 2=30-45, 3=45-00
    total_trades: int
    wins: int
    losses: int
    breakeven: int
    avg_rr: float
    last_updated: datetime

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.5  # Default
        return self.wins / self.total_trades

@dataclass
class PatternStats:
    pattern_name: str
    total_occurrences: int
    wins: int
    losses: int
    avg_rr: float
    best_time_window: str
    worst_time_window: str
    confidence_interval: Tuple[float, float]

    @property
    def win_rate(self) -> float:
        if self.total_occurrences == 0:
            return 0.5
        return self.wins / self.total_occurrences

    @property
    def is_viable(self) -> bool:
        """Pattern worth trading?"""
        return (
            self.total_occurrences >= 20 and
            self.win_rate >= 0.40 and
            self.avg_rr >= 1.5
        )
```

---

## 🔧 CORE ALGORITHMS

### 1. Swing Point Detection
```python
def detect_swing_points(candles: List[Candle], lookback: int = 5) -> List[SwingPoint]:
    """
    Detect swing highs and lows.
    A swing high: High is highest of lookback candles on each side.
    A swing low: Low is lowest of lookback candles on each side.
    """
    swings = []

    for i in range(lookback, len(candles) - lookback):
        current = candles[i]

        # Check swing high
        left_highs = [c.high for c in candles[i-lookback:i]]
        right_highs = [c.high for c in candles[i+1:i+lookback+1]]

        if current.high > max(left_highs) and current.high > max(right_highs):
            swings.append(SwingPoint(
                type="SWING_HIGH",
                price=current.high,
                timestamp=current.timestamp,
                timeframe=current.timeframe,
                strength=lookback,
                status="ACTIVE"
            ))

        # Check swing low
        left_lows = [c.low for c in candles[i-lookback:i]]
        right_lows = [c.low for c in candles[i+1:i+lookback+1]]

        if current.low < min(left_lows) and current.low < min(right_lows):
            swings.append(SwingPoint(
                type="SWING_LOW",
                price=current.low,
                timestamp=current.timestamp,
                timeframe=current.timeframe,
                strength=lookback,
                status="ACTIVE"
            ))

    return swings
```

### 2. Liquidity Pool Mapping
```python
def map_liquidity_pools(
    swing_points: List[SwingPoint],
    pdh: float, pdl: float,
    pwh: float, pwl: float,
    opening_range: Tuple[float, float],
    tolerance: float = 0.001
) -> List[LiquidityPool]:
    """Map all liquidity pools from various sources."""
    pools = []

    # PDH/PDL pools
    pools.append(LiquidityPool(
        type="BSL", price_level=pdh, price_range=(pdh * 0.999, pdh * 1.001),
        strength=8, formation_time=datetime.now(), timeframe="D1",
        status="ACTIVE", source="PDH"
    ))
    pools.append(LiquidityPool(
        type="SSL", price_level=pdl, price_range=(pdl * 0.999, pdl * 1.001),
        strength=8, formation_time=datetime.now(), timeframe="D1",
        status="ACTIVE", source="PDL"
    ))

    # PWH/PWL pools
    pools.append(LiquidityPool(
        type="BSL", price_level=pwh, price_range=(pwh * 0.999, pwh * 1.001),
        strength=10, formation_time=datetime.now(), timeframe="W1",
        status="ACTIVE", source="PWH"
    ))
    pools.append(LiquidityPool(
        type="SSL", price_level=pwl, price_range=(pwl * 0.999, pwl * 1.001),
        strength=10, formation_time=datetime.now(), timeframe="W1",
        status="ACTIVE", source="PWL"
    ))

    # Opening range pools
    pools.append(LiquidityPool(
        type="BSL", price_level=opening_range[1],
        price_range=(opening_range[1] * 0.999, opening_range[1] * 1.001),
        strength=6, formation_time=datetime.now(), timeframe="15M",
        status="ACTIVE", source="OPENING_RANGE"
    ))
    pools.append(LiquidityPool(
        type="SSL", price_level=opening_range[0],
        price_range=(opening_range[0] * 0.999, opening_range[0] * 1.001),
        strength=6, formation_time=datetime.now(), timeframe="15M",
        status="ACTIVE", source="OPENING_RANGE"
    ))

    # Equal highs/lows from swing points
    swing_highs = [s for s in swing_points if s.type == "SWING_HIGH"]
    swing_lows = [s for s in swing_points if s.type == "SWING_LOW"]

    # Find equal highs
    for i, sh1 in enumerate(swing_highs):
        for sh2 in swing_highs[i+1:]:
            if sh1.is_equal_to(sh2, tolerance):
                avg_price = (sh1.price + sh2.price) / 2
                pools.append(LiquidityPool(
                    type="BSL", price_level=avg_price,
                    price_range=(min(sh1.price, sh2.price), max(sh1.price, sh2.price)),
                    strength=2, formation_time=sh2.timestamp, timeframe=sh1.timeframe,
                    status="ACTIVE", source="EQUAL_HL"
                ))

    # Find equal lows
    for i, sl1 in enumerate(swing_lows):
        for sl2 in swing_lows[i+1:]:
            if sl1.is_equal_to(sl2, tolerance):
                avg_price = (sl1.price + sl2.price) / 2
                pools.append(LiquidityPool(
                    type="SSL", price_level=avg_price,
                    price_range=(min(sl1.price, sl2.price), max(sl1.price, sl2.price)),
                    strength=2, formation_time=sl2.timestamp, timeframe=sl1.timeframe,
                    status="ACTIVE", source="EQUAL_HL"
                ))

    return sorted(pools, key=lambda p: p.priority, reverse=True)
```

### 3. Sweep Detection
```python
def detect_sweep(
    current_candle: Candle,
    liquidity_pool: LiquidityPool,
    confirmation_candles: int = 3
) -> Optional[Dict]:
    """
    Detect if current candle has swept liquidity pool.
    Returns sweep details if confirmed, None otherwise.
    """
    if liquidity_pool.status != "ACTIVE":
        return None

    sweep_detected = False
    sweep_type = None

    if liquidity_pool.type == "BSL":  # Buy-side liquidity above
        # Price wicked above pool but didn't close above
        if (current_candle.high > liquidity_pool.price_level and
            current_candle.close < liquidity_pool.price_level):
            sweep_detected = True
            sweep_type = "JUDAS_HIGH"

    elif liquidity_pool.type == "SSL":  # Sell-side liquidity below
        # Price wicked below pool but didn't close below
        if (current_candle.low < liquidity_pool.price_level and
            current_candle.close > liquidity_pool.price_level):
            sweep_detected = True
            sweep_type = "JUDAS_LOW"

    if sweep_detected:
        # Calculate sweep quality
        wick_depth = (
            current_candle.high - liquidity_pool.price_level
            if liquidity_pool.type == "BSL"
            else liquidity_pool.price_level - current_candle.low
        )

        return {
            "pool": liquidity_pool,
            "sweep_type": sweep_type,
            "sweep_time": current_candle.timestamp,
            "wick_depth": wick_depth,
            "quality_score": calculate_sweep_quality(
                wick_depth, current_candle, liquidity_pool
            )
        }

    return None


def calculate_sweep_quality(
    wick_depth: float,
    candle: Candle,
    pool: LiquidityPool
) -> int:
    """Score sweep quality 0-100."""
    score = 0

    # Wick depth score (0-30)
    wick_ratio = wick_depth / pool.price_level * 100
    if wick_ratio > 0.5:
        score += 30
    elif wick_ratio > 0.3:
        score += 20
    elif wick_ratio > 0.1:
        score += 10

    # Rejection quality (0-25)
    if pool.type == "BSL":
        rejection = candle.upper_wick / candle.range if candle.range > 0 else 0
    else:
        rejection = candle.lower_wick / candle.range if candle.range > 0 else 0

    score += int(rejection * 25)

    # Pool priority (0-20)
    score += min(20, pool.priority * 2)

    # Time of day bonus (0-15)
    hour = candle.timestamp.hour
    if 11 <= hour <= 13:  # Post-hunt hours
        score += 15
    elif 9 <= hour <= 10:  # During hunt (expected but risky)
        score += 5

    # Timeframe importance (0-10)
    tf_scores = {"D1": 10, "4H": 8, "1H": 6, "15M": 4, "5M": 2}
    score += tf_scores.get(pool.timeframe, 2)

    return min(100, score)
```

### 4. Order Block Detection
```python
def detect_order_block(
    candles: List[Candle],
    displacement_multiplier: float = 2.0
) -> Optional[OrderBlock]:
    """
    Detect order block from recent candles.
    OB = last opposite candle before displacement.
    """
    if len(candles) < 5:
        return None

    # Calculate average body size for reference
    avg_body = sum(c.body_size for c in candles[-20:]) / 20 if len(candles) >= 20 else candles[-1].body_size

    # Check for bullish OB (last bearish candle before bullish displacement)
    last_bearish_idx = None
    for i in range(len(candles) - 2, -1, -1):
        if not candles[i].is_bullish:
            last_bearish_idx = i
            break

    if last_bearish_idx is not None:
        # Check for bullish displacement after
        displacement_candles = candles[last_bearish_idx + 1:]
        if displacement_candles:
            total_move = sum(c.close - c.open for c in displacement_candles if c.is_bullish)
            if total_move > avg_body * displacement_multiplier:
                ob_candle = candles[last_bearish_idx]
                return OrderBlock(
                    type="BULLISH",
                    price_range=(ob_candle.low, ob_candle.high),
                    formation_time=ob_candle.timestamp,
                    timeframe=ob_candle.timeframe,
                    status="VALID",
                    formed_during_hunt=is_hunt_hours(ob_candle.timestamp)
                )

    # Check for bearish OB (last bullish candle before bearish displacement)
    last_bullish_idx = None
    for i in range(len(candles) - 2, -1, -1):
        if candles[i].is_bullish:
            last_bullish_idx = i
            break

    if last_bullish_idx is not None:
        displacement_candles = candles[last_bullish_idx + 1:]
        if displacement_candles:
            total_move = sum(c.open - c.close for c in displacement_candles if not c.is_bullish)
            if total_move > avg_body * displacement_multiplier:
                ob_candle = candles[last_bullish_idx]
                return OrderBlock(
                    type="BEARISH",
                    price_range=(ob_candle.low, ob_candle.high),
                    formation_time=ob_candle.timestamp,
                    timeframe=ob_candle.timeframe,
                    status="VALID",
                    formed_during_hunt=is_hunt_hours(ob_candle.timestamp)
                )

    return None


def is_hunt_hours(dt: datetime) -> bool:
    """Check if time is during morning hunt hours (IST)."""
    hour, minute = dt.hour, dt.minute
    return (9 <= hour < 10) or (hour == 10 and minute <= 30)
```

### 5. Fair Value Gap Detection
```python
def detect_fvg(candles: List[Candle]) -> Optional[FairValueGap]:
    """
    Detect Fair Value Gap in last 3 candles.
    Bullish FVG: Candle 1 high < Candle 3 low
    Bearish FVG: Candle 1 low > Candle 3 high
    """
    if len(candles) < 3:
        return None

    c1, c2, c3 = candles[-3], candles[-2], candles[-1]

    # Bullish FVG
    if c1.high < c3.low:
        return FairValueGap(
            type="BULLISH",
            price_range=(c1.high, c3.low),
            formation_time=c2.timestamp,
            timeframe=c2.timeframe
        )

    # Bearish FVG
    if c1.low > c3.high:
        return FairValueGap(
            type="BEARISH",
            price_range=(c3.high, c1.low),
            formation_time=c2.timestamp,
            timeframe=c2.timeframe
        )

    return None
```

### 6. Confluence Scoring
```python
def calculate_confluence_score(
    htf_bias: str,
    ltf_direction: str,
    sweep_confirmed: bool,
    structure_confirmed: bool,
    ob_present: bool,
    fvg_present: bool,
    time_filter_passed: bool,
    ob_formed_during_hunt: bool,
    pattern_win_rate: float
) -> int:
    """Calculate overall setup confluence score (0-100)."""
    score = 0

    # HTF Alignment (20 points)
    if htf_bias == ltf_direction:
        score += 20

    # Liquidity Sweep (25 points)
    if sweep_confirmed:
        score += 25

    # Structure Confirmation (15 points)
    if structure_confirmed:
        score += 15

    # Order Block Present (15 points)
    if ob_present:
        score += 12
        if ob_formed_during_hunt:
            score += 3  # Bonus for hunt-formed OB

    # FVG Present (10 points)
    if fvg_present:
        score += 10

    # Time Filter (10 points)
    if time_filter_passed:
        score += 10

    # Pattern Historical Performance (5 points)
    score += int(pattern_win_rate * 5)

    return min(100, score)
```

---

## 📊 LEARNING SYSTEM

### Time Probability Tracker
```python
class TimeProbabilityTracker:
    def __init__(self):
        self.data: Dict[Tuple[int, int, int], TimeProbabilityEntry] = {}

    def record_trade(self, outcome: TradeOutcome) -> None:
        key = (
            outcome.day_of_week,
            outcome.entry_time.hour,
            outcome.entry_time.minute // 15
        )

        if key not in self.data:
            self.data[key] = TimeProbabilityEntry(
                day=key[0], hour=key[1], minute_bucket=key[2],
                total_trades=0, wins=0, losses=0, breakeven=0,
                avg_rr=0.0, last_updated=datetime.now()
            )

        entry = self.data[key]
        entry.total_trades += 1

        if outcome.outcome == "WIN":
            entry.wins += 1
        elif outcome.outcome == "LOSS":
            entry.losses += 1
        else:
            entry.breakeven += 1

        # Update running average RR
        entry.avg_rr = (
            (entry.avg_rr * (entry.total_trades - 1) + outcome.rr_achieved)
            / entry.total_trades
        )
        entry.last_updated = datetime.now()

    def should_trade(self, day: int, hour: int, minute: int, threshold: float = 0.45) -> bool:
        key = (day, hour, minute // 15)
        if key not in self.data:
            # No data - use default rules
            return not (9 <= hour <= 10)  # Avoid hunt hours

        return self.data[key].win_rate >= threshold

    def get_best_windows(self, min_trades: int = 10) -> List[Tuple[int, int, float]]:
        """Return top trading windows by win rate."""
        viable = [
            (k, v.win_rate)
            for k, v in self.data.items()
            if v.total_trades >= min_trades
        ]
        return sorted(viable, key=lambda x: x[1], reverse=True)[:10]
```

### Pattern Success Tracker
```python
class PatternSuccessTracker:
    def __init__(self):
        self.patterns: Dict[str, PatternStats] = {}

    def record_pattern_outcome(
        self,
        pattern_name: str,
        outcome: Literal["WIN", "LOSS", "BE"],
        rr: float,
        time_window: str
    ) -> None:
        if pattern_name not in self.patterns:
            self.patterns[pattern_name] = PatternStats(
                pattern_name=pattern_name,
                total_occurrences=0, wins=0, losses=0,
                avg_rr=0.0, best_time_window="", worst_time_window="",
                confidence_interval=(0.0, 1.0)
            )

        stat = self.patterns[pattern_name]
        stat.total_occurrences += 1

        if outcome == "WIN":
            stat.wins += 1
        elif outcome == "LOSS":
            stat.losses += 1

        # Update average RR
        stat.avg_rr = (
            (stat.avg_rr * (stat.total_occurrences - 1) + rr)
            / stat.total_occurrences
        )

        self._update_time_windows(stat, time_window, outcome)
        self._update_confidence_interval(stat)

    def get_viable_patterns(self) -> List[str]:
        """Return patterns worth trading."""
        return [
            name for name, stat in self.patterns.items()
            if stat.is_viable
        ]

    def _update_confidence_interval(self, stat: PatternStats) -> None:
        """Calculate 95% confidence interval for win rate."""
        if stat.total_occurrences < 5:
            stat.confidence_interval = (0.0, 1.0)
            return

        p = stat.win_rate
        n = stat.total_occurrences
        z = 1.96  # 95% CI

        margin = z * ((p * (1 - p)) / n) ** 0.5
        stat.confidence_interval = (
            max(0.0, p - margin),
            min(1.0, p + margin)
        )
```

---

## 🎯 ENTRY/EXIT LOGIC

### Entry Decision
```python
def should_enter_trade(setup: TradeSetup) -> Tuple[bool, str]:
    """
    Final entry decision with reason.
    Returns (should_enter, reason).
    """
    # Hard filters
    if not setup.time_filter_passed:
        return False, "Time filter failed - outside trading window"

    if not setup.sweep_confirmed and setup.confluence_score < 80:
        return False, "No sweep confirmation - waiting for liquidity grab"

    if setup.htf_bias != setup.direction:
        return False, "Against HTF bias - high risk trade"

    # Score threshold
    if setup.confluence_score < 50:
        return False, f"Low confluence ({setup.confluence_score}/100)"

    if setup.confluence_score < 65:
        return False, f"Marginal confluence ({setup.confluence_score}/100) - consider skipping"

    # Risk/Reward check
    if setup.risk_reward < 1.5:
        return False, f"Poor RR ({setup.risk_reward:.1f}:1)"

    # All checks passed
    return True, f"Valid setup - Score: {setup.confluence_score}/100, RR: {setup.risk_reward:.1f}:1"
```

### Stop Loss Calculation
```python
def calculate_stop_loss(
    direction: str,
    entry_price: float,
    sweep_low: Optional[float],
    sweep_high: Optional[float],
    ob: Optional[OrderBlock],
    atr: float,
    buffer_multiplier: float = 0.2
) -> float:
    """
    Calculate optimal stop loss.
    Goal: Smallest SL that won't get hunted.
    """
    candidates = []

    if direction == "LONG":
        # Below sweep low
        if sweep_low:
            candidates.append(sweep_low - (atr * buffer_multiplier))

        # Below OB
        if ob and ob.type == "BULLISH":
            candidates.append(ob.price_range[0] - (atr * buffer_multiplier))

        # Pick the tightest that's reasonable
        valid_candidates = [c for c in candidates if entry_price - c > atr * 0.1]
        if valid_candidates:
            return max(valid_candidates)  # Tightest (highest for long)

        # Fallback: fixed ATR-based
        return entry_price - (atr * 1.5)

    else:  # SHORT
        if sweep_high:
            candidates.append(sweep_high + (atr * buffer_multiplier))

        if ob and ob.type == "BEARISH":
            candidates.append(ob.price_range[1] + (atr * buffer_multiplier))

        valid_candidates = [c for c in candidates if c - entry_price > atr * 0.1]
        if valid_candidates:
            return min(valid_candidates)  # Tightest (lowest for short)

        return entry_price + (atr * 1.5)
```

### Target Calculation
```python
def calculate_targets(
    direction: str,
    entry_price: float,
    stop_loss: float,
    liquidity_pools: List[LiquidityPool],
    min_rr: float = 2.0
) -> Tuple[float, float, Optional[float]]:
    """
    Calculate TP levels based on opposite liquidity.
    Returns (TP1, TP2, TP3).
    """
    sl_distance = abs(entry_price - stop_loss)

    if direction == "LONG":
        # Target pools above entry
        pools_above = sorted(
            [p for p in liquidity_pools if p.type == "BSL" and p.price_level > entry_price],
            key=lambda p: p.price_level
        )

        min_tp1 = entry_price + (sl_distance * min_rr)

        if pools_above:
            tp1 = max(pools_above[0].price_level, min_tp1)
            tp2 = pools_above[1].price_level if len(pools_above) > 1 else tp1 * 1.5
            tp3 = pools_above[2].price_level if len(pools_above) > 2 else None
        else:
            tp1 = min_tp1
            tp2 = entry_price + (sl_distance * 4)
            tp3 = entry_price + (sl_distance * 6)

    else:  # SHORT
        pools_below = sorted(
            [p for p in liquidity_pools if p.type == "SSL" and p.price_level < entry_price],
            key=lambda p: p.price_level,
            reverse=True
        )

        min_tp1 = entry_price - (sl_distance * min_rr)

        if pools_below:
            tp1 = min(pools_below[0].price_level, min_tp1)
            tp2 = pools_below[1].price_level if len(pools_below) > 1 else tp1 * 0.5
            tp3 = pools_below[2].price_level if len(pools_below) > 2 else None
        else:
            tp1 = min_tp1
            tp2 = entry_price - (sl_distance * 4)
            tp3 = entry_price - (sl_distance * 6)

    return tp1, tp2, tp3
```

---

## 🚀 NEXT STEPS

### Phase 1: MVP (2-4 weeks)
1. [ ] Candle data ingestion (CSV/API)
2. [ ] Swing point detection
3. [ ] Basic liquidity pool mapping
4. [ ] Time filter (no morning trades)
5. [ ] CLI output for signals

### Phase 2: Detection (2-4 weeks)
6. [ ] Sweep detection with quality scoring
7. [ ] Order block detection
8. [ ] BOS/CHoCH structure analysis
9. [ ] FVG detection
10. [ ] Multi-timeframe fusion

### Phase 3: Intelligence (2-4 weeks)
11. [ ] Trade outcome logging
12. [ ] Time probability learning
13. [ ] Pattern success tracking
14. [ ] Confluence scoring engine
15. [ ] Self-calibration routine

### Phase 4: Production (2-4 weeks)
16. [ ] Alert system (webhook/telegram)
17. [ ] Risk management module
18. [ ] Backtesting framework
19. [ ] Paper trading mode
20. [ ] Performance dashboard

---

> **Key Insight**: This system doesn't predict. It WAITS for manipulation to complete and enters with the operator, not against them.
