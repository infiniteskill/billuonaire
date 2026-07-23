"""Tests for the htf_nest detector (trader/detectors/htf_nest.py)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from trader.detectors.base import REGISTRY
from trader.detectors.htf_nest import HtfNestDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Timeframe, tick
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 7, 15, 12, 0, tzinfo=IST)


def zone(kind, lo, hi, tf, state=LevelState.ACTIVE, zid=None):
    return Level(id=zid or f"{kind.name}-{tf.value}-{lo}", symbol="X", kind=kind,
                 zone=(tick(lo), tick(hi)), born=NOW, tf=tf, state=state)


def ctx(levels):
    st = CandleStore("/nonexistent")
    return StockContext(symbol="X", now=NOW, candles=st.view("X", NOW),
                        levels=levels, evidence_history=[],
                        day=DayState(session_date=NOW.date()))


def test_registered():
    assert REGISTRY["htf_nest"] is HtfNestDetector


def test_m5_nested_in_m15_and_h1_emits_depth_2():
    levels = [
        zone(LevelKind.OB_BULL, 100, 101, Timeframe.M5),    # base
        zone(LevelKind.OB_BULL, 99, 102, Timeframe.M15),    # parent 1
        zone(LevelKind.FVG_BULL, 98, 103, Timeframe.H1),    # parent 2 (FVG counts)
    ]
    [ev] = HtfNestDetector({}).detect(ctx(levels))
    assert ev.detector == "htf_nest"
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick(100), tick(101))                # innermost base
    assert ev.meta["nest_depth"] == 2
    assert ev.meta["tiers"] == ["15m", "1h"]
    assert ev.meta["ce"] == str(tick("100.5"))              # mid = entry
    assert ev.meta["sl"] == str(tick(100))                  # base far (low) edge


def test_lone_base_no_parents_no_emit():
    assert HtfNestDetector({}).detect(ctx([
        zone(LevelKind.OB_BULL, 100, 101, Timeframe.M5)])) == []


def test_opposite_direction_parent_not_counted():
    levels = [zone(LevelKind.OB_BULL, 100, 101, Timeframe.M5),
              zone(LevelKind.OB_BEAR, 99, 102, Timeframe.M15)]  # bear != base bull
    assert HtfNestDetector({}).detect(ctx(levels)) == []


def test_non_overlapping_parent_not_counted():
    levels = [zone(LevelKind.OB_BULL, 100, 101, Timeframe.M5),
              zone(LevelKind.OB_BULL, 200, 210, Timeframe.H1)]  # far away
    assert HtfNestDetector({}).detect(ctx(levels)) == []


def test_short_side_and_sl_at_high_edge():
    levels = [zone(LevelKind.OB_BEAR, 100, 101, Timeframe.M5),
              zone(LevelKind.OB_BEAR, 99, 102, Timeframe.H1)]
    [ev] = HtfNestDetector({}).detect(ctx(levels))
    assert ev.direction is Direction.SHORT
    assert ev.meta["sl"] == str(tick(101))                  # SHORT SL = high edge


def test_dedupe_per_base_zone():
    levels = [zone(LevelKind.OB_BULL, 100, 101, Timeframe.M5, zid="B"),
              zone(LevelKind.OB_BULL, 99, 102, Timeframe.H1)]
    det = HtfNestDetector({})
    assert len(det.detect(ctx(levels))) == 1
    assert det.detect(ctx(levels)) == []                    # same base -> no re-emit


def test_ext_band_as_htf_parent():
    # a base M5 demand OB nests inside a higher-TF EXT_L band (swing low = demand)
    levels = [zone(LevelKind.OB_BULL, 100, 101, Timeframe.M5),
              zone(LevelKind.EXT_L, 99, 102, Timeframe.H1)]   # HTF swing-low band
    [ev] = HtfNestDetector({}).detect(ctx(levels))
    assert ev.direction is Direction.LONG
    assert ev.meta["nest_depth"] == 1
    assert ev.meta["tiers"] == ["1h"]


def test_ext_high_is_bear_parent_only():
    # EXT_H (supply) must NOT parent a bull base
    levels = [zone(LevelKind.OB_BULL, 100, 101, Timeframe.M5),
              zone(LevelKind.EXT_H, 99, 102, Timeframe.H1)]
    assert HtfNestDetector({}).detect(ctx(levels)) == []
