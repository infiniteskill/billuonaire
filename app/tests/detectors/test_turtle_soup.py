"""Tests for the turtle_soup detector (trader/detectors/turtle_soup.py).
Binding design: v2-task7 brief (port of liq_hunt.py::turtle_soup) -- a new
N-bar low that closes back above the prior N-bar low (failed breakdown) is
FADED long, sl = the swept low; mirror for a new N-bar high closing back
below the prior N-bar high (failed breakout) -> fade short. Signal-emitter
only, no Levels.

Fixtures use N=3 (not the N=20 production default) so a qualifying bar fits
in a manageable number of bars (window = N+1 = 4)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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
    assert ev.meta["sl"] == tick(90)
    assert ev.meta["event"] == "TURTLE_SOUP"
    assert ev.zone == (tick(90) - TICK, tick(90) + TICK)
    assert ev.ttl_candles == 3
    assert 0.0 < ev.strength <= 1.0


def test_failed_breakout_fades_short_with_sl_at_swept_high():
    store = make_store([PRIOR_D, PRIOR_E, PRIOR_F, BREAK_SHORT])
    [ev] = TurtleSoupDetector(PARAMS).detect(ctx_at(store, 4))
    assert ev.direction is Direction.SHORT
    assert ev.meta["sl"] == tick(110)
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


def test_on_session_end_clears_dedupe():
    store = make_store([PRIOR_A, PRIOR_B, PRIOR_C, BREAK_LONG])
    det = TurtleSoupDetector(PARAMS)
    det.detect(ctx_at(store, 4))
    det.on_session_end()
    [ev] = det.detect(ctx_at(store, 4))
    assert ev.direction is Direction.LONG


def test_default_params_require_n_plus_one_bars():
    store = make_store([PRIOR_A])
    assert TurtleSoupDetector({}).detect(ctx_at(store, 1)) == []  # N=20 default, far short


def test_session_boundary_no_cross_day_fade():
    """PRIOR_A/B/C close out day 1; BREAK_LONG is day 2's first candle. The
    old ctx.candles.last(N+2, tf) window would span the session boundary,
    mixing day 1's prior lows with day 2's break bar into a false LONG fade
    on day 2's very first tick. Session-scoped ctx.candles.today(tf) means
    day 2 hasn't got N+1=4 bars of its own yet, so nothing fires."""
    day1 = SESSION_START
    day2 = day1 + timedelta(days=1)
    store = CandleStore("/nonexistent")
    for i, (o, h, l, c) in enumerate([PRIOR_A, PRIOR_B, PRIOR_C]):
        store.add(Candle("X", M1, day1 + timedelta(minutes=5 * i),
                         tick(o), tick(h), tick(l), tick(c), 10))
    o, h, l, c = BREAK_LONG
    store.add(Candle("X", M1, day2, tick(o), tick(h), tick(l), tick(c), 10))

    det = TurtleSoupDetector(PARAMS)
    now = day2 + timedelta(minutes=M5.minutes)
    ctx = StockContext(symbol="X", now=now, candles=store.view("X", now),
                       levels=[], evidence_history=[],
                       day=DayState(session_date=now.date()))
    assert det.detect(ctx) == []            # no cross-session fade

    # a genuine day-2-only PRIOR/BREAK sequence DOES fire, from day-2 candles only
    for i, (o, h, l, c) in enumerate([PRIOR_A, PRIOR_B, PRIOR_C, BREAK_LONG], start=1):
        store.add(Candle("X", M1, day2 + timedelta(minutes=5 * i),
                         tick(o), tick(h), tick(l), tick(c), 10))
    now2 = day2 + timedelta(minutes=5 * 5)
    ctx2 = StockContext(symbol="X", now=now2, candles=store.view("X", now2),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now2.date()))
    [ev] = det.detect(ctx2)
    assert ev.direction is Direction.LONG
    assert ev.meta["sl"] == tick(90)
