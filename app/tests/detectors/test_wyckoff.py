"""Tests for the Wyckoff detector (trader/detectors/wyckoff.py).
Binding design: task-6 brief (spring/upthrust events, phase classifier)."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from zoneinfo import ZoneInfo

from trader.detectors.wyckoff import WyckoffDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M1 = Timeframe.M1
PARAMS = {"tf": "5m", "window": 40, "range_atr": 3.0, "vol_sma": 20}


def bar_ts(i):  # one M1 per 5m bucket -> one 5m candle per bucket
    return SESSION_START + timedelta(minutes=5 * i)


def bar(i, o, h, l, c, v):
    return Candle("X", M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_ctx(candles):
    store = CandleStore("/nonexistent")
    for cd in candles:
        store.add(cd)
    now = candles[-1].ts + timedelta(minutes=5)
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


# 40 flat range candles: band = 101 - 99 = 2, TR = 2 -> ATR = 2; in-range
# (2 < 3*2). Range lo = 99, hi = 101. Vol SMA = 100.
def _range40():
    return [bar(i, 100, 101, 99, 100, 100) for i in range(40)]


# spring spike: low 96 < lo 99; mid = 96 + 4.5/2 = 98.25, close 100 in upper
# half; vol 200 > 1.5*100.
SPRING = dict(o=100, h="100.5", l=96, c=100, v=200)
# upthrust spike: high 104 > hi 101; mid = 99.5 + 4.5/2 = 101.75, close 100
# in lower half; vol 200.
UPTHRUST = dict(o=100, h=104, l="99.5", c=100, v=200)


def _spiked(spec):
    return _range40() + [bar(40, spec["o"], spec["h"], spec["l"], spec["c"], spec["v"])]


# 40 trending candles: close 100 + 0.15*i, h/l = close +/- 1 -> TR = 2,
# ATR = 2; band = 106.85 - 99 = 7.85 >= 6 -> out of range. Net close change
# = 39*0.15 = 5.85 > ATR -> MARKUP, confidence 5.85/6 = 0.975.
def _trend40(sign=1):
    return [bar(i, 100 + sign * Decimal("0.15") * i,
                101 + sign * Decimal("0.15") * i,
                99 + sign * Decimal("0.15") * i,
                100 + sign * Decimal("0.15") * i, 100) for i in range(40)]


# ---- spring / upthrust events ----

def test_spring_fires_exact():
    ctx = make_ctx(_spiked(SPRING))

    [ev] = WyckoffDetector(PARAMS).detect(ctx)

    assert ev.detector == "wyckoff"
    assert ev.direction is Direction.LONG
    assert ev.strength == 0.8
    assert ev.zone == (tick("98.95"), tick("99.05"))  # lo 99 +/- 1 tick
    assert ev.ttl_candles == 24
    assert ev.meta == {"event": "SPRING"}


def test_upthrust_fires_mirror():
    ctx = make_ctx(_spiked(UPTHRUST))

    [ev] = WyckoffDetector(PARAMS).detect(ctx)

    assert ev.direction is Direction.SHORT
    assert ev.strength == 0.8
    assert ev.zone == (tick("100.95"), tick("101.05"))  # hi 101 +/- 1 tick
    assert ev.meta == {"event": "UPTHRUST"}


def test_no_spring_when_volume_low():
    ctx = make_ctx(_spiked({**SPRING, "v": 100}))  # vol not > 1.5*SMA

    assert WyckoffDetector(PARAMS).detect(ctx) == []


def test_no_spring_when_close_in_lower_half():
    # low 96 < lo, vol fine, but close 96.5 < mid 96.75
    ctx = make_ctx(_spiked(dict(o=97, h="97.5", l=96, c="96.5", v=200)))

    assert WyckoffDetector(PARAMS).detect(ctx) == []


def test_no_spring_when_not_in_range():
    # steeper trend (step 0.2): band = 108.8 - 99 = 9.8, spike TR 12.8 ->
    # ATR = (13*2 + 12.8)/14 = 2.771, band_max = 8.31 < 9.8 -> out of range;
    # spike below with high volume must NOT fire a spring
    candles = [bar(i, 100 + Decimal("0.2") * i, 101 + Decimal("0.2") * i,
                   99 + Decimal("0.2") * i, 100 + Decimal("0.2") * i, 100)
               for i in range(40)]
    candles.append(bar(40, "107.8", "108.8", 96, "108.5", 200))
    ctx = make_ctx(candles)

    out = WyckoffDetector(PARAMS).detect(ctx)

    assert all(e.meta["event"] != "SPRING" for e in out)


def test_dedupe_same_candle():
    ctx = make_ctx(_spiked(SPRING))
    det = WyckoffDetector(PARAMS)

    assert len(det.detect(ctx)) == 1
    assert det.detect(ctx) == []


# ---- phase() ----

def test_phase_unclear_cold_start():
    ctx = make_ctx(_range40()[:5])

    assert WyckoffDetector(PARAMS).phase(ctx) == ("UNCLEAR", 0.0)


def test_phase_unclear_in_range_without_event():
    ctx = make_ctx(_range40())

    assert WyckoffDetector(PARAMS).phase(ctx) == ("UNCLEAR", 0.4)


def test_phase_accumulation_after_spring():
    ctx = make_ctx(_spiked(SPRING))
    det = WyckoffDetector(PARAMS)
    det.detect(ctx)

    assert det.phase(ctx) == ("ACCUMULATION", 0.7)


def test_phase_distribution_after_upthrust():
    ctx = make_ctx(_spiked(UPTHRUST))
    det = WyckoffDetector(PARAMS)
    det.detect(ctx)

    assert det.phase(ctx) == ("DISTRIBUTION", 0.7)


def test_phase_markup_with_confidence_math():
    ctx = make_ctx(_trend40())

    name, conf = WyckoffDetector(PARAMS).phase(ctx)

    assert name == "MARKUP"
    assert conf == pytest.approx(0.975)  # 5.85 / (3 * ATR 2)


def test_phase_markdown_mirror():
    ctx = make_ctx(_trend40(sign=-1))

    name, conf = WyckoffDetector(PARAMS).phase(ctx)

    assert name == "MARKDOWN"
    assert conf == pytest.approx(0.975)


# ---- continuation evidence ----

def test_continuation_evidence_in_markup_and_dedupe():
    ctx = make_ctx(_trend40())
    det = WyckoffDetector(PARAMS)

    [ev] = det.detect(ctx)

    latest = ctx.candles.last(1, Timeframe.M5)[-1]
    assert ev.direction is Direction.LONG
    assert ev.strength == 0.5
    assert ev.ttl_candles == 12
    assert ev.zone == (latest.low, latest.high)
    assert ev.meta == {"event": "PHASE", "phase": "MARKUP"}
    assert det.detect(ctx) == []  # dedupe per candle


# ---- htf_phase() over D1 ----

def _d1_ctx(n_days, step):
    store = CandleStore("/nonexistent")
    day0 = datetime(2026, 6, 1, 9, 15, tzinfo=IST)
    for d in range(n_days):
        px = tick(100 + step * d)
        store.add(Candle("X", M1, day0 + timedelta(days=d), px, px, px, px, 100))
    now = day0 + timedelta(days=n_days - 1, hours=7)  # after last session close
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


def test_htf_phase_markdown_on_drifting_down_d1():
    ctx = _d1_ctx(10, Decimal("-1"))  # closes 100 -> 91: -9% < -2%

    name, conf = WyckoffDetector(PARAMS).htf_phase(ctx)

    assert name == "MARKDOWN"
    assert conf == 1.0  # min(1, 9/5)


def test_htf_phase_unclear_below_ten_d1():
    ctx = _d1_ctx(9, Decimal("-1"))

    assert WyckoffDetector(PARAMS).htf_phase(ctx) == ("UNCLEAR", 0.0)
