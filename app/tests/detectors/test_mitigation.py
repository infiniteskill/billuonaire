"""Tests for the mitigation detector (trader/detectors/mitigation.py).
Binding design: v2-task6 brief (faithful port of ict_pieces.py::
mitigation_block) -- BODY-only zone (min(O,C), max(O,C)) of the last
opposite-color candle immediately before a qualifying displacement leg (no
intervening opposite candle across the lookback window); first return-touch
after the lookback window closed fires the signal. Pure signal-emitter, no
Levels.

Fixture geometry: one M1 candle per M5 bucket start -> the derived M5 bar
equals it exactly. Every candle before the touch bar keeps range==2 and
open == previous close, so ATR(M5,14) == 2 exactly once 15 candles have
closed and stays 2 through block formation (need = disp_atr(1.0) * 2 = 2)."""

import subprocess
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.mitigation import MitigationDetector
from trader.engine.context import DayState, StockContext
from trader.feed.file import FileFeed
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.market import NSE
from trader.store.candles import CandleStore, _bucket_start
from trader.tools.study import atr_series

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M1, M5 = Timeframe.M1, Timeframe.M5

FLAT = (100, 101, 99, 100)  # doji, TR=2, primes ATR(M5,14) == 2

# --- LONG fixture: bearish block candle then a qualifying up-displacement ---
BLOCK_L = (100, "100.5", "98.5", 99)     # bearish, body/zone (99, 100)
SEG_L1 = (99, "100.5", "98.5", 100)      # bullish, diff +1
SEG_L2 = (100, "101.5", "99.5", 101)     # bullish, diff +2
SEG_L3 = (101, "102.5", "100.5", 102)    # bullish, diff +3 (max disp)
TOUCH_L = (102, "102.5", 97, 98)         # dips through zone (99,100); low=97 < block low 98.5

# --- SHORT mirror: bullish block candle then a qualifying down-displacement ---
BLOCK_S = (100, "101.5", "99.5", 101)    # bullish, body/zone (100, 101)
SEG_S1 = (101, "101.5", "99.5", 100)     # bearish, diff -1
SEG_S2 = (100, "100.5", "98.5", 99)      # bearish, diff -2
SEG_S3 = (99, "99.5", "97.5", 98)        # bearish, diff -3 (max disp)
TOUCH_S = (98, "103.5", "97.5", 103)     # spans through zone (100,101); high=103.5 > block high 101.5

# --- intervening opposite candle: SEG_L2 replaced by a down-candle -> no block ever ---
SEG_BAD = (100, "100.5", "98.5", 99)     # down candle inside the LONG lookback window

# --- displacement below threshold: max diff 1.5 < need 2 -> no block ---
SEG_T1 = (99, "100.5", "98.5", "99.5")
SEG_T2 = ("99.5", "100.5", "98.5", 100)
SEG_T3 = (100, "101.5", "99.5", "100.5")


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def bar(i, o, h, l, c, v=10):
    return Candle("X", M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_store(bars):
    store = CandleStore("/nonexistent")
    for i, b in enumerate(bars):
        store.add(bar(i, *b))
    return store


def ctx_at(store, n_bars):
    now = bar_ts(n_bars)
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


def long_bars(seg2=SEG_L2):
    return [FLAT] * 15 + [BLOCK_L, SEG_L1, seg2, SEG_L3, TOUCH_L]


def short_bars():
    return [FLAT] * 15 + [BLOCK_S, SEG_S1, SEG_S2, SEG_S3, TOUCH_S]


def test_long_block_body_retest_correct_sl():
    store = make_store(long_bars())
    det = MitigationDetector({})
    assert det.detect(ctx_at(store, 19)) == []  # block forms here (clean ATR=2), no touch yet
    [ev] = det.detect(ctx_at(store, 20))
    assert ev.detector == "mitigation"
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick(99), tick(100))
    assert ev.meta == {"event": "MITIGATION",
                       "sl": str(tick(97)),  # min(block.low=98.5, touch.low=97)
                       "sl_floor": str(Decimal("0.15") * ctx_at(store, 20).atr(M5))}
    assert ev.ttl_candles == 6
    assert ev.strength == 0.5  # (disp=3 - need=2) / need=2, clamped [0,1]


