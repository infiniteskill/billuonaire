"""Tests for the bpr detector (trader/detectors/bpr.py).
Binding design: v2-task5 brief (ict_pieces.py::bpr/find_gaps port) -- a live
bull FVG overlapping a live bear FVG is a Balanced Price Range; the first
close back INSIDE the overlap fires in the direction of the NEWER
(later-born) gap, sl = overlap lo (LONG) / hi (SHORT). A gap dies when a
close breaks its far edge; only pairs still live at the touch bar qualify.

Fixture geometry: one M1 candle per M5 bucket start -> the derived M5 bar
equals it exactly, same convention as test_fvg.py/test_compression_fade.py.
16 FLAT filler bars (TR=2) prime ATR-14 (~2.0-2.3 through the scenario) so
the 0.3*ATR gap threshold sits around 0.6-0.7 points."""

import subprocess
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.bpr import BprDetector, _Gap
from trader.engine.context import DayState, StockContext
from trader.feed.file import FileFeed
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.market import NSE
from trader.store.candles import CandleStore, _bucket_start
from trader.tools.study import atr_series

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5

FLAT = (100, 101, 99, 100)  # TR = 2

# ---- Case A: bull FVG (older) x bear FVG (newer) -> SHORT ----
C1_BULL, C2_BULL = FLAT, (100, 105, 100, 105)
C3_BULL = (104, 106, 103, 105)              # bull zone (101, 103), born idx17
FILLER = (104, 105, 103, 104)
C1_BEAR, C2_BEAR = (103, 104, 102, 103), (103, 103.5, 101.5, 102)
C3_BEAR = (101.1, 101.2, 100.5, 101.1)      # bear zone (101.2, 102), born idx21
TOUCH = (101.5, 101.6, 101.4, 101.5)        # closes inside overlap (101.2, 102)
KILL = (102.3, 105, 102.3, 105)             # close 105 > bear.hi(102): kills bear

BARS_A = [FLAT] * 16 + [C1_BULL, C2_BULL, C3_BULL, FILLER,
                        C1_BEAR, C2_BEAR, C3_BEAR, TOUCH]

# ---- Case B: bear FVG (older) x bull FVG (newer) -> LONG ----
C1_BR, C2_BR, C3_BR = (103, 104, 103, 103), (103, 103, 98, 98), (99, 101, 97, 99)
# bear zone (101, 103), born idx17
C1_BU, C2_BU = (100.5, 101.2, 100, 100.8), (100.8, 103, 100.5, 102.5)
C3_BU = (102, 103, 102, 102.5)              # bull zone (101.2, 102), born idx20
TOUCH2 = (101.4, 101.6, 101.3, 101.5)       # closes inside overlap (101.2, 102)

BARS_B = [FLAT] * 16 + [C1_BR, C2_BR, C3_BR, C1_BU, C2_BU, C3_BU, TOUCH2]


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def make_store(bars):
    store = CandleStore("/nonexistent")
    for i, (o, h, l, c) in enumerate(bars):
        store.add(Candle("X", Timeframe.M1, bar_ts(i),
                         tick(o), tick(h), tick(l), tick(c), 10))
    return store


def ctx_at(store, n_bars):
    now = bar_ts(n_bars)  # first n_bars M5 bars are closed
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


def run_to(det, store, upto):
    """Replay every tick 1..upto in order (state is incremental/streaming)
    and return the evidence from the last (upto-th) tick."""
    out = []
    for n in range(1, upto + 1):
        out = det.detect(ctx_at(store, n))
    return out


def test_bull_older_bear_newer_fires_short_sl_hi():
    store = make_store(BARS_A)
    [ev] = run_to(BprDetector({}), store, 24)
    assert ev.detector == "bpr"
    assert ev.direction is Direction.SHORT
    assert ev.zone == (tick("101.2"), tick(102))     # overlap region
    floor = str(Decimal("0.15") * ctx_at(store, 24).atr(M5))
    assert ev.meta == {"event": "BPR", "sl": str(tick(102)),  # sl = overlap hi
                       "sl_floor": floor}
    assert ev.ttl_candles == 4
    assert 0.0 <= ev.strength <= 1.0


