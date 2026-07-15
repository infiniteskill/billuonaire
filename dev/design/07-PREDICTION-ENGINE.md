# 🔮 Prediction Engine Service Design

> **Service**: `prediction-engine`
> **Purpose**: Generate probabilistic projections for future price movement
> **Independence**: Consumes detections, context; produces scenarios

---

## 🎯 Responsibilities

1. Generate future price scenarios (bullish, bearish, neutral)
2. Calculate probability for each scenario
3. Project price paths with confidence bands
4. Learn from outcomes to improve accuracy
5. Concatenate predictions to existing data for visualization

---

## 📐 API Contract

### REST Endpoints

```yaml
GET /api/v1/projection/{symbol}:
  parameters:
    symbol: string (required)
    timeframe: string (default: "15m")
    horizon_candles: int (default: 20)  # How many candles ahead
  response:
    symbol: "NIFTY 50"
    timeframe: "15m"
    current_price: 22450.50
    current_time: "2025-01-31T12:30:00+05:30"
    horizon_time: "2025-01-31T15:30:00+05:30"
    
    # Main prediction
    primary_scenario:
      direction: "BULLISH"
      probability: 0.65
      target: 22550.00
      stop_zone: 22380.00
      reasoning:
        - "Bullish sweep at 10:45 (PDL taken)"
        - "OB at 22400 holding"
        - "HTF bias aligned (4H bullish)"
    
    # All scenarios
    scenarios:
      - name: "BULLISH_CONTINUATION"
        probability: 0.45
        path:
          - timestamp: "2025-01-31T12:45:00+05:30"
            projected_close: 22460.00
            confidence_high: 22480.00
            confidence_low: 22440.00
          - timestamp: "2025-01-31T13:00:00+05:30"
            projected_close: 22490.00
            confidence_high: 22520.00
            confidence_low: 22460.00
          # ... more candles
        target: 22550.00
        reasoning: ["OB retest complete", "Structure bullish"]
        
      - name: "BULLISH_OB_BOUNCE"
        probability: 0.20
        path: [...]
        target: 22480.00
        reasoning: ["Return to OB first", "Then move up"]
        
      - name: "BEARISH_REVERSAL"
        probability: 0.25
        path: [...]
        target: 22300.00
        reasoning: ["HTF supply above", "Possible distribution"]
        
      - name: "RANGING"
        probability: 0.10
        path: [...]
        target: null
        reasoning: ["Lunch session", "Low probability move"]
    
    # Confidence bands (for visualization)
    confidence_bands:
      68_percent:  # 1 standard deviation
        upper: [22460, 22475, 22495, ...]
        lower: [22440, 22420, 22400, ...]
      95_percent:  # 2 standard deviations
        upper: [22480, 22510, 22550, ...]
        lower: [22420, 22380, 22330, ...]
    
    # Concatenated data for charting
    chart_data:
      historical:
        - timestamp: "2025-01-31T12:00:00+05:30"
          open: 22430, high: 22455, low: 22420, close: 22445
        - timestamp: "2025-01-31T12:15:00+05:30"
          open: 22445, high: 22460, low: 22440, close: 22450
      projected:  # Dotted line on chart
        - timestamp: "2025-01-31T12:45:00+05:30"
          projected_close: 22460
          confidence_high: 22480
          confidence_low: 22440
          is_projection: true
        # ... continues

POST /api/v1/projection/outcome:
  description: Record actual outcome for learning
  body:
    prediction_id: "pred_abc123"
    actual_outcome:
      direction: "BULLISH"
      actual_target_hit: true
      actual_high: 22565.00
      actual_low: 22395.00
  response:
    accuracy_update:
      previous_accuracy: 0.62
      new_accuracy: 0.63
      prediction_was_correct: true
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   PREDICTION-ENGINE SERVICE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    API LAYER (FastAPI)                       ││
│  │  /projection/{symbol}  /projection/outcome                   ││
│  └───────────────────────────┬─────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │                  PREDICTION MANAGER                          ││
│  │                                                              ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       ││
│  │  │ Scenario     │  │ Path         │  │ Confluence   │       ││
│  │  │ Generator    │  │ Projector    │  │ Scorer       │       ││
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       ││
│  │         │                 │                 │                ││
│  │  ┌──────▼─────────────────▼─────────────────▼──────────────┐││
│  │  │                 MARKOV STATE MACHINE                     │││
│  │  │  Current State → Transition Probabilities → Next State  │││
│  │  └──────────────────────────────────────────────────────────┘││
│  │                                                              ││
│  │  ┌───────────────────────────────────────────────────────┐  ││
│  │  │              OUTCOME TRACKER                           │  ││
│  │  │  Records predictions, compares to reality, learns      │  ││
│  │  └───────────────────────────────────────────────────────┘  ││
│  │                                                              ││
│  └──────────────────────────────────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │                    INPUT AGGREGATOR                          ││
│  │                                                              ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       ││
│  │  │ From         │  │ From         │  │ From         │       ││
│  │  │ Detection    │  │ Context      │  │ Learning     │       ││
│  │  │ Engine       │  │ Engine       │  │ Engine       │       ││
│  │  │              │  │              │  │              │       ││
│  │  │ - Sweeps     │  │ - Phase      │  │ - Time probs │       ││
│  │  │ - OBs        │  │ - HTF bias   │  │ - Pattern    │       ││
│  │  │ - FVGs       │  │ - Kill zone  │  │   accuracy   │       ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘       ││
│  │                                                              ││
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
from typing import List, Optional, Dict
from enum import Enum
import uuid

class ScenarioType(Enum):
    BULLISH_CONTINUATION = "BULLISH_CONTINUATION"
    BULLISH_OB_BOUNCE = "BULLISH_OB_BOUNCE"
    BULLISH_SWEEP_REVERSAL = "BULLISH_SWEEP_REVERSAL"
    BEARISH_CONTINUATION = "BEARISH_CONTINUATION"
    BEARISH_OB_REJECTION = "BEARISH_OB_REJECTION"
    BEARISH_SWEEP_REVERSAL = "BEARISH_SWEEP_REVERSAL"
    RANGING = "RANGING"
    VOLATILE_CHOP = "VOLATILE_CHOP"

class ManipulationPhase(Enum):
    ACCUMULATION = "ACCUMULATION"
    MANIPULATION = "MANIPULATION"
    DISTRIBUTION = "DISTRIBUTION"
    POST_DISTRIBUTION = "POST_DISTRIBUTION"

@dataclass
class ProjectedCandle:
    """A single projected future candle"""
    timestamp: datetime
    projected_open: Decimal
    projected_high: Decimal
    projected_low: Decimal
    projected_close: Decimal
    confidence_high: Decimal  # Upper bound of confidence interval
    confidence_low: Decimal   # Lower bound of confidence interval
    confidence_level: float = 0.68  # Default 68% (1 std dev)
    is_projection: bool = True

@dataclass
class Scenario:
    """A possible future price scenario"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: ScenarioType
    direction: str  # BULLISH, BEARISH, NEUTRAL
    probability: float
    path: List[ProjectedCandle]
    target: Optional[Decimal]
    stop_zone: Optional[Decimal]
    reasoning: List[str]
    confluence_score: float  # 0-100
    
    def __post_init__(self):
        assert 0 <= self.probability <= 1, "Probability must be 0-1"

@dataclass
class ConfidenceBand:
    """Confidence interval for projections"""
    confidence_level: float  # 0.68, 0.95, etc.
    upper_band: List[Decimal]
    lower_band: List[Decimal]
    timestamps: List[datetime]

@dataclass
class Projection:
    """Complete projection with all scenarios"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    timeframe: str
    generated_at: datetime
    current_price: Decimal
    horizon_candles: int
    horizon_time: datetime
    
    # Primary (most likely) scenario
    primary_scenario: Scenario
    
    # All scenarios with probabilities
    scenarios: List[Scenario]
    
    # Confidence bands
    confidence_bands: Dict[str, ConfidenceBand]
    
    # Chart-ready data
    historical_candles: List[Candle]
    projected_candles: List[ProjectedCandle]
    
    # Tracking
    outcome_recorded: bool = False
    outcome: Optional[Dict] = None
    prediction_was_correct: Optional[bool] = None
    
    def validate(self) -> bool:
        """Ensure probabilities sum to ~1"""
        total_prob = sum(s.probability for s in self.scenarios)
        return 0.99 <= total_prob <= 1.01

@dataclass
class PredictionInput:
    """All inputs needed for prediction"""
    symbol: str
    timeframe: str
    current_price: Decimal
    
    # From detection-engine
    recent_sweeps: List[Dict]
    active_order_blocks: List[Dict]
    active_fvgs: List[Dict]
    trap_chains: List[Dict]
    
    # From context-engine
    current_phase: ManipulationPhase
    htf_bias: str
    kill_zone_active: bool
    kill_zone_name: Optional[str]
    time_danger_level: float
    
    # From structure-analyzer
    current_trend: str
    last_bos: Optional[Dict]
    last_choch: Optional[Dict]
    fibonacci_state: Dict
    
    # From learning-engine
    time_probabilities: Dict[str, float]
    pattern_success_rates: Dict[str, float]
```

