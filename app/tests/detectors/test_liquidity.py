"""Tests for the liquidity detector (trader/detectors/liquidity.py).
Binding design: see the module docstring and the task-4 brief."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.liquidity import LiquidityDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import TICK, Candle, Timeframe, tick
from trader.models.market import NSE
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
PREV_DAY = datetime(2026, 7, 14, tzinfo=IST)
TODAY = datetime(2026, 7, 15, tzinfo=IST)
SESSION_START = TODAY.replace(hour=9, minute=15)

DEFAULT_PARAMS = {
    "eq_tolerance": 0.001,
    "round_steps": [50, 100, 500],
    "round_within_pct": 2.0,
    "proximity_atr": 1.0,
}


def m1(ts, o, h, l, c, v=100):
    return Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(l), tick(c), v)


def add_full_day(store, day, o, h, l, c):
    """Add a full 375-minute session of M1 candles for `day`, each sharing
    the given OHLC, so the day's D1/prev_day aggregate is exactly h/l."""
    start = day.replace(hour=9, minute=15, second=0, microsecond=0)
    for i in range(NSE.session_minutes):
        store.add(m1(start + timedelta(minutes=i), o, h, l, c))


def add_bar(store, tf, bar_index, o, h, l, c, session_start=SESSION_START):
    """Add the tf.minutes M1 candles constituting bar_index's bucket, all
    sharing (o, h, l, c) so the tf-level aggregate is exactly that bar."""
    bucket_start = session_start + timedelta(minutes=bar_index * tf.minutes)
    for i in range(tf.minutes):
        store.add(m1(bucket_start + timedelta(minutes=i), o, h, l, c))


def bar_close(tf, bar_index, session_start=SESSION_START):
    return session_start + timedelta(minutes=(bar_index + 1) * tf.minutes)


def ctx_at(store, now, levels=None):
    view = store.view("X", now)
    return StockContext(
        symbol="X", now=now, candles=view,
        levels=levels if levels is not None else [],
        evidence_history=[], day=DayState(session_date=now.date()),
    )


# ---- PDH/PDL ---------------------------------------------------------

def test_pdh_pdl_created_from_prev_day():
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    add_full_day(store, PREV_DAY, o=100, h=120, l=90, c=110)
    store.add(m1(SESSION_START, 110, 111, 109, 110))
    now = SESSION_START + timedelta(minutes=1)
    ctx = ctx_at(store, now)

    det.detect(ctx)

    pdh = next(lv for lv in ctx.levels if lv.kind is LevelKind.PDH)
    pdl = next(lv for lv in ctx.levels if lv.kind is LevelKind.PDL)
    assert pdh.zone == (tick(120) - TICK, tick(120) + TICK)
    assert pdl.zone == (tick(90) - TICK, tick(90) + TICK)
    assert pdh.id == f"X-PDH-{ctx.day.session_date}"
    assert pdl.id == f"X-PDL-{ctx.day.session_date}"
    assert pdh.state is LevelState.ACTIVE


def test_pdh_pdl_absent_without_prev_day():
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    store.add(m1(SESSION_START, 110, 111, 109, 110))
    now = SESSION_START + timedelta(minutes=1)
    ctx = ctx_at(store, now)

    det.detect(ctx)

    assert not any(lv.kind in (LevelKind.PDH, LevelKind.PDL) for lv in ctx.levels)


# ---- Opening range -----------------------------------------------------

def test_open_range_absent_before_0930():
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    for i in range(10):  # only 10 of 15 minutes closed
        store.add(m1(SESSION_START + timedelta(minutes=i), 100, 105, 95, 100))
    now = SESSION_START + timedelta(minutes=10)
    ctx = ctx_at(store, now)

    det.detect(ctx)

    assert not any(
        lv.kind in (LevelKind.OPEN_RANGE_H, LevelKind.OPEN_RANGE_L)
        for lv in ctx.levels
    )


