# 🔭 Multi-Scale Context Architecture: The "Big Picture" Problem

> **Core Problem**: When looking at small timeframes, you miss HTF manipulation levels.
> When looking at big picture, you miss LTF execution opportunities.
> How do we maintain BOTH simultaneously?

---

## 📊 Chart Analysis: Your Samples

### Pattern Recognition from Uploaded Charts

````carousel
![Chart 1: Indecision → Breakout → Return](/home/doom/.gemini/antigravity/brain/2c678453-0200-41f9-ac60-733fac3f3a45/uploaded_media_0_1769859905169.png)

**Pattern: Classic Retail Trap Cycle**
1. Morning indecision (accumulation)
2. One-side breakout (trap longs/shorts)
3. Drain back to same level
4. End of day = where it started (premium collected)
<!-- slide -->
![Chart 2: Multi-Day Manipulation](/home/doom/.gemini/antigravity/brain/2c678453-0200-41f9-ac60-733fac3f3a45/uploaded_media_1_1769859905169.png)

**Pattern: HTF Structure with LTF Hunts**
1. Day 1: Sell-off (accumulation at lows)
2. Afternoon rally (trap shorts)
3. Day 2: Higher manipulation structure
4. Late day dump (distribution)
<!-- slide -->
![Chart 3: Extended Range with Sweeps](/home/doom/.gemini/antigravity/brain/2c678453-0200-41f9-ac60-733fac3f3a45/uploaded_media_2_1769859905169.png)

**Pattern: Range Expansion Trap**
1. Morning fake breakout UP
2. Consolidation mid-day
3. Late expansion DOWN
4. Wicks show sweep levels clearly
<!-- slide -->
![Chart 4: Double Manipulation Cycle](/home/doom/.gemini/antigravity/brain/2c678453-0200-41f9-ac60-733fac3f3a45/uploaded_media_3_1769859905169.png)

**Pattern: Power of 3 × 2**
1. Morning dump (manipulation down)
2. Recovery rally (trap shorts, lure longs)
3. Second dump (kill longs)
4. Final rally (distribution)
5. End of day collapse
<!-- slide -->
![Chart 5: V-Recovery Trap](/home/doom/.gemini/antigravity/brain/2c678453-0200-41f9-ac60-733fac3f3a45/uploaded_media_4_1769859905169.png)

**Pattern: Sharp V with Continuation**
1. Morning gap/dump
2. V-bottom recovery (trap shorts)
3. Push to highs (let longs in)
4. Distribution at top
5. Final day rally (second trap)
````

---

## 🔑 Key Observation: Manipulation Times (Indian Market)

From your samples and patterns, here are the **shifting kill zones**:

| Time Window | What Happens | Retail Behavior | Operator Action |
|-------------|--------------|-----------------|-----------------|
| **9:15-9:45** | Opening chaos | FOMO entries | Collect stops |
| **10:30-10:45** | First reversal | Chase breakout | Trap & reverse |
| **12:30-1:00** | Lunch lull | Relax, hold | Setup next hunt |
| **1:30-1:45** | Lunch sweep | Return from lunch | Sharp move to trap |
| **2:30-2:45** | Afternoon trap | Position for close | Final hunt |
| **3:00-3:15** | Closing chaos | Panic management | Last minute pins |

> **Critical Insight**: These times SHIFT based on market context, day of week, and HTF structure.
> The system must LEARN these dynamically, not hard-code them.

---

## 🧠 The Multi-Scale Problem

### Why Single Timeframe Fails

```
ZOOMED IN (5m/15m):
├── You SEE: Current candle patterns, recent structure
├── You MISS: PDH/PDL levels, weekly structure, multi-day OBs
└── TRAP: Enter against HTF trend

ZOOMED OUT (4H/Daily):
├── You SEE: Big picture trend, major levels
├── You MISS: Precise entry zones, LTF sweeps, exact timing
└── TRAP: Wide stops, poor entries
```

### The "Big Picture" Elements You Must Track

