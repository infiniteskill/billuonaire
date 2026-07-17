"""Phase-4 Task 2: decision gates -- each gate isolated, RiskState, chain order."""
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.config import Settings
from trader.engine.context import DayState, StockContext
from trader.engine.gates import (ChaseGate, EventCooldownGate, GateChain,
                                 RegimeVetoGate, RiskBudgetGate, RiskState,
                                 TemplateGate, TimeWindowGate)
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
CONFIG = Path(__file__).resolve().parents[2] / "config" / "config.json"
TODAY = datetime(2026, 7, 15, tzinfo=IST)
YDAY = datetime(2026, 7, 14, tzinfo=IST)


@pytest.fixture
def settings():
    return Settings.model_validate_json(CONFIG.read_text())


def at(day, hh, mm):
    return day.replace(hour=hh, minute=mm)


def m1(ts, o=100, h=101, lo=99, c=100):
    return Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(lo), tick(c), 100)


def calm(day=TODAY, n=15):
    """One M1 per 5-min bucket => n closed M5 candles, range 2, ATR(14)=2."""
    return [m1(at(day, 9, 15) + timedelta(minutes=5 * i)) for i in range(n)]


def build_ctx(candles, now, template="TREND_UP"):
    store = CandleStore("/nonexistent")
    for c in candles:
        store.add(c)
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date(), template=template))


def gate_ctx(now=at(TODAY, 11, 30), template="TREND_UP"):
    return build_ctx(calm(), now, template)


def run(gate, ctx, direction=Direction.LONG, plan_zone=None, htf="RANGING", risk=None):
    return gate.check(ctx, direction, plan_zone, htf, risk)


# --- TimeWindowGate: entry window [session_open + observe_min, no_entry_after) ---

@pytest.mark.parametrize("hh,mm,allowed", [(10, 59, False), (11, 0, True),
                                           (14, 29, True), (14, 30, False)])
def test_time_window_boundaries(settings, hh, mm, allowed):
    v = run(TimeWindowGate(settings), gate_ctx(now=at(TODAY, hh, mm)))
    assert v.allow is allowed and v.gate == "time_window" and v.reason


# --- TemplateGate ---

def test_template_gate(settings):
    assert not run(TemplateGate(), gate_ctx(template="UNCLASSIFIED")).allow
    assert run(TemplateGate(), gate_ctx(template="TREND_UP")).allow


# --- RegimeVetoGate ---

@pytest.mark.parametrize("htf,dirn,allowed", [
    ("MARKDOWN", Direction.LONG, False), ("MARKDOWN", Direction.SHORT, True),
    ("MARKUP", Direction.SHORT, False), ("MARKUP", Direction.LONG, True),
    ("ACCUMULATION", Direction.LONG, True)])
def test_regime_veto(settings, htf, dirn, allowed):
    assert run(RegimeVetoGate(), gate_ctx(), direction=dirn, htf=htf).allow is allowed


# --- EventCooldownGate ---

def test_event_cooldown_calm_passes(settings):
    assert run(EventCooldownGate(settings), gate_ctx()).allow


def test_event_cooldown_passes_without_atr(settings):
    assert run(EventCooldownGate(settings), build_ctx([], at(TODAY, 11, 30))).allow


def test_event_cooldown_big_candle_blocks_then_expires(settings):
    gate = EventCooldownGate(settings)
    candles = calm()  # 09:15 .. 10:25
    candles.append(m1(at(TODAY, 10, 30), o=100, h=107, lo=96, c=101))  # range 11 > 3xATR
    assert not run(gate, build_ctx(candles, at(TODAY, 10, 36))).allow
    for i in range(1, 8):  # 6 candles after trigger blocked; 7th releases
        candles.append(m1(at(TODAY, 10, 30) + timedelta(minutes=5 * i)))
        now = at(TODAY, 10, 36) + timedelta(minutes=5 * i)
        assert run(gate, build_ctx(candles, now)).allow is (i == 7), f"candle {i}"


