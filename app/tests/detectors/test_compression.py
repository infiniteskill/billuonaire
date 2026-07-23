"""Tests for the compression detector (trader/detectors/compression.py).
Binding design: task-7 brief / dev/plan/06 SS5 (+ SS3 leg-FSM driving)."""

from datetime import datetime, timedelta
from decimal import Decimal

from zoneinfo import ZoneInfo

from trader.detectors.compression import CompressionDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M1 = Timeframe.M1


def bar_ts(i):  # one M1 per 5m bucket -> one 5m candle per bucket
    return SESSION_START + timedelta(minutes=5 * i)


def bar(i, o, h, l, c, v):
    return Candle("X", M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_ctx(candles, levels=None, history=None, day=None):
    store = CandleStore("/nonexistent")
    for cd in candles:
        store.add(cd)
    now = candles[-1].ts + timedelta(minutes=5)
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=levels if levels is not None else [],
                        evidence_history=history if history is not None else [],
                        day=day or DayState(session_date=now.date()))


# 4 wide filler candles + the 12-candle window: first 4 wide (range 3.0),
# tapering middle, last 6 narrow with overlapping bodies (all contain
# [100.20, 100.25]) and contracting volume. Expected: contraction
# 0.925/3.0 < 0.6, overlap yes, vol slope < 0, NR-cluster >= 2 => score 1.0.
# Box = min low / max high of last 6 = (99.40, 100.90) at candle 15.
COILED = [bar(i, 100, "101.5", "98.5", "100.5", 520 - 5 * i) for i in range(4)] + [
    bar(4, 100, "101.5", "98.5", "100.5", 500),
    bar(5, 100, "101.5", "98.5", "100.5", 480),
    bar(6, 100, "101.5", "98.5", "100.5", 460),
    bar(7, 100, "101.5", "98.5", "100.5", 440),
    bar(8, 100, 101, 99, "100.3", 420),
    bar(9, "100.3", 101, 99, 100, 400),
    bar(10, 100, "100.8", "99.4", "100.4", 380),
    bar(11, "100.4", "100.9", "99.5", "100.1", 360),
    bar(12, "100.1", "100.6", "99.6", "100.3", 340),
    bar(13, "100.3", "100.55", "99.55", "100.15", 320),
    bar(14, "100.15", "100.5", "99.6", "100.25", 300),
    bar(15, "100.25", "100.45", "99.65", "100.2", 280),
]
BOX = (tick("99.40"), tick("100.90"))
SWEEP = bar(16, "99.7", "99.9", 99, "99.7", 300)          # wick under 99.40, reclaim
DISPLACE = bar(17, 100, "104.1", "99.9", 104, 600)        # >= mid+1.5*ATR, up

# 12 identical candles: contraction ratio 1.0, vol slope 0 => score < 0.7.
FLAT = [bar(i, 100, 101, 99, "100.5", 100) for i in range(12)]


def bos_evidence(ts):
    return Evidence(detector="structure", direction=Direction.LONG, strength=0.6,
                    zone=(tick(100), tick(101)), ts=ts, ttl_candles=12,
                    meta={"event": "BOS"})


def ob_level(zone):
    return Level(id="OB1", symbol="X", kind=LevelKind.OB_BULL, zone=zone,
                 born=SESSION_START, tf=Timeframe.M5)


# ---- compression scoring + box registration ----

def test_coiled_cluster_confirms_box_and_arms_leg_fsm():
    ctx = make_ctx(COILED)

    out = CompressionDetector({}).detect(ctx)

    assert out == []  # box confirmation alone emits nothing without a level
    fsm = ctx.day.po3["leg"]
    assert fsm.state == "ACCUMULATION"
    assert fsm.box == BOX
    assert fsm.box_ts == bar_ts(15)


def test_non_compressing_window_is_silent():
    ctx = make_ctx(FLAT)

    out = CompressionDetector({}).detect(ctx)

    assert out == []
    assert ctx.day.po3["leg"].state == "IDLE"