---

## 🔧 Implementation

### MarkovStateMachine

```python
from collections import defaultdict
from typing import Dict, List, Tuple
import random

class MarkovStateMachine:
    """
    Markov chain for state transitions.
    
    States represent manipulation phases, transitions show what happens next.
    Learns from historical outcomes.
    """
    
    STATES = [
        "HUNTING",          # Sweeping liquidity
        "POST_HUNT",        # Just swept, looking for reaction
        "TRENDING_UP",      # Clear bullish move
        "TRENDING_DOWN",    # Clear bearish move
        "OB_RETEST",        # Returning to order block
        "RANGING",          # No clear direction
        "DISTRIBUTION",     # Smart money exiting
        "VOLATILE",         # Chaotic price action
    ]
    
    def __init__(self):
        # Transition counts: from_state -> to_state -> count
        self.transitions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Initialize with prior knowledge (ICT principles)
        self._initialize_priors()
    
    def _initialize_priors(self):
        """Set up initial transition probabilities based on ICT knowledge"""
        
        # After HUNTING, usually POST_HUNT (70%) or TRENDING (20%)
        self.transitions["HUNTING"]["POST_HUNT"] = 70
        self.transitions["HUNTING"]["TRENDING_UP"] = 10
        self.transitions["HUNTING"]["TRENDING_DOWN"] = 10
        self.transitions["HUNTING"]["VOLATILE"] = 10
        
        # After POST_HUNT, usually OB_RETEST (40%) or TRENDING (40%)
        self.transitions["POST_HUNT"]["OB_RETEST"] = 40
        self.transitions["POST_HUNT"]["TRENDING_UP"] = 20
        self.transitions["POST_HUNT"]["TRENDING_DOWN"] = 20
        self.transitions["POST_HUNT"]["RANGING"] = 15
        self.transitions["POST_HUNT"]["VOLATILE"] = 5
        
        # After OB_RETEST, usually TRENDING (60%)
        self.transitions["OB_RETEST"]["TRENDING_UP"] = 30
        self.transitions["OB_RETEST"]["TRENDING_DOWN"] = 30
        self.transitions["OB_RETEST"]["RANGING"] = 25
        self.transitions["OB_RETEST"]["VOLATILE"] = 15
        
        # TRENDING tends to continue (60%) or distribute (30%)
        self.transitions["TRENDING_UP"]["TRENDING_UP"] = 60
        self.transitions["TRENDING_UP"]["DISTRIBUTION"] = 20
        self.transitions["TRENDING_UP"]["RANGING"] = 15
        self.transitions["TRENDING_UP"]["HUNTING"] = 5
        
        self.transitions["TRENDING_DOWN"]["TRENDING_DOWN"] = 60
        self.transitions["TRENDING_DOWN"]["DISTRIBUTION"] = 20
        self.transitions["TRENDING_DOWN"]["RANGING"] = 15
        self.transitions["TRENDING_DOWN"]["HUNTING"] = 5
        
        # RANGING often leads to HUNTING (40%)
        self.transitions["RANGING"]["HUNTING"] = 40
        self.transitions["RANGING"]["RANGING"] = 30
        self.transitions["RANGING"]["TRENDING_UP"] = 15
        self.transitions["RANGING"]["TRENDING_DOWN"] = 15
    
    def learn_transition(self, from_state: str, to_state: str):
        """Record an observed transition"""
        self.transitions[from_state][to_state] += 1
    
    def get_transition_probabilities(self, current_state: str) -> Dict[str, float]:
        """Get probability distribution for next state"""
        counts = self.transitions[current_state]
        total = sum(counts.values())
        
        if total == 0:
            # Uniform distribution if no data
            return {state: 1/len(self.STATES) for state in self.STATES}
        
        return {
            state: count / total 
            for state, count in counts.items()
        }
    
    def predict_sequence(self, current_state: str, steps: int) -> List[Tuple[str, float]]:
        """Predict most likely sequence of states"""
        sequence = []
        state = current_state
        cumulative_prob = 1.0
        
        for _ in range(steps):
            probs = self.get_transition_probabilities(state)
            
            # Most likely next state
            next_state = max(probs.items(), key=lambda x: x[1])
            state = next_state[0]
            cumulative_prob *= next_state[1]
            
            sequence.append((state, cumulative_prob))
        
        return sequence
```

