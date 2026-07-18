import sys
import types
from datetime import date
from decimal import Decimal as D
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from trader.tools.fetch import chunks, fetch_symbol, gap_report, merge, to_filefeed

IST = ZoneInfo("Asia/Kolkata")


def _mk(rows):
    """rows: list of (Timestamp, o, h, l, c, v) -> yfinance-shaped OHLCV frame
    (tz-aware 'Datetime' index, columns Open/High/Low/Close/Volume)."""
    idx = pd.DatetimeIndex([r[0] for r in rows], name="Datetime")
    cols = ["Open", "High", "Low", "Close", "Volume"]
    return pd.DataFrame({c: [r[i] for r in rows] for i, c in enumerate(cols, start=1)}, index=idx)


def _raw(rows, day=15):
    """rows: list of (hh, mm, o, h, l, c, v) on 2026-07-<day>."""
    return _mk([(pd.Timestamp(2026, 7, day, hh, mm, tz=IST), o, h, l, c, v)
               for hh, mm, o, h, l, c, v in rows])


def _full_session_raw(day=15, n=300):
    start = pd.Timestamp(2026, 7, day, 9, 15, tz=IST)
    return _mk([(start + pd.Timedelta(minutes=i), 100, 101, 99, 100, 100) for i in range(n)])


# --------------------------------------------------------------- to_filefeed

def test_to_filefeed_filters_session_bounds():
    raw = _raw([(9, 10, 100, 101, 99, 100, 500),     # pre-open: dropped
               (9, 15, 100, 101, 99, 100.5, 1000),    # open boundary: kept
               (15, 29, 101, 102, 100, 101.5, 900),   # kept
               (15, 30, 101, 101, 101, 101, 200)])    # close boundary: dropped
    out = to_filefeed(raw)
    assert list(out["ts"]) == ["2026-07-15T09:15:00+05:30", "2026-07-15T15:29:00+05:30"]


def test_to_filefeed_quantizes_prices_and_ints_volume():
    raw = _raw([(9, 15, 100.02, 100.04, 99.98, 100.01, 999.6)])
    out = to_filefeed(raw)
    assert D(out.iloc[0]["open"]) == D("100.0") and D(out.iloc[0]["close"]) == D("100.0")
    assert out["volume"].iloc[0] == 999 and out["volume"].dtype.kind in "iu"


def test_to_filefeed_dedupes_keep_last_and_sorts():
    idx = pd.DatetimeIndex([pd.Timestamp(2026, 7, 15, 9, 16, tz=IST),
                            pd.Timestamp(2026, 7, 15, 9, 15, tz=IST),
                            pd.Timestamp(2026, 7, 15, 9, 15, tz=IST)], name="Datetime")
    raw = pd.DataFrame({"Open": [100, 100, 100], "High": [101, 101, 105],
                        "Low": [99, 99, 99], "Close": [100, 100, 104],
                        "Volume": [10, 10, 20]}, index=idx)
    out = to_filefeed(raw)
    assert list(out["ts"]) == ["2026-07-15T09:15:00+05:30", "2026-07-15T09:16:00+05:30"]
    assert D(out.iloc[0]["close"]) == D("104") and out.iloc[0]["volume"] == 20  # last wins


def test_to_filefeed_empty_input():
    out = to_filefeed(pd.DataFrame())
    assert list(out.columns) == ["ts", "open", "high", "low", "close", "volume"] and out.empty


def test_to_filefeed_drops_nan_rows():
    """yfinance emits NaN OHLCV rows for missing minutes; unfiltered, a NaN
    price quantizes to Decimal('NaN') and lands in the CSV as a poison
    'NaN' string, and a NaN volume crashes the int cast."""
    raw = _raw([(9, 15, 100, 101, 99, 100.5, 1000),
                (9, 16, 100, 101, 99, float("nan"), 1100),   # NaN price
                (9, 17, 100, 101, 99, 100.5, float("nan"))])  # NaN volume
    out = to_filefeed(raw)
    assert list(out["ts"]) == ["2026-07-15T09:15:00+05:30"]


# -------------------------------------------------------------------- merge

def test_merge_unions_by_ts_new_wins():
    existing = to_filefeed(_raw([(9, 15, 100, 101, 99, 100, 1000),
                                 (9, 16, 100, 102, 100, 101, 1100)]))
    new = to_filefeed(_raw([(9, 16, 999, 999, 999, 999, 5000),  # overlap: new wins
                            (9, 17, 101, 103, 101, 102, 1200)]))
    out = merge(existing, new)
    assert list(out["ts"]) == ["2026-07-15T09:15:00+05:30", "2026-07-15T09:16:00+05:30",
                               "2026-07-15T09:17:00+05:30"]
    assert out.iloc[1]["volume"] == 5000


def test_merge_empty_sides():
    new = to_filefeed(_raw([(9, 15, 100, 101, 99, 100, 1000)]))
    assert merge(pd.DataFrame(columns=new.columns), new).equals(new)
    assert merge(new, pd.DataFrame(columns=new.columns)).equals(new)


