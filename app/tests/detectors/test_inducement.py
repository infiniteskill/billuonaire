"""Tests for the inducement detector (trader/detectors/inducement.py).

Two layers:

* Hand-crafted 16-bar fixtures (ln=4, short_len=2 -- the state machine is
  length-parametric, so this drives the exact same code paths at a size a
  human can trace) pin the happy path / no-lookahead / dedupe / meta shape.

* An inlined faithful copy of the reference ``simulate`` (LuxAlgo idm branch,
  from scratchpad/ind_sweeps.py) is the fidelity ORACLE. The PARITY test feeds
  a long multi-day series tick-by-tick and asserts the detector reproduces
  ``simulate`` exactly -- this is the gate the adversarial review demanded.
  Two further tests pin the specific regressions the review found: a CHoCH
  ``>= 80`` bars before the sweep must still fire (full-history state, not a
  ``ln*4`` window), and two BOS-separated sweeps in one regime must both fire
  (BOS re-arm of the inducement latch).
"""

import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from trader.detectors.inducement import InducementDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import TICK, Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
PARAMS = {"tf": "5m", "ln": 4, "short_len": 2}
BARS_PER_DAY = 75  # 375 session minutes / 5


# --------------------------------------------------------------------------
# Reference oracle: verbatim idm branch of scratchpad simulate(), on Decimals
# (identical values to what the detector sees, so parity is exact -- no float
# rounding in the loop). ``rearm=False`` drops the BOS re-arm to expose it.
# --------------------------------------------------------------------------
def _swings(H, L, ln):
    n = len(H); top = [None] * n; btm = [None] * n; os_ = 0
    for i in range(n):
        prev = os_
        if i >= ln:
            upper = max(H[i - ln + 1:i + 1]); lower = min(L[i - ln + 1:i + 1])
            hlen, llen = H[i - ln], L[i - ln]
            os_ = 0 if hlen > upper else (1 if llen < lower else prev)
        if os_ == 0 and prev != 0: top[i] = H[i - ln]
        if os_ == 1 and prev != 1: btm[i] = L[i - ln]
    return top, btm


def _simulate(m5, ln, sl, rearm=True):
    """Returns (idm_events, os_sequence). idm_events: [(bar_index, dir)]."""
    H = [c.high for c in m5]; L = [c.low for c in m5]; C = [c.close for c in m5]
    top, btm = _swings(H, L, ln); stop, sbtm = _swings(H, L, sl)
    os = 0; tc = bc = False; maxv = minv = None; topy = btmy = None
    sc = sbc = False; stopy = sbtmy = None; idm = []; os_seq = []
    for i in range(len(m5)):
        p = os
        if top[i] is not None: topy = top[i]; tc = False
        if btm[i] is not None: btmy = btm[i]; bc = False
        if topy is not None and C[i] > topy and not tc: os = 1; tc = True
        if btmy is not None and C[i] < btmy and not bc: os = 0; bc = True
        if os != p: maxv = H[i]; minv = L[i]; sc = sbc = False
        if stop[i] is not None: stopy = stop[i]
        if sbtm[i] is not None: sbtmy = sbtm[i]
        if sbtmy is not None and L[i] < sbtmy and not sbc and os == 1 and sbtmy != btmy:
            sbc = True; idm.append((i, 1))
        if rearm and maxv is not None and C[i] > maxv and sbc and os == 1: sbc = False
        if stopy is not None and H[i] > stopy and not sc and os == 0 and stopy != topy:
            sc = True; idm.append((i, -1))
        if rearm and minv is not None and C[i] < minv and sc and os == 0: sc = False
        if maxv is not None: maxv = max(H[i], maxv)
        if minv is not None: minv = min(L[i], minv)
        os_seq.append(os)
    return idm, os_seq


def _windowed_last_bar_grabs(m5, ln, sl, W):
    """The OLD detector: recompute over the last ``W`` bars each tick, fire
    only when a grab lands on the last window bar. Returns global bar indices."""
    return [end for end in range(len(m5))
            if (ev := _simulate(m5[max(0, end - W + 1):end + 1], ln, sl)[0])
            and ev[-1][0] == end - max(0, end - W + 1)]


_DIR = {1: Direction.LONG, -1: Direction.SHORT}


