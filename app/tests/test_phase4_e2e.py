"""Phase-4 gate: 9 e2e assertions against the Orchestrator/Journal interfaces.

PRE-MERGE SKELETON -- reconciliation notes for the controller:
- ARM_THRESHOLD / VERDICT_MIN below are the calibration targets from the
  task-7 diagnosis. This worktree still ships config threshold 65 and
  pipeline._VERDICT_MIN 30, so _run_day applies both locally (config copy +
  module-constant patch, restored after the run). Once Agent A lands the
  recalibration in source, drop the patch block and read both from config.
- range_pin's best zone scores raw 3.5 by construction (NEUTRAL cluster), so
  VERDICT_MIN must stay <= 3.5 for assertion 3's "observed" leg; if the
  landed _VERDICT_MIN is higher, that assertion needs a decision.
- XFAIL_PARALLEL marks assertions whose shapes land with the parallel agents
  (A: judas enrichment; B: stop_hunt_survive). Flip them off at merge.
"""

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

import pytest

import trader.engine.pipeline as pipeline
import trader.feed.mock as mock
from trader.config import Settings
from trader.engine.context import DayState, StockContext
from trader.engine.gates import GateChain, RiskState
from trader.engine.pipeline import Orchestrator, SymbolPipeline
from trader.execution.manager import PositionManager
from trader.execution.paper import PaperBroker
from trader.feed.mock import ScenarioFeed, double_trap, judas_reversal, range_pin
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction
from trader.models.position import ExitReason
from trader.models.signal import TradePlan
from trader.store.candles import CandleStore
from trader.store.journal import Journal

# ---------------------------------------------------- reconciliation constants
ARM_THRESHOLD = 20.0          # target config confluence.threshold (diagnosis A)
VERDICT_MIN = 3.0             # target pipeline._VERDICT_MIN (<= 3.5, see module doc)
SYMBOL, DAY, OPEN_PRICE = "ACME", date(2026, 7, 14), 100.0
CAPITAL, MAX_QTY = 100000, 50
POST_OBSERVE = time(11, 0)    # config time.observe_until
SQUAREOFF = (15, 10)          # config time.squareoff
DT_RECLAIM_END_OFFSET = 8     # double_trap reclaim bucket closes sweep_high+8m
MULT_KEYS = {"align", "time", "template", "obviousness"}
FILL_KINDS = ("trade_open", "trade_partial", "trade_close")
EXIT_REASONS = {r.value for r in ExitReason}

IST = ZoneInfo("Asia/Kolkata")
CONFIG = Path(__file__).resolve().parent.parent / "config" / "config.json"
D = Decimal
XFAIL_PARALLEL = pytest.mark.xfail(
    strict=False, reason="shape lands with parallel agents; controller flips off")


class DayRun(NamedTuple):
    summary: dict
    entries: list[dict]
    scenario: object


def _cfg() -> Settings:
    raw = json.loads(CONFIG.read_text())
    raw["confluence"]["threshold"] = ARM_THRESHOLD
    return Settings.model_validate(raw)


def _run_day(make, tmp: Path) -> DayRun:
    sc = make(SYMBOL, DAY, OPEN_PRICE)
    orch = Orchestrator(_cfg(), ScenarioFeed([sc]), [SYMBOL],
                        capital=CAPITAL, max_qty=MAX_QTY, journal_dir=tmp)
    old, pipeline._VERDICT_MIN = pipeline._VERDICT_MIN, VERDICT_MIN
    try:
        summary = orch.run()
    finally:
        pipeline._VERDICT_MIN = old
    return DayRun(summary, orch.journal.read(DAY), sc)


def _kind(entries, k):
    return [e for e in entries if e["kind"] == k]


def _at(e) -> datetime:
    return datetime.fromisoformat(e["at"])


@pytest.fixture(scope="module")
def judas(tmp_path_factory):
    return _run_day(judas_reversal, tmp_path_factory.mktemp("judas"))


@pytest.fixture(scope="module")
def range_pin_day(tmp_path_factory):
    return _run_day(range_pin, tmp_path_factory.mktemp("range_pin"))


@pytest.fixture(scope="module")
def double_trap_day(tmp_path_factory):
    return _run_day(double_trap, tmp_path_factory.mktemp("double_trap"))


def _scripted_position_day(tmp: Path):
    """SymbolPipeline holding a scripted LONG into the close: fill ~14:55,
    price flat above stop, EOD squareoff fires on the 15:10 M5 close."""
    s = _cfg()
    spec = s.market_spec()
    pipe = SymbolPipeline(SYMBOL, s, CandleStore(tmp / "candles", spec),
                          Journal(tmp / "journal"), PaperBroker(s),
                          PositionManager(s, spec), RiskState(s), MAX_QTY)
    t0 = datetime.combine(DAY, time(14, 50), tzinfo=IST)
    bar = lambda m, o, h, lo, c: Candle(          # noqa: E731
        SYMBOL, Timeframe.M1, t0 + timedelta(minutes=m),
        D(str(o)), D(str(h)), D(str(lo)), D(str(c)), 1000)
    pipe.on_m1(bar(0, 100, 100, 100, 100))                    # warm-up M5
    pipe._pending_plan = TradePlan(                           # scripted arm
        SYMBOL, Direction.LONG, (D("99"), D("101")), D("95"),
        [D("107"), D("110")], MAX_QTY, ARM_THRESHOLD, t0,
        {"final": ARM_THRESHOLD, "mults": {"align": 1.0}})
    for m in (5, 10, 15, 20):                                 # fill, hold, EOD
        pipe.on_m1(bar(m, 100, 101, 99, 100))
    return pipe, pipe.journal.read(DAY)


