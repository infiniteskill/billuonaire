"""Phase-4 Task 4: PositionManager -- stealth stops, R-ladder, ratchet trail.

Geometry: entry fill 100, planned stop 95 => risk 5 (SHORT: stop 105).
LONG rungs 1R/2R/3R = 105/110/115. Candles are one M1 per M5 bucket; with
fewer than 15 closed M5s ATR(M5) is None so the trail pad is 0 unless the
test builds the full calm history (range 2 => ATR = 2 => pad 0.2).
"""
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.config import ExitsCfg, Settings
from trader.engine.context import DayState, StockContext
from trader.execution.manager import Action, PositionManager, ladder_exits
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind
from trader.models.position import Fill, Position
from trader.models.signal import TradePlan
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
CONFIG = Path(__file__).resolve().parents[2] / "trader" / "templates" / "config.baseline.json"
TODAY = datetime(2026, 7, 15, tzinfo=IST)
D = Decimal


def at(hh, mm):
    return TODAY.replace(hour=hh, minute=mm)


@pytest.fixture
def mgr():
    s = Settings.model_validate_json(CONFIG.read_text())
    return PositionManager(s, s.market_spec())


def m1(ts, o, h, lo, c):
    return Candle("X", Timeframe.M1, ts, D(str(o)), D(str(h)), D(str(lo)), D(str(c)), 100)


def ctx_at(now, candles, levels=()):
    store = CandleStore(Path("/nonexistent"))
    for c in candles:
        store.add(c)
    return StockContext("X", now, store.view("X", now), list(levels), [],
                        DayState(session_date=now.date()))


def one_candle_ctx(o, h, lo, c, ts=None, levels=()):
    ts = ts or at(10, 0)
    return ctx_at(ts + timedelta(minutes=5), [m1(ts, o, h, lo, c)], levels)


def pos(direction=Direction.LONG, stop=None, qty=100, opened=None, partials=(),
        targets=None):
    long = direction is Direction.LONG
    plan_stop = D("95") if long else D("105")
    tg = ([D(t) for t in targets] if targets is not None
          else [D("105"), D("110"), D("115")] if long
          else [D("95"), D("90"), D("85")])
    plan = TradePlan("X", direction, (D("98"), D("100")), plan_stop,
                     tg, qty, 70.0, TODAY, {})
    p = Position(plan=plan, entry=Fill(D("100"), qty, opened or at(10, 0), D("20")),
                 remaining_qty=qty, stop=D(stop) if stop else plan_stop)
    p.partials.update(partials)
    return p


def swing(kind, lo, hi, tf=Timeframe.M5, born=None):
    return Level(f"{kind.name}-{lo}-{born}", "X", kind, (D(str(lo)), D(str(hi))),
                 born or at(9, 30), tf)


def kinds(actions):
    return [a.kind for a in actions]


def test_r_multiple_signed():
    assert pos().r_multiple(D("110")) == 2
    assert pos().r_multiple(D("95")) == -1
    assert pos(Direction.SHORT).r_multiple(D("90")) == 2


def test_r_denominated_on_fill_to_stop_risk():
    # effective R: entry FILL 100.50 (not the plan CE 99.00), plan stop 95
    # => risk_pts 5.50 and every r floats on that fill->stop distance
    p = Position(plan=pos().plan, entry=Fill(D("100.50"), 100, at(10, 0), D("20")),
                 remaining_qty=100, stop=D("95"))
    assert p.risk_pts == D("5.50")
    assert p.r_multiple(D("106.00")) == 1
    assert p.r_multiple(D("89.50")) == -2


# -- (1) EOD squareoff -------------------------------------------------

def test_eod_squareoff_full_exit(mgr):
    acts = mgr.on_candle(pos(), one_candle_ctx(100, 101, 99, 100, ts=at(15, 5)))
    assert acts == [Action("EXIT_EOD", None, "squareoff")]   # now = 15:10


def test_before_squareoff_no_eod(mgr):
    acts = mgr.on_candle(pos(), one_candle_ctx(100, 101, 99, 100, ts=at(15, 0)))
    assert "EXIT_EOD" not in kinds(acts)                     # now = 15:05


