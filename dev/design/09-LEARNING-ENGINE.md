# 🧠 Learning Engine Service Design

> **Service**: `learning-engine`
> **Purpose**: Learn patterns from historical outcomes, adapt probabilities
> **Independence**: Consumes outcomes, improves system accuracy

---

## 🎯 Responsibilities

1. Track signal and prediction outcomes
2. Learn time-based pattern probabilities
3. Update Markov transition matrices
4. Identify which patterns work best
5. Provide backtesting capabilities
6. Generate accuracy reports

---

## 📐 API Contract

```yaml
POST /api/v1/learn/outcome:
  body:
    type: "SIGNAL" | "PREDICTION" | "PATTERN"
    id: string
    outcome:
      was_correct: bool
      actual_values: {...}
  response:
    recorded: true
    updated_metrics:
      accuracy_before: 0.62
      accuracy_after: 0.63

GET /api/v1/stats/patterns:
  response:
    patterns:
      - pattern: "BULLISH_SWEEP_PDL"
        occurrences: 145
        success_rate: 0.72
        avg_move_atr: 1.8
        best_time: "11:00-12:30"
      - pattern: "BEARISH_SWEEP_PDH"
        occurrences: 132
        success_rate: 0.68
        avg_move_atr: 1.5
        best_time: "11:00-12:30"

GET /api/v1/stats/time:
  response:
    hourly_stats:
      - hour: 9
        sweep_probability: 0.82
        reversal_probability: 0.45
        avg_volatility: 1.2
      - hour: 11
        sweep_probability: 0.31
        reversal_probability: 0.65
        avg_volatility: 0.8

GET /api/v1/backtest:
  parameters:
    from_date: date
    to_date: date
    strategy: string
  response:
    results:
      total_signals: 156
      winners: 98
      losers: 58
      win_rate: 0.628
      total_pnl: 4250
      max_drawdown: -450
      sharpe_ratio: 1.8
```

---

## 📊 Data Models

```python
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, time
from typing import Dict, List, Optional
from collections import defaultdict
import json

@dataclass
class Outcome:
    """A recorded outcome"""
    id: str
    type: str  # SIGNAL, PREDICTION, PATTERN
    timestamp: datetime
    
    # What was predicted
    predicted_direction: str
    predicted_target: Optional[Decimal]
    confidence: float
    
    # What actually happened
    was_correct: bool
    actual_direction: Optional[str]
    actual_move: Optional[Decimal]
    
    # Context for learning
    pattern_name: str
    timeframe: str
    time_of_day: time
    phase: str

@dataclass
class PatternStats:
    """Statistics for a specific pattern"""
    pattern_name: str
    total_occurrences: int = 0
    successful: int = 0
    failed: int = 0
    
    # Performance metrics
    total_pnl: Decimal = Decimal("0")
    avg_move_atr: float = 0.0
    
    # Time analysis
    success_by_hour: Dict[int, float] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        if self.total_occurrences == 0:
            return 0.0
        return self.successful / self.total_occurrences

@dataclass
class TimeStats:
    """Statistics by time of day"""
    hour: int
    
    # Probabilities
    sweep_probability: float = 0.0
    reversal_probability: float = 0.0
    trend_probability: float = 0.0
    
    # Volatility
    avg_atr: float = 0.0
    volatility_rank: float = 0.0  # 0-1
    
    # Signal performance
    signal_success_rate: float = 0.0
    sample_size: int = 0

@dataclass
class BacktestResult:
    """Results from backtesting"""
    from_date: datetime
    to_date: datetime
    strategy: str
    
    # Counts
    total_signals: int
    winners: int
    losers: int
    
    # Performance
    win_rate: float
    total_pnl: Decimal
    max_drawdown: Decimal
    
    # Risk metrics
    sharpe_ratio: float
    profit_factor: float
    
    # Details
    trades: List[Dict]
```

---

## 🔧 Implementation

### OutcomeTracker

