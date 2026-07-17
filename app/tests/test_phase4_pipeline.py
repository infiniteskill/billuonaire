"""Phase-4 Task 5: SymbolPipeline + Orchestrator integration.

Covers the contract: a full judas_reversal day (x2 days) through the real
Orchestrator with the shipped config; broker+manager wiring (2 partials +
EOD remainder, exact Decimal accounting incl costs); the shared RiskState
blocking a third symbol after two losses; and IndexView reaching stock ctx.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from trader.config import Settings
from trader.engine.context import DayState, IndexView, StockContext
from trader.engine.entry import EntryState
from trader.engine.gates import RiskState
from trader.engine.pipeline import Orchestrator, SymbolPipeline
from trader.execution.manager import Action, PositionManager
from trader.execution.paper import PaperBroker
from trader.feed.mock import ScenarioFeed, judas_reversal, trend_day
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction
from trader.models.position import Fill, Position
from trader.models.signal import TradePlan
from trader.store.candles import CandleStore
from trader.store.journal import Journal

IST = ZoneInfo("Asia/Kolkata")
CONFIG = Path(__file__).resolve().parent.parent / "config" / "config.json"
D = Decimal
DAY1, DAY2 = date(2026, 7, 14), date(2026, 7, 15)
PCT = (D("0.025") + D("0.00297")) / 100          # config statutory percents


def cfg() -> Settings:
    return Settings.model_validate_json(CONFIG.read_text())


def cost(price: Decimal, qty: int) -> Decimal:
    return D("20") + PCT * price * qty


def m1(sym, ts, o, h, lo, c, vol=1000):
    return Candle(sym, Timeframe.M1, ts, D(str(o)), D(str(h)), D(str(lo)),
                  D(str(c)), vol)


def make_pipeline(tmp_path, max_qty=50):
    s = cfg()
    spec = s.market_spec()
    risk = RiskState(s)
    pipe = SymbolPipeline("X", s, CandleStore(tmp_path / "candles", spec),
                          Journal(tmp_path / "journal"), PaperBroker(s),
                          PositionManager(s, spec), risk, max_qty)
    return pipe, risk


# ------------------------------------------------- 1. full-day orchestrator

def test_judas_two_day_orchestrator(tmp_path):
    """Day 1: the canonical reversal cluster (distinct>=4 LONG at the pivot)
    must ARM, fill and close profitably. Day 2 gaps up +7: carried-over M5
    history keeps ATR/wyckoff live from the session open, so the same pivot
    re-scores above threshold (verdicts) but its cluster chains wider and
    every arm attempt is REFUSED stop_too_wide -- journaled risk discipline."""
    feed = ScenarioFeed([judas_reversal("ACME", DAY1, 100.0),
                         judas_reversal("ACME", DAY2, 107.0)])
    orch = Orchestrator(cfg(), feed, ["ACME"], capital=100000, max_qty=50,
                        journal_dir=tmp_path)
    summary = orch.run()
    pipe = orch.pipelines["ACME"]
    # ran both sessions; DayState was reset onto day 2 (fresh po3 dict too)
    assert pipe.day.session_date == DAY2
    assert isinstance(pipe.day.po3, dict)
    assert len(pipe.evidence_history) <= 200
    entries = orch.journal.read(DAY1) + orch.journal.read(DAY2)
    verdicts = [e for e in entries if e["kind"] == "verdict"]
    assert verdicts, "no verdict entries journaled on a judas day"
    assert all(v["mults"] and {"align", "time", "template", "obviousness"}
               <= set(v["mults"]) for v in verdicts)
    threshold = cfg().confluence.threshold
    armable = [v for v in verdicts if v["final"] >= threshold]
    assert armable and all(v["direction"] == "LONG" and v["distinct"] >= 4
                           and v["template"] == "TRAP_REVERSAL" for v in armable)
    # day 1 arms at the 12:50 pivot and the trade closes profitably
    day1 = orch.journal.read(DAY1)
    opens = [e for e in day1 if e["kind"] == "trade_open"]
    closes = [e for e in day1 if e["kind"] == "trade_close"]
    assert len(opens) == 1 and opens[0]["direction"] == "LONG"
    assert opens[0]["at"][11:16] == "12:50" and opens[0]["stop"] == "100.20"
    assert len(closes) == 1 and Decimal(closes[0]["pnl"]) > 0
    assert summary["trades"] == 1 and summary["wins"] == 1
    # day 2: pivot re-scores above threshold, but arms are refused
    day2 = orch.journal.read(DAY2)
    assert [e for e in day2 if e["kind"] == "verdict" and e["final"] >= threshold]
    day2_skips = [e for e in day2 if e["kind"] == "skip"]
    assert day2_skips and all(e["reason"] == "stop_too_wide" for e in day2_skips)
    assert not [e for e in day2 if e["kind"] == "trade_open"]
    assert set(summary) == {"trades", "wins", "losses", "pnl", "skips"}
    assert summary["skips"] == len([e for e in entries if e["kind"] == "skip"])


# --------------------------------------------- 2. broker+manager integration

def test_partials_and_eod_exact_accounting(tmp_path):
    """Scripted LONG 50 @ ~100 stop 95: 1R and 2R shave 16 each through the
    broker, EOD squares off the remaining 18; realized is the exact Decimal
    sum including entry + exit costs, and RiskState records the close."""
    pipe, risk = make_pipeline(tmp_path)
    t0 = datetime(2026, 7, 14, 9, 55, tzinfo=IST)
    pipe.on_m1(m1("X", t0, 100, 100, 100, 100))                    # warm-up M5
    plan = TradePlan("X", Direction.LONG, (D("99"), D("101")), D("95"),
                     [D("107"), D("110"), D("115")], 50, 70.0, t0,
                     {"final": 70.0, "mults": {"align": 1.0}})
    pipe._pending_plan = plan                                      # scripted arm
    pipe.on_m1(m1("X", t0 + timedelta(minutes=5), 100, 106, 100, 106))   # fill @100
    pos = pipe.position
    assert pos is not None and pos.remaining_qty == 50
    assert pos.entry.price == D("100.05")                          # adverse open
    pipe.on_m1(m1("X", t0 + timedelta(minutes=10), 106, 111, 106, 111))  # 1R seen
    assert pos.remaining_qty == 34 and "1R" in pos.partials
    pipe.on_m1(m1("X", t0 + timedelta(minutes=15), 111, 112, 110, 111))  # 2R seen
    assert pos.remaining_qty == 18 and "2R" in pos.partials
    pipe.on_m1(m1("X", t0.replace(hour=15, minute=10), 111, 111, 110, 111))
    pipe.on_m1(m1("X", t0.replace(hour=15, minute=15), 111, 111, 110, 111))  # EOD
    assert pipe.position is None and pos.remaining_qty == 0
    expected = (-cost(D("100.05"), 50)
                + (D("105.95") - D("100.05")) * 16 - cost(D("105.95"), 16)
                + (D("110.95") - D("100.05")) * 16 - cost(D("110.95"), 16)
                + (D("110.95") - D("100.05")) * 18 - cost(D("110.95"), 18))
    assert pos.realized == expected
    assert risk.trades_today == 1 and risk.consecutive_losses == 0
    assert risk.daily_pnl_R == pytest.approx(float(expected / (D("5.05") * 50)))
    kinds = [e["kind"] for e in pipe.journal.read(t0.date())]
    assert "trade_open" in kinds and "trade_close" in kinds


# --------------------------------------------- 2b. stale/late pending plans

def test_pending_plan_dropped_on_new_session(tmp_path):
    """A plan queued on day-1's last evaluated bucket must NOT fill at
    day-2's open (day-old stop/targets across the gap); an armed FSM must
    not survive the session change either."""
    pipe, _ = make_pipeline(tmp_path)
    t = datetime(2026, 7, 14, 15, 20, tzinfo=IST)
    pipe.on_m1(m1("X", t, 100, 100, 100, 100))
    pipe.on_m1(m1("X", t + timedelta(minutes=5), 100, 100, 100, 100))  # day set
    plan = TradePlan("X", Direction.LONG, (D("99"), D("101")), D("95"),
                     [D("107")], 10, 70.0, t + timedelta(minutes=5), {})
    pipe._pending_plan = plan
    pipe.fsm.state, pipe.fsm.plan = EntryState.ARMED, plan
    pipe.fsm._armed_ts = plan.created
    pipe.on_m1(m1("X", datetime(2026, 7, 15, 9, 15, tzinfo=IST),
                  102, 102, 102, 102))
    assert pipe.position is None and pipe._pending_plan is None
    assert pipe.fsm.state is EntryState.IDLE and pipe.fsm.plan is None
    skips = [e for e in pipe.journal.read(date(2026, 7, 14))
             if e["kind"] == "skip" and e["reason"] == "session_end"]
    assert len(skips) == 2                       # dropped plan + disarmed FSM


def test_fill_after_no_entry_cutoff_dropped(tmp_path):
    """A pending entry whose fill M1 lands at/after no_entry_after (14:30)
    is dropped, journaled as skip 'too_late', and opens nothing."""
    pipe, risk = make_pipeline(tmp_path)
    t = datetime(2026, 7, 14, 14, 25, tzinfo=IST)
    pipe.on_m1(m1("X", t, 100, 100, 100, 100))
    pipe.on_m1(m1("X", t + timedelta(minutes=5), 100, 100, 100, 100))  # day set
    pipe._pending_plan = TradePlan("X", Direction.LONG, (D("99"), D("101")),
                                   D("95"), [D("107")], 10, 70.0,
                                   t + timedelta(minutes=5), {})
    pipe.on_m1(m1("X", t + timedelta(minutes=10), 100, 100, 100, 100))  # 14:35
    assert pipe.position is None and pipe._pending_plan is None
    assert risk.trades_today == 0
    skips = [e for e in pipe.journal.read(t.date()) if e["kind"] == "skip"]
    assert any(e["reason"] == "too_late" for e in skips)


# ------------------------------------------------------ 3. shared RiskState

def test_risk_state_shared_across_symbols(tmp_path):
    orch = Orchestrator(cfg(), ScenarioFeed([]), ["A", "B", "C"],
                        capital=100000, max_qty=50, journal_dir=tmp_path)
    t = datetime(2026, 7, 14, 11, 30, tzinfo=IST)
    for sym in ("A", "B"):                       # two losing closes wired
        pipe = orch.pipelines[sym]               # through broker.exit_fill
        pipe.day = DayState(session_date=t.date())
        plan = TradePlan(sym, Direction.LONG, (D("99"), D("101")), D("95"),
                         [D("107")], 10, 70.0, t, {})
        pipe.position = Position(plan, Fill(D("100"), 10, t, D("20")), 10, D("95"))
        pipe._pending_exits = [Action("EXIT_STOP", None, "close_beyond_stop")]
        pipe._fill_pending(m1(sym, t, 95, 95, 94, 95))
        assert pipe.position is None
    assert orch.risk.consecutive_losses == 2 and orch.risk.locked
    third = orch.pipelines["C"]                  # third arm is gate-blocked
    ctx = StockContext("C", t, CandleStore(tmp_path / "cc").view("C", t), [], [],
                       DayState(session_date=t.date(), template="TREND"))
    verdict = third.gates.check(ctx, Direction.LONG, None, "UNCLEAR", orch.risk)
    assert not verdict.allow and verdict.gate == "risk_budget"


# --------------------------------------------------------- 4. index wiring

def test_index_view_reaches_stock_ctx(tmp_path, monkeypatch):
    seen = []
    orig = SymbolPipeline._on_m5_close

    def spy(self, now, index):
        if not self.is_index:
            seen.append(index)
        return orig(self, now, index)

    monkeypatch.setattr(SymbolPipeline, "_on_m5_close", spy)
    feed = ScenarioFeed([judas_reversal("ACME", DAY1, 100.0),
                         trend_day("NIFTY", DAY1, 200.0)])
    orch = Orchestrator(cfg(), feed, ["ACME"], index_symbol="NIFTY",
                        capital=100000, max_qty=50, journal_dir=tmp_path)
    orch.run()
    views = [v for v in seen if v is not None]
    assert views, "IndexView never reached the stock pipeline"
    assert all(isinstance(v, IndexView) for v in views)
    assert any(v.trend is Direction.LONG for v in views)   # index trend day
