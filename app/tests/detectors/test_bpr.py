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

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from trader.detectors.bpr import BprDetector, _Gap
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

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
