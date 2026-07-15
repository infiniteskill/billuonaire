# 🧠 META-LEARNING ENGINE

> **Service**: `meta-learning-engine`
> **Purpose**: Learn about how we learn
> **Key Insight**: Learning can go wrong. We must learn CORRECTLY.

---

## 🎯 THE META-LEARNING CHALLENGE

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║   THREE WAYS LEARNING CAN FAIL:                                        ║
║                                                                        ║
║   1. OVERFITTING: Learning noise, not patterns                         ║
║   2. CATASTROPHIC FORGETTING: New learning erases old                  ║
║   3. REGIME BLINDNESS: Patterns from old regime fail in new            ║
║                                                                        ║
║   Meta-learning protects against ALL THREE.                            ║
║                                                                        ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## 📊 META-LEARNING IMPLEMENTATION

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np

@dataclass
class LearningMetrics:
    """Metrics about our learning"""
    
    # Accuracy tracking
    training_accuracy: float = 0.0
    validation_accuracy: float = 0.0
    real_trading_accuracy: float = 0.0
    
    # Improvement tracking
    accuracy_30_days_ago: float = 0.5
    accuracy_7_days_ago: float = 0.5
    accuracy_today: float = 0.5
    
    # Overfitting indicators
    overfitting_score: float = 0.0  # 0 = none, 1 = severe
    
    # Forgetting indicators
    old_pattern_accuracy: float = 0.0
    new_pattern_accuracy: float = 0.0
    forgetting_score: float = 0.0
    
    # Regime indicators
    current_regime_accuracy: float = 0.0
    regime_change_detected: bool = False


