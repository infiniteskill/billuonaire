# 📬 Event Bus Service Design

> **Service**: `event-bus`
> **Purpose**: Asynchronous communication between services
> **Stack**: Redis Pub/Sub

---

## 🎯 Responsibilities

1. Publish events from any service
2. Subscribe services to event channels
3. Ensure message delivery
4. Event persistence for replay
5. Dead letter queue for failed events

---

## 📐 Event Channels

```yaml
Channels:
  # Data events
  candle.new.{symbol}.{timeframe}:
    description: New candle received
    payload: Candle
    
  candle.processed.{symbol}:
    description: Candle validated and enriched
    payload: ProcessedCandle
  
  # Structure events
  structure.swing.new:
    description: New swing point detected
    payload: SwingPoint
    
  structure.bos.detected:
    description: Break of Structure detected
    payload: StructureEvent
    
  structure.choch.detected:
    description: Change of Character detected
    payload: StructureEvent
  
  # Liquidity events
  liquidity.pool.new:
    description: New liquidity pool identified
    payload: LiquidityPool
    
  liquidity.sweep.detected:
    description: Liquidity sweep occurred
    payload: SweepEvent
  
  # Detection events
  detection.ob.new:
    description: New Order Block formed
    payload: OrderBlock
    
  detection.ob.mitigated:
    description: Order Block touched/mitigated
    payload: OrderBlock
    
  detection.fvg.new:
    description: New Fair Value Gap
    payload: FairValueGap
    
  detection.fvg.filled:
    description: FVG completely filled
    payload: FairValueGap
    
  detection.trap.alert:
    description: Manipulation trap detected
    payload: Trap
  
  # Context events
  context.phase.changed:
    description: AMD phase changed
    payload: PhaseChange
    
  context.killzone.entered:
    description: Entered a kill zone
    payload: KillZoneEvent
    
  context.killzone.exited:
    description: Exited a kill zone
    payload: KillZoneEvent
  
  # Signal events
  signal.new:
    description: New signal generated
    payload: Signal
    
  signal.triggered:
    description: Signal entry triggered
    payload: SignalTrigger
    
  signal.outcome:
    description: Signal concluded
    payload: SignalOutcome
  
  # Learning events
  learning.outcome.recorded:
    description: New outcome recorded for learning
    payload: Outcome
    
  learning.tree.evolved:
    description: Decision tree updated
    payload: TreeEvolution
    
  learning.pattern.discovered:
    description: New manipulation pattern found
    payload: PatternDiscovery
  
  # Alert events
  alert.risk.high:
    description: Risk level elevated
    payload: RiskAlert
    
  alert.volatility.spike:
    description: Unusual volatility detected
    payload: VolatilityAlert
    
  alert.manipulation.detected:
    description: Manipulation tactic in progress
    payload: ManipulationAlert
```

---

## 📊 Event Schema

```python
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict
import json

@dataclass
class Event:
    """Base event structure"""
    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    source_service: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    correlation_id: Optional[str] = None  # For tracking related events
    retry_count: int = 0
    
    def to_json(self) -> str:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Event':
        data = json.loads(json_str)
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

# Specific event types
@dataclass
class CandleEvent(Event):
    event_type: str = "candle.new"
    
    def __post_init__(self):
        self.payload = {
            "symbol": self.payload.get("symbol"),
            "timeframe": self.payload.get("timeframe"),
            "candle": self.payload.get("candle")
        }

@dataclass
class SignalEvent(Event):
    event_type: str = "signal.new"

@dataclass
class SweepEvent(Event):
    event_type: str = "liquidity.sweep.detected"

@dataclass
class PhaseChangeEvent(Event):
    event_type: str = "context.phase.changed"
```

---

## 🔧 Implementation

