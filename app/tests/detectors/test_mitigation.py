"""Tests for the mitigation detector (trader/detectors/mitigation.py).
Binding design: v2-task6 brief (faithful port of ict_pieces.py::
mitigation_block) -- BODY-only zone (min(O,C), max(O,C)) of the last
opposite-color candle immediately before a qualifying displacement leg (no
intervening opposite candle across the lookback window); first return-touch
after the lookback window closed fires the signal. Pure signal-emitter, no
Levels.

Fixture geometry: one M1 candle per M5 bucket start -> the derived M5 bar
equals it exactly. Every candle before the touch bar keeps range==2 and
open == previous close, so ATR(M5,14) == 2 exactly once 15 candles have
closed and stays 2 through block formation (need = disp_atr(1.0) * 2 = 2)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from trader.detectors.mitigation import MitigationDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M1, M5 = Timeframe.M1, Timeframe.M5

FLAT = (100, 101, 99, 100)  # doji, TR=2, primes ATR(M5,14) == 2

# --- LONG fixture: bearish block candle then a qualifying up-displacement ---
BLOCK_L = (100, "100.5", "98.5", 99)     # bearish, body/zone (99, 100)
SEG_L1 = (99, "100.5", "98.5", 100)      # bullish, diff +1
SEG_L2 = (100, "101.5", "99.5", 101)     # bullish, diff +2
SEG_L3 = (101, "102.5", "100.5", 102)    # bullish, diff +3 (max disp)
TOUCH_L = (102, "102.5", 97, 98)         # dips through zone (99,100); low=97 < block low 98.5

# --- SHORT mirror: bullish block candle then a qualifying down-displacement ---
BLOCK_S = (100, "101.5", "99.5", 101)    # bullish, body/zone (100, 101)
SEG_S1 = (101, "101.5", "99.5", 100)     # bearish, diff -1
SEG_S2 = (100, "100.5", "98.5", 99)      # bearish, diff -2
SEG_S3 = (99, "99.5", "97.5", 98)        # bearish, diff -3 (max disp)
TOUCH_S = (98, "103.5", "97.5", 103)     # spans through zone (100,101); high=103.5 > block high 101.5

# --- intervening opposite candle: SEG_L2 replaced by a down-candle -> no block ever ---
SEG_BAD = (100, "100.5", "98.5", 99)     # down candle inside the LONG lookback window

# --- displacement below threshold: max diff 1.5 < need 2 -> no block ---
SEG_T1 = (99, "100.5", "98.5", "99.5")
SEG_T2 = ("99.5", "100.5", "98.5", 100)
SEG_T3 = (100, "101.5", "99.5", "100.5")


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def bar(i, o, h, l, c, v=10):
    return Candle("X", M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_store(bars):
    store = CandleStore("/nonexistent")
    for i, b in enumerate(bars):
        store.add(bar(i, *b))
    return store


def ctx_at(store, n_bars):
    now = bar_ts(n_bars)
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


def long_bars(seg2=SEG_L2):
    return [FLAT] * 15 + [BLOCK_L, SEG_L1, seg2, SEG_L3, TOUCH_L]


def short_bars():
    return [FLAT] * 15 + [BLOCK_S, SEG_S1, SEG_S2, SEG_S3, TOUCH_S]


def test_long_block_body_retest_correct_sl():
    store = make_store(long_bars())
    det = MitigationDetector({})
    assert det.detect(ctx_at(store, 19)) == []  # block forms here (clean ATR=2), no touch yet
    [ev] = det.detect(ctx_at(store, 20))
    assert ev.detector == "mitigation"
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick(99), tick(100))
    assert ev.meta["event"] == "MITIGATION"
    assert ev.meta["sl"] == tick(97)  # min(block.low=98.5, touch.low=97)
    assert ev.ttl_candles == 6
    assert ev.strength == 0.5  # (disp=3 - need=2) / need=2, clamped [0,1]


def test_short_block_mirror():
    store = make_store(short_bars())
    det = MitigationDetector({})
    assert det.detect(ctx_at(store, 19)) == []  # block forms here (clean ATR=2), no touch yet
    [ev] = det.detect(ctx_at(store, 20))
    assert ev.direction is Direction.SHORT
    assert ev.zone == (tick(100), tick(101))
    assert ev.meta["sl"] == tick("103.5")  # max(block.high=101.5, touch.high=103.5)
    assert ev.strength == 0.5


def test_intervening_opposite_candle_blocks_formation():
    store = make_store(long_bars(seg2=SEG_BAD))
    det = MitigationDetector({})
    assert det.detect(ctx_at(store, 19)) == []
    assert det.detect(ctx_at(store, 20)) == []  # touch bar closed, still no block ever formed


def test_displacement_below_threshold_no_block():
    bars = [FLAT] * 15 + [BLOCK_L, SEG_T1, SEG_T2, SEG_T3, TOUCH_L]
    store = make_store(bars)
    det = MitigationDetector({})
    assert det.detect(ctx_at(store, 19)) == []
    assert det.detect(ctx_at(store, 20)) == []


def test_no_lookahead():
    store = make_store(long_bars())
    det = MitigationDetector({})
    for n in (16, 17, 18, 19):  # lookback window (+ block confirm) not fully closed / no touch yet
        assert det.detect(ctx_at(store, n)) == []
    [ev] = det.detect(ctx_at(store, 20))  # touch bar now closed
    assert ev.direction is Direction.LONG


def test_dedupe_one_fire_per_block():
    store = make_store(long_bars())
    det = MitigationDetector({})
    [ev] = det.detect(ctx_at(store, 20))
    assert det.detect(ctx_at(store, 20)) == []  # same tick again: no duplicate


def test_on_session_end_clears_state():
    store = make_store(long_bars())
    det = MitigationDetector({})
    det.detect(ctx_at(store, 20))
    det.on_session_end()
    [ev] = det.detect(ctx_at(store, 20))  # re-forms and re-fires after reset
    assert ev.direction is Direction.LONG
    assert ev.meta["sl"] == tick(97)
