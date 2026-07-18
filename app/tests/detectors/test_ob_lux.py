"""Tests for the ob_lux detector (trader/detectors/ob_lux.py).
Binding design: v2 task-1 brief (validated LuxAlgo internal Order Block,
ported from the measured-winner scratchpad luxob.py: swing-pivot leg
extreme with an ATR-based volatility-as-volume-proxy adjustment).

Fixture geometry: every bar (flat warmup + custom) keeps TR == 2, so
ATR(M5,14) == 2 exactly at every tick -- no drift between the creation and
retest ticks. size=2 keeps the pivot window short enough for compact
fixtures (default is 5).
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.ob_lux import ObLuxDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)  # NSE open
M5 = Timeframe.M5
FLAT = (100, 101, 99, 100)  # TR == 2 warmup bar


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def make_store(bars):
    store = CandleStore("/nonexistent")
    for i, (o, h, l, c) in enumerate(bars):
        store.add(Candle("X", Timeframe.M1, bar_ts(i),
                         tick(o), tick(h), tick(l), tick(c), 10))
    return store


def ctx_at(store, n_bars, levels):
    now = bar_ts(n_bars)  # first n_bars M5 bars are closed
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=levels, evidence_history=[],
                        day=DayState(session_date=now.date()))


# Bull leg (size=2): pivot high at bar16 (H=102) confirmed once bars 17-18
# fail to exceed it; pullback 17-19, breakout close (103) past 102 confirmed
# at bar22 (overshoot 1 / ATR 2 -> quality 0.5). Every bar TR == 2. The leg
# extreme (lowest low in [16,22]) is bar17 -> zone (99, 101).
BULL_16_21 = [(100, 102, 100, 101), (101, 101, 99, 100), (100, 101, 99, 99),
             (99, 101, 99, 100), (100, 102, 100, 101), (101, 103, 101, 102)]


def bull_bars(c22=103):
    return [FLAT] * 16 + BULL_16_21 + [(102, 104, 102, c22)]


BULL_RETRACE = (103, 103, 101, 101)  # TR == 2, closes at zone hi (101)

# Bear mirror (prices reflected 200-x, H/L swapped): pivot low at bar16
# (L=98), breakout close (97) past 98 confirmed at bar22. Leg extreme is
# bar17 -> zone (99, 101).
BEAR_16_21 = [(100, 100, 98, 99), (99, 101, 99, 100), (100, 101, 99, 101),
             (101, 101, 99, 100), (100, 100, 98, 99), (99, 99, 97, 98)]


def bear_bars(c22=97):
    return [FLAT] * 16 + BEAR_16_21 + [(98, 98, 96, c22)]


BEAR_RETRACE = (97, 99, 97, 99)  # TR == 2, closes at zone lo (99)


def test_bullish_ob_created_and_retest_long():
    store = make_store(bull_bars() + [BULL_RETRACE])
    det, levels = ObLuxDetector({"size": 2}), []
    # confirmation tick: OB born, but its own close (103) is outside the zone
    assert det.detect(ctx_at(store, 23, levels)) == []
    [lv] = levels
    assert lv.kind is LevelKind.OB_BULL
    assert lv.zone == (tick(99), tick(101))
    assert lv.born == bar_ts(17)
    assert lv.tf is M5
    assert lv.state is LevelState.ACTIVE
    [ev] = det.detect(ctx_at(store, 24, levels))  # retrace closes inside zone
    assert ev.detector == "ob_lux"
    assert ev.direction is Direction.LONG
    assert ev.strength == pytest.approx(0.5)
    assert ev.zone == (tick(99), tick(101))
    assert ev.ttl_candles == 6
    assert ev.meta == {"level_id": lv.id, "event": "OB_RETEST"}


def test_bearish_ob_mirror():
    store = make_store(bear_bars() + [BEAR_RETRACE])
    det, levels = ObLuxDetector({"size": 2}), []
    assert det.detect(ctx_at(store, 23, levels)) == []
    [lv] = levels
    assert lv.kind is LevelKind.OB_BEAR
    assert lv.zone == (tick(99), tick(101))
    assert lv.born == bar_ts(17)
    [ev] = det.detect(ctx_at(store, 24, levels))
    assert ev.direction is Direction.SHORT
    assert ev.strength == pytest.approx(0.5)
    assert ev.meta == {"level_id": lv.id, "event": "OB_RETEST"}


def test_no_evidence_before_retest_no_lookahead():
    store = make_store(bull_bars() + [BULL_RETRACE])
    det, levels = ObLuxDetector({"size": 2}), []
    det.detect(ctx_at(store, 23, levels))
    assert len(levels) == 1  # OB exists...
    # ...but bar23 (already sitting in the store) is invisible until its own
    # tf duration closes, and the confirmation candle's own close is outside
    # the zone, so no evidence yet either way.
    assert det.detect(ctx_at(store, 23, levels)) == []
    [ev] = det.detect(ctx_at(store, 24, levels))
    assert ev.direction is Direction.LONG


def test_vol_adjustment_excludes_high_volatility_wick():
    # bar17's raw low (90) would win a plain argmin(low); its range (11.5)
    # trips the hv threshold (2 * ATR = 4) so it is excluded from the
    # leg-extreme search and bar18 (low 99) is picked instead.
    bars = ([FLAT] * 16 + [(100, 102, 100, 101), (101, 101.5, 90, 101),
                           (101, 101, 99, 100), (100, 102, 100, 101),
                           (101, 103, 101, 102), (102, 104, 102, 103)])
    store = make_store(bars)
    levels = []
    ObLuxDetector({"size": 2}).detect(ctx_at(store, 22, levels))
    [lv] = levels
    assert lv.zone == (tick(99), tick(101))  # not (90, 101.5)
    assert lv.born == bar_ts(18)


def test_overlap_keeps_higher_quality_new_wins():
    store = make_store(bull_bars(c22=103.5))  # overshoot 1.5 -> quality 0.75
    rival = Level(id="seed", symbol="X", kind=LevelKind.OB_BULL,
                 zone=(tick(99.5), tick(100.5)), born=bar_ts(5), tf=M5)
    levels = [rival]
    ObLuxDetector({"size": 2}).detect(ctx_at(store, 23, levels))
    [lv] = levels
    assert lv.zone == (tick(99), tick(101))  # replaced the rival (0.75 > 0.5)


def test_overlap_keeps_higher_quality_old_wins():
    store = make_store(bull_bars())  # overshoot 1 -> quality 0.5
    rival = Level(id="seed", symbol="X", kind=LevelKind.OB_BULL,
                 zone=(tick(99.5), tick(100.5)), born=bar_ts(5), tf=M5)
    levels = [rival]
    ObLuxDetector({"size": 2}).detect(ctx_at(store, 23, levels))
    assert levels == [rival]  # 0.5 <= rival's default 0.5: new OB discarded


def test_on_session_end_persists_structural_memory():
    # Continuum: _quality/_anchor describe levels/legs that carry across
    # days -- they persist; _emitted is pruned to the newest bar's entries
    # (that bar is still the latest close across the boundary).
    store = make_store(bull_bars() + [BULL_RETRACE])
    det, levels = ObLuxDetector({"size": 2}), []
    det.detect(ctx_at(store, 23, levels))
    [ev] = det.detect(ctx_at(store, 24, levels))
    quality, anchor = dict(det._quality), dict(det._anchor)
    assert quality and anchor and det._emitted
    det.on_session_end()
    assert det._quality == quality and det._anchor == anchor
    assert det._emitted == {(ev.meta["level_id"], bar_ts(23))}
    assert det.detect(ctx_at(store, 24, levels)) == []  # dedupe survived


def test_continuum_leg_spans_session_boundary():
    """CONTINUUM (validated): the bull leg's pivot/pullback close out day 1;
    the confirming breakout close and the retrace are day 2's first two
    candles. luxob.py::lux_ob_events ran one long multi-day series, so the
    swing structure carries: the OB is born at day 1's leg-extreme bar and
    day 2's retrace fires the LONG retest."""
    day1_bars = [FLAT] * 16 + BULL_16_21            # pivot @16, leg through 21
    day2 = SESSION_START + timedelta(days=1)
    store = make_store(day1_bars)
    for i, (o, h, l, c) in enumerate([(102, 104, 102, 103), BULL_RETRACE]):
        store.add(Candle("X", Timeframe.M1, day2 + timedelta(minutes=5 * i),
                         tick(o), tick(h), tick(l), tick(c), 10))

    det, levels = ObLuxDetector({"size": 2}), []
    det.on_session_end()                            # boundary hook: keeps structure
    now = day2 + timedelta(minutes=5)
    assert det.detect(StockContext(symbol="X", now=now, candles=store.view("X", now),
                                   levels=levels, evidence_history=[],
                                   day=DayState(session_date=now.date()))) == []
    [lv] = levels                                   # confirmed by day-2's first close
    assert lv.kind is LevelKind.OB_BULL
    assert lv.zone == (tick(99), tick(101))
    assert lv.born == bar_ts(17)                    # day-1 leg-extreme bar
    now2 = day2 + timedelta(minutes=10)
    [ev] = det.detect(StockContext(symbol="X", now=now2, candles=store.view("X", now2),
                                   levels=levels, evidence_history=[],
                                   day=DayState(session_date=now2.date())))
    assert ev.direction is Direction.LONG
    assert ev.strength == pytest.approx(0.5)


