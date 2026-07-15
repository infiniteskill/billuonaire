# 🧬 SELF-EVOLVING RADAR: The Living Organism

> **Purpose**: A system that learns, adapts, and evolves from EVERY failure
> **Goal**: Create a nightmare for market manipulators - a system that NEVER forgets
> **Philosophy**: Document every manipulation tactic, learn from every trap, evolve constantly

---

## 🎯 THE VISION

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║   RADAR is not a tool. It's a LIVING ORGANISM.                        ║
║                                                                        ║
║   It watches.                                                          ║
║   It remembers.                                                        ║
║   It learns.                                                           ║
║   It evolves.                                                          ║
║   It NEVER makes the same mistake twice.                               ║
║                                                                        ║
║   Every time they steal our money:                                     ║
║   → We document the tactic                                             ║
║   → We analyze the pattern                                             ║
║   → We add it to the decision tree                                     ║
║   → Next time, WE see them coming                                      ║
║                                                                        ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## 📋 SYSTEM COMPONENTS

### 1. 📊 Signal Tester (Backtester++)
### 2. 📚 Signal History Database
### 3. 🌅 Pre-Market Analyzer
### 4. 🔮 Next-Day Projector
### 5. 💀 Manipulation Catalog (Every Dirty Trick)
### 6. ❌ Failure Forensics (Why We Lost)
### 7. 🧠 Evolving Decision Tree
### 8. 🔴 Live Signal Organism

---

# PART 1: 📊 SIGNAL TESTER

## Purpose
Test every signal strategy on historical data before going live.
**"Never trust a signal you haven't tested 1000 times."**

## Features

```yaml
Signal Tester:
  modes:
    - BACKTEST: Run on historical data
    - PAPER: Run live but no real money
    - SHADOW: Compare against real trades
    - STRESS: Test on extreme conditions (2020 crash, etc.)
  
  metrics:
    - Win rate by: pattern, time, symbol, phase
    - Drawdown analysis
    - Streak analysis (max wins, max losses)
    - Time-to-target analysis
    - False signal rate
    
  stress_scenarios:
    - Market crash (5%+ drop)
    - Expiry day volatility
    - Gap opens (2%+ gaps)
    - Low volume sessions
    - RBI announcement days
    - Budget day
    - Election result day
```

## Implementation

```python
@dataclass
class SignalTest:
    """Complete signal test run"""
    test_id: str
    strategy_name: str
    date_range: Tuple[date, date]
    symbols: List[str]
    
    # Results
    total_signals: int
    executed_signals: int
    skipped_signals: int  # Due to risk
    
    # Performance
    wins: int
    losses: int
    breakeven: int
    
    win_rate: float
    avg_winner: Decimal
    avg_loser: Decimal
    profit_factor: float
    
    # Risk metrics
    max_drawdown: Decimal
    max_consecutive_losses: int
    recovery_time_avg: int  # candles to recover
    
    # Breakdown
    by_pattern: Dict[str, TestMetrics]
    by_hour: Dict[int, TestMetrics]
    by_day: Dict[str, TestMetrics]  # Monday, Tuesday, etc.
    by_phase: Dict[str, TestMetrics]
    
    # Failure analysis
    failure_reasons: Dict[str, int]  # Reason -> count

class SignalTester:
    """Test signals on historical data"""
    
    def run_backtest(
        self,
        strategy: Strategy,
        candles: Dict[str, List[Candle]],  # symbol -> candles
        date_range: Tuple[date, date]
    ) -> SignalTest:
        """Run full backtest"""
        
        test = SignalTest(...)
        
        for symbol, symbol_candles in candles.items():
            for i in range(100, len(symbol_candles)):
                # Get context up to this point
                historical = symbol_candles[:i]
                future = symbol_candles[i:i+50]  # For outcome checking
                
                # Generate signal
                signal = strategy.generate_signal(historical)
                
                if signal:
                    # Check outcome
                    outcome = self._check_signal_outcome(signal, future)
                    
                    # Record
                    test.total_signals += 1
                    if outcome.was_winner:
                        test.wins += 1
                    else:
                        test.losses += 1
                        # CRITICAL: Document why we lost
                        failure_reason = self._analyze_failure(signal, historical, future)
                        test.failure_reasons[failure_reason] += 1
        
        return test
    
    def run_stress_test(
        self,
        strategy: Strategy,
        scenario: str  # "CRASH", "GAP", "EXPIRY", etc.
    ) -> SignalTest:
        """Test on extreme market conditions"""
        
        # Load specific stress data
        stress_data = self._load_stress_scenario(scenario)
        
        return self.run_backtest(strategy, stress_data, ...)
```

---