class MetaLearningEngine:
    """
    Learn about how we learn.
    
    Prevent: Overfitting, Catastrophic Forgetting, Regime Blindness
    """
    
    def __init__(self):
        self.learning_history: List[LearningMetrics] = []
        self.pattern_memory: List[Dict] = []  # Important patterns to remember
        self.regime_signatures: Dict[str, List] = {}  # Patterns per regime
    
    # ═══════════════════════════════════════════════════════════════
    # OVERFITTING DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    def detect_overfitting(self) -> Dict:
        """
        Detect if we're overfitting to recent data.
        
        Signs:
        - Training accuracy >> Real accuracy
        - Performance degrades on new data
        - Rules become too complex
        """
        
        metrics = self._get_current_metrics()
        
        # Compare training vs real
        gap = metrics.training_accuracy - metrics.real_trading_accuracy
        
        if gap > 0.15:
            return {
                'overfitting': True,
                'severity': 'HIGH',
                'gap': gap,
                'action': 'REDUCE_COMPLEXITY',
                'recommendation': 'Simplify rules. Remove recent adjustments.'
            }
        
        if gap > 0.08:
            return {
                'overfitting': True,
                'severity': 'MEDIUM',
                'gap': gap,
                'action': 'MONITOR',
                'recommendation': 'Watch for further degradation.'
            }
        
        return {'overfitting': False}
    
    # ═══════════════════════════════════════════════════════════════
    # CATASTROPHIC FORGETTING PREVENTION
    # ═══════════════════════════════════════════════════════════════
    
    def prevent_forgetting(self):
        """
        When learning new patterns, don't forget successful old ones.
        
        Uses EXPERIENCE REPLAY - mix old and new data when training.
        """
        
        # Keep a buffer of important historical patterns
        self.pattern_memory = self._select_diverse_patterns()
    
    def _select_diverse_patterns(self) -> List[Dict]:
        """Select diverse patterns to remember"""
        
        patterns = []
        
        # Include patterns from different regimes
        for regime, regime_patterns in self.regime_signatures.items():
            # Top 3 most successful patterns per regime
            sorted_patterns = sorted(
                regime_patterns, 
                key=lambda x: x.get('success_rate', 0), 
                reverse=True
            )[:3]
            patterns.extend(sorted_patterns)
        
        # Include patterns from different market conditions
        # Include patterns from different times of day
        
        return patterns
    
    def check_forgetting(self) -> Dict:
        """Check if we're forgetting old patterns"""
        
        # Test old patterns on recent data
        old_accuracy = self._test_old_patterns()
        
        # Compare to historical accuracy
        historical_accuracy = self._get_historical_accuracy()
        
        degradation = historical_accuracy - old_accuracy
        
        if degradation > 0.15:
            return {
                'forgetting': True,
                'severity': 'HIGH',
                'degradation': degradation,
                'action': 'REPLAY_OLD_PATTERNS',
                'recommendation': 'Re-include old patterns in training.'
            }
        
        return {'forgetting': False, 'degradation': degradation}
    
    # ═══════════════════════════════════════════════════════════════
    # REGIME ADAPTATION
    # ═══════════════════════════════════════════════════════════════
    
    def detect_regime_change(self, recent_data: List) -> Dict:
        """
        Detect if market regime has changed.
        
        Old patterns may not work in new regime.
        """
        
        # Calculate regime signature from recent data
        current_signature = self._calculate_regime_signature(recent_data)
        
        # Compare to known regimes
        best_match = None
        best_score = 0
        
        for regime_name, signature in self.regime_signatures.items():
            similarity = self._compare_signatures(current_signature, signature)
            if similarity > best_score:
                best_score = similarity
                best_match = regime_name
        
        if best_score < 0.6:
            return {
                'new_regime': True,
                'similarity_to_known': best_score,
                'action': 'RESET_PARTIAL',
                'recommendation': 'New regime detected. Use only robust patterns.'
            }
        
        return {
            'new_regime': False,
            'current_regime': best_match,
            'confidence': best_score
        }
    
    # ═══════════════════════════════════════════════════════════════
    # LEARNING EFFECTIVENESS
    # ═══════════════════════════════════════════════════════════════
    
    def evaluate_learning_effectiveness(self) -> Dict:
        """Is our learning actually improving accuracy?"""
        
        periods = {
            'last_week': 7,
            'last_month': 30,
            'last_quarter': 90
        }
        
        effectiveness = {}
        
        for period_name, days in periods.items():
            start_acc = self._get_accuracy_n_days_ago(days)
            end_acc = self._get_accuracy_n_days_ago(0)
            
            effectiveness[period_name] = {
                'start': start_acc,
                'end': end_acc,
                'improvement': end_acc - start_acc,
                'is_improving': end_acc > start_acc
            }
        
        # Overall assessment
        improving_periods = sum(
            1 for p in effectiveness.values() if p['is_improving']
        )
        
        return {
            'periods': effectiveness,
            'overall': 'IMPROVING' if improving_periods >= 2 else 'STAGNANT',
            'recommendation': self._get_learning_recommendation(effectiveness)
        }
    
    # ═══════════════════════════════════════════════════════════════
    # RESET DECISIONS
    # ═══════════════════════════════════════════════════════════════
    
    def should_reset_learning(self) -> Dict:
        """
        Sometimes we need to UNLEARN.
        Markets change. Old patterns stop working.
        """
        
        recent_accuracy = self._get_accuracy_n_days_ago(0)
        
        if recent_accuracy < 0.40:
            return {
                'reset_needed': True,
                'type': 'FULL',
                'reason': 'Accuracy below random chance',
                'recommendation': 'Full reset. Start fresh.'
            }
        
        if recent_accuracy < 0.50:
            return {
                'reset_needed': True,
                'type': 'PARTIAL',
                'reason': 'Accuracy barely above random',
                'recommendation': 'Keep only highest-confidence patterns.'
            }
        
        return {'reset_needed': False}
    
    def _get_learning_recommendation(self, effectiveness: Dict) -> str:
        """Get recommendation based on learning trends"""
        
        if all(p['is_improving'] for p in effectiveness.values()):
            return "Learning is effective. Continue current approach."
        
        if effectiveness['last_week']['is_improving']:
            return "Recent improvement. Monitor for consistency."
        
        if not any(p['is_improving'] for p in effectiveness.values()):
            return "Learning stalled. Consider simplifying rules or resetting."
        
        return "Mixed results. Review recent changes."
```

---

## ✅ ACCEPTANCE CRITERIA

- [ ] Detect overfitting (training vs real gap)
- [ ] Prevent catastrophic forgetting (experience replay)
- [ ] Detect regime changes
- [ ] Evaluate learning effectiveness over time
- [ ] Know when to reset/unlearn
- [ ] Maintain pattern memory buffer