def test_short_block_mirror():
    store = make_store(short_bars())
    det = MitigationDetector({})
    assert det.detect(ctx_at(store, 19)) == []  # block forms here (clean ATR=2), no touch yet
    [ev] = det.detect(ctx_at(store, 20))
    assert ev.direction is Direction.SHORT
    assert ev.zone == (tick(100), tick(101))
    # max(block.high=101.5, touch.high=103.5)
    assert ev.meta["sl"] == str(tick("103.5"))
    assert ev.meta["sl_floor"] == str(Decimal("0.15") * ctx_at(store, 20).atr(M5))
    assert ev.strength == 0.5


def test_intervening_opposite_candle_blocks_formation():
    store = make_store(long_bars(seg2=SEG_BAD))
    det = MitigationDetector({})
    assert det.detect(ctx_at(store, 19)) == []
    assert det.detect(ctx_at(store, 20)) == []  # touch bar closed, still no block ever formed


def test_displacement_below_threshold_no_block():
    bars = [FLAT] * 15 + [BLOCK_L, SEG_T1, SEG_T2, SEG_T3, TOUCH_L]
    store = make_store(bars)
    det = MitigationDetector({})
    assert det.detect(ctx_at(store, 19)) == []
    assert det.detect(ctx_at(store, 20)) == []


def test_no_lookahead():
    store = make_store(long_bars())
    det = MitigationDetector({})
    for n in (16, 17, 18, 19):  # lookback window (+ block confirm) not fully closed / no touch yet
        assert det.detect(ctx_at(store, n)) == []
    [ev] = det.detect(ctx_at(store, 20))  # touch bar now closed
    assert ev.direction is Direction.LONG


def test_dedupe_one_fire_per_block():
    store = make_store(long_bars())
    det = MitigationDetector({})
    det.detect(ctx_at(store, 19))  # block forms here
    [ev] = det.detect(ctx_at(store, 20))
    assert det.detect(ctx_at(store, 20)) == []  # same tick again: no duplicate


def test_on_session_end_keeps_pending_blocks():
    # Continuum: a block formed but not yet touched carries across the
    # boundary and fires on the next session's touch; _seen is age-pruned.
    store = make_store(long_bars())
    det = MitigationDetector({})
    det.detect(ctx_at(store, 19))         # block forms, no touch yet
    assert det._blocks
    det.on_session_end()
    assert det._blocks                    # pending block carried
    assert len(det._seen) <= 5            # lookback + 2 newest ts kept
    [ev] = det.detect(ctx_at(store, 20))  # next-session touch still fires
    assert ev.direction is Direction.LONG
    assert ev.meta["sl"] == str(tick(97))


def test_atr_spike_ages_out_no_stale_touch():
    """A volatility spike inflates ATR so the block candidate fails its
    displacement check at its one true formation tick (disp=3 < need~5.4).
    Later the spike ages out of the ATR(14) window and ATR relaxes back to
    2 (need=2 < disp=3) -- old (bounded-rescan) behaviour would retry the
    stale candle then and stamp a ~40-min-old touch with ts=ctx.now. Fixed
    behaviour: that one tick was the block's only shot: reject-once is
    permanent, so no signal -- stale or otherwise -- ever appears, even
    though a real overlapping "touch" candle (DIP_TOUCH) is sitting right
    there in history the whole time."""
    FLAT2 = (100, 101, 99, 100)          # TR=2, primes ATR=2
    SPIKE = (100, 140, 90, 100)          # TR=50 -- temporarily inflates ATR
    BLOCK = (100, "100.5", "98.5", 99)   # bearish, body/zone (99, 100)
    SEG1 = (99, "100.5", "98.5", 100)
    SEG2 = (100, "101.5", "99.5", 101)
    SEG3 = (101, "102.5", "100.5", 102)  # max disp = 3 vs blk.close
    COAST = (102, 103, 101, 102)
    DIP_TOUCH = (102, "102.5", "99.5", 102)  # overlaps zone (99, 100)

    bars = ([FLAT2] * 14 + [SPIKE] + [BLOCK] + [SEG1, SEG2, SEG3]
             + [COAST] + [DIP_TOUCH] + [COAST] * 9)  # spike ages out of ATR(14) by n=30
    store = make_store(bars)
    det = MitigationDetector({})

    for n in range(15, len(bars) + 1):
        assert det.detect(ctx_at(store, n)) == []
        assert det._blocks == {}  # never persisted -> never a late/stale touch