```python
import sqlite3
from pathlib import Path

class OutcomeTracker:
    """Track and store all outcomes"""
    
    def __init__(self, db_path: Path = Path("learning.db")):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS outcomes (
                id TEXT PRIMARY KEY,
                type TEXT,
                timestamp TEXT,
                predicted_direction TEXT,
                predicted_target REAL,
                confidence REAL,
                was_correct INTEGER,
                actual_direction TEXT,
                actual_move REAL,
                pattern_name TEXT,
                timeframe TEXT,
                time_hour INTEGER,
                phase TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def record_outcome(self, outcome: Outcome) -> bool:
        """Record a new outcome"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO outcomes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            outcome.id,
            outcome.type,
            outcome.timestamp.isoformat(),
            outcome.predicted_direction,
            float(outcome.predicted_target) if outcome.predicted_target else None,
            outcome.confidence,
            1 if outcome.was_correct else 0,
            outcome.actual_direction,
            float(outcome.actual_move) if outcome.actual_move else None,
            outcome.pattern_name,
            outcome.timeframe,
            outcome.time_of_day.hour,
            outcome.phase
        ))
        
        conn.commit()
        conn.close()
        return True
    
    def get_pattern_stats(self, pattern_name: str = None) -> List[PatternStats]:
        """Get statistics for patterns"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        if pattern_name:
            c.execute('''
                SELECT pattern_name, 
                       COUNT(*) as total,
                       SUM(was_correct) as successes,
                       AVG(actual_move) as avg_move
                FROM outcomes
                WHERE pattern_name = ?
                GROUP BY pattern_name
            ''', (pattern_name,))
        else:
            c.execute('''
                SELECT pattern_name, 
                       COUNT(*) as total,
                       SUM(was_correct) as successes,
                       AVG(actual_move) as avg_move
                FROM outcomes
                GROUP BY pattern_name
            ''')
        
        results = []
        for row in c.fetchall():
            results.append(PatternStats(
                pattern_name=row[0],
                total_occurrences=row[1],
                successful=row[2] or 0,
                failed=(row[1] - (row[2] or 0)),
                avg_move_atr=row[3] or 0.0
            ))
        
        conn.close()
        return results
    
    def get_time_stats(self) -> List[TimeStats]:
        """Get statistics by hour"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT time_hour,
                   COUNT(*) as total,
                   AVG(was_correct) as success_rate,
                   AVG(ABS(actual_move)) as avg_move
            FROM outcomes
            GROUP BY time_hour
            ORDER BY time_hour
        ''')
        
        results = []
        for row in c.fetchall():
            results.append(TimeStats(
                hour=row[0],
                signal_success_rate=row[2] or 0.0,
                avg_atr=row[3] or 0.0,
                sample_size=row[1]
            ))
        
        conn.close()
        return results
```

### MarkovLearner

```python
class MarkovLearner:
    """Learn and update Markov transition probabilities"""
    
    def __init__(self, db_path: Path = Path("markov.json")):
        self.db_path = db_path
        self.transitions = self._load_transitions()
    
    def _load_transitions(self) -> Dict[str, Dict[str, int]]:
        """Load transition counts from file"""
        if self.db_path.exists():
            with open(self.db_path, 'r') as f:
                return json.load(f)
        return defaultdict(lambda: defaultdict(int))
    
    def _save_transitions(self):
        """Save transition counts to file"""
        with open(self.db_path, 'w') as f:
            json.dump(dict(self.transitions), f, indent=2)
    
    def learn_transition(self, from_state: str, to_state: str):
        """Record an observed transition"""
        if from_state not in self.transitions:
            self.transitions[from_state] = defaultdict(int)
        
        self.transitions[from_state][to_state] += 1
        self._save_transitions()
    
    def get_transition_probability(self, from_state: str, to_state: str) -> float:
        """Get probability of transition"""
        if from_state not in self.transitions:
            return 0.0
        
        total = sum(self.transitions[from_state].values())
        if total == 0:
            return 0.0
        
        return self.transitions[from_state].get(to_state, 0) / total
    
    def get_most_likely_next(self, from_state: str) -> Optional[str]:
        """Get most likely next state"""
        if from_state not in self.transitions:
            return None
        
        counts = self.transitions[from_state]
        if not counts:
            return None
        
        return max(counts.items(), key=lambda x: x[1])[0]
    
    def get_all_probabilities(self, from_state: str) -> Dict[str, float]:
        """Get all transition probabilities from a state"""
        if from_state not in self.transitions:
            return {}
        
        total = sum(self.transitions[from_state].values())
        if total == 0:
            return {}
        
        return {
            state: count / total
            for state, count in self.transitions[from_state].items()
        }
```

### PatternAnalyzer