### ScenarioGenerator

```python
class ScenarioGenerator:
    """
    Generate possible future scenarios based on current market state.
    
    Uses Markov transitions + confluence scoring + ICT principles.
    """
    
    def __init__(self, markov: MarkovStateMachine):
        self.markov = markov
    
    def generate_scenarios(self, input: PredictionInput) -> List[Scenario]:
        """Generate all possible scenarios with probabilities"""
        scenarios = []
        
        # Determine current Markov state
        current_state = self._infer_current_state(input)
        
        # Get transition probabilities
        next_state_probs = self.markov.get_transition_probabilities(current_state)
        
        # Generate scenario for each likely next state
        for next_state, base_prob in next_state_probs.items():
            if base_prob < 0.05:  # Skip very unlikely states
                continue
            
            scenario = self._build_scenario(
                input=input,
                target_state=next_state,
                base_probability=base_prob
            )
            
            if scenario:
                scenarios.append(scenario)
        
        # Normalize probabilities to sum to 1
        total_prob = sum(s.probability for s in scenarios)
        for scenario in scenarios:
            scenario.probability /= total_prob
        
        return sorted(scenarios, key=lambda s: s.probability, reverse=True)
    
    def _infer_current_state(self, input: PredictionInput) -> str:
        """Infer current Markov state from input signals"""
        
        # Check for recent sweep
        if input.recent_sweeps and input.recent_sweeps[0].get('age_minutes', 999) < 30:
            sweep = input.recent_sweeps[0]
            if sweep.get('age_minutes', 999) < 5:
                return "HUNTING"
            else:
                return "POST_HUNT"
        
        # Check for OB proximity
        if input.active_order_blocks:
            for ob in input.active_order_blocks:
                distance_pct = abs(ob['level'] - float(input.current_price)) / float(input.current_price)
                if distance_pct < 0.002:  # Within 0.2%
                    return "OB_RETEST"
        
        # Check trend from structure
        if input.current_trend == "BULLISH" and input.last_bos:
            return "TRENDING_UP"
        elif input.current_trend == "BEARISH" and input.last_bos:
            return "TRENDING_DOWN"
        
        # Check for distribution (CHoCH after trend)
        if input.last_choch:
            return "DISTRIBUTION"
        
        # Default to ranging
        return "RANGING"
    
    def _build_scenario(
        self, 
        input: PredictionInput,
        target_state: str,
        base_probability: float
    ) -> Optional[Scenario]:
        """Build a complete scenario for a target state"""
        
        # Determine direction and type
        if target_state in ["TRENDING_UP", "POST_HUNT"] and input.htf_bias == "BULLISH":
            scenario_type = ScenarioType.BULLISH_CONTINUATION
            direction = "BULLISH"
        elif target_state == "OB_RETEST" and input.htf_bias == "BULLISH":
            scenario_type = ScenarioType.BULLISH_OB_BOUNCE
            direction = "BULLISH"
        elif target_state in ["TRENDING_DOWN", "POST_HUNT"] and input.htf_bias == "BEARISH":
            scenario_type = ScenarioType.BEARISH_CONTINUATION
            direction = "BEARISH"
        elif target_state == "OB_RETEST" and input.htf_bias == "BEARISH":
            scenario_type = ScenarioType.BEARISH_OB_REJECTION
            direction = "BEARISH"
        elif target_state == "RANGING":
            scenario_type = ScenarioType.RANGING
            direction = "NEUTRAL"
        elif target_state == "DISTRIBUTION":
            # Distribution is often a reversal
            direction = "BEARISH" if input.current_trend == "BULLISH" else "BULLISH"
            scenario_type = ScenarioType.BEARISH_SWEEP_REVERSAL if direction == "BEARISH" else ScenarioType.BULLISH_SWEEP_REVERSAL
        else:
            scenario_type = ScenarioType.VOLATILE_CHOP
            direction = "NEUTRAL"
        
        # Calculate confluence score
        confluence_score = self._calculate_confluence(input, direction)
        
        # Adjust probability based on confluence
        adjusted_probability = base_probability * (0.5 + confluence_score / 200)
        
        # Calculate target
        target = self._calculate_target(input, direction)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(input, direction, scenario_type)
        
        return Scenario(
            type=scenario_type,
            direction=direction,
            probability=adjusted_probability,
            path=[],  # Will be filled by PathProjector
            target=target,
            stop_zone=self._calculate_stop(input, direction),
            reasoning=reasoning,
            confluence_score=confluence_score
        )
    
    def _calculate_confluence(self, input: PredictionInput, direction: str) -> float:
        """Calculate confluence score (0-100)"""
        score = 0.0
        
        # HTF alignment (+25)
        if input.htf_bias == direction:
            score += 25
        elif input.htf_bias == "NEUTRAL":
            score += 10
        
        # Recent sweep in our direction (+20)
        if input.recent_sweeps:
            sweep = input.recent_sweeps[0]
            if sweep.get('direction') == direction:
                score += 20
        
        # OB in our direction (+15)
        if input.active_order_blocks:
            for ob in input.active_order_blocks:
                if ob.get('type') == f"{direction}_OB":
                    score += 15
                    break
        
        # FVG in our direction (+10)
        if input.active_fvgs:
            for fvg in input.active_fvgs:
                if fvg.get('type') == f"{direction}_FVG":
                    score += 10
                    break
        
        # Good time (not in danger zone) (+15)
        if input.time_danger_level < 0.5:
            score += 15
        elif input.time_danger_level > 0.8:
            score -= 10
        
        # Pattern success rate (+15)
        pattern_key = f"{input.current_phase}_{direction}"
        if pattern_key in input.pattern_success_rates:
            success_rate = input.pattern_success_rates[pattern_key]
            score += success_rate * 15
        
        return min(100, max(0, score))
    
    def _calculate_target(self, input: PredictionInput, direction: str) -> Optional[Decimal]:
        """Calculate price target based on direction and levels"""
        
        # Use Fibonacci extensions or opposing liquidity
        if direction == "BULLISH":
            # Target: Next swing high or FVG above or OB above
            targets = []
            
            # Fibonacci -27.2% extension
            if 'extensions' in input.fibonacci_state:
                ext = input.fibonacci_state['extensions'].get('-27.2%')
                if ext:
                    targets.append(Decimal(str(ext)))
            
            if targets:
                return min(targets)  # Nearest target
        
        elif direction == "BEARISH":
            targets = []
            
            if 'extensions' in input.fibonacci_state:
                ext = input.fibonacci_state['extensions'].get('-27.2%')
                if ext:
                    targets.append(Decimal(str(ext)))
            
            if targets:
                return max(targets)  # Nearest target (lowest)
        
        return None
    
    def _calculate_stop(self, input: PredictionInput, direction: str) -> Optional[Decimal]:
        """Calculate stop loss zone"""
        
        if direction == "BULLISH":
            # Stop below recent swing low or OB low
            if input.active_order_blocks:
                ob = input.active_order_blocks[0]
                return Decimal(str(ob.get('low', 0))) - Decimal("10")
        
        elif direction == "BEARISH":
            if input.active_order_blocks:
                ob = input.active_order_blocks[0]
                return Decimal(str(ob.get('high', 0))) + Decimal("10")
        
        return None
    
    def _generate_reasoning(
        self, 
        input: PredictionInput, 
        direction: str,
        scenario_type: ScenarioType
    ) -> List[str]:
        """Generate human-readable reasoning"""
        reasons = []
        
        # HTF alignment
        if input.htf_bias == direction:
            reasons.append(f"HTF bias aligned ({input.htf_bias})")
        
        # Recent sweep
        if input.recent_sweeps:
            sweep = input.recent_sweeps[0]
            reasons.append(f"Sweep at {sweep.get('level')} ({sweep.get('age_minutes')}min ago)")
        
        # OB
        if input.active_order_blocks:
            ob = input.active_order_blocks[0]
            reasons.append(f"{ob.get('type')} at {ob.get('level')} active")
        
        # Fibonacci
        if input.fibonacci_state.get('current_price_in_ote'):
            reasons.append("Price in OTE zone (61.8%-79%)")
        
        # Time
        if input.kill_zone_active:
            reasons.append(f"Kill zone ACTIVE: {input.kill_zone_name}")
        elif input.time_danger_level > 0.7:
            reasons.append(f"⚠️ High manipulation risk ({input.time_danger_level:.0%})")
        
        return reasons
```

