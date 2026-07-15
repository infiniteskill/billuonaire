# 🌍 Context Engine Service Design

> **Service**: `context-engine`
> **Purpose**: Provide multi-timeframe context, kill zones, and manipulation phases
> **Independence**: Aggregates data from multiple sources for holistic view

---

## 🎯 Responsibilities

1. Multi-timeframe (MTF) bias alignment
2. Time-based context (kill zones, session awareness)
3. Manipulation phase detection (AMD: Accumulation, Manipulation, Distribution)
4. Higher timeframe bias for lower timeframe entries
5. Danger level assessment

---

## 📐 API Contract

```yaml
GET /api/v1/context/{symbol}:
  parameters:
    symbol: string
    timeframe: string (default: "15m")
  response:
    symbol: "NIFTY 50"
    timestamp: "2025-01-31T10:45:00+05:30"
    
    # Multi-timeframe bias
    mtf_bias:
      daily: "BULLISH"
      h4: "BULLISH"
      h1: "NEUTRAL"
      m15: "BEARISH"
      alignment_score: 0.65  # How aligned are TFs
      primary_bias: "BULLISH"  # HTF wins
    
    # Time context
    time_context:
      current_session: "MORNING"
      kill_zone_active: true
      kill_zone_name: "MORNING_HUNT"
      kill_zone_ends_at: "2025-01-31T10:30:00+05:30"
      is_lunch_session: false
      minutes_to_close: 285
      danger_level: 0.85  # High during kill zone
    
    # Manipulation phase
    phase:
      current: "MANIPULATION"
      phase_start: "2025-01-31T09:45:00+05:30"
      confidence: 0.78
      next_expected: "DISTRIBUTION"
      amd_position: "M"  # A, M, or D
    
    # Combined assessment
    overall:
      safe_to_enter: false
      reasoning: ["Kill zone active", "Manipulation phase", "Wait for distribution"]
      entry_quality: 0.25

GET /api/v1/htf-bias/{symbol}:
  parameters:
    symbol: string
    entry_timeframe: string (default: "15m")
  response:
    htf_levels:
      - timeframe: "4H"
        bias: "BULLISH"
        key_level: 22400.00
        level_type: "OB"
      - timeframe: "1D"
        bias: "BULLISH"
        next_target: 22600.00

GET /api/v1/kill-zones:
  response:
    zones:
      - name: "MORNING_HUNT"
        start: "09:15"
        end: "10:30"
        danger_level: 0.9
        description: "Primary manipulation window"
      - name: "POST_HUNT"
        start: "10:30"
        end: "11:00"
        danger_level: 0.5
        description: "OB formation zone"
      # ... more zones
```

---

## 📊 Data Models