```python
class PatternAnalyzer:
    """Analyze pattern effectiveness"""
    
    def __init__(self, tracker: OutcomeTracker):
        self.tracker = tracker
    
    def get_best_patterns(self, min_samples: int = 20) -> List[Dict]:
        """Get patterns ranked by success rate"""
        stats = self.tracker.get_pattern_stats()
        
        # Filter by minimum samples
        qualified = [s for s in stats if s.total_occurrences >= min_samples]
        
        # Sort by success rate
        ranked = sorted(qualified, key=lambda s: s.success_rate, reverse=True)
        
        return [
            {
                "pattern": s.pattern_name,
                "success_rate": s.success_rate,
                "occurrences": s.total_occurrences,
                "avg_move_atr": s.avg_move_atr
            }
            for s in ranked
        ]
    
    def get_pattern_by_time(self, pattern_name: str) -> Dict[int, float]:
        """Get pattern success rate by hour"""
        conn = sqlite3.connect(self.tracker.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT time_hour, AVG(was_correct) as success_rate
            FROM outcomes
            WHERE pattern_name = ?
            GROUP BY time_hour
        ''', (pattern_name,))
        
        results = {row[0]: row[1] for row in c.fetchall()}
        conn.close()
        
        return results
    
    def get_best_time_for_pattern(self, pattern_name: str) -> Optional[int]:
        """Find the best hour for a specific pattern"""
        by_time = self.get_pattern_by_time(pattern_name)
        
        if not by_time:
            return None
        
        return max(by_time.items(), key=lambda x: x[1])[0]
```

### Backtester

```python
class Backtester:
    """Backtest strategies on historical data"""
    
    def __init__(self, tracker: OutcomeTracker):
        self.tracker = tracker
    
    def run_backtest(
        self,
        from_date: datetime,
        to_date: datetime,
        strategy: str,
        min_confluence: float = 50
    ) -> BacktestResult:
        """Run backtest on historical outcomes"""
        
        conn = sqlite3.connect(self.tracker.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM outcomes
            WHERE timestamp BETWEEN ? AND ?
            AND confidence >= ?
            ORDER BY timestamp
        ''', (from_date.isoformat(), to_date.isoformat(), min_confluence / 100))
        
        trades = []
        total_pnl = Decimal("0")
        peak_pnl = Decimal("0")
        max_drawdown = Decimal("0")
        winners = 0
        losers = 0
        
        for row in c.fetchall():
            was_correct = row[6]
            actual_move = Decimal(str(row[8])) if row[8] else Decimal("0")
            
            if was_correct:
                winners += 1
                total_pnl += actual_move
            else:
                losers += 1
                total_pnl -= actual_move * Decimal("0.5")  # Assume 0.5R loss
            
            peak_pnl = max(peak_pnl, total_pnl)
            drawdown = peak_pnl - total_pnl
            max_drawdown = max(max_drawdown, drawdown)
            
            trades.append({
                "id": row[0],
                "direction": row[3],
                "was_correct": was_correct,
                "pnl": float(actual_move) if was_correct else float(-actual_move * Decimal("0.5"))
            })
        
        conn.close()
        
        total_signals = winners + losers
        win_rate = winners / total_signals if total_signals > 0 else 0
        
        # Calculate Sharpe (simplified)
        if trades:
            pnls = [t["pnl"] for t in trades]
            avg_return = sum(pnls) / len(pnls)
            std_dev = (sum((p - avg_return) ** 2 for p in pnls) / len(pnls)) ** 0.5
            sharpe = avg_return / std_dev if std_dev > 0 else 0
        else:
            sharpe = 0
        
        return BacktestResult(
            from_date=from_date,
            to_date=to_date,
            strategy=strategy,
            total_signals=total_signals,
            winners=winners,
            losers=losers,
            win_rate=win_rate,
            total_pnl=total_pnl,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            profit_factor=float(winners) / losers if losers > 0 else float('inf'),
            trades=trades
        )
```

---

## 📤 Events Published

```python
@dataclass
class LearningUpdateEvent:
    event_type: str = "learning.updated"
    pattern: str
    new_success_rate: float
    sample_size: int
    timestamp: datetime

@dataclass
class AccuracyReportEvent:
    event_type: str = "learning.accuracy.report"
    overall_accuracy: float
    best_patterns: List[str]
    worst_patterns: List[str]
    timestamp: datetime
```

---

## ✅ Acceptance Criteria

- [ ] Records all signal and prediction outcomes
- [ ] Calculates pattern success rates
- [ ] Tracks performance by time of day
- [ ] Updates Markov transition probabilities
- [ ] Provides backtesting capabilities
- [ ] Identifies best/worst patterns
- [ ] Persists learning data to disk
- [ ] Generates accuracy reports
