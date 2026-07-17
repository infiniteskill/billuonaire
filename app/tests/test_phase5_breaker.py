"""Phase-5 Task 5 (B14): breaker end-to-end on the scripted breaker_retest day.

Proves the full chain: a real M5 swing level walks SWEPT -> RECLAIMED ->
INVERTED from raw candles alone, the retest fires breaker evidence 0.85,
that evidence lands in an armed-strength verdict's journaled members, and
the cluster it joins actually trades to target."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal as D
from pathlib import Path

import pytest

from tests.harness import ALL_IMPLEMENTED, run_scenario
from trader.config import load_settings
from trader.engine.pipeline import Orchestrator
from trader.feed.mock import ScenarioFeed, breaker_retest
from trader.models.level import LevelKind
from trader.models.position import ExitReason

SYMBOL, DAY, OPEN_PRICE = "ACME", date(2026, 7, 14), 100.0
CONFIG = Path(__file__).resolve().parent.parent / "config" / "config.json"
ARM_THRESHOLD = load_settings(CONFIG).confluence.threshold
POST_OBSERVE = time(11, 0)
BREAKER_MEMBER = ["breaker", "BREAKER_RETEST", 0.85]


def _at(e) -> datetime:
    return datetime.fromisoformat(e["at"])


def _kind(entries, k):
    return [e for e in entries if e["kind"] == k]


@pytest.fixture(scope="module")
def day(tmp_path_factory):
    sc = breaker_retest(SYMBOL, DAY, OPEN_PRICE)
    orch = Orchestrator(load_settings(CONFIG), ScenarioFeed([sc]), [SYMBOL],
                        capital=100000, max_qty=50,
                        journal_dir=tmp_path_factory.mktemp("breaker"))
    orch.run()
    return sc, orch.journal.read(DAY)


# (1) the level's state history walks SWEPT -> RECLAIMED -> INVERTED from raw
# candles (real swings detector + LevelEngine, no hand-built Level), and the
# retest fires exactly one breaker evidence 0.85 at the truth minute
def test_level_walks_swept_reclaimed_inverted_then_breaker_fires():
    sc = breaker_retest(SYMBOL, DAY, OPEN_PRICE)
    res = run_scenario(sc, ALL_IMPLEMENTED)
    lv = next(l for l in res.levels if l.kind is LevelKind.SWING_H
              and l.zone == sc.truth["breaker_zone"])
    assert [st.name for _, st in lv.state_history] == [
        "SWEPT", "RECLAIMED", "INVERTED"]
    open_dt = sc.session_open()
    sweep_bucket = sc.truth["breaker_sweep_minute"] // 5 * 5
    assert [ts for ts, _ in lv.state_history] == [
        open_dt + timedelta(minutes=m)
        for m in (sweep_bucket, sc.truth["reclaim_minute"],
                  sc.truth["inversion_minute"])]
    evs = [e for r in res.runs for e in r.evidence
           if e.detector == "breaker" and e.zone == sc.truth["breaker_zone"]]
    assert [(e.ts, e.strength, e.meta["event"]) for e in evs] == [
        (open_dt + timedelta(minutes=sc.truth["retest_minute"] + 5),
         0.85, "BREAKER_RETEST")]


# (2) B14 gate: breaker evidence is journaled inside armed-strength verdict
# members, on-template, LONG
def test_breaker_in_armed_verdict_members(day):
    sc, entries = day
    armed = [v for v in _kind(entries, "verdict")
             if v["final"] >= ARM_THRESHOLD and _at(v).time() >= POST_OBSERVE]
    assert armed, "no armed-strength verdict journaled"
    with_breaker = [v for v in armed if BREAKER_MEMBER in v["members"]]
    assert with_breaker, "breaker evidence missing from armed verdict members"
    assert all(v["template"] == sc.truth["template"] for v in armed)
    assert {v["direction"] for v in with_breaker} == {
        sc.truth["afternoon_direction"]}


# (3) the breaker cluster arms AND trades: LONG open at an armed verdict that
# carries the breaker member, stop beyond the swept pivot, targets execute as
# partials and the runner rides >= 1R gross to EOD (traded-zone entries carry
# tiny risk so the target ladder collapses to T1/T2 partials; flat brokerage
# swamps net r at this notional, like stop_hunt_survive)
def test_breaker_cluster_trades_to_target(day):
    sc, entries = day
    opens, closes = _kind(entries, "trade_open"), _kind(entries, "trade_close")
    assert len(opens) == 1 and len(closes) == 1
    o, c = opens[0], closes[0]
    assert o["direction"] == "LONG" and _at(o).time() >= POST_OBSERVE
    assert D(o["stop"]) < min(sc.truth["pivot_zone"])
    arming = next(v for v in _kind(entries, "verdict") if v["at"] == o["at"])
    assert arming["final"] >= ARM_THRESHOLD
    assert BREAKER_MEMBER in arming["members"]
    assert _kind(entries, "trade_partial"), "targets did not execute"
    assert c["reason"] == ExitReason.EOD.value
    risk = D(o["price"]) - D(o["stop"])
    assert (D(c["exit_price"]) - D(o["price"])) / risk >= 1
