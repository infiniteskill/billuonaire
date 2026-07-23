"""Tests for the ob_taught detector (trader/detectors/ob_taught.py).
Binding design: lessons 3/12 + runs/taught/TUNE.md frozen config. OB =
opposite-direction candle OR consolidation cluster pausing a leg; BOX =
BODIES-ONLY hi-lo of the cluster (frozen: bodies, join 0), born at the
continuation break. Pivot-distance grade in meta (ATR distance to nearest
extremes pivot in ctx.levels, else large). BREAK-DEPTH LAW lifecycle
(>= 0.5xATR close-through kills, shallower = second life); on kill the box
flips: BRK when the birth leg swept the prior same-side extreme, else MIT
(lesson 12 one-question test); the flipped zone emits on retest from the
other side. Evidence on first armed retest, continuation direction, edge
entry, meta {"event","sl","sl_floor","pivot_dist_atr"}.

Fixture geometry: one M1 per M5 bucket start; FLAT primes ATR(M5,14)."""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from trader.detectors.base import REGISTRY
from trader.detectors.ob_taught import ObTaughtDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
SESSION_START = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
M5 = Timeframe.M5

FLAT = (100, 101, 99, 100)

# --- bull OB: bear pause candle inside an up-leg, bodies box (103, 104.5) ---
B15 = (100, 105, "99.5", "104.5")     # push (bull body 100-104.5)
B16 = ("104.5", 106, 102, 103)        # PAUSE: bear body 103-104.5, wicks 102/106
B17 = (103, 107, "102.8", 106)        # continuation close 106 > 104.5 -> OB born
PARM = (106, 107, 105, "106.5")       # low 105 > 104.5 -> armed
PTOUCH = ("106.5", 107, 104, 105)     # low 104 <= 104.5 -> first retest

KILL = (106, 106, "101.5", "101.5")   # close 1.5 below box lo >= 0.5xATR -> kill
FARM = ("101.5", "102.5", 100, 102)   # high 102.5 < 103 -> flip armed
FTOUCH = (102, 104, 101, "103.5")     # high 104 >= 103 -> flip retest

SHAL = (106, 106, "102.3", "102.4")   # close 0.6 below lo < 0.5xATR -> alive
SREC = ("102.4", 106, "102.4", "105.8")
SARM = ("105.8", 107, "104.6", 106)   # low 104.6 > 104.5 -> armed
STOUCH = (106, 106, "104.2", 105)     # low 104.2 <= 104.5 -> second-life retest


def bar_ts(i):
    return SESSION_START + timedelta(minutes=i * M5.minutes)


def bar(i, o, h, l, c, v=10):
    return Candle("X", Timeframe.M1, bar_ts(i), tick(o), tick(h), tick(l), tick(c), v)


def make_store(bars):
    store = CandleStore("/nonexistent")
    for i, b in enumerate(bars):
        store.add(bar(i, *b))
    return store


def swing(kind, price):
    return Level(id=f"X-{kind.name}-{price}", symbol="X", kind=kind,
                 zone=(tick(price), tick(price)), born=bar_ts(0), tf=Timeframe.M15)


def ctx_at(store, n_bars, levels):
    now = bar_ts(n_bars)
    return StockContext(symbol="X", now=now, candles=store.view("X", now),
                        levels=levels, evidence_history=[],
                        day=DayState(session_date=now.date()))


def run_to(det, store, levels, n_last):
    for n in range(15, n_last):
        assert det.detect(ctx_at(store, n, levels)) == []
    return det.detect(ctx_at(store, n_last, levels))


def test_registered():
    assert REGISTRY["ob_taught"] is ObTaughtDetector
    d = ObTaughtDetector({})
    assert d.params == {"tf": "5m", "depth_atr": 0.5, "sl_atr_floor": 0.15,
                        "far_dist_atr": 99.0, "require_sweep_bos": False,
                        "gate_window": 20, "gate_mode": "sweep_and_bos", "min_disp_atr": 0.0}


def test_bodies_only_box_and_retest_fires():
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, PTOUCH])
    levels = [swing(LevelKind.SWING_L, 101)]
    [ev] = run_to(ObTaughtDetector({}), store, levels, 20)
    assert ev.detector == "ob_taught"
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick(103), tick("104.5"))  # bodies, NOT wicks (102, 107)
    assert ev.ttl_candles == 6
    assert ev.strength == 0.7
    assert ev.meta["event"] == "OB_RETEST"
    assert ev.meta["sl"] == str(tick(103))
    # |box lo 103 - pivot 101| / ATR at birth (35.7 / 14)
    assert ev.meta["pivot_dist_atr"] == pytest.approx(float(Decimal(2) / (Decimal("35.7") / 14)))


def test_pivot_distance_defaults_large_without_swings():
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, PTOUCH])
    [ev] = run_to(ObTaughtDetector({}), store, [], 20)
    assert ev.meta["pivot_dist_atr"] == 99.0


