"""Tests for the ob_lux detector (trader/detectors/ob_lux.py).
Binding design: v2 task-1 brief (validated LuxAlgo internal Order Block,
ported from the measured-winner scratchpad luxob.py: swing-pivot leg
extreme with an ATR-based volatility-as-volume-proxy adjustment).

Fixture geometry: every bar (flat warmup + custom) keeps TR == 2, so
ATR(M5,14) == 2 exactly at every tick -- no drift between the creation and
retest ticks. size=2 keeps the pivot window short enough for compact
fixtures (default is 5).

PARITY GATE (bottom of file): the detector, driven tick-by-tick over real
continuum M5 data (RELIANCE + INFY, session-anchored M5 across ALL 19
sessions, no session scoping), must create the SAME order-block set (birth
ts, kind) as the validated reference ``lux_ob_events`` (scratchpad
luxob.py) -- the fidelity oracle, inlined per the test_inducement.py
precedent (the scratchpad script lives in an ephemeral agent tmpdir, not a
stable import path). This gate caught and drove two real fixes to
``ob_lux.py``:

1. The hv-volatility threshold was applying a single *current* ``ctx.atr``
   to the WHOLE rescanned history every tick, instead of each bar's own
   point-in-time trailing ATR (the reference's ``atrs[j]`` array) --
   silently reclassifying early bars' swap decision as ATR drifted, which
   flipped an already-decided anchor bar. Fixed via ``_atr_series``.
2. The full-rescan-every-tick design could RESURRECT a previously
   overlap-evicted OB once its evicting rival aged off ACTIVE, because
   ``_upsert``'s existence check only looked at current ``ctx.levels``, not
   permanent history. Fixed via the ``_decided`` set.

Overlap-dedupe (a documented detector behavior absent from the reference's
unbounded, append-only ``obs`` list) is the only allowed source of fewer
detector levels; every dropped level is verified genuinely overlap-evicted
(same-kind, zone-overlapping, quality-dominated per ``_upsert``'s own
tie-break), not missed.
"""

from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from trader.detectors.ob_lux import ObLuxDetector
from trader.engine.context import DayState, StockContext
from trader.engine.levels import LevelEngine
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore
from trader.tools.study import atr_series

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)  # NSE open
M5 = Timeframe.M5
FLAT = (100, 101, 99, 100)  # TR == 2 warmup bar


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


# Bull leg (size=2): pivot high at bar16 (H=102) confirmed once bars 17-18
# fail to exceed it; pullback 17-19, breakout close (103) past 102 confirmed
# at bar22 (overshoot 1 / ATR 2 -> quality 0.5). Every bar TR == 2. The leg
# extreme (lowest low in [16,22]) is bar17 -> zone (99, 101).
BULL_16_21 = [(100, 102, 100, 101), (101, 101, 99, 100), (100, 101, 99, 99),
             (99, 101, 99, 100), (100, 102, 100, 101), (101, 103, 101, 102)]


def bull_bars(c22=103):
    return [FLAT] * 16 + BULL_16_21 + [(102, 104, 102, c22)]


BULL_RETRACE = (103, 103, 101, 101)  # TR == 2, closes at zone hi (101)

# Bear mirror (prices reflected 200-x, H/L swapped): pivot low at bar16
# (L=98), breakout close (97) past 98 confirmed at bar22. Leg extreme is
# bar17 -> zone (99, 101).
BEAR_16_21 = [(100, 100, 98, 99), (99, 101, 99, 100), (100, 101, 99, 101),
             (101, 101, 99, 100), (100, 100, 98, 99), (99, 99, 97, 98)]


def bear_bars(c22=97):
    return [FLAT] * 16 + BEAR_16_21 + [(98, 98, 96, c22)]


BEAR_RETRACE = (97, 99, 97, 99)  # TR == 2, closes at zone lo (99)