### PathProjector

```python
from decimal import Decimal
import math

class PathProjector:
    """
    Project price paths for scenarios.
    
    Generates candle-by-candle projections with confidence bands.
    """
    
    def __init__(self, atr: Decimal):
        """
        Args:
            atr: Average True Range for volatility estimation
        """
        self.atr = atr
    
    def project_path(
        self,
        scenario: Scenario,
        current_price: Decimal,
        current_time: datetime,
        candle_interval_minutes: int,
        num_candles: int
    ) -> List[ProjectedCandle]:
        """Project price path for a scenario"""
        
        path = []
        price = current_price
        time = current_time
        
        for i in range(num_candles):
            # Calculate expected move per candle
            move_per_candle = self._calculate_expected_move(
                scenario=scenario,
                candle_number=i,
                total_candles=num_candles,
                current_price=price
            )
            
            # Apply move
            new_price = price + move_per_candle
            
            # Calculate confidence interval
            uncertainty = self._calculate_uncertainty(
                candle_number=i,
                scenario_probability=scenario.probability
            )
            
            # Project OHLC
            time = time + timedelta(minutes=candle_interval_minutes)
            
            if scenario.direction == "BULLISH":
                projected_candle = ProjectedCandle(
                    timestamp=time,
                    projected_open=price,
                    projected_high=new_price + self.atr * Decimal("0.3"),
                    projected_low=price - self.atr * Decimal("0.2"),
                    projected_close=new_price,
                    confidence_high=new_price + uncertainty,
                    confidence_low=new_price - uncertainty
                )
            elif scenario.direction == "BEARISH":
                projected_candle = ProjectedCandle(
                    timestamp=time,
                    projected_open=price,
                    projected_high=price + self.atr * Decimal("0.2"),
                    projected_low=new_price - self.atr * Decimal("0.3"),
                    projected_close=new_price,
                    confidence_high=new_price + uncertainty,
                    confidence_low=new_price - uncertainty
                )
            else:  # NEUTRAL/RANGING
                projected_candle = ProjectedCandle(
                    timestamp=time,
                    projected_open=price,
                    projected_high=price + self.atr * Decimal("0.4"),
                    projected_low=price - self.atr * Decimal("0.4"),
                    projected_close=price + move_per_candle,
                    confidence_high=price + self.atr,
                    confidence_low=price - self.atr
                )
            
            path.append(projected_candle)
            price = new_price
        
        return path
    
    def _calculate_expected_move(
        self,
        scenario: Scenario,
        candle_number: int,
        total_candles: int,
        current_price: Decimal
    ) -> Decimal:
        """Calculate expected price move for this candle"""
        
        if not scenario.target:
            # No target, assume small moves
            return Decimal("0")
        
        total_move = scenario.target - current_price
        
        # Non-linear path: faster at start, slower at end (or vice versa)
        if scenario.direction == "BULLISH":
            # Start fast, slow down (profit taking)
            progress = (candle_number + 1) / total_candles
            weight = 1 - (progress ** 2)  # Square decay
        elif scenario.direction == "BEARISH":
            # Start fast, slow down
            progress = (candle_number + 1) / total_candles
            weight = 1 - (progress ** 2)
        else:
            weight = 0.5
        
        # Normalize weights
        move = (total_move / total_candles) * Decimal(str(weight * 2))
        
        return move
    
    def _calculate_uncertainty(
        self,
        candle_number: int,
        scenario_probability: float
    ) -> Decimal:
        """Calculate uncertainty (confidence interval width)"""
        
        # Uncertainty increases with:
        # 1. Distance into future (sqrt of candle number)
        # 2. Lower scenario probability
        
        base_uncertainty = self.atr * Decimal("0.5")
        
        time_factor = Decimal(str(math.sqrt(candle_number + 1)))
        probability_factor = Decimal(str(2 - scenario_probability))  # Lower prob = wider
        
        return base_uncertainty * time_factor * probability_factor
```