def test_event_cooldown_open_gap_blocks(settings):
    gate = EventCooldownGate(settings)
    candles = calm(day=YDAY)  # prev day closes at 100
    candles.append(m1(at(TODAY, 9, 15), o=105, h=106, lo=104, c=105))  # gap 5 > 1xATR
    assert not run(gate, build_ctx(candles, at(TODAY, 9, 21))).allow


# --- ChaseGate ---

def test_chase_gate(settings):
    zone = (Decimal("100"), Decimal("102"))
    chased = calm() + [m1(at(TODAY, 10, 30), o=102, h=104, lo=102, c=103)]
    assert not run(ChaseGate(settings), build_ctx(chased, at(TODAY, 10, 36)),
                   plan_zone=zone).allow
    inside = calm() + [m1(at(TODAY, 10, 30), o=101, h=102.5, lo=100.5, c=102.1)]
    assert run(ChaseGate(settings), build_ctx(inside, at(TODAY, 10, 36)),
               plan_zone=zone).allow
    below = calm() + [m1(at(TODAY, 10, 30), o=100, h=100.5, lo=98, c=99.5)]
    assert not run(ChaseGate(settings), build_ctx(below, at(TODAY, 10, 36)),
                   direction=Direction.SHORT, plan_zone=zone).allow
    assert run(ChaseGate(settings), gate_ctx(), plan_zone=None).allow  # no plan


# --- RiskState ---

def test_risk_state_two_losses_lock(settings):
    rs = RiskState(settings)
    rs.record_close(-1.0)
    assert not rs.locked and rs.consecutive_losses == 1
    rs.record_close(-1.0)
    assert rs.locked


def test_risk_state_win_resets_consecutive(settings):
    rs = RiskState(settings)
    rs.record_close(-1.0); rs.record_close(1.0); rs.record_close(-1.0)
    assert rs.consecutive_losses == 1 and not rs.locked


def test_risk_state_profit_lock(settings):
    rs = RiskState(settings)
    rs.record_close(2.0)  # +2R hits daily_profit_lock_R
    assert rs.locked and rs.daily_pnl_R == 2.0


def test_risk_state_daily_loss_lock(settings):
    rs = RiskState(settings)
    rs.record_close(-3.0)  # -3R * 0.5%/R = -1.5% daily loss cap
    assert rs.locked and rs.consecutive_losses == 1


def test_risk_state_open_counts_and_reset(settings):
    rs = RiskState(settings)
    rs.record_open("X"); rs.record_open("X"); rs.record_open("Y")
    rs.record_close(-1.0)
    assert rs.trades_today == 3 and rs.per_symbol == {"X": 2, "Y": 1}
    rs.reset_day()
    assert (rs.trades_today, rs.per_symbol, rs.consecutive_losses,
            rs.daily_pnl_R, rs.locked) == (0, {}, 0, 0.0, False)


# --- RiskBudgetGate ---

def test_risk_budget_gate(settings):
    gate, ctx = RiskBudgetGate(settings), gate_ctx()
    assert run(gate, ctx, risk=RiskState(settings)).allow
    assert not run(gate, ctx, risk=RiskState(settings, locked=True)).allow
    assert not run(gate, ctx, risk=RiskState(settings, trades_today=3)).allow
    assert not run(gate, ctx, risk=RiskState(settings, per_symbol={"X": 1})).allow
    assert run(gate, ctx, risk=RiskState(settings, per_symbol={"Y": 1})).allow


# --- B8: portfolio heat + correlation cap ---

def test_risk_state_open_close_releases(settings):
    rs = RiskState(settings)
    rs.record_open("A", Decimal("400"), Direction.LONG)
    rs.record_open("B", Decimal("300"), Direction.SHORT)
    assert rs.open_risk == Decimal("700")
    assert rs.open_dirs == {"A": Direction.LONG, "B": Direction.SHORT}
    rs.record_close(1.0, "A")
    assert rs.open_risk == Decimal("300") and rs.open_dirs == {"B": Direction.SHORT}
    rs.reset_day()
    assert rs.open_risk == 0 and rs.open_dirs == {}