# PART 2: 📚 SIGNAL HISTORY DATABASE

## Purpose
Track EVERY signal ever generated, for EVERY stock.
**"Those who cannot remember the past are condemned to repeat it."**

## Schema

```python
@dataclass
class SignalRecord:
    """Permanent record of every signal"""
    id: str
    timestamp: datetime
    
    # Symbol
    symbol: str
    timeframe: str
    
    # Signal details
    direction: str
    entry_zone: Tuple[Decimal, Decimal]
    stop_loss: Decimal
    targets: List[Decimal]
    confidence: float
    confluence_score: float
    
    # Context at generation
    context_snapshot:
        current_price: Decimal
        atr: Decimal
        trend: str
        phase: str
        kill_zone: Optional[str]
        htf_bias: str
    
    # What triggered this signal
    trigger_factors:
        sweep: Optional[Dict]
        ob: Optional[Dict]
        fvg: Optional[Dict]
        structure_event: Optional[Dict]
    
    # Outcome (updated later)
    outcome:
        status: str  # PENDING, TRIGGERED, TARGET_HIT, STOPPED, EXPIRED
        triggered_at: Optional[datetime]
        exit_at: Optional[datetime]
        exit_price: Optional[Decimal]
        pnl_points: Optional[Decimal]
        hit_target: Optional[int]  # Which target (1, 2, 3)
        
    # Failure analysis (if lost)
    failure_analysis:
        reason: Optional[str]
        what_went_wrong: Optional[str]
        what_we_missed: Optional[str]
        lesson_learned: Optional[str]

class SignalHistoryDB:
    """Permanent signal history database"""
    
    def __init__(self, db_path: Path = Path("signal_history.db")):
        self.db_path = db_path
        self._init_db()
    
    def get_signal_history(
        self,
        symbol: str = None,
        from_date: date = None,
        to_date: date = None,
        direction: str = None,
        outcome: str = None
    ) -> List[SignalRecord]:
        """Query signal history with filters"""
        ...
    
    def get_statistics(self, symbol: str) -> Dict:
        """Get statistics for a symbol"""
        return {
            "total_signals": ...,
            "win_rate": ...,
            "best_pattern": ...,
            "worst_pattern": ...,
            "best_time": ...,
            "avg_pnl": ...,
            "common_failures": [...]
        }
    
    def find_similar_setups(
        self,
        current_setup: Dict,
        limit: int = 10
    ) -> List[Tuple[SignalRecord, float]]:
        """Find historically similar setups and their outcomes"""
        # This is POWERFUL - before taking a trade, see what happened
        # in similar situations before
        ...
```

---

# PART 3: 🌅 PRE-MARKET ANALYZER

## Purpose
Analyze BEFORE market opens. Know the battlefield.
**"The battle is won before it is fought."** - Sun Tzu

## Pre-Market Analysis

```python
@dataclass
class PreMarketAnalysis:
    """Analysis done before market opens"""
    symbol: str
    date: date
    generated_at: datetime
    
    # Previous session
    prev_session:
        pdh: Decimal
        pdl: Decimal
        prev_close: Decimal
        range: Decimal
        trend: str
        unfilled_fvgs: List[FairValueGap]
        active_obs: List[OrderBlock]
    
    # Global context
    global_context:
        sgx_nifty: Decimal  # Pre-market indicator
        dow_close: Decimal
        vix: Decimal
        fii_dii_data: Dict  # If available
        
    # Key levels for today
    key_levels:
        pdh: Decimal
        pdl: Decimal
        pwh: Decimal
        pwl: Decimal
        monthly_levels: List[Decimal]
        round_numbers: List[Decimal]
        unfilled_gaps: List[Tuple[Decimal, Decimal]]
    
    # Scenarios
    scenarios:
        gap_up_scenario:
            probability: float
            likely_targets: List[Decimal]
            danger_zones: List[Decimal]
        gap_down_scenario:
            probability: float
            likely_targets: List[Decimal]
            danger_zones: List[Decimal]
        flat_open_scenario:
            probability: float
            likely_sweep_direction: str
    
    # Predictions
    predictions:
        expected_direction: str
        confidence: float
        expected_range: Tuple[Decimal, Decimal]
        likely_sweep_time: str  # "MORNING", "LUNCH", "NONE"
        
    # Watch list
    watch_for:
        - "PDL sweep if gap down"
        - "PDH test if opens above"
        - "OB at 22380 if retraces"

class PreMarketAnalyzer:
    """Generate pre-market analysis"""
    
    def analyze(self, symbol: str, date: date) -> PreMarketAnalysis:
        """Generate pre-market analysis for tomorrow"""
        
        # Get previous day data
        prev_day = self._get_previous_day(symbol, date)
        
        # Get global indicators
        global_ctx = self._get_global_context()
        
        # Calculate key levels
        levels = self._calculate_key_levels(symbol, date)
        
        # Generate scenarios
        scenarios = self._generate_scenarios(prev_day, global_ctx, levels)
        
        # Make predictions
        predictions = self._make_predictions(prev_day, global_ctx, scenarios)
        
        # Create watch list
        watch_list = self._create_watch_list(levels, predictions)
        
        return PreMarketAnalysis(...)
    
    def _generate_scenarios(self, prev_day, global_ctx, levels):
        """Generate possible scenarios for tomorrow"""
        
        scenarios = {}
        
        # Gap up scenario
        if global_ctx.sgx_nifty > prev_day.close:
            gap_size = global_ctx.sgx_nifty - prev_day.close
            scenarios['gap_up'] = {
                'probability': min(0.8, gap_size / 100),
                'likely_targets': self._find_targets_above(prev_day.high, levels),
                'danger_zones': [prev_day.high]  # Potential rejection
            }
        
        # Gap down scenario
        if global_ctx.sgx_nifty < prev_day.close:
            gap_size = prev_day.close - global_ctx.sgx_nifty
            scenarios['gap_down'] = {
                'probability': min(0.8, gap_size / 100),
                'likely_targets': self._find_targets_below(prev_day.low, levels),
                'danger_zones': [prev_day.low]  # Potential support
            }
        
        return scenarios
```