def test_bear_older_bull_newer_fires_long_sl_lo():
    store = make_store(BARS_B)
    n = len(BARS_B)
    [ev] = run_to(BprDetector({}), store, n)
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick("101.2"), tick(102))
    floor = str(Decimal("0.15") * ctx_at(store, n).atr(M5))
    assert ev.meta == {"event": "BPR", "sl": str(tick("101.2")),  # sl = overlap lo
                       "sl_floor": floor}


def test_no_overlap_no_signal():
    """Disjoint bull/bear zones, injected directly (mirrors test_fvg.py's
    direct-Level-construction BPR tests): lo > hi on intersection -> skip."""
    store = make_store([FLAT, FLAT, TOUCH])  # 3 bars: atr is None, no new gaps
    det = BprDetector({})
    det._gaps = [_Gap(bar_ts(0), tick(101), tick(103), True),
                _Gap(bar_ts(1), tick(90), tick(95), False)]
    assert det.detect(ctx_at(store, 3)) == []


def test_dead_gap_not_paired():
    # Same as Case A, but a KILL candle (close 105 > bear.hi 102) breaks the
    # bear gap's far edge before TOUCH -> no BPR even though TOUCH's close
    # still sits inside the geometric overlap.
    bars = [FLAT] * 16 + [C1_BULL, C2_BULL, C3_BULL, FILLER,
                          C1_BEAR, C2_BEAR, C3_BEAR, KILL, TOUCH]
    store = make_store(bars)
    assert run_to(BprDetector({}), store, 25) == []


def test_no_lookahead_before_touch_bar_closes():
    store = make_store(BARS_A)
    assert run_to(BprDetector({}), store, 23) == []  # TOUCH (idx23) not closed


def test_dedupe_once_per_pair():
    store = make_store(BARS_A)
    det = BprDetector({})
    [ev] = run_to(det, store, 24)
    assert det.detect(ctx_at(store, 24)) == []  # same tick again: no duplicate


def test_on_session_end_keeps_live_gaps_and_fired_pairs():
    # Continuum: live gaps are structure and carry across days; fired pairs
    # referencing them stay deduped. Only dead gaps/orphaned pairs prune.
    store = make_store(BARS_A)
    det = BprDetector({})
    run_to(det, store, 24)
    live, fired = list(det._gaps), set(det._fired)
    det.on_session_end()
    assert det._gaps == live and det._fired == fired  # both gaps live: all kept
    assert det.detect(ctx_at(store, 24)) == []        # still deduped: no re-fire
    det._gaps[0].dead = True                          # kill the bull gap
    det.on_session_end()
    assert det._gaps == live[1:]                      # dead gap + its pair pruned
    assert det._fired == set()


