# 📡 Data Feed Service Design

> **Service**: `data-feed`
> **Purpose**: Fetch and stream OHLC data for any symbol
> **Independence**: Fully standalone, no dependencies on other services

---

## 🎯 Responsibilities

1. Fetch historical OHLC data
2. Provide real-time price updates
3. Support multiple symbols concurrently
4. Cache data to reduce API calls
5. Handle rate limiting gracefully
6. Emit events for new candles

---

## 📐 API Contract

### REST Endpoints

```yaml
GET /api/v1/symbols:
  description: List available symbols
  response:
    symbols:
      - symbol: "NIFTY 50"
        name: "Nifty 50 Index"
        exchange: "NSE"
        type: "INDEX"
      - symbol: "RELIANCE"
        name: "Reliance Industries Ltd"
        exchange: "NSE"
        type: "EQUITY"

GET /api/v1/candles/{symbol}:
  parameters:
    symbol: string (required)
    timeframe: string (default: "15m") # 1m, 5m, 15m, 1h, 4h, 1d
    from_date: date (required)
    to_date: date (required)
  response:
    symbol: "NIFTY 50"
    timeframe: "15m"
    candles:
      - timestamp: "2025-01-31T09:15:00+05:30"
        open: 22450.50
        high: 22465.75
        low: 22440.00
        close: 22455.25
        volume: 1234567

GET /api/v1/quote/{symbol}:
  description: Get current live quote
  response:
    symbol: "NIFTY 50"
    last_price: 22455.25
    change: -35.50
    change_percent: -0.16
    high: 22490.00
    low: 22420.00
    open: 22480.00
    timestamp: "2025-01-31T14:30:15+05:30"

POST /api/v1/subscribe:
  description: Subscribe to real-time updates
  body:
    symbols: ["NIFTY 50", "BANKNIFTY"]
  response:
    subscription_id: "sub_abc123"
    websocket_url: "ws://localhost:8001/ws/sub_abc123"
```

### WebSocket Events

```yaml
# Client sends
{
  "action": "subscribe",
  "symbols": ["NIFTY 50", "BANKNIFTY"]
}

# Server sends (on each tick)
{
  "event": "candle.update",
  "data": {
    "symbol": "NIFTY 50",
    "timeframe": "15m",
    "candle": {
      "timestamp": "2025-01-31T14:30:00+05:30",
      "open": 22450.50,
      "high": 22465.75,
      "low": 22440.00,
      "close": 22455.25,
      "is_closed": false
    }
  }
}

# Server sends (on candle close)
{
  "event": "candle.closed",
  "data": {
    "symbol": "NIFTY 50",
    "timeframe": "15m",
    "candle": { ... },
    "is_closed": true
  }
}
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA-FEED SERVICE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    API LAYER (FastAPI)                       ││
│  │  /symbols  /candles/{symbol}  /quote/{symbol}  /subscribe   ││
│  └───────────────────────────┬─────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │                    DATA MANAGER                              ││
│  │                                                              ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       ││
│  │  │ Historical   │  │ Live Quote   │  │ Candle       │       ││
│  │  │ Fetcher      │  │ Fetcher      │  │ Aggregator   │       ││
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       ││
│  │         │                 │                 │                ││
│  │         └─────────────────┴─────────────────┘                ││
│  │                           │                                   ││
│  └───────────────────────────┼──────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │                    DATA SOURCES                              ││
│  │                                                              ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       ││
│  │  │ jugaad-data  │  │ NSE Direct   │  │ CSV Fallback │       ││
│  │  │ (Primary)    │  │ (Backup)     │  │ (Offline)    │       ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘       ││
│  │                                                              ││
│  └──────────────────────────────────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │                    CACHE LAYER (Redis)                       ││
│  │  Historical: 1 day TTL  │  Live: 5 sec TTL  │  Symbols: 1hr ││
│  └──────────────────────────────────────────────────────────────┘│
│                              │                                   │
│  ┌───────────────────────────▼─────────────────────────────────┐│
│  │                    EVENT EMITTER                             ││
│  │  Publishes: data.candle.new, data.candle.closed              ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Models

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from enum import Enum

class Timeframe(Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"

@dataclass(frozen=True)
class Symbol:
    """Immutable symbol definition"""
    code: str           # "NIFTY 50", "RELIANCE"
    name: str           # Full name
    exchange: str       # "NSE", "BSE"
    type: Literal["INDEX", "EQUITY", "FUTURES", "OPTIONS"]
    lot_size: int = 1
    tick_size: Decimal = Decimal("0.05")

@dataclass
class Candle:
    """Single OHLC candle"""
    symbol: str
    timeframe: Timeframe
    timestamp: datetime      # Candle START time
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int = 0
    is_closed: bool = True
    
    def __post_init__(self):
        # Validate OHLC relationship
        assert self.high >= self.open, "High must be >= Open"
        assert self.high >= self.close, "High must be >= Close"
        assert self.low <= self.open, "Low must be <= Open"
        assert self.low <= self.close, "Low must be <= Close"
        assert self.high >= self.low, "High must be >= Low"
    
    @property
    def range(self) -> Decimal:
        return self.high - self.low
    
    @property
    def body(self) -> Decimal:
        return abs(self.close - self.open)
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open
    
    @property
    def upper_wick(self) -> Decimal:
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> Decimal:
        return min(self.open, self.close) - self.low

@dataclass
class Quote:
    """Real-time quote"""
    symbol: str
    last_price: Decimal
    change: Decimal
    change_percent: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    close: Optional[Decimal]  # Previous close
    volume: int
    timestamp: datetime
    
@dataclass
class CandleRequest:
    """Request for historical candles"""
    symbol: str
    timeframe: Timeframe
    from_date: datetime
    to_date: datetime
    
@dataclass
class CandleResponse:
    """Response with historical candles"""
    symbol: str
    timeframe: Timeframe
    candles: list[Candle]
    from_date: datetime
    to_date: datetime
    is_complete: bool = True
    missing_dates: list[datetime] = None
```