---

# PART 4: 🔮 NEXT-DAY PROJECTOR

## Purpose
Calculate next day's projected direction using ALL factors.
**"Prepare for tomorrow's war tonight."**

## Projection Model

```python
@dataclass
class NextDayProjection:
    """Projection for next trading day"""
    symbol: str
    for_date: date
    generated_at: datetime
    
    # Core projection
    projected_direction: str  # BULLISH, BEARISH, NEUTRAL
    confidence: float
    
    # Range projection
    projected_high: Decimal
    projected_low: Decimal
    projected_close_zone: Tuple[Decimal, Decimal]
    
    # Key decision factors (with weights)
    decision_factors:
        htf_structure: Factor  # weight, score, reasoning
        weekly_bias: Factor
        daily_bias: Factor
        liquidity_above: Factor
        liquidity_below: Factor
        unfilled_fvgs: Factor
        global_context: Factor
        historical_pattern: Factor  # Same setup in past
        time_cycle: Factor  # Monthly/weekly cycles
    
    # Decision tree path
    decision_tree_path: List[str]  # The actual path taken in decision tree
    
    # Projected candle
    projected_candle:
        open_zone: Tuple[Decimal, Decimal]
        high_zone: Tuple[Decimal, Decimal]
        low_zone: Tuple[Decimal, Decimal]
        close_zone: Tuple[Decimal, Decimal]
        is_bullish_probability: float
        
    # Trading plan
    trading_plan:
        primary_bias: str
        entry_zones: List[Tuple[Decimal, Decimal]]
        avoid_zones: List[Tuple[Decimal, Decimal]]
        key_invalidation: Decimal

class NextDayProjector:
    """Project next day's direction and range"""
    
    def __init__(self, decision_tree: DecisionTree, history_db: SignalHistoryDB):
        self.tree = decision_tree
        self.history = history_db
    
    def project(self, symbol: str, for_date: date) -> NextDayProjection:
        """Generate next day projection"""
        
        # Collect all factors
        factors = self._collect_factors(symbol, for_date)
        
        # Run through decision tree
        direction, confidence, path = self.tree.evaluate(factors)
        
        # Calculate projected range
        projected_range = self._calculate_range(symbol, direction, factors)
        
        # Find similar historical setups
        similar = self.history.find_similar_setups(factors)
        
        # Adjust based on historical outcomes
        if similar:
            historical_success = sum(1 for s, _ in similar if s.outcome.status == "TARGET_HIT") / len(similar)
            confidence = (confidence + historical_success) / 2
        
        return NextDayProjection(
            symbol=symbol,
            for_date=for_date,
            projected_direction=direction,
            confidence=confidence,
            decision_tree_path=path,
            ...
        )
```

---

# PART 5: 💀 MANIPULATION CATALOG

## Purpose
Document EVERY dirty trick big players use.
**"Know your enemy."** - Sun Tzu

## THE COMPLETE MANIPULATION ENCYCLOPEDIA

