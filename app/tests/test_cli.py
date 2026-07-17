import json
from datetime import date, datetime, timedelta
from decimal import Decimal as D
from zoneinfo import ZoneInfo

from typer.testing import CliRunner

from trader.cli import app
from trader.engine.scanner import fit
from trader.models.candle import Candle, Timeframe
from trader.models.market import NSE
from trader.store.candles import CandleStore
from trader.store.journal import Journal

runner = CliRunner()
IST = ZoneInfo("Asia/Kolkata")

def test_init_scaffolds(tmp_path):
    r = runner.invoke(app, ["init", "--dir", str(tmp_path)])
    assert r.exit_code == 0
    assert (tmp_path / "config.json").exists() and (tmp_path / "stocks.json").exists()

def test_init_refuses_overwrite(tmp_path):
    runner.invoke(app, ["init", "--dir", str(tmp_path)])
    r = runner.invoke(app, ["init", "--dir", str(tmp_path)])
    assert r.exit_code != 0

def test_list_numbers_stocks(tmp_path):
    runner.invoke(app, ["init", "--dir", str(tmp_path)])
    (tmp_path / "stocks.json").write_text(json.dumps({"stocks": ["RELIANCE", "TCS"]}))
    r = runner.invoke(app, ["list", "--dir", str(tmp_path)])
    assert r.exit_code == 0 and "1" in r.output and "RELIANCE" in r.output and "TCS" in r.output


def _init(tmp_path, stocks):
    runner.invoke(app, ["init", "--dir", str(tmp_path)])
    (tmp_path / "stocks.json").write_text(json.dumps({"stocks": stocks}))


def _d1(sym, i, o, h, l, c, v=100_000):
    ts = datetime(2026, 6, 1, 9, 15, tzinfo=IST) + timedelta(days=i)
    return Candle(sym, Timeframe.D1, ts, D(str(o)), D(str(h)), D(str(l)), D(str(c)), v)


def _m5(sym, i, o, h, l, c, v=1_000):
    ts = datetime(2026, 6, 1, 9, 15, tzinfo=IST) + timedelta(minutes=5 * i)
    return Candle(sym, Timeframe.M5, ts, D(str(o)), D(str(h)), D(str(l)), D(str(c)), v)


# -------------------------------------------------------------------- watch

def test_watch_mock_runs_end_to_end(tmp_path):
    _init(tmp_path, ["ACME"])
    r = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path), "--capital", "100000",
                            "--max-qty", "10", "--feed", "mock"])
    assert r.exit_code == 0
    assert "Session Summary" in r.output and "ACME" in r.output


def test_watch_file_feed(tmp_path):
    _init(tmp_path, ["ACME"])
    csv = ("ts,open,high,low,close,volume\n"
          "2026-07-15T09:15:00+05:30,100,101,99,100.5,1000\n"
          "2026-07-15T09:16:00+05:30,100.5,102,100,101.5,1200\n")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "ACME.csv").write_text(csv)
    r = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path),
                            "--feed", "file", "--data", str(data_dir)])
    assert r.exit_code == 0 and "ACME" in r.output


def _spy_index(monkeypatch, seen):
    import trader.cli as cli_mod
    orig = cli_mod.Orchestrator

    def spy(settings, feed, symbols, index_symbol=None, **kw):
        seen["index"] = index_symbol
        return orig(settings, feed, symbols, index_symbol=index_symbol, **kw)

    monkeypatch.setattr(cli_mod, "Orchestrator", spy)


def test_watch_index_flag_overrides_config(tmp_path, monkeypatch):
    _init(tmp_path, ["ACME"])
    cfg = json.loads((tmp_path / "config.json").read_text())
    cfg["index_symbol"] = "CFGIDX"
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    seen = {}
    _spy_index(monkeypatch, seen)
    r = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path), "--feed", "mock",
                            "--index", "NIFTY"])
    assert r.exit_code == 0 and seen["index"] == "NIFTY"      # flag wins
    r = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path), "--feed", "mock"])
    assert r.exit_code == 0 and seen["index"] == "CFGIDX"     # config fallback


def test_watch_file_feed_index_without_data_dropped(tmp_path, monkeypatch):
    _init(tmp_path, ["ACME"])
    csv = ("ts,open,high,low,close,volume\n"
           "2026-07-15T09:15:00+05:30,100,101,99,100.5,1000\n")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "ACME.csv").write_text(csv)
    seen = {}
    _spy_index(monkeypatch, seen)
    r = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path), "--feed", "file",
                            "--data", str(data_dir), "--index", "NIFTY"])
    assert r.exit_code == 0 and seen["index"] is None         # no NIFTY.csv


def test_watch_requires_symbols(tmp_path):
    _init(tmp_path, ["ACME"])
    r = runner.invoke(app, ["watch", "--dir", str(tmp_path)])
    assert r.exit_code != 0


def test_watch_out_of_range_number(tmp_path):
    _init(tmp_path, ["ACME"])
    r = runner.invoke(app, ["watch", "5", "--dir", str(tmp_path), "--feed", "mock"])
    assert r.exit_code == 1
    out = r.output + (r.stderr or "")
    assert "out of range" in out and "Traceback" not in out


def test_watch_file_feed_requires_data(tmp_path):
    _init(tmp_path, ["ACME"])
    r = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path), "--feed", "file"])
    assert r.exit_code == 1
    out = r.output + (r.stderr or "")
    assert "requires --data" in out and "Traceback" not in out


