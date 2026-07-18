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

PARITY GATE (bottom of file): real M1 continuum data (data/wide: RELIANCE,
INFY) driven tick-by-tick through the actual detector and cross-checked
against an inlined faithful copy of fvg2.py's gaps(...,"luxded")/cehold/
retest -- the pattern from test_inducement.py's parity test. Also proves the
one documented divergence (session-carry re-fire) is exactly that and
nothing else.
"""

import glob
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from trader.detectors.fvg_cb import FvgCbDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.level import TERMINAL, LevelKind, LevelState
from trader.models.market import NSE
from trader.store.candles import CandleStore
from trader.tools.study import atr_series

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


# ===========================================================================
# PARITY GATE -- real continuum M1 data (data/wide) vs the fvg2.py oracle.
#
# Reference: scratchpad/fvg2.py's gaps(m5, atrs, "luxded") + cehold(m5, z) +
# retest(m5, z), inlined verbatim below (same pattern as test_inducement.py's
# ``_simulate``: an independent fidelity oracle, not shared code with the
# detector). ``atr_series`` IS imported from trader.tools.study, exactly as
# fvg2.py itself does -- it is fvg2.py's own dependency, not fvg_cb's.
#
# Driving: the whole M1 series is loaded into one CandleStore up front, then
# each M5 bucket's close is ticked in order. CandleView is a pure function of
# (stored data, now), so this reproduces true tick-by-tick M1 feeding without
# needing to interleave adds (verified against an M1-by-M1 driver during
# development -- identical counts).
# ===========================================================================
def _data_wide() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        cand = parent / "data" / "wide"
        if cand.is_dir():
            return cand
    return None


_WIDE = _data_wide()
_MIN_ROWS = 1000  # LTIM/TATAMOTORS ship as header-only stubs -- excluded
_REAL_SYMBOLS = sorted(
    sym for f in (glob.glob(str(_WIDE / "*.csv")) if _WIDE else [])
    if (sym := Path(f).stem) in {"RELIANCE", "INFY", "LTIM", "TATAMOTORS"}
    and sum(1 for _ in open(f)) - 1 >= _MIN_ROWS
)
_real_data = pytest.mark.skipif(not _REAL_SYMBOLS, reason="data/wide real M1 fixtures not found")


def _load_m1(symbol: str) -> list[Candle]:
    df = pd.read_csv(_WIDE / f"{symbol}.csv")
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("Asia/Kolkata")
    return [Candle(symbol, Timeframe.M1, row.ts.to_pydatetime(),
                   NSE.quantize(row.open), NSE.quantize(row.high),
                   NSE.quantize(row.low), NSE.quantize(row.close), int(row.volume))
            for row in df.itertuples(index=False)]


def _build_m5(symbol: str, m1s: list[Candle]):
    store = CandleStore("/nonexistent")
    for c in m1s:
        store.add(c)
    far = m1s[-1].ts + timedelta(days=2)
    return store, store.view(symbol, far).last(1_000_000, M5)


def _ref_gaps(m5, atrs):  # verbatim: fvg2.py gaps(..., "luxded")
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; C = [float(c.close) for c in m5]
    cum = 0.0; z = []
    for i in range(2, len(m5)):
        a = atrs[i]; cum += (H[i] - L[i]) / L[i] if L[i] else 0; thr = cum / (i + 1)
        if a is None:
            continue
        if L[i] > H[i - 2] and C[i - 1] > H[i - 2] and (L[i] - H[i - 2]) / H[i - 2] > thr:
            z.append((i, H[i - 2], L[i], 1))
        if H[i] < L[i - 2] and C[i - 1] < L[i - 2] and (L[i - 2] - H[i]) / H[i] > thr:
            z.append((i, H[i], L[i - 2], -1))
    return z


def _ref_retest(m5, z):  # verbatim: fvg2.py retest(m5, z)
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; ev = []
    for born, lo, hi, dr in z:
        for j in range(born + 1, len(m5)):
            if dr == 1 and L[j] < lo: break
            if dr == -1 and H[j] > hi: break
            if L[j] <= hi and H[j] >= lo:
                ev.append((j, dr)); break
    return ev


def _ref_cehold(m5, z):  # verbatim: fvg2.py cehold(m5, z)
    L = [float(c.low) for c in m5]; H = [float(c.high) for c in m5]; C = [float(c.close) for c in m5]; ev = []
    for born, lo, hi, dr in z:
        mid = (lo + hi) / 2
        for j in range(born + 1, len(m5)):
            if dr == 1 and C[j] < lo: break
            if dr == -1 and C[j] > hi: break
            if lo <= C[j] <= hi and ((dr == 1 and C[j] >= mid) or (dr == -1 and C[j] <= mid)):
                ev.append((j, dr)); break
    return ev


_DIR = {1: Direction.LONG, -1: Direction.SHORT}


def _sessions_old(born, ref):  # verbatim mirror of SymbolPipeline._sessions_old
    if ref is None or ref <= born:
        return 0
    return sum((born + timedelta(days=i)).weekday() < 5 for i in range(1, (ref - born).days + 1))


def _drive(symbol, store, m5_full, with_sessions):
    """Tick every M5 bucket close in order. ``with_sessions=True`` additionally
    fires on_session_end() + the SymbolPipeline._carry_over zone-prune (drop
    TERMINAL or >=5-session-old FVG levels) at each real day boundary, in
    production's own order: the OLD day's last bucket closes first, THEN the
    session ends using that OLD session_date as the age reference."""
    det, levels = FvgCbDetector({}), []
    gaps, events = [], []
    prev_date = None
    for i, bar in enumerate(m5_full):
        if with_sessions and prev_date is not None and bar.ts.date() != prev_date:
            det.on_session_end()
            levels[:] = [lv for lv in levels if lv.state not in TERMINAL
                        and _sessions_old(lv.born.date(), prev_date) < 5]
        now = bar.ts + timedelta(minutes=M5.minutes)
        before = {lv.id for lv in levels}
        ctx = StockContext(symbol=symbol, now=now, candles=store.view(symbol, now),
                           levels=levels, evidence_history=[],
                           day=DayState(session_date=bar.ts.date()))
        for ev in det.detect(ctx):
            events.append((i, ev.meta["level_id"], ev.meta["event"], ev.direction))
        gaps += [(i, lv.zone, lv.kind) for lv in levels if lv.id not in before]
        prev_date = bar.ts.date()
    return gaps, events


@_real_data
def test_parity_gapset_and_events_match_luxded_reference_on_real_data():
    """Continuum drive (no on_session_end -- same pattern as
    test_inducement.py's parity test, whose reference likewise never resets):
    the created gap-set and the retest/CE-hold event-set must reproduce
    fvg2.py's gaps(...,"luxded")/retest/cehold exactly, bar-index-for-bar-
    index, direction-for-direction, on two real symbols' full M1 history."""
    assert _REAL_SYMBOLS == ["INFY", "RELIANCE"]  # guard: LTIM/TATAMOTORS excluded
    total_gaps = total_events = 0
    for symbol in _REAL_SYMBOLS:
        store, m5_full = _build_m5(symbol, _load_m1(symbol))
        z = _ref_gaps(m5_full, atr_series(m5_full))
        expected_gaps = sorted((i, round(lo, 6), round(hi, 6), dr) for i, lo, hi, dr in z)
        expected_events = sorted(
            [(j, "FVG_RETEST", _DIR[dr]) for j, dr in _ref_retest(m5_full, z)] +
            [(j, "FVG_CE_HOLD", _DIR[dr]) for j, dr in _ref_cehold(m5_full, z)])

        got_gaps, got_events = _drive(symbol, store, m5_full, with_sessions=False)
        got_gaps_r = sorted((i, round(float(lo), 6), round(float(hi), 6),
                             1 if kind is LevelKind.FVG_BULL else -1)
                            for i, (lo, hi), kind in got_gaps)
        got_events_r = sorted((i, ev, dr) for i, _lid, ev, dr in got_events)

        assert got_gaps_r == expected_gaps, symbol
        assert got_events_r == expected_events, symbol
        total_gaps += len(expected_gaps); total_events += len(expected_events)
    assert total_gaps >= 50 and total_events >= 100  # guard: real structure exercised, both directions


@_real_data
def test_session_carry_refire_is_the_only_divergence_from_continuum():
    """Documented difference: on_session_end() clears the one-shot dedupe
    sets (see FvgCbDetector.on_session_end's docstring), so an unmitigated
    level carried into a later (< 5 sessions old) session may re-fire an
    event it already fired -- fvg2.py has no session concept (one unbroken
    forward scan) so it never does. Proves that carry-refire is the ONLY
    source of divergence: every session-driven (level, event) pair's first
    occurrence set is identical to the continuum reference's event count,
    no pair ever fires twice within the SAME session, and re-fires are
    actually observed on this real data (not a hypothetical)."""
    for symbol in _REAL_SYMBOLS:
        store, m5_full = _build_m5(symbol, _load_m1(symbol))
        z = _ref_gaps(m5_full, atr_series(m5_full))
        n_reference_events = len(_ref_retest(m5_full, z)) + len(_ref_cehold(m5_full, z))

        _, session_events = _drive(symbol, store, m5_full, with_sessions=True)
        fires_by_pair: dict[tuple[str, str], list] = {}
        for i, lid, ev, _dr in session_events:
            fires_by_pair.setdefault((lid, ev), []).append(m5_full[i].ts.date())

        assert len(fires_by_pair) == n_reference_events, symbol   # same first-fire set as continuum
        for days in fires_by_pair.values():
            assert len(set(days)) == len(days), symbol            # never twice in the same session
        assert any(len(days) > 1 for days in fires_by_pair.values()), symbol  # re-fire actually observed
