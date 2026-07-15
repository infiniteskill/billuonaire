# 😱 PSYCHOLOGY GUARD SERVICE

> **Service**: `psychology-guard`
> **Purpose**: Protect the trader from their own emotions
> **Philosophy**: The mind is the weakest link. Protect it FIRST.

---

## 🎯 THE BRUTAL TRUTH

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                        ║
║   "The market can remain irrational longer than you can remain         ║
║    solvent... and SANE."                                               ║
║                                                                        ║
║   90% of trading failures are PSYCHOLOGICAL, not technical.            ║
║                                                                        ║
║   We don't just lose money. We lose our MINDS.                         ║
║                                                                        ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## 📊 EMOTIONAL STATE MODEL

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum
from decimal import Decimal

class EmotionalState(Enum):
    # Healthy states
    CALM = "CALM"
    FOCUSED = "FOCUSED"
    CONFIDENT = "CONFIDENT"
    
    # Warning states (can still trade with caution)
    ANXIOUS = "ANXIOUS"
    IMPATIENT = "IMPATIENT"
    FRUSTRATED = "FRUSTRATED"
    EXCITED = "EXCITED"
    
    # Danger states (STOP trading)
    FEARFUL = "FEARFUL"
    GREEDY = "GREEDY"
    REVENGE = "REVENGE"
    TILTED = "TILTED"
    EUPHORIC = "EUPHORIC"
    DESPERATE = "DESPERATE"


class TradingBehavior(Enum):
    """Behavioral patterns we detect"""
    NORMAL = "NORMAL"
    OVERTRADING = "OVERTRADING"
    REVENGE_TRADING = "REVENGE_TRADING"
    CHASING = "CHASING"
    FOMO = "FOMO"
    FREEZING = "FREEZING"  # Afraid to pull trigger
    OVERRIDING = "OVERRIDING"  # Ignoring system signals
    MOVING_STOPS = "MOVING_STOPS"  # Widening stops (deadly)
    AVERAGING_DOWN = "AVERAGING_DOWN"  # Adding to losers


@dataclass
class TraderPsychologyState:
    """Complete psychological profile at any moment"""
    
    # Timestamp
    timestamp: datetime
    
    # Current session stats
    session_start: datetime
    trades_today: int = 0
    wins_today: int = 0
    losses_today: int = 0
    
    # Streak tracking
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    longest_win_streak: int = 0
    longest_loss_streak: int = 0
    
    # P&L tracking
    current_daily_pnl: Decimal = Decimal("0")
    max_daily_pnl: Decimal = Decimal("0")
    min_daily_pnl: Decimal = Decimal("0")
    current_drawdown: Decimal = Decimal("0")
    
    # Timing analysis
    time_since_last_trade: Optional[timedelta] = None
    trades_last_hour: int = 0
    avg_time_between_trades: Optional[timedelta] = None
    
    # Position sizing behavior
    recent_position_sizes: List[float] = field(default_factory=list)
    size_increasing_after_loss: bool = False
    
    # Stop behavior
    stops_moved_today: int = 0
    stops_widened_today: int = 0
    
    # Override behavior
    signals_overridden_today: int = 0
    good_signals_skipped: int = 0
    bad_signals_taken: int = 0
    
    # Emotional indicators (calculated)
    emotional_state: EmotionalState = EmotionalState.CALM
    behavior_pattern: TradingBehavior = TradingBehavior.NORMAL
    
    # Risk tolerance (dynamic)
    risk_tolerance: float = 1.0  # 1.0 = normal, 0.5 = half, 0 = stop
    
    # Flags
    is_on_tilt: bool = False
    is_revenge_trading: bool = False
    is_overtrading: bool = False
    is_fomo: bool = False
    is_overconfident: bool = False
    trading_allowed: bool = True
    
    # Reason if trading not allowed
    block_reason: Optional[str] = None


@dataclass
class PsychologyRules:
    """Configurable psychology rules"""
    
    # Hard limits
    max_trades_per_day: int = 6
    max_trades_per_hour: int = 2
    max_consecutive_losses: int = 3
    max_consecutive_wins_before_caution: int = 5
    max_daily_loss_percent: float = 2.0
    
    # Time rules
    min_time_between_trades: timedelta = timedelta(minutes=15)
    cooldown_after_loss_streak: timedelta = timedelta(hours=2)
    cooldown_after_tilt: timedelta = timedelta(hours=24)
    
    # Size rules
    max_size_increase_percent: float = 50.0  # Can't increase by more than 50%
    size_after_loss_streak: float = 0.5  # Reduce to 50% after losses
    
    # Recovery rules
    wins_needed_to_reset: int = 2  # 2 wins to reset from caution
