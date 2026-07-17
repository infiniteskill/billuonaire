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
