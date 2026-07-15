# 🔄 Replay Engine Service Design

> **Service**: `replay-engine`
> **Purpose**: Replay historical market data to test and train the system
> **Independence**: Simulates market at any speed for backtesting

---

## 🎯 Responsibilities

1. Load historical data for any date range
2. Replay candles at configurable speed
3. Simulate live market conditions
4. Allow pausing, rewinding, fast-forwarding
5. Collect metrics during replay
6. Support multiple simultaneous replays

---

## 📐 API Contract

```yaml
POST /api/v1/replay/start:
  body:
    symbol: "NIFTY 50"
    from_date: "2025-01-01"
    to_date: "2025-01-31"
    timeframe: "15m"
    speed: 10  # 10x realtime
  response:
    replay_id: "replay_abc123"
    total_candles: 450
    estimated_duration: "45 minutes at 10x"
    status: "RUNNING"

POST /api/v1/replay/{replay_id}/control:
  body:
    action: "PAUSE" | "RESUME" | "STOP" | "REWIND" | "FAST_FORWARD"
    target_time: "2025-01-15T10:30:00"  # For rewind
    speed: 50  # New speed for changes
  response:
    status: "PAUSED"
    current_time: "2025-01-10T11:15:00"
    candles_processed: 150

GET /api/v1/replay/{replay_id}/status:
  response:
    replay_id: "replay_abc123"
    status: "RUNNING"
    current_time: "2025-01-15T14:30:00"
    candles_processed: 250
    candles_remaining: 200
    signals_generated: 12
    signals_correct: 8
    signals_incorrect: 3
    signals_pending: 1

GET /api/v1/replay/{replay_id}/results:
  response:
    summary:
      total_signals: 45
      winners: 32
      losers: 13
      win_rate: 0.711
      total_pnl: 1250
    by_day: [...]
    by_pattern: [...]
    failures: [...]
```

---

## 📊 Data Models

```python
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Dict, Optional
from enum import Enum

class ReplayStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

@dataclass
class ReplaySession:
    """A replay session"""
    id: str
    symbol: str
    timeframe: str
    
    # Time range
    from_date: date
    to_date: date
    
    # Control
    speed: float  # Multiplier (1 = realtime, 10 = 10x)
    status: ReplayStatus
    
    # Progress
    current_time: datetime
    candles_processed: int
    total_candles: int
    
    # Results
    signals_generated: List[Dict]
    outcomes: List[Dict]
    
    # Metrics
    metrics: ReplayMetrics

@dataclass
class ReplayMetrics:
    """Metrics collected during replay"""
    total_signals: int = 0
    winners: int = 0
    losers: int = 0
    pending: int = 0
    
    total_pnl: Decimal = Decimal("0")
    max_drawdown: Decimal = Decimal("0")
    
    by_pattern: Dict[str, Dict] = field(default_factory=dict)
    by_hour: Dict[int, Dict] = field(default_factory=dict)
    by_day_of_week: Dict[str, Dict] = field(default_factory=dict)
    
    failures: List[Dict] = field(default_factory=list)
```

---

## 🔧 Implementation

