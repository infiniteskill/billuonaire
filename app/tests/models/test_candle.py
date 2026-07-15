from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
import pytest
from trader.models.candle import Candle, Timeframe, tick

IST = ZoneInfo("Asia/Kolkata")

def c(o, h, l, cl, v=1000):
    return Candle("RELIANCE", Timeframe.M5, datetime(2026, 7, 15, 9, 15, tzinfo=IST),
                  tick(o), tick(h), tick(l), tick(cl), v)

def test_tick_quantizes_to_nse_tick():
    assert tick("100.07") == Decimal("100.05")
    assert tick("100.08") == Decimal("100.10")

def test_properties():
    x = c("100", "110", "95", "105")
    assert x.body == Decimal("5.00") and x.range == Decimal("15.00")
    assert x.upper_wick == Decimal("5.00") and x.lower_wick == Decimal("5.00")
    assert x.is_bullish

def test_invalid_ohlc_rejected():
    with pytest.raises(ValueError):
        c("100", "99", "95", "98")     # high < open
    with pytest.raises(ValueError):
        c("100", "110", "101", "105")  # low > open

def test_naive_timestamp_rejected():
    with pytest.raises(ValueError):
        Candle("X", Timeframe.M5, datetime(2026, 7, 15, 9, 15),
               tick(1), tick(1), tick(1), tick(1), 0)

def test_timeframe_minutes():
    assert Timeframe.M5.minutes == 5 and Timeframe.D1.minutes == 375
