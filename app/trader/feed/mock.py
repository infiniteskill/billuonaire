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
#
# Post-11:00 canonical reversal (b16.. = m80..): b16 dips to a forced +6T low
# -> confirmed M5 SWING_L "PL" zone (5,7)T at 10:55; rally to a forced +25T
# swing high H3 (the >=1.5R target pool); a GENTLE pullback (all-red M5s,
# lows pinned minclose-3 so no bucket gaps its 2nd predecessor: no bearish
# OB displacement, no bearish M5 FVG) into a flat bottom that TESTS PL 3x
# (touches>=3 => sweep quality + obviousness 1.15); b36 lower-high H4
# (forced 12T); b37 red OB candle spanning (5,11)T closes AT 5T (m56 pins
# b11's high to 4T so the (b11,b12,b13) morning gap reads (4,7)T and its CE
# 5.5T sits above that close: no morning CE_HOLD can drag a day-2 cluster
# below the pivot -- day 2 carries live ATR/wyckoff from the open); b38
# single-candle SWEEP of PL (forced low 3T, 4x volume, M5 closes 9T) =>
# SWEPT, reclaimed b39 (sweep upgrade); b38-40 displacement (8T off the b37
# close => OB_BULL) leaves a bullish FVG (9,11)T; b41 retest closes 10T:
# holds the FVG CE (CE_HOLD) inside the OB (OB_RETEST); b42 closes 13T >
# mid(H4) => CHoCH LONG on the trigger candle itself. sweep+orderblock+fvg+
# structure (+wyckoff/volume boosters) cluster over (5,13)T: a distinct>=4
# LONG pivot, 8T wide (stop 4T, risk 5T < 1.2xATR), with H3 liquidity 11T+
# above for >=1.5R room. The afternoon (m225+) stair-steps +1T/min with
# shallow alternating dips: no bearish OB/FVG, LONG close near the high.

_JUDAS_MORNING: list[tuple[list[int], int, int]] = [
    ([2, 5, 8, 6, 4], -1, 8), ([3, 2, 1, 1, 0], -1, 4), ([0, -1, -1, 0, -1], -1, 1),
    ([-1, 0, -1, 1, 2], -1, 3), ([3, 4, 5, 5, 4], 0, 5), ([3, 3, 2, 1, 1], 0, 4),
    ([1, 0, 0, 1, 0], -1, 2), ([-1, -1, -1, 0, 1], -1, 2), ([2, 3, 4, 4, 4], 0, 4),
    ([3, 3, 2, 2, 2], 1, 4), ([2, 1, 1, 1, 1], 0, 3), ([1, 1, 0, 1, 1], 0, 4),
    ([3, 5, 6, 7, 7], 1, 8), ([8, 9, 9, 10, 10], 7, 11),
    ([11, 11, 12, 12, 12], 9, 13), ([12, 13, 13, 13, 13], 11, 14),
]
_JUDAS_AFTERNOON: list[tuple[list[int], int, int]] = [
    ([12, 11, 10, 10, 11], 9, 13), ([11, 12, 12, 13, 13], 10, 14),   # b16-17
    ([13, 13, 14, 14, 14], 12, 15), ([14, 15, 15, 15, 15], 13, 16),  # b18-19
    ([16, 16, 17, 17, 17], 14, 18), ([18, 18, 19, 19, 19], 16, 20),  # b20-21
    ([20, 21, 21, 21, 21], 18, 23), ([22, 22, 23, 22, 22], 20, 23),  # b22-23
    ([22, 21, 21, 21, 21], 19, 23), ([21, 21, 20, 20, 20], 18, 22),  # b24-25
    ([21, 22, 22, 23, 23], 19, 23), ([22, 22, 21, 21, 21], 18, 24),  # b26-27
    ([20, 20, 19, 19, 19], 16, 22), ([18, 18, 17, 17, 17], 14, 20),  # b28-29
    ([16, 16, 15, 15, 15], 12, 18), ([14, 14, 13, 13, 13], 10, 16),  # b30-31
    ([12, 12, 11, 11, 11], 8, 14), ([10, 10, 9, 9, 9], 7, 11),       # b32-33
    ([9, 9, 8, 8, 8], 6, 10), ([8, 8, 8, 9, 9], 6, 10),              # b34-35
    ([10, 10, 11, 10, 9], 8, 12), ([8, 7, 6, 5, 5], 5, 11),          # b36-37
    ([6, 6, 8, 9, 9], 4, 9), ([10, 10, 11, 11, 11], 9, 11),          # b38-39
    ([12, 12, 13, 13, 13], 11, 13), ([12, 11, 11, 10, 10], 9, 13),   # b40-41
    ([11, 12, 12, 13, 13], 10, 13), ([14, 14, 15, 15, 15], 12, 16),  # b42-43
    ([15, 16, 16, 17, 17], 14, 18),                                  # b44
]
_JUDAS_FORCED = {2: ("high", 9), 12: ("low", -2), 17: ("low", -3), 22: ("high", 8),
                 37: ("low", -6), 44: ("high", 5), 56: ("high", 4), 57: ("low", -1),
                 # afternoon: PL dip, H3 target pool, gentle-pullback low pins,
                 # PL touches, H4/OB highs, pivot sweep spike, FVG far edge
                 82: ("low", 6), 112: ("high", 25), 138: ("low", 18),
                 143: ("low", 16), 148: ("low", 14), 153: ("low", 12),
                 158: ("low", 10), 163: ("low", 8), 168: ("low", 7),
                 173: ("low", 6), 176: ("low", 6), 182: ("high", 12),
                 185: ("high", 11), 191: ("low", 3)}