---

## 🔧 Implementation

### DataSourceInterface

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class DataSourceInterface(ABC):
    """Interface for all data sources"""
    
    @abstractmethod
    async def get_symbols(self, exchange: str = None) -> List[Symbol]:
        """Get list of available symbols"""
        pass
    
    @abstractmethod
    async def get_historical(self, request: CandleRequest) -> CandleResponse:
        """Get historical candles"""
        pass
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if data source is available"""
        pass
```

### JugaadDataSource

```python
from jugaad_data.nse import stock_df, NSELive
from datetime import date, datetime
import pandas as pd

class JugaadDataSource(DataSourceInterface):
    """Primary data source using jugaad-data"""
    
    def __init__(self, cache_ttl: int = 300):
        self.nse_live = NSELive()
        self.cache_ttl = cache_ttl
        self._symbol_cache = None
        self._symbol_cache_time = None
    
    async def get_historical(self, request: CandleRequest) -> CandleResponse:
        """
        Fetch historical data from NSE via jugaad-data.
        
        Note: jugaad-data provides DAILY data only.
        For intraday, we need to aggregate from daily or use alternative source.
        """
        try:
            # For now, daily data only
            if request.timeframe not in [Timeframe.D1, Timeframe.W1]:
                raise NotImplementedError(
                    f"jugaad-data only supports daily data. "
                    f"For {request.timeframe.value}, use CSV import."
                )
            
            df = stock_df(
                symbol=self._normalize_symbol(request.symbol),
                from_date=request.from_date.date(),
                to_date=request.to_date.date(),
                series="EQ"
            )
            
            candles = self._dataframe_to_candles(df, request.symbol, request.timeframe)
            
            return CandleResponse(
                symbol=request.symbol,
                timeframe=request.timeframe,
                candles=candles,
                from_date=request.from_date,
                to_date=request.to_date,
                is_complete=True
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            raise DataFeedError(
                message=f"Failed to fetch data for {request.symbol}",
                code=DataFeedError.CONNECTION_FAILED,
                details={"original_error": str(e)}
            )
    
    async def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote from NSE"""
        try:
            data = self.nse_live.stock_quote(self._normalize_symbol(symbol))
            price_info = data.get('priceInfo', {})
            
            return Quote(
                symbol=symbol,
                last_price=Decimal(str(price_info.get('lastPrice', 0))),
                change=Decimal(str(price_info.get('change', 0))),
                change_percent=Decimal(str(price_info.get('pChange', 0))),
                open=Decimal(str(price_info.get('open', 0))),
                high=Decimal(str(price_info.get('intraDayHighLow', {}).get('max', 0))),
                low=Decimal(str(price_info.get('intraDayHighLow', {}).get('min', 0))),
                close=Decimal(str(price_info.get('previousClose', 0))),
                volume=0,  # Not available in this API
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch quote: {e}")
            raise DataFeedError(
                message=f"Failed to fetch quote for {symbol}",
                code=DataFeedError.CONNECTION_FAILED,
                details={"original_error": str(e)}
            )
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Convert display symbol to API symbol"""
        # "NIFTY 50" → "NIFTY 50" (indices have spaces)
        # "RELIANCE" → "RELIANCE"
        return symbol.strip().upper()
    
    def _dataframe_to_candles(
        self, df: pd.DataFrame, symbol: str, timeframe: Timeframe
    ) -> List[Candle]:
        """Convert pandas DataFrame to list of Candle objects"""
        candles = []
        
        for _, row in df.iterrows():
            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=pd.to_datetime(row['DATE']).to_pydatetime(),
                open=Decimal(str(row['OPEN'])),
                high=Decimal(str(row['HIGH'])),
                low=Decimal(str(row['LOW'])),
                close=Decimal(str(row['CLOSE'])),
                volume=int(row.get('VOLUME', 0)),
                is_closed=True
            )
            candles.append(candle)
        
        return sorted(candles, key=lambda c: c.timestamp)
```

### CSVDataSource (Fallback)

```python
import csv
from pathlib import Path

class CSVDataSource(DataSourceInterface):
    """
    CSV fallback for intraday data.
    
    Expected CSV format:
    timestamp,open,high,low,close,volume
    2025-01-31 09:15:00,22450.50,22465.75,22440.00,22455.25,1234567
    """
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
    
    async def get_historical(self, request: CandleRequest) -> CandleResponse:
        csv_path = self.data_dir / f"{request.symbol}_{request.timeframe.value}.csv"
        
        if not csv_path.exists():
            raise DataFeedError(
                message=f"No CSV data for {request.symbol}",
                code=DataFeedError.SYMBOL_NOT_FOUND,
                details={"expected_path": str(csv_path)}
            )
        
        candles = []
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = datetime.fromisoformat(row['timestamp'])
                
                if request.from_date <= ts <= request.to_date:
                    candle = Candle(
                        symbol=request.symbol,
                        timeframe=request.timeframe,
                        timestamp=ts,
                        open=Decimal(row['open']),
                        high=Decimal(row['high']),
                        low=Decimal(row['low']),
                        close=Decimal(row['close']),
                        volume=int(row.get('volume', 0)),
                        is_closed=True
                    )
                    candles.append(candle)
        
        return CandleResponse(
            symbol=request.symbol,
            timeframe=request.timeframe,
            candles=candles,
            from_date=request.from_date,
            to_date=request.to_date,
            is_complete=True
        )
```

---

## 📤 Events Published

```python
# Published to event bus when new candle received
@dataclass
class CandleEvent:
    event_type: Literal["data.candle.new", "data.candle.closed"]
    symbol: str
    timeframe: str
    candle: Candle
    timestamp: datetime = field(default_factory=datetime.now)
    
# Published when symbol changes
@dataclass
class SymbolChangeEvent:
    event_type: str = "data.symbol.changed"
    old_symbol: Optional[str] = None
    new_symbol: str
    timestamp: datetime = field(default_factory=datetime.now)
```

---

## ⚠️ Error Handling

```python
class DataFeedError(Exception):
    """Base error for data feed service"""
    
    # Error codes
    SYMBOL_NOT_FOUND = "DATA_001"
    CONNECTION_FAILED = "DATA_002"
    RATE_LIMITED = "DATA_003"
    INVALID_DATE_RANGE = "DATA_004"
    INVALID_TIMEFRAME = "DATA_005"
    CACHE_ERROR = "DATA_006"
    
    def __init__(self, message: str, code: str, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

# Retry logic for transient failures
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(DataFeedError)
)
async def fetch_with_retry(self, request: CandleRequest) -> CandleResponse:
    return await self.data_source.get_historical(request)
```

---

## 🧪 Testing

```python
# tests/test_data_feed.py

import pytest
from decimal import Decimal
from datetime import datetime

class TestCandle:
    def test_candle_validation(self):
        # Valid candle
        candle = Candle(
            symbol="NIFTY",
            timeframe=Timeframe.M15,
            timestamp=datetime.now(),
            open=Decimal("100"),
            high=Decimal("105"),
            low=Decimal("95"),
            close=Decimal("102")
        )
        assert candle.is_bullish
        assert candle.range == Decimal("10")
        assert candle.body == Decimal("2")
    
    def test_invalid_candle_raises(self):
        # High < Low should fail
        with pytest.raises(AssertionError):
            Candle(
                symbol="NIFTY",
                timeframe=Timeframe.M15,
                timestamp=datetime.now(),
                open=Decimal("100"),
                high=Decimal("95"),  # Invalid: high < low
                low=Decimal("105"),
                close=Decimal("102")
            )

class TestJugaadDataSource:
    @pytest.mark.asyncio
    async def test_get_quote(self, mock_nse_live):
        source = JugaadDataSource()
        quote = await source.get_quote("RELIANCE")
        
        assert quote.symbol == "RELIANCE"
        assert quote.last_price > 0
    
    @pytest.mark.asyncio
    async def test_invalid_symbol(self, mock_nse_live):
        source = JugaadDataSource()
        
        with pytest.raises(DataFeedError) as exc:
            await source.get_quote("INVALID_SYMBOL")
        
        assert exc.value.code == DataFeedError.SYMBOL_NOT_FOUND
```

---

## 📋 Configuration

```yaml
# config/data-feed.yaml

service:
  name: data-feed
  port: 8001
  
data_sources:
  primary: jugaad
  fallback: csv
  
cache:
  type: redis
  host: localhost
  port: 6379
  ttl:
    historical: 86400  # 1 day
    quote: 5           # 5 seconds
    symbols: 3600      # 1 hour
    
rate_limit:
  max_requests_per_minute: 60
  cooldown_seconds: 10
  
polling:
  enabled: true
  interval_ms: 1000  # 1 second
  
logging:
  level: INFO
  format: json
```

---

## ✅ Acceptance Criteria

- [ ] Can fetch list of available symbols
- [ ] Can fetch historical daily data via jugaad-data
- [ ] Can fetch intraday data via CSV import
- [ ] Can get real-time quote for any symbol
- [ ] Caches data to reduce API calls
- [ ] Handles rate limiting gracefully
- [ ] Publishes events on new candles
- [ ] All OHLC relationships validated
- [ ] Uses Decimal for all prices (no float)
- [ ] Comprehensive error handling
- [ ] Unit tests with >90% coverage