```python
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, time
from typing import List, Optional, Dict
from enum import Enum

class TimeframeBias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class ManipulationPhase(Enum):
    ACCUMULATION = "A"    # Building position, range-bound
    MANIPULATION = "M"    # Stop hunt, sweep
    DISTRIBUTION = "D"    # Real move, trend

class SessionName(Enum):
    PRE_MARKET = "PRE_MARKET"
    MORNING_HUNT = "MORNING_HUNT"
    POST_HUNT = "POST_HUNT"
    EXECUTION_1 = "EXECUTION_1"
    LUNCH = "LUNCH"
    LUNCH_SWEEP = "LUNCH_SWEEP"
    EXECUTION_2 = "EXECUTION_2"
    CLOSING_CHAOS = "CLOSING_CHAOS"
    POST_MARKET = "POST_MARKET"

@dataclass
class KillZone:
    """Time-based kill zone definition"""
    name: SessionName
    start_time: time
    end_time: time
    danger_level: float  # 0-1
    description: str
    typical_behavior: str

@dataclass
class TimeframeBiasInfo:
    """Bias for a single timeframe"""
    timeframe: str
    bias: TimeframeBias
    trend_strength: float  # 0-1
    key_level: Optional[Decimal]
    level_type: Optional[str]  # OB, FVG, SWING
    last_structure_event: Optional[str]  # BOS, CHoCH

@dataclass
class MTFContext:
    """Multi-timeframe context"""
    biases: Dict[str, TimeframeBiasInfo]  # TF -> bias info
    alignment_score: float  # 0-1, how aligned are TFs
    primary_bias: TimeframeBias  # HTF bias
    conflicting_timeframes: List[str]

@dataclass
class TimeContext:
    """Current time-based context"""
    current_time: datetime
    current_session: SessionName
    
    # Kill zone
    kill_zone_active: bool
    kill_zone_name: Optional[str]
    kill_zone_ends_at: Optional[datetime]
    
    # Special times
    is_lunch: bool
    is_opening: bool
    is_closing: bool
    
    # Risk assessment
    danger_level: float  # 0-1
    minutes_to_close: int
    
    # Recommendations
    avoid_entry: bool
    reason: Optional[str]

@dataclass
class PhaseContext:
    """AMD phase context"""
    current_phase: ManipulationPhase
    phase_started: datetime
    phase_duration_minutes: int
    confidence: float
    
    # Predictions
    next_expected_phase: ManipulationPhase
    expected_transition_time: Optional[datetime]
    
    # Signals
    phase_signals: List[str]

@dataclass
class FullContext:
    """Complete market context"""
    symbol: str
    timeframe: str
    generated_at: datetime
    
    mtf: MTFContext
    time: TimeContext
    phase: PhaseContext
    
    # Overall assessment
    safe_to_enter: bool
    entry_quality: float  # 0-1
    warnings: List[str]
    recommendations: List[str]
```

---

## 🔧 Implementation

### KillZoneManager

```python
class KillZoneManager:
    """Manage Indian market kill zones"""
    
    # Indian market kill zones
    ZONES = [
        KillZone(
            name=SessionName.MORNING_HUNT,
            start_time=time(9, 15),
            end_time=time(10, 30),
            danger_level=0.9,
            description="Primary manipulation window - sweeps and traps",
            typical_behavior="Stop hunts, false breakouts, liquidity grabs"
        ),
        KillZone(
            name=SessionName.POST_HUNT,
            start_time=time(10, 30),
            end_time=time(11, 0),
            danger_level=0.5,
            description="Order blocks forming, direction establishing",
            typical_behavior="OBs form, FVGs created, structure built"
        ),
        KillZone(
            name=SessionName.EXECUTION_1,
            start_time=time(11, 0),
            end_time=time(12, 30),
            danger_level=0.3,
            description="SAFEST entry window",
            typical_behavior="Trend moves, OB reactions, clean price action"
        ),
        KillZone(
            name=SessionName.LUNCH,
            start_time=time(12, 30),
            end_time=time(13, 30),
            danger_level=0.4,
            description="Low volume consolidation",
            typical_behavior="Range-bound, whipsaws, avoid new entries"
        ),
        KillZone(
            name=SessionName.LUNCH_SWEEP,
            start_time=time(13, 30),
            end_time=time(14, 0),
            danger_level=0.7,
            description="Secondary manipulation window",
            typical_behavior="Smaller sweeps, position adjustment"
        ),
        KillZone(
            name=SessionName.EXECUTION_2,
            start_time=time(14, 0),
            end_time=time(14, 45),
            danger_level=0.4,
            description="Second safe window",
            typical_behavior="Continuation moves if setup exists"
        ),
        KillZone(
            name=SessionName.CLOSING_CHAOS,
            start_time=time(14, 45),
            end_time=time(15, 30),
            danger_level=0.8,
            description="Final manipulation, position squaring",
            typical_behavior="Volatility, traps, avoid new entries"
        ),
    ]
    
    def get_current_zone(self, current_time: datetime) -> Optional[KillZone]:
        """Get the current kill zone based on time"""
        t = current_time.time()
        
        for zone in self.ZONES:
            if zone.start_time <= t < zone.end_time:
                return zone
        
        return None
    
    def get_time_context(self, current_time: datetime) -> TimeContext:
        """Get full time-based context"""
        zone = self.get_current_zone(current_time)
        
        # Calculate minutes to market close
        close_time = time(15, 30)
        now = current_time.time()
        
        if now < close_time:
            minutes_to_close = (
                (close_time.hour - now.hour) * 60 + 
                (close_time.minute - now.minute)
            )
        else:
            minutes_to_close = 0
        
        # Determine if should avoid entry
        avoid_entry = False
        reason = None
        
        if zone:
            if zone.danger_level >= 0.8:
                avoid_entry = True
                reason = f"{zone.name.value}: {zone.description}"
            elif zone.name == SessionName.LUNCH:
                avoid_entry = True
                reason = "Lunch session - low volume"
        
        if minutes_to_close < 30:
            avoid_entry = True
            reason = "Less than 30 minutes to close"
        
        return TimeContext(
            current_time=current_time,
            current_session=zone.name if zone else SessionName.POST_MARKET,
            kill_zone_active=zone is not None and zone.danger_level >= 0.7,
            kill_zone_name=zone.name.value if zone and zone.danger_level >= 0.7 else None,
            kill_zone_ends_at=datetime.combine(current_time.date(), zone.end_time) if zone else None,
            is_lunch=zone.name == SessionName.LUNCH if zone else False,
            is_opening=zone.name == SessionName.MORNING_HUNT if zone else False,
            is_closing=zone.name == SessionName.CLOSING_CHAOS if zone else False,
            danger_level=zone.danger_level if zone else 0.0,
            minutes_to_close=minutes_to_close,
            avoid_entry=avoid_entry,
            reason=reason
        )
```