def test_watch_unknown_feed(tmp_path):
    _init(tmp_path, ["ACME"])
    r = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path), "--feed", "bogus"])
    assert r.exit_code != 0


def test_watch_loads_and_saves_candle_cache_across_runs(tmp_path):
    """watch loads dir/journal/candles before the run and saves after --
    a second invocation must see the first run's day merged with the new
    day's feed data (proving load-before-run, not just save-after-run)."""
    _init(tmp_path, ["ACME"])
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    def _csv(day, o):
        return ("ts,open,high,low,close,volume\n"
               f"{day}T09:15:00+05:30,{o},{o + 1},{o - 1},{o + 0.5},1000\n")

    (data_dir / "ACME.csv").write_text(_csv("2026-07-14", 100))
    r1 = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path),
                             "--feed", "file", "--data", str(data_dir)])
    assert r1.exit_code == 0
    cache = tmp_path / "journal" / "candles" / "ACME"
    assert (cache / "1d.parquet").exists()

    (data_dir / "ACME.csv").write_text(_csv("2026-07-15", 110))   # a second day
    r2 = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path),
                             "--feed", "file", "--data", str(data_dir)])
    assert r2.exit_code == 0

    reloaded = CandleStore(tmp_path / "journal" / "candles", NSE)
    reloaded.load("ACME")
    d1_dates = {c.ts.date().isoformat() for c in reloaded._data["ACME"][Timeframe.D1]}
    assert d1_dates == {"2026-07-14", "2026-07-15"}     # both days survived

    r3 = runner.invoke(app, ["list", "--dir", str(tmp_path)])
    assert r3.exit_code == 0
    assert f"{fit('ACME', reloaded, NSE)['score']:.1f}" in r3.output


def test_list_shows_dash_without_cache(tmp_path):
    _init(tmp_path, ["ACME"])
    r = runner.invoke(app, ["list", "--dir", str(tmp_path)])
    assert r.exit_code == 0 and "-" in r.output


def test_watch_auto_picks_top_fit(tmp_path):
    _init(tmp_path, ["GOOD", "BAD"])
    store = CandleStore(tmp_path / "journal" / "candles", NSE)

    good_d1 = [_d1("GOOD", i, 100, 102.5, 97.5, 100) for i in range(6)]
    good_d1[-1] = _d1("GOOD", 5, 100, 130, 97.5, 100)             # new 5-day high
    store._data["GOOD"] = {tf: [] for tf in Timeframe}
    store._data["GOOD"][Timeframe.D1] = good_d1
    store._data["GOOD"][Timeframe.M5] = [_m5("GOOD", i, 10, 10.5, 9.5, 10) for i in range(6)]

    bad_d1 = [_d1("BAD", i, 100 * (i % 2 + 1), 100 * (i % 2 + 1) + 1,
                  100 * (i % 2 + 1) - 1, 100 * (i % 2 + 1)) for i in range(6)]  # alternating gaps
    store._data["BAD"] = {tf: [] for tf in Timeframe}
    store._data["BAD"][Timeframe.D1] = bad_d1
    store._data["BAD"][Timeframe.M5] = [_m5("BAD", i, 10, 10.05, 9.95, 10) for i in range(6)]

    store.save("GOOD")
    store.save("BAD")

    good_score, bad_score = (fit("GOOD", store, NSE)["score"], fit("BAD", store, NSE)["score"])
    assert good_score != bad_score
    winner, loser = ("GOOD", "BAD") if good_score > bad_score else ("BAD", "GOOD")

    r = runner.invoke(app, ["watch", "--dir", str(tmp_path), "--auto", "1", "--feed", "mock"])
    assert r.exit_code == 0
    assert winner in r.output and loser not in r.output


# ------------------------------------------------------------------ journal

def test_journal_command_reads_fixture(tmp_path):
    j = Journal(tmp_path / "journal")
    d = date(2026, 7, 15)
    j.log("verdict", {"symbol": "ACME", "template": "TREND", "final": 72.5,
                      "at": datetime(2026, 7, 15, 10, 0, tzinfo=IST)}, day=d)
    j.log("trade_open", {"symbol": "ACME", "qty": 10, "price": D("100.5"),
                         "at": datetime(2026, 7, 15, 10, 5, tzinfo=IST)}, day=d)
    r = runner.invoke(app, ["journal", "--day", "2026-07-15", "--dir", str(tmp_path)])
    assert r.exit_code == 0
    assert "verdict" in r.output and "ACME" in r.output and "trade_open" in r.output


# ------------------------------------------------------------------- status

def test_status_command_summarizes_latest_day(tmp_path):
    j = Journal(tmp_path / "journal")
    d = date(2026, 7, 15)
    j.log("trade_open", {"symbol": "ACME"}, day=d)
    j.log("trade_close", {"symbol": "ACME", "pnl": D("150.25")}, day=d)
    j.log("skip", {"symbol": "ACME", "gate": "risk_budget", "reason": "x"}, day=d)
    r = runner.invoke(app, ["status", "--dir", str(tmp_path)])
    assert r.exit_code == 0
    assert "trades" in r.output and "150.25" in r.output and "skips" in r.output


def test_status_no_journal(tmp_path):
    r = runner.invoke(app, ["status", "--dir", str(tmp_path)])
    assert r.exit_code == 0
    assert "no journal entries" in r.output