```
ALWAYS VISIBLE (regardless of zoom):
├── HTF Trend Direction (Daily/Weekly)
├── Major Liquidity Pools (PDH/PDL/PWH/PWL)
├── Multi-Day Order Blocks (4H/Daily OBs)
├── Session Highs/Lows (Asian, Previous European)
├── Gap Zones (unfilled from previous days)
├── Equal Highs/Lows across multiple days
└── Current Position in Wyckoff Cycle
```

---

## 🏗️ SOLUTION: Multi-Scale Context Engine

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                 MULTI-SCALE CONTEXT ENGINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    CONTEXT LAYERS                           ││
│  │                                                             ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       ││
│  │  │ WEEKLY  │  │  DAILY  │  │  4H     │  │  1H     │       ││
│  │  │ (W1)    │◄─┤ (D1)    │◄─┤         │◄─┤         │       ││
│  │  │         │  │         │  │         │  │         │       ││
│  │  │ PWH/PWL │  │ PDH/PDL │  │ Swing   │  │ OBs     │       ││
│  │  │ Trend   │  │ OBs     │  │ Points  │  │ FVGs    │       ││
│  │  │ Range   │  │ Gaps    │  │ OBs     │  │ LTF Str │       ││
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘       ││
│  │       │            │            │            │             ││
│  │       └────────────┴────────────┴────────────┘             ││
│  │                          │                                  ││
│  │                          ▼                                  ││
│  │              ┌─────────────────────┐                       ││
│  │              │   CONTEXT FUSION    │                       ││
│  │              │                     │                       ││
│  │              │ "Current price is:  │                       ││
│  │              │  - Below daily OB   │                       ││
│  │              │  - Near PDL         │                       ││
│  │              │  - In bearish HTF   │                       ││
│  │              │  - At lunch time"   │                       ││
│  │              └─────────────────────┘                       ││
│  │                          │                                  ││
│  └──────────────────────────┼──────────────────────────────────┘│
│                             ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                 EXECUTION LAYER (15m/5m)                    ││
│  │                                                             ││
│  │  Current Price Analysis + HTF Context = Trade Decision     ││
│  │                                                             ││
│  │  "15m sweep at PDL + Daily bearish + 10:45 time window"    ││
│  │  → High probability long after sweep                        ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📐 Data Structure: Context State

```python
@dataclass
class MultiScaleContext:
    """Always-available big picture context"""
    
    # Weekly Context
    weekly_trend: Literal["BULLISH", "BEARISH", "RANGING"]
    pwh: float  # Previous Week High
    pwl: float  # Previous Week Low
    weekly_ob: Optional[OrderBlock]
    week_range: Tuple[float, float]
    
    # Daily Context
    daily_trend: Literal["BULLISH", "BEARISH", "RANGING"]
    pdh: float  # Previous Day High
    pdl: float  # Previous Day Low
    daily_ob_list: List[OrderBlock]  # Last 5 days OBs
    daily_fvg_list: List[FairValueGap]
    overnight_gap: Optional[Tuple[float, float]]
    daily_atr: float
    
    # 4H Context
    h4_trend: Literal["BULLISH", "BEARISH", "RANGING"]
    h4_swing_high: float
    h4_swing_low: float
    h4_ob_list: List[OrderBlock]
    h4_wyckoff_phase: Literal["ACCUMULATION", "MARKUP", "DISTRIBUTION", "MARKDOWN"]
    
    # 1H Context
    h1_structure: MarketStructure
    h1_last_bos: Optional[Tuple[str, datetime, float]]
    h1_last_choch: Optional[Tuple[str, datetime, float]]
    
    # Session Context
    asian_high: float
    asian_low: float
    opening_range: Tuple[float, float]  # First 15-30 min
    session_high: float
    session_low: float
    
    # Time Context
    current_time: datetime
    time_since_open: timedelta
    kill_zone_active: bool
    time_to_next_kill_zone: timedelta
    
    # Position in Manipulation Cycle
    manipulation_phase: Literal["PRE_HUNT", "HUNTING", "POST_HUNT", "DISTRIBUTION"]
    hunt_completed_today: bool
    direction_of_hunt: Optional[str]
    
    def get_confluence_at_price(self, price: float) -> Dict:
        """Check what HTF elements are near current price"""
        confluence = {
            "near_pdh": abs(price - self.pdh) / self.pdh < 0.002,
            "near_pdl": abs(price - self.pdl) / self.pdl < 0.002,
            "near_pwh": abs(price - self.pwh) / self.pwh < 0.003,
            "near_pwl": abs(price - self.pwl) / self.pwl < 0.003,
            "in_daily_ob": any(ob.contains_price(price) for ob in self.daily_ob_list),
            "in_h4_ob": any(ob.contains_price(price) for ob in self.h4_ob_list),
            "in_fvg": any(fvg.contains_price(price) for fvg in self.daily_fvg_list),
            "at_opening_range_high": abs(price - self.opening_range[1]) / price < 0.001,
            "at_opening_range_low": abs(price - self.opening_range[0]) / price < 0.001,
        }
        return confluence
    
    def htf_bias_aligned(self, direction: str) -> bool:
        """Check if direction aligns with HTF trend"""
        if direction == "LONG":
            return self.weekly_trend != "BEARISH" and self.daily_trend != "BEARISH"
        else:
            return self.weekly_trend != "BULLISH" and self.daily_trend != "BULLISH"
```

