# 🔍 Detection Engine Service Design

> **Service**: `detection-engine`
> **Purpose**: Detect Order Blocks, FVGs, Traps, and Manipulation Patterns
> **Independence**: Consumes candles + structure, produces detections

---

## 🎯 Responsibilities

1. Detect Order Blocks (bullish and bearish)
2. Detect Fair Value Gaps (imbalances)
3. Track OB/FVG mitigation
4. Detect trap chains and manipulation patterns
5. Score detection quality
6. Emit detection events

---

## 📐 API Contract

```yaml
GET /api/v1/orderblocks/{symbol}:
  parameters:
    symbol: string
    timeframe: string (default: "15m")
    include_mitigated: bool (default: false)
  response:
    symbol: "NIFTY 50"
    timeframe: "15m"
    orderblocks:
      - type: "BULLISH"
        high: 22420.00
        low: 22390.00
        formation_time: "2025-01-31T10:30:00+05:30"
        displacement_atr: 2.3
        quality: 0.85
        mitigated: false
        touches: 0
        
GET /api/v1/fvgs/{symbol}:
  response:
    fvgs:
      - type: "BULLISH"
        high: 22450.00
        low: 22430.00
        size: 20.00
        formation_time: "2025-01-31T11:00:00+05:30"
        fill_percent: 0.35
        fully_filled: false

GET /api/v1/traps/{symbol}:
  response:
    active_traps:
      - type: "BULL_TRAP"
        entry_zone: [22480, 22500]
        trapped_at: "2025-01-31T10:45:00+05:30"
        severity: "HIGH"
        pattern: "SWEEP_REVERSAL"

POST /api/v1/analyze:
  body:
    symbol: string
    candles: [...]
    swings: [...]
  response:
    orderblocks: [...]
    fvgs: [...]
    traps: [...]
    manipulation_score: 0.72
```

---

## 📊 Data Models

```python
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Tuple
from enum import Enum

class OBType(Enum):
    BULLISH = "BULLISH"   # Last bearish candle before bullish move
    BEARISH = "BEARISH"   # Last bullish candle before bearish move

class FVGType(Enum):
    BULLISH = "BULLISH"   # Gap up (C3 low > C1 high)
    BEARISH = "BEARISH"   # Gap down (C3 high < C1 low)

class TrapType(Enum):
    BULL_TRAP = "BULL_TRAP"
    BEAR_TRAP = "BEAR_TRAP"
    STOP_HUNT = "STOP_HUNT"
    FAKE_BREAKOUT = "FAKE_BREAKOUT"
    LIQUIDITY_GRAB = "LIQUIDITY_GRAB"

@dataclass
class OrderBlock:
    """Order Block detection"""
    type: OBType
    high: Decimal
    low: Decimal
    formation_candle: Candle
    formation_index: int
    formation_time: datetime
    
    # Quality metrics
    displacement_atr: float  # Size of displacement in ATR multiples
    quality_score: float     # 0-1
    
    # State tracking
    valid: bool = True
    mitigated: bool = False
    mitigated_at: Optional[datetime] = None
    touch_count: int = 0
    
    @property
    def midpoint(self) -> Decimal:
        return (self.high + self.low) / 2
    
    @property
    def size(self) -> Decimal:
        return self.high - self.low

@dataclass
class FairValueGap:
    """Fair Value Gap (imbalance)"""
    type: FVGType
    high: Decimal           # Top of gap
    low: Decimal            # Bottom of gap
    size: Decimal           # Gap size
    formation_time: datetime
    formation_candles: Tuple[int, int, int]  # Indices of 3 candles
    
    # Fill tracking
    filled: bool = False
    filled_at: Optional[datetime] = None
    fill_percentage: float = 0.0
    
    @property
    def midpoint(self) -> Decimal:
        return (self.high + self.low) / 2

@dataclass
class Trap:
    """Manipulation trap pattern"""
    type: TrapType
    entry_zone: Tuple[Decimal, Decimal]  # (low, high) of trap zone
    trigger_time: datetime
    trigger_candle_index: int
    
    # Pattern details
    pattern_name: str
    involved_candles: List[int]
    
    # Severity
    severity: str  # LOW, MEDIUM, HIGH
    estimated_trapped_percent: float  # Rough estimate
    
    # Resolution
    resolved: bool = False
    resolution_direction: Optional[str] = None  # TRAPPED_BULLS_EXIT, etc.

@dataclass
class ManipulationChain:
    """Sequence of related manipulation events"""
    events: List[Dict]  # Sweeps, traps, OBs in sequence
    start_time: datetime
    phase: str  # ACCUMULATION, MANIPULATION, DISTRIBUTION
    confidence: float
```

