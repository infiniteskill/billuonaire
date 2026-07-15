# 🚨 Signal Generator Service Design

> **Service**: `signal-generator`
> **Purpose**: Generate actionable trade signals with confidence scoring
> **Independence**: Consumes all analysis, produces final signals

---

## 🎯 Responsibilities

1. Aggregate all detection and context data
2. Apply confluence rules
3. Generate trade signals with confidence
4. Provide entry, target, and stop levels
5. Track signal outcomes

---

## 📐 API Contract

```yaml
GET /api/v1/signals/{symbol}:
  parameters:
    symbol: string
    timeframe: string
    min_confidence: float (default: 0.6)
  response:
    symbol: "NIFTY 50"
    active_signals:
      - id: "sig_abc123"
        direction: "LONG"
        confidence: 0.78
        entry_zone: [22380, 22400]
        stop_loss: 22340
        targets: [22480, 22550]
        risk_reward: 2.5
        reasoning:
          - "Bullish sweep at PDL (quality: 0.85)"
          - "OB at 22390 (quality: 0.82)"
          - "HTF aligned BULLISH"
          - "DISTRIBUTION phase"
        generated_at: "2025-01-31T11:15:00+05:30"
        expires_at: "2025-01-31T15:30:00+05:30"
        status: "ACTIVE"

POST /api/v1/signals/{id}/outcome:
  body:
    hit_target: 1  # Which target was hit (0 = none, 1 = TP1, 2 = TP2)
    hit_stop: false
    actual_exit: 22485.00
    actual_pnl_points: 95
  response:
    recorded: true
    updated_accuracy: 0.67
```

---

## 📊 Data Models

```python
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Tuple
from enum import Enum
import uuid

class SignalDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class SignalStatus(Enum):
    PENDING = "PENDING"      # Generated but not active
    ACTIVE = "ACTIVE"        # Price in entry zone
    TRIGGERED = "TRIGGERED"  # Entry executed
    TARGET_HIT = "TARGET_HIT"
    STOPPED_OUT = "STOPPED_OUT"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

@dataclass
class Signal:
    """A trade signal"""
    id: str = field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:8]}")
    symbol: str
    timeframe: str
    
    # Direction
    direction: SignalDirection
    
    # Levels
    entry_zone: Tuple[Decimal, Decimal]  # (low, high)
    stop_loss: Decimal
    targets: List[Decimal]  # TP1, TP2, etc.
    
    # Confidence
    confidence: float  # 0-1
    confluence_score: float  # 0-100
    
    # Reasoning
    factors: List[str]  # What triggered this signal
    warnings: List[str]  # Risk factors
    
    # Timing
    generated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    triggered_at: Optional[datetime] = None
    
    # Status
    status: SignalStatus = SignalStatus.PENDING
    
    # Outcome tracking
    outcome_recorded: bool = False
    actual_exit: Optional[Decimal] = None
    actual_pnl: Optional[Decimal] = None
    
    @property
    def entry_mid(self) -> Decimal:
        return (self.entry_zone[0] + self.entry_zone[1]) / 2
    
    @property
    def risk_points(self) -> Decimal:
        """Points at risk (entry to stop)"""
        if self.direction == SignalDirection.LONG:
            return self.entry_mid - self.stop_loss
        else:
            return self.stop_loss - self.entry_mid
    
    @property
    def reward_points(self) -> Decimal:
        """Points to first target"""
        if not self.targets:
            return Decimal("0")
        
        if self.direction == SignalDirection.LONG:
            return self.targets[0] - self.entry_mid
        else:
            return self.entry_mid - self.targets[0]
    
    @property
    def risk_reward(self) -> float:
        """Risk/Reward ratio"""
        if self.risk_points == 0:
            return 0.0
        return float(self.reward_points / self.risk_points)

@dataclass
class ConfluentFactor:
    """A factor contributing to signal confluence"""
    name: str
    weight: float  # How much this factor contributes
    present: bool
    details: str
    score: float  # 0-1, quality of this factor
```

