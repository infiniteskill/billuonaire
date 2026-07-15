"""ScenarioFeed: scripted market days with KNOWN ground truth.

These scenarios are the detector test fixtures for later phases: each helper
constructor returns a full 375-minute NSE session (09:15..15:29 IST, exactly
what CandleStore.add accepts) whose interesting features are placed by
construction, not by luck, and recorded in ``scenario.truth``.

Determinism is mandatory: generation uses ONLY a ``random.Random`` instance
seeded with ``f"{name}:{symbol}:{date}"`` — never the global ``random``
module, never wall-clock entropy. Same inputs => byte-identical candles.

A scenario is a piecewise random walk over ``segments``, where each segment
is a tuple ``(minutes, drift_per_min, vol_range, volume)``:

- ``minutes``        length of the segment (all segments must sum to 375)
- ``drift_per_min``  fractional close-to-close drift, e.g. -0.0008 = -0.08%/min
- ``vol_range``      (lo, hi) fractional noise band; lo bounds the close
                     jitter, wicks are drawn uniformly from [lo, hi]
- ``volume``         base per-minute volume (jittered +/-20%)

OHLC validity is guaranteed by construction: after tick-quantization,
``high = max(open, close, raw_high)`` and ``low = min(open, close, raw_low)``.

Sweep forcing: when ``scenario.sweep_minute`` is set, that candle's low is
rebuilt as (day minimum - 5 ticks) and its volume tripled AFTER the walk, so
it is the day's unique absolute low no matter what the noise did.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from datetime import date as date_type
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Iterator
from zoneinfo import ZoneInfo

from trader.feed.base import DataFeed, FeedEvent
from trader.models.candle import TICK, Candle, Timeframe, tick

IST = ZoneInfo("Asia/Kolkata")
SESSION_MINUTES = 375  # 09:15 .. 15:29 inclusive
SWEEP_MARGIN = 5 * TICK
SWEEP_VOLUME_MULT = 3

# (minutes, drift_per_min, (noise_lo, noise_hi), base_volume)
Segment = tuple[int, float, tuple[float, float], int]


@dataclass
class Scenario:
    """A scripted 375-minute session with ground-truth markers in ``truth``."""

    name: str
    symbol: str
    date: date_type
    segments: list[Segment]
    open_price: float
    truth: dict = field(default_factory=dict)
    sweep_minute: int | None = None

    def __post_init__(self) -> None:
        total = sum(m for m, *_ in self.segments)
        if total != SESSION_MINUTES:
            raise ValueError(f"segments sum to {total} minutes, need {SESSION_MINUTES}")
        if self.sweep_minute is not None and not 0 <= self.sweep_minute < SESSION_MINUTES:
            raise ValueError(f"sweep_minute {self.sweep_minute} outside session")

    def candles(self) -> list[Candle]:
        """Generate the day's 375 M1 candles. Pure + deterministic: repeated
        calls (or fresh identical Scenarios) return identical candles."""
        rng = random.Random(f"{self.name}:{self.symbol}:{self.date}")
        session_open = datetime.combine(self.date, time(9, 15), tzinfo=IST)
        out: list[Candle] = []
        price = float(self.open_price)
        minute = 0
        for minutes, drift, (noise_lo, noise_hi), volume in self.segments:
            for _ in range(minutes):
                o = price
                c = o * (1 + drift + rng.uniform(-noise_lo, noise_lo))
                h = max(o, c) * (1 + rng.uniform(noise_lo, noise_hi))
                l = min(o, c) * (1 - rng.uniform(noise_lo, noise_hi))
                qo, qc = tick(o), tick(c)
                out.append(
                    Candle(
                        symbol=self.symbol,
                        tf=Timeframe.M1,
                        ts=session_open + timedelta(minutes=minute),
                        open=qo,
                        high=max(qo, qc, tick(h)),
                        low=min(qo, qc, tick(l)),
                        close=qc,
                        volume=rng.randint(int(volume * 0.8), int(volume * 1.2)),
                    )
                )
                price = c
                minute += 1
        if self.sweep_minute is not None:
            i = self.sweep_minute
            forced_low = min(c.low for c in out) - SWEEP_MARGIN
            out[i] = replace(
                out[i], low=forced_low, volume=out[i].volume * SWEEP_VOLUME_MULT
            )
        return out


class ScenarioFeed(DataFeed):
    """Replays scenarios as a FeedEvent stream of closed M1 candles."""

    def __init__(self, scenarios: list[Scenario]):
        self._scenarios = list(scenarios)
        self._subscribed: set[str] | None = None  # None => all symbols

    def subscribe(self, symbols: list[str]) -> None:
        self._subscribed = set(symbols)

    def _active(self) -> list[Scenario]:
        if self._subscribed is None:
            return self._scenarios
        return [s for s in self._scenarios if s.symbol in self._subscribed]

    def events(self) -> Iterator[FeedEvent]:
        """All 375 M1 candles of each subscribed scenario, in time order
        (ties across symbols broken by symbol)."""
        candles = [c for sc in self._active() for c in sc.candles()]
        candles.sort(key=lambda c: (c.ts, c.symbol))
        for candle in candles:
            yield FeedEvent(candle)

    def historical(
        self,
        symbol: str,
        tf: Timeframe,
        start: date_type | datetime,
        end: date_type | datetime,
    ) -> list[Candle]:
        """M1 candles for symbol within [start, end] inclusive, by calendar
        day. ``start``/``end`` are ``datetime.date``; a ``datetime`` is
        accepted too and normalized via ``.date()`` (time-of-day ignored).
        Internally this builds tz-aware IST day bounds: 00:00:00 of
        ``start`` to 23:59:59.999999 of ``end``. Other timeframes are not
        synthesized here (aggregate via CandleStore instead)."""
        if tf is not Timeframe.M1:
            raise NotImplementedError("ScenarioFeed serves M1 history only")
        start_date = start.date() if isinstance(start, datetime) else start
        end_date = end.date() if isinstance(end, datetime) else end
        start_dt = datetime.combine(start_date, time.min, tzinfo=IST)
        end_dt = datetime.combine(end_date, time.max, tzinfo=IST)
        out = [
            c
            for sc in self._scenarios
            if sc.symbol == symbol
            for c in sc.candles()
            if start_dt <= c.ts <= end_dt
        ]
        out.sort(key=lambda c: c.ts)
        return out


def judas_reversal(symbol: str, date: date_type, open_price: float) -> Scenario:
    """Judas swing day: morning drive down into a liquidity sweep, then a
    reversal that trends LONG all afternoon.

    Shape (375 min): 23 min drift -0.08%/min (sweep spike forced at minute
    22, day's unique absolute low, 3x volume) -> 40 min recovery +0.06%/min
    -> 180 min flat chop -> 132 min rally +0.04%/min into the close.
    """
    segments: list[Segment] = [
        (23, -0.0008, (0.0002, 0.0006), 1000),   # morning drive down (incl. min 22)
        (40, +0.0006, (0.0002, 0.0006), 1200),   # sharp recovery off the sweep
        (180, 0.0, (0.0001, 0.0004), 800),       # midday chop
        (132, +0.0004, (0.0002, 0.0006), 1100),  # afternoon rally to close
    ]
    sc = Scenario("judas_reversal", symbol, date, segments, open_price,
                  sweep_minute=22)
    sweep_low: Decimal = sc.candles()[22].low  # deterministic, so safe to read
    sc.truth = {
        "sweep_low_minute": 22,
        "reversal_from": sweep_low,
        "afternoon_direction": "LONG",
    }
    return sc


def trend_day(symbol: str, date: date_type, open_price: float) -> Scenario:
    """One-way LONG trend day: +0.05%/min grind with a shallow 10-minute
    -0.02%/min pullback every 45 minutes; closes near the high."""
    segments: list[Segment] = []
    for _ in range(8):  # 8 x (35 up + 10 pullback) = 360 min
        segments.append((35, +0.0005, (0.0002, 0.0005), 1000))
        segments.append((10, -0.0002, (0.0001, 0.0004), 700))
    segments.append((15, +0.0005, (0.0002, 0.0005), 1000))  # final leg -> 375
    return Scenario(
        "trend_day", symbol, date, segments, open_price,
        truth={"direction": "LONG"},
    )
