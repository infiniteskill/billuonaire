"""Tests for the decision tree (trader/engine/decision.py)."""

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from trader.engine.context import DayState, StockContext
from trader.engine.decision import Decision, decide
from trader.models.candle import tick, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 7, 15, 12, 0, tzinfo=IST)


def ev(detector, direction=Direction.NEUTRAL, zone=(100, 101), **meta):
    return Evidence(detector=detector, direction=direction, strength=0.7,
                    zone=(tick(zone[0]), tick(zone[1])), ts=NOW, ttl_candles=6, meta=meta)


def ctx(ext_h=None, ext_l=None):
    levels = []
    if ext_h is not None:
        levels.append(Level(id="EH", symbol="X", kind=LevelKind.EXT_H,
                            zone=(tick(ext_h), tick(ext_h)), born=NOW, tf=Timeframe.H1,
                            state=LevelState.ACTIVE))
    if ext_l is not None:
        levels.append(Level(id="EL", symbol="X", kind=LevelKind.EXT_L,
                            zone=(tick(ext_l), tick(ext_l)), born=NOW, tf=Timeframe.H1,
                            state=LevelState.ACTIVE))
    st = CandleStore("/nonexistent")
    return StockContext(symbol="X", now=NOW, candles=st.view("X", NOW), levels=levels,
                        evidence_history=[], day=DayState(session_date=NOW.date()))


def _pd(side="discount", permits="LONG"):
    return ev("premium_discount", side=side, permits=permits)


def _zone_long():
    return ev("ob_taught", Direction.LONG, event="OB_RETEST", sl=str(tick(99)))


def test_full_stack_long_takes():
    evs = [_pd(), _zone_long(),
           ev("structure", Direction.LONG, event="BOS"),
           ev("sweep"),
           ev("htf_nest", Direction.LONG, event="NEST", nest_depth=2, ce="100.5", sl="100"),
           ev("compression", event="BOX_ON_LEVEL", maturity=0.7)]
    d = decide(ctx(ext_h=110), evs)
    assert d.take is True
    assert d.direction is Direction.LONG
    assert d.entry == Decimal("100.5")          # from nest CE
    assert d.sl == Decimal("100")               # from nest SL
    assert d.target == tick(110)                # far EXT_H
    assert d.grade == 6                          # bos1+sweep1+(1+nest2)+maturity1
    for r in ("extreme:discount", "bos", "sweep", "nest:2", "runway", "take"):
        assert any(r == x for x in d.reasons), r


def test_mid_pd_skips_no_extreme():
    d = decide(ctx(ext_h=110), [ev("premium_discount", side="mid", permits=None), _zone_long()])
    assert d.take is False and d.direction is None
    assert d.reasons == ["no extreme (p/d mid/absent)"]


def test_no_zone_skips():
    d = decide(ctx(ext_h=110), [_pd()])
    assert d.take is False
    assert "no decisional zone" in d.reasons


def test_no_runway_skips():
    # discount long but NO EXT_H above entry -> no target
    d = decide(ctx(), [_pd(), _zone_long(), ev("structure", Direction.LONG, event="BOS")])
    assert d.take is False
    assert d.target is None and "no runway" in d.reasons


def test_grade_floor_blocks_take():
    # extreme + zone + runway but zero confirmations -> grade 0 < 2
    d = decide(ctx(ext_h=110), [_pd(), _zone_long()])
    assert d.take is False and d.grade == 0
    assert "grade 0<2" in d.reasons


def test_short_side_target_is_ext_l_below():
    evs = [_pd(side="premium", permits="SHORT"),
           ev("ob_taught", Direction.SHORT, event="OB_RETEST", sl=str(tick(102))),
           ev("structure", Direction.SHORT, event="BOS"), ev("sweep")]
    d = decide(ctx(ext_l=90), evs)
    assert d.take is True and d.direction is Direction.SHORT
    assert d.target == tick(90)
    assert d.sl == tick(102)


def test_ote_and_phase_raise_grade():
    # deep-extreme (OTE) + wyckoff phase-alignment each add to the grade
    evs = [ev("premium_discount", side="discount", permits="LONG", ote=True),
           _zone_long(),
           ev("wyckoff", Direction.LONG, event="MARKUP")]
    d = decide(ctx(ext_h=110), evs, min_grade=1)
    assert "ote" in d.reasons and "phase" in d.reasons
    assert d.grade == 2                      # ote(1)+phase(1); no bos/sweep/nest/maturity
    assert d.take is True