```python
MANIPULATION_CATALOG = {
    
    # ═══════════════════════════════════════════════════════════════
    # CATEGORY 1: STOP HUNTING TACTICS
    # ═══════════════════════════════════════════════════════════════
    
    "STOP_HUNT_001": {
        "name": "Classic Stop Hunt",
        "description": "Price spikes through obvious stop level then reverses",
        "how_they_do_it": [
            "Identify where retail stops are clustered (below swing lows)",
            "Push price through cluster with volume",
            "Absorb all stop orders",
            "Immediately reverse direction"
        ],
        "detection": {
            "wick_beyond_level": True,
            "close_back_inside": True,
            "volume_spike": True,
            "quick_reversal": True
        },
        "our_defense": "Don't place stops at obvious levels. Use ATR-based stops.",
        "times_we_got_hurt": 0,  # Track this
        "learning_applied": False
    },
    
    "STOP_HUNT_002": {
        "name": "Double Stop Hunt",
        "description": "Hunt both lows AND highs in same session",
        "how_they_do_it": [
            "Morning: sweep lows, trap bulls",
            "Lunch: Range / consolidation", 
            "Afternoon: sweep highs, trap bears",
            "End: Close near open (doji day)"
        ],
        "detection": {
            "morning_sweep_low": True,
            "afternoon_sweep_high": True,
            "close_near_open": True
        },
        "our_defense": "Wait for second sweep before entering",
        "times_we_got_hurt": 0,
        "learning_applied": False
    },
    
    "STOP_HUNT_003": {
        "name": "Opening Range Stop Hunt",
        "description": "Fake breakout of opening 15min range",
        "pattern": "OR forms → breakout → immediate reversal → real move opposite",
        "our_defense": "Never trade OR breakout in first 30 minutes",
    },
    
    # ═══════════════════════════════════════════════════════════════
    # CATEGORY 2: FAKE BREAKOUT TACTICS
    # ═══════════════════════════════════════════════════════════════
    
    "FAKEOUT_001": {
        "name": "Resistance Fake Breakout",
        "description": "Price breaks above resistance, then crashes",
        "how_they_do_it": [
            "Let retail see 'breakout'",
            "Wait for breakout buyers to enter",
            "Immediately sell into their buying",
            "Push price below resistance",
            "Trigger breakout buyers' stops"
        ],
        "detection": {
            "break_above_resistance": True,
            "weak_follow_through": True,  # < 2 candles above
            "high_volume_reversal": True
        },
        "our_defense": "Wait for CLOSE above, then RETEST"
    },
    
    "FAKEOUT_002": {
        "name": "Failed Breakout After Hours",
        "description": "Gap up above resistance, then fill gap",
    },
    
    # ═══════════════════════════════════════════════════════════════
    # CATEGORY 3: LIQUIDITY TRAPS
    # ═══════════════════════════════════════════════════════════════
    
    "TRAP_001": {
        "name": "Bull Trap at Highs",
        "description": "New highs made, longs enter, immediate reversal",
    },
    
    "TRAP_002": {
        "name": "Bear Trap at Lows", 
        "description": "New lows made, shorts enter, immediate reversal",
    },
    
    "TRAP_003": {
        "name": "Range Trap",
        "description": "Extended range, breakout both directions, close inside",
    },
    
    "TRAP_004": {
        "name": "News Trap",
        "description": "Spike on news, then complete reversal",
    },
    
    # ═══════════════════════════════════════════════════════════════
    # CATEGORY 4: TIME-BASED MANIPULATION
    # ═══════════════════════════════════════════════════════════════
    
    "TIME_001": {
        "name": "Opening Bell Fakeout",
        "description": "First 15 min direction is opposite to day's real move",
        "frequency": "60-70% of days",
        "our_defense": "NEVER trade first 30 minutes"
    },
    
    "TIME_002": {
        "name": "Lunch Session Trap",
        "description": "Low volume sweep during lunch, reverses before close",
    },
    
    "TIME_003": {
        "name": "Last Hour Squeeze",
        "description": "Aggressive move in last hour to trap overnight holders",
    },
    
    "TIME_004": {
        "name": "Expiry Day Pinning",
        "description": "Price pinned to max pain level on expiry",
    },
    
    # ═══════════════════════════════════════════════════════════════
    # CATEGORY 5: PSYCHOLOGICAL MANIPULATION
    # ═══════════════════════════════════════════════════════════════
    
    "PSYCH_001": {
        "name": "FOMO Candle",
        "description": "Huge candle to trigger fear of missing out",
        "how_they_do_it": "Create 3-4x normal size candle to attract FOMO entries",
        "our_defense": "Never chase. Wait for pullback to OB."
    },
    
    "PSYCH_002": {
        "name": "Panic Candle",
        "description": "Huge opposite candle to shake out weak hands",
    },
    
    "PSYCH_003": {
        "name": "Grind Exhaustion",
        "description": "Slow, steady move to exhaust patient traders",
    },
    
    "PSYCH_004": {
        "name": "False Confidence",
        "description": "Multiple small wins before big loss",
    },
    
    # ═══════════════════════════════════════════════════════════════
    # CATEGORY 6: TECHNICAL MANIPULATION  
    # ═══════════════════════════════════════════════════════════════
    
    "TECH_001": {
        "name": "Indicator Trap",
        "description": "Create perfect technical setup, then fail it",
        "example": "Perfect double bottom → break below both lows"
    },
    
    "TECH_002": {
        "name": "Trendline Fake Break",
        "description": "Break trendline, reverse, continue original trend",
    },
    
    "TECH_003": {
        "name": "Moving Average Game",
        "description": "Multiple crosses of key MA to confuse algos",
    },
}

class ManipulationDetector:
    """Detect active manipulation tactics"""
    
    def __init__(self, catalog: Dict):
        self.catalog = catalog
        self.active_detections: List[Dict] = []
    
    def scan(self, candles: List[Candle], context: Dict) -> List[Dict]:
        """Scan for any manipulation patterns"""
        detections = []
        
        for tactic_id, tactic in self.catalog.items():
            if self._matches_pattern(candles, context, tactic['detection']):
                detections.append({
                    "tactic_id": tactic_id,
                    "name": tactic['name'],
                    "description": tactic['description'],
                    "defense": tactic['our_defense'],
                    "confidence": self._calculate_match_confidence(...)
                })
        
        return detections
    
    def report_hurt(self, tactic_id: str, details: Dict):
        """Record when a tactic hurt us"""
        self.catalog[tactic_id]['times_we_got_hurt'] += 1
        self.catalog[tactic_id]['hurt_history'].append({
            "date": datetime.now(),
            "details": details,
            "lesson": details.get('lesson')
        })
        
        # Trigger learning update
        self._trigger_learning(tactic_id)
```

