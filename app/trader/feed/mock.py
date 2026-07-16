"""ScenarioFeed: scripted market days with KNOWN ground truth.

These scenarios are the detector test fixtures: each helper constructor
returns a full session for its MarketSpec (default NSE: 375 minutes from
09:15 IST, exactly what CandleStore.add accepts) whose interesting features
are placed by construction, not by luck, and recorded in ``scenario.truth``.

Determinism is mandatory: generation uses ONLY a ``random.Random`` instance
seeded with ``f"{name}:{symbol}:{date}"`` -- never the global ``random``
module, never wall-clock entropy. Same inputs => byte-identical candles.

Two generation modes:

- ``segments`` random walk: piecewise ``(minutes, drift_per_min, vol_range,
  volume)`` segments. Noise is TICK-SCALED: per-candle amplitude =
  ``max(price * vol_pct, 3 * spec.tick_size)``, so wicks always span whole
  ticks and strict-inequality swing confirmation stays possible at any price.
- ``script``: a callable building the session's candles explicitly, used where a
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

from trader.feed.base import DataFeed, FeedEvent
from trader.models.candle import Candle, Timeframe
from trader.models.market import NSE, MarketSpec

# (minutes, drift_per_min, (noise_lo, noise_hi), base_volume)
Segment = tuple[int, float, tuple[float, float], int]


@dataclass
class Scenario:
    """A scripted full-session day with ground-truth markers in ``truth``."""

    name: str
    symbol: str
    date: date_type
    segments: list[Segment]
    open_price: float
    truth: dict = field(default_factory=dict)
    script: Callable[["Scenario"], list[Candle]] | None = None
    spec: MarketSpec = NSE

    def __post_init__(self) -> None:
        total = sum(m for m, *_ in self.segments)
        if self.script is None and total != self.spec.session_minutes:
            raise ValueError(f"segments sum to {total} minutes, need {self.spec.session_minutes}")

    def rng(self) -> random.Random:
        return random.Random(f"{self.name}:{self.symbol}:{self.date}")

    def session_open(self) -> datetime:
        return datetime.combine(self.date, self.spec.open_t, tzinfo=self.spec.tzinfo)

    def candles(self) -> list[Candle]:
        """Generate the day's session_minutes M1 candles. Pure + deterministic:
        repeated calls (or fresh identical Scenarios) return identical candles."""
        if self.script is not None:
            return self.script(self)
        rng = self.rng()
        session_open, tick = self.session_open(), self.spec.quantize
        noise_floor = float(3 * self.spec.tick_size)  # never collapses sub-tick
        out: list[Candle] = []
        price = float(self.open_price)
        minute = 0
        for minutes, drift, (noise_lo, noise_hi), volume in self.segments:
            for _ in range(minutes):
                o = price
                amp = lambda v: max(o * v, noise_floor)  # tick-scaled noise
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
        """All M1 candles of each subscribed scenario, in time order
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
        Internally this builds tz-aware day bounds in each scenario's market
        tz: 00:00:00 of ``start`` to 23:59:59.999999 of ``end``. Other
        timeframes are not synthesized here (aggregate via CandleStore)."""
        if tf is not Timeframe.M1:
            raise NotImplementedError("ScenarioFeed serves M1 history only")
        start_date = start.date() if isinstance(start, datetime) else start
        end_date = end.date() if isinstance(end, datetime) else end
        out = [
            c
            for sc in self._scenarios
            if sc.symbol == symbol
            for c in sc.candles()
            if datetime.combine(start_date, time.min, tzinfo=sc.spec.tzinfo)
            <= c.ts <= datetime.combine(end_date, time.max, tzinfo=sc.spec.tzinfo)
        ]
        out.sort(key=lambda c: c.ts)
        return out


# ------------------------------------------------------- scripted-day builder
#
# Shared by every ``script`` scenario: a plan of per-minute rows
# ``(close, low clamp, high clamp, base volume)`` in TICKS from
# ``base = tick(open_price)``; ``forced`` pins a minute's wick exactly
# (("high"|"low"), tick value) -- day extremes are placed this way, by
# construction; minutes in ``boosted`` get ``_SWEEP_VOLUME_MULT``x volume.
# ``rng`` is passed in (not re-seeded) so a caller may spend entropy on
# plan-building first; rng consumption order per minute is fixed:
# high wick, low wick, volume.


def _plan_candles(sc: Scenario, rng: random.Random,
                  plan: list[tuple[int, int, int, int]],
                  forced: dict[int, tuple[str, int]],
                  boosted: frozenset[int] = frozenset()) -> list[Candle]:
    T, base = sc.spec.tick_size, sc.spec.quantize(sc.open_price)
    session_open, out, prev = sc.session_open(), [], 0
    for minute, (close, lo, hi, vol) in enumerate(plan):
        o = prev
        h = min(hi, max(o, close) + rng.randint(0, 3))
        l = max(lo, min(o, close) - rng.randint(0, 3))
        volume = rng.randint(int(vol * 0.8), int(vol * 1.2))
        side, pin = forced.get(minute, (None, 0))
        h, l = (pin if side == "high" else h), (pin if side == "low" else l)
        if minute in boosted:
            volume *= _SWEEP_VOLUME_MULT
        out.append(Candle(
            symbol=sc.symbol, tf=Timeframe.M1,
            ts=session_open + timedelta(minutes=minute),
            open=base + o * T,
            high=base + max(h, o, close) * T,
            low=base + min(l, o, close) * T,
            close=base + close * T,
            volume=volume,
        ))
        prev = close
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
    return _plan_candles(sc, rng, plan, _JUDAS_FORCED,
                         boosted=frozenset({_SWEEP_MINUTE}))


def judas_reversal(symbol: str, date: date_type, open_price: float,
                   spec: MarketSpec = NSE) -> Scenario:
    """Judas swing day: opening range, drift down that TESTS but never breaks
    the OR low, a single-candle liquidity sweep of it (wick through, close
    back => LevelEngine SWEPT), then bearish->bullish CHoCH and a LONG trend
    into the close. See the script commentary above for the exact geometry.
    """
    sc = Scenario("judas_reversal", symbol, date, [], open_price,
                  script=_judas_candles, spec=spec)
    candles = sc.candles()  # deterministic, so safe to read ground truth back
    or_low = min(c.low for c in candles[:15])
    sc.truth = {
        "template": "TRAP_REVERSAL",
        "sweep_low_minute": _SWEEP_MINUTE,
        "reversal_from": candles[_SWEEP_MINUTE].low,   # = or_low - 4 ticks
        "afternoon_direction": "LONG",
        "swept_zone": (or_low - spec.tick_size, or_low + spec.tick_size),
    }
    return sc


# ---------------------------------------------------------- trend_day script
#
# Scripted LONG stair-step, all in ticks from base = tick(open_price), wick
# clamps close +/-1T so the FORCED spikes are the only decisive wicks:
# - 35-min cycles: 25-min run at +1T/min then 10-min pullback at -1T/min
#   (net +15T/cycle). The peak minute is forced to high = close + 3T and the
#   trough minute to low = close - 3T, so every cycle's M5 peak/trough is a
#   STRICTLY confirmed swing by construction (neighbors' wicks are clamped
#   1T from their closes) -- swings, then BOS, print on schedule: trend is
#   known once H1/L1/H2/L2 confirm (~m85) and the second same-direction BOS
#   lands ~m120, comfortably before the 11:30 template lock.
# - minutes 140-169 are a displacement block: 10-min run, a 5-min +4T/min
#   burst (one big-bodied M5 => bullish FVG vs the pre-burst candle), then a
#   15-min -1T/min fade whose M5 closes step down INTO the gap's upper half
#   (CE hold) without ever closing beyond its far edge.
# - remaining minutes resume 25/10 cycles (truncated at session end).
# The opening range high is broken by consecutive M5 CLOSES early in run 1
# (DEAD, never wick-through-close-back swept) and price never returns to the
# ORL zone: no OR edge is ever swept or reclaimed, so the day cannot read as
# a trap; sweep stays quiet on this day by construction.


def _trend_candles(sc: Scenario) -> list[Candle]:
    total = sc.spec.session_minutes
    plan: list[tuple[int, int, int, int]] = []
    forced: dict[int, tuple[str, int]] = {}
    c = 0

    def leg(minutes: int, step: int, vol: int, spike: str | None = None) -> None:
        nonlocal c
        for _ in range(min(minutes, total - len(plan))):
            c += step
            plan.append((c, c - 1, c + 1, vol))
        if spike and len(plan) <= total:
            forced[len(plan) - 1] = (
                ("high", c + 3) if spike == "high" else ("low", c - 3))

    for _ in range(4):                       # m0-139: four swing cycles
        leg(25, +1, 1000, spike="high")
        leg(10, -1, 700, spike="low")
    leg(10, +1, 1000)                        # m140-169: displacement block
    leg(5, +4, 1600)                         # burst M5 => FVG_BULL
    leg(15, -1, 700)                         # fade retests the gap (CE hold)
    while len(plan) < total:                 # afternoon: resume the stair
        leg(25, +1, 1100, spike="high")
        leg(10, -1, 700, spike="low")
    return _plan_candles(sc, sc.rng(), plan, forced)


def trend_day(symbol: str, date: date_type, open_price: float,
              spec: MarketSpec = NSE) -> Scenario:
    """One-way LONG trend day (scripted; see commentary above): stair-step
    cycles whose forced peak/trough spikes confirm M5 swings on schedule, so
    >=2 same-direction BOS print before the 11:30 template lock; a midday
    displacement burst leaves a bullish FVG that the following fade retests
    (CE hold); closes near the high; no OR edge is ever swept."""
    return Scenario(
        "trend_day", symbol, date, [], open_price,
        truth={"direction": "LONG", "template": "TREND"},
        script=_trend_candles, spec=spec,
    )


# ---------------------------------------------------------- range_pin script
#
# OR forms in minutes 0-14 (high +10T forced at m2, low -10T forced at m12),
# then the whole day is a fixed +/-4T triangle wave around base with wick
# clamps +/-6T: no wick can come within 3T of either OR zone (+/-9..11T), so
# both edges hold ACTIVE all session -- RANGE_PIN by construction. The wave
# is periodic (60-minute M5 cycle), so confirmed swings are rare and never
# stack two same-direction BOS by 11:30.

_RANGE_PIN_OR: list[tuple[list[int], int, int]] = [
    ([2, 4, 5, 4, 3], 0, 8), ([2, 1, 0, -1, -2], -4, 4), ([-3, -4, -4, -3, -2], -6, 0),
]
_RANGE_PIN_WAVE = [0, 2, 3, 4, 3, 2, 0, -2, -3, -4, -3, -2]


def _range_pin_candles(sc: Scenario) -> list[Candle]:
    plan = [(c, lo, hi, 1000) for closes, lo, hi in _RANGE_PIN_OR for c in closes]
    n = sc.spec.session_minutes - len(plan)
    plan += [(_RANGE_PIN_WAVE[m % len(_RANGE_PIN_WAVE)], -6, 6, 800)
             for m in range(n)]
    return _plan_candles(sc, sc.rng(), plan,
                         forced={2: ("high", 10), 12: ("low", -10)})


def range_pin(symbol: str, date: date_type, open_price: float,
              spec: MarketSpec = NSE) -> Scenario:
    """Range-pin day: opening range forms, then tight chop strictly inside
    the OR band all session; both OR edges hold (never swept, never broken).
    """
    return Scenario("range_pin", symbol, date, [], open_price,
                    truth={"template": "RANGE_PIN"},
                    script=_range_pin_candles, spec=spec)


# --------------------------------------------------------- double_trap script
#
# Both OR edges are swept (wick-through + same-M5-bucket close-back, judas
# style) BEFORE the 11:30 template lock:
# m0-14   OR: high +10T (forced m2), low -10T (forced m12); zones +/-9..11T
# m15-29  drift down, closes hold above the ORL zone (no 2-candle break)
# m30-34  ORL SWEEP: m32 spikes to -14T (= OR low - 4T, unique day low, 4x
#         volume); the M5 bucket closes -6T, back above the zone => SWEPT
# m35-39  recovery closes to 0 => ORL RECLAIMED inside the reclaim window
# m40-119 grind up toward (never through) the ORH zone
# m120-4  ORH SWEEP mirror: m122 spikes to +14T (unique day high, 4x
#         volume); M5 closes +7T, back below the zone => SWEPT
# m125-9  closes fall to +3T => ORH RECLAIMED
# m130-4  settles ~+2T; the 11:30 M5 close locks the template: both edges
#         swept => DOUBLE_TRAP
# m135+   mid-range wave (-2..+3T), closing the day near 0 = mid-range.

_DT_SWEEP_LOW_MINUTE, _DT_SWEEP_HIGH_MINUTE = 32, 122
_DT_MORNING: list[tuple[list[int], int, int]] = [
    ([2, 4, 6, 5, 4], 0, 8), ([3, 1, -1, -3, -4], -6, 5), ([-5, -6, -6, -5, -4], -8, -3),
    ([-4, -5, -5, -6, -6], -8, -3), ([-6, -7, -7, -6, -7], -8, -4),
    ([-7, -7, -8, -8, -8], -8, -5),
    ([-8, -8, -7, -7, -6], -8, -4),   # ORL sweep bucket (m30-34)
    ([-4, -3, -2, -1, 0], -6, 2),     # reclaim bucket
]
_DT_FORCED = {2: ("high", 10), 12: ("low", -10),
              _DT_SWEEP_LOW_MINUTE: ("low", -14),
              _DT_SWEEP_HIGH_MINUTE: ("high", 14)}


def _double_trap_candles(sc: Scenario) -> list[Candle]:
    plan = [(c, lo, hi, 1000) for closes, lo, hi in _DT_MORNING for c in closes]
    for m in range(80):                          # m40-119: grind up 0 -> ~6T
        trend = min(6, m * 7 // 80)
        c = max(-2, min(7, trend + (0, 1, 1, 0, -1)[m % 5]))
        plan.append((c, -3, 8, 900))
    plan += [(c, 5, 9, 1000) for c in (7, 8, 8, 8, 7)]   # ORH sweep bucket
    plan += [(c, 1, 7, 900) for c in (5, 4, 3, 3, 3)]    # reclaim bucket
    plan += [(c, 0, 4, 800) for c in (2, 2, 1, 2, 2)]    # into the 11:30 lock
    n = sc.spec.session_minutes - len(plan)
    wave = [0, 1, 2, 3, 2, 1, 0, -1, -2, -1]
    plan += [(wave[m % len(wave)], -4, 5, 900) for m in range(n)]
    return _plan_candles(
        sc, sc.rng(), plan, _DT_FORCED,
        boosted=frozenset({_DT_SWEEP_LOW_MINUTE, _DT_SWEEP_HIGH_MINUTE}))


def double_trap(symbol: str, date: date_type, open_price: float,
                spec: MarketSpec = NSE) -> Scenario:
    """Double-trap day: ORL swept (~m32) and reclaimed, then ORH swept
    (~m122) and reclaimed -- both before the 11:30 template lock -- with the
    spike wicks the unique day extremes by construction; closes mid-range.
    """
    sc = Scenario("double_trap", symbol, date, [], open_price,
                  script=_double_trap_candles, spec=spec)
    candles = sc.candles()  # deterministic: read ground truth back
    sc.truth = {
        "template": "DOUBLE_TRAP",
        "sweep_low_minute": _DT_SWEEP_LOW_MINUTE,
        "sweep_high_minute": _DT_SWEEP_HIGH_MINUTE,
        "day_low": candles[_DT_SWEEP_LOW_MINUTE].low,
        "day_high": candles[_DT_SWEEP_HIGH_MINUTE].high,
    }
    return sc
