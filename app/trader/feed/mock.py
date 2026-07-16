"""ScenarioFeed: scripted market days with KNOWN ground truth.

These scenarios are the detector test fixtures: each helper constructor
returns a full 375-minute NSE session (09:15..15:29 IST, exactly what
CandleStore.add accepts) whose interesting features are placed by
construction, not by luck, and recorded in ``scenario.truth``.

Determinism is mandatory: generation uses ONLY a ``random.Random`` instance
seeded with ``f"{name}:{symbol}:{date}"`` -- never the global ``random``
module, never wall-clock entropy. Same inputs => byte-identical candles.

Two generation modes:

- ``segments`` random walk: piecewise ``(minutes, drift_per_min, vol_range,
  volume)`` segments. Noise is TICK-SCALED: per-candle amplitude =
  ``max(price * vol_pct, 3 * TICK)``, so wicks always span whole ticks and
  strict-inequality swing confirmation stays possible at any price.
- ``script``: a callable building all 375 candles explicitly, used where a
  shape must hold BY CONSTRUCTION (judas_reversal). Scripted candles are
  planned in integer ticks with per-minute clamp bands, so every level/swing
  interaction below is guaranteed, not probabilistic.

OHLC validity is guaranteed by construction: ``high >= max(open, close)``,
``low <= min(open, close)``, all prices tick-quantized.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime, time, timedelta
from typing import Callable, Iterator
from zoneinfo import ZoneInfo

from trader.feed.base import DataFeed, FeedEvent
from trader.models.candle import TICK, Candle, Timeframe, tick

IST = ZoneInfo("Asia/Kolkata")
SESSION_MINUTES = 375  # 09:15 .. 15:29 inclusive
_NOISE_FLOOR = float(3 * TICK)  # random-walk noise never collapses sub-tick

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
    script: Callable[["Scenario"], list[Candle]] | None = None

    def __post_init__(self) -> None:
        total = sum(m for m, *_ in self.segments)
        if self.script is None and total != SESSION_MINUTES:
            raise ValueError(f"segments sum to {total} minutes, need {SESSION_MINUTES}")

    def rng(self) -> random.Random:
        return random.Random(f"{self.name}:{self.symbol}:{self.date}")

    def session_open(self) -> datetime:
        return datetime.combine(self.date, time(9, 15), tzinfo=IST)

    def candles(self) -> list[Candle]:
        """Generate the day's 375 M1 candles. Pure + deterministic: repeated
        calls (or fresh identical Scenarios) return identical candles."""
        if self.script is not None:
            return self.script(self)
        rng = self.rng()
        session_open = self.session_open()
        out: list[Candle] = []
        price = float(self.open_price)
        minute = 0
        for minutes, drift, (noise_lo, noise_hi), volume in self.segments:
            for _ in range(minutes):
                o = price
                amp = lambda v: max(o * v, _NOISE_FLOOR)  # tick-scaled noise
                c = o * (1 + drift) + rng.uniform(-amp(noise_lo), amp(noise_lo))
                h = max(o, c) + rng.uniform(0, amp(noise_hi))
                l = min(o, c) - rng.uniform(0, amp(noise_hi))
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


# --------------------------------------------------------------- judas script
#
# Minutes 0-79 are planned per M5 bucket as (5 M1 closes, low clamp, high
# clamp), all in ticks from base = tick(open_price). OR low = -2T, so:
# b0-b2  opening range: high +9T (forced m2), low -2T (forced m12), range 11T
# b3     dip to -3T (m17): prints M5 SWING_L "L1" WITHOUT breaching the ORL
#        far edge (-3T == zone lo, not beyond) -- closes recover above zone
# b4     lower-high bounce to +8T (m22): M5 SWING_H "H1" (3+ ticks above H2,
#        so their +/-1-tick zones don't overlap -- swings dedups overlaps)
# b5-b6  drift down, closes hold above the ORL zone (no 2-candle break)
# b7     SWEEP bucket: m37 spikes to -6T (= OR low - 4T, unique day low, 4x
#        volume), M5 closes +1T -> wick-through + close-back => ORL (and L1)
#        transition SWEPT on this single candle, guaranteed
# b8     recovery pop to +5T (m44): lower SWING_H "H2" (falling highs)
# b9-b11 pullback bottoming -1T (m57): its SWING_L confirms only at 10:30,
#        AFTER the CHoCH below, so the SHORT trend (H1>H2, L1>L2) holds
# b12    rally closes +7T > mid(H2) => structure emits CHoCH LONG at 10:20,
#        5 M5 candles after the 09:55 sweep evidence
# b13-15 breaks ORH by consecutive closes (DEAD, never swept)
# Chop (m80-229) is clamp-bounded to [11T, 15T] with closes in [12T, 14T]:
# no wick can pass any in-chop level zone with a close back on the origin
# side, so the chop can never fabricate sweep evidence. The afternoon rally
# (m230-374) stair-steps +1T/min with 10-min pullbacks: rising M5 swings =>
# bullish structure/BOS into a close near the day high.

_JUDAS_MORNING: list[tuple[list[int], int, int]] = [
    ([2, 5, 8, 6, 4], -1, 8), ([3, 2, 1, 1, 0], -1, 4), ([0, -1, -1, 0, -1], -1, 1),
    ([-1, 0, -1, 1, 2], -1, 3), ([3, 4, 5, 5, 4], 0, 5), ([3, 3, 2, 1, 1], 0, 4),
    ([1, 0, 0, 1, 0], -1, 2), ([-1, -1, -1, 0, 1], -1, 2), ([2, 3, 4, 4, 4], 0, 4),
    ([3, 3, 2, 2, 2], 1, 4), ([2, 1, 1, 1, 1], 0, 3), ([1, 1, 0, 1, 1], 0, 2),
    ([3, 5, 6, 7, 7], 1, 8), ([8, 9, 9, 10, 10], 6, 11),
    ([11, 11, 12, 12, 12], 9, 13), ([12, 13, 13, 13, 13], 11, 14),
]
_JUDAS_FORCED = {2: ("high", 9), 12: ("low", -2), 17: ("low", -3), 22: ("high", 8),
                 37: ("low", -6), 44: ("high", 5), 57: ("low", -1)}
_SWEEP_MINUTE = 37
_SWEEP_VOLUME_MULT = 4


def _judas_candles(sc: Scenario) -> list[Candle]:
    rng = sc.rng()
    base = tick(sc.open_price)
    # (close, low clamp, high clamp, base volume) per minute, in ticks
    plan: list[tuple[int, int, int, int]] = []
    for i, (closes, lo, hi) in enumerate(_JUDAS_MORNING):
        plan += [(c, lo, hi, 1000 if i < 8 else 1200) for c in closes]
    plan += [(rng.randint(12, 14), 11, 15, 800) for _ in range(150)]  # midday chop
    c = 13
    for step, n in ((1, 35), (-1, 10)) * 3 + ((1, 10),):  # afternoon stair-step
        for _ in range(n):
            c += step
            plan.append((c, c - 3, c + 3, 1100))
    session_open, out, prev = sc.session_open(), [], 0
    for minute, (close, lo, hi, vol) in enumerate(plan):
        o = prev
        h = min(hi, max(o, close) + rng.randint(0, 3))
        l = max(lo, min(o, close) - rng.randint(0, 3))
        volume = rng.randint(int(vol * 0.8), int(vol * 1.2))
        side, forced = _JUDAS_FORCED.get(minute, (None, 0))
        h, l = (forced if side == "high" else h), (forced if side == "low" else l)
        if minute == _SWEEP_MINUTE:
            volume *= _SWEEP_VOLUME_MULT
        out.append(Candle(
            symbol=sc.symbol, tf=Timeframe.M1,
            ts=session_open + timedelta(minutes=minute),
            open=base + o * TICK,
            high=base + max(h, o, close) * TICK,
            low=base + min(l, o, close) * TICK,
            close=base + close * TICK,
            volume=volume,
        ))
        prev = close
    return out


def judas_reversal(symbol: str, date: date_type, open_price: float) -> Scenario:
    """Judas swing day: opening range, drift down that TESTS but never breaks
    the OR low, a single-candle liquidity sweep of it (wick through, close
    back => LevelEngine SWEPT), then bearish->bullish CHoCH and a LONG trend
    into the close. See the script commentary above for the exact geometry.
    """
    sc = Scenario("judas_reversal", symbol, date, [], open_price,
                  script=_judas_candles)
    candles = sc.candles()  # deterministic, so safe to read ground truth back
    or_low = min(c.low for c in candles[:15])
    sc.truth = {
        "sweep_low_minute": _SWEEP_MINUTE,
        "reversal_from": candles[_SWEEP_MINUTE].low,   # = or_low - 4 ticks
        "afternoon_direction": "LONG",
        "swept_zone": (or_low - TICK, or_low + TICK),  # the ORL zone swept
    }
    return sc


def trend_day(symbol: str, date: date_type, open_price: float) -> Scenario:
    """One-way LONG trend day: 45-min +0.05%/min runs with 10-min
    -0.06%/min pullbacks (deep enough to confirm M5 swings, never breaking a
    prior swing low); closes near the high. No level is ever wick-through-
    close-back swept, so structure sees BOS but sweep stays quiet."""
    run: Segment = (45, +0.0005, (0.0002, 0.0005), 1000)
    pullback: Segment = (10, -0.0006, (0.0001, 0.0004), 700)
    segments = [run, pullback] * 6 + [run]  # 6 x 55 + 45 = 375 min
    return Scenario(
        "trend_day", symbol, date, segments, open_price,
        truth={"direction": "LONG"},
    )