---

## 🔧 Implementation

### ConfluenceCalculator

```python
class ConfluenceCalculator:
    """Calculate signal confluence from multiple factors"""
    
    # Factor weights (must sum to 100)
    FACTORS = {
        "htf_bias": 20,           # Higher timeframe alignment
        "sweep_quality": 20,      # Recent sweep quality
        "ob_present": 15,         # Order block at entry
        "fvg_present": 10,        # Fair value gap
        "structure_aligned": 15,  # BOS/CHoCH alignment
        "time_safe": 10,          # Not in danger zone
        "phase_correct": 10,      # Distribution phase
    }
    
    def calculate(
        self,
        direction: SignalDirection,
        context: FullContext,
        sweeps: List[Dict],
        orderblocks: List[OrderBlock],
        fvgs: List[FairValueGap],
        structure_events: List[Dict]
    ) -> Tuple[float, List[ConfluentFactor]]:
        """
        Calculate confluence score and list contributing factors.
        
        Returns: (score 0-100, list of factors)
        """
        factors = []
        total_score = 0.0
        
        # 1. HTF Bias (20%)
        htf_aligned = context.mtf.primary_bias.value == direction.value
        htf_score = context.mtf.alignment_score if htf_aligned else 0
        factors.append(ConfluentFactor(
            name="HTF Bias",
            weight=self.FACTORS["htf_bias"],
            present=htf_aligned,
            details=f"{context.mtf.primary_bias.value} ({context.mtf.alignment_score:.0%})",
            score=htf_score
        ))
        total_score += htf_score * self.FACTORS["htf_bias"]
        
        # 2. Sweep Quality (20%)
        recent_sweep = self._find_aligned_sweep(sweeps, direction)
        sweep_score = recent_sweep.get('quality', 0) if recent_sweep else 0
        factors.append(ConfluentFactor(
            name="Sweep",
            weight=self.FACTORS["sweep_quality"],
            present=recent_sweep is not None,
            details=f"Quality: {sweep_score:.2f}" if recent_sweep else "No aligned sweep",
            score=sweep_score
        ))
        total_score += sweep_score * self.FACTORS["sweep_quality"]
        
        # 3. Order Block (15%)
        ob = self._find_aligned_ob(orderblocks, direction)
        ob_score = ob.quality_score if ob else 0
        factors.append(ConfluentFactor(
            name="Order Block",
            weight=self.FACTORS["ob_present"],
            present=ob is not None,
            details=f"OB at {ob.low}-{ob.high}" if ob else "No aligned OB",
            score=ob_score
        ))
        total_score += ob_score * self.FACTORS["ob_present"]
        
        # 4. FVG (10%)
        fvg = self._find_aligned_fvg(fvgs, direction)
        fvg_score = 0.7 if fvg else 0  # FVGs don't have quality score
        factors.append(ConfluentFactor(
            name="Fair Value Gap",
            weight=self.FACTORS["fvg_present"],
            present=fvg is not None,
            details=f"FVG at {fvg.low}-{fvg.high}" if fvg else "No aligned FVG",
            score=fvg_score
        ))
        total_score += fvg_score * self.FACTORS["fvg_present"]
        
        # 5. Structure (15%)
        structure_aligned = self._check_structure(structure_events, direction)
        structure_score = 0.8 if structure_aligned else 0
        factors.append(ConfluentFactor(
            name="Structure",
            weight=self.FACTORS["structure_aligned"],
            present=structure_aligned,
            details="BOS aligned" if structure_aligned else "No aligned structure",
            score=structure_score
        ))
        total_score += structure_score * self.FACTORS["structure_aligned"]
        
        # 6. Time Safety (10%)
        time_safe = not context.time.avoid_entry
        time_score = 1 - context.time.danger_level if time_safe else 0
        factors.append(ConfluentFactor(
            name="Time",
            weight=self.FACTORS["time_safe"],
            present=time_safe,
            details=f"Danger: {context.time.danger_level:.0%}",
            score=time_score
        ))
        total_score += time_score * self.FACTORS["time_safe"]
        
        # 7. Phase (10%)
        phase_correct = context.phase.current_phase == ManipulationPhase.DISTRIBUTION
        phase_score = context.phase.confidence if phase_correct else 0.2
        factors.append(ConfluentFactor(
            name="Phase",
            weight=self.FACTORS["phase_correct"],
            present=phase_correct,
            details=f"{context.phase.current_phase.value} ({context.phase.confidence:.0%})",
            score=phase_score
        ))
        total_score += phase_score * self.FACTORS["phase_correct"]
        
        return total_score, factors
    
    def _find_aligned_sweep(self, sweeps, direction):
        if not sweeps:
            return None
        
        sweep_type = "BULLISH_SWEEP" if direction == SignalDirection.LONG else "BEARISH_SWEEP"
        for sweep in sweeps:
            if sweep.get('type') == sweep_type:
                return sweep
        return None
    
    def _find_aligned_ob(self, obs, direction):
        if not obs:
            return None
        
        ob_type = OBType.BULLISH if direction == SignalDirection.LONG else OBType.BEARISH
        for ob in obs:
            if ob.type == ob_type and not ob.mitigated:
                return ob
        return None
    
    def _find_aligned_fvg(self, fvgs, direction):
        if not fvgs:
            return None
        
        fvg_type = FVGType.BULLISH if direction == SignalDirection.LONG else FVGType.BEARISH
        for fvg in fvgs:
            if fvg.type == fvg_type and not fvg.filled:
                return fvg
        return None
    
    def _check_structure(self, events, direction):
        if not events:
            return False
        
        recent = events[-1] if events else None
        if not recent:
            return False
        
        if recent.get('type') == 'BOS':
            return recent.get('direction', '').upper() == direction.value
        
        return False
```

