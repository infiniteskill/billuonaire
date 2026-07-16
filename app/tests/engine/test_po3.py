"""Tests for the PO3 FSM (trader/engine/po3.py).
Binding design: task-7 brief / dev/plan/06 SS3 (ACC -> MANIP -> DIST)."""

from datetime import datetime, timedelta
from decimal import Decimal

from zoneinfo import ZoneInfo

from trader.engine.po3 import PO3FSM
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction

IST = ZoneInfo("Asia/Kolkata")
T0 = datetime(2026, 7, 15, 10, 0, tzinfo=IST)
ATR = Decimal("1")


def bar(i, o, h, l, c):
    return Candle("X", Timeframe.M5, T0 + timedelta(minutes=5 * i),
                  tick(o), tick(h), tick(l), tick(c), 100)


def _armed():
    fsm = PO3FSM(None, {})
    fsm.set_box(tick(100), tick(102), T0)
    return fsm


def test_set_box_enters_accumulation():
    fsm = PO3FSM(None, {})
    assert fsm.state == "IDLE"

    assert fsm.set_box(tick(100), tick(102), T0) == "ACCUMULATION"

    assert fsm.state == "ACCUMULATION"
    assert fsm.box == (tick(100), tick(102))
    assert fsm.swept_side is None and fsm.true_direction is None


def test_happy_path_low_sweep_displacement_up_bos_gives_long():
    fsm = _armed()

    # inside candle: no transition
    assert fsm.step(bar(0, 101, "101.5", "100.5", 101), ATR, False) is None
    # sweep: wick below lo 100, close back inside
    assert fsm.step(bar(1, "100.5", "100.8", 99, "100.6"), ATR, False) == "MANIPULATION"
    assert fsm.swept_side == "low"
    assert fsm.sweep_extreme == tick(99)
    # drift candle, not displaced
    assert fsm.step(bar(2, "100.6", "101.2", "100.4", 101), ATR, True) is None
    # displacement: close 102.8 >= mid 101 + 1.5*ATR, BOS present
    assert fsm.step(bar(3, 101, 103, "100.9", "102.8"), ATR, True) == "DISTRIBUTION"
    assert fsm.state == "DISTRIBUTION"
    assert fsm.true_direction is Direction.LONG


def test_high_sweep_displacement_down_gives_short():
    fsm = _armed()

    assert fsm.step(bar(0, "101.5", 103, "101.2", "101.4"), ATR, False) == "MANIPULATION"
    assert fsm.swept_side == "high"
    assert fsm.sweep_extreme == tick(103)
    # close 99.4 <= mid 101 - 1.5*ATR
    assert fsm.step(bar(1, 101, "101.2", 99, "99.4"), ATR, True) == "DISTRIBUTION"
    assert fsm.true_direction is Direction.SHORT


def test_no_distribution_without_bos_flag():
    fsm = _armed()
    fsm.step(bar(0, "100.5", "100.8", 99, "100.6"), ATR, False)  # -> MANIPULATION

    pullback = bar(2, "101.8", 102, "100.9", "101.5")  # close back inside
    assert fsm.step(bar(1, 101, 103, "100.9", "102.8"), ATR, False) is None  # no BOS
    assert fsm.state == "MANIPULATION"
    assert fsm.step(pullback, ATR, True) is None
    assert fsm.step(bar(3, 101, 103, "100.9", "102.8"), None, True) is None  # no ATR
    assert fsm.step(pullback, ATR, True) is None
    assert fsm.step(bar(4, 101, 103, "100.9", "102.8"), ATR, True) == "DISTRIBUTION"


def test_trend_handoff_two_closes_beyond_no_reclaim():
    fsm = _armed()

    assert fsm.step(bar(0, 102, "102.6", "101.8", "102.5"), ATR, False) is None
    assert fsm.step(bar(1, "102.5", "103.2", "102.2", 103), ATR, False) == "IDLE"
    assert fsm.state == "IDLE"
    assert fsm.reason == "trend"
    # IDLE is inert until a new box
    assert fsm.step(bar(2, 103, 104, "102.8", "103.5"), ATR, True) is None


def test_close_back_inside_resets_handoff_streak():
    fsm = _armed()

    assert fsm.step(bar(0, 102, "102.6", "101.8", "102.5"), ATR, False) is None
    # closes back inside without wick beyond: streak broken, still ACCUMULATION
    assert fsm.step(bar(1, "101.9", 102, 101, "101.5"), ATR, False) is None
    assert fsm.state == "ACCUMULATION"
    assert fsm.step(bar(2, "101.5", "102.8", "101.4", "102.5"), ATR, False) is None
    assert fsm.state == "ACCUMULATION"


def test_distribution_terminal_until_new_box():
    fsm = _armed()
    fsm.step(bar(0, "100.5", "100.8", 99, "100.6"), ATR, False)
    fsm.step(bar(1, 101, 103, "100.9", "102.8"), ATR, True)
    assert fsm.state == "DISTRIBUTION"

    assert fsm.step(bar(2, 103, 105, "102.9", "104.8"), ATR, True) is None
    assert fsm.state == "DISTRIBUTION"

    assert fsm.set_box(tick(104), tick(105), T0 + timedelta(minutes=15)) == "ACCUMULATION"
    assert fsm.swept_side is None and fsm.true_direction is None
    assert fsm.box == (tick(104), tick(105))
