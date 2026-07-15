# 🛡️ Protection Layer Service Design

> **Service**: `protection-layer`
> **Purpose**: Risk assessment, warnings, and guardrails
> **Independence**: Wraps all signals with safety checks

---

## 🎯 Responsibilities

1. Assess risk level for each signal
2. Provide real-time danger warnings
3. Detect extreme conditions (volatility, news)
4. Enforce position limits and exposure rules
5. Alert on unusual market behavior

---

## 📐 API Contract

```yaml
GET /api/v1/risk-assessment/{symbol}:
  response:
    symbol: "NIFTY 50"
    timestamp: "2025-01-31T10:30:00+05:30"
    
    risk_level: "HIGH"  # LOW, MEDIUM, HIGH, EXTREME
    risk_score: 78  # 0-100
    
    factors:
      - factor: "KILL_ZONE"
        impact: 25
        description: "Morning hunt active"
      - factor: "VOLATILITY"
        impact: 20
        description: "ATR 1.5x normal"
      - factor: "PHASE"
        impact: 18
        description: "Manipulation phase detected"
      - factor: "STRUCTURE_WEAK"
        impact: 15
        description: "CHoCH detected, trend uncertain"
    
    recommendations:
      - "Reduce position size by 50%"
      - "Use wider stops (1.5x normal)"
      - "Avoid new entries until 10:30"
    
    safe_to_trade: false
    wait_until: "2025-01-31T10:30:00+05:30"

POST /api/v1/validate-signal:
  body:
    signal: {...}
  response:
    approved: false
    rejection_reasons:
      - "Risk level too high (78/100)"
      - "Kill zone active"
    modified_signal:
      entry_zone: [22380, 22395]  # Tighter
      stop_loss: 22330  # Wider stop
      position_size_factor: 0.5  # Reduced size

GET /api/v1/alerts:
  response:
    active_alerts:
      - type: "VOLATILITY_SPIKE"
        severity: "WARNING"
        message: "ATR increased 80% in last hour"
        triggered_at: "2025-01-31T10:15:00+05:30"
      - type: "CONSECUTIVE_LOSSES"
        severity: "CAUTION"
        message: "3 consecutive stopped signals"
        triggered_at: "2025-01-31T10:20:00+05:30"
```

---

## 📊 Data Models

```python
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"

class AlertType(Enum):
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    CONSECUTIVE_LOSSES = "CONSECUTIVE_LOSSES"
    UNUSUAL_VOLUME = "UNUSUAL_VOLUME"
    NEWS_EVENT = "NEWS_EVENT"
    GAP_DETECTED = "GAP_DETECTED"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    MANIPULATION_INTENSE = "MANIPULATION_INTENSE"

class AlertSeverity(Enum):
    INFO = "INFO"
    CAUTION = "CAUTION"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

@dataclass
class RiskFactor:
    """A single risk factor"""
    name: str
    impact: int  # 0-100
    description: str
    
@dataclass
class RiskAssessment:
    """Complete risk assessment"""
    symbol: str
    timestamp: datetime
    
    risk_level: RiskLevel
    risk_score: int  # 0-100
    
    factors: List[RiskFactor]
    recommendations: List[str]
    
    safe_to_trade: bool
    wait_until: Optional[datetime]

@dataclass
class Alert:
    """Active alert"""
    id: str
    type: AlertType
    severity: AlertSeverity
    symbol: Optional[str]
    message: str
    triggered_at: datetime
    expires_at: Optional[datetime]
    acknowledged: bool = False

@dataclass
class SignalValidation:
    """Result of signal validation"""
    approved: bool
    rejection_reasons: List[str]
    warnings: List[str]
    
    # Modified signal parameters
    suggested_position_size: float  # Multiplier (0.5 = half size)
    suggested_stop_buffer: float    # Multiplier (1.5 = 50% wider)
```

---

## 🔧 Implementation

### RiskAssessor