def test_open_range_created_after_0930():
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    for i in range(15):
        h = 110 if i == 5 else 105
        l = 90 if i == 7 else 95
        store.add(m1(SESSION_START + timedelta(minutes=i), 100, h, l, 100))
    now = SESSION_START + timedelta(minutes=15)  # 09:30, all 15 closed
    ctx = ctx_at(store, now)

    det.detect(ctx)

    orh = next(lv for lv in ctx.levels if lv.kind is LevelKind.OPEN_RANGE_H)
    orl = next(lv for lv in ctx.levels if lv.kind is LevelKind.OPEN_RANGE_L)
    assert orh.zone == (tick(110) - TICK, tick(110) + TICK)
    assert orl.zone == (tick(90) - TICK, tick(90) + TICK)
    assert orh.id == f"X-ORH-{ctx.day.session_date}"


# ---- Round numbers -------------------------------------------------------

def test_round_levels_created_within_pct():
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    store.add(m1(SESSION_START, 101, 101, 101, 101))
    now = SESSION_START + timedelta(minutes=1)
    ctx = ctx_at(store, now)

    det.detect(ctx)

    round_levels = [lv for lv in ctx.levels if lv.kind is LevelKind.ROUND]
    # step=50 and step=100 both round 101 -> 100 (within 2%); step=500 -> 0,
    # which is >2% away and must not be created.
    assert len(round_levels) == 2
    for lv in round_levels:
        assert lv.zone == (tick(100) - TICK, tick(100) + TICK)
    ids = {lv.id for lv in round_levels}
    assert ids == {f"X-ROUND-50-{tick(100)}", f"X-ROUND-100-{tick(100)}"}


def test_round_levels_absent_outside_pct():
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    store.add(m1(SESSION_START, 137, 137, 137, 137))
    now = SESSION_START + timedelta(minutes=1)
    ctx = ctx_at(store, now)

    det.detect(ctx)

    assert not any(lv.kind is LevelKind.ROUND for lv in ctx.levels)


# ---- EQH/EQL --------------------------------------------------------------

def test_eqh_created_from_two_close_swing_highs():
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    now = SESSION_START + timedelta(minutes=1)
    swing1 = Level(
        id="X-SWING_H-1", symbol="X", kind=LevelKind.SWING_H,
        zone=(tick(100) - TICK, tick(100) + TICK),
        born=now - timedelta(hours=1), tf=Timeframe.M5, state=LevelState.ACTIVE,
    )
    swing2 = Level(
        id="X-SWING_H-2", symbol="X", kind=LevelKind.SWING_H,
        zone=(tick("100.05") - TICK, tick("100.05") + TICK),
        born=now, tf=Timeframe.M5, state=LevelState.ACTIVE,
    )
    ctx = ctx_at(store, now, levels=[swing1, swing2])

    det.detect(ctx)

    eqh = next(lv for lv in ctx.levels if lv.kind is LevelKind.EQH)
    assert eqh.touches == 2
    assert eqh.zone[0] == min(swing1.zone[0], swing2.zone[0])
    assert eqh.zone[1] == max(swing1.zone[1], swing2.zone[1])


def test_eqh_not_created_from_single_swing_high():
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    now = SESSION_START + timedelta(minutes=1)
    swing1 = Level(
        id="X-SWING_H-1", symbol="X", kind=LevelKind.SWING_H,
        zone=(tick(100) - TICK, tick(100) + TICK),
        born=now, tf=Timeframe.M5, state=LevelState.ACTIVE,
    )
    ctx = ctx_at(store, now, levels=[swing1])

    det.detect(ctx)

    assert not any(lv.kind is LevelKind.EQH for lv in ctx.levels)


def test_eqh_not_created_when_swings_too_far_apart():
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    now = SESSION_START + timedelta(minutes=1)
    swing1 = Level(
        id="X-SWING_H-1", symbol="X", kind=LevelKind.SWING_H,
        zone=(tick(100) - TICK, tick(100) + TICK),
        born=now, tf=Timeframe.M5, state=LevelState.ACTIVE,
    )
    swing2 = Level(
        id="X-SWING_H-2", symbol="X", kind=LevelKind.SWING_H,
        zone=(tick(105) - TICK, tick(105) + TICK),  # 5% away, outside 0.1%
        born=now, tf=Timeframe.M5, state=LevelState.ACTIVE,
    )
    ctx = ctx_at(store, now, levels=[swing1, swing2])

    det.detect(ctx)

    assert not any(lv.kind is LevelKind.EQH for lv in ctx.levels)