def test_eod_wins_over_stop(mgr):
    acts = mgr.on_candle(pos(), one_candle_ctx(95, 95.5, 94, 94.2, ts=at(15, 5)))
    assert kinds(acts) == ["EXIT_EOD"]


# -- (2) stealth stop: close-confirmed only ----------------------------

def test_stop_exits_on_close_beyond_long(mgr):
    acts = mgr.on_candle(pos(), one_candle_ctx(95.5, 95.6, 94.2, 94.5))
    assert acts == [Action("EXIT_STOP", None, "close_beyond_stop")]


def test_wick_through_survives_and_flags(mgr):
    p = pos()
    acts = mgr.on_candle(p, one_candle_ctx(96, 96.5, 94.5, 96))
    assert acts == []
    assert p.hunt_survived is True
    assert p.stop == D("95")


def test_second_consecutive_wick_also_survives(mgr):
    p = pos()
    mgr.on_candle(p, one_candle_ctx(96, 96.5, 94.5, 96, ts=at(10, 0)))
    acts = mgr.on_candle(p, one_candle_ctx(96, 96.5, 94.8, 95.5, ts=at(10, 5)))
    assert acts == []            # wicks NEVER exit; tolerance counts closes
    assert p.hunt_survived is True


def test_stop_mirror_short(mgr):
    acts = mgr.on_candle(pos(Direction.SHORT),
                         one_candle_ctx(104.8, 105.8, 104.5, 105.5))
    assert kinds(acts) == ["EXIT_STOP"]
    p = pos(Direction.SHORT)
    acts = mgr.on_candle(p, one_candle_ctx(104, 105.5, 103.8, 104))
    assert acts == [] and p.hunt_survived is True


# -- (3) R-ladder: partials + breakeven + trail-mode promotion ---------

def test_1r_partial_and_breakeven(mgr):
    p = pos()
    acts = mgr.on_candle(p, one_candle_ctx(104, 105.2, 103.8, 105))
    assert acts == [Action("PARTIAL", 33, "1R")]
    assert p.stop == D("100") and "1R" in p.partials


def test_1r_fires_once(mgr):
    p = pos(stop="100", partials={"1R"})
    assert mgr.on_candle(p, one_candle_ctx(104, 105.2, 103.8, 105)) == []


def test_gap_to_2r_fires_both_rungs(mgr):
    p = pos()                    # high 110.2 touches T2 110: limit fill AT T2
    acts = mgr.on_candle(p, one_candle_ctx(109, 110.2, 108.8, 110))
    assert [(a.kind, a.qty, a.reason, a.price) for a in acts] == \
        [("PARTIAL", 33, "1R", None), ("PARTIAL", 33, "T2", D("110"))]
    assert p.stop == D("100") and p.partials == {"1R", "2R"}


def test_2r_engages_m5_trail(mgr):
    p = pos(stop="100", partials={"1R"})
    lv = swing(LevelKind.SWING_L, 104, 104.1)
    acts = mgr.on_candle(p, one_candle_ctx(109, 110.2, 108.8, 110, levels=[lv]))
    assert acts == [Action("PARTIAL", 33, "T2", D("110"))]   # T2 touched
    assert p.stop == D("104")    # swing lo - 0.1*ATR; ATR None => pad 0


def test_3r_promotes_to_m15_no_third_partial(mgr):
    p = pos(stop="104", partials={"1R", "2R"}, targets=("105", "110"))
    lvls = [swing(LevelKind.SWING_L, 104, 104.1, tf=Timeframe.M5),
            swing(LevelKind.SWING_L, 108, 108.1, tf=Timeframe.M15)]
    acts = mgr.on_candle(p, one_candle_ctx(114, 115.2, 113.8, 115, levels=lvls))
    assert acts == []            # no T3 in plan => runner rides trail/EOD
    assert "3R" in p.partials and p.stop == D("108")   # M15 swing, not M5


# -- target exits merged into the ladder (06 §6) -----------------------

