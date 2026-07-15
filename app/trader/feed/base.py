"""DataFeed contract: the single seam between market data and the engine.

A feed emits ``FeedEvent`` objects, each wrapping exactly one fully CLOSED
M1 candle. Consumers never see a partial bar. ``historical`` provides
backfill for warm-up (e.g. previous-day levels) before the event stream.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
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
        self, symbol: str, tf: Timeframe, start: date, end: date
    ) -> list[Candle]:
        """Closed candles of ``tf`` for symbol within [start, end] inclusive.

        ``start``/``end`` are calendar days (``datetime.date``), not
        timestamps. Implementations build tz-aware IST day bounds from them
        internally. A ``datetime`` is tolerated too: it is normalized via
        ``.date()`` before use (its time-of-day is discarded), so feeds stay
        interchangeable regardless of which concrete type a caller passes.
        """
