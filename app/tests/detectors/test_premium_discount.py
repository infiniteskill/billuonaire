"""Tests for the premium_discount gate (trader/detectors/premium_discount.py)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from trader.detectors.premium_discount import PremiumDiscountDetector
from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
DAY = datetime(2026, 7, 15, 9, 15, tzinfo=IST)
PARAMS = {"tf": "5m", "min_range_atr": 8.0, "eq_deadband": 0.10}


def _ext(kind, price, master=True, state=LevelState.ACTIVE):
    p = tick(str(price))
    return Level(id=f"X-{kind.name}-{price}", symbol="X", kind=kind,
                 zone=(p, p), born=DAY, tf=Timeframe.M5,
                 state=state, meta={"master": master, "rank_atr": 3.0})


def _ctx(price, levels, n=90):
    """90 M1 candles oscillating around `price` (small ATR), last close=price."""
    st = CandleStore("/nonexistent")
    for i in range(n):
        o = float(price) + ((i % 4) - 1.5) * 0.3
        h = max(o, float(price)) + 0.4
        l = min(o, float(price)) - 0.4
        st.add(Candle("X", Timeframe.M1, DAY + timedelta(minutes=i),
                      tick(str(o)), tick(str(h)), tick(str(l)), tick(str(price)), 100))
    now = DAY + timedelta(minutes=n - 1)
    return StockContext(symbol="X", now=now, candles=st.view("X", now),
                        levels=levels, evidence_history=[],
                        day=DayState(session_date=now.date()))


def _run(price, lo=90, hi=110, **over):
    ctx = _ctx(price, [_ext(LevelKind.EXT_L, lo), _ext(LevelKind.EXT_H, hi)])
    return PremiumDiscountDetector({**PARAMS, **over}).detect(ctx)


def test_discount_permits_long():
    ev = _run(94)  # pos = (94-90)/20 = 0.2
    assert len(ev) == 1
    assert ev[0].direction is Direction.NEUTRAL         # a gate, not a signal
    assert ev[0].meta["side"] == "discount"
    assert ev[0].meta["permits"] == "LONG"
    assert ev[0].meta["range_pos"] == 0.2


def test_premium_permits_short():
    ev = _run(106)  # pos = 0.8
    assert ev[0].meta["side"] == "premium"
    assert ev[0].meta["permits"] == "SHORT"


def test_mid_permits_nothing():
    ev = _run(100)  # pos = 0.5, inside eq_deadband
    assert ev[0].meta["side"] == "mid"
    assert ev[0].meta["permits"] is None
    assert ev[0].strength == 0.0


def test_ote_band_flagged():
    assert _run(95)[0].meta["ote"] is True    # pos 0.25 in [0.21,0.38]
    assert _run(94)[0].meta["ote"] is False   # pos 0.20 below band


def test_strength_scales_with_extremeness():
    assert _run(90.5)[0].strength > _run(96)[0].strength  # deeper discount = stronger


def test_tiny_range_emits_nothing():
    # range 2 pts vs ATR~0.5 * min_range_atr 8 = 4 -> below floor -> no gate
    assert _run(100, lo=99, hi=101) == []


def test_no_master_pair_emits_nothing():
    ctx = _ctx(100, [_ext(LevelKind.EXT_L, 90), _ext(LevelKind.EXT_H, 110, master=False)])
    assert PremiumDiscountDetector(PARAMS).detect(ctx) == []


def test_swept_extreme_excluded():
    ctx = _ctx(94, [_ext(LevelKind.EXT_L, 90, state=LevelState.SWEPT),
                    _ext(LevelKind.EXT_H, 110)])
    assert PremiumDiscountDetector(PARAMS).detect(ctx) == []  # no live low -> no range


def test_edge_trigger_emits_only_on_ote_entry():
    det = PremiumDiscountDetector({**PARAMS, "edge_trigger": True})
    c = _ctx(95, [_ext(LevelKind.EXT_L, 90), _ext(LevelKind.EXT_H, 110)])  # pos 0.25 = OTE
    assert len(det.detect(c)) == 1        # 0->1 entry into OTE band -> emit
    assert len(det.detect(c)) == 0        # dwell in band -> suppressed