def test_read_csv_merge_preserves_existing_text_exactly(tmp_path):
    """read_csv must load ALL columns as str: numeric dtypes would rewrite
    existing rows on the next merge ('1328.90' -> '1328.9', volume '0' ->
    '0.0' when any NaN coerces the column to float)."""
    from trader.tools.fetch import read_csv, write_csv

    line = "2026-07-14T09:15:00+05:30,1328.90,1330.00,1325.05,1327.30,0"
    (tmp_path / "R.csv").write_text(f"ts,open,high,low,close,volume\n{line}\n")
    existing = read_csv(tmp_path / "R.csv")
    assert [v for v in existing.iloc[0]] == line.split(",")   # str, text-exact
    new = to_filefeed(_raw([(9, 15, 1327, 1328, 1326, 1327.5, 100)]))
    write_csv(tmp_path / "R.csv", merge(existing, new))
    assert line in (tmp_path / "R.csv").read_text()


# --------------------------------------------------------------- gap_report

def test_gap_report_flags_thin_sessions_only():
    full = to_filefeed(_full_session_raw(day=15, n=300))       # not thin
    thin = to_filefeed(_raw([(9, 15, 100, 101, 99, 100, 100),
                             (9, 16, 100, 101, 99, 100, 100)], day=16))  # thin
    df = pd.concat([full, thin], ignore_index=True)
    assert gap_report(df) == [("2026-07-16", 2)]


def test_gap_report_empty_frame():
    assert gap_report(pd.DataFrame(columns=["ts"])) == []


# ------------------------------------------------------------------- chunks

def test_chunks_splits_into_at_most_7_day_windows():
    windows = chunks(25, today=date(2026, 7, 17))
    assert windows[0][0] == date(2026, 6, 22) and windows[-1][1] == date(2026, 7, 17)
    assert all((e - s).days <= 7 for s, e in windows)
    assert windows[0][1] == windows[1][0]  # contiguous, no gaps/overlap


def test_chunks_zero_days():
    assert chunks(0, today=date(2026, 7, 17)) == []


# --------------------------------------------------------------- fetch_symbol

def test_fetch_symbol_missing_yfinance_gives_friendly_error(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "yfinance", None)
    with pytest.raises(RuntimeError, match="yfinance"):
        fetch_symbol("RELIANCE", 5, tmp_path)


def _stub_yf(monkeypatch, hist):
    calls = []

    class FakeTicker:
        def __init__(self, symbol): self.symbol = symbol
        def history(self, interval, start, end, **kw):
            calls.append({"interval": interval, "start": start, "end": end, **kw})
            return hist

    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Ticker=FakeTicker))
    return calls


def test_fetch_symbol_writes_and_merges_csv(tmp_path, monkeypatch):
    """Stub yfinance entirely (no network): exercises the chunk/merge/write
    wiring end to end."""
    hist = _raw([(9, 15, 100, 101, 99, 100.5, 1000), (9, 16, 100.5, 102, 100, 101, 1100)])
    _stub_yf(monkeypatch, hist)

    summary = fetch_symbol("RELIANCE", 5, tmp_path)
    assert summary == {"symbol": "RELIANCE", "days": 5, "rows": 2,
                       "gaps": [("2026-07-15", 2)], "splices": []}
    written = (tmp_path / "RELIANCE.csv").read_text().splitlines()
    assert written[0] == "ts,open,high,low,close,volume" and len(written) == 3

    fetch_symbol("RELIANCE", 5, tmp_path)  # overlapping re-fetch merges, no duplicates
    assert len((tmp_path / "RELIANCE.csv").read_text().splitlines()) == 3


def test_fetch_symbol_requests_raw_prices(tmp_path, monkeypatch):
    """auto_adjust must be explicitly False: yfinance's default (True)
    rewrites history after every corporate action, so merged windows fetched
    at different times splice differently-adjusted bases together."""
    calls = _stub_yf(monkeypatch, _raw([(9, 15, 100, 101, 99, 100.5, 1000)]))
    fetch_symbol("RELIANCE", 5, tmp_path)
    assert calls and all(c["auto_adjust"] is False for c in calls)


def test_fetch_symbol_no_merge_overwrites(tmp_path, monkeypatch):
    _stub_yf(monkeypatch, _raw([(9, 15, 100, 101, 99, 100.5, 1000)], day=16))
    old = "2026-07-15T09:15:00+05:30,999.00,999.00,999.00,999.00,1"
    (tmp_path / "RELIANCE.csv").write_text(f"ts,open,high,low,close,volume\n{old}\n")
    summary = fetch_symbol("RELIANCE", 5, tmp_path, merge_existing=False)
    text = (tmp_path / "RELIANCE.csv").read_text()
    assert summary["rows"] == 1 and old not in text and "2026-07-16" in text


def test_fetch_symbol_reports_splice_after_merge(tmp_path, monkeypatch):
    """A >15% close->open jump across the merge boundary (probable split or
    mixed adjustment basis) must land in summary['splices'] -- the loud
    guard; history is never silently adjusted."""
    _stub_yf(monkeypatch, _raw([(9, 15, 200, 201, 199, 200.5, 1000)], day=16))
    old = "2026-07-15T15:29:00+05:30,100.00,101.00,99.00,100.00,10"
    (tmp_path / "RELIANCE.csv").write_text(f"ts,open,high,low,close,volume\n{old}\n")
    summary = fetch_symbol("RELIANCE", 5, tmp_path)
    assert summary["splices"] == [("2026-07-16T09:15:00+05:30", 100.0)]