### MTFAnalyzer

```python
class MTFAnalyzer:
    """Analyze multi-timeframe bias alignment"""
    
    # Timeframe hierarchy (higher = more important)
    TF_HIERARCHY = {
        "1D": 100,
        "4H": 80,
        "1H": 60,
        "15M": 40,
        "5M": 20,
        "1M": 10,
    }
    
    def analyze(self, tf_data: Dict[str, Dict]) -> MTFContext:
        """
        Analyze bias across timeframes.
        
        tf_data = {
            "1D": {"trend": "BULLISH", "last_event": "BOS", ...},
            "4H": {"trend": "BULLISH", "last_event": None, ...},
            ...
        }
        """
        biases = {}
        
        for tf, data in tf_data.items():
            trend = data.get('trend', 'NEUTRAL')
            bias = TimeframeBias[trend] if trend in TimeframeBias.__members__ else TimeframeBias.NEUTRAL
            
            biases[tf] = TimeframeBiasInfo(
                timeframe=tf,
                bias=bias,
                trend_strength=data.get('trend_strength', 0.5),
                key_level=Decimal(str(data['key_level'])) if data.get('key_level') else None,
                level_type=data.get('level_type'),
                last_structure_event=data.get('last_event')
            )
        
        # Calculate alignment
        alignment = self._calculate_alignment(biases)
        
        # Determine primary bias (HTF wins)
        primary = self._determine_primary_bias(biases)
        
        # Find conflicting TFs
        conflicts = self._find_conflicts(biases, primary)
        
        return MTFContext(
            biases=biases,
            alignment_score=alignment,
            primary_bias=primary,
            conflicting_timeframes=conflicts
        )
    
    def _calculate_alignment(self, biases: Dict[str, TimeframeBiasInfo]) -> float:
        """Calculate how aligned the timeframes are (0-1)"""
        if not biases:
            return 0.0
        
        # Weight each TF by hierarchy
        bullish_weight = 0
        bearish_weight = 0
        total_weight = 0
        
        for tf, info in biases.items():
            weight = self.TF_HIERARCHY.get(tf.upper(), 10)
            total_weight += weight
            
            if info.bias == TimeframeBias.BULLISH:
                bullish_weight += weight
            elif info.bias == TimeframeBias.BEARISH:
                bearish_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # Alignment = dominant direction's percentage
        dominant = max(bullish_weight, bearish_weight)
        return dominant / total_weight
    
    def _determine_primary_bias(self, biases: Dict[str, TimeframeBiasInfo]) -> TimeframeBias:
        """Determine primary bias from highest timeframes"""
        # Check in order of hierarchy
        for tf in ["1D", "4H", "1H"]:
            if tf in biases and biases[tf].bias != TimeframeBias.NEUTRAL:
                return biases[tf].bias
        
        return TimeframeBias.NEUTRAL
    
    def _find_conflicts(
        self, 
        biases: Dict[str, TimeframeBiasInfo], 
        primary: TimeframeBias
    ) -> List[str]:
        """Find timeframes that conflict with primary bias"""
        conflicts = []
        
        for tf, info in biases.items():
            if info.bias != TimeframeBias.NEUTRAL and info.bias != primary:
                conflicts.append(tf)
        
        return conflicts
```

