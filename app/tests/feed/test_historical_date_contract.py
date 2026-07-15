"""historical() contract: takes datetime.date and behaves the same across
feed implementations (Fix 1 for the final-review "signature drift" finding).

Both ScenarioFeed and FileFeed must accept plain ``date`` objects for
``start``/``end`` and return the same candles a caller would expect
regardless of which concrete feed is wired up.
"""

from datetime import date, datetime

from trader.feed.file import FileFeed
from trader.feed.mock import ScenarioFeed, judas_reversal
from trader.models.candle import Timeframe

D = date(2026, 7, 15)

CSV = """ts,open,high,low,close,volume
2026-07-15T09:15:00+05:30,100,101,99,100.5,1000
2026-07-15T09:16:00+05:30,100.5,102,100,101.5,1200
"""


def test_scenario_feed_historical_accepts_date_objects():
    sc = judas_reversal("X", D, 100.0)
    feed = ScenarioFeed([sc])
    feed.subscribe(["X"])

    got = feed.historical("X", Timeframe.M1, D, D)  # plain date, not datetime

    assert len(got) == 375
    assert all(c.symbol == "X" and c.tf == Timeframe.M1 for c in got)
    assert got == sorted(got, key=lambda c: c.ts)
    assert got[0].ts.date() == D and got[-1].ts.date() == D


def test_file_feed_historical_accepts_date_objects(tmp_path):
    (tmp_path / "X.csv").write_text(CSV)
    feed = FileFeed(tmp_path)

    got = feed.historical("X", Timeframe.M1, D, D)  # plain date, not datetime

    assert len(got) == 2
    assert all(c.symbol == "X" for c in got)
    assert got[0].ts < got[1].ts


def test_datetime_arguments_normalized_via_date_scenario_feed():
    """Passing a datetime (instead of a date) must not silently misbehave:
    it is normalized to its calendar date."""
    sc = judas_reversal("X", D, 100.0)
    feed = ScenarioFeed([sc])
    feed.subscribe(["X"])
    dt = datetime(D.year, D.month, D.day, 12, 0)

    got = feed.historical("X", Timeframe.M1, dt, dt)

    assert len(got) == 375  # whole calendar day, not a TypeError or empty result


def test_datetime_arguments_normalized_via_date_file_feed(tmp_path):
    (tmp_path / "X.csv").write_text(CSV)
    feed = FileFeed(tmp_path)
    dt = datetime(D.year, D.month, D.day, 12, 0)

    got = feed.historical("X", Timeframe.M1, dt, dt)

    assert len(got) == 2  # whole calendar day, not a TypeError or empty result
