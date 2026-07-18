import json
from datetime import date, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path
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


def test_init_installs_v2_profile_and_baseline(tmp_path):
    """init writes the evidence-backed v2 profile as config.json (never the
    obsolete baseline) + config.baseline.json alongside for A/B replay."""
    from trader.config import load_settings

    runner.invoke(app, ["init", "--dir", str(tmp_path)])
    s = load_settings(tmp_path / "config.json")
    assert s.confluence.threshold == 6 and "bpr" in s.detectors.enabled
    assert "structure" not in s.detectors.enabled        # measured harmful
    b = load_settings(tmp_path / "config.baseline.json")
    assert b.confluence.weights["structure"] == 15 and b.confluence.weights["breaker"] == 10


def test_templates_resolve_from_package_path(tmp_path):
    """BUG: pyproject packaged only trader*; templates now live INSIDE the
    package (trader/templates + package-data) so a non-editable wheel still
    scaffolds. _TEMPLATE_DIR must resolve under the trader package."""
    import trader
    from trader.cli import _TEMPLATE_DIR

    assert _TEMPLATE_DIR == Path(trader.__file__).resolve().parent / "templates"
    for name in ("config.json", "config.baseline.json", "stocks.json"):
        assert (_TEMPLATE_DIR / name).is_file()

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


# -------------------------------------------------------------- logging (C7)

def test_watch_creates_debug_log_file(tmp_path):
    _init(tmp_path, ["ACME"])
    r = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path), "--feed", "mock"])
    assert r.exit_code == 0
    assert (tmp_path / "logs" / "trader.log").exists()


def test_detector_exception_lands_in_log_file(tmp_path, monkeypatch):
    """A raising detector must not crash the run AND its traceback must land
    in --dir/logs/trader.log (registry logs it; _setup_logging makes it land)."""
    from trader.detectors.liquidity import LiquidityDetector   # v2-enabled

    def boom(self, ctx):
        raise RuntimeError("kaboom-for-log-test")

    monkeypatch.setattr(LiquidityDetector, "detect", boom)
    _init(tmp_path, ["ACME"])
    r = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path), "--feed", "mock"])
    assert r.exit_code == 0                       # run_all swallowed it
    text = (tmp_path / "logs" / "trader.log").read_text()
    assert "detector 'liquidity' failed" in text
    assert "kaboom-for-log-test" in text          # full traceback in the file


def test_verbose_flag_flips_console_to_debug(tmp_path):
    import logging as _logging

    from rich.logging import RichHandler

    _init(tmp_path, ["ACME"])
    runner.invoke(app, ["watch", "1", "--dir", str(tmp_path), "--feed", "mock"])
    rich = [h for h in _logging.getLogger().handlers if isinstance(h, RichHandler)]
    assert rich and rich[0].level == _logging.INFO
    runner.invoke(app, ["watch", "1", "--dir", str(tmp_path), "--feed", "mock",
                        "--verbose"])
    rich = [h for h in _logging.getLogger().handlers if isinstance(h, RichHandler)]
    assert rich and rich[0].level == _logging.DEBUG


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


def test_watch_persists_timestats(tmp_path):
    """watch wires timestats_dir: learned sweep counts land under
    dir/journal/timestats per symbol."""
    _init(tmp_path, ["ACME"])
    r = runner.invoke(app, ["watch", "1", "--dir", str(tmp_path), "--feed", "mock"])
    assert r.exit_code == 0
    assert (tmp_path / "journal" / "timestats" / "timestats-ACME.json").exists()


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


# ------------------------------------------------------------ replay / report

def test_replay_cli_runs_and_reports(tmp_path):
    _init(tmp_path, ["ACME"])
    data = tmp_path / "data"
    data.mkdir()
    (data / "ACME.csv").write_text(
        "ts,open,high,low,close,volume\n"
        "2026-07-15T09:15:00+05:30,100,101,99,100.5,1000\n"
        "2026-07-15T09:16:00+05:30,100.5,102,100,101.5,1200\n")
    r = runner.invoke(app, ["replay", "--data", str(data), "--from", "2026-07-15",
                            "--to", "2026-07-15", "--stocks", "1", "--dir", str(tmp_path)])
    assert r.exit_code == 0
    assert "Replay Summary" in r.output and "Totals" in r.output
    assert "CIs unreliable" in r.output


def test_replay_all_uses_every_csv_except_index(tmp_path, monkeypatch):
    _init(tmp_path, ["ACME"])
    data = tmp_path / "data"
    data.mkdir()
    for s in ("AAA", "ZZZ", "NIFTY"):
        (data / f"{s}.csv").write_text("ts,open,high,low,close,volume\n")
    seen = {}
    import trader.cli as cli_mod
    monkeypatch.setattr(cli_mod, "run_replay", lambda st, d, syms, s0, s1, jd, **kw:
                        seen.update(syms=syms, **kw) or {"trades": 0})
    r = runner.invoke(app, ["replay", "--data", str(data), "--from", "2026-07-14",
                            "--to", "2026-07-15", "--all", "--dir", str(tmp_path),
                            "--index", "NIFTY"])
    assert r.exit_code == 0
    assert seen["syms"] == ["AAA", "ZZZ"] and seen["index"] == "NIFTY"