---

## ⏰ Dynamic Time Window Learning

### The Problem: Fixed Times Don't Work

Your observation is critical: **10:45, 1:30, 1:45, 2:45** are common BUT they shift.

### Solution: Probabilistic Time Windows

```python
class DynamicTimeWindowLearner:
    """Learn when manipulation typically occurs, not fixed times"""
    
    def __init__(self):
        # Store events by time bucket (5-minute granularity)
        self.sweep_times: Dict[int, List[SweepEvent]] = defaultdict(list)
        self.reversal_times: Dict[int, List[ReversalEvent]] = defaultdict(list)
        self.trap_times: Dict[int, List[TrapEvent]] = defaultdict(list)
        
    def time_to_bucket(self, dt: datetime) -> int:
        """Convert time to 5-minute bucket (0-78 for trading day)"""
        minutes_from_open = (dt.hour - 9) * 60 + dt.minute - 15
        return minutes_from_open // 5
    
    def record_event(self, event_type: str, timestamp: datetime, context: Dict):
        bucket = self.time_to_bucket(timestamp)
        
        if event_type == "SWEEP":
            self.sweep_times[bucket].append(SweepEvent(
                time=timestamp,
                direction=context["direction"],
                pool_type=context["pool_type"],
                resulted_in_reversal=context.get("reversal", False)
            ))
        # ... similar for other events
    
    def get_high_probability_windows(self, event_type: str, min_occurrences: int = 5) -> List[TimeWindow]:
        """Return time windows where event_type frequently occurs"""
        
        if event_type == "SWEEP":
            events = self.sweep_times
        elif event_type == "REVERSAL":
            events = self.reversal_times
        else:
            events = self.trap_times
        
        # Find buckets with significant occurrences
        hot_buckets = [
            (bucket, len(events))
            for bucket, events in events.items()
            if len(events) >= min_occurrences
        ]
        
        # Convert to time windows
        windows = []
        for bucket, count in sorted(hot_buckets, key=lambda x: x[1], reverse=True):
            start_min = bucket * 5 + 15  # Add 9:15 offset
            end_min = start_min + 5
            
            start_time = time(9 + start_min // 60, start_min % 60)
            end_time = time(9 + end_min // 60, end_min % 60)
            
            windows.append(TimeWindow(
                start=start_time,
                end=end_time,
                probability=self._calculate_probability(bucket, events),
                event_type=event_type
            ))
        
        return windows[:5]  # Top 5 windows
    
    def is_kill_zone_now(self, current_time: datetime) -> Tuple[bool, float]:
        """Check if current time is a learned kill zone"""
        bucket = self.time_to_bucket(current_time)
        
        # Check if this bucket has high sweep/reversal activity
        sweep_count = len(self.sweep_times.get(bucket, []))
        adjacent_sweeps = (
            len(self.sweep_times.get(bucket - 1, [])) +
            len(self.sweep_times.get(bucket + 1, []))
        ) / 2
        
        total_sweeps = sum(len(v) for v in self.sweep_times.values())
        
        if total_sweeps == 0:
            # No data yet, use default rules
            return self._default_kill_zone(current_time)
        
        local_concentration = (sweep_count + adjacent_sweeps) / total_sweeps
        is_kill_zone = local_concentration > 0.05  # 5% of all sweeps here
        
        return is_kill_zone, local_concentration
    
    def _default_kill_zone(self, dt: datetime) -> Tuple[bool, float]:
        """Default kill zones before learning kicks in"""
        hour, minute = dt.hour, dt.minute
        
        # Morning hunt
        if 9 <= hour <= 10:
            return True, 0.8
        # Lunch sweep
        if hour == 13 and 30 <= minute <= 45:
            return True, 0.6
        # Afternoon trap
        if hour == 14 and 30 <= minute <= 45:
            return True, 0.5
        
        return False, 0.0
```

