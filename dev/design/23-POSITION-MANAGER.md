# 📈 POSITION MANAGER SERVICE

> **Service**: `position-manager`
> **Purpose**: Manage positions AFTER entry
> **Key Insight**: Entry is 20% of trading. Management is 80%.

---

## 🎯 POSITION MANAGEMENT

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from decimal import Decimal
from enum import Enum

class PositionStatus(Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    BREAKEVEN = "BREAKEVEN"
    PARTIAL_PROFIT = "PARTIAL_PROFIT"
    CLOSED = "CLOSED"


@dataclass
class Position:
    id: str
    symbol: str
    direction: str  # LONG or SHORT
    entry_price: Decimal
    current_stop: Decimal
    target1: Decimal
    target2: Decimal
    target3: Decimal
    
    quantity: int
    remaining_quantity: int
    
    entry_time: datetime
    status: PositionStatus


class PositionManager:
    """Manage positions after entry"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        
        # Scaling rules
        self.scale_out_rules = [
            {'at_rr': 1.0, 'close_percent': 0.33, 'move_stop': 'BREAKEVEN'},
            {'at_rr': 2.0, 'close_percent': 0.33, 'trail_stop': True},
            {'at_rr': 3.0, 'close_percent': 0.34, 'trail_stop': True},
        ]
    
    def update_stop(self, position: Position, price: Decimal, context: Dict) -> Optional[Decimal]:
        """
        Structure-based stop trailing.
        NOT arbitrary - based on swing points.
        """
        
        entry = float(position.entry_price)
        stop = float(position.current_stop)
        current = float(price)
        
        # Only trail if in profit
        if position.direction == 'LONG' and current <= entry:
            return None
        if position.direction == 'SHORT' and current >= entry:
            return None
        
        # Calculate current R
        risk = abs(entry - stop)
        profit = abs(current - entry)
        current_rr = profit / risk if risk > 0 else 0
        
        # At 1R: Move to breakeven
        if current_rr >= 1.0 and stop < entry:
            return Decimal(str(entry))
        
        # After breakeven: Trail to recent structure
        if current_rr >= 1.5 and position.direction == 'LONG':
            recent_swing_low = context.get('last_swing_low')
            if recent_swing_low and float(recent_swing_low) > stop:
                # Trail to swing low - 0.1 ATR
                atr = context.get('atr', 0)
                new_stop = float(recent_swing_low) - atr * 0.1
                return Decimal(str(new_stop))
        
        return None
    
    def check_scale_out(self, position: Position, price: Decimal) -> Optional[Dict]:
        """Check if should take partial profits"""
        
        entry = float(position.entry_price)
        stop = float(position.current_stop)
        current = float(price)
        
        risk = abs(entry - stop)
        profit = abs(current - entry)
        current_rr = profit / risk if risk > 0 else 0
        
        for rule in self.scale_out_rules:
            if current_rr >= rule['at_rr']:
                already_scaled = position.status in [PositionStatus.PARTIAL_PROFIT]
                # Check if this R level already scaled
                
                if not already_scaled:
                    return {
                        'action': 'SCALE_OUT',
                        'percent': rule['close_percent'],
                        'reason': f"Reached {rule['at_rr']}R",
                        'move_stop_to': 'BREAKEVEN' if rule.get('move_stop') else None,
                    }
        
        return None
    
    def should_add(self, position: Position, context: Dict) -> Optional[Dict]:
        """Should we add to winner on pullback?"""
        
        regime = context.get('regime')
        
        # Only add in strong trends
        if regime not in ['STRONG_UPTREND', 'STRONG_DOWNTREND']:
            return None
        
        # Must be in profit
        entry = float(position.entry_price)
        current = float(context.get('current_price', entry))
        
        if position.direction == 'LONG' and current < entry:
            return None
        
        # Must be pulling back to entry zone
        distance = abs(current - entry) / entry * 100
        
        if 0.1 < distance < 0.5:  # Within 0.1% to 0.5% of entry
            return {
                'action': 'ADD',
                'size_multiplier': 0.5,  # Add 50% of original
                'stop': position.current_stop,  # Same stop
                'reason': 'Strong trend pullback to entry zone',
            }
        
        return None
    
    def get_position_stats(self, position: Position, price: Decimal) -> Dict:
        """Get current position statistics"""
        
        entry = float(position.entry_price)
        stop = float(position.current_stop)
        current = float(price)
        
        risk = abs(entry - stop)
        profit = current - entry if position.direction == 'LONG' else entry - current
        current_rr = profit / risk if risk > 0 else 0
        
        return {
            'entry': entry,
            'current': current,
            'stop': stop,
            'profit_points': profit,
            'risk_points': risk,
            'current_rr': round(current_rr, 2),
            'pnl_percent': round(profit / entry * 100, 2),
            'time_in_trade': datetime.now() - position.entry_time,
            'status': position.status,
        }
```

---

## 📋 MANAGEMENT RULES

```
RULE 1: Move stop to BREAKEVEN at 1R
RULE 2: Take 1/3 profit at 1R
RULE 3: Take 1/3 profit at 2R
RULE 4: Let final 1/3 run with trailing stop
RULE 5: Trail to structure (swing lows/highs), NOT arbitrary
RULE 6: NEVER widen stops. EVER.
RULE 7: Only add in STRONG trends on pullbacks
```

---

## ✅ ACCEPTANCE CRITERIA

- [ ] Structure-based stop trailing
- [ ] Partial profit taking at R levels
- [ ] Break-even move at 1R
- [ ] Add-to-winner logic for strong trends
- [ ] NEVER widen stops