```python
import redis.asyncio as redis
import asyncio
from typing import Callable, List
import structlog

logger = structlog.get_logger()

class EventBus:
    """Redis-based event bus for service communication"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: redis.Redis = None
        self.pubsub: redis.client.PubSub = None
        self.handlers: Dict[str, List[Callable]] = {}
        self.running = False
    
    async def connect(self):
        """Connect to Redis"""
        self.redis = await redis.from_url(self.redis_url)
        self.pubsub = self.redis.pubsub()
        logger.info("event_bus_connected", url=self.redis_url)
    
    async def disconnect(self):
        """Disconnect from Redis"""
        self.running = False
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
    
    # ═══════════════════════════════════════════════════════════════
    # PUBLISHING
    # ═══════════════════════════════════════════════════════════════
    
    async def publish(self, event: Event):
        """Publish an event to the bus"""
        channel = event.event_type
        message = event.to_json()
        
        # Publish to Redis
        await self.redis.publish(channel, message)
        
        # Store in stream for persistence
        await self.redis.xadd(
            f"events:{channel}",
            {"data": message},
            maxlen=10000  # Keep last 10k events per channel
        )
        
        logger.info(
            "event_published",
            event_id=event.event_id,
            event_type=event.event_type,
            source=event.source_service
        )
    
    async def publish_many(self, events: List[Event]):
        """Publish multiple events"""
        async with self.redis.pipeline() as pipe:
            for event in events:
                channel = event.event_type
                message = event.to_json()
                pipe.publish(channel, message)
                pipe.xadd(f"events:{channel}", {"data": message}, maxlen=10000)
            await pipe.execute()
    
    # ═══════════════════════════════════════════════════════════════
    # SUBSCRIBING
    # ═══════════════════════════════════════════════════════════════
    
    async def subscribe(self, pattern: str, handler: Callable):
        """Subscribe to events matching pattern"""
        if pattern not in self.handlers:
            self.handlers[pattern] = []
            await self.pubsub.psubscribe(pattern)
        
        self.handlers[pattern].append(handler)
        logger.info("subscribed_to_pattern", pattern=pattern)
    
    async def unsubscribe(self, pattern: str, handler: Callable = None):
        """Unsubscribe from pattern"""
        if pattern in self.handlers:
            if handler:
                self.handlers[pattern].remove(handler)
            else:
                self.handlers[pattern] = []
            
            if not self.handlers[pattern]:
                await self.pubsub.punsubscribe(pattern)
    
    async def start_listening(self):
        """Start listening for events"""
        self.running = True
        
        async for message in self.pubsub.listen():
            if not self.running:
                break
            
            if message['type'] == 'pmessage':
                pattern = message['pattern'].decode()
                channel = message['channel'].decode()
                data = message['data'].decode()
                
                # Parse event
                try:
                    event = Event.from_json(data)
                except Exception as e:
                    logger.error("event_parse_error", error=str(e), data=data)
                    continue
                
                # Call handlers
                for handler in self.handlers.get(pattern, []):
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error(
                            "handler_error",
                            error=str(e),
                            event_id=event.event_id,
                            handler=handler.__name__
                        )
                        # Send to dead letter queue
                        await self._dead_letter(event, str(e))
    
    # ═══════════════════════════════════════════════════════════════
    # REPLAY & PERSISTENCE
    # ═══════════════════════════════════════════════════════════════
    
    async def replay_events(
        self,
        channel: str,
        from_time: datetime = None,
        to_time: datetime = None,
        handler: Callable = None
    ):
        """Replay historical events from a channel"""
        stream_key = f"events:{channel}"
        
        # Convert times to Redis stream IDs
        start = f"{int(from_time.timestamp() * 1000)}-0" if from_time else "-"
        end = f"{int(to_time.timestamp() * 1000)}-0" if to_time else "+"
        
        events = await self.redis.xrange(stream_key, start, end)
        
        for event_id, data in events:
            event = Event.from_json(data[b'data'].decode())
            if handler:
                await handler(event)
            yield event
    
    async def get_recent_events(self, channel: str, count: int = 100) -> List[Event]:
        """Get recent events from a channel"""
        stream_key = f"events:{channel}"
        events = await self.redis.xrevrange(stream_key, count=count)
        
        return [
            Event.from_json(data[b'data'].decode())
            for _, data in events
        ]
    
    # ═══════════════════════════════════════════════════════════════
    # DEAD LETTER QUEUE
    # ═══════════════════════════════════════════════════════════════
    
    async def _dead_letter(self, event: Event, error: str):
        """Send failed event to dead letter queue"""
        await self.redis.xadd(
            "events:dead_letter",
            {
                "event": event.to_json(),
                "error": error,
                "failed_at": datetime.now().isoformat()
            },
            maxlen=1000
        )
    
    async def retry_dead_letters(self, max_retries: int = 3):
        """Retry processing dead letter events"""
        dead_letters = await self.redis.xrange("events:dead_letter")
        
        for event_id, data in dead_letters:
            event = Event.from_json(data[b'event'].decode())
            
            if event.retry_count >= max_retries:
                logger.warning("event_max_retries", event_id=event.event_id)
                continue
            
            event.retry_count += 1
            await self.publish(event)
            
            # Remove from dead letter queue
            await self.redis.xdel("events:dead_letter", event_id)
```

---

## 🔌 Service Integration

```python
# Example: How services use the event bus

class StructureAnalyzerService:
    """Structure analyzer service with event bus integration"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def start(self):
        # Subscribe to candle events
        await self.event_bus.subscribe("candle.processed.*", self.on_candle)
    
    async def on_candle(self, event: Event):
        """Handle new candle event"""
        candle = event.payload.get('candle')
        symbol = event.payload.get('symbol')
        
        # Analyze candle
        swing = self.detect_swing(candle)
        
        if swing:
            # Publish swing event
            await self.event_bus.publish(Event(
                event_type="structure.swing.new",
                source_service="structure-analyzer",
                payload={
                    "symbol": symbol,
                    "swing": swing
                }
            ))
        
        # Check for BOS/CHoCH
        structure_event = self.check_structure(candle)
        
        if structure_event:
            event_type = f"structure.{structure_event.type.lower()}.detected"
            await self.event_bus.publish(Event(
                event_type=event_type,
                source_service="structure-analyzer",
                payload={
                    "symbol": symbol,
                    "event": structure_event
                }
            ))
```

---

## 📊 Monitoring

```python
# Event bus metrics
class EventBusMetrics:
    """Collect event bus metrics"""
    
    def __init__(self, redis: redis.Redis):
        self.redis = redis
    
    async def get_metrics(self) -> Dict:
        """Get current metrics"""
        return {
            "total_events_today": await self._count_today(),
            "events_per_channel": await self._events_by_channel(),
            "dead_letter_count": await self._dead_letter_count(),
            "avg_latency_ms": await self._average_latency()
        }
    
    async def _count_today(self) -> int:
        # Count events from today
        ...
    
    async def _events_by_channel(self) -> Dict[str, int]:
        # Count events per channel
        ...
```

---

## ✅ Acceptance Criteria

- [ ] Pub/Sub working with Redis
- [ ] Event persistence in Redis Streams
- [ ] Pattern-based subscriptions
- [ ] Dead letter queue for failures
- [ ] Event replay capability
- [ ] Multiple handlers per channel
- [ ] Structured logging for all events
- [ ] Metrics collection