_SWEEP_MINUTE = 37
_PIVOT_SWEEP_MINUTE = 191
_SWEEP_VOLUME_MULT = 4


def _judas_candles(sc: Scenario) -> list[Candle]:
    rng = sc.rng()
    # (close, low clamp, high clamp, base volume) per minute, in ticks
    plan: list[tuple[int, int, int, int]] = []
    for i, (closes, lo, hi) in enumerate(_JUDAS_MORNING):
        plan += [(c, lo, hi, 1000 if i < 8 else 1200) for c in closes]
    for closes, lo, hi in _JUDAS_AFTERNOON:                # m80-224: reversal
        plan += [(c, lo, hi, 1000) for c in closes]
    c = 17
    for i in range(sc.spec.session_minutes - len(plan)):   # m225+: gentle stair
        c += 1 if i % 50 < 40 else (-1 if i % 2 else 0)
        plan.append((c, c - 3, c + 3, 1100))
    return _plan_candles(sc, rng, plan, _JUDAS_FORCED,
                         boosted=frozenset({_SWEEP_MINUTE, _PIVOT_SWEEP_MINUTE}))


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
        "pivot_sweep_minute": _PIVOT_SWEEP_MINUTE,        # PL sweep spike
        "pivot_zone": (candles[82].low - spec.tick_size,  # PL swing-low zone
                       candles[82].low + spec.tick_size),
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


# --------------------------------------------------- stop_hunt_survive script
#
# Judas morning (minutes 0-79 reused verbatim: ORL swept m37, CHoCH ~10:20 =>
# TRAP_REVERSAL locks 11:30), then a scripted post-11:00 LONG setup at a
# fresh pivot; all ticks from base = tick(open_price):
# m80-99   chop wave 16..20T; period-4 wave + exact clamps tie every M5
#          high/low => no swings, no sweeps, no M5 gap up into the ramp
# m100-109 ramp to 25T, lows floored 21T so the 20T pivot stays a strict low
# b22      peak doji, forced high 29T => SWING_H "TH1" (28,30)
# b23      full-body drop 25->22T clamped to (22,25): a high-quality demand
#          OB once b25-b26 displace up (marubozu => body_pct 1.0)
# b24      the PIVOT: forced low 20T, M5 close 21 => SWING_L (19,21); its
#          high is pinned 22T = FVG c1
# b25-b26  rally to 30T; b26 low pinned 26T => FVG_BULL (22,26) by
#          construction; close 30 > TH1 mid 29 => BOS LONG; forced high 33
# b27      forced high 31 sweeps TH1 (close 25 < 28): the opposing sweep
#          that deepens the LONG sweep's trap chain; close 25 also holds the
#          FVG CE (24) => CE_HOLD evidence, ttl into the arm
# b28-b30  pullback sits on the pivot: forced lows 21T x3 => touches>=3;
#          M5 closes 22 inside the OB => OB retest evidence each candle
# b31      PIVOT SWEEP m157: forced low 18T under the (19,21) zone with 4x
#          volume, M5 closes 22 back above => sweep (pool+touches+chain
#          ~0.82) + orderblock + fvg cluster around (18,26)T arms the FSM
#          and the 80% lower wick triggers; fill at the m160 open (11:55).
#          Arming before minute 200 matters: wyckoff PHASE (needs 40 closed
#          M5) would otherwise tile candle-range zones over the whole
#          descent and sprawl the cluster (stop_too_wide)
# b32      HUNT m162: ONE M5 wicks to 14T, through the stop (cluster lo 18T
#          minus 0.25xATR => quantized 16-17T), but closes 21T above it =>
#          manager flags hunt_survived, position lives
# b33+     recovery, then a +1T/min stair rally into the close: 1R/2R
#          partials + EOD squareoff realize well over 1R.