---

## 🎯 The "Always Aware" Overlay System

### Concept: Virtual HTF Lines

Even when analyzing 5m charts, the system ALWAYS knows and displays:

```
OVERLAY ON ANY TIMEFRAME:
┌────────────────────────────────────────────────────────────┐
│  Price Chart (5m/15m)                                      │
│                                                            │
│  ═══════════════════════════════════ PWH (45,892)         │
│                                     [Weekly resistance]    │
│                                                            │
│  ──────────────────────────────────── PDH (45,650)        │
│                                     [Daily high - major]   │
│                                                            │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 4H OB Zone            │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ (45,400-45,480)       │
│                                                            │
│        ▲ Current Price: 45,420                             │
│        │                                                   │
│  ──────────────────────────────────── Opening Range Low   │
│                                     (45,380)               │
│                                                            │
│  ──────────────────────────────────── PDL (45,200)        │
│                                     [Daily low - major]    │
│                                                            │
│  ═══════════════════════════════════ PWL (45,050)         │
│                                     [Weekly support]       │
└────────────────────────────────────────────────────────────┘

CONTEXT PANEL (always visible):
┌────────────────────────────────────────────────────────────┐
│ 📊 HTF CONTEXT                                             │
│ ─────────────────────                                      │
│ Weekly: BEARISH (below PWH, tested PWL)                    │
│ Daily:  RANGING (inside PDH-PDL)                           │
│ 4H:     BULLISH (recent CHoCH up)                          │
│ 1H:     BULLISH (HH forming)                               │
│                                                            │
│ ⏰ TIME CONTEXT                                            │
│ ─────────────────────                                      │
│ Current: 10:42 AM (KILL ZONE active - 75% prob)            │
│ Morning hunt: IN PROGRESS                                  │
│ Next safe window: ~11:00 AM                                │
│                                                            │
│ 🎯 NEAREST LEVELS                                          │
│ ─────────────────────                                      │
│ Above: PDH (45,650) - 0.5% away                            │
│ Below: Opening Low (45,380) - 0.1% away ⚠️                 │
│ In:    4H OB (45,400-45,480) ✓                             │
│                                                            │
│ 📈 MANIPULATION PHASE                                      │
│ ─────────────────────                                      │
│ Phase: HUNTING (targeting lows)                            │
│ Retail trapped: LONGS (61% of OI)                          │
│ Likely next: SWEEP Opening Low → Reversal up               │
└────────────────────────────────────────────────────────────┘
```

---

## 🔄 Continuous Context Update Flow