### SignalGenerator

```python
class SignalGenerator:
    """Generate trade signals from analysis"""
    
    def __init__(self, min_confluence: float = 50):
        self.min_confluence = min_confluence
        self.confluence_calc = ConfluenceCalculator()
    
    def generate(
        self,
        symbol: str,
        timeframe: str,
        current_price: Decimal,
        context: FullContext,
        sweeps: List[Dict],
        orderblocks: List[OrderBlock],
        fvgs: List[FairValueGap],
        structure_events: List[Dict],
        atr: Decimal
    ) -> Optional[Signal]:
        """Generate a signal if conditions are met"""
        
        # Check both directions
        for direction in [SignalDirection.LONG, SignalDirection.SHORT]:
            confluence, factors = self.confluence_calc.calculate(
                direction=direction,
                context=context,
                sweeps=sweeps,
                orderblocks=orderblocks,
                fvgs=fvgs,
                structure_events=structure_events
            )
            
            if confluence >= self.min_confluence:
                signal = self._build_signal(
                    symbol=symbol,
                    timeframe=timeframe,
                    direction=direction,
                    current_price=current_price,
                    confluence=confluence,
                    factors=factors,
                    context=context,
                    orderblocks=orderblocks,
                    atr=atr
                )
                
                # Only generate if risk/reward is acceptable
                if signal.risk_reward >= 1.5:
                    return signal
        
        return None
    
    def _build_signal(
        self,
        symbol: str,
        timeframe: str,
        direction: SignalDirection,
        current_price: Decimal,
        confluence: float,
        factors: List[ConfluentFactor],
        context: FullContext,
        orderblocks: List[OrderBlock],
        atr: Decimal
    ) -> Signal:
        """Build a complete signal with levels"""
        
        # Find entry zone (OB or current price area)
        entry_zone = self._calculate_entry_zone(direction, current_price, orderblocks, atr)
        
        # Calculate stop loss
        stop_loss = self._calculate_stop(direction, entry_zone, orderblocks, atr)
        
        # Calculate targets
        targets = self._calculate_targets(direction, entry_zone, stop_loss, atr)
        
        # Extract reasoning
        reasoning = [f.details for f in factors if f.present]
        warnings = [f.details for f in factors if not f.present and f.weight >= 15]
        
        # Add time warning if relevant
        if context.time.danger_level > 0.5:
            warnings.append(f"⚠️ Elevated danger: {context.time.danger_level:.0%}")
        
        return Signal(
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            entry_zone=entry_zone,
            stop_loss=stop_loss,
            targets=targets,
            confidence=confluence / 100,
            confluence_score=confluence,
            factors=reasoning,
            warnings=warnings,
            expires_at=datetime.now() + timedelta(hours=4)  # Signal valid for 4 hours
        )
    
    def _calculate_entry_zone(
        self, 
        direction: SignalDirection,
        current_price: Decimal,
        orderblocks: List[OrderBlock],
        atr: Decimal
    ) -> Tuple[Decimal, Decimal]:
        """Calculate optimal entry zone"""
        
        # Try to find an OB for entry
        ob_type = OBType.BULLISH if direction == SignalDirection.LONG else OBType.BEARISH
        aligned_obs = [ob for ob in orderblocks if ob.type == ob_type and not ob.mitigated]
        
        if aligned_obs:
            # Use the most recent, highest quality OB
            best_ob = max(aligned_obs, key=lambda ob: ob.quality_score)
            return (best_ob.low, best_ob.high)
        
        # Default: zone around current price
        zone_size = atr * Decimal("0.5")
        
        if direction == SignalDirection.LONG:
            return (current_price - zone_size, current_price)
        else:
            return (current_price, current_price + zone_size)
    
    def _calculate_stop(
        self,
        direction: SignalDirection,
        entry_zone: Tuple[Decimal, Decimal],
        orderblocks: List[OrderBlock],
        atr: Decimal
    ) -> Decimal:
        """Calculate stop loss level"""
        buffer = atr * Decimal("0.5")
        
        if direction == SignalDirection.LONG:
            # Stop below entry zone low
            return entry_zone[0] - buffer
        else:
            # Stop above entry zone high
            return entry_zone[1] + buffer
    
    def _calculate_targets(
        self,
        direction: SignalDirection,
        entry_zone: Tuple[Decimal, Decimal],
        stop_loss: Decimal,
        atr: Decimal
    ) -> List[Decimal]:
        """Calculate target levels (TP1, TP2, TP3)"""
        entry_mid = (entry_zone[0] + entry_zone[1]) / 2
        risk = abs(entry_mid - stop_loss)
        
        if direction == SignalDirection.LONG:
            return [
                entry_mid + risk * Decimal("1.5"),   # TP1: 1.5R
                entry_mid + risk * Decimal("2.5"),   # TP2: 2.5R
                entry_mid + risk * Decimal("4.0"),   # TP3: 4R
            ]
        else:
            return [
                entry_mid - risk * Decimal("1.5"),
                entry_mid - risk * Decimal("2.5"),
                entry_mid - risk * Decimal("4.0"),
            ]
```

---

## 📤 Events Published

```python
@dataclass
class SignalEvent:
    event_type: str = "signal.new"
    symbol: str
    direction: str
    confidence: float
    entry_zone: Tuple[Decimal, Decimal]
    risk_reward: float
    timestamp: datetime

@dataclass
class SignalOutcomeEvent:
    event_type: str = "signal.outcome"
    signal_id: str
    was_winner: bool
    actual_pnl: Decimal
    timestamp: datetime
```

---

## ✅ Acceptance Criteria

- [ ] Calculates confluence from 7 factors
- [ ] Generates signals only above minimum confluence
- [ ] Provides clear entry zones based on OBs
- [ ] Calculates appropriate stop loss
- [ ] Calculates multiple targets (1.5R, 2.5R, 4R)
- [ ] Tracks signal outcomes
- [ ] Only generates signals with R:R >= 1.5
- [ ] Includes reasoning and warnings
