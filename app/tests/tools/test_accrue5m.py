"""tools/accrue5m.py (repo root): merge semantics + splice guard, yfinance
stubbed (no network)."""

import importlib.util
import sys
import types
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[3] / "tools"


def _load(monkeypatch, hist, calls):
    class FakeTicker:
        def __init__(self, tk): calls.append(tk)
        def history(self, **kw):
            calls.append(kw)
            return hist

    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Ticker=FakeTicker))
    spec = importlib.util.spec_from_file_location("accrue5m", TOOLS / "accrue5m.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hist(days, price):
    """8x75 native-5m yfinance rows (>=500 so the thin guard passes)."""
    idx = pd.DatetimeIndex(
        [pd.Timestamp(2026, 7, d, 9, 15, tz="Asia/Kolkata") + pd.Timedelta(minutes=5 * i)
         for d in days for i in range(75)], name="Datetime")
    n = len(idx)
    return pd.DataFrame({"Open": [price] * n, "High": [price + 1] * n,
                         "Low": [price - 1] * n, "Close": [price] * n,
                         "Volume": [10] * n}, index=idx)


def test_accrue_merges_new_wins_and_warns_on_splice(tmp_path, monkeypatch, capsys):
    calls = []
    mod = _load(monkeypatch, _hist(days=range(6, 14), price=130.0), calls)
    old = ["2026-07-01T09:15:00+05:30,100.00,101.00,99.00,100.00,10",  # keeps tail
           "2026-07-06T09:15:00+05:30,999.00,999.00,999.00,999.00,1"]  # new wins
    (tmp_path / "RELIANCE.csv").write_text(
        "ts,open,high,low,close,volume\n" + "\n".join(old) + "\n")

    assert mod.main(out=tmp_path, pause=0) == 0     # no failures
    text = (tmp_path / "RELIANCE.csv").read_text()
    assert old[0] in text and old[1] not in text    # merge: old tail survives, overlap replaced
    assert "2026-07-13T15:25:00+05:30,130.00,131.00,129.00,130.00,10" in text
    assert all(kw["auto_adjust"] is False for kw in calls if isinstance(kw, dict))
    out = capsys.readouterr().out
    assert "SPLICE WARNING RELIANCE @ 2026-07-06T09:15:00+05:30" in out  # 100 -> 130


def test_accrue_thin_fetch_fails_symbol_not_batch(tmp_path, monkeypatch, capsys):
    mod = _load(monkeypatch, _hist(days=[6], price=130.0), [])   # 75 rows < 500
    keep = "ts,open,high,low,close,volume\n2026-07-01T09:15:00+05:30,100.00,101.00,99.00,100.00,10\n"
    (tmp_path / "RELIANCE.csv").write_text(keep)
    assert mod.main(out=tmp_path, pause=0) == 1                  # 1 failure, no crash
    assert (tmp_path / "RELIANCE.csv").read_text() == keep       # file untouched
    assert "FAIL RELIANCE: thin" in capsys.readouterr().out