def test_t2_touch_partial_exact_fill_long(mgr):
    p = pos(stop="100", partials={"1R"})   # close 108 => r 1.6 < 2: touch wins
    acts = mgr.on_candle(p, one_candle_ctx(107, 110.2, 106.8, 108))
    assert acts == [Action("PARTIAL", 33, "T2", D("110"))]
    assert "2R" in p.partials


def test_t2_touch_partial_exact_fill_short(mgr):
    p = pos(Direction.SHORT, stop="100", partials={"1R"})  # T2 90
    acts = mgr.on_candle(p, one_candle_ctx(93, 93.5, 89.9, 92))
    assert acts == [Action("PARTIAL", 33, "T2", D("90"))]


def test_2r_close_fires_when_t2_farther_untouched(mgr):
    p = pos(stop="100", partials={"1R"}, targets=("105", "112", "118"))
    acts = mgr.on_candle(p, one_candle_ctx(109, 110.5, 108.8, 110.2))
    assert acts == [Action("PARTIAL", 33, "2R")]    # market, no limit price


def test_t3_touch_exits_final_third_long(mgr):
    p = pos(stop="104", partials={"1R", "2R"})      # T3 115; close r 2.9 < 3
    acts = mgr.on_candle(p, one_candle_ctx(114, 115.2, 113.8, 114.5))
    assert acts == [Action("EXIT_TARGET", None, "T3", D("115"))]


def test_t3_touch_exits_final_third_short(mgr):
    p = pos(Direction.SHORT, stop="96", partials={"1R", "2R"})   # T3 85
    acts = mgr.on_candle(p, one_candle_ctx(86, 87, 84.8, 85.5))
    assert acts == [Action("EXIT_TARGET", None, "T3", D("85"))]


def test_t2_and_t3_same_candle_partial_then_full(mgr):
    p = pos(stop="100", partials={"1R"})            # spike through 110 AND 115
    acts = mgr.on_candle(p, one_candle_ctx(109, 115.5, 108.8, 114))
    assert [(a.kind, a.reason, a.price) for a in acts] == \
        [("PARTIAL", "T2", D("110")), ("EXIT_TARGET", "T3", D("115"))]


# -- (4) trailing ratchet ----------------------------------------------

def test_trail_uses_latest_confirmed_swing(mgr):
    p = pos(stop="100", partials={"1R", "2R"})
    lvls = [swing(LevelKind.SWING_L, 106, 106.1, born=at(9, 40)),
            swing(LevelKind.SWING_L, 103, 103.1, born=at(9, 55))]
    mgr.on_candle(p, one_candle_ctx(106, 107.2, 105.8, 107, levels=lvls))
    assert p.stop == D("103")    # latest-born swing wins, not the higher one


def test_trail_pad_is_tenth_atr(mgr):
    candles = [m1(at(9, 15) + timedelta(minutes=5 * i), 100, 101, 99, 100)
               for i in range(15)]              # 15 closed M5 => ATR = 2
    ctx = ctx_at(at(10, 30), candles, [swing(LevelKind.SWING_L, 104, 104.1)])
    p = pos(stop="98", partials={"1R", "2R"})
    mgr.on_candle(p, ctx)
    assert p.stop == D("103.80")                # 104 - 0.1*2, tick-quantized


def round_lvl(lo, hi):
    return Level(f"X-ROUND-{lo}", "X", LevelKind.ROUND, (D(str(lo)), D(str(hi))),
                 at(9, 30), None)


def test_trail_snaps_off_round_long(mgr):
    # B13: cand 104 within 2 ticks of ROUND zone (103.95, 104.05) edge ->
    # landed round_offset_ticks (3) PAST the far edge: 103.95 - 0.15 = 103.80
    p = pos(stop="100", partials={"1R", "2R"})
    lvls = [swing(LevelKind.SWING_L, 104, 104.1), round_lvl("103.95", "104.05")]
    mgr.on_candle(p, one_candle_ctx(106, 107.2, 105.8, 107, levels=lvls))
    assert p.stop == D("103.80")