### PhaseDetector

```python
class PhaseDetector:
    """Detect AMD manipulation phases"""
    
    def detect_phase(
        self, 
        candles: List[Candle],
        sweeps: List[Dict],
        structure_events: List[Dict],
        current_time: datetime
    ) -> PhaseContext:
        """Detect current manipulation phase"""
        
        signals = []
        
        # Recent sweeps suggest MANIPULATION
        recent_sweeps = [s for s in sweeps if self._is_recent(s, current_time, minutes=30)]
        
        # Recent BOS suggests DISTRIBUTION  
        recent_bos = [e for e in structure_events if e.get('type') == 'BOS' and self._is_recent(e, current_time, minutes=60)]
        
        # Range detection suggests ACCUMULATION
        range_candles = candles[-20:] if len(candles) >= 20 else candles
        is_ranging = self._detect_range(range_candles)
        
        # Determine phase
        if recent_sweeps and not recent_bos:
            phase = ManipulationPhase.MANIPULATION
            confidence = min(0.5 + len(recent_sweeps) * 0.15, 0.95)
            signals.append(f"Recent sweep(s): {len(recent_sweeps)}")
            next_phase = ManipulationPhase.DISTRIBUTION
            
        elif recent_bos:
            phase = ManipulationPhase.DISTRIBUTION
            confidence = min(0.6 + len(recent_bos) * 0.1, 0.9)
            signals.append(f"BOS detected: {len(recent_bos)}")
            next_phase = ManipulationPhase.ACCUMULATION
            
        elif is_ranging:
            phase = ManipulationPhase.ACCUMULATION
            confidence = 0.7
            signals.append("Price ranging, potential accumulation")
            next_phase = ManipulationPhase.MANIPULATION
            
        else:
            # Default
            phase = ManipulationPhase.DISTRIBUTION
            confidence = 0.4
            signals.append("No clear phase signals")
            next_phase = ManipulationPhase.ACCUMULATION
        
        return PhaseContext(
            current_phase=phase,
            phase_started=current_time - timedelta(minutes=15),  # Estimate
            phase_duration_minutes=15,
            confidence=confidence,
            next_expected_phase=next_phase,
            expected_transition_time=None,
            phase_signals=signals
        )
    
    def _is_recent(self, event: Dict, current_time: datetime, minutes: int) -> bool:
        """Check if event is within recent timeframe"""
        event_time = event.get('timestamp')
        if not event_time:
            return False
        
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)
        
        return (current_time - event_time).total_seconds() < minutes * 60
    
    def _detect_range(self, candles: List[Candle]) -> bool:
        """Detect if price is ranging"""
        if len(candles) < 10:
            return False
        
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]
        
        range_high = max(highs)
        range_low = min(lows)
        total_range = range_high - range_low
        
        # If total range is less than 2x average candle range, it's ranging
        avg_candle_range = sum(float(c.high - c.low) for c in candles) / len(candles)
        
        return total_range < avg_candle_range * 3
```

