"""Tests for the turtle_soup detector (trader/detectors/turtle_soup.py).
Binding design: v2-task7 brief (port of liq_hunt.py::turtle_soup) -- a new
N-bar low that closes back above the prior N-bar low (failed breakdown) is
FADED long, sl = the swept low; mirror for a new N-bar high closing back
below the prior N-bar high (failed breakout) -> fade short. Signal-emitter
only, no Levels.

Fixtures use N=3 (not the N=20 production default) so a qualifying bar fits
in a manageable number of bars (window = N+1 = 4)."""

import csv
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.turtle_soup import TurtleSoupDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import TICK, Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M1, M5 = Timeframe.M1, Timeframe.M5
PARAMS = {"tf": "5m", "N": 3}

# LONG fixture: prior lows 95(first)/97/98 -> min=95, ref=L[i-N]=95
PRIOR_A = (100, 105, 95, 100)
PRIOR_B = (100, 105, 97, 100)
PRIOR_C = (100, 105, 98, 100)
BREAK_LONG = (94, 97, 90, 96)      # low=90<95 (new low), close=96>95 (reclaim) -> LONG
NO_RECLAIM = (94, 95, 90, 92)      # low=90<95 (new low), close=92<=95 -> genuine breakout, no signal

# SHORT fixture (mirror): prior highs 105(first)/103/102 -> max=105, ref=H[i-N]=105
PRIOR_D = (100, 105, 95, 100)
PRIOR_E = (100, 103, 95, 100)
PRIOR_F = (100, 102, 95, 100)
BREAK_SHORT = (106, 110, 103, 104)  # high=110>105 (new high), close=104<105 (reclaim) -> SHORT
NO_RECLAIM_SHORT = (106, 110, 103, 108)  # high=110>105 (new high), close=108>=105 -> genuine breakout, no signal


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


def test_failed_breakdown_fades_long_with_sl_at_swept_low():
    store = make_store([PRIOR_A, PRIOR_B, PRIOR_C, BREAK_LONG])
    [ev] = TurtleSoupDetector(PARAMS).detect(ctx_at(store, 4))
    assert ev.detector == "turtle_soup"
    assert ev.direction is Direction.LONG
    # raw swept low; atr None on this 4-bar fixture -> sl_floor "0"
    assert ev.meta == {"event": "TURTLE_SOUP", "sl": str(tick(90)), "sl_floor": "0"}
    assert ev.zone == (tick(90) - TICK, tick(90) + TICK)
    assert ev.ttl_candles == 3
    assert 0.0 < ev.strength <= 1.0


def test_failed_breakout_fades_short_with_sl_at_swept_high():
    store = make_store([PRIOR_D, PRIOR_E, PRIOR_F, BREAK_SHORT])
    [ev] = TurtleSoupDetector(PARAMS).detect(ctx_at(store, 4))
    assert ev.direction is Direction.SHORT
    assert ev.meta == {"event": "TURTLE_SOUP", "sl": str(tick(110)), "sl_floor": "0"}
    assert ev.zone == (tick(110) - TICK, tick(110) + TICK)
    assert 0.0 < ev.strength <= 1.0


def test_new_low_without_reclaim_is_genuine_breakout_no_signal():
    store = make_store([PRIOR_A, PRIOR_B, PRIOR_C, NO_RECLAIM])
    assert TurtleSoupDetector(PARAMS).detect(ctx_at(store, 4)) == []


def test_new_high_without_reclaim_is_genuine_breakout_no_signal():
    store = make_store([PRIOR_D, PRIOR_E, PRIOR_F, NO_RECLAIM_SHORT])
    assert TurtleSoupDetector(PARAMS).detect(ctx_at(store, 4)) == []


def test_no_lookahead_before_qualifying_bar_closes():
    store = make_store([PRIOR_A, PRIOR_B, PRIOR_C, BREAK_LONG])
    assert TurtleSoupDetector(PARAMS).detect(ctx_at(store, 3)) == []  # only 3 prior closed


def test_dedupe_one_fire_per_qualifying_bar():
    store = make_store([PRIOR_A, PRIOR_B, PRIOR_C, BREAK_LONG])
    det = TurtleSoupDetector(PARAMS)
    [ev] = det.detect(ctx_at(store, 4))
    assert det.detect(ctx_at(store, 4)) == []  # same tick again: no duplicate