---

# PART 6: ❌ FAILURE FORENSICS

## Purpose
Analyze EVERY loss. Extract lesson from EVERY failure.
**"A failure unexamined is a lesson unlearned."**

## Failure Categories

```python
class FailureCategory(Enum):
    # Signal quality failures
    LOW_CONFLUENCE = "LOW_CONFLUENCE"      # Took signal with weak confluence
    WRONG_DIRECTION = "WRONG_DIRECTION"    # HTF was actually opposite
    BAD_TIMING = "BAD_TIMING"              # Entered at wrong time (kill zone)
    
    # Execution failures
    EARLY_ENTRY = "EARLY_ENTRY"            # Entered before confirmation
    LATE_ENTRY = "LATE_ENTRY"              # Entered too late, poor R:R
    STOP_TOO_TIGHT = "STOP_TOO_TIGHT"      # Got stopped, then went our way
    STOP_TOO_WIDE = "STOP_TOO_WIDE"        # Too much risk per trade
    
    # Analysis failures
    MISSED_HTF_STRUCTURE = "MISSED_HTF_STRUCTURE"  # Didn't see HTF resistance
    MISSED_LIQUIDITY = "MISSED_LIQUIDITY"          # Didn't see liquidity above/below
    MISSED_FVG = "MISSED_FVG"                      # Didn't see unfilled gap
    WRONG_PHASE = "WRONG_PHASE"                    # Entered in manipulation phase
    
    # Market condition failures
    EXTREME_VOLATILITY = "EXTREME_VOLATILITY"      # ATR spiked unexpectedly
    GAP_DESTROYED = "GAP_DESTROYED"                # Gap ruined the setup
    NEWS_EVENT = "NEWS_EVENT"                      # News moved market
    
    # Manipulation failures
    GOT_STOPPED_HUNTED = "GOT_STOPPED_HUNTED"      # Classic stop hunt
    FELL_FOR_FAKEOUT = "FELL_FOR_FAKEOUT"          # Fake breakout trap
    FOMO_ENTRY = "FOMO_ENTRY"                      # Chased FOMO candle
    
    # Psychological failures
    REVENGE_TRADE = "REVENGE_TRADE"                # Traded to recover loss
    OVERTRADING = "OVERTRADING"                    # Too many trades
    IGNORED_RULES = "IGNORED_RULES"                # Knew better, did anyway

@dataclass
class FailureForensics:
    """Complete failure analysis"""
    signal_id: str
    symbol: str
    timestamp: datetime
    
    # What happened
    entry_price: Decimal
    stop_loss: Decimal
    exit_price: Decimal
    loss_points: Decimal
    
    # Primary failure category
    primary_category: FailureCategory
    secondary_categories: List[FailureCategory]
    
    # Detailed analysis
    what_we_thought: str
    what_actually_happened: str
    what_we_missed: str
    
    # Root cause analysis
    root_cause: str
    contributing_factors: List[str]
    
    # Manipulation detection
    manipulation_detected: Optional[str]  # Tactic ID
    manipulation_details: Optional[Dict]
    
    # Lesson
    lesson_learned: str
    rule_to_add: Optional[str]
    rule_to_strengthen: Optional[str]
    
    # Prevention
    how_to_prevent: str
    detection_improvement: str
    
    # Impact on system
    decision_tree_update: Optional[Dict]  # Changes to make
    new_filter_needed: bool
    filter_description: Optional[str]

class FailureAnalyzer:
    """Analyze every failure in detail"""
    
    def analyze_failure(
        self,
        signal: SignalRecord,
        candles_before: List[Candle],
        candles_after: List[Candle],
        context_at_entry: Dict
    ) -> FailureForensics:
        """Perform complete failure autopsy"""
        
        forensics = FailureForensics(
            signal_id=signal.id,
            symbol=signal.symbol,
            ...
        )
        
        # 1. What did we think would happen?
        forensics.what_we_thought = self._reconstruct_thesis(signal)
        
        # 2. What actually happened?
        forensics.what_actually_happened = self._describe_actual_outcome(candles_after)
        
        # 3. What did we miss?
        forensics.what_we_missed = self._find_missed_signals(candles_before, candles_after)
        
        # 4. Categorize the failure
        forensics.primary_category = self._categorize_failure(
            signal, candles_before, candles_after, context_at_entry
        )
        
        # 5. Check for manipulation
        manipulation = self._check_manipulation(candles_after)
        if manipulation:
            forensics.manipulation_detected = manipulation['tactic_id']
            forensics.manipulation_details = manipulation
        
        # 6. Extract lesson
        forensics.lesson_learned = self._extract_lesson(forensics)
        
        # 7. Suggest decision tree update
        forensics.decision_tree_update = self._suggest_tree_update(forensics)
        
        return forensics
    
    def _find_missed_signals(self, before: List[Candle], after: List[Candle]) -> str:
        """Find what we should have seen but didn't"""
        
        missed = []
        
        # Check for HTF resistance we missed
        if self._had_htf_resistance(before):
            missed.append("HTF resistance directly above entry")
        
        # Check for liquidity we missed
        if self._had_liquidity_above(before) and after[0].high > before[-1].high:
            missed.append("Obvious liquidity above that got swept")
        
        # Check for unfilled FVG we missed
        if unfilled_fvg := self._find_unfilled_fvg(before):
            missed.append(f"Unfilled FVG at {unfilled_fvg}")
        
        # Check time - were we in kill zone?
        if self._was_in_kill_zone(before[-1].timestamp):
            missed.append("Entered during kill zone")
        
        return "; ".join(missed) if missed else "No obvious misses - market was unpredictable"
```

