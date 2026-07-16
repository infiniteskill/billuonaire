"""Tests for the timestats detector (trader/detectors/timestats.py).
Binding design: task-8 brief (bucket math, NSE prior table, Laplace blend,
save/load, dedupe)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.timestats import (
    TimestatsDetector, bucket_count, bucket_index, nse_prior,
)
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.market import NSE, MarketSpec
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5
CRYPTO = MarketSpec(session_open="00:00", session_close="24:00")


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def add_bar(store, i, o, h, l, c):
    """Add 5 M1 candles that aggregate to exactly (o, h, l, c) for bar i."""
    ts0 = bar_ts(i)
    store.add(Candle("X", Timeframe.M1, ts0, o, o, o, o, 10))
    store.add(Candle("X", Timeframe.M1, ts0 + timedelta(minutes=1), o, h, o, o, 10))
    store.add(Candle("X", Timeframe.M1, ts0 + timedelta(minutes=2), o, o, l, o, 10))
    store.add(Candle("X", Timeframe.M1, ts0 + timedelta(minutes=3), o, o, o, o, 10))
    store.add(Candle("X", Timeframe.M1, ts0 + timedelta(minutes=4), o, max(o, c), min(o, c), c, 10))


def make_ctx(n_bars, store=None):
    store = store or CandleStore("/nonexistent")
    for i in range(n_bars):
        add_bar(store, i, tick(100), tick(101), tick(99), tick(100))
    now = bar_ts(n_bars)
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


def empty_ctx(now):
    store = CandleStore("/nonexistent")
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


# ---- bucket math ----

def test_bucket_count_nse_is_75():
    assert bucket_count(NSE, 5) == 75


def test_bucket_count_crypto_24h_is_288():
    assert bucket_count(CRYPTO, 5) == 288


def test_bucket_index_from_minutes_elapsed():
    now = SESSION_START + timedelta(minutes=37)
    assert bucket_index(now, NSE, 5) == 7  # 37 // 5


# ---- NSE prior table (exact at boundaries) ----

@pytest.mark.parametrize("minutes,expected", [
    (74, 0.8), (75, 0.5), (105, 0.3), (225, 0.6), (285, 0.8),
])
def test_nse_prior_table_boundaries(minutes, expected):
    assert nse_prior(minutes) == expected


def test_non_nse_session_flat_half_prior():
    det = TimestatsDetector({})
    for bucket in (0, 20, 100, 280):
        assert det.prior(bucket, CRYPTO) == 0.5


def test_nse_session_prior_uses_table():
    det = TimestatsDetector({})
    assert det.prior(21, NSE) == 0.3  # bucket 21 * 5min = 105 -> 0.3


# ---- danger blend arithmetic ----

def test_danger_blend_exact_arithmetic():
    det = TimestatsDetector({"prior_weight": 20})
    det._counts["X"] = {21: (10, 10)}  # bucket 21 -> NSE prior 0.3
    assert det.danger("X", 21, NSE) == pytest.approx((0.3 * 20 + 10) / (20 + 10))


def test_danger_cold_start_equals_prior():
    det = TimestatsDetector({"prior_weight": 20})
    assert det.danger("X", 21, NSE) == pytest.approx(0.3)


def test_record_accumulates_counts():
    det = TimestatsDetector({})
    det.record("X", 5, swept=True)
    det.record("X", 5, swept=False)
    assert det._counts["X"][5] == (1, 2)


def test_record_is_per_symbol():
    det = TimestatsDetector({})
    det.record("A", 5, swept=True)
    det.record("B", 5, swept=False)
    assert det._counts["A"][5] == (1, 1)
    assert det._counts["B"][5] == (0, 1)


# ---- evidence ----

def test_evidence_neutral_strength_inverts_danger():
    det = TimestatsDetector({})
    ctx = make_ctx(3)
    [ev] = det.detect(ctx)
    bucket = bucket_index(ctx.now, ctx.spec, det.params["bucket_min"])
    expected_danger = det.danger(ctx.symbol, bucket, ctx.spec)
    assert ev.detector == "timestats"
    assert ev.direction is Direction.NEUTRAL
    assert ev.strength == pytest.approx(1 - expected_danger)
    assert ev.ttl_candles == 1
    assert ev.meta == {"bucket": bucket, "danger": expected_danger, "event": "TIME"}


def test_evidence_zone_is_latest_closed_candle():
    det = TimestatsDetector({})
    ctx = make_ctx(3)
    [ev] = det.detect(ctx)
    assert ev.zone == (tick(99), tick(101))


def test_no_candles_emits_no_evidence():
    det = TimestatsDetector({})
    ctx = empty_ctx(SESSION_START + timedelta(minutes=10))
    assert det.detect(ctx) == []


def test_dedupe_same_candle_silent_second_call():
    det = TimestatsDetector({})
    ctx = make_ctx(3)
    assert len(det.detect(ctx)) == 1
    assert det.detect(ctx) == []


def test_new_candle_fires_again():
    det = TimestatsDetector({})
    store = CandleStore("/nonexistent")
    ctx1 = make_ctx(3, store=store)
    assert len(det.detect(ctx1)) == 1
    ctx2 = make_ctx(4, store=store)
    assert len(det.detect(ctx2)) == 1


# ---- save / load ----

def test_save_load_roundtrip(tmp_path):
    det = TimestatsDetector({"path": str(tmp_path)})
    det.record("X", 3, swept=True)
    det.record("X", 3, swept=False)
    det.record("X", 10, swept=True)
    det.save("X")

    loaded = TimestatsDetector({"path": str(tmp_path)})
    loaded.load("X")
    assert loaded._counts == det._counts
    assert (tmp_path / "timestats-X.json").exists()


def test_load_other_symbol_does_not_clobber(tmp_path):
    # Regression: save/load are per-symbol, so loading B must not wipe A's
    # already-loaded counts on the same instance.
    a = TimestatsDetector({"path": str(tmp_path)})
    a.record("A", 3, swept=True)
    a.save("A")

    b = TimestatsDetector({"path": str(tmp_path)})
    b.record("B", 7, swept=False)
    b.save("B")

    det = TimestatsDetector({"path": str(tmp_path)})
    det.load("A")
    det.load("B")
    assert det._counts["A"][3] == (1, 1)
    assert det._counts["B"][7] == (0, 1)


def test_no_path_skips_disk_io(tmp_path):
    det = TimestatsDetector({"path": None})
    det.record("X", 3, swept=True)
    det.save("X")
    assert list(tmp_path.iterdir()) == []


def test_load_missing_file_is_noop(tmp_path):
    det = TimestatsDetector({"path": str(tmp_path)})
    det.load("X")  # no file yet
    assert det._counts == {}