def test_continuum_cross_day_bear_gap_fires():
    """CONTINUUM (validated): same candle content/order as BARS_A, except
    C1_BEAR/C2_BEAR close out day 1 and C3_BEAR/TOUCH open day 2. The
    ict_pieces.py reference ran one concatenated series, so the bear FVG
    forms from the boundary-spanning triad, pairs with day 1's live bull
    gap, and TOUCH fires the same SHORT BPR as the single-day test."""
    day1 = SESSION_START
    day2 = day1 + timedelta(days=1)
    day1_bars = [FLAT] * 16 + [C1_BULL, C2_BULL, C3_BULL, FILLER, C1_BEAR, C2_BEAR]
    day2_bars = [C3_BEAR, TOUCH]
    store = CandleStore("/nonexistent")
    for i, (o, h, l, c) in enumerate(day1_bars):
        store.add(Candle("X", Timeframe.M1, day1 + timedelta(minutes=5 * i),
                         tick(o), tick(h), tick(l), tick(c), 10))
    for i, (o, h, l, c) in enumerate(day2_bars):
        store.add(Candle("X", Timeframe.M1, day2 + timedelta(minutes=5 * i),
                         tick(o), tick(h), tick(l), tick(c), 10))

    det = BprDetector({})
    for n in range(1, len(day1_bars) + 1):
        now = day1 + timedelta(minutes=5 * n)
        det.detect(StockContext(symbol="X", now=now, candles=store.view("X", now),
                                levels=[], evidence_history=[],
                                day=DayState(session_date=now.date())))
    assert any(not g.dead and g.bull for g in det._gaps)  # day-1 bull gap live
    det.on_session_end()                                  # bull gap must survive

    out = []
    for n in range(1, len(day2_bars) + 1):
        now = day2 + timedelta(minutes=5 * n)
        out = det.detect(StockContext(symbol="X", now=now, candles=store.view("X", now),
                                      levels=[], evidence_history=[],
                                      day=DayState(session_date=now.date())))
    assert any(not g.dead and not g.bull for g in det._gaps)  # boundary bear gap formed
    [ev] = out                                # day-1 bull x boundary bear -> SHORT
    assert ev.direction is Direction.SHORT
    assert ev.zone == (tick("101.2"), tick(102))
    assert ev.meta["sl"] == str(tick(102))


# --------------------------------------------------------------------------
# PARITY GATE -- fidelity vs ict_pieces.py::bpr on real continuum data.
# Pattern: test_inducement.py's parity test (inlined verbatim oracle,
# tick-by-tick feed, exact-match assertion).
# --------------------------------------------------------------------------
_DIR = {1: Direction.LONG, -1: Direction.SHORT}
REAL_SYMBOLS = ("RELIANCE", "INFY")  # LTIM/TATAMOTORS: empty CSVs in this fixture


def _data_wide_dir() -> Path | None:
    """Absolute path to the repo's data/wide fixture. It is untracked and
    lives only in the MAIN worktree checkout, not this (or any) `git
    worktree`, so resolve it via git's common dir rather than a path
    relative to this file."""
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=Path(__file__).resolve().parent, capture_output=True, text=True,
            check=True, timeout=5).stdout.strip()
    except Exception:
        return None
    d = Path(common).parent / "data" / "wide"
    return d if d.is_dir() else None


DATA_WIDE = _data_wide_dir()


def _ref_find_gaps(m5, atrs):
    """Verbatim ict_pieces.py::find_gaps -- fidelity ORACLE for bpr parity."""
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; z = []
    for i in range(2, len(m5)):
        a = atrs[i]
        if a is None: continue
        need = 0.3 * float(a)
        if L[i] > H[i - 2] and (L[i] - H[i - 2]) >= need: z.append((i - 1, H[i - 2], L[i], 1))
        if H[i] < L[i - 2] and (L[i - 2] - H[i]) >= need: z.append((i - 1, H[i], L[i - 2], -1))
    return z


def _ref_bpr(m5, atrs):
    """Verbatim ict_pieces.py::bpr -- fidelity ORACLE for bpr parity."""
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; C = [float(c.close) for c in m5]
    gaps = _ref_find_gaps(m5, atrs)
    bulls = [g for g in gaps if g[3] == 1]; bears = [g for g in gaps if g[3] == -1]
    die = {}
    for g in gaps:
        born, lo, hi, dr = g
        die[g] = next((j for j in range(born + 1, len(m5))
                       if (C[j] < lo if dr == 1 else C[j] > hi)), len(m5))
    ev = []
    for bb in bulls:
        for br in bears:
            lo = max(bb[1], br[1]); hi = min(bb[2], br[2])
            if lo > hi: continue
            start = max(bb[0], br[0]) + 1; end = min(die[bb], die[br])
            newer_dr = 1 if bb[0] > br[0] else -1
            for k in range(start, end):
                if L[k] <= hi and H[k] >= lo and lo <= C[k] <= hi:
                    ev.append((k, newer_dr, lo if newer_dr == 1 else hi))
                    break
    return ev