---

# PART 7: 🧠 EVOLVING DECISION TREE

## Purpose
A decision tree that LEARNS and EVOLVES from every outcome.
**"The system gets smarter every single day."**

## Architecture

```python
@dataclass
class DecisionNode:
    """A single node in the decision tree"""
    id: str
    condition: str  # e.g., "htf_bias == 'BULLISH'"
    
    # Branches
    true_branch: Optional[str]  # Node ID or terminal
    false_branch: Optional[str]
    
    # Learning metrics
    times_evaluated: int = 0
    times_true_was_correct: int = 0
    times_false_was_correct: int = 0
    
    # Adaptive thresholds
    threshold: Optional[float] = None  # For numeric conditions
    learned_threshold: Optional[float] = None  # Adjusted by learning
    
    # Confidence
    confidence_when_true: float = 0.5
    confidence_when_false: float = 0.5

@dataclass
class DecisionTree:
    """Self-evolving decision tree"""
    version: int
    nodes: Dict[str, DecisionNode]
    root_node: str
    
    # Performance tracking
    total_evaluations: int = 0
    correct_predictions: int = 0
    
    # Version history
    evolution_history: List[Dict]  # Each change made
    
    def evaluate(self, factors: Dict) -> Tuple[str, float, List[str]]:
        """Evaluate factors through the tree"""
        
        path = []
        current_node_id = self.root_node
        confidence = 1.0
        
        while current_node_id:
            node = self.nodes[current_node_id]
            path.append(f"{node.id}: {node.condition}")
            
            # Evaluate condition
            result = self._evaluate_condition(node.condition, factors)
            
            # Update node metrics
            node.times_evaluated += 1
            
            # Adjust confidence
            if result:
                confidence *= node.confidence_when_true
                current_node_id = node.true_branch
            else:
                confidence *= node.confidence_when_false
                current_node_id = node.false_branch
            
            # Check for terminal node
            if current_node_id in ["BULLISH", "BEARISH", "NEUTRAL"]:
                return current_node_id, confidence, path
        
        return "NEUTRAL", 0.5, path
    
    def learn_from_outcome(self, path: List[str], prediction: str, was_correct: bool):
        """Update tree based on outcome"""
        
        for node_step in path:
            node_id = node_step.split(":")[0]
            node = self.nodes[node_id]
            
            # Update the branch that was taken
            if was_correct:
                if self._took_true_branch(node_step):
                    node.times_true_was_correct += 1
                else:
                    node.times_false_was_correct += 1
        
        # If we were wrong, analyze if we need to:
        # 1. Add a new condition
        # 2. Adjust thresholds
        # 3. Change branch weights
        
        if not was_correct:
            self._evolve_tree(path, prediction)
    
    def _evolve_tree(self, failed_path: List[str], prediction: str):
        """Evolve tree based on failure"""
        
        # Track the evolution
        evolution = {
            "timestamp": datetime.now(),
            "failed_path": failed_path,
            "prediction": prediction,
            "changes": []
        }
        
        # Strategy 1: Adjust confidence weights
        for node_step in failed_path:
            node_id = node_step.split(":")[0]
            node = self.nodes[node_id]
            
            # Reduce confidence in the taken branch
            if self._took_true_branch(node_step):
                old = node.confidence_when_true
                node.confidence_when_true *= 0.95  # Decay
                evolution["changes"].append(f"{node_id}.true_conf: {old:.2f} → {node.confidence_when_true:.2f}")
            else:
                old = node.confidence_when_false
                node.confidence_when_false *= 0.95
                evolution["changes"].append(f"{node_id}.false_conf: {old:.2f} → {node.confidence_when_false:.2f}")
        
        # Strategy 2: If specific failure pattern, add new node
        failure_pattern = self._detect_failure_pattern(failed_path)
        if failure_pattern:
            new_node = self._create_node_for_pattern(failure_pattern)
            self._insert_node(new_node, failed_path[-1])
            evolution["changes"].append(f"Added new node: {new_node.id}")
        
        self.evolution_history.append(evolution)
        self.version += 1

# Initial Decision Tree (will evolve)
INITIAL_TREE = DecisionTree(
    version=1,
    root_node="check_htf_bias",
    nodes={
        "check_htf_bias": DecisionNode(
            id="check_htf_bias",
            condition="htf_bias in ['BULLISH', 'BEARISH']",
            true_branch="check_sweep",
            false_branch="NEUTRAL"
        ),
        "check_sweep": DecisionNode(
            id="check_sweep",
            condition="recent_sweep and sweep_quality > 0.6",
            true_branch="check_phase",
            false_branch="check_ob"
        ),
        "check_phase": DecisionNode(
            id="check_phase",
            condition="phase == 'DISTRIBUTION'",
            true_branch="check_kill_zone",
            false_branch="wait_for_distribution"
        ),
        "check_kill_zone": DecisionNode(
            id="check_kill_zone",
            condition="not in_kill_zone",
            true_branch="generate_signal",
            false_branch="wait_for_safe_time"
        ),
        "check_ob": DecisionNode(
            id="check_ob",
            condition="active_ob and price_near_ob",
            true_branch="check_phase",
            false_branch="NEUTRAL"
        ),
        "generate_signal": DecisionNode(
            id="generate_signal",
            condition="confluence_score > 60",
            true_branch="htf_bias",  # Return the HTF bias as direction
            false_branch="NEUTRAL"
        ),
        "wait_for_distribution": DecisionNode(
            id="wait_for_distribution",
            condition="",
            true_branch="NEUTRAL",
            false_branch="NEUTRAL"
        ),
        "wait_for_safe_time": DecisionNode(
            id="wait_for_safe_time",
            condition="",
            true_branch="NEUTRAL",
            false_branch="NEUTRAL"
        ),
    }
)
```

