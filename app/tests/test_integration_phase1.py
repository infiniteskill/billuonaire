"""Phase-1 exit integration test: pump a full scenario day through the real
feed -> store pipeline and check the aggregation/visibility contract holds
end-to-end (not just in the unit tests for each piece)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from trader.feed.mock import ScenarioFeed, judas_reversal
from trader.models.candle import Timeframe
from trader.store.candles import CandleStore

IST = ZoneInfo("Asia/Kolkata")


def test_judas_day_flows_through_candle_store(tmp_path):
    scenario = judas_reversal("X", date(2026, 7, 15), 100.0)
    feed = ScenarioFeed([scenario])

    store = CandleStore(tmp_path)
    for event in feed.events():
        store.add(event.candle)

    view = store.view("X", datetime(2026, 7, 15, 15, 30, tzinfo=IST))

    m1 = view.last(375, Timeframe.M1)
    assert len(m1) == 375

    m5 = view.last(100, Timeframe.M5)
    assert len(m5) == 75

    d1 = view.last(1, Timeframe.D1)
    assert len(d1) == 1
    assert d1[0].low == min(c.low for c in m1)
