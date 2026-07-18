"""Tests for the compression_fade detector (trader/detectors/compression_fade.py).
Binding design: v2-task3 brief (port of rr.py::compress_fade) — FADE the coil
breakout: a break of the compression candle's high => SHORT (sl = break
high); a break of its low => LONG (sl = break low). Signal-emitter only, no
Levels."""

import csv
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.compression_fade import CompressionFadeDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M1, M5 = Timeframe.M1, Timeframe.M5

COMPRESS = (100, 105, 95, 100)     # doji, range 10: body 0<=3.5, wicks 5>=2 each
INSIDE = (100, 102, 99, 102)       # non-compress (body/range=0.67), no break
FILLER = (100, 101, 99, "100.8")   # non-compress, TR=2 (ATR priming filler)
UP_BREAK = (106, 107, 106, "106.5")    # high 107 > 105 -> SHORT, sl=107
DOWN_BREAK = (94, "94.5", 93, "93.5")  # low 93 < 95 -> LONG, sl=93
NOT_COMPRESS = (100, 101, 99, "100.8")  # body 0.8/range 2 = 0.4 > 0.35


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def bar(i, o, h, l, c, v=10):
    return Candle("X", M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_store(bars):
    """One M1 candle per M5 bucket start -> the derived M5 bar equals it."""
    store = CandleStore("/nonexistent")
    for i, b in enumerate(bars):
        store.add(bar(i, *b))
    return store


def ctx_at(store, n_bars):
    now = bar_ts(n_bars)  # first n_bars M5 bars are closed
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


def test_up_break_emits_short_with_sl_at_break_high():
    # FILLER anchors COMPRESS off bar 0 of the continuum (see the dedicated
    # bar0 carve-out test below) -- this test is about the break mechanics.
    store = make_store([FILLER, COMPRESS, UP_BREAK])
    [ev] = CompressionFadeDetector({}).detect(ctx_at(store, 3))
    assert ev.detector == "compression_fade"
    assert ev.direction is Direction.SHORT
    # raw break high, no buffer; entry key dropped; atr None here -> sl_floor "0"
    assert ev.meta == {"event": "COMPRESSION_FADE", "sl": str(tick(107)), "sl_floor": "0"}
    assert ev.zone == (tick("106.5"), tick(107))
    assert ev.ttl_candles == 2
    assert 0.0 <= ev.strength <= 1.0


def test_down_break_emits_long_with_sl_at_break_low():
    store = make_store([FILLER, COMPRESS, DOWN_BREAK])
    [ev] = CompressionFadeDetector({}).detect(ctx_at(store, 3))
    assert ev.direction is Direction.LONG
    assert ev.meta == {"event": "COMPRESSION_FADE", "sl": str(tick(93)), "sl_floor": "0"}
    assert ev.zone == (tick(93), tick("93.5"))


def test_non_compression_candle_no_signal():
    store = make_store([NOT_COMPRESS, UP_BREAK])
    assert CompressionFadeDetector({}).detect(ctx_at(store, 2)) == []


def test_break_beyond_window_no_signal():
    # inside x3 then a 4th-bar break: outside the default break_window=3
    store = make_store([COMPRESS, INSIDE, INSIDE, INSIDE, UP_BREAK])
    det = CompressionFadeDetector({})
    for n in range(2, 5):
        assert det.detect(ctx_at(store, n)) == []
    assert det.detect(ctx_at(store, 5)) == []


def test_break_within_window_fires_on_third_bar():
    store = make_store([FILLER, COMPRESS, INSIDE, INSIDE, UP_BREAK])
    det = CompressionFadeDetector({})
    assert det.detect(ctx_at(store, 3)) == []
    assert det.detect(ctx_at(store, 4)) == []
    [ev] = det.detect(ctx_at(store, 5))
    assert ev.direction is Direction.SHORT


def test_sl_floor_annotated_when_atr_available():
    store = make_store([FILLER] * 15 + [COMPRESS, UP_BREAK])
    ctx = ctx_at(store, 17)
    atr = ctx.atr(M5)
    [ev] = CompressionFadeDetector({}).detect(ctx)
    assert atr is not None
    assert ev.meta["sl_floor"] == str(Decimal("0.15") * atr)


def test_no_lookahead_before_break_bar_closes():
    store = make_store([COMPRESS, UP_BREAK])
    assert CompressionFadeDetector({}).detect(ctx_at(store, 1)) == []  # only COMPRESS closed


def test_dedupe_one_fire_per_compression():
    store = make_store([FILLER, COMPRESS, UP_BREAK])
    det = CompressionFadeDetector({})
    [ev] = det.detect(ctx_at(store, 3))
    assert det.detect(ctx_at(store, 3)) == []  # same tick again: no duplicate


def test_on_session_end_keeps_recent_dedupe():
    # Continuum: dedupe survives the boundary; a fired coil still inside the
    # break window must NOT re-fire after on_session_end (age-prune only).
    store = make_store([FILLER, COMPRESS, UP_BREAK])
    det = CompressionFadeDetector({})
    det.detect(ctx_at(store, 3))
    det.on_session_end()
    assert det._emitted  # coil ts retained (within break_window age)
    assert det.detect(ctx_at(store, 3)) == []


def test_bar0_of_continuum_never_a_compression_candidate():
    """FIX (FINDER micro-divergence): rr.py::compress_fade loops i from 1,
    so the very first bar of a symbol's WHOLE continuum can never be a
    compression candidate there -- the parity gate below flags this as a
    latent gap unexercised by the real fixture. Construct it directly: no
    FILLER anchor, so COMPRESS really is bar 0 of this store's history, and
    it breaks within its window -- pre-fix the detector would have fired
    here (diverging from the reference); post-fix it must not."""
    store = make_store([COMPRESS, UP_BREAK])
    assert CompressionFadeDetector({}).detect(ctx_at(store, 2)) == []


def test_continuum_cross_day_fade():
    """CONTINUUM (validated): FILLER (bar 0, non-compression) then COMPRESS
    close out day 1; UP_BREAK is day 2's first candle and breaks its high.
    rr.py::compress_fade was measured on one concatenated multi-day series,
    so the coil stays live across the gap: the fade MUST fire on day 2's
    very first tick. FILLER keeps COMPRESS off bar 0 of the continuum (see
    test_bar0_of_continuum_never_a_compression_candidate) -- unrelated to
    what this test validates."""
    day1 = SESSION_START
    day2 = day1 + timedelta(days=1)
    store = CandleStore("/nonexistent")
    store.add(Candle("X", M1, day1, *(tick(x) for x in FILLER), 10))
    store.add(Candle("X", M1, day1 + timedelta(minutes=M5.minutes),
                     *(tick(x) for x in COMPRESS), 10))
    store.add(Candle("X", M1, day2, *(tick(x) for x in UP_BREAK), 10))

    det = CompressionFadeDetector({})
    det.on_session_end()                    # boundary hook must not lose the coil
    now = day2 + timedelta(minutes=M5.minutes)
    ctx = StockContext(symbol="X", now=now, candles=store.view("X", now),
                       levels=[], evidence_history=[],
                       day=DayState(session_date=now.date()))
    [ev] = det.detect(ctx)                  # day-1 coil faded by day-2 break
    assert ev.direction is Direction.SHORT
    assert ev.meta["sl"] == str(tick(107))


# --------------------------------------------------------------------------
# PARITY GATE -- real continuum data vs rr.py::compress_fade (validated ref)
# --------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "wide"
_SYMBOLS = ("RELIANCE", "INFY")     # LTIM/TATAMOTORS excluded: empty in data/wide
_BPD = 375                          # M1 bars/session (full 09:15-15:30 NSE day)


def _load_m1(symbol):
    with (DATA_DIR / f"{symbol}.csv").open() as f:
        return [Candle(symbol, M1, datetime.fromisoformat(r["ts"]),
                       Decimal(r["open"]), Decimal(r["high"]), Decimal(r["low"]),
                       Decimal(r["close"]), int(float(r["volume"])))
                for r in csv.DictReader(f)]


def _compress_fade_ref(m5):
    """Verbatim port of the scratchpad reference rr.py::compress_fade -- the
    validated edge (n=6144, win@3R=31%, exp +0.26R) this detector reproduces."""
    def isc(c):
        r = float(c.high - c.low)
        if r <= 0:
            return False
        b = abs(float(c.close - c.open))
        uw = float(c.high - max(c.open, c.close))
        lw = float(min(c.open, c.close) - c.low)
        return b <= 0.35 * r and uw >= 0.2 * r and lw >= 0.2 * r
    H = [float(c.high) for c in m5]
    L = [float(c.low) for c in m5]
    ev = []
    for i in range(1, len(m5) - 1):
        if not isc(m5[i]):
            continue
        for j in range(i + 1, min(i + 4, len(m5))):
            if H[j] > H[i]:
                ev.append((j, -1, H[j])); break               # noqa: E702
            if L[j] < L[i]:
                ev.append((j, 1, L[j])); break                # noqa: E702
    return ev


def _feed_real(m1_rows, det, symbol):
    """Drive the detector tick-by-tick: one M5 close per 5 real M1 minutes,
    on_session_end() at each session boundary -- the same order as
    SymbolPipeline.on_m1/_end_session (pipeline.py): a day's last M5 bucket
    closes (and detect() runs on it) before on_session_end() fires, which
    runs before the next day's first M1 is added. Real data/wide sessions
    have no gaps (uniform 375 M1/day), so this reproduces that order exactly
    without needing the gap-closing machinery pipeline.py needs for live/
    partial feeds. Returns (events, full continuum M5 series)."""
    store = CandleStore("/nonexistent")
    got, day = [], None
    for ds in range(0, len(m1_rows), _BPD):
        rows = m1_rows[ds:ds + _BPD]
        if day is not None:
            det.on_session_end()
        day = rows[0].ts.date()
        for k in range(0, len(rows), 5):
            for c in rows[k:k + 5]:
                store.add(c)
            now = rows[k].ts + timedelta(minutes=5)
            ctx = StockContext(symbol=symbol, now=now, candles=store.view(symbol, now),
                               levels=[], evidence_history=[],
                               day=DayState(session_date=day))
            for e in det.detect(ctx):
                # e.ts is ctx.now (decision instant = bar close); pair with
                # the closing bar's OWN ts (bucket start), matching m5[i].ts
                got.append((rows[k].ts, e.direction, Decimal(e.meta["sl"])))
    return got, store._data[symbol][M5]


@pytest.mark.skipif(not (DATA_DIR / "RELIANCE.csv").exists(),
                    reason="data/wide real fixtures not present")
def test_parity_with_reference_over_real_continuum_data():
    """PARITY GATE: for each symbol, run rr.py::compress_fade (inlined,
    verbatim) over the full session-anchored continuum M5 series, and assert
    the detector -- driven tick-by-tick, on_session_end at every session
    boundary -- reproduces the SAME event set (ts, direction, sl).

    No ATR-warmup difference to document: sl_floor is ATR-gated, but
    detect()'s emission itself is not (atr only annotates meta), so parity
    holds from the very first eligible window.

    One documented, justified ORDER-ONLY difference: the reference iterates
    by compression-candidate index i and appends each one's first break
    immediately, so when two candidates' break_window lookaheads overlap its
    output list can interleave out of chronological (bar) order. The
    detector is a live tick-by-tick stream and can only ever emit in
    non-decreasing tick order (causality). The underlying event SET (which
    bar, which direction, which sl -- the only things that matter for
    trading) is identical either way, so both sides are compared as sorted
    multisets, not raw sequences.

    Bar-0 carve-out (fixed): the reference loops ``i`` from 1, so the very
    first M5 bar of a symbol's whole continuum can never be a compression
    candidate there; ``detect()`` now carries the identical carve-out (the
    ``bar0`` guard). On this fixture RELIANCE's bar 0 IS compression-shaped
    but never breaks within its window, so this gate cannot exercise the
    carve-out either way -- see
    test_bar0_of_continuum_never_a_compression_candidate for a constructed
    case that does."""
    key = lambda t: (t[0], t[1].value, t[2])       # noqa: E731 -- avoid Enum '<'
    dirs = set()
    total = 0
    for symbol in _SYMBOLS:
        m1 = _load_m1(symbol)
        det = CompressionFadeDetector({})
        got, m5 = _feed_real(m1, det, symbol)
        ref = _compress_fade_ref(m5)
        expected = [(m5[i].ts, Direction.LONG if d == 1 else Direction.SHORT,
                    Decimal(str(x))) for i, d, x in ref]
        assert sorted(got, key=key) == sorted(expected, key=key), symbol
        total += len(expected)
        dirs |= {d for _, d, _ in expected}
    assert total > 100                              # fixture exercises the detector
    assert dirs == {Direction.LONG, Direction.SHORT}
