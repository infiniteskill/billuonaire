"""Phase-4 gate: 9 e2e assertions against the Orchestrator/Journal interfaces."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

import pytest

from trader.config import Settings
from trader.engine.context import DayState, StockContext
from trader.engine.gates import GateChain, RiskState
from trader.engine.pipeline import Orchestrator, SymbolPipeline
from trader.execution.manager import PositionManager
from trader.execution.paper import PaperBroker
from trader.feed.mock import (ScenarioFeed, double_trap, judas_reversal,
                              range_pin, stop_hunt_survive)
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction
from trader.models.position import ExitReason
from trader.models.signal import TradePlan
from trader.store.candles import CandleStore
from trader.store.journal import Journal

# --------------------------------------------------------------- gate constants
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


class DayRun(NamedTuple):
    summary: dict
    entries: list[dict]
    scenario: object


def _cfg() -> Settings:
    from tests.harness import ALL_IMPLEMENTED, scenario_settings
    return scenario_settings(ALL_IMPLEMENTED)  # shipped enabled, guard off


ARM_THRESHOLD = _cfg().confluence.threshold  # shipped config.json calibration


def _run_day(make, tmp: Path) -> DayRun:
    sc = make(SYMBOL, DAY, OPEN_PRICE)
    orch = Orchestrator(_cfg(), ScenarioFeed([sc]), [SYMBOL],
                        capital=CAPITAL, max_qty=MAX_QTY, journal_dir=tmp)
    summary = orch.run()
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
    # fill must land BEFORE the 14:30 late-fill cutoff (pipeline drops later fills)
    t0 = datetime.combine(DAY, time(14, 20), tzinfo=IST)
    bar = lambda m, o, h, lo, c: Candle(          # noqa: E731
        SYMBOL, Timeframe.M1, t0 + timedelta(minutes=m),
        D(str(o)), D(str(h)), D(str(lo)), D(str(c)), 1000)
    pipe.on_m1(bar(0, 100, 100, 100, 100))                    # warm-up M5
    pipe._pending_plan = TradePlan(                           # scripted arm
        SYMBOL, Direction.LONG, (D("99"), D("101")), D("95"),
        [D("107"), D("110")], MAX_QTY, ARM_THRESHOLD, t0,
        {"final": ARM_THRESHOLD, "mults": {"align": 1.0}})
    for m in range(5, 60, 5):                # fill 14:25, hold to 15:15 (EOD 15:10)
        pipe.on_m1(bar(m, 100, 101, 99, 100))
    return pipe, pipe.journal.read(DAY)


# (1) judas: armed zone post-11:00, LONG open, SL below swept zone, mults
def test_judas_armed_zone_and_long_open(judas):
    armable = [v for v in _kind(judas.entries, "verdict")
               if v["final"] >= ARM_THRESHOLD and _at(v).time() >= POST_OBSERVE]
    assert armable, "no armed-strength zone post-11:00"
    opens = _kind(judas.entries, "trade_open")
    assert opens, "no trade_open journaled on judas day"
    o = opens[0]
    assert o["direction"] == "LONG" and _at(o).time() >= POST_OBSERVE
    # SL behind the TRADED zone (tightest level inside the entry cluster);
    # the cluster itself still anchors at the swept pivot (floor = pivot lo).
    assert D(o["stop"]) < D(o["zone"][0])
    assert D(o["plan"]["cluster"][0]) == min(judas.scenario.truth["pivot_zone"])
    assert MULT_KEYS <= set(o["plan"]["mults"])


# (2) judas lifecycle completes: every open has a close with a known reason
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
def test_double_trap_no_trades_before_second_reclaim(double_trap_day):
    truth = double_trap_day.scenario.truth
    # no scenario sets reclaim_high_minute; the reclaim bucket always closes
    # DT_RECLAIM_END_OFFSET minutes after the sweep (mock.py double_trap)
    reclaim_min = truth["sweep_high_minute"] + DT_RECLAIM_END_OFFSET
    cutoff = double_trap_day.scenario.session_open() + timedelta(minutes=reclaim_min)
    early = [o for o in _kind(double_trap_day.entries, "trade_open")
             if _at(o) < cutoff]
    assert not early, f"trade(s) opened before 2nd reclaim {cutoff:%H:%M}: {early}"


# (5) stop_hunt_survive: wick-through survives, pinned to THE hunt bucket,
# targets execute as partials (B1) and the runner rides >= 1R gross to EOD
# (traded-zone entries carry tiny risk, so R-fallback targets collapse into
# T1 and the remainder always outlives the target ladder; flat brokerage
# swamps net r at this scenario's tiny notional, so gross price R is asserted)
def test_stop_hunt_survive_holds_through_hunt(tmp_path):
    run = _run_day(stop_hunt_survive, tmp_path)
    truth = run.scenario.truth
    hunts = _kind(run.entries, "hunt_survived")
    assert hunts, "hunt candle did not journal"
    bucket = truth["hunt_minute"] - truth["hunt_minute"] % 5
    hunt_close = run.scenario.session_open() + timedelta(minutes=bucket + 5)
    assert _at(hunts[0]) == hunt_close
    # stop behind the TRADED zone (the pivot level itself), hunt wick pierced
    # it and the close-confirm held
    assert D(hunts[0]["stop"]) < min(truth["pivot_zone"])
    o, c = _kind(run.entries, "trade_open")[0], _kind(run.entries, "trade_close")[-1]
    assert _kind(run.entries, "trade_partial"), "targets did not execute"
    assert c["reason"] == ExitReason.EOD.value             # runner squared off
    risk = D(o["price"]) - D(o["stop"])
    assert (D(c["exit_price"]) - D(o["price"])) / risk >= 1


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


# (7b) targets: a spike M5 through T2+T3 partials AT T2 and closes EXIT_TARGET
def test_target_ladder_exit_journaled(tmp_path):
    s = _cfg()
    spec = s.market_spec()
    pipe = SymbolPipeline(SYMBOL, s, CandleStore(tmp_path / "candles", spec),
                          Journal(tmp_path / "journal"), PaperBroker(s),
                          PositionManager(s, spec), RiskState(s), MAX_QTY)
    t0 = datetime.combine(DAY, time(11, 0), tzinfo=IST)
    bar = lambda m, o, h, lo, c: Candle(          # noqa: E731
        SYMBOL, Timeframe.M1, t0 + timedelta(minutes=m),
        D(str(o)), D(str(h)), D(str(lo)), D(str(c)), 1000)
    pipe.on_m1(bar(0, 100, 100, 100, 100))
    pipe._pending_plan = TradePlan(               # scripted arm, T = 104/106/108
        SYMBOL, Direction.LONG, (D("99"), D("101")), D("95"),
        [D("104"), D("106"), D("108")], MAX_QTY, ARM_THRESHOLD, t0,
        {"final": ARM_THRESHOLD, "mults": {"align": 1.0}})
    pipe.on_m1(bar(5, 100, 101, 99, 100))         # entry fills 11:05 @ ~100.05
    pipe.on_m1(bar(10, 110, 112, 109, 111))       # spike M5 through T2 and T3
    pipe.on_m1(bar(15, 111, 111, 111, 111))       # close evaluates the spike
    entries = pipe.journal.read(DAY)
    parts, closes = _kind(entries, "trade_partial"), _kind(entries, "trade_close")
    assert [p["reason"] for p in parts] == ["1R", "T2"]
    assert D(parts[1]["price"]) == D("106.00")    # limit AT T2 (2bps < half tick)
    assert pipe.position is None and len(closes) == 1
    assert closes[0]["reason"] == ExitReason.TARGET.value and closes[0]["why"] == "T3"
    assert D(closes[0]["exit_price"]) == D("108.00")


# (8) determinism: same judas day twice => byte-identical journals, sim-time
# ts included (A7: Journal.log ts = pipeline event time, not wall clock)
def test_judas_journal_deterministic(judas, tmp_path):
    rerun = _run_day(judas_reversal, tmp_path)
    assert judas.entries, "judas day journaled nothing (vacuous determinism)"
    assert rerun.entries == judas.entries
    assert all(e["ts"] == e["at"] for e in judas.entries if "at" in e)


# (9) every fill journaled anywhere carries positive costs
def test_every_fill_has_positive_costs(judas, range_pin_day, double_trap_day,
                                       tmp_path):
    _, scripted = _scripted_position_day(tmp_path)
    fills = [e for run in (judas.entries, range_pin_day.entries,
                           double_trap_day.entries, scripted)
             for e in run if e["kind"] in FILL_KINDS]
    assert len(fills) >= 2, "scripted day must contribute open+close fills"
    assert all(D(e["costs"]) > 0 for e in fills)
