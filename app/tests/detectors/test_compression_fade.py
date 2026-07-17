"""Tests for the compression_fade detector (trader/detectors/compression_fade.py).
Binding design: v2-task3 brief (port of rr.py::compress_fade) — FADE the coil
breakout: a break of the compression candle's high => SHORT (sl = break
high); a break of its low => LONG (sl = break low). Signal-emitter only, no
Levels."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.compression_fade import CompressionFadeDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M1, M5 = Timeframe.M1, Timeframe.M5

COMPRESS = (100, 105, 95, 100)     # doji, range 10: body 0<=3.5, wicks 5>=2 each
INSIDE = (100, 102, 99, 102)       # non-compress (body/range=0.67), no break
FILLER = (100, 101, 99, "100.8")   # non-compress, TR=2 (ATR priming filler)
UP_BREAK = (106, 107, 106, "106.5")    # high 107 > 105 -> SHORT, sl=107
DOWN_BREAK = (94, "94.5", 93, "93.5")  # low 93 < 95 -> LONG, sl=93
NOT_COMPRESS = (100, 101, 99, "100.8")  # body 0.8/range 2 = 0.4 > 0.35


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def bar(i, o, h, l, c, v=10):
    return Candle("X", M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_store(bars):
    """One M1 candle per M5 bucket start -> the derived M5 bar equals it."""
    store = CandleStore("/nonexistent")
    for i, b in enumerate(bars):
        store.add(bar(i, *b))
    return store


def ctx_at(store, n_bars):
    now = bar_ts(n_bars)  # first n_bars M5 bars are closed
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


def test_up_break_emits_short_with_sl_at_break_high():
    store = make_store([COMPRESS, UP_BREAK])
    [ev] = CompressionFadeDetector({}).detect(ctx_at(store, 2))
    assert ev.detector == "compression_fade"
    assert ev.direction is Direction.SHORT
    assert ev.meta["sl"] == tick(107)
    assert ev.meta["entry"] == tick("106.5")
    assert ev.meta["event"] == "COMPRESSION_FADE"
    assert ev.zone == (tick("106.5"), tick(107))
    assert ev.ttl_candles == 2
    assert 0.0 <= ev.strength <= 1.0


def test_down_break_emits_long_with_sl_at_break_low():
    store = make_store([COMPRESS, DOWN_BREAK])
    [ev] = CompressionFadeDetector({}).detect(ctx_at(store, 2))
    assert ev.direction is Direction.LONG
    assert ev.meta["sl"] == tick(93)
    assert ev.meta["entry"] == tick("93.5")
    assert ev.zone == (tick(93), tick("93.5"))


def test_non_compression_candle_no_signal():
    store = make_store([NOT_COMPRESS, UP_BREAK])
    assert CompressionFadeDetector({}).detect(ctx_at(store, 2)) == []


def test_break_beyond_window_no_signal():
    # inside x3 then a 4th-bar break: outside the default break_window=3
    store = make_store([COMPRESS, INSIDE, INSIDE, INSIDE, UP_BREAK])
    det = CompressionFadeDetector({})
    for n in range(2, 5):
        assert det.detect(ctx_at(store, n)) == []
    assert det.detect(ctx_at(store, 5)) == []


def test_break_within_window_fires_on_third_bar():
    store = make_store([COMPRESS, INSIDE, INSIDE, UP_BREAK])
    det = CompressionFadeDetector({})
    assert det.detect(ctx_at(store, 2)) == []
    assert det.detect(ctx_at(store, 3)) == []
    [ev] = det.detect(ctx_at(store, 4))
    assert ev.direction is Direction.SHORT


def test_sl_floor_annotated_when_atr_available():
    store = make_store([FILLER] * 15 + [COMPRESS, UP_BREAK])
    ctx = ctx_at(store, 17)
    atr = ctx.atr(M5)
    [ev] = CompressionFadeDetector({}).detect(ctx)
    assert atr is not None
    assert ev.meta["sl_floor"] == Decimal("0.15") * atr


def test_no_lookahead_before_break_bar_closes():
    store = make_store([COMPRESS, UP_BREAK])
    assert CompressionFadeDetector({}).detect(ctx_at(store, 1)) == []  # only COMPRESS closed


def test_dedupe_one_fire_per_compression():
    store = make_store([COMPRESS, UP_BREAK])
    det = CompressionFadeDetector({})
    [ev] = det.detect(ctx_at(store, 2))
    assert det.detect(ctx_at(store, 2)) == []  # same tick again: no duplicate


def test_on_session_end_clears_dedupe():
    store = make_store([COMPRESS, UP_BREAK])
    det = CompressionFadeDetector({})
    det.detect(ctx_at(store, 2))
    det.on_session_end()
    # re-running the same compression/break pair fires again after reset
    [ev] = det.detect(ctx_at(store, 2))
    assert ev.direction is Direction.SHORT


def test_session_boundary_no_cross_day_fade():
    """COMPRESS is day 1's last candle; UP_BREAK is day 2's first candle and
    breaks COMPRESS's high. The old ctx.candles.last(bw+1, tf) window would
    span the session boundary and mix them into a false SHORT fade on day
    2's very first tick. Session-scoped ctx.candles.today(tf) excludes
    COMPRESS on day 2, so the detector correctly emits nothing until it has
    its own intraday compression candle."""
    day1 = SESSION_START
    day2 = day1 + timedelta(days=1)
    store = CandleStore("/nonexistent")
    store.add(Candle("X", M1, day1, *(tick(x) for x in COMPRESS), 10))
    store.add(Candle("X", M1, day2, *(tick(x) for x in UP_BREAK), 10))

    det = CompressionFadeDetector({})
    now = day2 + timedelta(minutes=M5.minutes)
    ctx = StockContext(symbol="X", now=now, candles=store.view("X", now),
                       levels=[], evidence_history=[],
                       day=DayState(session_date=now.date()))
    assert det.detect(ctx) == []            # no cross-session fade

    # a genuine day-2-only COMPRESS + break DOES fire, from day-2 candles only
    store.add(Candle("X", M1, day2 + timedelta(minutes=5), *(tick(x) for x in COMPRESS), 10))
    store.add(Candle("X", M1, day2 + timedelta(minutes=10), *(tick(x) for x in DOWN_BREAK), 10))
    now2 = day2 + timedelta(minutes=15)
    ctx2 = StockContext(symbol="X", now=now2, candles=store.view("X", now2),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now2.date()))
    [ev] = det.detect(ctx2)
    assert ev.direction is Direction.LONG
    assert ev.meta["sl"] == tick(93)