# --------------------------------------------------------------------------
# Fixtures / feed helpers
# --------------------------------------------------------------------------
def _m1(ts, o, h, l, c):
    return Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(l), tick(c), 100)


def _bar_start(k):
    """M5 bucket start for the k-th bar of a continuous multi-day series."""
    day, j = divmod(k, BARS_PER_DAY)
    return SESSION_START + timedelta(days=day, minutes=j * 5)


def _build_m5(bars):
    return [Candle("X", Timeframe.M5, _bar_start(k), tick(o), tick(h), tick(l), tick(c), 500)
            for k, (o, h, l, c) in enumerate(bars)]


def _add_bar(store, k, o, h, l, c):
    bs = _bar_start(k)
    for i in range(5):
        store.add(_m1(bs + timedelta(minutes=i), o, h, l, c))
    return bs + timedelta(minutes=5)  # bar close = 'now'


def _ctx(store, now):
    return StockContext(symbol="X", now=now, candles=store.view("X", now), levels=[],
                        evidence_history=[], day=DayState(session_date=now.date()))


def _feed(bars, params, det=None):
    """Feed one closed M5 bar per tick; return [(bar_index, Direction)]."""
    store = CandleStore("/nonexistent")
    det = det or InducementDetector(params)
    grabs = []
    for k, (o, h, l, c) in enumerate(bars):
        now = _add_bar(store, k, o, h, l, c)
        for ev in det.detect(_ctx(store, now)):
            grabs.append((k, ev.direction))
    return grabs


def _rand_series(n, seed):
    """Deterministic quantized random walk (steps on the 0.25 grid, so tick
    quantization is exact). Produces varied CHoCH/BOS/grab structure."""
    rng = random.Random(seed); price = 100.0; bars = []
    q = lambda v: round(v * 4) / 4
    for _ in range(n):
        o = price; c = max(20.0, o + rng.uniform(-3, 3))
        hi = max(o, c) + rng.uniform(0, 2.5); lo = min(o, c) - rng.uniform(0, 2.5)
        bars.append((q(o), q(hi), q(lo), q(c))); price = c
    return bars


# One-window hand-crafted fixtures (single day) -----------------------------
LONG_BARS = [
    (98, 100, 92, 98), (99, 101, 93, 99), (100, 102, 94, 100), (101, 103, 95, 101),
    (101, 103, 95, 101), (100, 102, 94, 100), (99, 101, 93, 99), (98, 100, 92, 98),
    (99, 101, 93, 99), (100, 102, 94, 100), (101, 103, 95, 101), (100, 102, 94, 100),
    (99, 101, 93, 99), (102, 104, 96, 102), (105, 107, 99, 105), (106, 108, 91, 106),
]  # bar 14: CHoCH bullish; bar 15: sweeps short-swing low 93 -> grab
SHORT_BARS = [(200 - o, 200 - l, 200 - h, 200 - c) for (o, h, l, c) in LONG_BARS]
NO_CHOCH_BARS = LONG_BARS[:13] + [(82, 84, 76, 82), (85, 87, 79, 85), (86, 88, 71, 86)]


def _load_single(bars, upto=None):
    """Single detect() over the whole (single-day) fixture."""
    store = CandleStore("/nonexistent")
    n = upto if upto is not None else len(bars)
    now = None
    for k in range(n):
        now = _add_bar(store, k, *bars[k])
    return _ctx(store, now)


# --------------------------------------------------------------------------
# Happy path / meta / no-lookahead / dedupe (hand-crafted, real asserts)
# --------------------------------------------------------------------------
def test_no_grab_without_preceding_choch():
    assert InducementDetector(PARAMS).detect(_load_single(NO_CHOCH_BARS)) == []


def test_choch_then_sweep_fires_long_grab():
    [ev] = InducementDetector(PARAMS).detect(_load_single(LONG_BARS))
    assert ev.detector == "inducement"
    assert ev.direction is Direction.LONG
    assert 0 < ev.strength <= 1
    assert ev.ttl_candles == 3
    extreme = tick(93)
    assert ev.zone == (extreme - TICK, extreme + TICK)
    assert ev.meta == {"event": "INDUCEMENT_GRAB", "sl": extreme - TICK, "os": 1}