def test_eqh_group_ids_differ_when_max_born_collides():
    """Two distinct 2-swing clusters at different prices whose younger swing
    shares the same born ts must not collide on level id (zone-mid disambiguates)."""
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    now = SESSION_START + timedelta(minutes=1)
    shared_born = now

    a1 = Level(id="X-SWING_H-A1", symbol="X", kind=LevelKind.SWING_H,
               zone=(tick(100) - TICK, tick(100) + TICK),
               born=now - timedelta(hours=1), tf=Timeframe.M5, state=LevelState.ACTIVE)
    a2 = Level(id="X-SWING_H-A2", symbol="X", kind=LevelKind.SWING_H,
               zone=(tick("100.05") - TICK, tick("100.05") + TICK),
               born=shared_born, tf=Timeframe.M5, state=LevelState.ACTIVE)
    b1 = Level(id="X-SWING_H-B1", symbol="X", kind=LevelKind.SWING_H,
               zone=(tick(200) - TICK, tick(200) + TICK),
               born=now - timedelta(hours=1), tf=Timeframe.M5, state=LevelState.ACTIVE)
    b2 = Level(id="X-SWING_H-B2", symbol="X", kind=LevelKind.SWING_H,
               zone=(tick("200.10") - TICK, tick("200.10") + TICK),
               born=shared_born, tf=Timeframe.M5, state=LevelState.ACTIVE)
    ctx = ctx_at(store, now, levels=[a1, a2, b1, b2])

    det.detect(ctx)

    eqh_levels = [lv for lv in ctx.levels if lv.kind is LevelKind.EQH]
    assert len(eqh_levels) == 2
    ids = {lv.id for lv in eqh_levels}
    assert len(ids) == 2  # unique despite identical max-born ts


def test_eqh_growth_mutate_third_swing_joins_group():
    """A 3rd swing arriving within tolerance of an existing 2-swing EQH group
    grows it in place: touches 2->3, zone widens to span all three, id stable."""
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    now = SESSION_START + timedelta(minutes=1)
    swing1 = Level(
        id="X-SWING_H-1", symbol="X", kind=LevelKind.SWING_H,
        zone=(tick(100) - TICK, tick(100) + TICK),
        born=now - timedelta(hours=1), tf=Timeframe.M5, state=LevelState.ACTIVE,
    )
    swing2 = Level(
        id="X-SWING_H-2", symbol="X", kind=LevelKind.SWING_H,
        zone=(tick("100.05") - TICK, tick("100.05") + TICK),
        born=now, tf=Timeframe.M5, state=LevelState.ACTIVE,
    )
    ctx = ctx_at(store, now, levels=[swing1, swing2])
    det.detect(ctx)

    eqh = next(lv for lv in ctx.levels if lv.kind is LevelKind.EQH)
    eqh_id, old_zone = eqh.id, eqh.zone
    assert eqh.touches == 2

    later = now + timedelta(minutes=5)
    swing3 = Level(
        id="X-SWING_H-3", symbol="X", kind=LevelKind.SWING_H,
        zone=(tick("100.08") - TICK, tick("100.08") + TICK),
        born=later, tf=Timeframe.M5, state=LevelState.ACTIVE,
    )
    ctx.levels.append(swing3)

    det.detect(ctx)

    eqh_levels = [lv for lv in ctx.levels if lv.kind is LevelKind.EQH]
    assert len(eqh_levels) == 1
    updated = eqh_levels[0]
    assert updated.id == eqh_id  # same level, mutated in place
    assert updated.touches == 3
    assert updated.zone == (old_zone[0], swing3.zone[1])  # widened to span
    assert updated.born == later


# ---- Proximity evidence --------------------------------------------------

def _ctx_with_atr(store_extra_levels=None):
    """Build 15 closed M5 bars (period=14 ATR needs 15) with a constant TR
    of 4, ending with the latest M1 close at 114. Returns (ctx,)."""
    store = CandleStore("/nonexistent")
    for i in range(15):
        o, h, l, c = 100 + i, 100 + i + 2, 100 + i - 2, 100 + i
        add_bar(store, Timeframe.M5, i, o, h, l, c)
    now = bar_close(Timeframe.M5, 14)
    return ctx_at(store, now, levels=store_extra_levels)


