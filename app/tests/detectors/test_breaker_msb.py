"""Tests for the breaker_msb detector (trader/detectors/breaker_msb.py).

Binding spec: the research implementation that measured the +19.6pp 5m
hit-edge -- scratchpad pine_det.py::emrekb_events, tag "brk_bb" (EmreKb
"MSB-OB" Pine, dev/h2h/2.txt). Zigzag(zz) alternating swings; bearish MSB
when market==1 and l0 < l1 - |h0 - l1| * fib (bullish mirrored); the BREAKER
box exists only when the older swing was SWEPT (bear: h0 > h1, bull:
l0 < l1) and is the full range of the last same-direction candle in
[older-swing-bar - zz, older-opposite-swing-bar]; entry = first LATER close
back inside the box, once per box; the box dies on a close beyond its far
edge (checked before entry, so a box can die the bar it is born).

Two layers (test_inducement.py pattern):

* hand fixtures at zz=3 / warm=0 (the machine is length-parametric, so the
  same code paths run at a human-traceable size) pin happy paths in both
  directions with the exact meta/zone/sl, invalidation, no-lookahead,
  per-box dedupe, per-tick collapse and session behavior;

* PARITY GATE: a verbatim inlined copy of pine_det.py::emrekb_events (only
  WARM lifted to a param and the box-origin bar index passed through -- no
  behavior change) is the fidelity ORACLE, run over RELIANCE + INFY from
  data/long5m against the detector fed tick-by-tick.
"""

import csv
import subprocess
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from trader.detectors.breaker_msb import BreakerMsbDetector, _Box
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5
PARAMS = {"tf": "5m", "zz": 3, "warm": 0}
_DIR = {1: Direction.LONG, -1: Direction.SHORT}

FLAT = (100, 101, 99, 100)  # zz=3 zigzag flips every flat bar; no MSB (l0 == l1)

# Oracle-verified (scratchpad fixture_design.py): bearish MSB at bar 24 forms
# the SHORT breaker from bar 17 (the last down candle in [h1i-3, l1i]), zone
# (100.5, 103.5); bar 25 closes 103 back inside -> SHORT fires at 25.
SHORT_BARS = [FLAT] * 14 + [
    (100, 103, 100, 102),        # 14 up-leg
    (102, 105, 102, 104),        # 15 h1 = 105
    (104, 104.5, 102.5, 103),    # 16 down
    (103, 103.5, 100.5, 101),    # 17 down -> the breaker candle (100.5, 103.5)
    (101, 104, 100, 103.5),      # 18 up
    (103.5, 106, 103, 105.5),    # 19 h0 = 106 sweeps h1
    (105.5, 105.5, 101, 101.5),  # 20 crash
    (101.5, 102, 97.5, 98),      # 21 l0 breaks l1 with fib margin
    (98, 99, 96.5, 97),          # 22 low confirms
    (97, 100, 96.8, 99.5),       # 23 rally
    (99.5, 102, 99, 101.5),      # 24 MSB fires; box born (no same-bar entry)
    (101.5, 103.2, 101, 103),    # 25 close 103 inside (100.5, 103.5] -> SHORT
]
# Close 104 > top 103.5 kills the box BEFORE any entry; the later close back
# inside the (dead) zone must not fire.
INVAL_BARS = SHORT_BARS[:25] + [
    (101.5, 104.5, 101, 104),    # 25 far-edge close: box dies
    (104, 104.2, 102, 103),      # 26 inside the dead zone -> nothing
]
# Oracle-verified continuation: bullish MSB at bar 33 forms the LONG breaker
# from bar 25 (last up candle in [l1i-3, h1i]), zone (101.0, 103.2); bar 34
# closes 102 back inside -> LONG fires at 34.
LONG_BARS = SHORT_BARS + [
    (103, 103.5, 99.5, 100),     # 26 turn down
    (100, 100.5, 96, 96.5),      # 27 l0' = 96 sweeps l1' = 96.5
    (96.5, 99, 96.2, 98.5),      # 28 reverse up
    (98.5, 103, 98, 102.5),      # 29 drive
    (102.5, 106.5, 102, 106),    # 30 structure breaks up with fib margin
    (106, 107.5, 105.5, 107),    # 31 extend
    (107, 107.2, 104, 104.5),    # 32 pull back
    (104.5, 105, 102.5, 103),    # 33 MSB fires; box born
    (103, 103.5, 101.5, 102),    # 34 close 102 inside [101.0, 103.2) -> LONG
]
DEDUPE_BARS = SHORT_BARS + [(103, 103.4, 102.5, 103.2)]  # 26 inside again