def test_no_evidence_for_terminal_state_level():
    store = make_store(bull_bars() + [BULL_RETRACE])
    det, levels = ObLuxDetector({"size": 2}), []
    det.detect(ctx_at(store, 23, levels))
    [lv] = levels
    lv.record_state(bar_ts(23), LevelState.MITIGATED)  # terminal: dead for entries
    assert det.detect(ctx_at(store, 24, levels)) == []  # retest inside zone, but no evidence


def test_restart_preserves_tested_level_no_eviction():
    # Session 1 (or pre-restart): the OB is born at bar17 (bar17's range is
    # plain, TR == 2) and gets tested -- real state/history now on the level.
    persisted = ObLuxDetector({"size": 2})
    levels = []
    persisted.detect(ctx_at(make_store(bull_bars()), 23, levels))
    [old] = levels
    assert old.born == bar_ts(17)
    old.record_state(bar_ts(20), LevelState.TESTED)

    # Restart: a brand new instance (no memoized anchor) rescans. Here bar17
    # is a high-volatility wick (excluded from the leg-extreme search, as in
    # test_vol_adjustment_excludes_high_volatility_wick) -- standing in for
    # an ATR-drifted re-classification -- so the anchor now resolves to
    # bar18 instead of bar17: a DIFFERENT level_id for the same zone.
    bars = ([FLAT] * 16 + [(100, 102, 100, 101), (101, 101.5, 90, 101),
                           (101, 101, 99, 100), (100, 102, 100, 101),
                           (101, 103, 101, 102), (102, 104, 102, 103)])
    fresh = ObLuxDetector({"size": 2})
    fresh.detect(ctx_at(make_store(bars), 22, levels))

    # The persisted TESTED level must survive untouched, not be evicted.
    assert old in levels and old.state is LevelState.TESTED
    assert old.zone == (tick(99), tick(101)) and old.born == bar_ts(17)
    # The anchor-mismatched OB is added alongside it (fresh ACTIVE dup),
    # never silently swapped in for the stateful one.
    assert len(levels) == 2
    [new] = [lv for lv in levels if lv is not old]
    assert new.state is LevelState.ACTIVE
    assert new.zone == (tick(99), tick(101)) and new.born == bar_ts(18)
