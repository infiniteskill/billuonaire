from datetime import date
from decimal import Decimal as D

import pytest

from trader.replay.metrics import compute
from trader.store.journal import Journal

D1, D2 = date(2026, 7, 14), date(2026, 7, 15)


@pytest.fixture()
def journal_dir(tmp_path):
    j = Journal(tmp_path)
    # day 1: winning LONG with a partial, template journaled, 3 skips
    j.log("verdict", {"symbol": "AAA", "template": "TRAP_REVERSAL", "final": 6.0}, day=D1)
    for gate in ("risk_budget", "risk_budget", "fsm_arm"):
        j.log("skip", {"symbol": "AAA", "gate": gate, "reason": "x"}, day=D1)
    j.log("trade_open", {"symbol": "AAA", "direction": "LONG", "qty": 10,
                         "price": D("100"), "stop": D("95")}, day=D1)
    j.log("trade_partial", {"symbol": "AAA", "qty": 5, "price": D("105")}, day=D1)
    j.log("trade_close", {"symbol": "AAA", "reason": "EXIT_TARGET", "pnl": D("70"),
                          "r": 1.4, "exit_price": D("110")}, day=D1)
    # day 2: losing SHORT, no partials, no verdict (template "-")
    j.log("trade_open", {"symbol": "AAA", "direction": "SHORT", "qty": 5,
                         "price": D("200"), "stop": D("204")}, day=D2)
    j.log("trade_close", {"symbol": "AAA", "reason": "EXIT_STOP", "pnl": D("-22"),
                          "r": -1.1, "exit_price": D("204")}, day=D2)
    return tmp_path


def test_totals_gross_net_split(journal_dir):
    t = compute(journal_dir).totals
    # gross day1: 5*(105-100) + 5*(110-100) = 75 over risk 50 => 1.5R
    # gross day2: 5*(204-200)*-1 = -20 over risk 20 => -1.0R
    assert (t["trades"], t["wins"], t["losses"], t["wr"]) == (2, 1, 1, 0.5)
    assert t["gross_r"] == pytest.approx(0.5) and t["net_r"] == pytest.approx(0.3)
    assert (t["gross_pnl"], t["net_pnl"]) == (D("55"), D("48"))
    assert t["pf_gross"] == pytest.approx(3.75)
    assert t["pf_net"] == pytest.approx(70 / 22)
    assert t["expectancy_r"] == pytest.approx(0.15)
    assert t["max_dd_r"] == pytest.approx(1.1)     # 1.4 peak -> 0.3


def test_tables(journal_dir):
    rep = compute(journal_dir)
    assert rep.per_template["TRAP_REVERSAL"]["n"] == 1 and rep.per_template["-"]["n"] == 1
    assert rep.per_symbol["AAA"]["n"] == 2
    assert rep.per_symbol["AAA"]["gross_r"] == pytest.approx(0.5)
    assert {k: v["n"] for k, v in rep.per_exit.items()} == {"EXIT_STOP": 1, "EXIT_TARGET": 1}
    assert rep.per_gate == {"risk_budget": 2, "fsm_arm": 1}


def test_day_cluster_and_ci_note(journal_dir):
    rep = compute(journal_dir)
    assert rep.per_day == [(D1.isoformat(), 1, 1.4), (D2.isoformat(), 1, -1.1)]
    assert rep.day_stats["mean"] == pytest.approx(0.15)
    assert rep.day_stats["std"] == pytest.approx(1.25)
    assert rep.day_stats["n_days"] == 2
    assert any("CIs unreliable" in n for n in rep.notes)


def test_date_bounds(journal_dir):
    rep = compute(journal_dir, start=D2, end=D2)
    assert rep.totals["trades"] == 1 and rep.per_day[0][0] == D2.isoformat()


def test_empty_journal(tmp_path):
    rep = compute(tmp_path)
    t = rep.totals
    assert t["trades"] == 0 and t["wr"] == 0.0 and t["pf_net"] is None
    assert rep.day_stats["n_days"] == 0 and rep.notes


def test_unmatched_opens_zero_when_all_close(journal_dir):
    rep = compute(journal_dir)
    assert rep.totals["unmatched_opens"] == 0
    assert not any("unmatched" in n for n in rep.notes)


def test_unmatched_open_counted_not_silently_dropped(journal_dir):
    # a trade_open with no trade_close (engine anomaly) must surface as a
    # metric + note, never vanish from the report
    Journal(journal_dir).log("trade_open", {"symbol": "BBB", "direction": "LONG",
                                            "qty": 1, "price": D("50"),
                                            "stop": D("49")}, day=D2)
    rep = compute(journal_dir)
    assert rep.totals["unmatched_opens"] == 1
    assert rep.totals["trades"] == 2               # matched trades unaffected
    assert any("unmatched_opens=1" in n for n in rep.notes)