def _ctx(store, now, sym="X"):
    return StockContext(symbol=sym, now=now, candles=store.view(sym, now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


def _feed(bars, det, breaks=()):
    """One closed M5 bar per tick (M1 == M5 fixture convention, test_bpr.py);
    the session day rolls over at each bar index in ``breaks`` (with
    ``on_session_end`` there). Returns [(bar_index, Evidence, fire ctx)]."""
    store = CandleStore("/nonexistent")
    out, day, k0 = [], 0, 0
    for k, (o, h, l, c) in enumerate(bars):
        if k in breaks:
            det.on_session_end()
            day, k0 = day + 1, k
        ts = SESSION_START + timedelta(days=day, minutes=5 * (k - k0))
        store.add(Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(l), tick(c), 10))
        ctx = _ctx(store, ts + timedelta(minutes=5))
        out += [(k, ev, ctx) for ev in det.detect(ctx)]
    return out


# --------------------------------------------------------------------------
# Happy paths / meta contract / invalidation / no-lookahead / dedupe
# --------------------------------------------------------------------------
def test_short_breaker_happy_path_exact_meta():
    [(k, ev, ctx)] = _feed(SHORT_BARS, BreakerMsbDetector(PARAMS))
    assert k == 25 and ev.detector == "breaker_msb"
    assert ev.direction is Direction.SHORT
    assert ev.zone == (tick("100.5"), tick("103.5"))
    assert ev.strength == 0.8 and ev.ttl_candles == 4 and ev.ts == ctx.now
    floor = str(Decimal("0.15") * ctx.atr(M5))
    assert ev.meta == {"event": "BREAKER_MSB", "sl": str(tick("103.5")),
                       "sl_floor": floor}  # sl = box top, the SHORT kill edge


def test_long_breaker_happy_path_exact_meta():
    evs = _feed(LONG_BARS, BreakerMsbDetector(PARAMS))
    assert [(k, e.direction) for k, e, _ in evs] == \
        [(25, Direction.SHORT), (34, Direction.LONG)]
    _, ev, ctx = evs[1]
    assert ev.zone == (tick(101), tick("103.2"))
    floor = str(Decimal("0.15") * ctx.atr(M5))
    assert ev.meta == {"event": "BREAKER_MSB", "sl": str(tick(101)),
                       "sl_floor": floor}  # sl = box bot, the LONG kill edge


def test_far_edge_close_invalidates_box():
    assert _feed(INVAL_BARS, BreakerMsbDetector(PARAMS)) == []


def test_no_lookahead_nothing_before_entry_close():
    det = BreakerMsbDetector(PARAMS)
    assert _feed(SHORT_BARS[:25], det) == []          # entry bar not closed yet
    assert [b.fired for b in det._boxes] == [False]   # box pending, not fired


def test_dedupe_box_fires_once():
    evs = _feed(DEDUPE_BARS, BreakerMsbDetector(PARAMS))
    assert [(k, e.direction) for k, e, _ in evs] == [(25, Direction.SHORT)]


def test_same_tick_redetect_and_batch_catchup():
    # One detect() over the whole closed history (catch-up) equals the
    # tick-by-tick run; a second call at the same tick emits nothing new.
    store = CandleStore("/nonexistent")
    for k, (o, h, l, c) in enumerate(SHORT_BARS):
        ts = SESSION_START + timedelta(minutes=5 * k)
        store.add(Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(l), tick(c), 10))
    det = BreakerMsbDetector(PARAMS)
    ctx = _ctx(store, ts + timedelta(minutes=5))
    assert [e.direction for e in det.detect(ctx)] == [Direction.SHORT]
    assert det.detect(ctx) == []