```

---

## 🔧 PSYCHOLOGY GUARD ENGINE

```python
class PsychologyGuard:
    """
    The guardian of the trader's mind.
    
    No signal passes through without psychological clearance.
    """
    
    def __init__(self, rules: PsychologyRules = None):
        self.rules = rules or PsychologyRules()
        self.state_history: List[TraderPsychologyState] = []
        self.current_state: TraderPsychologyState = None
        
        # Detection thresholds
        self.tilt_indicators = {
            'rapid_consecutive_trades': 3,  # 3 trades in 15 mins
            'increasing_size_after_loss': True,
            'stop_moving_count': 2,
            'override_count': 2,
        }
    
    def update_state(self, trade_event: Dict) -> TraderPsychologyState:
        """Update psychological state after any trade event"""
        
        if self.current_state is None:
            self.current_state = TraderPsychologyState(
                timestamp=datetime.now(),
                session_start=datetime.now()
            )
        
        state = self.current_state
        
        if trade_event['type'] == 'TRADE_COMPLETED':
            state.trades_today += 1
            
            if trade_event['outcome'] == 'WIN':
                state.wins_today += 1
                state.consecutive_wins += 1
                state.consecutive_losses = 0
            else:
                state.losses_today += 1
                state.consecutive_losses += 1
                state.consecutive_wins = 0
            
            state.current_daily_pnl += trade_event.get('pnl', Decimal("0"))
            state.max_daily_pnl = max(state.max_daily_pnl, state.current_daily_pnl)
            state.min_daily_pnl = min(state.min_daily_pnl, state.current_daily_pnl)
            
            # Track timing
            state.time_since_last_trade = timedelta(seconds=0)
            state.trades_last_hour += 1
        
        elif trade_event['type'] == 'STOP_MOVED':
            state.stops_moved_today += 1
            if trade_event.get('direction') == 'WIDENED':
                state.stops_widened_today += 1
        
        elif trade_event['type'] == 'SIGNAL_OVERRIDDEN':
            state.signals_overridden_today += 1
        
        elif trade_event['type'] == 'POSITION_SIZED':
            state.recent_position_sizes.append(trade_event['size'])
            if len(state.recent_position_sizes) > 1:
                if state.consecutive_losses > 0:
                    if trade_event['size'] > state.recent_position_sizes[-2]:
                        state.size_increasing_after_loss = True
        
        # Recalculate emotional state
        self._calculate_emotional_state(state)
        self._calculate_behavior_pattern(state)
        self._calculate_risk_tolerance(state)
        self._check_if_trading_allowed(state)
        
        self.state_history.append(state)
        return state
    
    def _calculate_emotional_state(self, state: TraderPsychologyState):
        """Determine current emotional state from indicators"""
        
        # DANGER STATES (highest priority)
        if state.consecutive_losses >= 3 and state.trades_last_hour >= 2:
            state.emotional_state = EmotionalState.REVENGE
            state.is_revenge_trading = True
            return
        
        if state.consecutive_losses >= 3:
            state.emotional_state = EmotionalState.TILTED
            state.is_on_tilt = True
            return
        
        if state.consecutive_wins >= 5:
            state.emotional_state = EmotionalState.EUPHORIC
            state.is_overconfident = True
            return
        
        if state.current_daily_pnl < -Decimal(str(self.rules.max_daily_loss_percent)):
            state.emotional_state = EmotionalState.DESPERATE
            return
        
        # WARNING STATES
        if state.trades_last_hour >= 3:
            state.emotional_state = EmotionalState.ANXIOUS
            state.is_overtrading = True
            return
        
        if state.size_increasing_after_loss:
            state.emotional_state = EmotionalState.GREEDY
            return
        
        # Could check other patterns for FOMO, etc.
        
        # HEALTHY STATE
        if state.consecutive_wins >= 1 and state.consecutive_wins <= 3:
            state.emotional_state = EmotionalState.CONFIDENT
        else:
            state.emotional_state = EmotionalState.CALM
    
    def _calculate_behavior_pattern(self, state: TraderPsychologyState):
        """Detect behavioral patterns"""
        
        if state.is_revenge_trading:
            state.behavior_pattern = TradingBehavior.REVENGE_TRADING
        elif state.trades_last_hour >= 3:
            state.behavior_pattern = TradingBehavior.OVERTRADING
        elif state.size_increasing_after_loss:
            state.behavior_pattern = TradingBehavior.AVERAGING_DOWN
        elif state.stops_widened_today >= 2:
            state.behavior_pattern = TradingBehavior.MOVING_STOPS
        elif state.signals_overridden_today >= 2:
            state.behavior_pattern = TradingBehavior.OVERRIDING
        else:
            state.behavior_pattern = TradingBehavior.NORMAL
    
    def _calculate_risk_tolerance(self, state: TraderPsychologyState):
        """Calculate dynamic risk tolerance"""
        
        tolerance = 1.0
        
        # Reduce for losses
        if state.consecutive_losses >= 2:
            tolerance *= 0.5
        
        # Reduce for drawdown
        if state.current_daily_pnl < Decimal("-1"):
            tolerance *= 0.7
        
        # Reduce for overconfidence
        if state.consecutive_wins >= 4:
            tolerance *= 0.7  # Paradoxically reduce when winning streak
        
        # Reduce for behavioral issues
        if state.stops_widened_today > 0:
            tolerance *= 0.8
        
        if state.signals_overridden_today > 0:
            tolerance *= 0.8
        
        state.risk_tolerance = max(0, min(1, tolerance))
    
    def _check_if_trading_allowed(self, state: TraderPsychologyState):
        """Final check: is trading allowed?"""
        
        # HARD STOPS - No exceptions
        
        if state.consecutive_losses >= self.rules.max_consecutive_losses:
            state.trading_allowed = False
            state.block_reason = f"🛑 {state.consecutive_losses} CONSECUTIVE LOSSES: Take a break. Come back in 2 hours."
            return
        
        if state.trades_today >= self.rules.max_trades_per_day:
            state.trading_allowed = False
            state.block_reason = "🛑 MAX TRADES REACHED: You've done enough for today. Come back tomorrow."
            return
        
        if state.current_daily_pnl <= Decimal(str(-self.rules.max_daily_loss_percent)):
            state.trading_allowed = False
            state.block_reason = "🛑 MAX DAILY LOSS: Trading is DONE for today. Protect your capital."
            return
        
        if state.is_on_tilt:
            state.trading_allowed = False
            state.block_reason = "🛑 TILT DETECTED: You're not thinking clearly. WALK AWAY."
            return
        
        if state.is_revenge_trading:
            state.trading_allowed = False
            state.block_reason = "🛑 REVENGE TRADING: You're trying to get back losses. This NEVER works."
            return
        
        # Check timing
        if state.time_since_last_trade and state.time_since_last_trade < self.rules.min_time_between_trades:
            state.trading_allowed = False
            state.block_reason = f"⏰ SLOW DOWN: Wait at least {self.rules.min_time_between_trades.seconds // 60} minutes between trades."
            return
        
        state.trading_allowed = True
        state.block_reason = None
    
    # ═══════════════════════════════════════════════════════════════
    # SIGNAL GATING
    # ═══════════════════════════════════════════════════════════════
    
    def gate_signal(self, signal: Dict) -> Tuple[bool, str, float]:
        """
        The final gate before any signal is executed.
        
        Returns: (allowed, message, position_size_multiplier)
        """
        
        state = self.current_state
        
        if not state.trading_allowed:
            return False, state.block_reason, 0.0
        
        # Apply risk tolerance to position size
        size_multiplier = state.risk_tolerance
        
        # Additional checks based on emotional state
        if state.emotional_state in [EmotionalState.ANXIOUS, EmotionalState.IMPATIENT]:
            size_multiplier *= 0.7
            return True, "⚠️ CAUTION: Reduce size due to elevated stress", size_multiplier
        
        if state.emotional_state in [EmotionalState.EUPHORIC]:
            size_multiplier *= 0.5
            return True, "⚠️ OVERCONFIDENCE: Cutting size in half. Stay humble.", size_multiplier
        
        if state.emotional_state in [EmotionalState.EXCITED]:
            return True, "⚠️ EXCITED: Make sure this is YOUR setup, not FOMO", size_multiplier
        
        return True, "✅ Psychological state: CLEAR", size_multiplier
    
    # ═══════════════════════════════════════════════════════════════
    # INTERVENTION MESSAGES
    # ═══════════════════════════════════════════════════════════════
    
    def get_intervention_message(self, context: str) -> str:
        """Get appropriate intervention message for context"""
        
        messages = {
            'AFTER_LOSS': [
                "One loss means nothing. Stick to the system.",
                "The best traders lose. It's how you RESPOND that matters.",
                "Don't compound this with a revenge trade.",
                "Take 5 deep breaths before your next trade.",
            ],
            'AFTER_WIN_STREAK': [
                "You're not invincible. The market will humble you.",
                "Strings of wins can be random. Don't get cocky.",
                "This is when most accounts blow up. Stay disciplined.",
            ],
            'BEFORE_TRADE': [
                "Is this YOUR setup, or are you CHASING?",
                "Check the checklist. Every. Single. Time.",
                "If you're not 100% sure, you're not trading.",
                "Ask yourself: Would I take this trade with fresh eyes?",
            ],
            'DURING_TRADE': [
                "Let the trade work. Don't micromanage.",
                "Your stop is there for a reason. DON'T MOVE IT.",
                "Walk away from the screen. Watching doesn't help.",
            ],
            'DURING_DRAWDOWN': [
                "Drawdowns are normal. They test your discipline.",
                "This is where winners and losers are separated.",
                "Reduce size, not strategy. Trust the system.",
            ],
            'CONTEMPLATING_OVERRIDE': [
                "Why did you build this system if you won't follow it?",
                "Your emotional brain is trying to take over. DON'T LET IT.",
                "The system has better odds than your gut. Use it.",
            ]
        }
        
        import random
        return random.choice(messages.get(context, ["Stay disciplined."]))