def test_bullish_ob_created_and_retest_long():
    store = make_store(bull_bars() + [BULL_RETRACE])
    det, levels = ObLuxDetector({"size": 2}), []
    # confirmation tick: OB born, but its own close (103) is outside the zone
    assert det.detect(ctx_at(store, 23, levels)) == []
    [lv] = levels
    assert lv.kind is LevelKind.OB_BULL
    assert lv.zone == (tick(99), tick(101))
    assert lv.born == bar_ts(17)
    assert lv.tf is M5
    assert lv.state is LevelState.ACTIVE
    [ev] = det.detect(ctx_at(store, 24, levels))  # retrace closes inside zone
    assert ev.detector == "ob_lux"
    assert ev.direction is Direction.LONG
    assert ev.strength == pytest.approx(0.5)
    assert ev.zone == (tick(99), tick(101))
    assert ev.ttl_candles == 6
    assert ev.meta == {"level_id": lv.id, "event": "OB_RETEST"}


def test_bearish_ob_mirror():
    store = make_store(bear_bars() + [BEAR_RETRACE])
    det, levels = ObLuxDetector({"size": 2}), []
    assert det.detect(ctx_at(store, 23, levels)) == []
    [lv] = levels
    assert lv.kind is LevelKind.OB_BEAR
    assert lv.zone == (tick(99), tick(101))
    assert lv.born == bar_ts(17)
    [ev] = det.detect(ctx_at(store, 24, levels))
    assert ev.direction is Direction.SHORT
    assert ev.strength == pytest.approx(0.5)
    assert ev.meta == {"level_id": lv.id, "event": "OB_RETEST"}


def test_no_evidence_before_retest_no_lookahead():
    store = make_store(bull_bars() + [BULL_RETRACE])
    det, levels = ObLuxDetector({"size": 2}), []
    det.detect(ctx_at(store, 23, levels))
    assert len(levels) == 1  # OB exists...
    # ...but bar23 (already sitting in the store) is invisible until its own
    # tf duration closes, and the confirmation candle's own close is outside
    # the zone, so no evidence yet either way.
    assert det.detect(ctx_at(store, 23, levels)) == []
    [ev] = det.detect(ctx_at(store, 24, levels))
    assert ev.direction is Direction.LONG


def test_vol_adjustment_excludes_high_volatility_wick():
    # bar17's raw low (90) would win a plain argmin(low); its range (11.5)
    # trips the hv threshold (2 * ATR = 4) so it is excluded from the
    # leg-extreme search and bar18 (low 99) is picked instead.
    bars = ([FLAT] * 16 + [(100, 102, 100, 101), (101, 101.5, 90, 101),
                           (101, 101, 99, 100), (100, 102, 100, 101),
                           (101, 103, 101, 102), (102, 104, 102, 103)])
    store = make_store(bars)
    levels = []
    ObLuxDetector({"size": 2}).detect(ctx_at(store, 22, levels))
    [lv] = levels
    assert lv.zone == (tick(99), tick(101))  # not (90, 101.5)
    assert lv.born == bar_ts(18)


def test_overlap_keeps_higher_quality_new_wins():
    store = make_store(bull_bars(c22=103.5))  # overshoot 1.5 -> quality 0.75
    rival = Level(id="seed", symbol="X", kind=LevelKind.OB_BULL,
                 zone=(tick(99.5), tick(100.5)), born=bar_ts(5), tf=M5)
    levels = [rival]
    ObLuxDetector({"size": 2}).detect(ctx_at(store, 23, levels))
    [lv] = levels
    assert lv.zone == (tick(99), tick(101))  # replaced the rival (0.75 > 0.5)


def test_overlap_keeps_higher_quality_old_wins():
    store = make_store(bull_bars())  # overshoot 1 -> quality 0.5
    rival = Level(id="seed", symbol="X", kind=LevelKind.OB_BULL,
                 zone=(tick(99.5), tick(100.5)), born=bar_ts(5), tf=M5)
    levels = [rival]
    ObLuxDetector({"size": 2}).detect(ctx_at(store, 23, levels))
    assert levels == [rival]  # 0.5 <= rival's default 0.5: new OB discarded


