"""Tests for the swings detector (trader/detectors/swings.py).

Design recap (task-3 brief + binding decisions):
- name = "swings"; params {"strength": 3, "timeframes": ["5m", "15m"]}.
- For each configured tf, look at the last (2*strength+1) CLOSED candles.
  The middle candle is a confirmed swing high iff its high is strictly
  greater than every other high in the window (both sides) -- a tie (>=)
  anywhere disqualifies it. Swing lows mirror this on lows.
- On confirmation, append a Level to ctx.levels (SWING_H/SWING_L), zone =
  (extreme - 1 tick, extreme + 1 tick), tf = the Timeframe, id =
  f"{symbol}-{kind.name}-{tf.value}-{ts.isoformat()}".
- Dedupe: same id already present -> skip; any existing SWING level of the
  same kind+tf whose zone overlaps this zone -> skip.
- detect() always returns [] (infrastructure detector; its output is
  levels, not Evidence).
- No-lookahead: a swing at window-index k is only creatable once k+strength
  candles have closed -- this falls out of CandleView only exposing closed
  candles, so the level must be absent from ctx.levels before then.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from trader.detectors.swings import SwingsDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import TICK, Candle, Timeframe, tick
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
D = datetime(2026, 7, 15, tzinfo=IST)
SESSION_START = D.replace(hour=9, minute=15)


def m1(ts, o, h, l, c, v=100):
    return Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(l), tick(c), v)


def add_bar(store, tf, bar_index, o, h, l, c):
    """Add all M1 candles constituting tf's bar_index'th bucket, each with
    OHLC = (o, h, l, c) so the aggregate open=o (first M1), close=c (last
    M1), high=max=h, low=min=l -- an exact tf-level bar under CandleStore's
    real M1-aggregation, without needing a public non-M1 add path."""
    bucket_start = SESSION_START + timedelta(minutes=bar_index * tf.minutes)
    for i in range(tf.minutes):
        store.add(m1(bucket_start + timedelta(minutes=i), o, h, l, c))


def ctx_at(store, now, levels=None):
    view = store.view("X", now)
    return StockContext(
        symbol="X", now=now, candles=view, levels=levels if levels is not None else [],
        evidence_history=[], day=DayState(session_date=now.date()),
    )


def bar_close(tf, bar_index):
    return SESSION_START + timedelta(minutes=(bar_index + 1) * tf.minutes)


# Highs strictly peak at index 3 (the middle of a 7-wide window); lows flat.
HIGHS_PEAK_AT_3 = [100, 101, 102, 110, 103, 102, 101]
BASE_LOW, BASE_CLOSE, BASE_OPEN = 90, 95, 95


def bars_with_high_peak(peak_index=3, highs=None):
    highs = highs or HIGHS_PEAK_AT_3
    return [(BASE_OPEN, h, BASE_LOW, BASE_CLOSE) for h in highs]


def test_detect_always_returns_empty_evidence_list():
    det = SwingsDetector({"strength": 3, "timeframes": ["5m"]})
    store = CandleStore("/nonexistent")
    bars = bars_with_high_peak()
    for i, (o, h, l, c) in enumerate(bars):
        add_bar(store, Timeframe.M5, i, o, h, l, c)
    now = bar_close(Timeframe.M5, 6)
    ctx = ctx_at(store, now)
    result = det.detect(ctx)
    assert result == []
    # sanity: it still did its side-channel job of writing a level
    assert any(lv.kind is LevelKind.SWING_H for lv in ctx.levels)


def test_swing_high_not_confirmed_before_window_closes_no_lookahead():
    det = SwingsDetector({"strength": 3, "timeframes": ["5m"]})
    store = CandleStore("/nonexistent")
    bars = bars_with_high_peak()

    # Add bars one at a time (0..5): only 6 closed bars exist, window needs
    # 7 -- the swing at index 3 must NOT appear yet at any intermediate step.
    for i in range(6):
        o, h, l, c = bars[i]
        add_bar(store, Timeframe.M5, i, o, h, l, c)
        now = bar_close(Timeframe.M5, i)
        ctx = ctx_at(store, now)
        det.detect(ctx)
        assert ctx.levels == [], f"swing must not exist after only {i + 1} bars"

    # Now the 7th bar (index 6) closes -> window [0..6] complete, index 3
    # confirmed as strict max.
    o, h, l, c = bars[6]
    add_bar(store, Timeframe.M5, 6, o, h, l, c)
    now = bar_close(Timeframe.M5, 6)
    ctx = ctx_at(store, now)
    det.detect(ctx)
    assert len(ctx.levels) == 1
    [level] = ctx.levels
    assert level.kind is LevelKind.SWING_H
    assert level.tf is Timeframe.M5
    expected_ts = SESSION_START + timedelta(minutes=3 * Timeframe.M5.minutes)
    assert level.born == expected_ts
    extreme = tick(110)
    assert level.zone == (extreme - TICK, extreme + TICK)
    assert level.id == f"X-SWING_H-5m-{expected_ts.isoformat()}"


def test_tie_disqualifies_swing_high():
    det = SwingsDetector({"strength": 3, "timeframes": ["5m"]})
    store = CandleStore("/nonexistent")
    # Neighbor at index 4 ties the middle's high of 110 -> disqualified.
    highs = [100, 101, 102, 110, 110, 102, 101]
    bars = bars_with_high_peak(highs=highs)
    for i, (o, h, l, c) in enumerate(bars):
        add_bar(store, Timeframe.M5, i, o, h, l, c)
    now = bar_close(Timeframe.M5, 6)
    ctx = ctx_at(store, now)
    det.detect(ctx)
    assert not any(lv.kind is LevelKind.SWING_H for lv in ctx.levels)


def test_tie_disqualifies_swing_low():
    det = SwingsDetector({"strength": 3, "timeframes": ["5m"]})
    store = CandleStore("/nonexistent")
    # Lows dip at index 3 but index 2 ties it -> disqualified.
    lows = [50, 40, 30, 30, 35, 40, 45]
    bars = [(60, 70, l, 60) for l in lows]
    for i, (o, h, l, c) in enumerate(bars):
        add_bar(store, Timeframe.M5, i, o, h, l, c)
    now = bar_close(Timeframe.M5, 6)
    ctx = ctx_at(store, now)
    det.detect(ctx)
    assert not any(lv.kind is LevelKind.SWING_L for lv in ctx.levels)


def test_swing_low_confirmed_when_strict_min():
    det = SwingsDetector({"strength": 3, "timeframes": ["5m"]})
    store = CandleStore("/nonexistent")
    lows = [50, 40, 35, 20, 35, 40, 45]  # strict min at index 3
    bars = [(60, 70, l, 60) for l in lows]
    for i, (o, h, l, c) in enumerate(bars):
        add_bar(store, Timeframe.M5, i, o, h, l, c)
    now = bar_close(Timeframe.M5, 6)
    ctx = ctx_at(store, now)
    det.detect(ctx)
    [level] = ctx.levels
    assert level.kind is LevelKind.SWING_L
    extreme = tick(20)
    assert level.zone == (extreme - TICK, extreme + TICK)


def test_both_high_and_low_confirmed_on_outside_bar():
    det = SwingsDetector({"strength": 3, "timeframes": ["5m"]})
    store = CandleStore("/nonexistent")
    # Middle bar (index 3) has both the highest high and the lowest low.
    bars = [
        (95, 100, 90, 95),
        (95, 101, 89, 95),
        (95, 102, 88, 95),
        (95, 115, 70, 95),   # outside bar: extreme high AND extreme low
        (95, 102, 88, 95),
        (95, 101, 89, 95),
        (95, 100, 90, 95),
    ]
    for i, (o, h, l, c) in enumerate(bars):
        add_bar(store, Timeframe.M5, i, o, h, l, c)
    now = bar_close(Timeframe.M5, 6)
    ctx = ctx_at(store, now)
    det.detect(ctx)
    kinds = {lv.kind for lv in ctx.levels}
    assert kinds == {LevelKind.SWING_H, LevelKind.SWING_L}
    assert len(ctx.levels) == 2


def test_rerunning_detect_does_not_duplicate_level():
    det = SwingsDetector({"strength": 3, "timeframes": ["5m"]})
    store = CandleStore("/nonexistent")
    bars = bars_with_high_peak()
    for i, (o, h, l, c) in enumerate(bars):
        add_bar(store, Timeframe.M5, i, o, h, l, c)
    now = bar_close(Timeframe.M5, 6)
    ctx = ctx_at(store, now)
    det.detect(ctx)
    det.detect(ctx)  # same ctx, same window -- must not add a second level
    assert len(ctx.levels) == 1


def test_dedupe_against_existing_overlapping_zone_different_id():
    det = SwingsDetector({"strength": 3, "timeframes": ["5m"]})
    store = CandleStore("/nonexistent")
    bars = bars_with_high_peak()
    for i, (o, h, l, c) in enumerate(bars):
        add_bar(store, Timeframe.M5, i, o, h, l, c)
    now = bar_close(Timeframe.M5, 6)

    extreme = tick(110)
    existing = Level(
        id="X-SWING_H-5m-PRE_EXISTING",
        symbol="X", kind=LevelKind.SWING_H,
        zone=(extreme - TICK, extreme + TICK),
        born=now, tf=Timeframe.M5, state=LevelState.ACTIVE,
    )
    ctx = ctx_at(store, now, levels=[existing])
    det.detect(ctx)
    assert len(ctx.levels) == 1  # no new level appended; overlap skipped
    assert ctx.levels[0] is existing


def test_multi_timeframe_param_respected_m15():
    det = SwingsDetector({"strength": 3, "timeframes": ["15m"]})
    store = CandleStore("/nonexistent")
    bars = bars_with_high_peak()
    for i, (o, h, l, c) in enumerate(bars):
        add_bar(store, Timeframe.M15, i, o, h, l, c)
    now = bar_close(Timeframe.M15, 6)
    ctx = ctx_at(store, now)
    det.detect(ctx)
    [level] = ctx.levels
    assert level.tf is Timeframe.M15
    expected_ts = SESSION_START + timedelta(minutes=3 * Timeframe.M15.minutes)
    assert level.born == expected_ts
    assert level.id == f"X-SWING_H-15m-{expected_ts.isoformat()}"


def test_both_configured_timeframes_scanned_independently():
    # Default-shaped params: both 5m and 15m configured. Feed a confirmable
    # swing high on 5m only; 15m has no data (too few closed 15m candles at
    # this "now") so it must simply be skipped, not raise.
    det = SwingsDetector({"strength": 3, "timeframes": ["5m", "15m"]})
    store = CandleStore("/nonexistent")
    bars = bars_with_high_peak()
    for i, (o, h, l, c) in enumerate(bars):
        add_bar(store, Timeframe.M5, i, o, h, l, c)
    now = bar_close(Timeframe.M5, 6)
    ctx = ctx_at(store, now)
    det.detect(ctx)
    assert len(ctx.levels) == 1
    assert ctx.levels[0].tf is Timeframe.M5