```

---

## 📊 BEHAVIORAL ANALYTICS

```python
class BehavioralAnalytics:
    """
    Analyze trading behavior patterns over time.
    Find your psychological weak points.
    """
    
    def analyze_session(self, trades: List[Dict]) -> Dict:
        """Analyze a trading session for behavioral insights"""
        
        return {
            'total_trades': len(trades),
            'win_rate': self._calculate_win_rate(trades),
            
            # Timing analysis
            'avg_time_between_trades': self._avg_time_between(trades),
            'trades_in_first_hour': self._count_in_period(trades, '09:15', '10:15'),
            'trades_in_last_hour': self._count_in_period(trades, '14:30', '15:30'),
            
            # Behavioral patterns
            'revenge_trades': self._count_revenge_trades(trades),
            'chased_trades': self._count_chased_trades(trades),
            'overridden_signals': self._count_overrides(trades),
            
            # Stop behavior
            'stops_moved': self._count_stops_moved(trades),
            'avg_stop_movement': self._avg_stop_movement(trades),
            
            # Size behavior
            'size_after_loss_pattern': self._analyze_size_after_loss(trades),
            
            # Performance by emotional state
            'pnl_by_state': self._pnl_by_emotional_state(trades),
        }
    
    def get_weakness_report(self, session_analyses: List[Dict]) -> Dict:
        """
        Identify your psychological weak points.
        
        This is uncomfortable but necessary.
        """
        
        weaknesses = []
        
        # Check for overtrading tendency
        avg_trades = sum(s['total_trades'] for s in session_analyses) / len(session_analyses)
        if avg_trades > 5:
            weaknesses.append({
                'weakness': 'OVERTRADING',
                'severity': 'HIGH',
                'evidence': f'Average {avg_trades:.1f} trades/day (target: ≤4)',
                'fix': 'Set a hard limit of 4 trades. After 4, close the platform.',
            })
        
        # Check for revenge trading
        avg_revenge = sum(s['revenge_trades'] for s in session_analyses) / len(session_analyses)
        if avg_revenge > 0.5:
            weaknesses.append({
                'weakness': 'REVENGE_TRADING',
                'severity': 'CRITICAL',
                'evidence': f'Average {avg_revenge:.1f} revenge trades/session',
                'fix': 'After any loss, MANDATORY 30-min break. No exceptions.',
            })
        
        # Check for stop moving
        avg_stop_moves = sum(s['stops_moved'] for s in session_analyses) / len(session_analyses)
        if avg_stop_moves > 1:
            weaknesses.append({
                'weakness': 'STOP_MANIPULATION',
                'severity': 'CRITICAL',
                'evidence': f'Moving stops {avg_stop_moves:.1f} times/session',
                'fix': 'Use bracket orders. Once placed, NO CHANGES allowed.',
            })
        
        # Check for chasing
        avg_chase = sum(s['chased_trades'] for s in session_analyses) / len(session_analyses)
        if avg_chase > 0.5:
            weaknesses.append({
                'weakness': 'FOMO/CHASING',
                'severity': 'HIGH',
                'evidence': f'Chasing {avg_chase:.1f} trades/session',
                'fix': 'If you missed the entry zone by 10 points, NO TRADE.',
            })
        
        return {
            'weaknesses': weaknesses,
            'primary_weakness': weaknesses[0] if weaknesses else None,
            'psychological_score': self._calculate_psych_score(weaknesses),
        }
