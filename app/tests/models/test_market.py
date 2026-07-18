import json
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.config import Settings, load_settings
from trader.models.candle import Candle, Timeframe, tick
from trader.models.market import NSE, MarketSpec, is_expiry
from trader.store.candles import CandleStore

CRYPTO = MarketSpec(tz="UTC", session_open="00:00", session_close="24:00",
                    tick_size=Decimal("0.01"))
TEMPLATE = Path(__file__).parents[2] / "trader" / "templates" / "config.json"


def test_nse_derived_fields():
    assert (NSE.session_minutes, NSE.open_t, NSE.close_t) == (375, time(9, 15), time(15, 30))
    assert NSE.tzinfo == ZoneInfo("Asia/Kolkata") and NSE.tick_size == Decimal("0.05")


def test_crypto_24h_derived_fields():
    assert (CRYPTO.session_minutes, CRYPTO.open_t, CRYPTO.close_t) == (1440, time(0), time(0))
    assert CRYPTO.tzinfo == ZoneInfo("UTC") and CRYPTO.tick_size == Decimal("0.01")


def test_quantize_parity_with_legacy_tick():
    for v in (100, "100.07", "100.08", 100.024, 99.975, 0.06, "123.456"):
        assert NSE.quantize(v) == tick(v)


@pytest.mark.parametrize("kw", [
    {"tick_size": "0"}, {"tick_size": "-0.05"},          # tick <= 0
    {"session_open": "9:15"}, {"session_close": "25:00"},  # malformed times
    {"session_open": "15:30", "session_close": "09:15"},   # close before open
    {"expiry_weekday": 7}, {"expiry_weekday": -1},          # weekday out of range
])
def test_invalid_spec_rejected(kw):
    with pytest.raises(ValueError):
        MarketSpec(**kw)


def test_is_expiry():
    assert NSE.expiry_weekday == 3                          # Thursday default
    assert is_expiry(date(2026, 7, 16), NSE)                # a Thursday
    assert not is_expiry(date(2026, 7, 15), NSE)            # Wednesday
    assert not is_expiry(date(2026, 7, 16), MarketSpec(expiry_weekday=None))


def test_expiry_weekday_config_roundtrip():
    data = json.loads(TEMPLATE.read_text())
    assert Settings.model_validate(data).market_spec().expiry_weekday == 3
    data["market"]["expiry_weekday"] = None                 # spot-only market
    assert Settings.model_validate(data).market_spec().expiry_weekday is None
    data["market"]["expiry_weekday"] = 9
    with pytest.raises(Exception):
        Settings.model_validate(data)


def test_settings_market_spec_roundtrip():
    assert load_settings(TEMPLATE).market_spec() == NSE  # shipped template = NSE
    data = json.loads(TEMPLATE.read_text())
    data["market"] = {"tz": "UTC", "session_open": "00:00",
                      "session_close": "24:00", "tick_size": 0.01}
    assert Settings.model_validate(data).market_spec() == CRYPTO
    del data["market"]                                   # absent section => NSE
    assert Settings.model_validate(data).market_spec() == NSE
    data["market"] = {"tick_size": -1}
    with pytest.raises(Exception):
        Settings.model_validate(data)


def test_candlestore_crypto_session_end_to_end(tmp_path):
    """Crypto spec: 03:00 UTC M1 candles (far outside any NSE session) are
    accepted and aggregate into an M5 bucket anchored at session open 00:00."""
    utc = CRYPTO.tzinfo
    store = CandleStore(tmp_path, spec=CRYPTO)
    tk = Decimal("0.01")
    for i in range(5):
        p = Decimal("100.01") + tk * i
        store.add(Candle("BTC", Timeframe.M1, datetime(2026, 7, 15, 3, i, tzinfo=utc),
                         p, p + 2 * tk, p - tk, p + tk, 10))
    view = store.view("BTC", datetime(2026, 7, 15, 3, 5, tzinfo=utc))
    [m5] = view.last(1, Timeframe.M5)
    assert m5.ts == datetime(2026, 7, 15, 3, 0, tzinfo=utc)  # 00:00-anchored bucket
    assert (m5.open, m5.high, m5.low, m5.close, m5.volume) == (
        Decimal("100.01"), Decimal("100.07"), Decimal("100.00"), Decimal("100.06"), 50)
    [d1] = store.view("BTC", datetime(2026, 7, 16, tzinfo=utc)).last(1, Timeframe.D1)
    assert d1.ts == datetime(2026, 7, 15, 0, 0, tzinfo=utc)  # D1 = whole 24h session