---

## 🔧 Implementation

### OrderBlockDetector

```python
class OrderBlockDetector:
    """
    Detect Order Blocks per ICT methodology.
    
    Bullish OB: Last bearish candle before bullish displacement
    Bearish OB: Last bullish candle before bearish displacement
    """
    
    def __init__(self, min_displacement_atr: float = 1.5, lookback: int = 5):
        self.min_displacement = min_displacement_atr
        self.lookback = lookback
    
    def detect(self, candles: List[Candle], atr: Decimal) -> List[OrderBlock]:
        orderblocks = []
        
        for i in range(self.lookback, len(candles) - 3):
            # Check for bullish OB (displacement up)
            displacement = self._check_bullish_displacement(candles, i, atr)
            if displacement:
                ob = self._find_bullish_ob(candles, i, displacement, atr)
                if ob:
                    orderblocks.append(ob)
            
            # Check for bearish OB (displacement down)
            displacement = self._check_bearish_displacement(candles, i, atr)
            if displacement:
                ob = self._find_bearish_ob(candles, i, displacement, atr)
                if ob:
                    orderblocks.append(ob)
        
        return self._filter_overlapping(orderblocks)
    
    def _check_bullish_displacement(
        self, candles: List[Candle], start_idx: int, atr: Decimal
    ) -> Optional[float]:
        """Check if there's bullish displacement starting at index"""
        
        # Need 2-3 strong bullish candles
        total_move = Decimal("0")
        bullish_count = 0
        
        for i in range(3):
            if start_idx + i >= len(candles):
                break
            c = candles[start_idx + i]
            if c.is_bullish and c.body > atr * Decimal("0.5"):
                total_move += c.close - c.open
                bullish_count += 1
        
        if bullish_count >= 2 and total_move >= atr * Decimal(str(self.min_displacement)):
            return float(total_move / atr)
        
        return None
    
    def _find_bullish_ob(
        self, candles: List[Candle], displacement_start: int, 
        displacement_atr: float, atr: Decimal
    ) -> Optional[OrderBlock]:
        """Find the last bearish candle before displacement"""
        
        # Look backwards for bearish candle
        for i in range(displacement_start - 1, max(0, displacement_start - self.lookback), -1):
            c = candles[i]
            if c.is_bearish:
                quality = self._calculate_quality(c, displacement_atr, atr)
                
                return OrderBlock(
                    type=OBType.BULLISH,
                    high=c.high,
                    low=c.low,
                    formation_candle=c,
                    formation_index=i,
                    formation_time=c.timestamp,
                    displacement_atr=displacement_atr,
                    quality_score=quality
                )
        
        return None
    
    def _check_bearish_displacement(self, candles, start_idx, atr):
        """Check for bearish displacement"""
        total_move = Decimal("0")
        bearish_count = 0
        
        for i in range(3):
            if start_idx + i >= len(candles):
                break
            c = candles[start_idx + i]
            if c.is_bearish and c.body > atr * Decimal("0.5"):
                total_move += c.open - c.close
                bearish_count += 1
        
        if bearish_count >= 2 and total_move >= atr * Decimal(str(self.min_displacement)):
            return float(total_move / atr)
        
        return None
    
    def _find_bearish_ob(self, candles, displacement_start, displacement_atr, atr):
        """Find the last bullish candle before bearish displacement"""
        
        for i in range(displacement_start - 1, max(0, displacement_start - self.lookback), -1):
            c = candles[i]
            if c.is_bullish:
                quality = self._calculate_quality(c, displacement_atr, atr)
                
                return OrderBlock(
                    type=OBType.BEARISH,
                    high=c.high,
                    low=c.low,
                    formation_candle=c,
                    formation_index=i,
                    formation_time=c.timestamp,
                    displacement_atr=displacement_atr,
                    quality_score=quality
                )
        
        return None
    
    def _calculate_quality(self, candle: Candle, displacement_atr: float, atr: Decimal) -> float:
        quality = 0.0
        
        # Larger displacement = better OB (+40%)
        quality += min(displacement_atr / 3, 0.4)
        
        # Candle body size relative to ATR (+30%)
        body_ratio = float(candle.body / atr)
        quality += min(body_ratio / 2, 0.3)
        
        # Low wick ratio (clean candle) (+30%)
        if candle.range > 0:
            body_percent = float(candle.body / candle.range)
            quality += body_percent * 0.3
        
        return min(1.0, quality)
    
    def _filter_overlapping(self, obs: List[OrderBlock]) -> List[OrderBlock]:
        """Remove overlapping OBs, keep highest quality"""
        if not obs:
            return obs
        
        # Sort by quality descending
        sorted_obs = sorted(obs, key=lambda x: x.quality_score, reverse=True)
        filtered = []
        
        for ob in sorted_obs:
            overlaps = False
            for existing in filtered:
                if self._overlaps(ob, existing):
                    overlaps = True
                    break
            
            if not overlaps:
                filtered.append(ob)
        
        return filtered
    
    def _overlaps(self, ob1: OrderBlock, ob2: OrderBlock) -> bool:
        """Check if two OBs overlap"""
        return not (ob1.high < ob2.low or ob1.low > ob2.high)
    
    def check_mitigation(self, ob: OrderBlock, candle: Candle) -> bool:
        """Check if candle mitigates (touches) the OB"""
        if ob.mitigated:
            return True
        
        touched = False
        if ob.type == OBType.BULLISH:
            # Price must come down to touch bullish OB
            if candle.low <= ob.high:
                touched = True
        else:
            # Price must come up to touch bearish OB
            if candle.high >= ob.low:
                touched = True
        
        if touched:
            ob.touch_count += 1
            if ob.touch_count >= 2:  # Consider mitigated after 2 touches
                ob.mitigated = True
                ob.mitigated_at = candle.timestamp
        
        return ob.mitigated
```