```

---

## 🎯 DAILY PSYCHOLOGICAL RITUALS

```python
class TradingRituals:
    """
    Mandatory rituals for psychological consistency.
    """
    
    PRE_MARKET_CHECKLIST = [
        "☐ I am well-rested (7+ hours sleep)",
        "☐ I have no urgent personal stress",
        "☐ I have reviewed today's key levels",
        "☐ I know my max loss for today: ___",
        "☐ I know my max trades for today: ___",
        "☐ I accept that I may have ZERO trades today",
        "☐ I accept that I may LOSE today",
        "☐ I will NOT move my stops",
        "☐ I will NOT override the system",
    ]
    
    PRE_TRADE_CHECKLIST = [
        "☐ This is a SYSTEM signal, not my opinion",
        "☐ I have confluence (3+ factors)",
        "☐ I know my exact entry, stop, and target",
        "☐ Risk is ≤1% of capital",
        "☐ I am NOT chasing",
        "☐ I am NOT revenge trading",
        "☐ I will accept the outcome",
    ]
    
    POST_LOSS_PROTOCOL = [
        "1. Close all charts. RIGHT NOW.",
        "2. Stand up. Walk away from desk.",
        "3. Get water. Take 5 deep breaths.",
        "4. Wait MINIMUM 15 minutes.",
        "5. Journal: What happened? Was it my fault or market?",
        "6. If fault was entry timing: forgive yourself.",
        "7. If fault was stop/size: LEARN and RECORD.",
        "8. Only return to charts when CALM.",
    ]
    
    POST_WIN_PROTOCOL = [
        "1. Acknowledge the win. Don't get excited.",
        "2. Ask: Was this luck or skill?",
        "3. If skill: Note what worked.",
        "4. If luck: Don't expect it again.",
        "5. Size stays the SAME. No increasing.",
        "6. Ego stays in CHECK.",
    ]
    
    END_OF_DAY_JOURNAL = """
    ## Today's Trading Journal
    
    ### Stats
    - Trades: ___
    - Wins: ___
    - Losses: ___
    - P&L: ___
    
    ### Emotional State
    - How did I FEEL today? (1-10 calm): ___
    - Did I deviate from the system? ___
    - What triggered me emotionally? ___
    
    ### Lessons
    - What did I learn? ___
    - What will I do differently? ___
    
    ### Grade Myself
    - Discipline (1-10): ___
    - Patience (1-10): ___
    - Execution (1-10): ___
    """
```

---

## ✅ ACCEPTANCE CRITERIA

- [ ] Track all psychological states in real-time
- [ ] Detect revenge trading automatically
- [ ] Detect tilt automatically
- [ ] Hard block trading when psychological state is dangerous
- [ ] Reduce position size when stress is elevated
- [ ] Display intervention messages at critical moments
- [ ] Force cooldowns after loss streaks
- [ ] Analyze behavioral patterns over time
- [ ] Generate weakness reports
- [ ] Mandatory checklists and rituals

---

> **THE UNCOMFORTABLE TRUTH**
>
> We built this system to protect you from the MARKET.
> But the real enemy is YOU.
> 
> Your fear. Your greed. Your ego.
> 
> This component protects you from YOURSELF.
