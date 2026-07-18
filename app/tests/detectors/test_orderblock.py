"""Tests for the orderblock detector (trader/detectors/orderblock.py).
Binding design: phase-3 task-2 brief (zone = full candle range, net
displacement within lookback, hunt-born +0.15, overlap keeps higher quality).

Fixture geometry: one M1 candle per M5 bucket start -> the derived M5 bar
equals it exactly. All shapes keep TR == 2 so ATR(M5,14) == 2 exactly and
the displacement threshold is 1.5 * 2 = 3 points.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.orderblock import OrderblockDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.level import LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)  # NSE open
M5 = Timeframe.M5

FLAT = (100, 101, 99, 100)  # doji, TR=2: never an OB candidate

# Bullish OB pattern (each TR=2): bearish OB candle then +3 net displacement
# over 2 candles; quality = 0.4 (disp capped) + 0.075 (body) + 0.075 = 0.55.
OB_BULL_C = (100, 101, 99, 99.5)          # body 0.5, range 2, zone (99, 101)
BULL_D1 = (99.5, 101.5, 99.5, 101.5)
BULL_D2 = (101.5, 103.5, 101.5, 102.5)    # net close move = +3 = 1.5*ATR
BULL_RETRACE = (102.5, 102.5, 100.5, 100.5)  # closes back inside (99, 101)

# Bearish mirror.
OB_BEAR_C = (100, 101, 99, 100.5)
BEAR_D1 = (100.5, 100.5, 98.5, 98.5)
BEAR_D2 = (98.5, 98.5, 96.5, 97.5)        # net close move = -3
BEAR_RETRACE = (97.5, 99.5, 97.5, 99.5)


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def make_store(bars):
    """One M1 candle at each M5 bucket start -> M5 bar i == bars[i]."""
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


def bull_store(n_flat=16, retrace=False):
    bars = [FLAT] * n_flat + [OB_BULL_C, BULL_D1, BULL_D2]
    if retrace:
        bars.append(BULL_RETRACE)
    return make_store(bars), n_flat  # n_flat == OB candle index


def test_bullish_ob_created_exact_zone_and_id():
    store, ob_i = bull_store()
    levels = []
    evs = OrderblockDetector({}).detect(ctx_at(store, ob_i + 3, levels))
    assert evs == []  # displacement close is outside the zone: no evidence
    [lv] = levels
    assert lv.kind is LevelKind.OB_BULL
    assert lv.id == f"X-OB_BULL-5m-{bar_ts(ob_i).isoformat()}"
    assert lv.zone == (tick(99), tick(101))  # full OB candle range
    assert lv.born == bar_ts(ob_i)
    assert lv.tf is M5
    assert lv.state is LevelState.ACTIVE


def test_bearish_ob_mirror():
    store = make_store([FLAT] * 16 + [OB_BEAR_C, BEAR_D1, BEAR_D2])
    levels = []
    assert OrderblockDetector({}).detect(ctx_at(store, 19, levels)) == []
    [lv] = levels
    assert lv.kind is LevelKind.OB_BEAR
    assert lv.id == f"X-OB_BEAR-5m-{bar_ts(16).isoformat()}"
    assert lv.zone == (tick(99), tick(101))


def test_no_ob_when_displacement_below_threshold():
    # net close move only +2 < 1.5 * ATR(=2) = 3
    store = make_store([FLAT] * 16 + [OB_BULL_C, (99.5, 101.5, 99.5, 101),
                                      (101, 102, 100, 101.5)])
    levels = []
    assert OrderblockDetector({}).detect(ctx_at(store, 19, levels)) == []
    assert levels == []


def test_evidence_inside_zone_hunt_born():
    # OB born 10:35 (< open + 105min = 11:00) -> strength 0.55 + 0.15
    store, ob_i = bull_store(retrace=True)
    det, levels = OrderblockDetector({}), []
    det.detect(ctx_at(store, ob_i + 3, levels))       # creation tick
    [ev] = det.detect(ctx_at(store, ob_i + 4, levels))  # retrace closes inside
    assert ev.detector == "orderblock"
    assert ev.direction is Direction.LONG
    assert ev.strength == pytest.approx(0.70)
    assert ev.zone == (tick(99), tick(101))
    assert ev.ttl_candles == 6
    assert ev.meta == {"level_id": levels[0].id, "hunt_born": True, "event": "OB_RETEST"}


def test_no_hunt_bonus_after_105_minutes():
    # OB candle at bar 22 opens 11:05 >= 11:00 -> base quality only
    store, ob_i = bull_store(n_flat=22, retrace=True)
    det, levels = OrderblockDetector({}), []
    det.detect(ctx_at(store, ob_i + 3, levels))
    [ev] = det.detect(ctx_at(store, ob_i + 4, levels))
    assert ev.strength == pytest.approx(0.55)
    assert ev.meta["hunt_born"] is False


def test_hunt_minutes_param_overrides_default():
    # B12: same 11:05 OB, hunt window widened to 115min (open+115 = 11:10)
    # -> hunt bonus applies where the 105 default (test above) denies it
    store, ob_i = bull_store(n_flat=22, retrace=True)
    det, levels = OrderblockDetector({"hunt_minutes": 115}), []
    det.detect(ctx_at(store, ob_i + 3, levels))
    [ev] = det.detect(ctx_at(store, ob_i + 4, levels))
    assert ev.strength == pytest.approx(0.70)
    assert ev.meta["hunt_born"] is True


def test_bearish_evidence_direction_short():
    store = make_store([FLAT] * 16 + [OB_BEAR_C, BEAR_D1, BEAR_D2, BEAR_RETRACE])
    det, levels = OrderblockDetector({}), []
    det.detect(ctx_at(store, 19, levels))
    [ev] = det.detect(ctx_at(store, 20, levels))
    assert ev.direction is Direction.SHORT
    assert ev.strength == pytest.approx(0.70)


def test_mitigated_zone_emits_no_evidence():
    store, ob_i = bull_store(retrace=True)
    det, levels = OrderblockDetector({}), []
    det.detect(ctx_at(store, ob_i + 3, levels))
    levels[0].record_state(bar_ts(ob_i + 3), LevelState.MITIGATED)
    assert det.detect(ctx_at(store, ob_i + 4, levels)) == []
    assert len(levels) == 1  # not re-created either


def test_overlap_keeps_higher_quality_new_wins():
    # OB2 (bigger body, bigger displacement) overlaps OB1 -> OB2 replaces it
    store = make_store([FLAT] * 16 + [OB_BULL_C, (99.5, 99.6, 98.4, 98.5),
                                      (98.5, 103.5, 98.5, 103.5)])
    levels = []
    OrderblockDetector({}).detect(ctx_at(store, 19, levels))
    [lv] = levels
    assert lv.id == f"X-OB_BULL-5m-{bar_ts(17).isoformat()}"
    assert lv.zone == (tick(98.4), tick(99.6))


def test_overlap_keeps_higher_quality_old_wins():
    # OB1 (body 1.0) beats the smaller overlapping OB2 (body 0.4)
    store = make_store([FLAT] * 16 + [(100, 101, 99, 99), (99, 99.1, 98.4, 98.6),
                                      (98.6, 103.6, 98.6, 103.6)])
    levels = []
    OrderblockDetector({}).detect(ctx_at(store, 19, levels))
    [lv] = levels
    assert lv.id == f"X-OB_BULL-5m-{bar_ts(16).isoformat()}"


def test_idempotent_redetect():
    store, ob_i = bull_store(retrace=True)
    det, levels = OrderblockDetector({}), []
    det.detect(ctx_at(store, ob_i + 3, levels))
    assert len(levels) == 1
    assert det.detect(ctx_at(store, ob_i + 3, levels)) == []  # same tick again
    assert len(levels) == 1
    [ev] = det.detect(ctx_at(store, ob_i + 4, levels))
    assert det.detect(ctx_at(store, ob_i + 4, levels)) == []  # evidence once
    assert len(levels) == 1


def test_fresh_instance_does_not_duplicate_level():
    store, ob_i = bull_store()
    levels = []
    OrderblockDetector({}).detect(ctx_at(store, ob_i + 3, levels))
    OrderblockDetector({}).detect(ctx_at(store, ob_i + 3, levels))
    assert len(levels) == 1


def test_carried_ob_day2_rescan_dedupes_and_retests():
    """Continuum: a day-1 OB carried across the session boundary is re-derived
    by day-2's rescan (window spans the gap) with the SAME id -> no duplicate
    level -- and a day-2 close back inside the zone emits OB_RETEST."""
    store, ob_i = bull_store()
    det, levels = OrderblockDetector({}), []
    det.detect(ctx_at(store, ob_i + 3, levels))
    [lv] = levels
    det.on_session_end()                    # pipeline boundary: quality cleared
    day2 = SESSION_START + timedelta(days=1)
    store.add(Candle("X", Timeframe.M1, day2,
                     *(tick(x) for x in BULL_RETRACE), 10))
    now = day2 + timedelta(minutes=M5.minutes)
    ctx = StockContext(symbol="X", now=now, candles=store.view("X", now),
                       levels=levels, evidence_history=[],
                       day=DayState(session_date=day2.date()))
    evs = det.detect(ctx)
    assert levels == [lv]                   # same-id dedupe: no duplicate
    assert [e for e in evs if e.meta == {"level_id": lv.id, "hunt_born": True,
                                         "event": "OB_RETEST"}]