def test_on_session_end_persists_structural_memory():
    # Continuum: _quality/_anchor describe levels/legs that carry across
    # days -- they persist; _emitted is pruned to the newest bar's entries
    # (that bar is still the latest close across the boundary).
    store = make_store(bull_bars() + [BULL_RETRACE])
    det, levels = ObLuxDetector({"size": 2}), []
    det.detect(ctx_at(store, 23, levels))
    [ev] = det.detect(ctx_at(store, 24, levels))
    quality, anchor = dict(det._quality), dict(det._anchor)
    assert quality and anchor and det._emitted
    det.on_session_end()
    assert det._quality == quality and det._anchor == anchor
    assert det._emitted == {(ev.meta["level_id"], bar_ts(23))}
    assert det.detect(ctx_at(store, 24, levels)) == []  # dedupe survived


def test_continuum_leg_spans_session_boundary():
    """CONTINUUM (validated): the bull leg's pivot/pullback close out day 1;
    the confirming breakout close and the retrace are day 2's first two
    candles. luxob.py::lux_ob_events ran one long multi-day series, so the
    swing structure carries: the OB is born at day 1's leg-extreme bar and
    day 2's retrace fires the LONG retest."""
    day1_bars = [FLAT] * 16 + BULL_16_21            # pivot @16, leg through 21
    day2 = SESSION_START + timedelta(days=1)
    store = make_store(day1_bars)
    for i, (o, h, l, c) in enumerate([(102, 104, 102, 103), BULL_RETRACE]):
        store.add(Candle("X", Timeframe.M1, day2 + timedelta(minutes=5 * i),
                         tick(o), tick(h), tick(l), tick(c), 10))

    det, levels = ObLuxDetector({"size": 2}), []
    det.on_session_end()                            # boundary hook: keeps structure
    now = day2 + timedelta(minutes=5)
    assert det.detect(StockContext(symbol="X", now=now, candles=store.view("X", now),
                                   levels=levels, evidence_history=[],
                                   day=DayState(session_date=now.date()))) == []
    [lv] = levels                                   # confirmed by day-2's first close
    assert lv.kind is LevelKind.OB_BULL
    assert lv.zone == (tick(99), tick(101))
    assert lv.born == bar_ts(17)                    # day-1 leg-extreme bar
    now2 = day2 + timedelta(minutes=10)
    [ev] = det.detect(StockContext(symbol="X", now=now2, candles=store.view("X", now2),
                                   levels=levels, evidence_history=[],
                                   day=DayState(session_date=now2.date())))
    assert ev.direction is Direction.LONG
    assert ev.strength == pytest.approx(0.5)


def test_no_evidence_for_terminal_state_level():
    store = make_store(bull_bars() + [BULL_RETRACE])
    det, levels = ObLuxDetector({"size": 2}), []
    det.detect(ctx_at(store, 23, levels))
    [lv] = levels
    lv.record_state(bar_ts(23), LevelState.MITIGATED)  # terminal: dead for entries
    assert det.detect(ctx_at(store, 24, levels)) == []  # retest inside zone, but no evidence


def test_restart_preserves_tested_level_no_eviction():
    # Session 1 (or pre-restart): the OB is born at bar17 (bar17's range is
    # plain, TR == 2) and gets tested -- real state/history now on the level.
    persisted = ObLuxDetector({"size": 2})
    levels = []
    persisted.detect(ctx_at(make_store(bull_bars()), 23, levels))
    [old] = levels
    assert old.born == bar_ts(17)
    old.record_state(bar_ts(20), LevelState.TESTED)

    # Restart: a brand new instance (no memoized anchor) rescans. Here bar17
    # is a high-volatility wick (excluded from the leg-extreme search, as in
    # test_vol_adjustment_excludes_high_volatility_wick) -- standing in for
    # an ATR-drifted re-classification -- so the anchor now resolves to
    # bar18 instead of bar17: a DIFFERENT level_id for the same zone.
    bars = ([FLAT] * 16 + [(100, 102, 100, 101), (101, 101.5, 90, 101),
                           (101, 101, 99, 100), (100, 102, 100, 101),
                           (101, 103, 101, 102), (102, 104, 102, 103)])
    fresh = ObLuxDetector({"size": 2})
    fresh.detect(ctx_at(make_store(bars), 22, levels))

    # The persisted TESTED level must survive untouched, not be evicted.
    assert old in levels and old.state is LevelState.TESTED
    assert old.zone == (tick(99), tick(101)) and old.born == bar_ts(17)
    # The anchor-mismatched OB is added alongside it (fresh ACTIVE dup),
    # never silently swapped in for the stateful one.
    assert len(levels) == 2
    [new] = [lv for lv in levels if lv is not old]
    assert new.state is LevelState.ACTIVE
    assert new.zone == (tick(99), tick(101)) and new.born == bar_ts(18)


