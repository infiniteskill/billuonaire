# 📅 TIME STATISTICS ENGINE

> **Service**: `time-statistics-engine`
> **Purpose**: Granular time-based patterns
> **Key Insight**: Monday ≠ Friday, Expiry ≠ Normal, Morning ≠ Afternoon

---

## 🎯 TIME PATTERNS

```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, time, date
from enum import Enum

class DayOfWeek(Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"


@dataclass
class TimeSlotStats:
    """Statistics for a specific time slot"""
    time_start: time
    time_end: time
    
    # Direction stats
    bullish_probability: float
    bearish_probability: float
    
    # Volatility
    avg_atr: float
    volatility_rank: str  # LOW, MEDIUM, HIGH, EXTREME
    
    # Quality
    signal_quality: float  # 0-1 how reliable signals are
    trap_probability: float  # Probability of false moves
    
    # Recommendation
    trading_allowed: bool
    recommended_action: str


class TimeStatisticsEngine:
    """Analyze time-based patterns"""
    
    # Day-of-week patterns
    DAY_PATTERNS = {
        DayOfWeek.MONDAY: {
            'typical': 'Gap fill attempts, volatile open',
            'volatility': 'HIGH in first hour',
            'avoid': ['09:15-09:45'],
            'best': ['11:00-12:30'],
            'gap_fill_prob': 0.65,
        },
        DayOfWeek.TUESDAY: {
            'typical': 'Trend continuation',
            'volatility': 'MEDIUM',
            'best': ['11:00-12:30', '14:00-14:30'],
        },
        DayOfWeek.WEDNESDAY: {
            'typical': 'Mid-week reversal possible',
            'volatility': 'MEDIUM',
            'weekly_high_low_prob': 0.35,
        },
        DayOfWeek.THURSDAY: {
            'typical': 'Weekly expiry (futures), high volatility',
            'volatility': 'VERY HIGH on expiry',
            'avoid': ['14:30-15:30'] if 'expiry' else [],
            'expiry_manipulation': True,
        },
        DayOfWeek.FRIDAY: {
            'typical': 'Profit booking, reduced volume',
            'volatility': 'Decreasing after lunch',
            'avoid': ['14:00-15:30'],
            'weekly_close': True,
        },
    }
    
    # Intraday patterns
    INTRADAY_SLOTS = {
        '09:15-09:45': {
            'name': 'Opening Manipulation',
            'volatility': 'EXTREME',
            'trap_prob': 0.8,
            'recommendation': 'AVOID',
            'reason': 'Stop hunts and fake moves',
        },
        '09:45-10:30': {
            'name': 'Opening Range Build',
            'volatility': 'HIGH',
            'trap_prob': 0.6,
            'recommendation': 'OBSERVE_ONLY',
            'reason': 'Establishing opening range',
        },
        '10:30-11:00': {
            'name': 'First Opportunity',
            'volatility': 'MEDIUM-HIGH',
            'trap_prob': 0.4,
            'recommendation': 'TRADE',
            'reason': 'Range established, direction emerging',
        },
        '11:00-12:30': {
            'name': 'Prime Trading',
            'volatility': 'MEDIUM',
            'trap_prob': 0.3,
            'recommendation': 'BEST_TIME',
            'reason': 'Clearest trends, lowest manipulation',
        },
        '12:30-13:30': {
            'name': 'Lunch Range',
            'volatility': 'LOW',
            'trap_prob': 0.5,
            'recommendation': 'LIGHT_TRADING',
            'reason': 'Low volume, choppy',
        },
        '13:30-14:30': {
            'name': 'Afternoon Session',
            'volatility': 'MEDIUM',
            'trap_prob': 0.4,
            'recommendation': 'TRADE',
            'reason': 'Second opportunity window',
        },
        '14:30-15:00': {
            'name': 'Last Hour Volatility',
            'volatility': 'HIGH',
            'trap_prob': 0.6,
            'recommendation': 'CAUTION',
            'reason': 'Position squaring begins',
        },
        '15:00-15:30': {
            'name': 'Closing Chaos',
            'volatility': 'EXTREME',
            'trap_prob': 0.7,
            'recommendation': 'AVOID',
            'reason': 'Expiry effects, last-minute moves',
        },
    }
    
    def get_current_slot(self, t: time = None) -> TimeSlotStats:
        """Get stats for current time slot"""
        
        t = t or datetime.now().time()
        
        for slot_range, stats in self.INTRADAY_SLOTS.items():
            start_str, end_str = slot_range.split('-')
            start = time(*map(int, start_str.split(':')))
            end = time(*map(int, end_str.split(':')))
            
            if start <= t <= end:
                return TimeSlotStats(
                    time_start=start,
                    time_end=end,
                    bullish_probability=0.5,
                    bearish_probability=0.5,
                    avg_atr=0,
                    volatility_rank=stats['volatility'],
                    signal_quality=1 - stats['trap_prob'],
                    trap_probability=stats['trap_prob'],
                    trading_allowed=stats['recommendation'] not in ['AVOID'],
                    recommended_action=stats['recommendation']
                )
        
        return None
    
    def is_expiry_week(self, d: date = None) -> bool:
        """Check if this is expiry week"""
        d = d or date.today()
        # Thursday expiry - check if any Thursday this week
        days_to_thursday = (3 - d.weekday()) % 7
        return days_to_thursday <= 4
    
    def is_expiry_day(self, d: date = None) -> bool:
        """Check if today is expiry day"""
        d = d or date.today()
        return d.weekday() == 3  # Thursday
    
    def get_expiry_adjustments(self) -> Dict:
        """Adjustments for expiry"""
        return {
            'position_size': 0.5,
            'avoid_times': ['09:15-10:00', '14:30-15:30'],
            'max_pain_effect': True,
            'pin_risk': 'HIGH at round strikes',
            'strategy': 'Avoid options, trade futures only',
        }
    
    def get_danger_level(self, t: time = None, d: date = None) -> float:
        """Calculate overall danger level 0-1"""
        
        slot = self.get_current_slot(t)
        is_expiry = self.is_expiry_day(d)
        is_opening = t and t < time(10, 0)
        is_closing = t and t > time(14, 45)
        
        danger = slot.trap_probability if slot else 0.5
        
        if is_expiry:
            danger += 0.2
        if is_opening or is_closing:
            danger += 0.1
        
        return min(1.0, danger)
```

---

## ✅ ACCEPTANCE CRITERIA

- [ ] Track patterns by day of week
- [ ] Track patterns by time of day
- [ ] Detect expiry day/week
- [ ] Calculate danger level
- [ ] Recommend trading windows
- [ ] Warn about trap periods
