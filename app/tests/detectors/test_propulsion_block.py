"""Tests for the propulsion_block detector (trader/detectors/propulsion_block.py).
Binding design: ICT Propulsion Block. A live OB_BULL/OB_BEAR Level (written
by orderblock/ob_lux, states ACTIVE/TESTED) is wick-TAPPED by a later candle
whose body respects the zone (bull: low inside the zone, min(O,C) at/above
zone top; bear mirror); within propel_bars(3) following candles price propels
away >= propel_atr(1.0) * ATR close-to-close from the tap close. The tapping
candle IS the propulsion block, its full range the refined zone; the first
later close back inside that zone fires Evidence in the parent OB direction.

Fixture geometry: one M1 candle per M5 bucket start -> the derived M5 bar
equals it exactly. FLAT primes ATR(M5,14) == 2 after 15 closed candles; the
tap candle keeps TR == 2, so need = propel_atr(1.0) * 2 = 2 exactly."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from trader.detectors.base import REGISTRY
from trader.detectors.propulsion_block import PropulsionBlockDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M1, M5 = Timeframe.M1, Timeframe.M5

FLAT = (100, 101, 99, 100)  # doji, TR=2, primes ATR(M5,14) == 2

# --- LONG: OB_BULL zone (96, 98.5); tap wick into zone, body >= zone top ---
TAP_L = (100, 100, 98, 100)              # low 98 in zone, body 100 >= 98.5; TR=2
P1_L = (100, "101.5", "99.5", 101)       # close disp +1 < need 2
P2_L = (101, "102.5", "100.5", 102)      # close disp +2 >= need -> confirm
RETEST_L = (102, "102.5", "98.6", 99)    # close 99 inside propulsion zone (98, 100)
RETEST2_L = (99, "99.5", "98.55", "98.6")  # second close inside zone (post-fire)
VIOL_L = (100, 100, 97, 98)              # body close 98 INSIDE OB zone -> violation
EARLY_L = (100, "100.5", "98.6", 99)     # close inside prop zone BEFORE confirm
MID_L = (99, "101.5", 99, 101)           # filler, disp +1 < need
CONF_L = (101, "102.5", "100.9", 102)    # disp +2 on 3rd following bar -> confirm
W2 = (101, "101.5", 100, "101.5")        # weak leg: max disp +1.5 < need 2
W3 = ("101.5", 102, "100.5", "101.5")

# --- SHORT mirror: OB_BEAR zone (101.5, 104); tap from below ---
TAP_S = (100, 102, 100, 100)             # high 102 in zone, body 100 <= 101.5; TR=2
P1_S = (100, "100.5", "98.5", 99)        # disp -1
P2_S = (99, "99.5", "97.5", 98)          # disp -2 -> confirm
RETEST_S = (98, "101.4", "97.5", 101)    # close 101 inside propulsion zone (100, 102)


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def bar(i, o, h, l, c, v=10):
    return Candle("X", M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_store(bars):
    store = CandleStore("/nonexistent")
    for i, b in enumerate(bars):
        store.add(bar(i, *b))
    return store


def ob(kind, lo, hi, state=LevelState.ACTIVE):
    lv = Level(id=f"X-{kind.name}", symbol="X", kind=kind,
               zone=(tick(lo), tick(hi)), born=bar_ts(0), tf=M5)
    lv.state = state
    return lv


def ctx_at(store, n_bars, levels):
    now = bar_ts(n_bars)
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=levels, evidence_history=[],
                        day=DayState(session_date=now.date()))


def long_bars(tail=(TAP_L, P1_L, P2_L, RETEST_L)):
    return [FLAT] * 15 + list(tail)


def run_to(det, store, levels, n_last):
    """Tick every bar close up to n_last, asserting silence before it;
    return the final tick's output."""
    for n in range(15, n_last):
        assert det.detect(ctx_at(store, n, levels)) == []
    return det.detect(ctx_at(store, n_last, levels))


def test_registered():
    assert REGISTRY["propulsion_block"] is PropulsionBlockDetector
    d = PropulsionBlockDetector({})
    assert d.params == {"tf": "5m", "propel_bars": 3, "propel_atr": 1.0,
                        "sl_atr_floor": 0.15}


def test_long_tap_propel_retest_fires():
    store, levels = make_store(long_bars()), [ob(LevelKind.OB_BULL, 96, "98.5")]
    [ev] = run_to(PropulsionBlockDetector({}), store, levels, 19)
    assert ev.detector == "propulsion_block"
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick(98), tick(100))  # tap candle range, NOT the OB zone
    assert ev.ttl_candles == 4
    assert ev.strength == 0.8  # min(disp 2 / atr 2, 1.0) * 0.8
    assert ev.meta == {"event": "PROPULSION",
                       "sl": str(tick(98)),  # zone far edge (tap low), raw
                       "sl_floor": str(Decimal("0.15") * ctx_at(store, 19, levels).atr(M5))}


