"""FileFeed: read OHLCV from CSV files, one file per symbol."""

from __future__ import annotations

import heapq
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from typing import Iterator

import pandas as pd

from trader.feed.base import DataFeed, FeedEvent
from trader.models.candle import Candle, Timeframe, tick


class FileFeed(DataFeed):
    """Reads CSV market data from files, one per symbol."""

    def __init__(self, root: Path):
        """Initialize FileFeed with a root directory containing symbol CSVs.

        Args:
            root: Directory containing <SYMBOL>.csv files with header:
                  ts,open,high,low,close,volume
        """
        self.root = Path(root)
        self._subscribed: set[str] | None = None

    def subscribe(self, symbols: list[str]) -> None:
        """Declare which symbols events() should stream."""
        self._subscribed = set(symbols)

    def _load_candles(self, symbol: str) -> list[Candle]:
        """Load all candles from CSV file for a symbol."""
        csv_path = self.root / f"{symbol}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(str(csv_path))

        df = pd.read_csv(csv_path)
        candles = []

        for _, row in df.iterrows():
            ts = pd.to_datetime(row["ts"], utc=False)  # Keep timezone info
            candles.append(
                Candle(
                    symbol=symbol,
                    tf=Timeframe.M1,
                    ts=ts,
                    open=tick(row["open"]),
                    high=tick(row["high"]),
                    low=tick(row["low"]),
                    close=tick(row["close"]),
                    volume=int(row["volume"]),
                )
            )

        return candles

    def events(self) -> Iterator[FeedEvent]:
        """Yield FeedEvents (closed M1 candles) in time order.

        For multiple symbols, events are interleaved chronologically,
        with ties broken by symbol name (stable ordering).
        """
        if self._subscribed is None:
            symbols = []
        else:
            symbols = sorted(self._subscribed)

        # Load all candles for subscribed symbols
        symbol_candles = {}
        for symbol in symbols:
            symbol_candles[symbol] = self._load_candles(symbol)

        # Create iterators keyed by (ts, symbol) for stable ordering
        iterators = [
            (
                (c.ts, c.symbol),
                FeedEvent(c),
            )
            for symbol in symbols
            for c in symbol_candles[symbol]
        ]

        # Sort by (ts, symbol) key
        iterators.sort(key=lambda x: x[0])

        # Yield in order
        for _, event in iterators:
            yield event

    def historical(
        self, symbol: str, tf: Timeframe, start: date_type, end: date_type
    ) -> list[Candle]:
        """Return closed candles of timeframe for symbol with start <= date <= end.

        Args:
            symbol: Symbol to query
            tf: Timeframe (M1 only)
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            List of Candle objects

        Raises:
            NotImplementedError: If tf is not M1
            FileNotFoundError: If CSV file for symbol doesn't exist
        """
        if tf is not Timeframe.M1:
            raise NotImplementedError("FileFeed serves M1 history only")

        candles = self._load_candles(symbol)

        # Filter by date range (inclusive)
        start_dt = datetime.combine(start, datetime.min.time()).replace(
            tzinfo=candles[0].ts.tzinfo if candles else None
        )
        end_dt = datetime.combine(end, datetime.max.time()).replace(
            tzinfo=candles[0].ts.tzinfo if candles else None
        )

        result = [
            c for c in candles
            if start_dt <= c.ts <= end_dt
        ]

        return result
