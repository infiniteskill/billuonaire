"""Phase-5 Task 4: the learning loop, timestats side.

The pipeline records exactly ONE (bucket, swept?) observation per closed M5
bar (gap boundaries only tick time), so after a judas day the sweep buckets'
danger sits ABOVE the cold-start prior and quiet buckets sit below; a
``timestats_dir`` persists per-symbol counts across Orchestrator runs
(save at finalize/session end, load at pipeline init).
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from trader.config import Settings
from trader.engine.gates import RiskState
from trader.learn.calibrate import analyze
from trader.engine.pipeline import Orchestrator, SymbolPipeline
from trader.execution.manager import PositionManager
from trader.execution.paper import PaperBroker
from trader.feed.mock import ScenarioFeed, judas_reversal
from trader.models.candle import Candle, Timeframe
from trader.store.candles import CandleStore
from trader.store.journal import Journal

IST = ZoneInfo("Asia/Kolkata")
CONFIG = Path(__file__).resolve().parent.parent / "trader" / "templates" / "config.baseline.json"
DAY1 = date(2026, 7, 14)
D = Decimal


def cfg() -> Settings:
    from tests.harness import ALL_IMPLEMENTED, scenario_settings
    return scenario_settings(ALL_IMPLEMENTED)  # shipped enabled, guard off


def run_judas(tmp_path, timestats_dir=None):
    feed = ScenarioFeed([judas_reversal("ACME", DAY1, 100.0)])
    orch = Orchestrator(cfg(), feed, ["ACME"], capital=100000, max_qty=50,
                        journal_dir=tmp_path / "journal",
                        timestats_dir=timestats_dir)
    orch.run()
    return orch.pipelines["ACME"]


def test_judas_shifts_sweep_bucket_danger(tmp_path):
    """One record per closed M5 (74 on a 375-min day, buckets 1..74); the
    ORL sweep (m37 -> close at open+40 => bucket 8) and the pivot sweep
    (m191 -> bucket 39) land swept=True, so their danger rises above the
    cold-start prior while never-swept buckets drift below it."""
    pipe = run_judas(tmp_path)
    ts, spec = pipe.timestats, pipe.spec
    counts = ts._counts["ACME"]
    assert len(counts) == 74
    assert all(t == 1 for _, t in counts.values())
    swept = {b for b, (s, _) in counts.items() if s}
    assert 8 in swept and 39 in swept
    for b in swept:
        assert ts.danger("ACME", b, spec) > ts.prior(b, spec)
    quiet = next(b for b, (s, _) in counts.items() if not s)
    assert ts.danger("ACME", quiet, spec) < ts.prior(quiet, spec)


def test_timestats_dir_round_trips_counts(tmp_path):
    """finalize() persists to timestats_dir; a fresh Orchestrator on the
    same dir loads the learned counts at pipeline init."""
    tdir = tmp_path / "timestats"
    pipe = run_judas(tmp_path, timestats_dir=tdir)
    assert (tdir / "timestats-ACME.json").exists()
    orch2 = Orchestrator(cfg(), ScenarioFeed([]), ["ACME"], capital=100000,
                         max_qty=50, journal_dir=tmp_path / "j2",
                         timestats_dir=tdir)
    ts2 = orch2.pipelines["ACME"].timestats
    assert ts2._counts["ACME"] == pipe.timestats._counts["ACME"]


def test_journal_members_feed_calibration(tmp_path):
    """Verdicts journal their zone members [(detector, event, strength)];
    analyze() closes the loop on a REAL judas journal: the day-1 winning
    trade links to a member-bearing verdict, so sweep scores a win."""
    run_judas(tmp_path)
    entries = Journal(tmp_path / "journal").read(DAY1)
    verdicts = [e for e in entries if e["kind"] == "verdict"]
    assert verdicts and all(e["members"] for e in verdicts)
    det, event, strength = verdicts[-1]["members"][0]      # journaled shape
    assert isinstance(det, str) and isinstance(strength, float)
    rep = analyze(tmp_path / "journal")
    assert rep.n_trades == 1 and rep.n_wins == 1
    assert rep.rows["sweep"]["wins"] >= 1
    assert rep.rows["sweep"]["appearances"] >= rep.rows["sweep"]["wins"]


def test_gap_boundaries_record_once_per_new_bar(tmp_path):
    """A6 gap: an M1 jumping 3 M5 buckets closes every boundary but only ONE
    new bar exists -- exactly one timestats observation."""
    s = cfg()
    spec = s.market_spec()
    pipe = SymbolPipeline("X", s, CandleStore(tmp_path / "c", spec),
                          Journal(tmp_path / "j"), PaperBroker(s),
                          PositionManager(s, spec), RiskState(s), 10)
    t0 = datetime.combine(DAY1, time(10, 0), tzinfo=IST)
    mk = lambda m: Candle("X", Timeframe.M1, t0 + timedelta(minutes=m),
                          D("100"), D("101"), D("99"), D("100"), 1000)
    for m in range(5):
        pipe.on_m1(mk(m))
    pipe.on_m1(mk(17))
    assert sum(t for _, t in pipe.timestats._counts["X"].values()) == 1