def test_collapse_two_boxes_same_close_single_evidence():
    # Two live same-direction boxes catch the SAME close in one tick -- one
    # physical price event; the tighter zone wins (constant strength).
    det = BreakerMsbDetector(PARAMS)
    det._boxes = [_Box(tick(104), tick(100), -1, 0),
                  _Box(tick("103.5"), tick(101), -1, 0)]
    [(k, ev, _)] = _feed([FLAT, FLAT, (100, 103, 100, 102.5)], det)
    assert k == 2 and ev.direction is Direction.SHORT
    assert ev.zone == (tick(101), tick("103.5"))


def test_session_boundary_continuum_then_dedupe_prune():
    # Continuum: a pending box carries across the session break and still
    # fires; on_session_end prunes ONLY fired boxes (per-box dedupe memory).
    det = BreakerMsbDetector(PARAMS)
    evs = _feed(SHORT_BARS, det, breaks={25})
    assert [(k, e.direction) for k, e, _ in evs] == [(25, Direction.SHORT)]
    assert [b.fired for b in det._boxes] == [True]
    det.on_session_end()
    assert det._boxes == []


def test_default_params():
    assert BreakerMsbDetector({}).params == {
        "tf": "5m", "zz": 9, "fib": 0.33, "warm": 25, "sl_atr_floor": 0.15}


# --------------------------------------------------------------------------
# PARITY GATE -- fidelity vs pine_det.py::emrekb_events (tag brk_bb) on real
# continuum data. Pattern: test_inducement.py / test_bpr.py parity oracle.
# --------------------------------------------------------------------------
REAL_SYMBOLS = ("RELIANCE", "INFY")


def _long5m_dir() -> Path | None:
    """data/long5m lives only in the MAIN checkout (untracked), so resolve it
    via git's common dir -- worktree-safe (test_bpr.py pattern)."""
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=Path(__file__).resolve().parent, capture_output=True, text=True,
            check=True, timeout=5).stdout.strip()
    except Exception:
        return None
    d = Path(common).parent / "data" / "long5m"
    return d if d.is_dir() else None


DATA = _long5m_dir()


def _ref_last(rng, pred):
    out = None
    for j in rng:
        if pred(j):
            out = j
    return out


def _ref_emrekb(o, h, l, c, ok, zz=9, fib=0.33, warm=25):
    """Verbatim pine_det.py::emrekb_events. Only changes: module WARM lifted
    to the ``warm`` param, and each box/event carries its origin candle index
    (obi/bbi) so the test can rebuild zone/sl in exact Decimals -- no
    behavior change. Events: (t, dir, tag, origin_index)."""
    n = len(c)
    trend, last_flip = 1, 0
    highs, lows = [], []
    market, last_l0, last_h0 = 1, None, None
    boxes, ev = [], []
    for t in range(n):
        s = max(0, t - zz + 1)
        if trend == 1 and l[t] <= l[s:t + 1].min():
            k = last_flip + int(np.argmax(h[last_flip:t + 1]))
            highs.append((k, h[k]))
            trend, last_flip = -1, t
        elif trend == -1 and h[t] >= h[s:t + 1].max():
            k = last_flip + int(np.argmin(l[last_flip:t + 1]))
            lows.append((k, l[k]))
            trend, last_flip = 1, t
        if len(highs) >= 2 and len(lows) >= 2 and ok[t] and t >= warm:
            (h0i, h0), (h1i, h1) = highs[-1], highs[-2]
            (l0i, l0), (l1i, l1) = lows[-1], lows[-2]
            if not (l0 == last_l0 or h0 == last_h0):
                if market == 1 and l0 < l1 and l0 < l1 - abs(h0 - l1) * fib:
                    market, last_l0, last_h0 = -1, l0, h0
                    obi = _ref_last(range(l1i, h0i + 1), lambda j: o[j] < c[j])
                    if obi is not None:
                        boxes.append([h[obi], l[obi], -1, t, "brk_ob", False, obi])
                    bbi = _ref_last(range(max(0, h1i - zz), l1i + 1), lambda j: o[j] > c[j])
                    if bbi is not None:
                        boxes.append([h[bbi], l[bbi], -1, t,
                                      "brk_bb" if h0 > h1 else "brk_mb", False, bbi])
                elif market == -1 and h0 > h1 and h0 > h1 + abs(h1 - l0) * fib:
                    market, last_l0, last_h0 = 1, l0, h0
                    obi = _ref_last(range(h1i, l0i + 1), lambda j: o[j] > c[j])
                    if obi is not None:
                        boxes.append([h[obi], l[obi], 1, t, "brk_ob", False, obi])
                    bbi = _ref_last(range(max(0, l1i - zz), h1i + 1), lambda j: o[j] < c[j])
                    if bbi is not None:
                        boxes.append([h[bbi], l[bbi], 1, t,
                                      "brk_bb" if l0 < l1 else "brk_mb", False, bbi])
        keep = []
        for bx in boxes:
            top, bot, d, born, tag, fired, oi = bx
            if (d == 1 and c[t] < bot) or (d == -1 and c[t] > top):
                continue
            if not fired and t > born and (
                    (d == 1 and bot <= c[t] < top)
                    or (d == -1 and bot < c[t] <= top)):
                bx[5] = True
                ev.append((t, d, tag, oi))
            keep.append(bx)
        boxes = keep
    return ev