```python
class RiskAssessor:
    """Assess overall market risk"""
    
    # Risk factor weights (must sum to 100)
    WEIGHTS = {
        "kill_zone": 25,
        "volatility": 20,
        "phase": 18,
        "structure": 15,
        "time_to_close": 10,
        "recent_performance": 12,
    }
    
    def assess(
        self,
        symbol: str,
        context: FullContext,
        atr_current: Decimal,
        atr_normal: Decimal,
        recent_signals: List[Dict]
    ) -> RiskAssessment:
        """Perform full risk assessment"""
        factors = []
        total_score = 0
        
        # 1. Kill Zone Risk
        if context.time.kill_zone_active:
            impact = int(context.time.danger_level * self.WEIGHTS["kill_zone"])
            factors.append(RiskFactor(
                name="KILL_ZONE",
                impact=impact,
                description=f"{context.time.kill_zone_name} active"
            ))
            total_score += impact
        
        # 2. Volatility Risk
        atr_ratio = float(atr_current / atr_normal) if atr_normal > 0 else 1
        if atr_ratio > 1.3:
            impact = min(int((atr_ratio - 1) * self.WEIGHTS["volatility"]), self.WEIGHTS["volatility"])
            factors.append(RiskFactor(
                name="VOLATILITY",
                impact=impact,
                description=f"ATR {atr_ratio:.1f}x normal"
            ))
            total_score += impact
        
        # 3. Phase Risk
        if context.phase.current_phase == ManipulationPhase.MANIPULATION:
            impact = int(context.phase.confidence * self.WEIGHTS["phase"])
            factors.append(RiskFactor(
                name="PHASE",
                impact=impact,
                description="Manipulation phase detected"
            ))
            total_score += impact
        
        # 4. Structure Risk
        if context.mtf.alignment_score < 0.5:
            impact = int((1 - context.mtf.alignment_score) * self.WEIGHTS["structure"])
            factors.append(RiskFactor(
                name="STRUCTURE_WEAK",
                impact=impact,
                description=f"TF alignment only {context.mtf.alignment_score:.0%}"
            ))
            total_score += impact
        
        # 5. Time to Close Risk
        if context.time.minutes_to_close < 60:
            impact = int((1 - context.time.minutes_to_close / 60) * self.WEIGHTS["time_to_close"])
            factors.append(RiskFactor(
                name="CLOSING_SOON",
                impact=impact,
                description=f"{context.time.minutes_to_close} min to close"
            ))
            total_score += impact
        
        # 6. Recent Performance Risk
        if recent_signals:
            recent_losses = sum(1 for s in recent_signals[-5:] if not s.get('was_winner', True))
            if recent_losses >= 3:
                impact = min(recent_losses * 4, self.WEIGHTS["recent_performance"])
                factors.append(RiskFactor(
                    name="LOSING_STREAK",
                    impact=impact,
                    description=f"{recent_losses} losses in last 5 signals"
                ))
                total_score += impact
        
        # Determine risk level
        if total_score >= 70:
            risk_level = RiskLevel.EXTREME
        elif total_score >= 50:
            risk_level = RiskLevel.HIGH
        elif total_score >= 30:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        # Generate recommendations
        recommendations = self._generate_recommendations(factors, risk_level, context)
        
        # Determine if safe
        safe_to_trade = risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM] and total_score < 50
        
        wait_until = None
        if not safe_to_trade and context.time.kill_zone_ends_at:
            wait_until = context.time.kill_zone_ends_at
        
        return RiskAssessment(
            symbol=symbol,
            timestamp=datetime.now(),
            risk_level=risk_level,
            risk_score=total_score,
            factors=factors,
            recommendations=recommendations,
            safe_to_trade=safe_to_trade,
            wait_until=wait_until
        )
    
    def _generate_recommendations(
        self, 
        factors: List[RiskFactor],
        risk_level: RiskLevel,
        context: FullContext
    ) -> List[str]:
        """Generate actionable recommendations"""
        recs = []
        
        if risk_level == RiskLevel.EXTREME:
            recs.append("DO NOT TRADE - conditions extremely risky")
        elif risk_level == RiskLevel.HIGH:
            recs.append("Reduce position size by 75%")
            recs.append("Consider sitting out this session")
        elif risk_level == RiskLevel.MEDIUM:
            recs.append("Reduce position size by 50%")
            recs.append("Use wider stops (1.5x normal)")
        
        for factor in factors:
            if factor.name == "KILL_ZONE":
                if context.time.kill_zone_ends_at:
                    recs.append(f"Wait until {context.time.kill_zone_ends_at.strftime('%H:%M')}")
            elif factor.name == "VOLATILITY":
                recs.append("Use ATR-based stops, not fixed points")
            elif factor.name == "LOSING_STREAK":
                recs.append("Take a break or reduce size significantly")
        
        return recs
```

### AlertManager