_SHS_WAVE = [16, 18, 20, 18]
_SHS_PIVOT_SWEEP_MINUTE, _SHS_HUNT_MINUTE = 157, 162
_SHS_BUCKETS: list[tuple[list[int], int, int, int]] = [
    ([25, 26, 26, 25, 25], 23, 27, 900),   # b22 TH1 peak (forced high 29)
    ([24, 24, 23, 23, 22], 22, 25, 900),   # b23 marubozu drop = the OB (22,25)
    ([21, 20, 20, 20, 21], 20, 22, 900),   # b24 pivot low 20, high pinned 22
    ([23, 24, 25, 26, 26], 21, 27, 1100),  # b25 bounce
    ([28, 29, 30, 30, 30], 26, 31, 1100),  # b26 BOS>29; FVG c3 low pinned 26
    ([27, 26, 26, 25, 25], 24, 30, 900),   # b27 CE hold; forced 31 sweeps TH1
    ([24, 23, 22, 22, 22], 21, 25, 900),   # b28 OB retest, pivot touch 1
    ([23, 22, 23, 22, 22], 21, 25, 900),   # b29 pivot touch 2
    ([23, 22, 22, 22, 22], 21, 25, 900),   # b30 pivot touch 3
    ([21, 20, 22, 22, 22], 18, 23, 1000),  # b31 SWEEP (forced low 18, boosted)
    ([21, 20, 20, 21, 21], 14, 23, 900),   # b32 HUNT (forced low 14)
    ([22, 23, 24, 25, 26], 21, 27, 1000),  # b33 recovery
]
_SHS_FORCED = {112: ("high", 29), 122: ("low", 20), 132: ("high", 33),
               137: ("high", 31), 143: ("low", 21), 147: ("low", 21),
               152: ("low", 21), _SHS_PIVOT_SWEEP_MINUTE: ("low", 18),
               _SHS_HUNT_MINUTE: ("low", 14)}


def _shs_candles(sc: Scenario) -> list[Candle]:
    rng = sc.rng()
    plan: list[tuple[int, int, int, int]] = []
    for i, (closes, lo, hi) in enumerate(_JUDAS_MORNING):         # m0-79
        plan += [(c, lo, hi, 1000 if i < 8 else 1200) for c in closes]
    plan += [(_SHS_WAVE[m % 4], 16, 20, 800) for m in range(20)]  # m80-99
    plan += [(c, c - 3, c + 3, 1000) for c in range(17, 22)]      # m100-104
    plan += [(c, 21, c + 3, 1000) for c in (22, 23, 24, 25, 25)]  # m105-109
    for closes, lo, hi, vol in _SHS_BUCKETS:                      # m110-169
        plan += [(c, lo, hi, vol) for c in closes]
    c = 26
    for step, n in ((1, 30), (-1, 5)) * 5 + ((1, 30),):           # m170-374
        for _ in range(n):
            c += step
            plan.append((c, c - 3, c + 3, 1100))
    return _plan_candles(sc, rng, plan, {**_JUDAS_FORCED, **_SHS_FORCED},
                         boosted=frozenset({_SWEEP_MINUTE,
                                            _SHS_PIVOT_SWEEP_MINUTE}))


def stop_hunt_survive(symbol: str, date: date_type, open_price: float,
                      spec: MarketSpec = NSE) -> Scenario:
    """Judas-style trap-reversal day whose post-11:00 LONG entry is stop-hunted
    ONCE -- a single M5 wicks through the position's stop without closing
    beyond -- then rallies to well over 1R. See the script commentary above.
    """
    sc = Scenario("stop_hunt_survive", symbol, date, [], open_price,
                  script=_shs_candles, spec=spec)
    candles = sc.candles()  # deterministic: read ground truth back
    base, T = spec.quantize(open_price), spec.tick_size
    or_low = min(c.low for c in candles[:15])
    pivot = base + 20 * T
    sc.truth = {
        "template": "TRAP_REVERSAL",
        "sweep_low_minute": _SWEEP_MINUTE,               # morning ORL sweep
        "swept_zone": (or_low - T, or_low + T),
        "afternoon_direction": "LONG",
        "pivot_zone": (pivot - T, pivot + T),            # hunted swing low
        "pivot_sweep_minute": _SHS_PIVOT_SWEEP_MINUTE,
        "hunt_minute": _SHS_HUNT_MINUTE,
        "stop_zone": (base + 16 * T, base + 17 * T),     # engine stop lands here
    }
    return sc
