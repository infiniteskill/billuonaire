"""TemplateClassifier unit tests: rule table, lock timing, day reset.

Contexts are built by hand (levels + evidence_history injected); the
classifier never touches candles, so ``candles=None`` is fine here.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from trader.engine.context import DayState, StockContext
from trader.engine.template import TemplateClassifier
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState
from trader.models.market import NSE

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


def test_range_pin_without_or_levels_yet():
    assert classify(10) == "RANGE_PIN"  # provisional: nothing swept, no BOS


def test_ignores_other_symbols_levels():
    foreign = [level(ORH, SWEPT, symbol="Y"), level(ORL, SWEPT, symbol="Y")]
    assert classify(135, foreign) == "RANGE_PIN"


def test_only_structure_evidence_counts():
    stray = Evidence(detector="sweep", direction=Direction.LONG, strength=0.6,
                     zone=Z, ts=at(60), ttl_candles=12, meta={"event": "CHOCH"})
    lvls = [level(ORH), level(ORL, SWEPT, RECLAIMED)]
    assert classify(135, lvls, [stray]) == "UNCLASSIFIED"


# ------------------------------------------------------------ locking + state

def test_provisional_before_lock_tracks_changes_and_writes_day():
    clf = TemplateClassifier(NSE)
    day = DayState(session_date=DAY)
    assert clf.update(ctx(30, day=day)) == "RANGE_PIN"
    assert day.template == "RANGE_PIN"
    c = ctx(60, BOTH_SWEPT, day=day)
    assert clf.update(c) == "DOUBLE_TRAP"
    assert day.template == "DOUBLE_TRAP"


def test_locks_at_lock_minute_and_freezes():
    clf = TemplateClassifier(NSE)
    day = DayState(session_date=DAY)
    assert clf.update(ctx(130, day=day)) == "RANGE_PIN"     # still provisional
    assert clf.update(ctx(135, day=day)) == "RANGE_PIN"     # locks here (11:30)
    after = ctx(200, BOTH_SWEPT, day=day)                   # evidence now says DOUBLE_TRAP
    assert clf.update(after) == "RANGE_PIN"                 # but the lock holds
    assert day.template == "RANGE_PIN"


def test_lock_minute_param():
    clf = TemplateClassifier(NSE, {"lock_min": 30})
    day = DayState(session_date=DAY)
    assert clf.update(ctx(30, day=day)) == "RANGE_PIN"
    assert clf.update(ctx(60, BOTH_SWEPT, day=day)) == "RANGE_PIN"


def test_new_session_resets_lock():
    clf = TemplateClassifier(NSE)
    assert clf.update(ctx(140)) == "RANGE_PIN"              # locked for DAY
    nxt = DAY + timedelta(days=1)
    c = StockContext(symbol="X", now=at(140) + timedelta(days=1), candles=None,
                     levels=BOTH_SWEPT, evidence_history=[],
                     day=DayState(session_date=nxt))
    assert clf.update(c) == "DOUBLE_TRAP"                   # fresh lock, new day