```python
class AlertManager:
    """Manage and track alerts"""
    
    def __init__(self):
        self.active_alerts: List[Alert] = []
    
    def check_volatility(self, atr_current: Decimal, atr_avg: Decimal) -> Optional[Alert]:
        """Check for volatility spikes"""
        if atr_avg == 0:
            return None
        
        ratio = float(atr_current / atr_avg)
        
        if ratio > 2.0:
            return Alert(
                id=f"vol_{datetime.now().timestamp()}",
                type=AlertType.VOLATILITY_SPIKE,
                severity=AlertSeverity.CRITICAL,
                symbol=None,
                message=f"ATR spiked {ratio:.1f}x above normal!",
                triggered_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=1)
            )
        elif ratio > 1.5:
            return Alert(
                id=f"vol_{datetime.now().timestamp()}",
                type=AlertType.VOLATILITY_SPIKE,
                severity=AlertSeverity.WARNING,
                symbol=None,
                message=f"ATR increased {int((ratio-1)*100)}% above normal",
                triggered_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=30)
            )
        
        return None
    
    def check_consecutive_losses(self, signals: List[Dict]) -> Optional[Alert]:
        """Check for consecutive losses"""
        if len(signals) < 3:
            return None
        
        recent = signals[-5:]
        consecutive_losses = 0
        
        for s in reversed(recent):
            if not s.get('was_winner', True):
                consecutive_losses += 1
            else:
                break
        
        if consecutive_losses >= 3:
            severity = AlertSeverity.WARNING if consecutive_losses >= 5 else AlertSeverity.CAUTION
            return Alert(
                id=f"loss_{datetime.now().timestamp()}",
                type=AlertType.CONSECUTIVE_LOSSES,
                severity=severity,
                symbol=None,
                message=f"{consecutive_losses} consecutive stopped signals",
                triggered_at=datetime.now(),
                expires_at=None  # Manual dismissal required
            )
        
        return None
    
    def check_gap(self, prev_close: Decimal, open_price: Decimal, atr: Decimal) -> Optional[Alert]:
        """Check for gap opens"""
        gap = abs(open_price - prev_close)
        gap_atr = float(gap / atr) if atr > 0 else 0
        
        if gap_atr > 1.0:
            return Alert(
                id=f"gap_{datetime.now().timestamp()}",
                type=AlertType.GAP_DETECTED,
                severity=AlertSeverity.WARNING,
                symbol=None,
                message=f"Gap of {gap_atr:.1f} ATR detected",
                triggered_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=2)
            )
        
        return None
    
    def add_alert(self, alert: Alert):
        """Add new alert"""
        self.active_alerts.append(alert)
        self._cleanup_expired()
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        self._cleanup_expired()
        return [a for a in self.active_alerts if not a.acknowledged]
    
    def acknowledge_alert(self, alert_id: str):
        """Mark alert as acknowledged"""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                break
    
    def _cleanup_expired(self):
        """Remove expired alerts"""
        now = datetime.now()
        self.active_alerts = [
            a for a in self.active_alerts
            if a.expires_at is None or a.expires_at > now
        ]
```

### SignalValidator

```python
class SignalValidator:
    """Validate and potentially modify signals"""
    
    def __init__(self, risk_assessor: RiskAssessor, alert_manager: AlertManager):
        self.risk_assessor = risk_assessor
        self.alert_manager = alert_manager
    
    def validate(
        self,
        signal: Signal,
        risk_assessment: RiskAssessment
    ) -> SignalValidation:
        """Validate a signal against current risk"""
        
        rejection_reasons = []
        warnings = []
        
        # Check risk level
        if risk_assessment.risk_level == RiskLevel.EXTREME:
            rejection_reasons.append("Risk level EXTREME - no trading")
        elif risk_assessment.risk_level == RiskLevel.HIGH:
            warnings.append("Risk level HIGH - reduced sizing recommended")
        
        # Check alerts
        active_alerts = self.alert_manager.get_active_alerts()
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        
        if critical_alerts:
            rejection_reasons.append(f"Critical alert active: {critical_alerts[0].message}")
        
        # Check signal confidence vs risk
        min_confidence = 0.6 + (risk_assessment.risk_score / 200)  # Higher risk = need more confidence
        if signal.confidence < min_confidence:
            rejection_reasons.append(
                f"Confidence {signal.confidence:.0%} below required {min_confidence:.0%} for current risk"
            )
        
        # Check R:R ratio
        if signal.risk_reward < 1.5:
            rejection_reasons.append(f"R:R {signal.risk_reward:.1f} below minimum 1.5")
        elif signal.risk_reward < 2.0:
            warnings.append(f"R:R {signal.risk_reward:.1f} is marginal")
        
        # Determine position size adjustment
        if risk_assessment.risk_level == RiskLevel.HIGH:
            position_size = 0.25
        elif risk_assessment.risk_level == RiskLevel.MEDIUM:
            position_size = 0.5
        else:
            position_size = 1.0
        
        # Determine stop buffer adjustment
        if risk_assessment.risk_score > 50:
            stop_buffer = 1.5
        else:
            stop_buffer = 1.0
        
        return SignalValidation(
            approved=len(rejection_reasons) == 0,
            rejection_reasons=rejection_reasons,
            warnings=warnings,
            suggested_position_size=position_size,
            suggested_stop_buffer=stop_buffer
        )
```

---

## 📤 Events Published

```python
@dataclass
class RiskAlertEvent:
    event_type: str = "protection.alert.new"
    alert_type: str
    severity: str
    message: str
    timestamp: datetime

@dataclass
class SignalBlockedEvent:
    event_type: str = "protection.signal.blocked"
    signal_id: str
    reasons: List[str]
    timestamp: datetime
```

---

## ✅ Acceptance Criteria

- [ ] Calculates comprehensive risk score
- [ ] Identifies all major risk factors
- [ ] Provides actionable recommendations
- [ ] Tracks and manages alerts
- [ ] Validates signals against risk
- [ ] Suggests position size adjustments
- [ ] Detects volatility spikes
- [ ] Tracks consecutive losses