### FVGDetector

```python
class FVGDetector:
    """Detect Fair Value Gaps (imbalances)"""
    
    def __init__(self, min_gap_atr: float = 0.3):
        self.min_gap = min_gap_atr
    
    def detect(self, candles: List[Candle], atr: Decimal) -> List[FairValueGap]:
        fvgs = []
        
        for i in range(2, len(candles)):
            c1, c2, c3 = candles[i-2], candles[i-1], candles[i]
            
            # Bullish FVG: C3 low > C1 high (gap up)
            if c3.low > c1.high:
                gap_size = c3.low - c1.high
                if gap_size >= atr * Decimal(str(self.min_gap)):
                    fvgs.append(FairValueGap(
                        type=FVGType.BULLISH,
                        high=c3.low,
                        low=c1.high,
                        size=gap_size,
                        formation_time=c2.timestamp,
                        formation_candles=(i-2, i-1, i)
                    ))
            
            # Bearish FVG: C3 high < C1 low (gap down)
            if c3.high < c1.low:
                gap_size = c1.low - c3.high
                if gap_size >= atr * Decimal(str(self.min_gap)):
                    fvgs.append(FairValueGap(
                        type=FVGType.BEARISH,
                        high=c1.low,
                        low=c3.high,
                        size=gap_size,
                        formation_time=c2.timestamp,
                        formation_candles=(i-2, i-1, i)
                    ))
        
        return fvgs
    
    def check_fill(self, fvg: FairValueGap, candle: Candle) -> float:
        """Check how much of the FVG has been filled"""
        if fvg.filled:
            return 1.0
        
        gap_size = float(fvg.size)
        
        if fvg.type == FVGType.BULLISH:
            # Price must come DOWN to fill bullish FVG
            if candle.low <= fvg.high:
                penetration = float(fvg.high - candle.low)
                fill_pct = min(penetration / gap_size, 1.0)
                
                if candle.low <= fvg.low:
                    fvg.filled = True
                    fvg.filled_at = candle.timestamp
                    fill_pct = 1.0
                
                fvg.fill_percentage = max(fvg.fill_percentage, fill_pct)
        else:
            # Price must come UP to fill bearish FVG
            if candle.high >= fvg.low:
                penetration = float(candle.high - fvg.low)
                fill_pct = min(penetration / gap_size, 1.0)
                
                if candle.high >= fvg.high:
                    fvg.filled = True
                    fvg.filled_at = candle.timestamp
                    fill_pct = 1.0
                
                fvg.fill_percentage = max(fvg.fill_percentage, fill_pct)
        
        return fvg.fill_percentage
```

### TrapDetector

