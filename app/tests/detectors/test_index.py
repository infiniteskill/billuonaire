"""Tests for the index-context detector (trader/detectors/index.py).
Binding design: task-9 brief (requires-gated, NEUTRAL-direction context
evidence, dedupe per candle ts)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.config import Settings
from trader.detectors.base import DetectorRegistry
from trader.detectors.index import IndexDetector
from trader.engine.context import DayState, IndexView, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5


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


def make_ctx(n_bars, index=None, store=None):
    store = store or CandleStore("/nonexistent")
    for i in range(n_bars):
        add_bar(store, i, tick(100), tick(101), tick(99), tick(100))
    now = bar_ts(n_bars)
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()), index=index)


def make_settings(enabled=("index",)):
    return Settings.model_validate({
        "capital": 100000,
        "risk": {"per_trade_pct": 0.5, "daily_loss_pct": 1.5, "max_trades_day": 3,
                 "max_per_stock": 1, "consecutive_loss_stop": 2, "expiry_size_mult": 0.5},
        "time": {"observe_until": "10:45", "no_entry_after": "14:30", "squareoff": "15:10"},
        "stops": {"atr_buffer": 0.25, "wick_tolerance_candles": 1, "round_offset_ticks": 3},
        "confluence": {"threshold": 65, "weights": {name: 10 for name in enabled}},
        "detectors": {"enabled": list(enabled), "disabled": [], "params": {}},
        "fills": {"slippage_bps": 3, "half_spread_bps": 2,
                  "costs": {"brokerage_flat": 20, "stt_pct": 0.025, "exchange_pct": 0.00297}},
    })


# ---- requires gating (table-driven, registry-level) ----

def test_skipped_by_registry_when_index_none():
    reg = DetectorRegistry(make_settings())
    ctx = make_ctx(3, index=None)
    assert reg.run_all(ctx) == []


def test_runs_via_registry_when_index_present():
    reg = DetectorRegistry(make_settings())
    ctx = make_ctx(3, index=IndexView(trend=Direction.LONG, phase="markup", strength=0.8))
    out = reg.run_all(ctx)
    assert [e.detector for e in out] == ["index"]


# ---- evidence ----

def test_evidence_long_trend_strength_and_meta():
    det = IndexDetector({})
    ctx = make_ctx(3, index=IndexView(trend=Direction.LONG, phase="markup", strength=0.8))
    [ev] = det.detect(ctx)
    assert ev.detector == "index"
    assert ev.direction is Direction.NEUTRAL
    assert ev.strength == pytest.approx(0.4)
    assert ev.ttl_candles == 1
    assert ev.meta == {"trend": "LONG", "phase": "markup", "event": "INDEX"}


def test_evidence_zone_is_latest_closed_candle():
    det = IndexDetector({})
    ctx = make_ctx(3, index=IndexView(trend=Direction.SHORT, phase="markdown", strength=0.6))
    [ev] = det.detect(ctx)
    assert ev.zone == (tick(99), tick(101))


def test_no_candles_emits_no_evidence():
    det = IndexDetector({})
    store = CandleStore("/nonexistent")
    now = SESSION_START + timedelta(minutes=10)
    ctx = StockContext(symbol="X", now=now, candles=store.view("X", now),
                       levels=[], evidence_history=[],
                       day=DayState(session_date=now.date()),
                       index=IndexView(trend=Direction.LONG, phase="markup", strength=0.8))
    assert det.detect(ctx) == []


def test_neutral_trend_is_silent():
    det = IndexDetector({})
    ctx = make_ctx(3, index=IndexView(trend=Direction.NEUTRAL, phase="range", strength=0.9))
    assert det.detect(ctx) == []


def test_dedupe_same_candle_silent_second_call():
    det = IndexDetector({})
    ctx = make_ctx(3, index=IndexView(trend=Direction.LONG, phase="markup", strength=0.8))
    assert len(det.detect(ctx)) == 1
    assert det.detect(ctx) == []


def test_new_candle_fires_again():
    det = IndexDetector({})
    store = CandleStore("/nonexistent")
    idx = IndexView(trend=Direction.LONG, phase="markup", strength=0.8)
    ctx1 = make_ctx(3, index=idx, store=store)
    assert len(det.detect(ctx1)) == 1
    ctx2 = make_ctx(4, index=idx, store=store)
    assert len(det.detect(ctx2)) == 1
