"""TemplateClassifier unit tests: rule table, lock timing, day reset.

Contexts are built by hand (levels + evidence_history injected); the
classifier never touches candles, so ``candles=None`` is fine here.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from trader.engine.context import DayState, StockContext
from trader.engine.template import TemplateClassifier
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState
from trader.models.market import NSE
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
DAY = date(2026, 7, 15)
OPEN = datetime.combine(DAY, time(9, 15), tzinfo=IST)
Z = (Decimal("99"), Decimal("101"))


def at(minute: int) -> datetime:
    return OPEN + timedelta(minutes=minute)


def level(kind: LevelKind, *states: LevelState, symbol: str = "X") -> Level:
    lv = Level(id=f"{symbol}-{kind.name}", symbol=symbol, kind=kind,
               zone=Z, born=at(15), tf=None)
    for i, st in enumerate(states):
        lv.record_state(at(20 + 5 * i), st)
    return lv


def ev(event: str, direction: Direction, minute: int = 60) -> Evidence:
    return Evidence(detector="structure", direction=direction, strength=0.6,
                    zone=Z, ts=at(minute), ttl_candles=12, meta={"event": event})


def ctx(minute: int, levels=(), history=(), day: DayState | None = None) -> StockContext:
    return StockContext(symbol="X", now=at(minute), candles=None,
                        levels=list(levels), evidence_history=list(history),
                        day=day or DayState(session_date=DAY))


ORH, ORL = LevelKind.OPEN_RANGE_H, LevelKind.OPEN_RANGE_L
SWEPT, RECLAIMED, TESTED = LevelState.SWEPT, LevelState.RECLAIMED, LevelState.TESTED
BOTH_SWEPT = [level(ORH, SWEPT), level(ORL, SWEPT, RECLAIMED)]


def classify(minute: int, levels=(), history=()) -> str:
    return TemplateClassifier(NSE).update(ctx(minute, levels, history))


# ---------------------------------------------------------------- rule table

def test_double_trap_both_edges_swept():
    assert classify(135, BOTH_SWEPT) == "DOUBLE_TRAP"


def test_double_trap_counts_reclaimed_as_swept():
    lvls = [level(ORH, SWEPT, RECLAIMED), level(ORL, SWEPT, RECLAIMED)]
    assert classify(135, lvls, [ev("CHOCH", Direction.LONG)]) == "DOUBLE_TRAP"


def test_trap_reversal_one_edge_swept_reclaimed_with_choch():
    lvls = [level(ORH, TESTED), level(ORL, SWEPT, RECLAIMED)]
    assert classify(135, lvls, [ev("CHOCH", Direction.LONG)]) == "TRAP_REVERSAL"


def test_swept_without_reclaim_is_not_trap_reversal():
    lvls = [level(ORH), level(ORL, SWEPT)]
    assert classify(135, lvls, [ev("CHOCH", Direction.LONG)]) == "UNCLASSIFIED"


def test_reclaim_without_choch_is_not_trap_reversal():
    lvls = [level(ORH), level(ORL, SWEPT, RECLAIMED)]
    assert classify(135, lvls) == "UNCLASSIFIED"


def test_trend_two_bos_same_direction_no_reclaim():
    hist = [ev("BOS", Direction.LONG, 60), ev("BOS", Direction.LONG, 90)]
    assert classify(135, [level(ORH), level(ORL)], hist) == "TREND"


def test_trend_allows_swept_unreclaimed_edge():
    lvls = [level(ORH, SWEPT), level(ORL)]
    hist = [ev("BOS", Direction.LONG, 60), ev("BOS", Direction.LONG, 90)]
    assert classify(135, lvls, hist) == "TREND"


def test_trend_needs_same_direction_bos():
    hist = [ev("BOS", Direction.LONG, 60), ev("BOS", Direction.SHORT, 90)]
    assert classify(135, [level(ORH), level(ORL)], hist) == "UNCLASSIFIED"


def test_reclaimed_edge_blocks_trend():
    lvls = [level(ORH), level(ORL, SWEPT, RECLAIMED)]
    hist = [ev("BOS", Direction.LONG, 60), ev("BOS", Direction.LONG, 90)]
    assert classify(135, lvls, hist) == "UNCLASSIFIED"  # and no CHoCH


def test_range_pin_no_sweep_few_bos():
    lvls = [level(ORH, TESTED), level(ORL)]
    assert classify(135, lvls, [ev("BOS", Direction.LONG)]) == "RANGE_PIN"


def test_missing_or_levels_fail_closed_unclassified():
    # audit 5: no opening-range levels = no information, never a tradable
    # RANGE_PIN (the old RANGE_PIN answer here was the fail-open bug)
    assert classify(10) == "UNCLASSIFIED"
    assert classify(135) == "UNCLASSIFIED"
    assert classify(135, [level(ORH)]) == "UNCLASSIFIED"   # one edge alone too


def test_ignores_other_symbols_levels():
    foreign = [level(ORH, SWEPT, symbol="Y"), level(ORL, SWEPT, symbol="Y")]
    # foreign sweeps never classify this symbol; with no OWN OR levels the
    # answer is UNCLASSIFIED (audit 5 fail-closed; was RANGE_PIN)
    assert classify(135, foreign) == "UNCLASSIFIED"


def test_only_structure_evidence_counts():
    stray = Evidence(detector="sweep", direction=Direction.LONG, strength=0.6,
                     zone=Z, ts=at(60), ttl_candles=12, meta={"event": "CHOCH"})
    lvls = [level(ORH), level(ORL, SWEPT, RECLAIMED)]
    assert classify(135, lvls, [stray]) == "UNCLASSIFIED"


# -------------------------------------------------- gap fade-bias (axiom 18)

def _gap_view(open_px: float):
    """Prev-day calm M5s (range 2 => ATR ~2, close 100) + today's open."""
    store = CandleStore("/nonexistent")
    prev = datetime.combine(DAY - timedelta(days=1), time(9, 15), tzinfo=IST)
    m1 = lambda ts, o: Candle("X", Timeframe.M1, ts, tick(o), tick(o + 1),
                              tick(o - 1), tick(o), 100)
    for i in range(15):
        store.add(m1(prev + timedelta(minutes=5 * i), 100))
    store.add(m1(OPEN, open_px))
    return store.view("X", at(6))


