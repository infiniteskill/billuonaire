"""FileFeed: read OHLCV from CSV files, one file per symbol."""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, time
from pathlib import Path
from typing import Iterator

import pandas as pd

from trader.feed.base import DataFeed, FeedEvent
from trader.models.candle import Candle, Timeframe
from trader.models.market import NSE, MarketSpec


class FileFeed(DataFeed):
    """Reads CSV market data from ``root/<SYMBOL>.csv`` (header ts,open,high,
    low,close,volume); prices quantized to spec's tick grid (default NSE)."""

    def __init__(self, root: Path, spec: MarketSpec = NSE):
        self.root = Path(root)
        self.spec = spec
        self._subscribed: set[str] | None = None

    def subscribe(self, symbols: list[str]) -> None:
        """Declare which symbols events() should stream."""
        self._subscribed = set(symbols)

    def _load_candles(self, symbol: str) -> list[Candle]:
        """Load all candles from the symbol's CSV file."""
        csv_path = self.root / f"{symbol}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(str(csv_path))
        q = self.spec.quantize
        return [
            Candle(
                symbol=symbol,
                tf=Timeframe.M1,
                ts=pd.to_datetime(row["ts"], utc=False),  # keep timezone info
                open=q(row["open"]),
                high=q(row["high"]),
                low=q(row["low"]),
                close=q(row["close"]),
                volume=int(row["volume"]),
            )
            for _, row in pd.read_csv(csv_path).iterrows()
        ]

    def events(self) -> Iterator[FeedEvent]:
        """Yield FeedEvents (closed M1 candles) in time order; interleaved
        chronologically across symbols, ties broken by symbol name."""
        symbols = sorted(self._subscribed) if self._subscribed else []
        candles = [c for s in symbols for c in self._load_candles(s)]
        candles.sort(key=lambda c: (c.ts, c.symbol))
        for c in candles:
            yield FeedEvent(c)

    def historical(
        self,
        symbol: str,
        tf: Timeframe,
        start: date_type | datetime,
        end: date_type | datetime,
    ) -> list[Candle]:
        """Closed M1 candles for symbol within [start, end] inclusive, by
        calendar day (a ``datetime`` bound is normalized via ``.date()``).
        Day bounds are tz-aware in the market's tz: 00:00:00 of ``start`` to
        23:59:59.999999 of ``end``. Raises NotImplementedError for tf != M1;
        FileNotFoundError if the symbol's CSV is absent."""
        if tf is not Timeframe.M1:
            raise NotImplementedError("FileFeed serves M1 history only")
        start_date = start.date() if isinstance(start, datetime) else start
        end_date = end.date() if isinstance(end, datetime) else end
        start_dt = datetime.combine(start_date, time.min, tzinfo=self.spec.tzinfo)
        end_dt = datetime.combine(end_date, time.max, tzinfo=self.spec.tzinfo)
        return [c for c in self._load_candles(symbol) if start_dt <= c.ts <= end_dt]
