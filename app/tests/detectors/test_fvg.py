"""Tests for the fvg detector (trader/detectors/fvg.py).
Binding design: phase-3 task-4 brief (3-candle gap >= min_gap_atr * ATR,
CE hold 0.7, full fill -> DEAD, iFVG retest 0.75, BPR 0.8 newer-gap
direction, episode/pair dedupe).

Fixture geometry: one M1 candle per M5 bucket start -> the derived M5 bar
equals it exactly. FLAT bars keep TR == 2 so ATR stays close to 2 and the
0.3 * ATR gap threshold is ~0.6-0.7 points at the detection ticks used.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.fvg import FvgDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5

FLAT = (100, 101, 99, 100)                # TR = 2

# Bullish FVG triple: c3.low (102.5) > c1.high (101), gap 1.5 >= 0.3*ATR.
C1 = FLAT
C2 = (100, 104, 100, 104)                 # displacement candle
C3 = (103, 105, 102.5, 104)               # zone = (101, 102.5), CE = 101.75
C3_SMALL = (103, 105, 101.5, 104)         # gap 0.5 < 0.3*ATR: no FVG

# Bearish mirror: c3.high (97.5) < c1.low (99), zone = (97.5, 99).
C2_BEAR = (100, 100, 96, 96)
C3_BEAR = (97, 97.5, 95, 96)

HOLD = (104, 104, 101.8, 102)             # close 102: in zone, >= CE
HOLD2 = (102, 102.2, 101.8, 102)          # second in-zone CE-holding candle
BELOW_CE = (104, 104, 101.2, 101.2)       # in zone but below CE 101.75
LEAVE = (102, 103.5, 102, 103.5)          # close above zone: episode reset
FILL = (104, 104, 100, 100.5)             # close 100.5 < zone lo 101: full fill
AFTER_FILL = (100.5, 102, 100.5, 102)     # back inside the (dead) zone


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


def bull_store(extra=()):
    return make_store([FLAT] * 16 + [C1, C2, C3] + list(extra))


# ------------------------------------------------------------------ creation

def test_bull_fvg_created_exact_zone_and_id():
    levels = []
    evs = FvgDetector({}).detect(ctx_at(bull_store(), 19, levels))
    assert evs == []  # displacement close is above the gap: no evidence yet
    [lv] = levels
    assert lv.kind is LevelKind.FVG_BULL
    assert lv.id == f"X-FVG_BULL-5m-{bar_ts(17).isoformat()}"  # c2 ts
    assert lv.zone == (tick(101), tick(102.5))  # (c1.high, c3.low)
    assert lv.born == bar_ts(17)
    assert lv.tf is M5
    assert lv.state is LevelState.ACTIVE


def test_bear_fvg_mirror():
    store = make_store([FLAT] * 16 + [C1, C2_BEAR, C3_BEAR])
    levels = []
    assert FvgDetector({}).detect(ctx_at(store, 19, levels)) == []
    [lv] = levels
    assert lv.kind is LevelKind.FVG_BEAR
    assert lv.id == f"X-FVG_BEAR-5m-{bar_ts(17).isoformat()}"
    assert lv.zone == (tick(97.5), tick(99))  # (c3.high, c1.low)


def test_sub_threshold_gap_no_level():
    store = make_store([FLAT] * 16 + [C1, C2, C3_SMALL])
    levels = []
    assert FvgDetector({}).detect(ctx_at(store, 19, levels)) == []
    assert levels == []


def test_idempotent_redetect_and_fresh_instance():
    store, levels = bull_store(), []
    det = FvgDetector({})
    det.detect(ctx_at(store, 19, levels))
    assert len(levels) == 1
    assert det.detect(ctx_at(store, 19, levels)) == []  # same tick again
    assert len(levels) == 1
    FvgDetector({}).detect(ctx_at(store, 19, levels))   # fresh instance
    assert len(levels) == 1


# ------------------------------------------------------------------- CE hold

def test_ce_hold_fires_gap_direction():
    store, det, levels = bull_store([HOLD]), FvgDetector({}), []
    det.detect(ctx_at(store, 19, levels))               # creation tick
    [ev] = det.detect(ctx_at(store, 20, levels))
    assert ev.detector == "fvg"
    assert ev.direction is Direction.LONG
    assert ev.strength == pytest.approx(0.7)
    assert ev.zone == (tick(101), tick(102.5))
    assert ev.ttl_candles == 12
    assert ev.meta == {"level_id": levels[0].id, "event": "CE_HOLD"}


def test_close_inside_below_ce_no_evidence_until_hold():
    store, det, levels = bull_store([BELOW_CE, HOLD]), FvgDetector({}), []
    det.detect(ctx_at(store, 19, levels))
    assert det.detect(ctx_at(store, 20, levels)) == []  # in zone, CE not held
    [ev] = det.detect(ctx_at(store, 21, levels))        # same episode holds now
    assert ev.direction is Direction.LONG


def test_ce_once_per_episode_reentry_fires_again():
    store = bull_store([HOLD, HOLD2, LEAVE, (103.5, 103.5, 101.8, 102)])
    det, levels = FvgDetector({}), []
    det.detect(ctx_at(store, 19, levels))
    assert len(det.detect(ctx_at(store, 20, levels))) == 1
    assert det.detect(ctx_at(store, 21, levels)) == []  # same episode: silent
    assert det.detect(ctx_at(store, 22, levels)) == []  # left the zone
    assert len(det.detect(ctx_at(store, 23, levels))) == 1  # new episode


# ----------------------------------------------------------------- full fill

def test_full_fill_marks_dead_and_silences():
    store, det, levels = bull_store([FILL, AFTER_FILL]), FvgDetector({}), []
    det.detect(ctx_at(store, 19, levels))
    assert det.detect(ctx_at(store, 20, levels)) == []  # fill candle
    [lv] = levels
    assert lv.state is LevelState.DEAD
    assert lv.state_history == [(bar_ts(19), LevelState.DEAD)]
    assert det.detect(ctx_at(store, 21, levels)) == []  # back inside: dead
    assert lv.state_history == [(bar_ts(19), LevelState.DEAD)]  # not re-recorded


# ---------------------------------------------------------------------- iFVG

def flat_ctx(retest, levels, n_bars=6, flat=105):
    f = (flat, flat, flat, flat)
    return ctx_at(make_store([f] * (n_bars - 1) + [retest]), n_bars, levels)


def inverted_fvg(kind, inv_ts, zone=(tick(100), tick(101))):
    lv = Level(id=f"X-{kind.name}-5m-old", symbol="X", kind=kind, zone=zone,
               born=SESSION_START, tf=M5)
    lv.record_state(inv_ts - timedelta(minutes=5), LevelState.RECLAIMED)
    lv.record_state(inv_ts, LevelState.INVERTED)
    return lv


def test_ifvg_bull_retest_fires_short():
    lv = inverted_fvg(LevelKind.FVG_BULL, bar_ts(2))
    [ev] = FvgDetector({}).detect(flat_ctx((105, 105, 98, 99), [lv]))
    assert ev.direction is Direction.SHORT  # flipped: away from the zone
    assert ev.strength == pytest.approx(0.75)
    assert ev.ttl_candles == 12
    assert ev.zone == lv.zone
    assert ev.meta == {"level_id": lv.id, "event": "IFVG"}


def test_ifvg_bear_retest_fires_long():
    lv = inverted_fvg(LevelKind.FVG_BEAR, bar_ts(2))
    [ev] = FvgDetector({}).detect(flat_ctx((95, 103, 95, 102), [lv], flat=95))
    assert ev.direction is Direction.LONG
    assert ev.strength == pytest.approx(0.75)


def test_ifvg_close_inside_zone_no_evidence():
    lv = inverted_fvg(LevelKind.FVG_BULL, bar_ts(2))
    assert FvgDetector({}).detect(flat_ctx((105, 105, 98, 100.5), [lv])) == []


def test_ifvg_episode_dedupe_and_reinversion():
    det = FvgDetector({})
    lv = inverted_fvg(LevelKind.FVG_BULL, bar_ts(2))
    assert len(det.detect(flat_ctx((105, 105, 98, 99), [lv]))) == 1
    assert det.detect(flat_ctx((99, 100.5, 98, 99), [lv], n_bars=7)) == []
    lv.record_state(bar_ts(9), LevelState.INVERTED)     # simulated re-inversion
    assert len(det.detect(flat_ctx((99, 100.5, 98, 99), [lv], n_bars=11))) == 1


# ----------------------------------------------------------------------- BPR

def fvg_level(kind, zone, born_i, suffix):
    return Level(id=f"X-{kind.name}-5m-{suffix}", symbol="X", kind=kind,
                 zone=(tick(zone[0]), tick(zone[1])), born=bar_ts(born_i), tf=M5)


def bpr_evs(det, retest, levels, n_bars=6):
    return [e for e in det.detect(flat_ctx(retest, levels, n_bars=n_bars))
            if e.meta.get("event") == "BPR"]


def test_bpr_overlap_fires_newer_gap_direction_once():
    bull = fvg_level(LevelKind.FVG_BULL, (100, 102), 0, "a")
    bear = fvg_level(LevelKind.FVG_BEAR, (101, 103), 1, "b")  # newer
    det = FvgDetector({})
    [ev] = bpr_evs(det, (101.5, 101.6, 101.4, 101.5), [bull, bear])
    assert ev.direction is Direction.SHORT  # newer gap is bearish
    assert ev.strength == pytest.approx(0.8)
    assert ev.zone == (tick(101), tick(102))  # overlap region
    assert ev.ttl_candles == 12
    assert ev.meta == {"event": "BPR", "bull_id": bull.id, "bear_id": bear.id}
    # once per pair: a later close inside the overlap stays silent
    assert bpr_evs(det, (101.5, 101.6, 101.4, 101.5), [bull, bear], 7) == []


def test_bpr_newer_bull_fires_long():
    bull = fvg_level(LevelKind.FVG_BULL, (100, 102), 2, "a")  # newer
    bear = fvg_level(LevelKind.FVG_BEAR, (101, 103), 1, "b")
    [ev] = bpr_evs(FvgDetector({}), (101.5, 101.6, 101.4, 101.5), [bull, bear])
    assert ev.direction is Direction.LONG


def test_bpr_close_outside_overlap_no_evidence():
    bull = fvg_level(LevelKind.FVG_BULL, (100, 102), 0, "a")
    bear = fvg_level(LevelKind.FVG_BEAR, (101, 103), 1, "b")
    # 100.5 is inside the bull zone but below the (101, 102) overlap
    assert bpr_evs(FvgDetector({}), (100.5, 100.6, 100.4, 100.5),
                   [bull, bear]) == []