# ==========================================================================
# PARITY GATE -- fidelity vs the validated reference (see module docstring)
# ==========================================================================
DATA = Path(__file__).resolve().parents[3] / "data" / "wide"
PARITY_SYMBOLS = ["RELIANCE", "INFY"]   # LTIM/TATAMOTORS in data/wide are empty stubs
PARITY_PARAMS = {"tf": "5m", "size": 5, "hv_atr_mult": 2.0}
_KIND = {1: LevelKind.OB_BULL, -1: LevelKind.OB_BEAR}


def _load_m1(symbol: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / f"{symbol}.csv")
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert("Asia/Kolkata")
    return df.sort_values("ts")


# --------------------------------------------------------------------------
# Reference oracle: verbatim copy of scratchpad luxob.py::lux_ob_events,
# extended to expose each OB's birth (anchor bar index) and first-touch bar
# -- the original only returns retest events, not creation, and doesn't tag
# which ob a touch belongs to. `events` (bar, dir) is kept for the
# retest-timing sanity check (item 3 below).
# --------------------------------------------------------------------------
def _lux_ob(m5, atrs, size=5):
    n = len(m5)
    H = [float(c.high) for c in m5]; L = [float(c.low) for c in m5]; C = [float(c.close) for c in m5]
    pH = [0.0] * n; pL = [0.0] * n
    for j in range(n):
        a = atrs[j]
        hv = a is not None and (H[j] - L[j]) >= 2 * float(a)
        pH[j] = L[j] if hv else H[j]
        pL[j] = H[j] if hv else L[j]
    swHlvl = swHidx = swLlvl = swLidx = None
    swHc = swLc = False
    obs, events = [], []
    for i in range(n):
        if i >= size:
            p = i - size
            win_h = max(H[p + 1:i + 1]); win_l = min(L[p + 1:i + 1])
            if H[p] > win_h:
                swHlvl, swHidx, swHc = H[p], p, False
            if L[p] < win_l:
                swLlvl, swLidx, swLc = L[p], p, False
        if swHlvl is not None and not swHc and C[i] > swHlvl and (i == 0 or C[i - 1] <= swHlvl):
            swHc = True
            seg = range(swHidx, i + 1); idx = min(seg, key=lambda j: pL[j])
            obs.append(dict(lo=pL[idx], hi=pH[idx], bias=1, mitig=False, touched=False,
                            born=i, anchor=idx, piv=swHlvl))
        if swLlvl is not None and not swLc and C[i] < swLlvl and (i == 0 or C[i - 1] >= swLlvl):
            swLc = True
            seg = range(swLidx, i + 1); idx = max(seg, key=lambda j: pH[j])
            obs.append(dict(lo=pL[idx], hi=pH[idx], bias=-1, mitig=False, touched=False,
                            born=i, anchor=idx, piv=swLlvl))
        for ob in obs:
            if ob["mitig"] or ob["born"] >= i:
                continue
            if ob["bias"] == 1 and L[i] < ob["lo"]:
                ob["mitig"] = True; continue
            if ob["bias"] == -1 and H[i] > ob["hi"]:
                ob["mitig"] = True; continue
            if not ob["touched"] and L[i] <= ob["hi"] and H[i] >= ob["lo"]:
                ob["touched"] = True
                ob["touched_at"] = i
                events.append((i, ob["bias"]))
    return obs, events


def _quality(ob: dict, atrs: list, m5: list) -> float:
    """The port's quality formula (``ObLuxDetector._quality_of``), applied to
    the reference's own overshoot/pivot/confirm-bar data -- reused verbatim
    (not re-derived) so the fixture can never silently drift from the
    production formula."""
    i = ob["born"]
    piv = Decimal(str(ob["piv"]))
    overshoot = (m5[i].close - piv) if ob["bias"] == 1 else (piv - m5[i].close)
    return ObLuxDetector._quality_of(overshoot, atrs[i])