@pytest.mark.parametrize("levels,event", [
    ([swing(LevelKind.SWING_H, "106.5")], "BRK_RETEST"),  # leg high 107 swept it
    ([swing(LevelKind.SWING_H, 110)], "MIT_RETEST"),      # never swept
    ([], "MIT_RETEST"),                                   # no extreme known
])
def test_flip_family_sweep_split(levels, event):
    store = make_store([FLAT] * 15 + [B15, B16, B17, KILL, FARM, FTOUCH])
    evs = run_to(ObTaughtDetector({}), store, levels, 21)
    [ev] = [e for e in evs if e.meta["event"] == event]
    assert ev.direction is Direction.SHORT      # flipped: works the other way
    assert ev.zone == (tick(103), tick("104.5"))  # same box
    assert ev.meta["sl"] == str(tick("104.5"))


def test_second_life_shallow_close_through_keeps_zone():
    store = make_store([FLAT] * 15 + [B15, B16, B17, SHAL, SREC, SARM, STOUCH])
    [ev] = run_to(ObTaughtDetector({}), store, [], 22)
    assert ev.direction is Direction.LONG
    assert ev.zone == (tick(103), tick("104.5"))
    assert ev.meta["event"] == "OB_RETEST"


def test_meta_schema_contract():
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, PTOUCH])
    [ev] = run_to(ObTaughtDetector({}), store, [], 20)
    assert set(ev.meta) == {"event", "sl", "sl_floor", "pivot_dist_atr"}
    for k in ("sl", "sl_floor"):
        assert isinstance(ev.meta[k], str)
        Decimal(ev.meta[k])
    assert ev.meta["sl_floor"] == str(Decimal("0.15") * ctx_at(store, 20, []).atr(M5))
    assert 0.0 <= ev.strength <= 1.0


# ---- node-4 birth gate: require an upstream sweep + same-dir BOS ----

def test_birth_gate_default_off_unchanged():
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, PTOUCH])
    [ev] = run_to(ObTaughtDetector({}), store, [swing(LevelKind.SWING_L, 101)], 20)
    assert ev.meta["event"] == "OB_RETEST"          # default behavior intact


def test_birth_gate_suppresses_without_sweep_bos():
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, PTOUCH])
    det = ObTaughtDetector({"require_sweep_bos": True})
    assert run_to(det, store, [swing(LevelKind.SWING_L, 101)], 20) == []


def test_birth_gate_passes_with_sweep_and_bos():
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, PTOUCH])
    swept = Level(id="X-EXT_L-99", symbol="X", kind=LevelKind.EXT_L,
                  zone=(tick(99), tick(99)), born=bar_ts(0), tf=M5)
    swept.record_state(bar_ts(16), LevelState.SWEPT)
    bos = Evidence(detector="structure", direction=Direction.LONG, strength=0.6,
                   zone=(tick(103), tick(103)), ts=bar_ts(17), ttl_candles=12,
                   meta={"event": "BOS"})
    det = ObTaughtDetector({"require_sweep_bos": True})
    ev = []
    for n in range(15, 21):
        now = bar_ts(n)
        ev = det.detect(StockContext(symbol="X", now=now, candles=store.view("X", now),
                                     levels=[swept], evidence_history=[bos],
                                     day=DayState(session_date=now.date())))
    assert ev and ev[0].meta["event"] == "OB_RETEST"


def test_gate_mode_sweep_arms_on_sweep_alone():
    # range-fade: a swept level with NO structure BOS still arms the retest
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, PTOUCH])
    swept = Level(id="X-EXT_L-99", symbol="X", kind=LevelKind.EXT_L,
                  zone=(tick(99), tick(99)), born=bar_ts(0), tf=M5)
    swept.record_state(bar_ts(16), LevelState.SWEPT)
    det = ObTaughtDetector({"require_sweep_bos": True, "gate_mode": "sweep"})
    ev = []
    for n in range(15, 21):
        now = bar_ts(n)
        ev = det.detect(StockContext(symbol="X", now=now, candles=store.view("X", now),
                                     levels=[swept], evidence_history=[],  # NO bos
                                     day=DayState(session_date=now.date())))
    assert ev and ev[0].meta["event"] == "OB_RETEST"


def test_gate_mode_sweep_still_needs_a_sweep():
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, PTOUCH])
    det = ObTaughtDetector({"require_sweep_bos": True, "gate_mode": "sweep"})
    assert run_to(det, store, [], 20) == []          # no swept level -> no arm


def test_min_disp_gate_suppresses_small_break():
    # displacement gate: B17 clears the box by ~1.5 < 1.0*ATR(~2.55) -> mint nothing
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, PTOUCH])
    assert run_to(ObTaughtDetector({"min_disp_atr": 1.0}), store, [], 20) == []


def test_min_disp_default_off_unchanged():
    store = make_store([FLAT] * 15 + [B15, B16, B17, PARM, PTOUCH])
    [ev] = run_to(ObTaughtDetector({}), store, [], 20)     # default 0 -> fires
    assert ev.meta["event"] == "OB_RETEST"