---

## 📤 Events Published

```python
@dataclass
class ProjectionEvent:
    event_type: str = "prediction.scenario.new"
    symbol: str
    timeframe: str
    primary_direction: str
    primary_probability: float
    confluence_score: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class OutcomeEvent:
    event_type: str = "prediction.outcome.recorded"
    prediction_id: str
    was_correct: bool
    accuracy_delta: float
    timestamp: datetime = field(default_factory=datetime.now)
```

---

## 📊 Visualization Output

The prediction engine provides data formatted for chart concatenation:

```python
def get_chart_data(projection: Projection) -> Dict:
    """
    Return data ready for charting.
    
    Historical candles as solid lines.
    Projected candles as dotted/transparent lines.
    Confidence bands as shaded areas.
    """
    return {
        "historical": [
            {
                "x": candle.timestamp.isoformat(),
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close),
                "color": "#2196F3",  # Blue for historical
                "style": "solid"
            }
            for candle in projection.historical_candles
        ],
        "projected": [
            {
                "x": pc.timestamp.isoformat(),
                "open": float(pc.projected_open),
                "high": float(pc.projected_high),
                "low": float(pc.projected_low),
                "close": float(pc.projected_close),
                "color": "#4CAF50" if projection.primary_scenario.direction == "BULLISH" else "#F44336",
                "style": "dashed",
                "opacity": 0.6
            }
            for pc in projection.projected_candles
        ],
        "confidence_bands": {
            "68%": {
                "upper": [float(b.confidence_high) for b in projection.projected_candles],
                "lower": [float(b.confidence_low) for b in projection.projected_candles],
                "color": "rgba(76, 175, 80, 0.2)"
            }
        },
        "annotations": [
            {
                "x": projection.projected_candles[-1].timestamp.isoformat(),
                "y": float(projection.primary_scenario.target or 0),
                "text": f"Target: {projection.primary_scenario.target}",
                "type": "target"
            },
            {
                "x": projection.projected_candles[0].timestamp.isoformat(),
                "y": float(projection.primary_scenario.stop_zone or 0),
                "text": f"Stop: {projection.primary_scenario.stop_zone}",
                "type": "stop"
            }
        ]
    }
```

---

## ✅ Acceptance Criteria

- [ ] Generates multiple scenarios with probabilities summing to 1
- [ ] Primary scenario clearly identified with highest probability
- [ ] Path projection includes OHLC for each future candle
- [ ] Confidence bands widen with time horizon
- [ ] Confluence score calculated from multiple factors
- [ ] Human-readable reasoning for each scenario
- [ ] Outcome tracking and accuracy measurement
- [ ] Markov model learns from outcomes
- [ ] Chart-ready data format for visualization
- [ ] All prices use Decimal
- [ ] Comprehensive testing
