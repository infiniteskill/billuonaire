from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from trader.engine.context import DayState, StockContext
from trader.models.candle import Candle, Timeframe, tick
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")
D = datetime(2026, 7, 15, tzinfo=IST)


def m1(minute_offset, o, h, l, c, v=100):
    ts = D.replace(hour=9, minute=15) + timedelta(minutes=minute_offset)
    return Candle("X", Timeframe.M1, ts, tick(o), tick(h), tick(l), tick(c), v)


def ctx_with(candles, now):
    store = CandleStore("/nonexistent")
    for candle in candles:
        store.add(candle)
    view = store.view("X", now)
    return StockContext(
        symbol="X",
        now=now,
        candles=view,
        levels=[],
        evidence_history=[],
        day=DayState(session_date=now.date()),
    )


def test_atr_known_values():
    # Hand-computed true ranges (TR = max(h-l, |h-prev_c|, |l-prev_c|)):
    #   c2: max(110-103=7,  |110-104|=6, |103-104|=1) = 7   (plain range)
    #   c3: max(112-100=12, |112-108|=4, |100-108|=8) = 12  (plain range)
    #   c4: max(103-95=8,   |103-101|=2, |95-101|=6)  = 8   (plain range)
    # ATR(3) = (7 + 12 + 8) / 3 = 9
    candles = [
        m1(0, 100, 105, 99, 104),
        m1(1, 104, 110, 103, 108),
        m1(2, 108, 112, 100, 101),
        m1(3, 101, 103, 95, 96),
    ]
    ctx = ctx_with(candles, D.replace(hour=9, minute=30))
    assert ctx.atr(Timeframe.M1, period=3) == Decimal("9")


def test_atr_gap_uses_prev_close():
    # Gap up: c2 range h-l = 2, but |l - prev_close| dominates.
    #   c1 close = 100; c2: o=110 h=111 l=109 c=110
    #   TR = max(111-109=2, |111-100|=11, |109-100|=9) = 11
    # ATR(1) = 11
    candles = [
        m1(0, 100, 101, 99, 100),
        m1(1, 110, 111, 109, 110),
    ]
    ctx = ctx_with(candles, D.replace(hour=9, minute=30))
    assert ctx.atr(Timeframe.M1, period=1) == Decimal("11")


def test_atr_keeps_full_decimal_precision():
    # TRs: 7, 12, 8.2 -> ATR(3) = 27.2/3 = 9.0666... NOT tick-quantized.
    candles = [
        m1(0, 100, 105, 99, 104),
        m1(1, 104, 110, 103, 108),
        m1(2, 108, 112, 100, 101),
        m1(3, 101, 103, "94.8", 96),
    ]
    ctx = ctx_with(candles, D.replace(hour=9, minute=30))
    atr = ctx.atr(Timeframe.M1, period=3)
    assert atr == Decimal("27.2") / Decimal("3")
    assert atr != tick(atr)  # a measure, not a price: no 0.05 quantization


def test_atr_none_when_insufficient():
    # period=3 needs 4 closed candles; only 3 available.
    candles = [
        m1(0, 100, 105, 99, 104),
        m1(1, 104, 110, 103, 108),
        m1(2, 108, 112, 100, 101),
    ]
    ctx = ctx_with(candles, D.replace(hour=9, minute=30))
    assert ctx.atr(Timeframe.M1, period=3) is None


def test_atr_none_on_empty_view():
    ctx = ctx_with([], D.replace(hour=9, minute=30))
    assert ctx.atr(Timeframe.M1) is None
    assert ctx.atr(Timeframe.M5) is None


def test_atr_none_when_candles_not_yet_closed():
    # 4 M1 candles exist but as of 09:17 only 2 are closed -> None for period=3.
    candles = [
        m1(0, 100, 105, 99, 104),
        m1(1, 104, 110, 103, 108),
        m1(2, 108, 112, 100, 101),
        m1(3, 101, 103, 95, 96),
    ]
    ctx = ctx_with(candles, D.replace(hour=9, minute=17))
    assert ctx.atr(Timeframe.M1, period=3) is None


def test_atr_uses_last_period_trs_only():
    # 6 candles, period=3 -> only the 3 most recent TRs enter the SMA.
    candles = [
        m1(0, 100, 200, 50, 100),   # huge early range must NOT leak in
        m1(1, 100, 150, 90, 100),
        m1(2, 100, 105, 99, 104),   # window starts here (prev_close source)
        m1(3, 104, 110, 103, 108),  # TR 7
        m1(4, 108, 112, 100, 101),  # TR 12
        m1(5, 101, 103, 95, 96),    # TR 8
    ]
    ctx = ctx_with(candles, D.replace(hour=9, minute=30))
    assert ctx.atr(Timeframe.M1, period=3) == Decimal("9")


def test_day_state_defaults():
    day = DayState(session_date=D.date())
    assert day.template == "UNCLASSIFIED"


def test_context_options_defaults_none():
    ctx = ctx_with([], D.replace(hour=9, minute=30))
    assert ctx.options is None