def test_continuum_cross_day_block_fires():
    """CONTINUUM (validated): BLOCK_L is day 1's last candle; SEG_L1..3 (the
    displacement leg) and TOUCH_L open day 2 -- byte-identical content to
    long_bars()'s tick-19 window, just split across the session boundary.
    ict_pieces.py ran one concatenated series, so the leg legitimately spans
    the gap: BLOCK_L forms once its boundary-spanning displacement window
    closes, and TOUCH_L fires the same LONG as the single-day test."""
    day1 = SESSION_START
    day2 = day1 + timedelta(days=1)
    store = CandleStore("/nonexistent")
    for i, b in enumerate([FLAT] * 15 + [BLOCK_L]):
        store.add(bar(i, *b))
    for i, (o, h, l, c) in enumerate([SEG_L1, SEG_L2, SEG_L3, TOUCH_L]):
        store.add(Candle("X", M1, day2 + timedelta(minutes=5 * i),
                         tick(o), tick(h), tick(l), tick(c), 10))

    det = MitigationDetector({})
    det.on_session_end()                   # boundary hook must not blind day 2
    out = []
    for n in range(1, 5):
        now = day2 + timedelta(minutes=5 * n)
        out = det.detect(StockContext(symbol="X", now=now, candles=store.view("X", now),
                                      levels=[], evidence_history=[],
                                      day=DayState(session_date=now.date())))
    [ev] = out                             # cross-session block + touch fires
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick(99), tick(100))
    assert ev.meta["sl"] == str(tick(97))


# --------------------------------------------------------------------------
# PARITY GATE -- fidelity vs ict_pieces.py::mitigation_block on real
# continuum data. Pattern: test_inducement.py's parity test (inlined
# verbatim oracle, tick-by-tick feed) -- but NOT an exact-match assertion
# (see the test's own docstring for why, and how the remainder is verified).
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


def _ref_mitigation_block(m5, atrs, disp_atr=1.0, lookback=3):
    """Verbatim ict_pieces.py::mitigation_block -- fidelity ORACLE. Returns
    [(block_i, touch_k, sign, sl)]; block_i is kept (the source only returns
    touch_k) so divergences can be traced back to their forming candidate."""
    O = [float(c.open) for c in m5]; H = [float(c.high) for c in m5]
    L = [float(c.low) for c in m5]; C = [float(c.close) for c in m5]
    ev = []
    for sign in (1, -1):
        for i in range(1, len(m5) - lookback):
            down = C[i] < O[i] if sign == 1 else C[i] > O[i]
            if not down: continue
            seg = range(i + 1, i + 1 + lookback)
            if any((C[j] < O[j]) if sign == 1 else (C[j] > O[j]) for j in seg): continue
            a = atrs[i]
            if a is None: continue
            disp = max((C[j] - C[i]) * sign for j in seg)
            if disp < disp_atr * float(a): continue
            lo, hi = min(O[i], C[i]), max(O[i], C[i])
            for k in range(i + 1 + lookback, len(m5)):
                if L[k] <= hi and H[k] >= lo:
                    sl = min(L[i], L[k]) if sign == 1 else max(H[i], H[k])
                    ev.append((i, k, sign, sl))
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
    """Like test_bpr.py's harness, but also traces WHICH pending block
    resolved each emitted touch (by diffing det._blocks before/after
    detect()), so a divergence can be attributed to a specific block
    candidate. Returns [(bar_ts, block_ts, Evidence), ...]."""
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
            pending = dict(det._blocks)
            for ev in det.detect(ctx):
                sign = 1 if ev.direction is Direction.LONG else -1
                blk_ts = next(ts for ts, (s, *_) in pending.items()
                             if s == sign and ts not in det._blocks)
                out.append((t - timedelta(minutes=5), blk_ts, ev))
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