def test_replay_fresh_wipes_journal_dir(tmp_path):
    """T3: reruns must not append duplicate day entries -- default --fresh
    wipes dir/journal first; --no-fresh accumulates (watch-style)."""
    _init(tmp_path, ["ACME"])
    data = tmp_path / "data"
    data.mkdir()
    (data / "ACME.csv").write_text(
        "ts,open,high,low,close,volume\n"
        "2026-07-15T09:15:00+05:30,100,101,99,100.5,1000\n")
    sentinel = tmp_path / "journal" / "stale.marker"
    base = ["replay", "--data", str(data), "--from", "2026-07-15",
            "--to", "2026-07-15", "--stocks", "1", "--dir", str(tmp_path)]
    for extra, survives in (([], False), (["--no-fresh"], True)):
        sentinel.parent.mkdir(exist_ok=True)
        sentinel.write_text("")
        assert runner.invoke(app, base + extra).exit_code == 0
        assert sentinel.exists() is survives


def test_replay_validation_errors(tmp_path):
    _init(tmp_path, ["ACME"])
    data = tmp_path / "data"
    data.mkdir()
    base = ["replay", "--data", str(data), "--dir", str(tmp_path)]
    for extra, msg in (
            (["--from", "2026-07-15", "--to", "2026-07-14", "--all"], "after"),
            (["--from", "bogus", "--to", "2026-07-14", "--all"], "invalid date"),
            (["--from", "2026-07-14", "--to", "2026-07-15"], "--stocks"),
            (["--from", "2026-07-14", "--to", "2026-07-15", "--stocks", "x"], "invalid --stocks"),
            (["--from", "2026-07-14", "--to", "2026-07-15", "--all"], "no symbols")):
        r = runner.invoke(app, base + extra)
        out = r.output + (r.stderr or "")
        assert r.exit_code == 1 and msg in out and "Traceback" not in out


def _report_fixture(root):
    j = Journal(root)
    d1, d2 = date(2026, 7, 14), date(2026, 7, 15)
    j.log("verdict", {"symbol": "AAA", "template": "TRAP_REVERSAL", "final": 6.0}, day=d1)
    j.log("skip", {"symbol": "AAA", "gate": "risk_budget", "reason": "x"}, day=d1)
    j.log("trade_open", {"symbol": "AAA", "direction": "LONG", "qty": 10,
                         "price": D("100"), "stop": D("95")}, day=d1)
    j.log("trade_close", {"symbol": "AAA", "reason": "EXIT_TARGET", "pnl": D("70"),
                          "r": 1.4, "exit_price": D("110")}, day=d1)
    j.log("skip", {"symbol": "AAA", "gate": "fsm_arm", "reason": "y"}, day=d2)


def test_calibrate_prints_suggestions_and_never_writes(tmp_path):
    """calibrate: >=30 wyckoff appearances earn a suggestion, thin detectors
    read insufficient, a copy-paste weights block prints -- and config.json
    is byte-identical after (PRINT ONLY)."""
    _init(tmp_path, ["ACME"])
    j = Journal(tmp_path / "journal")
    day = date(2026, 7, 14)
    at = datetime(2026, 7, 14, 11, 0, tzinfo=IST)
    for m in range(30):
        j.log("verdict", {"symbol": "ACME",
                          "members": [["wyckoff", "SPRING", 0.8]]},
              day=day, ts=at + timedelta(minutes=5 * m))
    j.log("trade_open", {"symbol": "ACME"}, day=day, ts=at + timedelta(hours=3))
    j.log("trade_close", {"symbol": "ACME", "pnl": "100"}, day=day,
          ts=at + timedelta(hours=4))
    before = (tmp_path / "config.json").read_bytes()
    r = runner.invoke(app, ["calibrate", "--journal", str(tmp_path / "journal"),
                            "--dir", str(tmp_path)])
    assert r.exit_code == 0
    assert "wyckoff" in r.output and "insufficient" in r.output
    assert "copy-paste" in r.output and '"wyckoff"' in r.output
    assert (tmp_path / "config.json").read_bytes() == before


def test_calibrate_without_config_precision_only(tmp_path):
    j = Journal(tmp_path / "journal")
    j.log("verdict", {"symbol": "A", "members": [["sweep", "SWEEP", 0.8]]},
          day=date(2026, 7, 14), ts=datetime(2026, 7, 14, 11, 0, tzinfo=IST))
    r = runner.invoke(app, ["calibrate", "--journal", str(tmp_path / "journal"),
                            "--dir", str(tmp_path / "nowhere")])
    assert r.exit_code == 0
    assert "no weight suggestions" in r.output and "sweep" in r.output


def test_report_command_renders_tables(tmp_path):
    _report_fixture(tmp_path)
    r = runner.invoke(app, ["report", "--journal", str(tmp_path)])
    assert r.exit_code == 0
    for text in ("Totals", "TRAP_REVERSAL", "EXIT_TARGET", "risk_budget",
                 "Per day", "CIs unreliable"):
        assert text in r.output


def test_report_command_date_bounds(tmp_path):
    _report_fixture(tmp_path)
    r = runner.invoke(app, ["report", "--journal", str(tmp_path),
                            "--from", "2026-07-15"])
    assert r.exit_code == 0
    assert "TRAP_REVERSAL" not in r.output and "fsm_arm" in r.output