def _overlaps(a: dict, b: dict) -> bool:
    return a["lo"] <= b["hi"] and b["lo"] <= a["hi"]


def _justified_drop(dropped: dict, obs: list, atrs: list, m5: list) -> bool:
    """A dropped (reference-expected but detector-absent) OB is justified iff
    a same-kind, zone-overlapping counterpart exists whose quality dominates
    per ``_upsert``'s own tie-break (`<=` keeps the earlier/existing one;
    strictly-greater evicts it)."""
    dq = _quality(dropped, atrs, m5)
    for other in obs:
        if other is dropped or other["bias"] != dropped["bias"] or not _overlaps(dropped, other):
            continue
        oq = _quality(other, atrs, m5)
        later = other["born"] > dropped["born"]
        if (later and oq > dq) or (not later and oq >= dq):
            return True
    return False


# --------------------------------------------------------------------------
# Minimal ctx driver: real M1 -> CandleStore (auto-derives M5, byte-identical
# to the reference's own day-first-row bucketing since every session in
# data/wide starts exactly at 09:15 on a clean 375-row grid) -- one detect()
# call per closed M5 bar, LevelEngine.update() run first each bar (production
# order, see SymbolPipeline._on_m5_close), across ALL sessions with NO level
# pruning (continuum: every OB the algorithm ever creates must stay visible
# for the birth-parity assertion; only on_session_end's dedupe-set prune
# fires, as in production).
# --------------------------------------------------------------------------
def _drive(symbol: str, df: pd.DataFrame):
    store = CandleStore("/nonexistent")
    det = ObLuxDetector(PARITY_PARAMS)
    engine = LevelEngine({})
    levels: list = []
    evidence_history: list = []
    created, removed = [], []          # (born, kind) append/evict log, in order
    prev_date = None
    for day, g in df.groupby(df.ts.dt.date):
        if prev_date is not None:
            det.on_session_end()
            engine.on_session_end()
        prev_date = day
        day_state = DayState(session_date=day)
        rows = list(g.itertuples(index=False))
        assert len(rows) % 5 == 0, (symbol, day, len(rows))
        for b in range(0, len(rows), 5):
            chunk = rows[b:b + 5]
            for r in chunk:
                store.add(Candle(symbol, Timeframe.M1, r.ts.to_pydatetime(),
                                 Decimal(str(r.open)), Decimal(str(r.high)),
                                 Decimal(str(r.low)), Decimal(str(r.close)),
                                 int(r.volume)))
            now = chunk[0].ts.to_pydatetime() + timedelta(minutes=5)
            ctx = StockContext(symbol=symbol, now=now, candles=store.view(symbol, now),
                               levels=levels, evidence_history=evidence_history, day=day_state)
            before = {lv.id: lv for lv in levels}
            c5 = ctx.candles.last(1, Timeframe.M5)[-1]
            atr = ctx.atr(Timeframe.M5)
            engine.update(levels, c5, atr)          # production order: engine before detect
            evs = det.detect(ctx)
            evidence_history.extend(evs)
            after = {lv.id: lv for lv in levels}
            for lid, lv in after.items():
                if lid not in before:
                    created.append((lv.born, lv.kind))
            for lid, lv in before.items():
                if lid not in after:
                    removed.append((lv.born, lv.kind))
    m5 = store._data[symbol][Timeframe.M5]
    return m5, levels, evidence_history, created, removed


@pytest.fixture(scope="module", params=PARITY_SYMBOLS)
def parity_run(request):
    symbol = request.param
    df = _load_m1(symbol)
    m5, levels, evidence_history, created, removed = _drive(symbol, df)
    atrs = atr_series(m5)
    obs, events = _lux_ob(m5, atrs, size=PARITY_PARAMS["size"])
    expected = [(m5[ob["anchor"]].ts, _KIND[ob["bias"]]) for ob in obs]
    return dict(symbol=symbol, m5=m5, atrs=atrs, obs=obs, events=events,
                expected=expected, levels=levels, evidence_history=evidence_history,
                created=created, removed=removed)


