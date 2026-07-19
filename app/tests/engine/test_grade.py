"""Zone-graph grading (runs/taught/TUNE.md frozen composite): nst birth-
structure dedup, propulsion parent cascade, 0.5xATR depth-alive law,
pivot distance component, and the journal-only context tags."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from trader.engine.grade import context_tags, zone_grade
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState

IST = ZoneInfo("Asia/Kolkata")
D = Decimal
DAY = date(2026, 7, 14)
M5 = timedelta(minutes=5)
BAND = (D("99"), D("101"))


def at(hh, mm):
    return datetime.combine(DAY, time(hh, mm), tzinfo=IST)


def c(ts, o, h, lo, cl, tf=Timeframe.M5):
    return Candle("X", tf, ts, D(str(o)), D(str(h)), D(str(lo)), D(str(cl)), 100)


def lv(kind=LevelKind.OB_BULL, lo="99", hi="101", born=None, id="z", **extra):
    out = Level(id=id, symbol="X", kind=kind, zone=(D(lo), D(hi)),
                born=born or at(10, 0), tf=Timeframe.M5)
    for k, v in extra.items():
        setattr(out, k, v)
    return out


def stub(name, **kw):    # future-kind level (PRP_/EXT_ land with new detectors)
    base = dict(kind=SimpleNamespace(name=name), zone=(D("99"), D("101")),
                born=at(10, 0), tf=Timeframe.M5, state=LevelState.ACTIVE,
                id=name, symbol="X")
    return SimpleNamespace(**{**base, **kw})


class View:
    def __init__(self, m5=(), h1=(), d1=(), prev=()):
        self.series = {Timeframe.M5: list(m5), Timeframe.H1: list(h1),
                       Timeframe.D1: list(d1)}
        self.prev = list(prev)

    def last(self, n, tf):
        return self.series.get(tf, [])[-n:]

    def today(self, tf):
        return self.series.get(tf, [])

    def prev_day(self, tf):
        return self.prev


def ctx_for(levels=(), view=None, history=(), now=None, atr=D("1")):
    return SimpleNamespace(candles=view, levels=list(levels),
                           evidence_history=list(history),
                           now=now or at(11, 30),
                           atr=lambda tf, period=14: atr)


# ------------------------------------------------------------ nst stacking

def test_nst_dedup_same_birth_chain():
    """Same kind born within 2 bars chain into ONE structure (TUNE merge)."""
    zs = [lv(id="a"), lv(id="b", born=at(10, 5)), lv(id="c", born=at(10, 30))]
    assert zone_grade(ctx_for(zs), Direction.LONG, BAND).nst == 2


def test_nst_birth_id_wins_over_proximity():
    zs = [lv(id="a", birth_id="leg"), lv(id="b", born=at(11, 0), birth_id="leg"),
          lv(id="c", born=at(11, 0))]
    assert zone_grade(ctx_for(zs), Direction.LONG, BAND).nst == 2


def test_nst_propulsion_child_shares_parent_structure():
    zs = [lv(id="p"), stub("PRP_BULL", parent_id="p", born=at(11, 0))]
    assert zone_grade(ctx_for(zs), Direction.LONG, BAND).nst == 1


def test_nst_exact_overlap_direction_and_liveness():
    dead = lv(id="d", born=at(10, 30))
    dead.state = LevelState.DEAD
    zs = [lv(id="a"),                                     # counts
          lv(id="b", kind=LevelKind.OB_BEAR, born=at(10, 30)),  # wrong side
          lv(id="c", lo="101.5", hi="102", born=at(11, 0)),     # disjoint band
          dead]                                                 # terminal
    assert zone_grade(ctx_for(zs), Direction.LONG, BAND).nst == 1


def test_nst_different_kind_same_bar_two_structures():
    zs = [lv(id="a"), lv(id="b", kind=LevelKind.FVG_BULL)]
    assert zone_grade(ctx_for(zs), Direction.LONG, BAND).nst == 2


def test_g_composite_and_stack_threshold():
    zs = [lv(id=str(i), born=at(10, 0) + i * 3 * M5) for i in range(4)]
    zg = zone_grade(ctx_for(zs), Direction.LONG, BAND)
    assert (zg.nst, zg.parent_ok, zg.depth_alive, zg.g) == (4, True, True, 3)
    assert zone_grade(ctx_for(zs[:3]), Direction.LONG, BAND).g == 2  # nst<4


# --------------------------------------------------------- parent cascade

def test_parent_cascade():
    prp, parent = stub("PRP_BULL", parent_id="p"), lv(id="p", lo="97", hi="98")
    ctx = ctx_for([prp, parent])
    assert zone_grade(ctx, Direction.LONG, BAND).parent_ok
    parent.state = LevelState.MITIGATED               # parent dies -> cascade
    assert not zone_grade(ctx, Direction.LONG, BAND).parent_ok
    assert not zone_grade(ctx_for([stub("PRP_BULL")]), Direction.LONG,
                          BAND).parent_ok             # orphan: no linkage
    assert zone_grade(ctx_for([lv()]), Direction.LONG, BAND).parent_ok  # vacuous


# ------------------------------------------------------------ depth-alive

def test_depth_alive_kill_and_shallow_second_life():
    shallow = [c(at(10, 5), 100, 100.5, 98.4, 98.6)]  # 0.4 below lo: lives
    assert zone_grade(ctx_for([lv()], view=View(m5=shallow)),
                      Direction.LONG, BAND).depth_alive
    deep = shallow + [c(at(10, 10), 98.6, 98.6, 98.4, 98.5)]  # 0.5xATR: dead
    assert not zone_grade(ctx_for([lv()], view=View(m5=deep)),
                          Direction.LONG, BAND).depth_alive


def test_depth_alive_ignores_pre_birth_and_short_mirror():
    pre = [c(at(9, 30), 100, 100.5, 98, 98.4)]        # deep close BEFORE birth
    assert zone_grade(ctx_for([lv()], view=View(m5=pre)),
                      Direction.LONG, BAND).depth_alive
    bear = [c(at(10, 5), 100, 101.6, 100, 101.5)]     # 0.5 above hi: dead
    assert not zone_grade(
        ctx_for([lv(kind=LevelKind.OB_BEAR)], view=View(m5=bear)),
        Direction.SHORT, BAND).depth_alive


def test_depth_alive_level_flag_wins():
    assert not zone_grade(ctx_for([lv(depth_alive=False)]), Direction.LONG,
                          BAND).depth_alive
    assert not zone_grade(ctx_for([]), Direction.LONG, BAND).depth_alive


# ------------------------------------------------- pivot_dist + journaling

def test_pivot_dist_from_ext_levels_not_in_g():
    ext = stub("EXT_H", zone=(D("103"), D("104")))
    zg = zone_grade(ctx_for([lv(), ext], view=View()), Direction.LONG, BAND)
    assert zg.pivot_dist == 2.0 and zg.g == 2         # journaled, NOT graded
    assert zone_grade(ctx_for([lv()]), Direction.LONG, BAND).pivot_dist is None


def test_parts_payload():
    zg = zone_grade(ctx_for([lv()]), Direction.LONG, BAND)
    assert zg.parts() == {"nst": 1, "parent_ok": True, "depth_alive": True,
                          "pivot_dist": None}


# ------------------------------------------------------------ context tags

def ev(event="CHOCH", direction=Direction.LONG, ts=None, det="structure"):
    return Evidence(det, direction, 0.8, BAND, ts or at(11, 0), 12,
                    {"event": event})


def test_minor_ch_recent_tag():
    ctx = ctx_for(history=[ev()], view=View())
    assert context_tags(ctx, Direction.LONG)["minor_ch_recent"]
    assert not context_tags(ctx, Direction.SHORT)["minor_ch_recent"]
    for stale in (ev(ts=at(11, 30) - 51 * M5), ev(event="BOS")):  # >50 bars/BOS
        assert not context_tags(ctx_for(history=[stale], view=View()),
                                Direction.LONG)["minor_ch_recent"]


def test_po3_wick_signature_tags():
    h1 = c(at(10, 15), 100, 103, 99.8, 100.2, Timeframe.H1)  # body .2, wick 2.8
    d1 = c(at(9, 15), 100, 101, 99, 100.5, Timeframe.D1)     # wick == 0.5xrange
    tags = context_tags(ctx_for(view=View(h1=[h1], d1=[d1])), Direction.LONG)
    assert tags["po3_h1"] and not tags["po3_d1"]


def test_pd_tags_candle_fallback_and_ext_bracket():
    prev = [c(at(9, 15) - timedelta(days=1), 100, 110, 100, 105)]
    today = [c(at(9, 15), 105, 106, 90, 91)]          # range 90-110, close 91
    tags = context_tags(ctx_for(view=View(m5=today, prev=prev)), Direction.LONG)
    assert (tags["pd"], tags["pd_pos"]) == ("discount", 0.05)
    up = [c(at(9, 15), 105, 110, 90, 109)]
    assert context_tags(ctx_for(view=View(m5=up, prev=prev)),
                        Direction.LONG)["pd"] == "premium"
    exts = [stub("EXT_H", zone=(D("120"), D("121"))),
            stub("EXT_L", zone=(D("91"), D("92")))]   # bracket 91-121 wins
    tags = context_tags(ctx_for(exts, view=View(m5=today, prev=prev)),
                        Direction.LONG)
    assert (tags["pd"], tags["pd_pos"]) == ("discount", 0.0)


def test_pd_absent_without_range():
    assert "pd" not in context_tags(ctx_for(view=View()), Direction.LONG)
    assert "pd" not in context_tags(ctx_for(view=None), Direction.LONG)
