"""Incremental-scan guarantee for ob_lux / fvg_cb (the perf contract behind
the parity gates): a warm tick consumes only NEWLY-closed bars -- cursor +
per-bar call-count assertions, deliberately NOT wall-clock (flake-free).
A cold call (fresh instance) still replays the whole history exactly once."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from trader.detectors.fvg_cb import FvgCbDetector
from trader.detectors.ob_lux import ObLuxDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5
FLAT = (100, 101, 99, 100)  # TR == 2 every bar: ATR defined, no gaps/pivots


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def add_bar(store, i):
    o, h, l, c = FLAT
    store.add(Candle("X", Timeframe.M1, bar_ts(i),
                     tick(o), tick(h), tick(l), tick(c), 10))


def store_with(n):
    store = CandleStore("/nonexistent")
    for i in range(n):
        add_bar(store, i)
    return store


def ctx_at(store, n_bars, levels):
    now = bar_ts(n_bars)  # first n_bars M5 bars are closed
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=levels, evidence_history=[],
                        day=DayState(session_date=now.date()))


def test_ob_lux_warm_tick_steps_only_new_bars(monkeypatch):
    store, levels = store_with(30), []
    det = ObLuxDetector({})
    det.detect(ctx_at(store, 30, levels))
    assert det._n == 30                          # cold call consumed all 30 once
    stepped, orig = [], det._step
    monkeypatch.setattr(det, "_step",
                        lambda ctx, tf, w, i: (stepped.append(i), orig(ctx, tf, w, i))[1])
    add_bar(store, 30)
    det.detect(ctx_at(store, 31, levels))
    assert stepped == [30] and det._n == 31      # warm tick: exactly the ONE new bar
    det.detect(ctx_at(store, 31, levels))
    assert stepped == [30]                       # same-tick re-detect: zero steps


def test_fvg_cb_warm_tick_folds_only_new_bars(monkeypatch):
    store, levels = store_with(30), []
    det = FvgCbDetector({})
    det.detect(ctx_at(store, 30, levels))
    assert det._n == 30                          # cold call folded all history once
    folded, orig = [], FvgCbDetector._pct
    monkeypatch.setattr(det, "_pct", lambda c: (folded.append(c.ts), orig(c))[1])
    add_bar(store, 30)
    rsum = det._rsum
    det.detect(ctx_at(store, 31, levels))
    assert folded == [bar_ts(30)] and det._n == 31   # warm tick: ONE new bar folded
    assert det._rsum == rsum + orig(store.view("X", bar_ts(31)).last(1, M5)[0])
    det.detect(ctx_at(store, 31, levels))
    assert folded == [bar_ts(30)]                # same-tick re-detect: zero folds
