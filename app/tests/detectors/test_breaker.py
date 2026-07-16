"""Tests for the breaker detector (trader/detectors/breaker.py).
Binding design: task-3 brief (INVERTED retest, direction flip, episode dedupe)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.breaker import BreakerDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5
ZONE = (tick(100), tick(101))


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def add_bar(store, i, o, h, l, c):
    """Add 5 M1 candles that aggregate to exactly (o, h, l, c) for bar i.
    Caller must ensure h >= max(o, c) and l <= min(o, c)."""
    ts0 = bar_ts(i)
    store.add(Candle("X", Timeframe.M1, ts0, o, o, o, o, 10))
    store.add(Candle("X", Timeframe.M1, ts0 + timedelta(minutes=1), o, h, o, o, 10))
    store.add(Candle("X", Timeframe.M1, ts0 + timedelta(minutes=2), o, o, l, o, 10))
    store.add(Candle("X", Timeframe.M1, ts0 + timedelta(minutes=3), o, o, o, o, 10))
    store.add(Candle("X", Timeframe.M1, ts0 + timedelta(minutes=4), o, max(o, c), min(o, c), c, 10))


def make_ctx(n_bars, retest_ohlc, levels, store=None):
    """n_bars closed M5 bars; bars 0..n_bars-2 flat @105, latest bar is
    retest_ohlc = (o, h, l, c)."""
    store = store or CandleStore("/nonexistent")
    for i in range(n_bars - 1):
        add_bar(store, i, tick(105), tick(105), tick(105), tick(105))
    add_bar(store, n_bars - 1, *retest_ohlc)
    now = bar_ts(n_bars)
    return StockContext(
        symbol="X", now=now, candles=store.view("X", now),
        levels=levels, evidence_history=[], day=DayState(session_date=now.date()),
    )


def inverted_level(kind, inv_ts, zone=ZONE):
    lv = Level(id=f"X-{kind.name}-1", symbol="X", kind=kind, zone=zone,
               born=SESSION_START, tf=None)
    lv.record_state(inv_ts - timedelta(minutes=5), LevelState.RECLAIMED)
    lv.record_state(inv_ts, LevelState.INVERTED)
    return lv


# a candle rallying up into the zone from below and closing back below it
_RETEST_FROM_BELOW = (tick(99), tick("100.5"), tick(98), tick(99))
# a candle dipping into the zone from above and closing back above it
_RETEST_FROM_ABOVE = (tick("100.5"), tick(102), tick("99.5"), tick(102))
# a candle overlapping the zone but closing INSIDE it
_RETEST_INSIDE = (tick(99), tick("100.7"), tick(98), tick("100.5"))


def test_inverted_swing_l_retest_fires_short():
    lv = inverted_level(LevelKind.SWING_L, bar_ts(2))
    ctx = make_ctx(6, _RETEST_FROM_BELOW, [lv])
    [ev] = BreakerDetector({}).detect(ctx)
    assert ev.detector == "breaker"
    assert ev.direction is Direction.SHORT
    assert ev.strength == pytest.approx(0.85)
    assert ev.ttl_candles == 12
    assert ev.zone == lv.zone
    assert ev.meta == {"level_id": lv.id, "event": "BREAKER_RETEST"}


def test_inverted_ob_bear_retest_fires_long():
    lv = inverted_level(LevelKind.OB_BEAR, bar_ts(2))
    ctx = make_ctx(6, _RETEST_FROM_ABOVE, [lv])
    [ev] = BreakerDetector({}).detect(ctx)
    assert ev.direction is Direction.LONG
    assert ev.strength == pytest.approx(0.85)


def test_close_inside_zone_no_evidence():
    lv = inverted_level(LevelKind.SWING_L, bar_ts(2))
    ctx = make_ctx(6, _RETEST_INSIDE, [lv])
    assert BreakerDetector({}).detect(ctx) == []


def test_non_inverted_state_no_evidence():
    lv = inverted_level(LevelKind.SWING_L, bar_ts(2))
    lv.state = LevelState.RECLAIMED  # not INVERTED, even though history has it
    ctx = make_ctx(6, _RETEST_FROM_BELOW, [lv])
    assert BreakerDetector({}).detect(ctx) == []


def test_episode_dedupe_second_retest_candle_silent():
    det = BreakerDetector({})
    lv = inverted_level(LevelKind.SWING_L, bar_ts(2))
    ctx = make_ctx(6, _RETEST_FROM_BELOW, [lv])
    assert len(det.detect(ctx)) == 1
    ctx2 = make_ctx(7, _RETEST_FROM_BELOW, [lv])
    assert det.detect(ctx2) == []


def test_re_inversion_new_episode_fires_again():
    det = BreakerDetector({})
    lv = inverted_level(LevelKind.SWING_L, bar_ts(2))
    ctx1 = make_ctx(6, _RETEST_FROM_BELOW, [lv])
    assert len(det.detect(ctx1)) == 1

    lv.record_state(bar_ts(9), LevelState.INVERTED)  # simulated re-inversion
    ctx2 = make_ctx(11, _RETEST_FROM_BELOW, [lv])
    assert len(det.detect(ctx2)) == 1
