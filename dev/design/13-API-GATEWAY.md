# 🚪 API Gateway Service Design

> **Service**: `api-gateway`
> **Purpose**: Single entry point for all client requests
> **Stack**: FastAPI + uvicorn

---

## 🎯 Responsibilities

1. Route requests to appropriate services
2. Authentication (future, currently none for personal use)
3. Rate limiting
4. Request validation
5. Response aggregation
6. WebSocket proxy for real-time updates
7. API versioning

---

## 📐 API Structure

```yaml
Base URL: http://localhost:8000/api/v1

Routes:
  # Data Feed
  /data/symbols                    → data-feed
  /data/historical/{symbol}        → data-feed
  /data/quote/{symbol}             → data-feed
  
  # Structure Analysis
  /analysis/swings/{symbol}        → structure-analyzer
  /analysis/structure/{symbol}     → structure-analyzer
  /analysis/fibonacci/{symbol}     → structure-analyzer
  
  # Liquidity
  /liquidity/pools/{symbol}        → liquidity-mapper
  /liquidity/levels/{symbol}       → liquidity-mapper
  /liquidity/heatmap/{symbol}      → liquidity-mapper
  
  # Detection
  /detection/orderblocks/{symbol}  → detection-engine
  /detection/fvgs/{symbol}         → detection-engine
  /detection/traps/{symbol}        → detection-engine
  
  # Context
  /context/{symbol}                → context-engine
  /context/killzones               → context-engine
  /context/htf-bias/{symbol}       → context-engine
  
  # Predictions
  /prediction/scenarios/{symbol}   → prediction-engine
  /prediction/paths/{symbol}       → prediction-engine
  /prediction/next-day/{symbol}    → next-day-projector
  
  # Signals
  /signals/{symbol}                → signal-generator
  /signals/{id}/outcome            → signal-generator
  /signals/history                 → signal-history
  
  # Learning
  /learning/patterns               → learning-engine
  /learning/stats                  → learning-engine
  /learning/backtest               → learning-engine
  
  # Protection
  /risk/{symbol}                   → protection-layer
  /risk/alerts                     → protection-layer
  /risk/validate-signal            → protection-layer
  
  # Pre-Market
  /premarket/{symbol}              → premarket-analyzer
  /premarket/projection/{symbol}   → next-day-projector
  
  # Replay
  /replay/start                    → replay-engine
  /replay/{id}/control             → replay-engine
  /replay/{id}/status              → replay-engine
  /replay/{id}/results             → replay-engine
  
  # System
  /health                          → all services
  /metrics                         → system metrics

WebSocket:
  /ws/live                         → Real-time candle updates
  /ws/signals                      → Real-time signal updates
  /ws/alerts                       → Real-time alerts
```

---

## 📊 Implementation