def test_choch_then_sweep_fires_short_grab_mirror():
    [ev] = InducementDetector(PARAMS).detect(_load_single(SHORT_BARS))
    assert ev.direction is Direction.SHORT
    extreme = tick(107)
    assert ev.zone == (extreme - TICK, extreme + TICK)
    assert ev.meta == {"event": "INDUCEMENT_GRAB", "sl": extreme + TICK, "os": 0}


def test_no_lookahead_fractal_confirmation_delay():
    det = InducementDetector(PARAMS)
    store = CandleStore("/nonexistent")
    result = []
    for k, bar in enumerate(LONG_BARS):
        now = _add_bar(store, k, *bar)
        result = det.detect(_ctx(store, now))
        if k < len(LONG_BARS) - 1:
            assert result == [], f"grab must not fire before bar {len(LONG_BARS) - 1} closes"
    assert len(result) == 1 and result[0].meta["event"] == "INDUCEMENT_GRAB"


def test_dedupe_fires_once_for_same_event():
    det = InducementDetector(PARAMS)
    ctx = _load_single(LONG_BARS)
    assert len(det.detect(ctx)) == 1
    assert det.detect(ctx) == []  # same closed history: nothing new to advance over


def test_on_session_end_preserves_structure_no_refire():
    # New semantics: on_session_end prunes ONLY the dedupe set; the structural
    # FSM state (and the processed-bar cursor) persists across sessions, so the
    # same already-consumed history does NOT re-fire.
    det = InducementDetector(PARAMS)
    ctx = _load_single(LONG_BARS)
    assert len(det.detect(ctx)) == 1
    det.on_session_end()
    assert det.detect(ctx) == []


def test_insufficient_history_returns_empty():
    assert InducementDetector(PARAMS).detect(_load_single(LONG_BARS, upto=3)) == []


def test_default_params():
    assert InducementDetector({}).params == {"tf": "5m", "ln": 20, "short_len": 3}


# --------------------------------------------------------------------------
# 1. PARITY -- the fidelity gate
# --------------------------------------------------------------------------
def test_parity_with_reference_over_multiday_series():
    bars = _rand_series(240, 12)  # ~3.2 sessions of continuous 5m structure
    m5 = _build_m5(bars)
    events, _ = _simulate(m5, 4, 2)
    expected = [(m5[i].ts, _DIR[d]) for i, d in events]

    got = [(_bar_start(k), direction) for k, direction in _feed(bars, PARAMS)]

    assert got == expected
    # guard: the fixture must actually exercise the machine in both directions
    assert len(expected) >= 6
    assert {d for _, d in expected} == {Direction.LONG, Direction.SHORT}


# --------------------------------------------------------------------------
# 2. CHoCH >= 80 bars before the sweep still fires (full-history state)
# --------------------------------------------------------------------------
def test_far_choch_state_carried_beyond_old_window():
    bars = _rand_series(120, 15)  # spans 2 sessions
    m5 = _build_m5(bars)
    events, os_seq = _simulate(m5, 4, 2)
    assert events == [(93, 1)]                      # exactly one late grab
    grab_bar = 93
    # the enabling CHoCH is the start of the os==1 run holding at the grab bar
    choch = grab_bar
    while choch and os_seq[choch - 1] == 1:
        choch -= 1
    assert grab_bar - choch >= 80                   # state carried across >= 80 bars

    # the OLD ln*4 window (=16) cannot reproduce this grab and invents spurious
    # ones -- exactly the review's finding.
    old = _windowed_last_bar_grabs(m5, 4, 2, 16)
    assert grab_bar not in old and old              # missed the real one, fired junk

    got = _feed(bars, PARAMS)
    assert got == [(93, Direction.LONG)]            # fixed detector fires it, once


# --------------------------------------------------------------------------
# 3. Two BOS-separated sweeps in one bullish regime -> two grabs (BOS re-arm)
# --------------------------------------------------------------------------
def test_two_bos_separated_sweeps_both_fire():
    bars = _rand_series(40, 373)
    m5 = _build_m5(bars)
    full, _ = _simulate(m5, 4, 2, rearm=True)
    no_rearm, _ = _simulate(m5, 4, 2, rearm=False)
    assert full == [(26, 1), (37, 1)]               # two LONG grabs, one regime
    assert no_rearm == [(26, 1)]                     # without BOS re-arm: only one

    got = _feed(bars, PARAMS)
    assert got == [(26, Direction.LONG), (37, Direction.LONG)]