def test_short_mirror():
    store = make_store([FLAT] * 15 + [TAP_S, P1_S, P2_S, RETEST_S])
    levels = [ob(LevelKind.OB_BEAR, "101.5", 104)]
    [ev] = run_to(PropulsionBlockDetector({}), store, levels, 19)
    assert ev.direction is Direction.SHORT
    assert ev.zone == (tick(100), tick(102))
    assert ev.strength == 0.8
    assert ev.meta["sl"] == str(tick(102))  # zone far edge (tap high)
    assert ev.meta["sl_floor"] == str(Decimal("0.15") * ctx_at(store, 19, levels).atr(M5))


def test_body_close_inside_ob_is_violation_not_tap():
    store = make_store(long_bars((VIOL_L, P1_L, P2_L, RETEST_L)))
    levels = [ob(LevelKind.OB_BULL, 96, "98.5")]
    assert run_to(PropulsionBlockDetector({}), store, levels, 19) == []


def test_weak_displacement_no_block():
    store = make_store(long_bars((TAP_L, P1_L, W2, W3, RETEST_L)))
    levels = [ob(LevelKind.OB_BULL, 96, "98.5")]
    assert run_to(PropulsionBlockDetector({}), store, levels, 20) == []


def test_touch_before_confirm_is_nothing_first_touch_after_fires():
    store = make_store(long_bars((TAP_L, EARLY_L, MID_L, CONF_L, RETEST_L)))
    levels = [ob(LevelKind.OB_BULL, 96, "98.5")]
    [ev] = run_to(PropulsionBlockDetector({}), store, levels, 20)  # EARLY_L silent
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick(98), tick(100))


def test_no_lookahead_closed_candles_only():
    store, levels = make_store(long_bars()), [ob(LevelKind.OB_BULL, 96, "98.5")]
    det = PropulsionBlockDetector({})
    for n in (15, 16, 17, 18):  # tap/propel closed, retest not yet
        assert det.detect(ctx_at(store, n, levels)) == []
    [ev] = det.detect(ctx_at(store, 19, levels))
    assert ev.direction is Direction.LONG


def test_dedupe_one_fire_per_block():
    store = make_store(long_bars((TAP_L, P1_L, P2_L, RETEST_L, RETEST2_L)))
    levels = [ob(LevelKind.OB_BULL, 96, "98.5")]
    det = PropulsionBlockDetector({})
    [ev] = run_to(det, store, levels, 19)
    assert det.detect(ctx_at(store, 19, levels)) == []  # same tick again
    assert det.detect(ctx_at(store, 20, levels)) == []  # later zone re-touch


def test_dead_parent_level_never_taps():
    store, levels = make_store(long_bars()), \
        [ob(LevelKind.OB_BULL, 96, "98.5", LevelState.MITIGATED)]
    assert run_to(PropulsionBlockDetector({}), store, levels, 19) == []


def test_session_end_keeps_blocks_prunes_pending():
    store, levels = make_store(long_bars()), [ob(LevelKind.OB_BULL, 96, "98.5")]
    det = PropulsionBlockDetector({})
    for n in (16, 17, 18):  # tap, P1, P2 -> block confirmed, untouched
        assert det.detect(ctx_at(store, n, levels)) == []
    assert det._blocks
    det._pending = {(bar_ts(i), 1): None for i in range(5)}  # stale taps
    det.on_session_end()
    assert det._blocks                       # carried while parent OB lives
    assert len(det._pending) == 3            # pruned to propel_bars newest
    det._pending.clear()
    [ev] = det.detect(ctx_at(store, 19, levels))  # next-session touch fires
    assert ev.direction is Direction.LONG


def test_meta_schema_contract():
    store, levels = make_store(long_bars()), [ob(LevelKind.OB_BULL, 96, "98.5")]
    [ev] = run_to(PropulsionBlockDetector({}), store, levels, 19)
    assert set(ev.meta) == {"event", "sl", "sl_floor"}
    assert ev.meta["event"] == "PROPULSION"
    for k in ("sl", "sl_floor"):
        assert isinstance(ev.meta[k], str)
        Decimal(ev.meta[k])  # stringified Decimal round-trips
    assert 0.0 <= ev.strength <= 1.0