---

# PART 8: 🔴 LIVE SIGNAL ORGANISM

## The Living System

```python
class RadarOrganism:
    """
    The living, breathing, evolving RADAR system.
    
    This is not a tool. It's an organism.
    It watches the market.
    It learns from every move.
    It evolves every day.
    It NEVER makes the same mistake twice.
    """
    
    def __init__(self):
        # Core components
        self.decision_tree = self._load_tree()
        self.manipulation_catalog = self._load_catalog()
        self.signal_history = SignalHistoryDB()
        self.failure_analyzer = FailureAnalyzer()
        
        # State
        self.active_signals: Dict[str, Signal] = {}
        self.daily_stats = DailyStats()
        
        # Learning
        self.lessons_today: List[str] = []
        self.tree_version = self.decision_tree.version
    
    async def heartbeat(self):
        """The organism's heartbeat - runs every candle"""
        
        while True:
            # 1. Breathe - gather new data
            market_data = await self._breathe()
            
            # 2. Think - analyze through evolved tree
            analysis = self._think(market_data)
            
            # 3. Remember - check against history
            similar_setups = self.signal_history.find_similar_setups(analysis)
            
            # 4. Warn - detect manipulation
            manipulation_warnings = self.manipulation_catalog.scan(market_data)
            
            # 5. Decide - generate or update signals
            signals = self._decide(analysis, similar_setups, manipulation_warnings)
            
            # 6. Act - emit signals
            for signal in signals:
                await self._emit_signal(signal)
            
            # 7. Learn - update from outcomes
            await self._learn_from_outcomes()
            
            # Sleep until next candle
            await asyncio.sleep(60)  # 1 minute
    
    async def _learn_from_outcomes(self):
        """Learn from any signals that just concluded"""
        
        for signal_id, signal in list(self.active_signals.items()):
            outcome = await self._check_outcome(signal)
            
            if outcome:
                # Record outcome
                self.signal_history.record_outcome(signal_id, outcome)
                
                # If we lost, do forensics
                if not outcome.was_winner:
                    forensics = self.failure_analyzer.analyze_failure(signal, ...)
                    
                    # Update manipulation catalog if we got trapped
                    if forensics.manipulation_detected:
                        self.manipulation_catalog.report_hurt(
                            forensics.manipulation_detected,
                            forensics.manipulation_details
                        )
                    
                    # Evolve decision tree
                    if forensics.decision_tree_update:
                        self.decision_tree.apply_update(forensics.decision_tree_update)
                    
                    # Store lesson
                    self.lessons_today.append(forensics.lesson_learned)
                
                # Remove from active
                del self.active_signals[signal_id]
    
    async def end_of_day_evolution(self):
        """Daily evolution ritual"""
        
        # 1. Generate daily report
        report = self._generate_daily_report()
        
        # 2. Analyze all failures
        failures = self.signal_history.get_failures_today()
        patterns = self._find_failure_patterns(failures)
        
        # 3. Update decision tree
        for pattern in patterns:
            self.decision_tree.evolve_for_pattern(pattern)
        
        # 4. Update manipulation catalog
        new_tactics = self._identify_new_tactics(failures)
        for tactic in new_tactics:
            self.manipulation_catalog.add_tactic(tactic)
        
        # 5. Generate next-day projection
        projection = self.projector.project_next_day(...)
        
        # 6. Update pre-market analysis
        premarket = self.premarket_analyzer.analyze(...)
        
        # 7. Log evolution
        logger.info(
            "daily_evolution_complete",
            tree_version=self.decision_tree.version,
            lessons_learned=len(self.lessons_today),
            new_tactics=len(new_tactics),
            accuracy=report.accuracy
        )
        
        # The organism is now smarter than yesterday
```

