"""StockContext: everything a detector may look at for one symbol at one
point in time. Built fresh per evaluation tick; ``levels`` and
``evidence_history`` are the live shared objects (mutable), ``candles`` is a
no-lookahead CandleView from CandleStore.view()."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from trader.models.candle import Timeframe
from trader.models.evidence import Evidence
from trader.models.level import Level
from trader.models.market import NSE, MarketSpec
from trader.store.candles import CandleView


@dataclass
class DayState:
    """Per-session state. Minimal this phase; grows later (bias, template
    classification, etc.)."""

    session_date: date
    template: str = "UNCLASSIFIED"


@dataclass
class StockContext:
    symbol: str
    now: datetime
    candles: CandleView                  # from CandleStore.view()
    levels: list[Level]                  # live level objects (mutable, shared)
    evidence_history: list[Evidence]
    day: DayState
    options: object | None = None        # options chain snapshot; None if absent
    spec: MarketSpec = NSE               # market calendar + tick grid

    def atr(self, tf: Timeframe, period: int = 14) -> Decimal | None:
        """Average True Range: SMA of the last ``period`` true ranges over
        fully closed ``tf`` candles, where
        ``TR = max(h - l, |h - prev_close|, |l - prev_close|)``.

        Needs ``period + 1`` closed candles (the oldest only supplies
        prev_close); returns None when fewer are available.

        Deliberately NOT tick-quantized: ATR is a measure used for stop
        buffers and normalization, not a quotable price, so it keeps full
        Decimal precision.
        """
        candles = self.candles.last(period + 1, tf)
        if len(candles) < period + 1:
            return None
        trs = [
            max(cur.high - cur.low,
                abs(cur.high - prev.close),
                abs(cur.low - prev.close))
            for prev, cur in zip(candles, candles[1:])
        ]
        return sum(trs) / Decimal(period)