```python
class ContextEngine:
    """Maintains big picture regardless of current view"""
    
    def __init__(self):
        self.context = MultiScaleContext()
        self.time_learner = DynamicTimeWindowLearner()
        
    async def initialize(self, historical_data: Dict[str, pd.DataFrame]):
        """Build initial context from historical data"""
        
        # Weekly context
        weekly_df = historical_data["W1"]
        self.context.pwh = weekly_df.iloc[-2]["high"]
        self.context.pwl = weekly_df.iloc[-2]["low"]
        self.context.weekly_trend = self._determine_trend(weekly_df)
        
        # Daily context
        daily_df = historical_data["D1"]
        self.context.pdh = daily_df.iloc[-2]["high"]
        self.context.pdl = daily_df.iloc[-2]["low"]
        self.context.daily_trend = self._determine_trend(daily_df)
        self.context.daily_ob_list = self._find_obs(daily_df, lookback=5)
        self.context.overnight_gap = self._calculate_gap(daily_df)
        
        # 4H context
        h4_df = historical_data["4H"]
        self.context.h4_trend = self._determine_trend(h4_df)
        self.context.h4_wyckoff_phase = self._detect_wyckoff_phase(h4_df)
        self.context.h4_ob_list = self._find_obs(h4_df, lookback=10)
        
        # Session context (updates intraday)
        self._update_session_context(historical_data["15M"])
    
    def update_with_new_candle(self, candle: Candle, timeframe: str):
        """Update context when new data arrives"""
        
        # Update session highs/lows
        if candle.high > self.context.session_high:
            self.context.session_high = candle.high
        if candle.low < self.context.session_low:
            self.context.session_low = candle.low
        
        # Check for sweeps of key levels
        self._check_level_sweeps(candle)
        
        # Update structure on larger timeframes
        if timeframe in ["1H", "4H", "D1"]:
            self._update_structure(candle, timeframe)
        
        # Update manipulation phase
        self._update_manipulation_phase(candle)
        
        # Update time learner
        self._record_time_events(candle)
    
    def get_context_for_price(self, price: float) -> ContextReport:
        """Get full context report for current price"""
        
        confluence = self.context.get_confluence_at_price(price)
        kill_zone, kz_prob = self.time_learner.is_kill_zone_now(datetime.now())
        
        return ContextReport(
            htf_bias={
                "weekly": self.context.weekly_trend,
                "daily": self.context.daily_trend,
                "h4": self.context.h4_trend
            },
            nearest_liquidity={
                "above": self._find_nearest_above(price),
                "below": self._find_nearest_below(price)
            },
            current_zones=confluence,
            kill_zone_active=kill_zone,
            kill_zone_probability=kz_prob,
            manipulation_phase=self.context.manipulation_phase,
            wyckoff_phase=self.context.h4_wyckoff_phase,
            risk_level=self._calculate_risk_level(price, confluence, kill_zone)
        )
    
    def _calculate_risk_level(self, price, confluence, kill_zone) -> str:
        """Determine current risk level for entry"""
        
        risk_score = 0
        
        # In kill zone = high risk
        if kill_zone:
            risk_score += 40
        
        # Near major levels = high risk for direction against
        if confluence["near_pdh"] or confluence["near_pdl"]:
            risk_score += 30
        
        # Not in any OB = lower probability
        if not confluence["in_daily_ob"] and not confluence["in_h4_ob"]:
            risk_score += 20
        
        # Against HTF trend = high risk
        # (calculated separately per direction)
        
        if risk_score > 60:
            return "HIGH - Wait for better setup"
        elif risk_score > 30:
            return "MEDIUM - Proceed with caution"
        else:
            return "LOW - Good conditions"
```

---

## 📊 Visualization: The "Big Picture Dashboard"