def test_parity_birth_set_vs_reference(parity_run):
    """The detector's FINAL level set (born ts, kind) must equal the
    reference's OB set, with the only allowed shortfall being genuine,
    quality-justified overlap-dedupe (never a spurious extra, never an
    unexplained miss)."""
    r = parity_run
    m5, atrs, obs, expected = r["m5"], r["atrs"], r["obs"], r["expected"]
    final = [(lv.born, lv.kind) for lv in r["levels"]]

    exp_count, final_count = Counter(expected), Counter(final)
    extra = final_count - exp_count
    assert not extra, f"[{r['symbol']}] detector created OB(s) absent from the reference: {extra}"

    remaining = exp_count - final_count       # multiset of dropped (expected, count)
    assert sum(remaining.values()) == len(expected) - len(final), "accounting mismatch"
    for ob in obs:
        key = (m5[ob["anchor"]].ts, _KIND[ob["bias"]])
        if remaining.get(key, 0) <= 0:
            continue
        assert _justified_drop(ob, obs, atrs, m5), \
            f"[{r['symbol']}] unjustified miss (not a genuine overlap-dedupe): {key}"
        remaining[key] -= 1
    assert +remaining == Counter(), f"[{r['symbol']}] unaccounted drops: {+remaining}"


def test_parity_no_created_only_final_differs_by_dedupe(parity_run):
    """Sanity on the CREATION log itself (before final-state pruning): every
    entry the detector ever creates must trace to a reference obs (no
    spurious anchor); every reference obs the detector never creates at all
    must be a same-tick overlap-reject (case (a) of ``_upsert``)."""
    r = parity_run
    obs, expected, created = r["obs"], r["expected"], r["created"]
    created_count, exp_count = Counter(created), Counter(expected)
    assert not (created_count - exp_count), \
        f"[{r['symbol']}] spurious anchors created: {created_count - exp_count}"
    never_created = exp_count - created_count
    for ob in obs:
        key = (r["m5"][ob["anchor"]].ts, _KIND[ob["bias"]])
        if never_created.get(key, 0) <= 0:
            continue
        assert _justified_drop(ob, obs, r["atrs"], r["m5"]), \
            f"[{r['symbol']}] never created and unjustified: {key}"


def test_retest_evidence_timing_sanity(parity_run):
    """Item 3 (sanity, not strict parity): the reference's retest definition
    is range-overlap (first touch); the detector's is close-inside-zone --
    a strictly narrower condition, so the detector's first OB_RETEST for a
    surviving level can never fire BEFORE the reference's first-touch bar
    for the same OB (no lookahead), though it may fire later or never (a
    range-overlap that never closes inside). Assert the no-lookahead
    invariant strictly; the coverage ratio is reported as a loose sanity
    floor since the two definitions genuinely differ."""
    r = parity_run
    m5, obs = r["m5"], r["obs"]
    final_by_key = {(lv.born, lv.kind): lv for lv in r["levels"]}
    first_retest: dict[str, datetime] = {}
    for e in r["evidence_history"]:
        if e.meta.get("event") != "OB_RETEST":
            continue
        lid = e.meta["level_id"]
        if lid not in first_retest or e.ts < first_retest[lid]:
            first_retest[lid] = e.ts

    touched_surviving = matched = 0
    for ob in obs:
        if "touched_at" not in ob:
            continue
        lv = final_by_key.get((m5[ob["anchor"]].ts, _KIND[ob["bias"]]))
        if lv is None:              # dropped by dedupe: not this test's concern
            continue
        touched_surviving += 1
        fr = first_retest.get(lv.id)
        if fr is None:
            continue
        matched += 1
        ref_touch_ts = m5[ob["touched_at"]].ts
        assert fr >= ref_touch_ts, \
            f"[{r['symbol']}] detector retest fired before reference's first touch: {lv.id}"

    assert touched_surviving > 0, f"[{r['symbol']}] fixture too thin to exercise retests"
    assert matched / touched_surviving >= 0.4, (
        f"[{r['symbol']}] detector OB_RETEST coverage too low vs reference touches: "
        f"{matched}/{touched_surviving}")