def _explained(m5, atrs, i, sign, lookback=3, disp_atr=1.0) -> bool:
    """Every divergence between the (Decimal, single-eval) detector and the
    (float, full-rescan) reference must trace to one of two unavoidable
    consequences of that port, never to an unrelated logic bug:

    (a) DIFFERENT-BAR ATR: the reference always thresholds with atrs[i] (the
        block's OWN bar). ``mitigation.py``'s ``_atr_of`` recomputes the same
        ATR ending at the block's own close, so this should not fire on
        current code -- kept as a live, programmatic guard against a future
        regression back to using the current-tick's (later) ATR.
    (b) FLOAT/DECIMAL BOUNDARY TIE: with the SAME atrs[i], Decimal-exact
        arithmetic (what the production detector uses) and ict_pieces' float
        arithmetic can disagree only when disp==need to the last
        representable digit -- i.e. only ever an exact tie, never a
        meaningfully different number.
    """
    C = [c.close for c in m5]  # Decimal, exact (unlike the float oracle's C)
    seg = range(i + 1, i + 1 + lookback)
    disp_dec = max((C[j] - C[i]) * sign for j in seg)
    a_i = atrs[i]
    T = i + lookback
    a_T = atrs[T] if T < len(atrs) else None
    if a_i != a_T:
        return True                                     # (a)
    if a_i is None:
        return False
    need_dec = Decimal(str(disp_atr)) * a_i
    exact_pass = disp_dec >= need_dec
    float_pass = float(disp_dec) >= disp_atr * float(a_i)
    return exact_pass != float_pass                      # (b)


@pytest.mark.skipif(DATA_WIDE is None, reason="data/wide real-data fixture not available")
def test_parity_with_reference_on_real_continuum_data():
    """PARITY GATE vs ict_pieces.py::mitigation_block, session-anchored M5,
    ALL sessions concatenated (continuum), across 2 real symbols.

    NOT an exact match by design: the detector is bounded single-eval (each
    block candidate is judged ONCE, at its natural formation tick) to fix a
    stale-touch bug (see test_atr_spike_ages_out_no_stale_touch) where the
    OLD behaviour kept retrying a rejected candidate against ever-later ATR
    readings. The reference has no such tick discipline: it is a single
    batch pass that always thresholds a candidate against ITS OWN bar's
    atrs[i]. The detector matches that exactly (mitigation.py's ``_atr_of``
    recomputes the ATR ending at the block's own close, not the current
    tick's), so on real data the two are near-exact; the residual
    divergence, in EITHER direction, is verified below -- never hand-waved
    -- to be fully explained by ``_explained``'s two categories (a stale
    different-bar ATR that no longer occurs post-fix, kept as a live
    regression guard, or a float/Decimal exact-tie artifact of comparing a
    float reference against a Decimal production detector)."""
    total_expected = total_got = 0
    for sym in REAL_SYMBOLS:
        m1 = _load_m1_real(sym)
        m5 = _build_m5_real(m1, sym)
        atrs = atr_series(m5)
        ts_index = {c.ts: idx for idx, c in enumerate(m5)}

        ref_ev = _ref_mitigation_block(m5, atrs)
        expected = {(m5[k].ts, _DIR[sign], Decimal(str(sl))): i
                    for i, k, sign, sl in ref_ev}

        det = MitigationDetector({})
        got = {(ts, ev.direction, Decimal(ev.meta["sl"])): ts_index[blk_ts]
               for ts, blk_ts, ev in _feed_real(m1, sym, det)}

        det_only, ref_only = set(got) - set(expected), set(expected) - set(got)
        for key in det_only:
            i, sign = got[key], key[1].value
            assert _explained(m5, atrs, i, sign), f"{sym}: unexplained det-only {key}"
        for key in ref_only:
            i, sign = expected[key], key[1].value
            assert _explained(m5, atrs, i, sign), f"{sym}: unexplained ref-only {key}"

        total_expected += len(expected)
        total_got += len(got)

    # guard: the real data must actually exercise the machine non-trivially,
    # and near-exactly (any explained remainder is a handful of bars, not a
    # large fraction of the event set)
    assert total_expected >= 150 and total_got >= 150
    assert abs(total_got - total_expected) <= 5