def test_trail_snaps_off_round_short(mgr):
    p = pos(Direction.SHORT, stop="96", partials={"1R", "2R"})
    lvls = [swing(LevelKind.SWING_H, 92, 92.1), round_lvl("91.95", "92.05")]
    mgr.on_candle(p, one_candle_ctx(90.5, 91.2, 89.8, 90, levels=lvls))
    assert p.stop == D("92.20")                 # 92.05 + 3 ticks, ratchet DOWN


def test_trail_snap_never_widens(mgr):
    # snapped candidate 103.80 is behind the current 103.85 stop -> no move
    p = pos(stop="103.85", partials={"1R", "2R"})
    lvls = [swing(LevelKind.SWING_L, 104, 104.1), round_lvl("103.95", "104.05")]
    acts = mgr.on_candle(p, one_candle_ctx(106, 107.2, 105.8, 107, levels=lvls))
    assert acts == [] and p.stop == D("103.85")


def test_ratchet_widen_attempt_is_no_move(mgr):
    p = pos(stop="103", partials={"1R", "2R"})
    lv = swing(LevelKind.SWING_L, 101, 101.1)
    acts = mgr.on_candle(p, one_candle_ctx(103.5, 104.2, 103.4, 104, levels=[lv]))
    assert acts == [] and p.stop == D("103")


def test_runtime_guard_raises_on_widen(mgr):
    p = pos()                                   # LONG, stop 95
    with pytest.raises(AssertionError):
        mgr._apply_stop(p, D("90"))
    ps = pos(Direction.SHORT)                   # SHORT, stop 105
    with pytest.raises(AssertionError):
        mgr._apply_stop(ps, D("110"))


def test_short_ladder_and_trail_mirror(mgr):
    p = pos(Direction.SHORT)                    # entry 100, stop 105
    acts = mgr.on_candle(p, one_candle_ctx(95.5, 96.2, 94.8, 95))
    assert acts == [Action("PARTIAL", 33, "1R")] and p.stop == D("100")
    lv = swing(LevelKind.SWING_H, 92, 92.1)
    acts = mgr.on_candle(p, one_candle_ctx(90.5, 91.2, 89.8, 90,
                                           ts=at(10, 5), levels=[lv]))
    assert acts == [Action("PARTIAL", 33, "T2", D("90"))]    # low touched T2 90
    assert p.stop == D("92.10")                 # swing hi + pad, ratchet DOWN


# -- per-signal profit target R (exits.target_r_by_source) -------------

@pytest.fixture
def mgr_sig():
    """Manager whose exits map keys the per-signal profit target R off a
    plan's meta["sl_source"] detector (compression_fade -> 2R, bpr -> 1.5R)."""
    s = Settings.model_validate_json(CONFIG.read_text()).model_copy(
        update={"exits": ExitsCfg(target_r_by_source={
            "compression_fade": 2.0, "bpr": 1.5})})
    return PositionManager(s, s.market_spec())


def sig_pos(source, targets=None):
    """LONG entry 100, stop 95 (risk 5), 1R already banked (stop at breakeven);
    the plan is tagged with meta["sl_source"]=source."""
    p = pos(stop="100", partials={"1R"}, targets=targets)
    p.plan.meta["sl_source"] = source
    return p


def test_compression_fade_plan_takes_profit_at_2r(mgr_sig):
    # sl_source=compression_fade => whole remainder exits AT the 2R close (110),
    # NOT the default 33% 2R partial / 3R M15-trail / T3 tail.
    p = sig_pos("compression_fade")
    acts = mgr_sig.on_candle(p, one_candle_ctx(109, 110.2, 108.8, 110))
    assert acts == [Action("EXIT_TARGET", None, "2.0R")]


def test_compression_fade_holds_below_2r(mgr_sig):
    # r = 1.9 (< 2): no take-profit yet, and the default 2R partial never fires
    p = sig_pos("compression_fade")
    acts = mgr_sig.on_candle(p, one_candle_ctx(109, 109.6, 108.8, 109.5))
    assert acts == []


