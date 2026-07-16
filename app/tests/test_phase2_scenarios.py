"""Phase-2 exit gate: scenario ground truth + detector isolation.

Runs both flagship scenarios through the real feed -> store -> LevelEngine ->
DetectorRegistry pipeline at every M5 close and asserts the detectors fire
where the scenario's ground truth says they must: the judas sweep (ORL wick-
through-close-back), the CHoCH LONG shortly after it, BOS on the trend day,
sweep silence on the trend day, detector isolation, and no lookahead.
"""

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

import pytest

import trader.detectors.liquidity  # noqa: F401  -- register phase-2 detectors
import trader.detectors.structure  # noqa: F401
import trader.detectors.sweep  # noqa: F401
import trader.detectors.swings  # noqa: F401
from trader.config import Settings
from trader.detectors.base import DetectorRegistry
from trader.engine.context import DayState, StockContext
from trader.engine.levels import LevelEngine
from trader.feed.mock import ScenarioFeed, judas_reversal, trend_day
from trader.models.candle import Timeframe
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
DAY = date(2026, 7, 15)
CONFIG = Path(__file__).resolve().parent.parent / "config" / "config.json"
PHASE2 = ("swings", "liquidity", "structure", "sweep")
JUDAS = judas_reversal("X", DAY, 100.0)
TREND = trend_day("X", DAY, 100.0)

class Run(NamedTuple):
    now: datetime            # M5 close this tick evaluated at
    evidence: list


class Result(NamedTuple):
    runs: list[Run]
    levels: list
    history: list


def phase2_settings(enabled: tuple = PHASE2) -> Settings:
    raw = json.loads(CONFIG.read_text())
    raw["detectors"]["enabled"] = list(enabled)
    return Settings.model_validate(raw)


def run_scenario(scenario, enabled: tuple = PHASE2) -> Result:
    """Pump the scenario's M1s; at each M5 close run LevelEngine.update on the
    latest closed M5, then the registry, accumulating evidence_history."""
    registry = DetectorRegistry(phase2_settings(enabled))
    engine = LevelEngine({})
    store = CandleStore(Path("/unused"))
    levels, history, runs = [], [], []
    feed = ScenarioFeed([scenario])
    feed.subscribe([scenario.symbol])
    for i, event in enumerate(feed.events()):
        store.add(event.candle)
        if (i + 1) % 5:
            continue
        now = event.candle.ts + timedelta(minutes=1)
        view = store.view(scenario.symbol, now)
        ctx = StockContext(symbol=scenario.symbol, now=now, candles=view,
                           levels=levels, evidence_history=history,
                           day=DayState(session_date=scenario.date))
        engine.update(levels, view.last(1, Timeframe.M5)[-1], ctx.atr(Timeframe.M5))
        evidence = registry.run_all(ctx)
        runs.append(Run(now, evidence))
        history.extend(evidence)
    assert len(runs) == 75
    return Result(runs, levels, history)


@pytest.fixture(scope="module")
def judas() -> Result:
    return run_scenario(JUDAS)


@pytest.fixture(scope="module")
def trend() -> Result:
    return run_scenario(TREND)


def m5_close(minute: int) -> datetime:
    open_ = datetime.combine(DAY, time(9, 15), tzinfo=IST)
    return open_ + timedelta(minutes=(minute // 5 + 1) * 5)


def sweeps(result: Result) -> list:
    return [e for e in result.history if e.detector == "sweep"]


def structure_events(result: Result, event: str, direction: Direction) -> list:
    return [e for e in result.history if e.detector == "structure"
            and e.meta.get("event") == event and e.direction is direction]


# 1. sweep fires near truth minute, LONG, on a low pool at reversal_from
def test_judas_sweep_near_truth_minute(judas):
    target = JUDAS.truth["reversal_from"]
    band = target * Decimal("0.003")  # both zone bounds within 0.3% of truth
    center = m5_close(JUDAS.truth["sweep_low_minute"])
    tol = timedelta(minutes=4 * 5)
    hits = [e for e in sweeps(judas)
            if e.direction is Direction.LONG
            and e.meta["kind"] in ("OPEN_RANGE_L", "SWING_L")
            and abs(e.ts - center) <= tol
            and all(abs(z - target) <= band for z in e.zone)]
    assert hits, "no LONG sweep evidence on OPEN_RANGE_L/SWING_L near truth"


# 2. CHoCH LONG within 12 M5 candles after the sweep
def test_judas_choch_long_within_12_m5_of_sweep(judas):
    assert sweeps(judas), "prerequisite: sweep evidence (assertion 1)"
    first = min(e.ts for e in sweeps(judas))
    direction = Direction[JUDAS.truth["afternoon_direction"]]
    hits = [e for e in structure_events(judas, "CHOCH", direction)
            if first < e.ts <= first + timedelta(minutes=12 * 5)]
    assert hits, "no CHoCH LONG within 12 M5 candles of the sweep"


# 3a. trend day produces BOS in the truth direction
def test_trend_day_bos_long(trend):
    assert structure_events(trend, "BOS", Direction[TREND.truth["direction"]])


# 3b. no strong sweep-reversal on a trend day
def test_trend_day_no_strong_sweep_reversal(trend):
    assert not [e for e in sweeps(trend) if e.strength > 0.6]


# 4. isolation: disabling structure changes nothing for the other detectors
def test_structure_isolation_and_weight_renormalization():
    reduced_set = tuple(n for n in PHASE2 if n != "structure")
    full, reduced = run_scenario(JUDAS), run_scenario(JUDAS, enabled=reduced_set)

    def stream(result: Result) -> bytes:
        return "\n".join(f"{i}|{e!r}" for i, run in enumerate(result.runs)
                         for e in run.evidence if e.detector != "structure").encode()

    assert stream(full) == stream(reduced)
    assert [repr(lv) for lv in full.levels] == [repr(lv) for lv in reduced.levels]
    assert full.levels  # non-vacuous: levels (incl. state history) really compared

    weights = phase2_settings(reduced_set).enabled_weights()
    assert weights == {"liquidity": pytest.approx(100 / 3),
                       "sweep": pytest.approx(200 / 3)}  # swings has no weight
    assert sum(weights.values()) == pytest.approx(100)


# 5. no lookahead: evidence never timestamped past its view's now
def test_no_lookahead(judas, trend):
    for result in (judas, trend):
        for run in result.runs:
            assert all(e.ts <= run.now for e in run.evidence)