---

## 📊 SYSTEM EVOLUTION METRICS

```python
@dataclass
class EvolutionMetrics:
    """Track how the system evolves over time"""
    
    # Tree evolution
    tree_versions: List[int]
    nodes_added: int
    nodes_removed: int
    threshold_adjustments: int
    
    # Accuracy over time
    weekly_accuracy: List[float]
    monthly_accuracy: List[float]
    
    # Manipulation learning
    tactics_cataloged: int
    tactics_defended_successfully: int
    new_tactics_discovered: int
    
    # Failure reduction
    failures_by_category: Dict[FailureCategory, List[int]]  # By week
    repeat_failures: int  # Same mistake twice
    
    # Signal quality
    average_confluence: float
    signals_above_80_confluence: int
```

---

## ✅ ACCEPTANCE CRITERIA

- [ ] Signal Tester backtests on 1+ year of data
- [ ] Signal History tracks every signal ever generated
- [ ] Pre-Market Analyzer runs before 9:00 AM
- [ ] Next-Day Projector provides direction + range
- [ ] Manipulation Catalog has 50+ documented tactics
- [ ] Failure Forensics analyzes every loss within 24 hours
- [ ] Decision Tree evolves after each failure
- [ ] Live Organism runs 24/7 during market hours
- [ ] System gets measurably smarter each week
- [ ] Never makes the same mistake twice

---

> **THE DREAM**: Every time they steal our money, we get smarter.
> Every trap they set, we learn to see.
> Every manipulation they run, we add to our catalog.
> 
> Eventually, we see them coming before they even start.
> 
> **That's the nightmare we create for them.**
