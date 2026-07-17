"""StockContext: everything a detector may look at for one symbol at one
point in time. Built fresh per evaluation tick; ``levels`` and
``evidence_history`` are the live shared objects (mutable), ``candles`` is a
no-lookahead CandleView from CandleStore.view()."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal

from trader.models.candle import Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level
from trader.models.market import NSE, MarketSpec
from trader.store.candles import CandleView

_M5 = timedelta(minutes=5)


def live_evidence(history: list[Evidence], now: datetime | None = None,
                  session_date: date | None = None) -> list[Evidence]:
    """Evidence still in play: unexpired ttl at ``now`` (ttl_candles are M5)
    and/or stamped in the ``session_date`` session. None skips that filter."""
    return [e for e in history
            if (now is None or e.ts + e.ttl_candles * _M5 >= now)
            and (session_date is None or e.ts.date() == session_date)]


@dataclass(frozen=True)
class IndexView:
    """Index-symbol read (structure+wyckoff run upstream by the orchestrator
    on the index; wired in Phase 4)."""

    trend: Direction
    phase: str
    strength: float


@dataclass
class DayState:
    """Per-session state. Minimal this phase; grows later (bias, template
    classification, etc.)."""

    session_date: date
    template: str = "UNCLASSIFIED"
    po3: dict = field(default_factory=dict)  # scale ("day"/"leg") -> PO3FSM


@dataclass
class StockContext:
    symbol: str
    now: datetime
    candles: CandleView                  # from CandleStore.view()
    levels: list[Level]                  # live level objects (mutable, shared)
    evidence_history: list[Evidence]
    day: DayState
    options: object | None = None        # options chain snapshot; None if absent
    index: IndexView | None = None       # index-context read; None if absent
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