def _ref_atr_ok(h, l, c):
    """Verbatim pine_lib.py::atr_sma14 -> the ok[] gate (Scorer, intraday)."""
    n = len(c)
    atr = np.full(n, np.nan)
    if n >= 15:
        tr = np.maximum(h[1:], c[:-1]) - np.minimum(l[1:], c[:-1])
        atr[14:] = pd.Series(tr).rolling(14).mean().to_numpy()[13:]
    return np.isfinite(atr)


def _load_rows(sym):
    """[(ts, o, h, l, c)] Decimals; h/l widened over o/c exactly like
    pine_lib.py::segments (a no-op on this clean fixture, asserted clean by
    Candle's own OHLC validation when fed)."""
    rows = []
    with open(DATA / f"{sym}.csv") as f:
        for r in csv.DictReader(f):
            o, h, l, c = (Decimal(r[k]) for k in ("open", "high", "low", "close"))
            rows.append((datetime.fromisoformat(r["ts"]), o, max(h, o, c),
                         min(l, o, c), c))
    return rows


def _feed_real(sym, rows, det):
    """One closed 5m bar per tick, on_session_end at every day boundary --
    exactly how SymbolPipeline drives closed-M5 detection over a continuum."""
    store = CandleStore("/nonexistent")
    out, day = [], None
    for k, (ts, o, h, l, c) in enumerate(rows):
        if day is not None and ts.date() != day:
            det.on_session_end()
        day = ts.date()
        store.add(Candle(sym, Timeframe.M1, ts, o, h, l, c, 0))
        for ev in det.detect(_ctx(store, ts + timedelta(minutes=5), sym)):
            out.append((k, ev))
    return out


@pytest.mark.skipif(DATA is None, reason="data/long5m real-data fixture not available")
def test_parity_with_reference_on_real_long5m():
    """PARITY GATE: event-set equality (ts, direction, sl, zone) vs the
    verbatim research oracle, RELIANCE + INFY, all 57 sessions concatenated
    (the continuum the +19.6pp edge was measured on). The oracle side is
    guarded collapse-free (no same-bar same-direction clashes on this
    fixture), so the raw reference events must match 1:1 -- the per-tick
    ``_collapse`` is pinned by its own unit test above."""
    expected, got = set(), set()
    for sym in REAL_SYMBOLS:
        rows = _load_rows(sym)
        o, h, l, c = (np.array([float(r[i]) for r in rows]) for i in (1, 2, 3, 4))
        ev = [e for e in _ref_emrekb(o, h, l, c, _ref_atr_ok(h, l, c))
              if e[2] == "brk_bb"]
        assert len({(t, d) for t, d, *_ in ev}) == len(ev)  # collapse-free
        for t, d, _, j in ev:
            bot, top = rows[j][3], rows[j][2]
            expected.add((sym, rows[t][0], _DIR[d], top if d == -1 else bot, bot, top))
        for k, e in _feed_real(sym, rows, BreakerMsbDetector({})):
            got.add((sym, rows[k][0], e.direction, Decimal(e.meta["sl"]),
                     e.zone[0], e.zone[1]))
    assert got == expected
    # guard: the fixture must exercise the machine non-trivially, both ways
    assert len(expected) >= 20
    assert {s for s, *_ in expected} == set(REAL_SYMBOLS)
    assert {d for _, _, d, *_ in expected} == {Direction.LONG, Direction.SHORT}