def test_active_sequence_not_clobbered_by_new_confirmation():
    day = DayState(session_date=SESSION_START.date())
    det = CompressionDetector({})
    det.detect(make_ctx(COILED, day=day))
    fsm = day.po3["leg"]
    fsm.state = "MANIPULATION"  # simulate an active sequence

    det.detect(make_ctx(COILED, day=day))

    assert fsm.state == "MANIPULATION"  # set_box not called


# ---- BOX_ON_LEVEL ----

def test_box_on_active_ob_level_emits_075_at_confirmation():
    level = ob_level((tick(99), tick("99.8")))  # overlaps box low edge
    ctx = make_ctx(COILED, levels=[level])

    [ev] = CompressionDetector({}).detect(ctx)

    assert ev.detector == "compression"
    assert ev.direction is Direction.LONG  # OB_BULL direction
    assert ev.strength == 0.75
    assert ev.zone == BOX
    assert ev.meta["event"] == "BOX_ON_LEVEL"
    assert ev.meta["level_id"] == "OB1"
    assert 0.0 <= ev.meta["maturity"] <= 1.0   # taught coil/maturity grade scalar


def test_box_not_on_level_no_bonus():
    level = ob_level((tick(90), tick(91)))  # far below the box
    ctx = make_ctx(COILED, levels=[level])

    assert CompressionDetector({}).detect(ctx) == []


def test_box_on_level_deduped_per_box_ts():
    level = ob_level((tick(99), tick("99.8")))
    day = DayState(session_date=SESSION_START.date())
    det = CompressionDetector({})
    assert len(det.detect(make_ctx(COILED, levels=[level], day=day))) == 1

    day.po3["leg"].state = "IDLE"  # force re-confirmation of the same box
    assert det.detect(make_ctx(COILED, levels=[level], day=day)) == []


# ---- PO3_DIST end-to-end via detector stepping the FSM ----

def _run_to_distribution(det, day, history):
    det.detect(make_ctx(COILED, history=history, day=day))                    # box
    det.detect(make_ctx(COILED + [SWEEP], history=history, day=day))          # sweep
    history.append(bos_evidence(DISPLACE.ts))
    return det.detect(make_ctx(COILED + [SWEEP, DISPLACE],
                               history=history, day=day))


def test_po3_dist_evidence_end_to_end():
    day, history = DayState(session_date=SESSION_START.date()), []
    det = CompressionDetector({})

    out = _run_to_distribution(det, day, history)

    assert day.po3["leg"].swept_side == "low"
    [ev] = out
    assert ev.detector == "compression"
    assert ev.direction is Direction.LONG
    assert ev.strength == 0.85
    assert ev.zone == BOX
    assert ev.ttl_candles == 24
    assert ev.meta["event"] == "PO3_DIST"
    # energy = box height 1.50 x expansion_factor 2.5
    assert Decimal(ev.meta["energy"]) == Decimal("3.75")


def test_no_dist_without_recent_bos_evidence():
    day, history = DayState(session_date=SESSION_START.date()), []
    det = CompressionDetector({})
    det.detect(make_ctx(COILED, history=history, day=day))
    det.detect(make_ctx(COILED + [SWEEP], history=history, day=day))

    out = det.detect(make_ctx(COILED + [SWEEP, DISPLACE], history=history, day=day))

    assert out == []
    assert day.po3["leg"].state == "MANIPULATION"


def test_po3_dist_deduped_per_box_ts():
    day, history = DayState(session_date=SESSION_START.date()), []
    det = CompressionDetector({})
    assert len(_run_to_distribution(det, day, history)) == 1

    day.po3["leg"].state = "MANIPULATION"  # force the transition to re-fire
    out = det.detect(make_ctx(COILED + [SWEEP, DISPLACE], history=history, day=day))

    assert out == []