def test_on_session_end_keeps_newest_dedupe():
    # Continuum: the just-fired bar is still window[-1] across the boundary,
    # so its dedupe entry must survive on_session_end (age-prune only).
    store = make_store([PRIOR_A, PRIOR_B, PRIOR_C, BREAK_LONG])
    det = TurtleSoupDetector(PARAMS)
    det.detect(ctx_at(store, 4))
    det.on_session_end()
    assert det.detect(ctx_at(store, 4)) == []


def test_default_params_require_n_plus_one_bars():
    store = make_store([PRIOR_A])
    assert TurtleSoupDetector({}).detect(ctx_at(store, 1)) == []  # N=20 default, far short


def test_continuum_cross_day_fade():
    """CONTINUUM (validated): PRIOR_A/B/C close out day 1; BREAK_LONG is day
    2's first candle. liq_hunt.py::turtle_soup was measured on one
    concatenated multi-day series, so the N-bar window legitimately spans
    the overnight gap: the fade MUST fire on day 2's very first tick."""
    day1 = SESSION_START
    day2 = day1 + timedelta(days=1)
    store = CandleStore("/nonexistent")
    for i, (o, h, l, c) in enumerate([PRIOR_A, PRIOR_B, PRIOR_C]):
        store.add(Candle("X", M1, day1 + timedelta(minutes=5 * i),
                         tick(o), tick(h), tick(l), tick(c), 10))
    o, h, l, c = BREAK_LONG
    store.add(Candle("X", M1, day2, tick(o), tick(h), tick(l), tick(c), 10))

    det = TurtleSoupDetector(PARAMS)
    det.on_session_end()                    # boundary hook must not blind day 2
    now = day2 + timedelta(minutes=M5.minutes)
    ctx = StockContext(symbol="X", now=now, candles=store.view("X", now),
                       levels=[], evidence_history=[],
                       day=DayState(session_date=now.date()))
    [ev] = det.detect(ctx)                  # window spans the boundary: fires
    assert ev.direction is Direction.LONG
    assert ev.meta["sl"] == str(tick(90))


# --------------------------------------------------------------------------
# PARITY GATE -- real continuum data vs liq_hunt.py::turtle_soup (validated ref)
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


def _turtle_soup_ref(m5, N=20):
    """Verbatim port of the scratchpad reference liq_hunt.py::turtle_soup
    (its ``atrs``/``mins`` params are unused in the body, so dropped here)."""
    H = [float(c.high) for c in m5]
    L = [float(c.low) for c in m5]
    C = [float(c.close) for c in m5]
    ev = []
    for i in range(N, len(m5)):
        if L[i] < min(L[i - N:i]) and C[i] > L[i - N]:
            ev.append((i, 1, L[i]))
        elif H[i] > max(H[i - N:i]) and C[i] < H[i - N]:
            ev.append((i, -1, H[i]))
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
    """PARITY GATE: for each symbol, run liq_hunt.py::turtle_soup (inlined,
    verbatim, N=20) over the full session-anchored continuum M5 series, and
    assert the detector -- driven tick-by-tick, on_session_end at every
    session boundary -- reproduces EXACTLY the same event sequence (ts,
    direction, sl). No allowed differences: unlike compress_fade, each
    qualifying bar i maps to at most one event AT i itself (no lookahead), so
    output order is already strictly chronological on both sides -- plain
    list equality holds, no sorting needed. sl_floor is ATR-gated but
    detect()'s emission itself is not, so there is no ATR-warmup gap either."""
    total = 0
    dirs = set()
    for symbol in _SYMBOLS:
        m1 = _load_m1(symbol)
        det = TurtleSoupDetector({})            # default N=20, matches ref default
        got, m5 = _feed_real(m1, det, symbol)
        ref = _turtle_soup_ref(m5)
        expected = [(m5[i].ts, Direction.LONG if d == 1 else Direction.SHORT,
                    Decimal(str(x))) for i, d, x in ref]
        assert got == expected, symbol
        total += len(expected)
        dirs |= {d for _, d, _ in expected}
    assert total > 10                            # fixture exercises the detector
    assert dirs == {Direction.LONG, Direction.SHORT}
