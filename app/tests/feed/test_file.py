from datetime import date
from pathlib import Path
from trader.feed.file import FileFeed
from trader.models.candle import Timeframe

CSV = """ts,open,high,low,close,volume
2026-07-15T09:15:00+05:30,100,101,99,100.5,1000
2026-07-15T09:16:00+05:30,100.5,102,100,101.5,1200
"""

def test_reads_and_orders(tmp_path):
    (tmp_path / "X.csv").write_text(CSV)
    f = FileFeed(tmp_path); f.subscribe(["X"])
    evs = list(f.events())
    assert len(evs) == 2 and evs[0].candle.ts < evs[1].candle.ts

def test_historical_range(tmp_path):
    (tmp_path / "X.csv").write_text(CSV)
    f = FileFeed(tmp_path)
    got = f.historical("X", Timeframe.M1, date(2026, 7, 15), date(2026, 7, 15))
    assert len(got) == 2

def test_interleaves_symbols(tmp_path):
    (tmp_path / "A.csv").write_text(CSV)
    (tmp_path / "B.csv").write_text(CSV)
    f = FileFeed(tmp_path); f.subscribe(["A", "B"])
    evs = list(f.events())
    assert [e.candle.symbol for e in evs[:2]] == ["A", "B"]   # same ts → stable symbol order
