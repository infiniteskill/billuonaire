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

from trader.config import Settings
from trader.engine.context import DayState, StockContext
from trader.execution.manager import Action, PositionManager
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind
from trader.models.position import Fill, Position
from trader.models.signal import TradePlan
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
CONFIG = Path(__file__).resolve().parents[2] / "config" / "config.json"
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


def pos(direction=Direction.LONG, stop=None, qty=100, opened=None, partials=()):
    plan_stop = D("95") if direction is Direction.LONG else D("105")
    plan = TradePlan("X", direction, (D("98"), D("100")), plan_stop,
                     [D("105"), D("110"), D("115")], qty, 70.0, TODAY, {})
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
    p = pos()
    acts = mgr.on_candle(p, one_candle_ctx(109, 110.2, 108.8, 110))
    assert [(a.kind, a.qty, a.reason) for a in acts] == \
        [("PARTIAL", 33, "1R"), ("PARTIAL", 33, "2R")]
    assert p.stop == D("100") and p.partials == {"1R", "2R"}


def test_2r_engages_m5_trail(mgr):
    p = pos(stop="100", partials={"1R"})
    lv = swing(LevelKind.SWING_L, 104, 104.1)
    acts = mgr.on_candle(p, one_candle_ctx(109, 110.2, 108.8, 110, levels=[lv]))
    assert acts == [Action("PARTIAL", 33, "2R")]
    assert p.stop == D("104")    # swing lo - 0.1*ATR; ATR None => pad 0


def test_3r_promotes_to_m15_no_third_partial(mgr):
    p = pos(stop="104", partials={"1R", "2R"})
    lvls = [swing(LevelKind.SWING_L, 104, 104.1, tf=Timeframe.M5),
            swing(LevelKind.SWING_L, 108, 108.1, tf=Timeframe.M15)]
    acts = mgr.on_candle(p, one_candle_ctx(114, 115.2, 113.8, 115, levels=lvls))
    assert acts == []
    assert "3R" in p.partials and p.stop == D("108")   # M15 swing, not M5


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
    assert acts == [Action("PARTIAL", 33, "2R")]
    assert p.stop == D("92.10")                 # swing hi + pad, ratchet DOWN


# -- (5) counter-zone / (6) stall --------------------------------------

def test_counter_zone_exit_at_threshold(mgr):
    acts = mgr.on_candle(pos(), one_candle_ctx(101, 102.2, 100.8, 102),
                         counter_zone_score=65)
    assert kinds(acts) == ["EXIT_COUNTER"]


def test_counter_below_threshold_ignored(mgr):
    acts = mgr.on_candle(pos(), one_candle_ctx(101, 102.2, 100.8, 102),
                         counter_zone_score=64.9)
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
