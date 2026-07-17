"""Phase-5 gate: FileFeed replay == ScenarioFeed run, entry for entry."""

from datetime import date

import pytest

from trader.config import load_settings
from trader.engine.pipeline import Orchestrator
from trader.feed.mock import (ScenarioFeed, double_trap, judas_reversal,
                              range_pin, stop_hunt_survive, trend_day)
from trader.replay.engine import run_replay
from trader.store.journal import Journal
from tests.test_phase4_e2e import CONFIG

DAY, DAY2 = date(2026, 7, 14), date(2026, 7, 15)
CAPITAL, MAX_QTY = 100000, 50
MAKERS = (judas_reversal, trend_day, range_pin, double_trap, stop_hunt_survive)


def _write_csv(path, candles) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("ts,open,high,low,close,volume\n" + "".join(
        f"{c.ts.isoformat()},{c.open},{c.high},{c.low},{c.close},{c.volume}\n"
        for c in candles))


# GATE: the 5 mock scenarios through ScenarioFeed vs CSV+FileFeed+run_replay
# produce IDENTICAL journals (single-pipeline proof at the file layer)
def test_gate_replay_matches_scenariofeed(tmp_path):
    scs = [mk(f"S{i}", DAY, 100.0) for i, mk in enumerate(MAKERS)]
    symbols = [sc.symbol for sc in scs]
    cfg = load_settings(CONFIG)
    Orchestrator(cfg, ScenarioFeed(scs), symbols, capital=CAPITAL,
                 max_qty=MAX_QTY, journal_dir=tmp_path / "live").run()
    for sc in scs:
        _write_csv(tmp_path / "data" / f"{sc.symbol}.csv", sc.candles())
    run_replay(cfg, tmp_path / "data", symbols, DAY, DAY, tmp_path / "replay",
               capital=CAPITAL, max_qty=MAX_QTY)
    live = Journal(tmp_path / "live").read(DAY)
    kinds = {e["kind"] for e in live}
    assert {"verdict", "trade_open", "trade_close", "skip"} <= kinds  # non-vacuous
    assert Journal(tmp_path / "replay").read(DAY) == live


@pytest.fixture(scope="module")
def two_day_csv(tmp_path_factory):
    data = tmp_path_factory.mktemp("data")
    _write_csv(data / "ACME.csv",
               [c for d in (DAY, DAY2)
                for c in judas_reversal("ACME", d, 100.0).candles()])
    return data


def test_replay_multi_day_sessions(two_day_csv, tmp_path):
    """One run spans both sessions: day 1 trades; day 2 is processed with
    day-1 levels carried (its identical setup now reads stop_too_wide)."""
    cfg = load_settings(CONFIG)
    summary = run_replay(cfg, two_day_csv, ["ACME"], DAY, DAY2, tmp_path,
                         capital=CAPITAL, max_qty=MAX_QTY)
    assert summary["trades"] >= 1
    assert any(e["kind"] == "trade_open" for e in Journal(tmp_path).read(DAY))
    assert Journal(tmp_path).read(DAY2)          # second session journaled too


def test_replay_range_filters_days(two_day_csv, tmp_path):
    cfg = load_settings(CONFIG)
    run_replay(cfg, two_day_csv, ["ACME"], DAY, DAY, tmp_path,
               capital=CAPITAL, max_qty=MAX_QTY)
    assert Journal(tmp_path).read(DAY)
    assert not (tmp_path / f"{DAY2.isoformat()}.jsonl").exists()
