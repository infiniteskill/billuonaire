"""learn/calibrate.py: precision proxy, trade linkage, min-sample gate,
+/-10% capped suggestions -- and that analyze() never writes anything."""

from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.learn.calibrate import CalibrationReport, analyze
from trader.store.journal import Journal

IST = ZoneInfo("Asia/Kolkata")
DAY = date(2026, 7, 14)


def ts(day, minute):
    return datetime.combine(day, time(10, 0), tzinfo=IST) + timedelta(minutes=minute)


def verdict(j, day, sym, members, minute=0):
    j.log("verdict", {"symbol": sym, "final": 20.0, "members": members},
          day=day, ts=ts(day, minute))


def trade(j, day, sym, pnl, minute=5):
    j.log("trade_open", {"symbol": sym}, day=day, ts=ts(day, minute))
    j.log("trade_close", {"symbol": sym, "pnl": str(pnl)},
          day=day, ts=ts(day, minute + 30))


def test_precision_counts_win_linked_members_over_all_verdicts(tmp_path):
    j = Journal(tmp_path)
    verdict(j, DAY, "A", [["sweep", "SWEEP", 0.8], ["fvg", "CE_HOLD", 0.5]])
    verdict(j, DAY, "A", [["sweep", "SWEEP", 0.9]], minute=5)   # linked (last)
    trade(j, DAY, "A", "150", minute=10)                        # net-positive
    verdict(j, DAY, "B", [["sweep", "SWEEP", 0.7]], minute=15)  # never traded
    rep = analyze(tmp_path)
    assert (rep.n_verdicts, rep.n_trades, rep.n_wins) == (3, 1, 1)
    assert rep.rows["sweep"] == {"appearances": 3, "wins": 1,
                                 "precision": pytest.approx(1 / 3)}
    assert rep.rows["fvg"] == {"appearances": 1, "wins": 0, "precision": 0.0}


def test_losing_trade_counts_no_wins(tmp_path):
    j = Journal(tmp_path)
    verdict(j, DAY, "A", [["sweep", "SWEEP", 0.8]])
    trade(j, DAY, "A", "-90")
    rep = analyze(tmp_path)
    assert rep.n_trades == 1 and rep.n_wins == 0
    assert rep.rows["sweep"]["wins"] == 0


def test_trade_links_to_last_verdict_before_open(tmp_path):
    """Legacy fallback: a trade_open WITHOUT plan members links to the last
    verdict before it (pre-fix journals)."""
    j = Journal(tmp_path)
    verdict(j, DAY, "A", [["fvg", "CE_HOLD", 0.5]], minute=0)   # stale
    verdict(j, DAY, "A", [["sweep", "SWEEP", 0.8]], minute=5)   # the arm verdict
    trade(j, DAY, "A", "150", minute=10)
    rep = analyze(tmp_path)
    assert rep.rows["sweep"]["wins"] == 1
    assert rep.rows["fvg"]["wins"] == 0


def test_trade_credits_arming_verdict_from_plan_meta(tmp_path):
    """FIX 6: a delayed fill credits the ARMING verdict's members (stamped
    into the trade_open plan meta at arm time), never the symbol's latest
    verdict -- verdict B lands between arm and fill and gets nothing."""
    j = Journal(tmp_path)
    verdict(j, DAY, "A", [["sweep", "SWEEP", 0.8]], minute=0)   # A: arms
    verdict(j, DAY, "A", [["fvg", "CE_HOLD", 0.5]], minute=5)   # B: pre-fill
    j.log("trade_open", {"symbol": "A",
                         "plan": {"members": [["sweep", "SWEEP", 0.8]]}},
          day=DAY, ts=ts(DAY, 10))
    j.log("trade_close", {"symbol": "A", "pnl": "150"},
          day=DAY, ts=ts(DAY, 40))
    rep = analyze(tmp_path)
    assert rep.rows["sweep"]["wins"] == 1
    assert rep.rows["fvg"]["wins"] == 0


def test_min_sample_gate_and_share_suggestion(tmp_path):
    j = Journal(tmp_path)
    for m in range(2):
        verdict(j, DAY, "A", [["sweep", "SWEEP", 0.8]], minute=m * 5)
    verdict(j, DAY, "B", [["fvg", "CE_HOLD", 0.5]], minute=20)
    rep = analyze(tmp_path, weights={"sweep": 10, "fvg": 10}, min_samples=2)
    assert rep.insufficient == ["fvg"] and "fvg" not in rep.suggestions
    assert rep.suggestions == {"sweep": 10}   # sole eligible keeps its mass


def test_suggestions_capped_at_ten_percent(tmp_path):
    j = Journal(tmp_path)
    verdict(j, DAY, "A", [["sweep", "SWEEP", 0.8], ["fvg", "CE_HOLD", 0.5]])
    trade(j, DAY, "A", "150")
    verdict(j, DAY, "B", [["fvg", "CE_HOLD", 0.5]], minute=20)  # dilutes fvg
    rep = analyze(tmp_path, weights={"sweep": 10, "fvg": 10}, min_samples=1)
    # precisions 1/1 vs 1/2 -> raw shares 13.33 / 6.67 of mass 20; both moves
    # exceed 10% of the current weight and get clamped to 11 / 9
    assert rep.suggestions == {"sweep": 11.0, "fvg": 9.0}


def test_zero_precision_everywhere_keeps_current_weights(tmp_path):
    j = Journal(tmp_path)
    verdict(j, DAY, "A", [["sweep", "SWEEP", 0.8], ["fvg", "CE_HOLD", 0.5]])
    rep = analyze(tmp_path, weights={"sweep": 12, "fvg": 8}, min_samples=1)
    assert rep.suggestions == {"sweep": 12, "fvg": 8}


def test_date_bounds_filter_days(tmp_path):
    j = Journal(tmp_path)
    day2 = date(2026, 7, 15)
    verdict(j, DAY, "A", [["sweep", "SWEEP", 0.8]])
    verdict(j, day2, "A", [["fvg", "CE_HOLD", 0.5]])
    rep = analyze(tmp_path, start=day2, end=day2)
    assert set(rep.rows) == {"fvg"} and rep.n_verdicts == 1


def test_memberless_verdicts_are_ignored(tmp_path):
    j = Journal(tmp_path)   # pre-phase-5 journal shape: no members field
    j.log("verdict", {"symbol": "A", "final": 20.0}, day=DAY, ts=ts(DAY, 0))
    trade(j, DAY, "A", "150")
    rep = analyze(tmp_path)
    assert rep.rows == {} and rep.n_verdicts == 1 and rep.n_wins == 1


def test_analyze_is_read_only(tmp_path):
    j = Journal(tmp_path)
    verdict(j, DAY, "A", [["sweep", "SWEEP", 0.8]])
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    rep = analyze(tmp_path, weights={"sweep": 10})
    assert isinstance(rep, CalibrationReport)
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before


def test_empty_journal_dir(tmp_path):
    rep = analyze(Path(tmp_path), weights={"sweep": 10})
    assert rep.n_verdicts == rep.n_trades == 0
    assert rep.insufficient == ["sweep"] and rep.suggestions == {}