```python
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(
    title="RADAR API Gateway",
    version="1.0.0",
    description="Unified API for RADAR trading system"
)

# CORS for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Dashboard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service registry
SERVICES = {
    "data-feed": "http://localhost:8001",
    "structure-analyzer": "http://localhost:8002",
    "liquidity-mapper": "http://localhost:8003",
    "detection-engine": "http://localhost:8004",
    "context-engine": "http://localhost:8005",
    "prediction-engine": "http://localhost:8006",
    "signal-generator": "http://localhost:8007",
    "learning-engine": "http://localhost:8008",
    "protection-layer": "http://localhost:8009",
    "replay-engine": "http://localhost:8010",
}

class ServiceProxy:
    """Proxy requests to backend services"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def forward(self, service: str, path: str, method: str = "GET", **kwargs):
        """Forward request to service"""
        base_url = SERVICES.get(service)
        if not base_url:
            raise HTTPException(404, f"Service {service} not found")
        
        url = f"{base_url}{path}"
        
        try:
            response = await self.client.request(method, url, **kwargs)
            return response.json()
        except httpx.RequestError as e:
            raise HTTPException(503, f"Service {service} unavailable: {str(e)}")

proxy = ServiceProxy()

# ═══════════════════════════════════════════════════════════════
# DATA ROUTES
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/data/symbols")
async def get_symbols():
    return await proxy.forward("data-feed", "/api/v1/symbols")

@app.get("/api/v1/data/historical/{symbol}")
async def get_historical(
    symbol: str,
    timeframe: str = "15m",
    from_date: str = None,
    to_date: str = None
):
    params = {"timeframe": timeframe}
    if from_date:
        params["from_date"] = from_date
    if to_date:
        params["to_date"] = to_date
    
    return await proxy.forward(
        "data-feed", 
        f"/api/v1/historical/{symbol}",
        params=params
    )

# ═══════════════════════════════════════════════════════════════
# ANALYSIS ROUTES
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/analysis/swings/{symbol}")
async def get_swings(symbol: str, timeframe: str = "15m", lookback: int = 100):
    return await proxy.forward(
        "structure-analyzer",
        f"/api/v1/swings/{symbol}",
        params={"timeframe": timeframe, "lookback": lookback}
    )

@app.get("/api/v1/analysis/structure/{symbol}")
async def get_structure(symbol: str, timeframe: str = "15m"):
    return await proxy.forward(
        "structure-analyzer",
        f"/api/v1/structure/{symbol}",
        params={"timeframe": timeframe}
    )

@app.get("/api/v1/analysis/fibonacci/{symbol}")
async def get_fibonacci(symbol: str, timeframe: str = "15m"):
    return await proxy.forward(
        "structure-analyzer",
        f"/api/v1/fibonacci/{symbol}",
        params={"timeframe": timeframe}
    )

# ═══════════════════════════════════════════════════════════════
# AGGREGATED ROUTES (Combine multiple services)
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/dashboard/{symbol}")
async def get_dashboard_data(symbol: str, timeframe: str = "15m"):
    """Get all data needed for dashboard in one call"""
    
    import asyncio
    
    # Parallel requests to all services
    [
        candles,
        structure,
        orderblocks,
        fvgs,
        liquidity,
        context,
        signals,
        risk
    ] = await asyncio.gather(
        proxy.forward("data-feed", f"/api/v1/historical/{symbol}", params={"timeframe": timeframe, "lookback": 200}),
        proxy.forward("structure-analyzer", f"/api/v1/structure/{symbol}"),
        proxy.forward("detection-engine", f"/api/v1/orderblocks/{symbol}"),
        proxy.forward("detection-engine", f"/api/v1/fvgs/{symbol}"),
        proxy.forward("liquidity-mapper", f"/api/v1/pools/{symbol}"),
        proxy.forward("context-engine", f"/api/v1/context/{symbol}"),
        proxy.forward("signal-generator", f"/api/v1/signals/{symbol}"),
        proxy.forward("protection-layer", f"/api/v1/risk-assessment/{symbol}"),
    )
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": candles,
        "structure": structure,
        "orderblocks": orderblocks,
        "fvgs": fvgs,
        "liquidity": liquidity,
        "context": context,
        "signals": signals,
        "risk": risk
    }

# ═══════════════════════════════════════════════════════════════
# WEBSOCKET
# ═══════════════════════════════════════════════════════════════

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive messages from client (subscriptions)
            data = await websocket.receive_json()
            
            if data.get("action") == "subscribe":
                # Subscribe to symbol updates
                symbol = data.get("symbol")
                # Add to subscription list
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ═══════════════════════════════════════════════════════════════
# HEALTH & METRICS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/health")
async def health_check():
    """Check health of all services"""
    import asyncio
    
    async def check_service(name, url):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/health")
                return name, response.status_code == 200
        except:
            return name, False
    
    results = await asyncio.gather(*[
        check_service(name, url) 
        for name, url in SERVICES.items()
    ])
    
    status = {name: healthy for name, healthy in results}
    all_healthy = all(status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": status
    }
```

---

## 🔧 Configuration

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Services
    data_feed_url: str = "http://localhost:8001"
    structure_analyzer_url: str = "http://localhost:8002"
    liquidity_mapper_url: str = "http://localhost:8003"
    detection_engine_url: str = "http://localhost:8004"
    context_engine_url: str = "http://localhost:8005"
    prediction_engine_url: str = "http://localhost:8006"
    signal_generator_url: str = "http://localhost:8007"
    learning_engine_url: str = "http://localhost:8008"
    protection_layer_url: str = "http://localhost:8009"
    replay_engine_url: str = "http://localhost:8010"
    
    # Redis (for pub/sub)
    redis_url: str = "redis://localhost:6379"
    
    # Timeouts
    request_timeout: int = 30
    
    class Config:
        env_prefix = "RADAR_"
```

---

## ✅ Acceptance Criteria

- [ ] Routes all requests to correct services
- [ ] Aggregates dashboard data in single call
- [ ] WebSocket support for real-time updates
- [ ] Health check for all services
- [ ] CORS configured for web dashboard
- [ ] Request timeout handling
- [ ] Error responses are consistent
