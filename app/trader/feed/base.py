"""DataFeed contract: the single seam between market data and the engine.

A feed emits ``FeedEvent`` objects, each wrapping exactly one fully CLOSED
M1 candle. Consumers never see a partial bar. ``historical`` provides
backfill for warm-up (e.g. previous-day levels) before the event stream.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

from trader.models.candle import Candle, Timeframe


@dataclass(frozen=True)
class FeedEvent:
    """One closed M1 candle arriving from a feed."""

    candle: Candle


class DataFeed(ABC):
    """Abstract market-data feed."""

    @abstractmethod
    def subscribe(self, symbols: list[str]) -> None:
        """Declare which symbols ``events()`` should stream."""

    @abstractmethod
    def events(self) -> Iterator[FeedEvent]:
        """Yield FeedEvents (closed M1 candles) in time order."""

    @abstractmethod
    def historical(
        self, symbol: str, tf: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        """Closed candles of ``tf`` for symbol with start <= ts <= end."""