def test_portfolio_heat_exact_boundary(settings):
    """Heat cap 1% of 100k = 1000; new plan budget 0.5% = 500. Open 500 +
    new 500 == 1000 passes (not >); a paisa more blocks."""
    gate, ctx = RiskBudgetGate(settings), gate_ctx()
    rs = RiskState(settings)
    rs.record_open("A", Decimal("500"), Direction.LONG)
    assert run(gate, ctx, risk=rs).allow
    rs2 = RiskState(settings)
    rs2.record_open("A", Decimal("500.01"), Direction.LONG)
    v = run(gate, ctx, risk=rs2)
    assert not v.allow and "heat" in v.reason


def test_correlation_cap_third_same_direction_blocked(settings):
    gate, ctx = RiskBudgetGate(settings), gate_ctx()
    rs = RiskState(settings)
    rs.record_open("A", Decimal("100"), Direction.LONG)
    rs.record_open("B", Decimal("100"), Direction.LONG)
    v = run(gate, ctx, direction=Direction.LONG, risk=rs)
    assert not v.allow and "LONG" in v.reason
    assert run(gate, ctx, direction=Direction.SHORT, risk=rs).allow


# --- B11: min_minutes_between_trades cooldown ---

def test_cooldown_after_trade_boundary_exact(settings):
    """Close at 11:30 + 15-min window: 11:44:59 blocked, 11:45:00 exact passes."""
    gate = RiskBudgetGate(settings)
    rs = RiskState(settings)
    rs.record_close(1.0, "X", ts=at(TODAY, 11, 30))
    assert rs.last_close_ts == at(TODAY, 11, 30)
    v = run(gate, gate_ctx(now=at(TODAY, 11, 44)), risk=rs)
    assert not v.allow and v.reason == "cooldown_after_trade"
    late = at(TODAY, 11, 44).replace(second=59)
    assert not run(gate, gate_ctx(now=late), risk=rs).allow
    assert run(gate, gate_ctx(now=at(TODAY, 11, 45)), risk=rs).allow  # exact boundary


def test_cooldown_without_close_or_ts_passes(settings):
    gate = RiskBudgetGate(settings)
    assert run(gate, gate_ctx(), risk=RiskState(settings)).allow  # never closed
    rs = RiskState(settings)
    rs.record_close(1.0, "X")             # legacy call, no ts: no anchor set
    assert rs.last_close_ts is None
    assert run(gate, gate_ctx(), risk=rs).allow


def test_cooldown_resets_on_new_day(settings):
    rs = RiskState(settings)
    rs.record_close(1.0, "X", ts=at(TODAY, 11, 30))
    rs.reset_day()
    assert rs.last_close_ts is None
    assert run(RiskBudgetGate(settings), gate_ctx(now=at(TODAY, 11, 31)),
               risk=rs).allow


# --- GateChain ---

def test_chain_returns_first_failure(settings):
    chain = GateChain(settings)
    ctx = gate_ctx(now=at(TODAY, 10, 0), template="UNCLASSIFIED")
    v = chain.check(ctx, Direction.LONG, None, "MARKDOWN",
                    RiskState(settings, locked=True))
    assert not v.allow and v.gate == "time_window"
    ctx2 = gate_ctx(template="UNCLASSIFIED")  # time OK -> template fails next
    v2 = chain.check(ctx2, Direction.LONG, None, "MARKDOWN", RiskState(settings))
    assert not v2.allow and v2.gate == "template"


def test_chain_all_pass(settings):
    ctx = gate_ctx()  # 11:30, calm candles, classified template
    v = GateChain(settings).check(ctx, Direction.LONG,
                                  (Decimal("99"), Decimal("101")), "RANGING",
                                  RiskState(settings))
    assert v.allow and v.reason