```python
class TrapDetector:
    """Detect manipulation traps"""
    
    def detect(
        self, 
        candles: List[Candle], 
        sweeps: List[Dict], 
        orderblocks: List[OrderBlock]
    ) -> List[Trap]:
        traps = []
        
        for sweep in sweeps:
            # Sweep that reverses strongly = trap
            trap = self._analyze_sweep_trap(candles, sweep)
            if trap:
                traps.append(trap)
        
        # Failed breakout traps
        traps.extend(self._detect_failed_breakouts(candles))
        
        return traps
    
    def _analyze_sweep_trap(self, candles: List[Candle], sweep: Dict) -> Optional[Trap]:
        """Check if sweep created a trap"""
        
        sweep_idx = sweep.get('candle_index')
        if not sweep_idx or sweep_idx >= len(candles) - 3:
            return None
        
        # Check next 3-5 candles for strong reversal
        reversal_strength = self._measure_reversal(candles, sweep_idx, sweep['direction'])
        
        if reversal_strength > 0.6:
            trap_type = TrapType.BULL_TRAP if sweep['direction'] == 'BEARISH' else TrapType.BEAR_TRAP
            
            return Trap(
                type=trap_type,
                entry_zone=(
                    Decimal(str(sweep.get('level', 0) - 20)),
                    Decimal(str(sweep.get('level', 0) + 20))
                ),
                trigger_time=candles[sweep_idx].timestamp,
                trigger_candle_index=sweep_idx,
                pattern_name="SWEEP_REVERSAL",
                involved_candles=list(range(sweep_idx, min(sweep_idx + 5, len(candles)))),
                severity="HIGH" if reversal_strength > 0.8 else "MEDIUM",
                estimated_trapped_percent=reversal_strength * 0.5
            )
        
        return None
    
    def _measure_reversal(
        self, candles: List[Candle], start_idx: int, sweep_direction: str
    ) -> float:
        """Measure strength of reversal after sweep"""
        
        if start_idx >= len(candles) - 2:
            return 0.0
        
        sweep_candle = candles[start_idx]
        next_candles = candles[start_idx + 1: min(start_idx + 5, len(candles))]
        
        if sweep_direction == "BULLISH":
            # Bullish sweep should lead to bearish reversal for bull trap
            move = sweep_candle.high - min(c.low for c in next_candles)
        else:
            # Bearish sweep should lead to bullish reversal for bear trap
            move = max(c.high for c in next_candles) - sweep_candle.low
        
        # Normalize by sweep range
        range_ref = sweep_candle.range if sweep_candle.range > 0 else Decimal("1")
        strength = float(move / range_ref)
        
        return min(1.0, strength / 3)
    
    def _detect_failed_breakouts(self, candles: List[Candle]) -> List[Trap]:
        """Detect failed breakout patterns"""
        traps = []
        
        # Look for: break above resistance → immediate return below
        for i in range(10, len(candles) - 3):
            # Find potential breakout
            recent_high = max(c.high for c in candles[i-10:i])
            
            if candles[i].high > recent_high:  # Breakout candle
                # Check if next candles fail
                next_3 = candles[i+1:i+4]
                if all(c.close < recent_high for c in next_3):
                    traps.append(Trap(
                        type=TrapType.FAKE_BREAKOUT,
                        entry_zone=(recent_high - Decimal("10"), candles[i].high),
                        trigger_time=candles[i].timestamp,
                        trigger_candle_index=i,
                        pattern_name="FAILED_BREAKOUT_HIGH",
                        involved_candles=list(range(i, i+4)),
                        severity="MEDIUM",
                        estimated_trapped_percent=0.3
                    ))
        
        return traps
```

---

## 📤 Events Published

```python
@dataclass
class OrderBlockEvent:
    event_type: str = "detection.ob.new"
    symbol: str
    timeframe: str
    ob_type: str
    high: Decimal
    low: Decimal
    quality: float
    timestamp: datetime

@dataclass
class FVGEvent:
    event_type: str = "detection.fvg.new"
    symbol: str
    timeframe: str
    fvg_type: str
    high: Decimal
    low: Decimal
    timestamp: datetime

@dataclass
class TrapEvent:
    event_type: str = "detection.trap.alert"
    symbol: str
    trap_type: str
    severity: str
    entry_zone: Tuple[Decimal, Decimal]
    timestamp: datetime
```

---

## ✅ Acceptance Criteria

- [ ] Accurately detects Order Blocks with displacement validation
- [ ] Calculates OB quality scores
- [ ] Detects Fair Value Gaps
- [ ] Tracks FVG fill percentage
- [ ] Identifies trap patterns from sweeps
- [ ] Detects failed breakouts
- [ ] Filters overlapping detections
- [ ] All prices use Decimal
