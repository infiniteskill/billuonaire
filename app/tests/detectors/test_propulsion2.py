"""Tests for the propulsion2 detector (trader/detectors/propulsion2.py).
Binding design: lesson 14 + ZONES P3 (the +43.4pp law) + TUNE (orphans
anti-signal, parent linkage mandatory). A candle trading INTO a live
ob_taught OB zone (its first armed retest) and closing away in the parent
direction with a directional body births the child: zone = that candle's
BODY range, carrying the parent zone id. The child emits ONLY while the
parent is alive -- parent killed => child killed instantly, BEFORE the
killing bar can touch the child, so orphan emission is impossible by
construction. Evidence on the child's first armed retest: parent
direction, ttl 4, meta {"event","sl","sl_floor","parent"}.

Fixture geometry: one M1 per M5 bucket start; FLAT primes ATR(M5,14).
Shared with test_ob_taught: B15/B16/B17 birth the parent OB (103, 104.5)."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from trader.detectors.base import REGISTRY
from trader.detectors.propulsion2 import Propulsion2Detector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5

FLAT = (100, 101, 99, 100)
B15 = (100, 105, "99.5", "104.5")
B16 = ("104.5", 106, 102, 103)         # pause: parent bodies box (103, 104.5)
B17 = (103, 107, "102.8", 106)         # break -> parent OB born
PARM = (106, 107, 105, "106.5")        # parent armed (low 105 > 104.5)
TAP = (105, "106.5", 104, 106)         # parent 1st retest: low 104 in zone,
                                       # closes 106 > 104.5 with bull body
                                       # -> child = body (105, 106)
KARM = ("106.5", "107.5", "106.05", 107)  # low 106.05 > 106 -> child armed
KTOUCH = (107, "107.5", "105.5", "106.5")  # low 105.5 <= 106 -> child retest
PKILL = (106, 106, "100.9", 101)       # close 2.0 below parent lo >= 0.5xATR
KILL18 = (106, 106, "101.5", "101.5")  # parent killed before any tap


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def bar(i, o, h, l, c, v=10):
    return Candle("X", Timeframe.M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_store(bars):
    store = CandleStore("/nonexistent")
    for i, b in enumerate(bars):
        store.add(bar(i, *b))
    return store


def ctx_at(store, n_bars):
    now = bar_ts(n_bars)
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=[], evidence_history=[],
                        day=DayState(session_date=now.date()))


def run_to(det, store, n_last):
    for n in range(15, n_last):
        assert det.detect(ctx_at(store, n)) == []
    return det.detect(ctx_at(store, n_last))


def test_registered():
    assert REGISTRY["propulsion2"] is Propulsion2Detector
    d = Propulsion2Detector({})
    assert d.params == {"tf": "5m", "depth_atr": 0.5, "sl_atr_floor": 0.15}


def test_child_body_zone_fires_with_parent_id():
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, TAP, KARM, KTOUCH])
    [ev] = run_to(Propulsion2Detector({}), store, 22)
    assert ev.detector == "propulsion2"
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick(105), tick(106))   # TAP body, NOT its range (104, 106.5)
    assert ev.ttl_candles == 4
    assert ev.strength == 0.8
    assert ev.meta["event"] == "PROPULSION2"
    assert ev.meta["sl"] == str(tick(105))
    assert ev.meta["parent"] == f"OB+1@{bar_ts(17).isoformat()}"


def test_parent_death_cascades_to_child():
    # child born at TAP; PKILL closes deep through the parent -> parent dead,
    # child dead INSTANTLY -- later would-be arm+touch bars stay silent.
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, TAP, PKILL,
                                      (101, "107.6", "100.9", "107.5"),
                                      ("107.5", 108, "106.1", 107),
                                      (107, "107.2", "105.8", 106)])
    assert run_to(Propulsion2Detector({}), store, 24) == []


def test_parent_killed_before_tap_births_no_child():
    # orphan forbidden by construction: a dead parent's box is not tradeable
    # context, so a tap-shaped candle after the kill creates nothing.
    store = make_store([FLAT] * 15 + [B15, B16, B17, KILL18, TAP, KARM, KTOUCH])
    assert run_to(Propulsion2Detector({}), store, 22) == []


def test_meta_schema_contract():
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, TAP, KARM, KTOUCH])
    [ev] = run_to(Propulsion2Detector({}), store, 22)
    assert set(ev.meta) == {"event", "sl", "sl_floor", "parent"}
    for k in ("sl", "sl_floor"):
        assert isinstance(ev.meta[k], str)
        Decimal(ev.meta[k])
    assert ev.meta["sl_floor"] == str(Decimal("0.15") * ctx_at(store, 22).atr(M5))
    assert 0.0 <= ev.strength <= 1.0
