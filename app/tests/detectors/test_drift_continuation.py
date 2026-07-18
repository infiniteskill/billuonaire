"""Tests for the drift_continuation detector
(trader/detectors/drift_continuation.py). Binding design: the recall-audit
missed-set profile (runs/long60/RECALL.md Table C): quiet continuation --
>=0.5-ATR 6-bar drift in d, close within 0.65 ATR of the prior 12-bar
extreme, NO >=0.75-ATR adverse leg in the last 6 bars; fresh 12-bar
breakout raises strength. Signal-emitter only, compression_fade meta
contract (sl + sl_floor stringified)."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.drift_continuation import DriftContinuationDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M1, M5 = Timeframe.M1, Timeframe.M5

FILLER = (100, 101, 99, 100)          # TR 2 (ATR priming; ATR=2 on fillers)


def dbar(pc, step):
    """Drift bar: open=prev close, net progress ``step``, 0.2 wicks -- the
    quiet-continuation shape (shallow cross-bar pullbacks of 0.4)."""
    c = round(pc + step, 2)
    return (pc, round(max(pc, c) + 0.2, 2), round(min(pc, c) - 0.2, 2), c)


def drift_run(pc=100, step=0.5, n=6):
    out = []
    for _ in range(n):
        out.append(dbar(pc, step))
        pc = round(pc + step, 2)
    return out


PROFILE = [FILLER] * 15 + drift_run()          # LONG: closes 100.5 .. 103


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def bar(i, o, h, l, c, v=10):
    return Candle("X", M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_store(bars):
    """One M1 candle per M5 bucket start -> the derived M5 bar equals it."""
    from trader.store.candles import CandleStore
    store = CandleStore("/nonexistent")
    for i, b in enumerate(bars):
        store.add(bar(i, *b))
    return store


def ctx_at(store, n_bars):
    now = bar_ts(n_bars)  # first n_bars M5 bars are closed
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


def expected_strength(drift, atr, fresh):
    return min(1.0, min(0.75, (drift / float(atr) - 0.5) / 2)
               + (0.25 if fresh else 0.0))


def test_fires_on_profile_case_long():
    """The missed-run profile: 3.0 drift over 6 bars, fresh 12-bar breakout,
    shallow (0.4) pullbacks only -> one LONG with the full meta contract."""
    store = make_store(PROFILE)
    ctx = ctx_at(store, 21)
    atr = ctx.atr(M5)
    [ev] = DriftContinuationDetector({}).detect(ctx)
    assert ev.detector == "drift_continuation"
    assert ev.direction is Direction.LONG
    assert ev.ttl_candles == 3
    # sl = 6-bar adverse extreme (min low of the drift run) = 100.5-0.2-0.5
    assert ev.meta == {"event": "DRIFT_CONT", "sl": str(tick("99.8")),
                       "sl_floor": str(Decimal("0.15") * atr)}
    band = Decimal("0.1") * atr                  # small band at close
    assert ev.zone == (tick(103) - band, tick(103) + band)
    assert ev.strength == pytest.approx(expected_strength(3.0, atr, True))
    assert 0.0 < ev.strength <= 1.0


def test_fires_short_mirror():
    store = make_store([FILLER] * 15 + drift_run(step=-0.5))
    ctx = ctx_at(store, 21)
    [ev] = DriftContinuationDetector({}).detect(ctx)
    assert ev.direction is Direction.SHORT
    assert ev.meta["sl"] == str(tick("100.2"))   # max high of the drift run
    assert ev.strength == pytest.approx(
        expected_strength(3.0, ctx.atr(M5), True))


def test_no_fire_on_deep_pullback_shape():
    """A run start AFTER a >=0.75-ATR flush-and-recover (sweep/pullback
    reversal -- the existing tools' turf): drift and breakout both pass, but
    the 3.3 adverse leg (101.5 high -> 98.2 low) inside the last 6 bars
    blocks it."""
    store = make_store([FILLER] * 15 + [
        (100, "101.5", "99.5", 100),
        (100, 100, "98.2", "98.4"),              # deep flush
        ("98.4", 100, "98.4", "99.9"),           # recovery
        ("99.9", 101, "99.8", "100.9"),
        ("100.9", "101.8", "100.8", "101.7"),
        ("101.7", "102.4", "101.6", "102.3")])   # closes above 12-bar high
    assert DriftContinuationDetector({}).detect(ctx_at(store, 21)) == []


def test_no_fire_far_below_recent_extreme():
    """Same drift, but a 104.5 spike high in the 12-bar lookback leaves the
    close 1.5 (> 0.65 ATR) below the extreme: pullback territory, no fire."""
    bars = list(PROFILE)
    bars[8] = (100, "104.5", 99, 100)
    assert DriftContinuationDetector({}).detect(ctx_at(make_store(bars), 21)) == []


def test_no_fire_below_drift_threshold():
    store = make_store([FILLER] * 15 + drift_run(step=0.1))  # 0.6 < 0.5*ATR
    assert DriftContinuationDetector({}).detect(ctx_at(store, 21)) == []


def test_no_fire_without_atr():
    # 14 closed bars: 13-bar window exists but ATR (needs 15) does not.
    store = make_store([FILLER] * 8 + drift_run())
    ctx = ctx_at(store, 14)
    assert ctx.atr(M5) is None
    assert DriftContinuationDetector({}).detect(ctx) == []


def test_fresh_breakout_bonus_raises_strength():
    """Non-fresh variant: a 103.4 prior high keeps the 103 close inside the
    12-bar range (still within 0.65 ATR) -> no +0.25 bonus."""
    bars = list(PROFILE)
    bars[12] = (100, "103.4", 99, 100)
    store = make_store(bars)
    ctx = ctx_at(store, 21)
    [ev] = DriftContinuationDetector({}).detect(ctx)
    assert ev.strength == pytest.approx(
        expected_strength(3.0, ctx.atr(M5), False))
    store_f = make_store(PROFILE)
    ctx_f = ctx_at(store_f, 21)
    [ev_f] = DriftContinuationDetector({}).detect(ctx_f)
    assert ev_f.strength > ev.strength + 0.2     # bonus dominates ATR drift


def test_no_lookahead_before_ignition_bar_closes():
    """Only the last bar crosses the drift threshold; while it is still
    forming (view at its bucket start) nothing may fire."""
    bars = ([FILLER] * 15 + [(100, "100.6", "99.6", 100)] * 5
            + [(100, "101.4", "99.9", "101.3")])
    store = make_store(bars)
    det = DriftContinuationDetector({})
    assert det.detect(ctx_at(store, 20)) == []   # ignition bar not closed
    [ev] = det.detect(ctx_at(store, 21))
    assert ev.direction is Direction.LONG


def test_dedupe_one_fire_per_closed_bar():
    store = make_store(PROFILE)
    det = DriftContinuationDetector({})
    [_] = det.detect(ctx_at(store, 21))
    assert det.detect(ctx_at(store, 21)) == []   # same tick again: no dup


def test_on_session_end_prunes_dedupe_only():
    store = make_store(PROFILE)
    det = DriftContinuationDetector({})
    [_] = det.detect(ctx_at(store, 21))
    det.on_session_end()
    assert det._emitted == {bar_ts(20)}          # newest ts survives pruning
    assert det.detect(ctx_at(store, 21)) == []   # no re-fire across boundary


def test_registered():
    from trader.detectors.base import REGISTRY
    assert REGISTRY["drift_continuation"] is DriftContinuationDetector
