"""Tests for the fvg_cb detector (trader/detectors/fvg_cb.py).
Binding design: v2 task-2 brief (validated LuxAlgo dedicated close-beyond
FVG, ported from the measured-winner scratchpad fvg2.py: `gaps(...,
"luxded")` -- 3-bar gap + displacement close-beyond + auto mean-bar-range%
threshold -- plus its `cehold`/`retest` one-shot forward-scan events).

Fixture geometry: one M1 candle per M5 bucket start -> the derived M5 bar
equals it exactly (same trick as test_fvg.py/test_ob_lux.py). 16 FLAT
warmup bars keep the auto threshold small (~0.02) so a real gap (~5%) easily
clears it; born index of the gap candle (c3) is bar 18, so eligibility for
retest/CE-hold starts at bar 19 (born+1, matching fvg2.py's `range(born+1,
...)`).
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.fvg_cb import FvgCbDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.level import LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5

FLAT = (100, 101, 99, 100)                     # TR%% ~ 2% warmup bar

# Bullish triple: c1 flat, c2 displaces & CLOSES beyond c1.high (101), c3
# gaps up (low 106 > c1.high 101); zone = (101, 106), gap% ~= 5% >> auto thr.
C1 = FLAT
C2 = (100, 108, 100, 108)
C3 = (107, 110, 106, 108)
C2_NO_DISP = (100, 108, 100, 100)              # same wick, close stays at 100: no displacement

# Bearish mirror: zone = (96, 99).
C2_BEAR = (100, 100, 94, 94)
C3_BEAR = (95, 96, 92, 94)

TOUCH = (108, 108, 103, 108)                   # wick overlaps zone, close outside -> retest only
HOLD = (105, 105, 104, 105)                    # closes inside zone, >= CE (103.5) -> CE-hold
BREAK = (100, 100, 95, 96)                     # low fully below zone -> both events silenced


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


def bull_bars(extra=()):
    return [FLAT] * 16 + [C1, C2, C3] + list(extra)


def bear_bars(extra=()):
    return [FLAT] * 16 + [C1, C2_BEAR, C3_BEAR] + list(extra)


# ------------------------------------------------------------------ creation

def test_bull_gap_birth_zone_and_ce_hold_long():
    store = make_store(bull_bars([TOUCH, HOLD]))
    det, levels = FvgCbDetector({}), []
    assert det.detect(ctx_at(store, 19, levels)) == []   # creation tick: c3 itself never eligible
    [lv] = levels
    assert lv.kind is LevelKind.FVG_BULL
    assert lv.zone == (tick(101), tick(106))              # (c1.high, c3.low)
    assert lv.born == bar_ts(17)                          # c2.ts
    assert lv.tf is M5
    assert lv.state is LevelState.ACTIVE
    [retest_ev] = det.detect(ctx_at(store, 20, levels))     # bar19 TOUCH: retest fires (checked below)
    assert retest_ev.meta["event"] == "FVG_RETEST"
    [ev] = det.detect(ctx_at(store, 21, levels))           # bar20 HOLD: CE-hold fires
    assert ev.detector == "fvg_cb"
    assert ev.direction is Direction.LONG
    assert ev.strength == pytest.approx(0.75)
    assert ev.zone == (tick(101), tick(106))
    assert ev.ttl_candles == 6
    assert ev.meta == {"level_id": lv.id, "event": "FVG_CE_HOLD"}


def test_bear_mirror():
    store = make_store(bear_bars())
    det, levels = FvgCbDetector({}), []
    assert det.detect(ctx_at(store, 19, levels)) == []
    [lv] = levels
    assert lv.kind is LevelKind.FVG_BEAR
    assert lv.zone == (tick(96), tick(99))                # (c3.high, c1.low)
    assert lv.born == bar_ts(17)


def test_no_displacement_no_level():
    store = make_store([FLAT] * 16 + [C1, C2_NO_DISP, C3])  # gap exists but c2 close doesn't beyond c1.high
    levels = []
    assert FvgCbDetector({}).detect(ctx_at(store, 19, levels)) == []
    assert levels == []


def test_auto_threshold_gate_rejects_valid_shape_below_mean_range_pct():
    """Coverage for the auto mean-bar-range% gate itself: the bull triple has
    valid 3-bar shape AND valid close-beyond displacement (both pass), but an
    inflated thr_mult pushes the auto threshold (~2.2% * mult) far above the
    gap's own size (~5%), so creation is rejected purely on `(hi-lo)/lo <=
    thr` -- previously zero coverage of this branch."""
    store = make_store(bull_bars())
    det, levels = FvgCbDetector({"thr_mult": 1000.0}), []
    assert det.detect(ctx_at(store, 19, levels)) == []
    assert levels == []


# --------------------------------------------------------------- retest/hold

def test_retest_fires_once_before_ce_hold():
    store = make_store(bull_bars([TOUCH, HOLD]))
    det, levels = FvgCbDetector({}), []
    det.detect(ctx_at(store, 19, levels))                  # creation
    [ev] = det.detect(ctx_at(store, 20, levels))            # TOUCH: retest, no hold yet
    assert ev.direction is Direction.LONG
    assert ev.strength == pytest.approx(0.6)
    assert ev.ttl_candles == 6
    assert ev.meta == {"level_id": levels[0].id, "event": "FVG_RETEST"}
    [ev2] = det.detect(ctx_at(store, 21, levels))           # HOLD: CE-hold only (retest already resolved)
    assert ev2.meta["event"] == "FVG_CE_HOLD"


def test_break_before_touch_silences_both_events():
    store = make_store(bull_bars([BREAK, HOLD]))            # HOLD would qualify but BREAK ran first
    det, levels = FvgCbDetector({}), []
    det.detect(ctx_at(store, 19, levels))
    assert det.detect(ctx_at(store, 20, levels)) == []      # BREAK: silenced, no event
    assert det.detect(ctx_at(store, 21, levels)) == []      # one-shot: stays silent even on a later hold


# ------------------------------------------------------------ no-lookahead

def test_no_lookahead_same_tick_redetect_is_idempotent():
    store, levels = make_store(bull_bars()), []
    det = FvgCbDetector({})
    det.detect(ctx_at(store, 19, levels))
    assert len(levels) == 1
    assert det.detect(ctx_at(store, 19, levels)) == []      # same tick again: no dup level, no evidence
    assert len(levels) == 1


# ------------------------------------------------------------ session gap

def test_c3_across_session_boundary_not_eligible_on_creation_tick():
    """Regression for the CRITICAL: c1/c2 close out day 1, c3 (the
    gap-confirming bar) is the FIRST bar of day 2. Level.born (=c2.ts) +
    tf.minutes lands mid-day-1 -- nowhere near the real c3 -- so the OLD
    born+tf gate would treat the creation tick's `last` (c3 itself) as
    already eligible and fire retest/CE-hold against the zone c3 just
    defined. The fix stores c3's actual ts per level and gates on that."""
    day1 = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
    day2 = datetime(2026, 7, 16, 9, 15, tzinfo=IST)
    store = CandleStore("/nonexistent")
    for i, (o, h, l, c) in enumerate([FLAT] * 16):
        store.add(Candle("X", Timeframe.M1, day1 + timedelta(minutes=5 * i),
                         tick(o), tick(h), tick(l), tick(c), 10))
    c1_ts = day1 + timedelta(minutes=5 * 16)
    store.add(Candle("X", Timeframe.M1, c1_ts, *(tick(x) for x in C1), 10))
    c2_ts = c1_ts + timedelta(minutes=5)
    store.add(Candle("X", Timeframe.M1, c2_ts, *(tick(x) for x in C2), 10))
    c3_ts = day2                                    # next session's first bar
    store.add(Candle("X", Timeframe.M1, c3_ts, *(tick(x) for x in C3), 10))

    det, levels = FvgCbDetector({}), []
    now = c3_ts + timedelta(minutes=M5.minutes)      # c3 just closed
    ctx = StockContext(symbol="X", now=now, candles=store.view("X", now),
                       levels=levels, evidence_history=[],
                       day=DayState(session_date=now.date()))
    assert det.detect(ctx) == []                     # creation tick: c3 excluded, no evidence
    [lv] = levels
    assert lv.born == c2_ts
    assert det._c3_ts[lv.id] == c3_ts                # gated on real c3.ts, not born+tf

    touch_ts = c3_ts + timedelta(minutes=M5.minutes)  # strictly after c3
    store.add(Candle("X", Timeframe.M1, touch_ts, *(tick(x) for x in TOUCH), 10))
    now2 = touch_ts + timedelta(minutes=M5.minutes)
    ctx2 = StockContext(symbol="X", now=now2, candles=store.view("X", now2),
                        levels=levels, evidence_history=[],
                        day=DayState(session_date=now2.date()))
    [ev] = det.detect(ctx2)                          # first eligible tick: retest fires
    assert ev.meta["event"] == "FVG_RETEST"


# --------------------------------------------------------------- session end

def test_on_session_end_clears_instance_memory():
    store = make_store(bull_bars([TOUCH, HOLD]))
    det, levels = FvgCbDetector({}), []
    det.detect(ctx_at(store, 19, levels))
    det.detect(ctx_at(store, 20, levels))
    det.detect(ctx_at(store, 21, levels))
    assert det._retest_done and det._ce_done
    det.on_session_end()
    assert det._retest_done == set() and det._ce_done == set()


def test_carried_level_day2_retest_no_keyerror():
    """Continuum: an unmitigated fvg_cb level carried across the session
    boundary arrives with its _c3_ts entry cleared -- day-2 events must treat
    it as long past c3 (no KeyError) and a day-2 touch fires a fresh retest."""
    store = make_store(bull_bars())
    det, levels = FvgCbDetector({}), []
    det.detect(ctx_at(store, 19, levels))
    [lv] = levels
    det.on_session_end()                   # pipeline boundary: maps cleared
    day2 = SESSION_START + timedelta(days=1)
    store.add(Candle("X", Timeframe.M1, day2, *(tick(x) for x in TOUCH), 10))
    now = day2 + timedelta(minutes=M5.minutes)
    ctx = StockContext(symbol="X", now=now, candles=store.view("X", now),
                       levels=levels, evidence_history=[],
                       day=DayState(session_date=day2.date()))
    evs = det.detect(ctx)
    assert levels == [lv]                  # no duplicate from the day-2 scan
    assert [e.meta["event"] for e in evs] == ["FVG_RETEST"]