def test_proximity_evidence_for_untapped_pool_within_atr():
    det = LiquidityDetector(DEFAULT_PARAMS)
    pool = Level(
        id="X-PDH-2026-07-15", symbol="X", kind=LevelKind.PDH,
        zone=(tick(116) - TICK, tick(116) + TICK),  # mid ~116, price ~114
        born=TODAY, tf=None, state=LevelState.ACTIVE,
    )
    ctx = _ctx_with_atr([pool])

    result = det.detect(ctx)

    matches = [e for e in result if e.meta.get("level_id") == pool.id]
    assert len(matches) == 1
    ev = matches[0]
    assert ev.detector == "liquidity"
    assert ev.direction is Direction.NEUTRAL
    assert ev.strength == 0.6 * 0.5
    assert ev.ttl_candles == 12
    assert ev.zone == pool.zone


def test_eq_proximity_evidence_strength_value():
    # Two SWING_H born exactly at ctx.now -> recency = 1.0, touches = 2:
    # strength = (min(2/5, 1)*0.7 + 1.0*0.3) * 0.5 = 0.29
    det = LiquidityDetector(DEFAULT_PARAMS)
    now = bar_close(Timeframe.M5, 14)  # the "now" _ctx_with_atr uses
    swings = [
        Level(id=f"X-SWING_H-{i}", symbol="X", kind=LevelKind.SWING_H,
              zone=(tick(p) - TICK, tick(p) + TICK), born=now,
              tf=Timeframe.M5, state=LevelState.ACTIVE)
        for i, p in enumerate((116, "116.05"))
    ]
    ctx = _ctx_with_atr(swings)

    result = det.detect(ctx)

    [ev] = [e for e in result if e.meta["kind"] == "EQH"]
    assert ev.strength == pytest.approx(0.29)


def test_proximity_evidence_absent_when_pool_swept():
    det = LiquidityDetector(DEFAULT_PARAMS)
    pool = Level(
        id="X-PDH-2026-07-15", symbol="X", kind=LevelKind.PDH,
        zone=(tick(116) - TICK, tick(116) + TICK),
        born=TODAY, tf=None, state=LevelState.SWEPT,
    )
    ctx = _ctx_with_atr([pool])

    result = det.detect(ctx)

    assert not any(e.meta.get("level_id") == pool.id for e in result)


def test_proximity_evidence_absent_when_atr_none():
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    store.add(m1(SESSION_START, 114, 116, 112, 114))
    now = SESSION_START + timedelta(minutes=1)
    pool = Level(
        id="X-PDH-2026-07-15", symbol="X", kind=LevelKind.PDH,
        zone=(tick(116) - TICK, tick(116) + TICK),
        born=TODAY, tf=None, state=LevelState.ACTIVE,
    )
    ctx = ctx_at(store, now, levels=[pool])

    result = det.detect(ctx)

    assert result == []


# ---- Idempotency ----------------------------------------------------------

def test_second_detect_call_adds_nothing_new():
    det = LiquidityDetector(DEFAULT_PARAMS)
    store = CandleStore("/nonexistent")
    add_full_day(store, PREV_DAY, o=100, h=120, l=90, c=110)
    for i in range(15):
        h = 110 if i == 5 else 105
        l = 90 if i == 7 else 95
        store.add(m1(SESSION_START + timedelta(minutes=i), 100, h, l, 100))
    now = SESSION_START + timedelta(minutes=15)
    swing1 = Level(
        id="X-SWING_H-1", symbol="X", kind=LevelKind.SWING_H,
        zone=(tick(100) - TICK, tick(100) + TICK),
        born=now - timedelta(hours=1), tf=Timeframe.M5, state=LevelState.ACTIVE,
    )
    swing2 = Level(
        id="X-SWING_H-2", symbol="X", kind=LevelKind.SWING_H,
        zone=(tick("100.05") - TICK, tick("100.05") + TICK),
        born=now, tf=Timeframe.M5, state=LevelState.ACTIVE,
    )
    ctx = ctx_at(store, now, levels=[swing1, swing2])

    det.detect(ctx)
    count_after_first = len(ctx.levels)
    det.detect(ctx)

    assert len(ctx.levels) == count_after_first
