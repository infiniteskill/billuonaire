# 🛡️ ANTIFRAGILITY LAYER

> **Service**: `antifragility-layer`
> **Purpose**: Get STRONGER from stress and chaos
> **Key Insight**: Don't just survive black swans. BENEFIT from them.

---

## 🎯 THE ANTIFRAGILE MINDSET

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║   Fragile: Breaks under stress                                         ║
║   Robust: Survives stress                                              ║
║   ANTIFRAGILE: Gets STRONGER from stress                               ║
║                                                                        ║
║   Our system must be ANTIFRAGILE.                                      ║
║   Every crisis teaches us. Every failure makes us stronger.            ║
║                                                                        ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## 📊 BLACK SWAN SCENARIOS

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from decimal import Decimal
from enum import Enum

class StressScenario(Enum):
    CIRCUIT_BREAKER_DOWN = "CIRCUIT_BREAKER_DOWN"  # 10% drop, trading halted
    CIRCUIT_BREAKER_UP = "CIRCUIT_BREAKER_UP"      # 10% up, trading halted
    FLASH_CRASH = "FLASH_CRASH"                    # 5%+ instant drop
    FLASH_RALLY = "FLASH_RALLY"                    # 5%+ instant spike
    GAP_EXTREME_DOWN = "GAP_EXTREME_DOWN"          # 3%+ gap down
    GAP_EXTREME_UP = "GAP_EXTREME_UP"              # 3%+ gap up
    LIQUIDITY_CRISIS = "LIQUIDITY_CRISIS"          # Wide spreads
    DATA_FAILURE = "DATA_FAILURE"                  # Our data stops
    SYSTEM_FAILURE = "SYSTEM_FAILURE"              # Our system crashes
    NEWS_SHOCK = "NEWS_SHOCK"                      # Unexpected major news


@dataclass
class StressTestResult:
    scenario: StressScenario
    max_loss: Decimal
    recovery_time: str
    system_behavior: str
    protection_triggered: bool
    lesson_learned: str


class AntifragilityLayer:
    """
    Make the system antifragile - stronger from stress.
    """
    
    def __init__(self):
        self.stress_scenarios = list(StressScenario)
        self.lessons_learned: List[Dict] = []
    
    def stress_test_strategy(self, strategy: Dict, scenario: StressScenario) -> StressTestResult:
        """Run strategy through stress scenario"""
        
        if scenario == StressScenario.CIRCUIT_BREAKER_DOWN:
            return StressTestResult(
                scenario=scenario,
                max_loss=Decimal("10"),  # 10%
                recovery_time="Unknown - trading halted",
                system_behavior="Close all positions on resume at ANY price",
                protection_triggered=True,
                lesson_learned="Position size must assume 10% gap risk"
            )
        
        if scenario == StressScenario.FLASH_CRASH:
            return StressTestResult(
                scenario=scenario,
                max_loss=Decimal("5"),
                recovery_time="Minutes to hours",
                system_behavior="Stops hit instantly, no fills at intended price",
                protection_triggered=False,
                lesson_learned="Use guaranteed stops OR accept flash crash risk"
            )
        
        return StressTestResult(
            scenario=scenario,
            max_loss=Decimal("0"),
            recovery_time="N/A",
            system_behavior="Unknown",
            protection_triggered=False,
            lesson_learned="Scenario not simulated"
        )
    
    def get_protection_rules(self) -> Dict:
        """Core protection rules for antifragility"""
        
        return {
            'position_sizing': {
                'max_risk_per_trade': 0.5,  # 0.5% of capital
                'assume_worst_case_slippage': 2.0,  # 2x expected
                'circuit_breaker_buffer': True,  # Size assuming 10% gap
            },
            'stop_strategy': {
                'use_exchange_stops': True,  # Not mental stops
                'guaranteed_stops': 'Consider for overnight',
                'never_remove_stop': True,
            },
            'cash_reserve': {
                'min_cash_percent': 30,  # Always 30% cash
                'opportunity_capital': 20,  # Extra for crashes
            },
            'hedging': {
                'consider_puts': 'For overnight/weekend risk',
                'vix_threshold': 25,  # Reduce size when VIX > 25
            },
            'recovery_plan': {
                'after_circuit_breaker': 'Close ALL positions on resume',
                'after_flash_crash': 'Wait 30 mins, assess damage',
                'after_data_failure': 'Close positions, wait for data',
            },
        }
    
    def detect_anomaly(self, candle, context: Dict) -> Optional[str]:
        """Detect if something unusual is happening RIGHT NOW"""
        
        atr = context.get('atr', 50)
        prev_close = context.get('prev_close')
        
        # Candle size anomaly
        candle_size = float(candle.high - candle.low)
        if candle_size > atr * 3:
            return "ANOMALY: Extreme candle 3x ATR - possible news"
        
        # Gap anomaly
        if prev_close:
            gap = abs(float(candle.open) - float(prev_close))
            if gap > atr * 2:
                return "ANOMALY: Large gap 2x ATR - external event"
        
        # Speed anomaly (if we have tick data)
        price_change = abs(float(candle.close - candle.open))
        if price_change > atr * 2:
            return "ANOMALY: Rapid move - check news"
        
        return None
    
    def handle_anomaly(self, anomaly_type: str, positions: List) -> Dict:
        """What to do when anomaly detected"""
        
        if "EXTREME" in anomaly_type or "RAPID" in anomaly_type:
            return {
                'action': 'CLOSE_ALL',
                'reason': 'Extreme market conditions',
                'wait_period': '30 minutes before new trades',
            }
        
        if "GAP" in anomaly_type:
            return {
                'action': 'REDUCE_SIZE',
                'new_size': 0.5,
                'reason': 'Gap risk elevated',
            }
        
        return {'action': 'MONITOR', 'reason': 'Unknown anomaly'}
    
    def learn_from_crisis(self, crisis_data: Dict):
        """Record lesson from crisis for future protection"""
        
        lesson = {
            'date': crisis_data['date'],
            'scenario': crisis_data['type'],
            'what_happened': crisis_data['description'],
            'our_loss': crisis_data.get('loss', 0),
            'what_we_learned': crisis_data.get('lesson', ''),
            'new_rule': crisis_data.get('rule_change', ''),
        }
        
        self.lessons_learned.append(lesson)
        
        # Update protection rules based on lesson
        self._update_rules_from_lesson(lesson)
    
    def calculate_risk_adjusted_size(self, base_size: float, context: Dict) -> float:
        """Adjust position size for current risk level"""
        
        vix = context.get('vix', 15)
        is_expiry = context.get('is_expiry', False)
        time_danger = context.get('time_danger', 0.5)
        
        adjusted = base_size
        
        # VIX adjustment
        if vix > 25:
            adjusted *= 0.5
        elif vix > 20:
            adjusted *= 0.7
        
        # Expiry adjustment
        if is_expiry:
            adjusted *= 0.5
        
        # Time adjustment
        adjusted *= (1 - time_danger * 0.3)
        
        return max(0.1, adjusted)  # Never less than 10% of base
```

---

## ✅ ACCEPTANCE CRITERIA

- [ ] Define all black swan scenarios
- [ ] Stress test strategies
- [ ] Protection rules for each scenario
- [ ] Anomaly detection in real-time
- [ ] Learn from every crisis
- [ ] Risk-adjusted position sizing