def _load_m1_real(symbol: str) -> list[Candle]:
    return FileFeed(DATA_WIDE)._load_candles(symbol)


def _build_m5_real(m1: list[Candle], symbol: str) -> list[Candle]:
    """Full continuum M5 series (session-anchored, all days concatenated),
    built the same way production does (CandleStore bucketing) so bar
    boundaries are byte-identical to the tick-fed detector's."""
    store = CandleStore("/nonexistent")
    for c in m1:
        store.add(c)
    view = store.view(symbol, m1[-1].ts + timedelta(days=1))
    return view.last(1_000_000, M5)


def _feed_real(m1: list[Candle], symbol: str, det, spec=NSE) -> list[tuple]:
    """Feed M1 candles tick by tick (session-anchored M5, exactly as
    SymbolPipeline.on_m1 drives closed-M5 detection): det.detect() at every
    M5 close, det.on_session_end() at every session boundary; flush the
    final pending bucket at the end (fair for a fixed-length replay -- live
    production only closes it once a NEXT tick arrives, which never comes
    for the last bar of a finite CSV). Returns [(bar_ts, Evidence), ...]
    keyed by the CLOSED bar's own ts (ev.ts stamps the close INSTANT =
    bar_ts + 5m, one bar later -- see ``_ref_bpr``'s touch-bar convention)."""
    store = CandleStore("/nonexistent")
    last_bucket = session_date = None
    out: list[tuple] = []

    def _flush(stop_bucket):
        nonlocal last_bucket
        if last_bucket is None:
            return
        t = last_bucket + timedelta(minutes=5)
        stop = min(stop_bucket, spec.session_open_dt(last_bucket)
                   + timedelta(minutes=spec.session_minutes))
        while t <= stop:
            ctx = StockContext(symbol=symbol, now=t, candles=store.view(symbol, t),
                               levels=[], evidence_history=[],
                               day=DayState(session_date=t.date()))
            for ev in det.detect(ctx):
                out.append((t - timedelta(minutes=5), ev))
            t += timedelta(minutes=5)

    for c in m1:
        bucket = _bucket_start(c.ts, M5, spec)
        if last_bucket is not None and bucket != last_bucket:
            _flush(bucket)
        if session_date is not None and c.ts.date() != session_date:
            det.on_session_end()
        session_date = c.ts.date()
        store.add(c)
        last_bucket = bucket
    _flush(last_bucket + timedelta(minutes=5))
    return out


@pytest.mark.skipif(DATA_WIDE is None, reason="data/wide real-data fixture not available")
def test_parity_with_reference_on_real_continuum_data():
    """PARITY GATE vs ict_pieces.py::bpr, session-anchored M5, ALL sessions
    concatenated (continuum -- exactly how ict_pieces.py validated the
    edge), across 2 real symbols. Exact match expected: gap formation and
    the overlap/touch check both read ``atr``/the newest closed bar at the
    CURRENT tick on both the detector and the reference side (no
    formation-vs-touch ATR-timing gap like mitigation's), so there is no
    documented-allowed remainder here."""
    expected, got = set(), set()
    for sym in REAL_SYMBOLS:
        m1 = _load_m1_real(sym)
        m5 = _build_m5_real(m1, sym)
        atrs = atr_series(m5)
        for k, d, sl in _ref_bpr(m5, atrs):
            expected.add((sym, m5[k].ts, _DIR[d], Decimal(str(sl))))
        det = BprDetector({})
        for ts, ev in _feed_real(m1, sym, det):
            got.add((sym, ts, ev.direction, Decimal(ev.meta["sl"])))

    assert got == expected
    # guard: the real data must actually exercise the machine non-trivially
    assert len(expected) >= 30
    assert {sym for sym, *_ in expected} == set(REAL_SYMBOLS)
    assert {d for _, _, d, _ in expected} == {Direction.LONG, Direction.SHORT}