@pytest.mark.parametrize("open_px,want", [(105, Direction.LONG),
                                          (95, Direction.SHORT), (100.5, None)])
def test_gap_dir_detected_from_candles(open_px, want):
    day = DayState(session_date=DAY)
    c = StockContext(symbol="X", now=at(6), candles=_gap_view(open_px),
                     levels=[], evidence_history=[], day=day)
    TemplateClassifier(NSE).update(c)
    assert day.gap_dir is want


def gap_day() -> DayState:
    return DayState(session_date=DAY, gap_dir=Direction.LONG)


def test_gap_direction_drive_one_bos_is_trap():
    lvls = [level(ORH), level(ORL)]         # would be RANGE_PIN without gap
    c = ctx(135, lvls, [ev("BOS", Direction.LONG)], gap_day())
    assert TemplateClassifier(NSE).update(c) == "UNCLASSIFIED"


def test_gap_direction_two_bos_locks_trend():
    hist = [ev("BOS", Direction.LONG, 60), ev("BOS", Direction.LONG, 90)]
    c = ctx(135, [level(ORH), level(ORL)], hist, gap_day())
    assert TemplateClassifier(NSE).update(c) == "TREND"


def test_gap_fade_direction_unaffected():
    c = ctx(135, [level(ORH), level(ORL)], [ev("BOS", Direction.SHORT)], gap_day())
    assert TemplateClassifier(NSE).update(c) == "RANGE_PIN"


# ------------------------------------------------------------ locking + state

EDGES = [level(ORH), level(ORL)]  # quiet OR pair: classifies RANGE_PIN


def test_provisional_before_lock_tracks_changes_and_writes_day():
    clf = TemplateClassifier(NSE)
    day = DayState(session_date=DAY)
    assert clf.update(ctx(30, EDGES, day=day)) == "RANGE_PIN"
    assert day.template == "RANGE_PIN"
    c = ctx(60, BOTH_SWEPT, day=day)
    assert clf.update(c) == "DOUBLE_TRAP"
    assert day.template == "DOUBLE_TRAP"


def test_locks_at_lock_minute_and_freezes():
    clf = TemplateClassifier(NSE)
    day = DayState(session_date=DAY)
    assert clf.update(ctx(130, EDGES, day=day)) == "RANGE_PIN"  # still provisional
    assert clf.update(ctx(135, EDGES, day=day)) == "RANGE_PIN"  # locks here (11:30)
    after = ctx(200, BOTH_SWEPT, day=day)                   # evidence now says DOUBLE_TRAP
    assert clf.update(after) == "RANGE_PIN"                 # but the lock holds
    assert day.template == "RANGE_PIN"


def test_lock_minute_param():
    clf = TemplateClassifier(NSE, {"lock_min": 30})
    day = DayState(session_date=DAY)
    assert clf.update(ctx(30, EDGES, day=day)) == "RANGE_PIN"
    assert clf.update(ctx(60, BOTH_SWEPT, day=day)) == "RANGE_PIN"


def test_new_session_resets_lock():
    clf = TemplateClassifier(NSE)
    assert clf.update(ctx(140, EDGES)) == "RANGE_PIN"       # locked for DAY
    nxt = DAY + timedelta(days=1)
    c = StockContext(symbol="X", now=at(140) + timedelta(days=1), candles=None,
                     levels=BOTH_SWEPT, evidence_history=[],
                     day=DayState(session_date=nxt))
    assert clf.update(c) == "DOUBLE_TRAP"                   # fresh lock, new day