```python
import asyncio
from typing import Callable

class ReplayEngine:
    """Engine for replaying historical market data"""
    
    def __init__(self, data_feed, analysis_stack):
        self.data_feed = data_feed
        self.analysis_stack = analysis_stack  # All analysis services
        self.active_replays: Dict[str, ReplaySession] = {}
    
    async def start_replay(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        timeframe: str,
        speed: float = 1.0,
        on_signal: Callable = None,
        on_candle: Callable = None
    ) -> str:
        """Start a new replay session"""
        
        # Load historical data
        candles = await self.data_feed.get_historical(
            symbol=symbol,
            from_date=from_date,
            to_date=to_date,
            timeframe=timeframe
        )
        
        # Create session
        replay_id = f"replay_{uuid.uuid4().hex[:8]}"
        session = ReplaySession(
            id=replay_id,
            symbol=symbol,
            timeframe=timeframe,
            from_date=from_date,
            to_date=to_date,
            speed=speed,
            status=ReplayStatus.RUNNING,
            current_time=candles[0].timestamp,
            candles_processed=0,
            total_candles=len(candles),
            signals_generated=[],
            outcomes=[],
            metrics=ReplayMetrics()
        )
        
        self.active_replays[replay_id] = session
        
        # Start replay loop
        asyncio.create_task(self._run_replay(session, candles, on_signal, on_candle))
        
        return replay_id
    
    async def _run_replay(
        self,
        session: ReplaySession,
        candles: List[Candle],
        on_signal: Callable,
        on_candle: Callable
    ):
        """Run the replay loop"""
        
        # Calculate delay between candles based on speed
        base_delay = self._get_timeframe_seconds(session.timeframe)
        
        for i, candle in enumerate(candles):
            # Check if paused or stopped
            while session.status == ReplayStatus.PAUSED:
                await asyncio.sleep(0.1)
            
            if session.status == ReplayStatus.STOPPED:
                break
            
            # Update session state
            session.current_time = candle.timestamp
            session.candles_processed = i + 1
            
            # Feed candle to analysis stack
            historical = candles[:i+1]
            future = candles[i+1:i+51] if i+1 < len(candles) else []
            
            # Run analysis
            context = await self.analysis_stack.analyze(historical)
            
            # Generate signal
            signal = await self.analysis_stack.generate_signal(context)
            
            if signal:
                session.signals_generated.append({
                    "signal": signal,
                    "candle_index": i,
                    "context": context
                })
                session.metrics.total_signals += 1
                
                if on_signal:
                    await on_signal(signal)
            
            # Check outcomes for pending signals
            await self._check_pending_outcomes(session, historical, future)
            
            # Callback
            if on_candle:
                await on_candle(candle, i, len(candles))
            
            # Delay based on speed
            delay = base_delay / session.speed
            if delay > 0:
                await asyncio.sleep(delay)
        
        session.status = ReplayStatus.COMPLETED
        
        # Final metrics
        self._calculate_final_metrics(session)
    
    async def _check_pending_outcomes(
        self,
        session: ReplaySession,
        historical: List[Candle],
        future: List[Candle]
    ):
        """Check if any pending signals have resolved"""
        
        for sig_data in session.signals_generated:
            if sig_data.get('resolved'):
                continue
            
            signal = sig_data['signal']
            
            # Check if signal has been triggered and resolved
            outcome = self._check_signal_outcome(signal, future)
            
            if outcome:
                sig_data['resolved'] = True
                sig_data['outcome'] = outcome
                session.outcomes.append(outcome)
                
                if outcome['was_winner']:
                    session.metrics.winners += 1
                    session.metrics.total_pnl += outcome['pnl']
                else:
                    session.metrics.losers += 1
                    session.metrics.total_pnl += outcome['pnl']
                    
                    # Record failure for learning
                    session.metrics.failures.append({
                        "signal": signal,
                        "outcome": outcome,
                        "context": sig_data['context']
                    })
    
    def control_replay(self, replay_id: str, action: str, **kwargs):
        """Control a running replay"""
        
        session = self.active_replays.get(replay_id)
        if not session:
            raise ValueError(f"Replay {replay_id} not found")
        
        if action == "PAUSE":
            session.status = ReplayStatus.PAUSED
        elif action == "RESUME":
            session.status = ReplayStatus.RUNNING
        elif action == "STOP":
            session.status = ReplayStatus.STOPPED
        elif action == "SPEED":
            session.speed = kwargs.get('speed', session.speed)
```

---

## ✅ Acceptance Criteria

- [ ] Loads historical data for any date range
- [ ] Replays at configurable speeds (1x to 100x)
- [ ] Supports pause, resume, stop, rewind
- [ ] Generates signals as if live market
- [ ] Tracks all outcomes and metrics
- [ ] Records failures for learning
- [ ] Multiple concurrent replays supported