### Always-Visible Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                    🎯 MANIPULATION RADAR                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TODAY'S STATUS                                                 │
│  ═══════════════                                                │
│  Phase: [▓▓▓▓▓░░░░░] HUNTING → Distribution soon               │
│                                                                 │
│  Morning Hunt: ✓ COMPLETED (swept PDL at 9:47)                 │
│  Retail Trap:  LONGS trapped above 45,600                      │
│  Expected:     Move DOWN to 45,200 area                        │
│                                                                 │
│  TIME ANALYSIS                                                  │
│  ═════════════                                                  │
│  Now: 10:42 AM │ Kill Zone: ⚠️ ACTIVE (72%)                     │
│  Safe entry window: 11:00 - 11:30 AM                           │
│  Next kill zone: 1:30 PM (lunch sweep)                         │
│                                                                 │
│  HTF STRUCTURE                                                  │
│  ═════════════                                                  │
│  Weekly: ↘ BEARISH │ Below PWH, testing PWL                    │
│  Daily:  ↔ RANGE   │ PDH: 45,650 │ PDL: 45,200                 │
│  4H:     ↗ BULLISH │ CHoCH up at 10:00 AM                      │
│  1H:     ↗ BULLISH │ HH forming                                 │
│                                                                 │
│  LIQUIDITY MAP                                                  │
│  ═════════════                                                  │
│         ┌──────────────┐                                       │
│  45,892 │ ═══ PWH ═══  │ Monthly level                         │
│  45,650 │ ─── PDH ───  │ ⬅ Equal highs (3x touched)           │
│  45,480 │ ░░░ OB TOP ░ │                                       │
│  45,420 │ ◆ PRICE NOW  │ Inside 4H OB                          │
│  45,400 │ ░░░ OB BOT ░ │                                       │
│  45,380 │ ─ Open Low ─ │ ⬅ Already swept at 9:47              │
│  45,200 │ ─── PDL ───  │                                       │
│  45,050 │ ═══ PWL ═══  │                                       │
│         └──────────────┘                                       │
│                                                                 │
│  PROJECTION                                                     │
│  ══════════                                                     │
│  Scenario A (68%): Retest 4H OB → Rally to PDH sweep           │
│  Scenario B (25%): Fail 4H OB → Drop to PDL                    │
│  Scenario C (7%):  Range day, no clear move                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 How This Solves the "Zoom Problem"

### Before (Traditional Approach)
```
5m chart: See current candles, miss HTF levels
4H chart: See levels, miss entry precision
RESULT: Never have full picture
```

### After (Multi-Scale Context)
```
ANY timeframe + Context Engine:
├── HTF levels ALWAYS overlaid
├── Time context ALWAYS visible
├── Manipulation phase ALWAYS tracked
├── Nearest liquidity ALWAYS calculated
└── Risk level ALWAYS assessed

RESULT: Big picture travels WITH you
```

---

## 🚀 Implementation Priority

### Phase 1: Context Foundation (Week 1-2)
```
□ MultiScaleContext data structure
□ HTF level calculations (PDH/PDL/PWH/PWL)
□ Basic OB detection across timeframes
□ Session high/low tracking
□ Context overlay output (text-based)
```

### Phase 2: Time Learning (Week 2-3)
```
□ DynamicTimeWindowLearner
□ Event recording (sweeps, reversals)
□ Kill zone probability calculation
□ Default time windows with learning override
```

### Phase 3: Manipulation Phase Detection (Week 3-4)
```
□ Wyckoff phase detection
□ Hunt completion tracking
□ Retail trap identification
□ Phase transition prediction
```

### Phase 4: Visualization (Week 4-5)
```
□ Context dashboard output
□ Chart overlay generation
□ Projection scenarios
□ Risk level display
```

---

## 📝 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Context Storage** | In-memory always | Fast access, no DB latency |
| **Update Frequency** | Every candle close | Balance freshness vs compute |
| **HTF Levels** | Pre-calculated daily | Don't recalculate intraday |
| **Time Learning** | 5-minute buckets | Granular enough, not noisy |
| **Overlay Display** | Text + horizontal lines | Works on any chart tool |
| **Phase Detection** | Rule-based first, learn later | Start with your knowledge |

---

> **Core Principle**: The "big picture" is not a timeframe - it's a CONTEXT LAYER that exists independently of what you're viewing. The system maintains this layer always, overlays it on any view, and never lets you trade without it.