### ContextAggregator

```python
class ContextAggregator:
    """Aggregate all context into actionable assessment"""
    
    def __init__(self):
        self.kill_zone_mgr = KillZoneManager()
        self.mtf_analyzer = MTFAnalyzer()
        self.phase_detector = PhaseDetector()
    
    def get_full_context(
        self,
        symbol: str,
        timeframe: str,
        current_time: datetime,
        tf_data: Dict[str, Dict],
        candles: List[Candle],
        sweeps: List[Dict],
        structure_events: List[Dict]
    ) -> FullContext:
        """Get complete market context"""
        
        # Get individual contexts
        time_ctx = self.kill_zone_mgr.get_time_context(current_time)
        mtf_ctx = self.mtf_analyzer.analyze(tf_data)
        phase_ctx = self.phase_detector.detect_phase(candles, sweeps, structure_events, current_time)
        
        # Assess safety
        warnings = []
        recommendations = []
        
        if time_ctx.avoid_entry:
            warnings.append(time_ctx.reason)
        
        if phase_ctx.current_phase == ManipulationPhase.MANIPULATION:
            warnings.append("Manipulation phase - high trap risk")
            recommendations.append("Wait for distribution phase")
        
        if mtf_ctx.alignment_score < 0.5:
            warnings.append(f"Timeframes conflicting: {mtf_ctx.conflicting_timeframes}")
            recommendations.append("Wait for better alignment")
        
        # Calculate entry quality
        entry_quality = self._calculate_entry_quality(time_ctx, mtf_ctx, phase_ctx)
        
        safe_to_enter = (
            not time_ctx.avoid_entry and
            phase_ctx.current_phase == ManipulationPhase.DISTRIBUTION and
            mtf_ctx.alignment_score >= 0.6 and
            entry_quality >= 0.5
        )
        
        if safe_to_enter:
            recommendations.append("Safe to look for entries")
        
        return FullContext(
            symbol=symbol,
            timeframe=timeframe,
            generated_at=current_time,
            mtf=mtf_ctx,
            time=time_ctx,
            phase=phase_ctx,
            safe_to_enter=safe_to_enter,
            entry_quality=entry_quality,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def _calculate_entry_quality(
        self, 
        time_ctx: TimeContext, 
        mtf_ctx: MTFContext, 
        phase_ctx: PhaseContext
    ) -> float:
        """Calculate overall entry quality (0-1)"""
        quality = 0.0
        
        # Time factor (30%)
        time_factor = 1 - time_ctx.danger_level
        quality += time_factor * 0.3
        
        # MTF alignment (30%)
        quality += mtf_ctx.alignment_score * 0.3
        
        # Phase factor (40%)
        if phase_ctx.current_phase == ManipulationPhase.DISTRIBUTION:
            quality += 0.4 * phase_ctx.confidence
        elif phase_ctx.current_phase == ManipulationPhase.ACCUMULATION:
            quality += 0.15
        else:  # MANIPULATION
            quality += 0.05
        
        return min(1.0, quality)
```

---

## 📤 Events Published

```python
@dataclass
class PhaseChangeEvent:
    event_type: str = "context.phase.changed"
    symbol: str
    old_phase: str
    new_phase: str
    confidence: float
    timestamp: datetime

@dataclass
class KillZoneEvent:
    event_type: str = "context.killzone.entered"
    symbol: str
    zone_name: str
    danger_level: float
    ends_at: datetime
    timestamp: datetime
```

---

## ✅ Acceptance Criteria

- [ ] Correctly identifies all Indian market kill zones
- [ ] Calculates MTF bias alignment
- [ ] Detects AMD manipulation phases
- [ ] Provides danger level assessment
- [ ] Generates entry quality score
- [ ] Provides clear recommendations
- [ ] Publishes events on significant changes
