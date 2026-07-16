"""Phase-4 Task 3: EntryFSM -- stealth stops, opposing-map targets, triggers.

Fixture geometry: calm() candles have range 2 => ATR(14) = 2 exactly, so
buffer = 0.25*ATR = 0.50, chase tol = 0.1*ATR = 0.20, max stop = 1.2*ATR = 2.4.
LONG zone (98, 100) => entry CE 99.00. capital 100000 x 0.5% => budget 500.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.config import Settings
from trader.engine.confluence import ScoredZone
from trader.engine.context import DayState, StockContext
from trader.engine.entry import EntryFSM, EntryState
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
CONFIG = Path(__file__).resolve().parents[2] / "config" / "config.json"
TODAY = datetime(2026, 7, 15, tzinfo=IST)
D = Decimal
SWEPT = [(TODAY, LevelState.SWEPT)]


@pytest.fixture
def fsm():
    settings = Settings.model_validate_json(CONFIG.read_text())
    return EntryFSM(settings, settings.market_spec())


def at(hh, mm):
    return TODAY.replace(hour=hh, minute=mm)


def m1(ts, o=100, h=101, lo=99, c=100):
    return Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(lo), tick(c), 100)


def calm(n=15):  # one M1 per M5 bucket, range 2 => ATR(14) = 2
    return [m1(at(9, 15) + timedelta(minutes=5 * i)) for i in range(n)]


def ctx_at(now, candles, levels, history=()):
    store = CandleStore("/nonexistent")
    for c in candles:
        store.add(c)
    return StockContext("X", now, store.view("X", now), list(levels),
                        list(history), DayState(session_date=now.date()))


def lvl(kind, lo, hi, state=LevelState.ACTIVE, hist=()):
    return Level(f"{kind.name}-{lo}", "X", kind, (D(lo), D(hi)), TODAY,
                 Timeframe.M5, state=state, state_history=list(hist))


def zone(lo, hi, dirn=Direction.LONG, final=72.5):
    return ScoredZone((D(lo), D(hi)), dirn, [], 3, 40.0, final,
                      {"align": 1.0, "time": 0.9})


def t_lvl():  # T1 source: 101.50 is 2.50 away >= 1.5R for risk 1.50
    return lvl(LevelKind.SWING_H, "101.50", "102.00")


# --- arm(): stop construction + qty ---

def test_arm_plain_far_edge_buffer_and_qty_floor(fsm):
    r = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), [t_lvl()]), 1000)
    assert r.armed and r.reason is None and fsm.state is EntryState.ARMED
    p = r.plan
    assert p.stop == D("97.50")                     # far edge 98 - 0.25*ATR
    assert p.meta["risk_pts"] == "1.50"
    assert p.qty == 333                             # floor(500 / 1.50)
    assert p.symbol == "X" and p.direction is Direction.LONG
    assert p.score == 72.5 and p.meta["mults"] == {"align": 1.0, "time": 0.9}


def test_arm_sweep_trap_round_snap_targets_decimal(fsm):
    levels = [lvl(LevelKind.SWING_L, "97.40", "98.50", LevelState.SWEPT, SWEPT),
              lvl(LevelKind.ROUND, "96.85", "96.85"),
              lvl(LevelKind.SWING_H, "100.50", "101.00"),   # < 1.5R: not T1
              lvl(LevelKind.SWING_H, "102.40", "102.80"),
              lvl(LevelKind.SWING_H, "104.00", "104.50"),
              lvl(LevelKind.PDH, "106.00", "106.10")]
    p = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), levels), 1000).plan
    # trap extreme 97.40 - 0.50 buffer = 96.90; within 2 ticks of round 96.85
    # => shifted away 3 ticks; risk 99.00 - 96.75 = 2.25
    assert p.stop == D("96.75")
    assert p.targets == [D("102.40"), D("104.00"), D("106.00")]
    assert p.qty == 222                             # floor(500 / 2.25)
    assert all(isinstance(x, Decimal) and x % D("0.05") == 0
               for x in [p.stop, *p.targets, *p.entry_zone])


def test_arm_stop_too_wide_skips(fsm):
    r = fsm.arm(zone("94.00", "100.00"), ctx_at(at(11, 0), calm(), []), 1000)
    assert (r.armed, r.reason, r.plan) == (False, "stop_too_wide", None)
    assert fsm.state is EntryState.IDLE


def test_arm_no_room_skips(fsm):  # only opposing level is < 1.5R away
    ctx = ctx_at(at(11, 0), calm(), [lvl(LevelKind.SWING_H, "100.50", "101.00")])
    r = fsm.arm(zone("98.00", "100.00"), ctx, 1000)
    assert (r.armed, r.reason) == (False, "no_room")


def test_arm_qty_zero_skips(fsm):
    r = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), [t_lvl()]), 0)
    assert (r.armed, r.reason) == (False, "qty_zero")


# --- targets ---

def test_t2_t3_fallback_prices(fsm):  # single level beyond: 2.5R / 4R fallbacks
    p = fsm.arm(zone("98.00", "100.00"), ctx_at(at(11, 0), calm(), [t_lvl()]), 1000).plan
    assert p.targets == [D("101.50"), D("102.75"), D("105.00")]


def test_t3_capped_by_compression_energy(fsm):
    hist = [Evidence("compression", Direction.LONG, 0.75, (D("98.50"), D("99.50")),
                     at(10, 0), 24, meta={"event": "PO3_DIST", "energy": "4.50"})]
    ctx = ctx_at(at(11, 0), calm(), [t_lvl()], history=hist)
    p = fsm.arm(zone("98.00", "100.00"), ctx, 1000).plan
    assert p.targets[2] == D("103.50")              # min(4R=105, entry + 4.50)


def test_opposing_scored_zone_supplies_t1(fsm):
    ctx = ctx_at(at(11, 0), calm(), [lvl(LevelKind.SWING_H, "100.50", "101.00")])
    opp = zone("102.60", "103.00", Direction.SHORT)
    p = fsm.arm(zone("98.00", "100.00"), ctx, 1000, opps=[opp]).plan
    assert p.targets == [D("102.60"), D("102.75"), D("105.00")]


def test_short_direction_stop_and_t1_boundary(fsm):  # T1 at exactly 1.5R counts
    ctx = ctx_at(at(11, 0), calm(), [lvl(LevelKind.SWING_L, "98.00", "98.75")])
    p = fsm.arm(zone("100.00", "102.00", Direction.SHORT), ctx, 1000).plan
    assert p.stop == D("102.50")                    # far edge 102 + 0.50 buffer
    assert p.targets == [D("98.75"), D("97.25"), D("95.00")]


# --- step(): triggers + disarms ---

def armed(fsm, extra_levels=()):
    levels = [t_lvl(), *extra_levels]
    assert fsm.arm(zone("98.00", "100.00"), ctx_at(at(10, 31), calm(), levels), 1000).armed
    return levels


def step_ctx(trigger=None, now=at(10, 36), levels=()):
    return ctx_at(now, calm() + ([trigger] if trigger else []), levels)


@pytest.mark.parametrize("o,filled", [(99.2, True),    # lower wick 1.2 = 60% exactly
                                      (99.1, False)])  # 55% + no evidence: hold
def test_trigger_rejection_wick_boundary(fsm, o, filled):
    levels = armed(fsm)
    r = fsm.step(step_ctx(m1(at(10, 30), o=o, h=100.0, lo=98.0, c=99.9), levels=levels))
    assert (r.action == "fill") is filled
    if filled:
        assert r.plan.qty == 333 and fsm.state is EntryState.IDLE
    else:
        assert r.action == "hold" and fsm.state is EntryState.ARMED


@pytest.mark.parametrize("det,event", [("structure", "CHOCH"), ("volume", "VSA")])
def test_trigger_on_confirmation_evidence(fsm, det, event):
    levels = armed(fsm)
    ev = Evidence(det, Direction.LONG, 0.7, (D("98"), D("100")), at(10, 30), 6,
                  meta={"event": event})
    c = m1(at(10, 30), o=99.1, h=100.0, lo=98.0, c=99.9)  # wick 55%: needs evidence
    assert fsm.step(step_ctx(c, levels=levels), [ev]).action == "fill"


def test_disarm_chased_close_beyond_far_edge(fsm):
    levels = armed(fsm)
    c = m1(at(10, 30), o=99.0, h=99.2, lo=97.5, c=97.7)   # close < 98 - 0.1*ATR
    r = fsm.step(step_ctx(c, levels=levels))
    assert (r.action, r.reason) == ("disarm", "chased") and fsm.state is EntryState.IDLE


def test_disarm_expired_after_ttl(fsm):
    levels = armed(fsm)
    assert fsm.step(step_ctx(now=at(11, 31), levels=levels)).action == "hold"  # age 12
    r = fsm.step(step_ctx(now=at(11, 36), levels=levels))                      # age 13
    assert (r.action, r.reason) == ("disarm", "expired")


def test_disarm_zone_broken_on_dead_ob(fsm):
    ob = lvl(LevelKind.OB_BULL, "98.20", "99.00", LevelState.DEAD)
    levels = armed(fsm)
    r = fsm.step(step_ctx(levels=[*levels, ob]))
    assert (r.action, r.reason) == ("disarm", "zone_broken")


def test_step_when_idle_holds(fsm):
    assert fsm.step(step_ctx(levels=[])).action == "hold"