def test_bpr_plan_takes_profit_at_1_5r(mgr_sig):
    # sl_source=bpr => whole remainder exits AT the 1.5R close (107.5)
    p = sig_pos("bpr")
    acts = mgr_sig.on_candle(p, one_candle_ctx(106, 107.6, 105.8, 107.5))
    assert acts == [Action("EXIT_TARGET", None, "1.5R")]


def test_non_mapped_source_keeps_default_ladder(mgr_sig):
    # sl_source present but NOT in the map => untouched default behavior: at
    # r=2 with T2 farther/untouched the ladder fires its 33% "2R" partial.
    p = sig_pos("inducement", targets=("105", "112", "118"))
    acts = mgr_sig.on_candle(p, one_candle_ctx(109, 110.5, 108.8, 110.2))
    assert acts == [Action("PARTIAL", 33, "2R")]


def test_ladder_exits_charges_only_emittable_tranches(mgr, mgr_sig):
    # audit 5: at qty 1-3 the 33% partial is 0 shares -- no partial rung can
    # emit, only the final exit, so the cost gate must budget 1 exit tranche
    # (2 orders total), whatever the plan's ladder shape says.
    assert ladder_exits(mgr.s) == 3
    assert ladder_exits(mgr_sig.s, "compression_fade") == 2
    for q in (1, 2, 3):
        assert ladder_exits(mgr.s, None, q) == 1
        assert ladder_exits(mgr_sig.s, "compression_fade", q) == 1
    assert ladder_exits(mgr.s, None, 4) == 3          # 4*33//100 = 1: partials live
    assert ladder_exits(mgr_sig.s, "compression_fade", 4) == 2


def test_absent_exits_map_defaults_to_existing_behavior(mgr):
    # default config carries no exits.target_r_by_source: even a
    # compression_fade plan runs the unchanged 3R/T3 ladder.
    p = sig_pos("compression_fade", targets=("105", "112", "118"))
    acts = mgr.on_candle(p, one_candle_ctx(109, 110.5, 108.8, 110.2))
    assert acts == [Action("PARTIAL", 33, "2R")]


# -- (5) counter-zone / (6) stall --------------------------------------

THRESHOLD = Settings.model_validate_json(CONFIG.read_text()).confluence.threshold


def test_counter_zone_exit_at_threshold(mgr):
    acts = mgr.on_candle(pos(), one_candle_ctx(101, 102.2, 100.8, 102),
                         counter_zone_score=THRESHOLD)
    assert kinds(acts) == ["EXIT_COUNTER"]


def test_counter_below_threshold_ignored(mgr):
    """Exactly 0.1 under the shipped arm threshold: the counter-zone exit
    must share the recalibrated confluence scale, not a stale constant."""
    acts = mgr.on_candle(pos(), one_candle_ctx(101, 102.2, 100.8, 102),
                         counter_zone_score=THRESHOLD - 0.1)
    assert acts == []


def test_partial_then_counter_same_candle(mgr):
    acts = mgr.on_candle(pos(), one_candle_ctx(104, 105.2, 103.8, 105),
                         counter_zone_score=80)
    assert kinds(acts) == ["PARTIAL", "EXIT_COUNTER"]


def test_stall_exit_after_18_candles_under_half_r(mgr):
    p = pos(opened=at(10, 0))                   # now 11:30 => 18 M5 candles
    acts = mgr.on_candle(p, one_candle_ctx(101, 102.2, 100.8, 101, ts=at(11, 25)))
    assert kinds(acts) == ["EXIT_STALL"]        # r = 0.2 < 0.5


def test_no_stall_before_18_candles(mgr):
    p = pos(opened=at(10, 0))                   # now 11:25 => 17 candles
    acts = mgr.on_candle(p, one_candle_ctx(101, 102.2, 100.8, 101, ts=at(11, 20)))
    assert acts == []


def test_no_stall_when_progressing(mgr):
    p = pos(opened=at(10, 0))                   # r = 0.6 >= 0.5
    acts = mgr.on_candle(p, one_candle_ctx(103, 104.2, 102.8, 103, ts=at(11, 25)))
    assert acts == []