# (1) judas: armed zone post-11:00, LONG open, SL below swept zone, mults
@XFAIL_PARALLEL
def test_judas_armed_zone_and_long_open(judas):
    armable = [v for v in _kind(judas.entries, "verdict")
               if v["final"] >= ARM_THRESHOLD and _at(v).time() >= POST_OBSERVE]
    assert armable, "no armed-strength zone post-11:00"
    opens = _kind(judas.entries, "trade_open")
    assert opens, "no trade_open journaled on judas day"
    o = opens[0]
    assert o["direction"] == "LONG" and _at(o).time() >= POST_OBSERVE
    assert D(o["stop"]) < min(judas.scenario.truth["swept_zone"])
    assert MULT_KEYS <= set(o["plan"]["mults"])


# (2) judas lifecycle completes: every open has a close with a known reason
@XFAIL_PARALLEL
def test_judas_lifecycle_completes(judas):
    opens, closes = (_kind(judas.entries, k) for k in ("trade_open", "trade_close"))
    assert closes and len(closes) == len(opens)
    assert all(c["reason"] in EXIT_REASONS for c in closes)
    assert all({"pnl", "r", "exit_price"} <= set(c) for c in closes)


# (3) range_pin: zero trades, but the day was observed (verdict or skip)
def test_range_pin_zero_trades_but_observed(range_pin_day):
    assert range_pin_day.summary["trades"] == 0
    assert not _kind(range_pin_day.entries, "trade_open")
    assert (_kind(range_pin_day.entries, "verdict")
            or _kind(range_pin_day.entries, "skip"))


# (4) double_trap: no trade before the second sweep's reclaim completes
@XFAIL_PARALLEL
def test_double_trap_no_trades_before_second_reclaim(double_trap_day):
    truth = double_trap_day.scenario.truth
    reclaim_min = truth.get("reclaim_high_minute",
                            truth["sweep_high_minute"] + DT_RECLAIM_END_OFFSET)
    cutoff = double_trap_day.scenario.session_open() + timedelta(minutes=reclaim_min)
    early = [o for o in _kind(double_trap_day.entries, "trade_open")
             if _at(o) < cutoff]
    assert not early, f"trade(s) opened before 2nd reclaim {cutoff:%H:%M}: {early}"


# (5) stop_hunt_survive: wick-through survives, exits >= 1R realized
@XFAIL_PARALLEL
def test_stop_hunt_survive_holds_through_hunt(tmp_path):
    make = getattr(mock, "stop_hunt_survive", None)
    if make is None:
        pytest.skip("stop_hunt_survive scenario not landed yet (Agent B)")
    run = _run_day(make, tmp_path)
    assert _kind(run.entries, "hunt_survived"), "hunt candle did not journal"
    assert sum(c["r"] for c in _kind(run.entries, "trade_close")) >= 1.0


# (6) two consecutive losses lock RiskState; third arm is gate-blocked
def test_two_losses_block_third_arm(tmp_path):
    s = _cfg()
    risk = RiskState(s)
    risk.record_close(-1.0)
    risk.record_close(-1.0)
    assert risk.consecutive_losses == 2 and risk.locked
    t = datetime.combine(DAY, time(11, 30), tzinfo=IST)
    ctx = StockContext(SYMBOL, t, CandleStore(tmp_path / "c").view(SYMBOL, t),
                       [], [], DayState(session_date=DAY, template="TREND"))
    verdict = GateChain(s).check(ctx, Direction.LONG, None, "UNCLEAR", risk)
    assert not verdict.allow and verdict.gate == "risk_budget"


# (7) EOD: an open position is squared off by 15:10 with reason EXIT_EOD
def test_eod_squareoff_by_1510(tmp_path):
    pipe, entries = _scripted_position_day(tmp_path)
    closes = _kind(entries, "trade_close")
    assert pipe.position is None and len(closes) == 1
    c = closes[0]
    assert c["reason"] == ExitReason.EOD.value
    assert (_at(c).hour, _at(c).minute) <= SQUAREOFF


# (8) determinism: same judas day twice => identical journals sans wall-clock ts
def test_judas_journal_deterministic(judas, tmp_path):
    rerun = _run_day(judas_reversal, tmp_path)
    strip = lambda es: [{k: v for k, v in e.items() if k != "ts"} for e in es]
    assert judas.entries, "judas day journaled nothing (vacuous determinism)"
    assert strip(rerun.entries) == strip(judas.entries)


# (9) every fill journaled anywhere carries positive costs
def test_every_fill_has_positive_costs(judas, range_pin_day, double_trap_day,
                                       tmp_path):
    _, scripted = _scripted_position_day(tmp_path)
    fills = [e for run in (judas.entries, range_pin_day.entries,
                           double_trap_day.entries, scripted)
             for e in run if e["kind"] in FILL_KINDS]
    assert len(fills) >= 2, "scripted day must contribute open+close fills"
    assert all(D(e["costs"]) > 0 for e in fills)
