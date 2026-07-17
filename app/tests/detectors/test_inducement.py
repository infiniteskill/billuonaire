"""Tests for the inducement detector (trader/detectors/inducement.py).

Fixtures use ln=4, short_len=2 (not the ln=20 production default) so a
CHoCH-then-sweep sequence fits in a manageable number of bars; the state
machine is length-parametric so this exercises the exact same code paths.

LONG_BARS: a down-up-down-up wiggle confirms a long-swing top (=103 via
ln=4), a rally closes above it (CHoCH bullish, bar 14), then a short-swing
low (=93 via short_len=2) forms and gets swept underneath on the final bar
(16th, exactly filling the ln*4=16 window -> no truncation) -> one bullish
INDUCEMENT_GRAB. SHORT_BARS is its exact mirror (price' = 200 - price),
producing the bearish counterpart. NO_CHOCH_BARS shares LONG_BARS' first 13
bars (close never crosses the long-swing top) with a shifted-down tail that
never approaches it -- the CHoCH gate (os_==1) never opens, so no grab
fires.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from trader.detectors.inducement import InducementDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import TICK, Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
PARAMS = {"tf": "5m", "ln": 4, "short_len": 2}  # window = ln*4 = 16

LONG_BARS = [
    (98, 100, 92, 98), (99, 101, 93, 99), (100, 102, 94, 100), (101, 103, 95, 101),
    (101, 103, 95, 101), (100, 102, 94, 100), (99, 101, 93, 99), (98, 100, 92, 98),
    (99, 101, 93, 99), (100, 102, 94, 100), (101, 103, 95, 101), (100, 102, 94, 100),
    (99, 101, 93, 99), (102, 104, 96, 102), (105, 107, 99, 105), (106, 108, 91, 106),
]  # bar 14 (0-idx): CHoCH bullish; bar 15: sweeps short-swing low 93 -> grab

SHORT_BARS = [
    (102, 108, 100, 102), (101, 107, 99, 101), (100, 106, 98, 100), (99, 105, 97, 99),
    (99, 105, 97, 99), (100, 106, 98, 100), (101, 107, 99, 101), (102, 108, 100, 102),
    (101, 107, 99, 101), (100, 106, 98, 100), (99, 105, 97, 99), (100, 106, 98, 100),
    (101, 107, 99, 101), (98, 104, 96, 98), (95, 101, 93, 95), (94, 109, 92, 94),
]  # mirror of LONG_BARS (price' = 200 - price): bearish CHoCH then a swept
   # short-swing high (107) -> grab

NO_CHOCH_BARS = LONG_BARS[:13] + [
    (82, 84, 76, 82), (85, 87, 79, 85), (86, 88, 71, 86),
]  # close never exceeds the long-swing top (103): no CHoCH, no grab


def m1(ts, o, h, l, c, v=100):
    return Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(l), tick(c), v)


def add_bar(store, tf, bar_index, o, h, l, c):
    bucket_start = SESSION_START + timedelta(minutes=bar_index * tf.minutes)
    for i in range(tf.minutes):
        store.add(m1(bucket_start + timedelta(minutes=i), o, h, l, c))


def bar_close(tf, bar_index):
    return SESSION_START + timedelta(minutes=(bar_index + 1) * tf.minutes)


def ctx_at(store, now):
    return StockContext(symbol="X", now=now, candles=store.view("X", now), levels=[],
                        evidence_history=[], day=DayState(session_date=now.date()))


def load(bars, upto=None):
    store = CandleStore("/nonexistent")
    for i, (o, h, l, c) in enumerate(bars[:upto]):
        add_bar(store, Timeframe.M5, i, o, h, l, c)
    n = upto if upto is not None else len(bars)
    return store, ctx_at(store, bar_close(Timeframe.M5, n - 1))


def test_no_grab_without_preceding_choch():
    store, ctx = load(NO_CHOCH_BARS)
    assert InducementDetector(PARAMS).detect(ctx) == []


def test_choch_then_sweep_fires_long_grab():
    store, ctx = load(LONG_BARS)
    [ev] = InducementDetector(PARAMS).detect(ctx)
    assert ev.detector == "inducement"
    assert ev.direction is Direction.LONG
    assert 0 < ev.strength <= 1
    assert ev.ttl_candles == 3
    extreme = tick(93)
    assert ev.zone == (extreme - TICK, extreme + TICK)
    assert ev.meta == {"event": "INDUCEMENT_GRAB", "sl": extreme - TICK, "os": 1}


def test_choch_then_sweep_fires_short_grab_mirror():
    store, ctx = load(SHORT_BARS)
    [ev] = InducementDetector(PARAMS).detect(ctx)
    assert ev.direction is Direction.SHORT
    extreme = tick(107)
    assert ev.zone == (extreme - TICK, extreme + TICK)
    assert ev.meta == {"event": "INDUCEMENT_GRAB", "sl": extreme + TICK, "os": 0}


def test_no_lookahead_fractal_confirmation_delay():
    det = InducementDetector(PARAMS)
    store = CandleStore("/nonexistent")
    for i, (o, h, l, c) in enumerate(LONG_BARS):
        add_bar(store, Timeframe.M5, i, o, h, l, c)
        ctx = ctx_at(store, bar_close(Timeframe.M5, i))
        result = det.detect(ctx)
        if i < len(LONG_BARS) - 1:
            assert result == [], f"grab must not fire before bar {len(LONG_BARS) - 1} closes"
    assert len(result) == 1
    assert result[0].meta["event"] == "INDUCEMENT_GRAB"


def test_dedupe_fires_once_for_same_event():
    store, ctx = load(LONG_BARS)
    det = InducementDetector(PARAMS)
    assert len(det.detect(ctx)) == 1
    assert det.detect(ctx) == []  # same ctx, same closed bar: no re-fire


def test_on_session_end_resets_dedupe():
    store, ctx = load(LONG_BARS)
    det = InducementDetector(PARAMS)
    assert len(det.detect(ctx)) == 1
    det.on_session_end()
    assert len(det.detect(ctx)) == 1  # memory cleared: fires again


def test_insufficient_history_returns_empty():
    store, ctx = load(LONG_BARS, upto=3)
    assert InducementDetector(PARAMS).detect(ctx) == []


def test_default_params():
    det = InducementDetector({})
    assert det.params == {"tf": "5m", "ln": 20, "short_len": 3}
