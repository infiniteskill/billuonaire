"""Phase-4 Task 5: SymbolPipeline + Orchestrator integration.

Covers the contract: a full judas_reversal day (x2 days) through the real
Orchestrator with the shipped config; broker+manager wiring (2 partials +
EOD remainder, exact Decimal accounting incl costs); the shared RiskState
blocking a third symbol after two losses; and IndexView reaching stock ctx.
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from types import SimpleNamespace

from trader.config import Settings
from trader.engine.confluence import ScoredZone
from trader.engine.context import DayState, IndexView, StockContext
from trader.engine.entry import EntryState
from trader.engine.gates import RiskState, Verdict
from trader.engine.levels import LevelStore
from trader.engine.pipeline import Orchestrator, SymbolPipeline
from trader.execution.manager import Action, PositionManager
from trader.execution.paper import PaperBroker
from trader.feed.mock import ScenarioFeed, judas_reversal, trend_day
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind, LevelState
from trader.models.position import ExitReason, Fill, Position
from trader.models.signal import TradePlan
from trader.store.candles import CandleStore
from trader.store.journal import Journal

IST = ZoneInfo("Asia/Kolkata")
CONFIG = Path(__file__).resolve().parent.parent / "config" / "config.json"
D = Decimal
DAY1, DAY2 = date(2026, 7, 14), date(2026, 7, 15)
PCT_EXCH = D("0.00297") / 100                    # exchange_pct, both legs
PCT = D("0.025") / 100 + PCT_EXCH                 # + STT, SELL leg only


def cfg() -> Settings:
    from tests.harness import ALL_IMPLEMENTED, scenario_settings
    return scenario_settings(ALL_IMPLEMENTED)  # shipped enabled, guard off


def cost(price: Decimal, qty: int) -> Decimal:
    """SELL-leg cost (STT + exchange): use for exits of a LONG."""
    return D("20") + PCT * price * qty


def cost_buy(price: Decimal, qty: int) -> Decimal:
    """BUY-leg cost (exchange only, no STT): use for entry of a LONG."""
    return D("20") + PCT_EXCH * price * qty


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
    must ARM, trigger at the 12:50 pivot and FILL AT THE RESTING LIMIT
    (traded-zone CE 100.60) on the 12:51 M1 -- no market chase -- then close
    profitably. Day 2 gaps up +7: carried-over M5 history keeps ATR/wyckoff
    live from the session open, so the same pivot re-scores above threshold
    early and the chase guard REFUSES 11:00-11:15; the 12:50 pivot arms and
    triggers again but day 2's rally never retraces to the 107.60 limit --
    the order expires (skip "unfilled") instead of chasing 3x risk."""
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
    # day 1 arms at the 12:50 pivot on the TRADED zone (tightest level in
    # the cluster; the natural stop is hunt-tight, so it widens to the
    # 1.0*ATR cost floor 100.40): the limit at CE 100.60 fills on the 12:51
    # M1, then partials 1R + 2R, runner rides to EOD squareoff
    day1 = orch.journal.read(DAY1)
    opens = [e for e in day1 if e["kind"] == "trade_open"]
    closes = [e for e in day1 if e["kind"] == "trade_close"]
    parts = [e for e in day1 if e["kind"] == "trade_partial"]
    assert len(opens) == 1 and opens[0]["direction"] == "LONG"
    assert opens[0]["at"][11:16] == "12:51" and opens[0]["stop"] == "100.40"
    assert opens[0]["price"] == "100.60"                  # AT the limit, no chase
    assert D(opens[0]["stop"]) < D(opens[0]["zone"][0])   # behind traded zone
    assert [p["reason"] for p in parts] == ["1R", "2R"]
    assert len(closes) == 1 and closes[0]["reason"] == ExitReason.EOD.value
    assert D(closes[0]["exit_price"]) > D(opens[0]["price"])
    # day 2: chase guard refuses the early over-threshold re-score; the 12:50
    # pivot triggers but never retraces to the limit => skip "unfilled"
    day2 = orch.journal.read(DAY2)
    assert [e for e in day2 if e["kind"] == "verdict" and e["final"] >= threshold]
    day2_skips = [e for e in day2 if e["kind"] == "skip"]
    assert day2_skips and all("chases" in e["reason"] or e["reason"] == "unfilled"
                              for e in day2_skips)
    assert [e for e in day2_skips if e["reason"] == "unfilled"]
    assert not [e for e in day2 if e["kind"] == "trade_open"]
    assert summary["trades"] == 1 and summary["wins"] == 1
    assert set(summary) == {"trades", "wins", "losses", "pnl", "skips"}
    assert summary["skips"] == len([e for e in entries if e["kind"] == "skip"])


def test_judas_two_day_no_gap_day2_reforms(tmp_path, monkeypatch):
    """Day 2 repeats day 1 at the SAME open (no gap): session-end level
    pruning (A2) drops day-1 M15 swings, so day-2's pre-structure m15_trend
    (A9: swing-derived) reads NEUTRAL instead of day-1's LONG, and day-2
    swings re-form at day-1's exact prices -- the pivot swing-low included --
    instead of being dedupe-blocked by day-1 corpses."""
    trends, orig = [], SymbolPipeline._on_m5_close

    def spy(self, now, index):
        r = orig(self, now, index)
        trends.append((now, self._m15_trend()))
        return r

    monkeypatch.setattr(SymbolPipeline, "_on_m5_close", spy)
    sc2 = judas_reversal("ACME", DAY2, 100.0)
    feed = ScenarioFeed([judas_reversal("ACME", DAY1, 100.0), sc2])
    orch = Orchestrator(cfg(), feed, ["ACME"], capital=100000, max_qty=50,
                        journal_dir=tmp_path)
    orch.run()
    pipe = orch.pipelines["ACME"]
    early = [r for now, r in trends
             if now.date() == DAY2 and now.time() < time(10, 0)]
    assert early and all(r is Direction.NEUTRAL for r in early)   # A1
    pz = tuple(sc2.truth["pivot_zone"])                           # A2
    assert any(lv.kind is LevelKind.SWING_L and lv.zone == pz
               and lv.born.date() == DAY2 for lv in pipe.levels)
    threshold = cfg().confluence.threshold
    assert [v for v in orch.journal.read(DAY2)                    # re-scored
            if v["kind"] == "verdict" and v["final"] >= threshold
            and v["direction"] == "LONG"]


def test_end_session_prunes_stale_levels(tmp_path):
    """Session end keeps live cross-day liquidity (PDH/PDL/EQ/ROUND,
    non-terminal) plus unmitigated OB/FVG zones (continuum); terminal states
    and intraday micro-structure (swings, OR) go."""
    pipe, _ = make_pipeline(tmp_path)
    t = datetime(2026, 7, 14, 15, 25, tzinfo=IST)
    mk = lambda kind, state: Level(f"X-{kind.name}-{state.name}", "X", kind,
                                   (D("99"), D("101")), t, None, state)
    pipe.levels[:] = [mk(LevelKind.PDH, LevelState.ACTIVE),
                      mk(LevelKind.ROUND, LevelState.TESTED),
                      mk(LevelKind.EQH, LevelState.SWEPT),        # not terminal
                      mk(LevelKind.PDL, LevelState.DEAD),         # terminal
                      mk(LevelKind.SWING_L, LevelState.ACTIVE),   # intraday
                      mk(LevelKind.OB_BULL, LevelState.ACTIVE),   # zone: carries
                      mk(LevelKind.FVG_BEAR, LevelState.ACTIVE),  # zone: carries
                      mk(LevelKind.OB_BEAR, LevelState.MITIGATED),  # terminal
                      mk(LevelKind.OPEN_RANGE_H, LevelState.SWEPT)]
    pipe._end_session(datetime(2026, 7, 15, 9, 15, tzinfo=IST))
    assert {lv.kind for lv in pipe.levels} == {
        LevelKind.PDH, LevelKind.ROUND, LevelKind.EQH,
        LevelKind.OB_BULL, LevelKind.FVG_BEAR}


def test_zone_carry_state_intact_and_age_prune(tmp_path):
    """An unmitigated OB/FVG zone crosses the session boundary with state,
    touches and state_history intact; a zone older than max_age_sessions
    (default 5 weekday sessions) is dropped, one exactly at the edge kept."""
    pipe, _ = make_pipeline(tmp_path)
    mk = lambda kind, d, state=LevelState.ACTIVE: Level(
        f"X-{kind.name}-{d.isoformat()}", "X", kind, (D("99"), D("101")),
        datetime.combine(d, time(11, 0), tzinfo=IST), Timeframe.M5, state)
    tested = mk(LevelKind.OB_BULL, DAY1)
    tested.record_state(tested.born, LevelState.TESTED)
    tested.touches = 1
    aged = mk(LevelKind.FVG_BULL, date(2026, 7, 7))   # 5 sessions before DAY1
    edge = mk(LevelKind.OB_BEAR, date(2026, 7, 8))    # 4 sessions: still live
    pipe.levels[:] = [tested, aged, edge]
    pipe.day = DayState(session_date=DAY1)            # session being ended
    pipe._end_session(datetime.combine(DAY2, time(9, 15), tzinfo=IST))
    assert pipe.levels == [tested, edge]
    assert (tested.state, tested.touches) == (LevelState.TESTED, 1)
    assert tested.state_history == [(tested.born, LevelState.TESTED)]


# ------------------------------------------------------- LevelStore wiring

def test_end_session_persists_and_reload_via_pipeline_init(tmp_path):
    """_end_session prunes then persists (level_store wired); a NEW pipeline
    built against the same store+symbol loads exactly that pruned set at
    __init__ -- state survives across process runs."""
    store = LevelStore(tmp_path / "levels")
    s, spec = cfg(), cfg().market_spec()
    mk_pipe = lambda: SymbolPipeline("X", s, CandleStore(tmp_path / "candles", spec),
                                     Journal(tmp_path / "journal"), PaperBroker(s),
                                     PositionManager(s, spec), RiskState(s), 50,
                                     level_store=store)
    pipe = mk_pipe()
    t = datetime(2026, 7, 14, 15, 25, tzinfo=IST)
    mk_lv = lambda kind, state: Level(f"X-{kind.name}-{state.name}", "X", kind,
                                      (D("99"), D("101")), t, None, state)
    pipe.levels[:] = [mk_lv(LevelKind.PDH, LevelState.ACTIVE),
                      mk_lv(LevelKind.SWING_L, LevelState.ACTIVE)]   # intraday, dropped
    pipe._end_session(datetime(2026, 7, 15, 9, 15, tzinfo=IST))

    reloaded = mk_pipe()
    assert [lv.kind for lv in reloaded.levels] == [LevelKind.PDH]
    assert reloaded.levels == store.load("X")


def test_orchestrator_level_dir_survives_across_runs(tmp_path):
    """level_dir wires a LevelStore through the Orchestrator: run() end
    (finalize) persists the cross-day-safe subset WITHOUT mutating the live
    pipeline's levels in place; a second Orchestrator pointed at the same
    level_dir loads exactly that subset at pipeline __init__."""
    level_dir = tmp_path / "levels"
    feed = ScenarioFeed([judas_reversal("ACME", DAY1, 100.0)])
    orch = Orchestrator(cfg(), feed, ["ACME"], capital=100000, max_qty=50,
                        journal_dir=tmp_path / "journal", level_dir=level_dir)
    orch.run()
    pipe = orch.pipelines["ACME"]
    assert any(lv.kind is LevelKind.SWING_L for lv in pipe.levels)  # untouched in memory

    persisted = LevelStore(level_dir).load("ACME")
    carry = {LevelKind.PDH, LevelKind.PDL, LevelKind.EQH, LevelKind.EQL,
             LevelKind.ROUND, LevelKind.OB_BULL, LevelKind.OB_BEAR,
             LevelKind.FVG_BULL, LevelKind.FVG_BEAR}
    assert persisted and {lv.kind for lv in persisted} <= carry
    assert all(lv.state.name not in ("DEAD", "MITIGATED", "INVERTED") for lv in persisted)

    feed2 = ScenarioFeed([judas_reversal("ACME", DAY2, 107.0)])
    orch2 = Orchestrator(cfg(), feed2, ["ACME"], capital=100000, max_qty=50,
                         journal_dir=tmp_path / "journal2", level_dir=level_dir)
    assert orch2.pipelines["ACME"].levels == persisted     # roundtrip: init loads it back


def _swing(kind, price, minute, tf=Timeframe.M15):
    born = datetime.combine(DAY1, time(10, 0), tzinfo=IST) + timedelta(minutes=minute)
    p = D(str(price))
    return Level(f"X-{kind.name}-{tf.value}-{born.isoformat()}", "X", kind,
                 (p - D("0.05"), p + D("0.05")), born, tf)


def test_m15_trend_from_swing_structure(tmp_path):
    """A9: trend is read from the last 4 confirmed M15 swing levels --
    HH+HL LONG, LH+LL SHORT, anything mixed or thin NEUTRAL."""
    pipe, _ = make_pipeline(tmp_path)
    SH, SL = LevelKind.SWING_H, LevelKind.SWING_L
    cases = [
        ([(SL, 99, 0), (SH, 102, 15), (SL, 100, 30), (SH, 104, 45)], Direction.LONG),
        ([(SH, 104, 0), (SL, 100, 15), (SH, 102, 30), (SL, 98, 45)], Direction.SHORT),
        ([(SL, 99, 0), (SH, 104, 15), (SL, 100, 30), (SH, 102, 45)],
         Direction.NEUTRAL),                                   # HL but LH: mixed
        ([(SL, 99, 0), (SH, 102, 15)], Direction.NEUTRAL),     # <2 highs+lows
        ([], Direction.NEUTRAL)]
    for seq, want in cases:
        pipe.levels[:] = [_swing(k, p, m) for k, p, m in seq]
        assert pipe._m15_trend() is want, seq


def test_m15_trend_windows_last_4_and_ignores_m5(tmp_path):
    pipe, _ = make_pipeline(tmp_path)
    SH, SL = LevelKind.SWING_H, LevelKind.SWING_L
    # unwindowed this reads LH(110>104)+LL => SHORT; the last-4 window keeps
    # one high only => NEUTRAL
    seq = [(SH, 110, 0), (SL, 101, 15), (SL, 100, 30), (SL, 99, 45), (SH, 104, 60)]
    pipe.levels[:] = [_swing(k, p, m) for k, p, m in seq]
    assert pipe._m15_trend() is Direction.NEUTRAL
    long_seq = [(SL, 99, 0), (SH, 102, 15), (SL, 100, 30), (SH, 104, 45)]
    pipe.levels[:] = [_swing(k, p, m, Timeframe.M5) for k, p, m in long_seq]
    assert pipe._m15_trend() is Direction.NEUTRAL          # M5 swings don't count
    pipe.levels[:] = [_swing(k, p, m) for k, p, m in long_seq]
    assert pipe._m15_trend() is Direction.LONG


def test_index_pipeline_runs_own_wyckoff_detect(tmp_path, monkeypatch):
    """A3: the index pipeline's own wyckoff instance gets .detect() so its
    spring/upthrust memory can make phase() reach ACC/DIST."""
    s = cfg()
    spec = s.market_spec()
    pipe = SymbolPipeline("NIFTY", s, CandleStore(tmp_path / "c", spec),
                          Journal(tmp_path / "j"), PaperBroker(s),
                          PositionManager(s, spec), RiskState(s), 1, True)
    seen = []
    monkeypatch.setattr(pipe.wyckoff, "detect", lambda ctx: seen.append(ctx.now) or [])
    t0 = datetime.combine(DAY1, time(10, 0), tzinfo=IST)
    for m in range(6):
        pipe.on_m1(m1("NIFTY", t0 + timedelta(minutes=m), 100, 101, 99, 100))
    assert seen == [t0 + timedelta(minutes=5)]
    assert pipe.index_view is not None


# --------------------------------------------- 2. broker+manager integration

def test_partials_and_eod_exact_accounting(tmp_path):
    """Scripted LONG 50 stop 95, entry limit AT zone CE 100 (half-spread
    only, quantized back to 100.00): 1R (market) and T2-touch (limit AT 110)
    shave 16 each through the broker, EOD squares off the remaining 18;
    realized is the exact Decimal sum including entry + exit costs, and
    RiskState records the close."""
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
    assert pos.entry.price == D("100.00")                          # AT the limit
    assert risk.open_risk == D("5.00") * 50                        # B8 ledger on
    assert risk.open_dirs == {"X": Direction.LONG}
    pipe.on_m1(m1("X", t0 + timedelta(minutes=10), 106, 111, 106, 111))  # 1R seen
    assert pos.remaining_qty == 34 and "1R" in pos.partials
    pipe.on_m1(m1("X", t0 + timedelta(minutes=15), 111, 112, 110, 111))  # T2 touch
    assert pos.remaining_qty == 18 and "2R" in pos.partials
    pipe.on_m1(m1("X", t0.replace(hour=15, minute=10), 111, 111, 110, 111))
    pipe.on_m1(m1("X", t0.replace(hour=15, minute=15), 111, 111, 110, 111))  # EOD
    assert pipe.position is None and pos.remaining_qty == 0
    expected = (-cost_buy(D("100.00"), 50)   # entry BUY leg; T2=110 touched: limit fill AT 110
                + (D("105.95") - D("100.00")) * 16 - cost(D("105.95"), 16)
                + (D("110.00") - D("100.00")) * 16 - cost(D("110.00"), 16)
                + (D("110.95") - D("100.00")) * 18 - cost(D("110.95"), 18))
    assert pos.realized == expected
    assert risk.trades_today == 1 and risk.consecutive_losses == 0
    assert risk.daily_pnl_R == pytest.approx(float(expected / (D("5.00") * 50)))
    assert risk.open_risk == 0 and risk.open_dirs == {}            # B8 released
    kinds = [e["kind"] for e in pipe.journal.read(t0.date())]
    assert "trade_open" in kinds and "trade_close" in kinds


# ------------------------------------------------ 2a2. expiry sizing (B7)

def test_expiry_day_halves_qty_and_journals(tmp_path):
    """Thursday (NSE weekly expiry): effective arm qty is max_qty x
    expiry_size_mult (50 x 0.5 = 25) and skip/verdict journal entries carry
    an expiry flag; a non-expiry day is full size, no flag."""
    thu = date(2026, 7, 16)                              # a Thursday
    pipe, _ = make_pipeline(tmp_path)                    # max_qty 50
    pipe.day = DayState(session_date=thu)
    assert pipe._eff_qty() == 25
    pipe._skip(datetime.combine(thu, time(11, 30), tzinfo=IST), "g", "r")
    [skip] = pipe.journal.read(thu)
    assert skip["expiry"] is True
    pipe.day = DayState(session_date=DAY1)               # Tuesday
    assert pipe._eff_qty() == 50
    pipe._skip(datetime.combine(DAY1, time(11, 30), tzinfo=IST), "g", "r")
    [skip2] = pipe.journal.read(DAY1)
    assert "expiry" not in skip2


# -------------------------------------- 2a2b. RANGE_PIN half-size (fade edges)

def test_range_pin_day_halves_qty_composes_with_expiry(tmp_path):
    """RANGE_PIN discipline lives in SIZE: qty x range_pin_size_mult (0.5),
    composed multiplicatively with the expiry throttle."""
    pipe, _ = make_pipeline(tmp_path)                    # max_qty 50
    pipe.day = DayState(session_date=DAY1, template="RANGE_PIN")   # Tuesday
    assert pipe._eff_qty() == 25
    pipe.day = DayState(session_date=date(2026, 7, 16),  # Thursday expiry
                        template="RANGE_PIN")
    assert pipe._eff_qty() == 12                         # 50 x 0.5 x 0.5


# ------------------------------------------- 2a3. day-after-TREND (B5)

def test_day_after_trend_scales_qty(tmp_path):
    """Day 1 locks TREND; day 2's fresh DayState snapshots it as
    prev_template and effective qty drops to max_qty x 0.75."""
    feed = ScenarioFeed([trend_day("ACME", DAY1, 100.0),
                         trend_day("ACME", DAY2, 100.0)])
    orch = Orchestrator(cfg(), feed, ["ACME"], capital=100000, max_qty=50,
                        journal_dir=tmp_path)
    orch.run()
    pipe = orch.pipelines["ACME"]
    assert pipe.day.session_date == DAY2
    assert pipe.day.prev_template == "TREND"
    assert pipe._eff_qty() == 37                     # 50 x 0.75


def test_arm_receives_throttled_qty(tmp_path, monkeypatch):
    """fsm.arm gets _eff_qty(): Thursday expiry x day-after-TREND compound
    (50 x 0.5 x 0.75 = 18)."""
    pipe, _ = make_pipeline(tmp_path)
    pipe.day = DayState(session_date=date(2026, 7, 16), prev_template="TREND")
    seen = {}
    monkeypatch.setattr(pipe.gates, "check",
                        lambda *a: Verdict(True, "chain", "ok"))

    def arm(top, ctx, max_qty, opps):
        seen["mq"] = max_qty
        return SimpleNamespace(armed=True, reason="")

    monkeypatch.setattr(pipe.fsm, "arm", arm)
    monkeypatch.setattr(pipe.fsm, "step",
                        lambda ctx, ev: SimpleNamespace(action=None, reason=""))
    zone = ScoredZone((D("99"), D("101")), Direction.LONG, [], 5, 50.0, 50.0, {})
    ctx = StockContext("X", datetime(2026, 7, 16, 11, 30, tzinfo=IST), None,
                       [], [], pipe.day)
    pipe._entry_flow(ctx, [zone], ("RANGING", 0.5), [])
    assert seen["mq"] == 18


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


# ------------------------------------------- 2b2. resting limit entries (F1)

def _queue_limit(pipe, t0, direction=Direction.LONG, stop="490"):
    """Arm a scripted resting limit: zone (495,505) => limit CE 500."""
    pipe.day = DayState(session_date=t0.date())
    plan = TradePlan("X", direction, (D("495"), D("505")), D(stop),
                     [D("520") if direction is Direction.LONG else D("480")],
                     10, 70.0, t0, {})
    pipe._pending_plan, pipe._pending_since = plan, t0
    return plan


def test_limit_entry_fills_at_limit_long(tmp_path):
    """LONG: M1s whose lows stay above the 500 limit do NOT fill; the first
    M1 trading through fills AT 500 + half-spread (2bps), never the market
    open -- the chase is gone by construction. R off the limit price."""
    pipe, risk = make_pipeline(tmp_path)
    t0 = datetime(2026, 7, 14, 11, 0, tzinfo=IST)
    pipe.on_m1(m1("X", t0, 500, 500, 500, 500))
    plan = _queue_limit(pipe, t0)
    pipe.on_m1(m1("X", t0 + timedelta(minutes=1), 502, 503, 500.05, 502))
    assert pipe.position is None and pipe._pending_plan is plan  # low > limit
    pipe.on_m1(m1("X", t0 + timedelta(minutes=2), 502, 502, 499.90, 500.50))
    pos = pipe.position
    assert pos is not None and pipe._pending_plan is None
    assert pos.entry.price == D("500.10")    # 500 x (1 + 2bps), no slippage
    assert risk.open_risk == (D("500.10") - D("490")) * 10


def test_limit_entry_fills_at_limit_short(tmp_path):
    """SHORT mirror: fills when an M1 high trades through, AT 500 - 2bps."""
    pipe, _ = make_pipeline(tmp_path)
    t0 = datetime(2026, 7, 14, 11, 0, tzinfo=IST)
    pipe.on_m1(m1("X", t0, 498, 498, 498, 498))
    plan = _queue_limit(pipe, t0, Direction.SHORT, stop="510")
    pipe.on_m1(m1("X", t0 + timedelta(minutes=1), 498, 499.95, 497, 498))
    assert pipe.position is None and pipe._pending_plan is plan  # high < limit
    pipe.on_m1(m1("X", t0 + timedelta(minutes=2), 499, 500.20, 498, 499))
    assert pipe.position is not None
    assert pipe.position.entry.price == D("499.90")   # 500 x (1 - 2bps)


def test_limit_entry_gap_through_fills_at_limit(tmp_path):
    """An M1 gapping clean through the limit (opens beyond it) still fills
    AT the limit -- always-adverse simulation, never a better-than-limit
    price."""
    pipe, _ = make_pipeline(tmp_path)
    t0 = datetime(2026, 7, 14, 11, 0, tzinfo=IST)
    pipe.on_m1(m1("X", t0, 502, 502, 502, 502))
    _queue_limit(pipe, t0)
    pipe.on_m1(m1("X", t0 + timedelta(minutes=1), 498, 499, 497, 498))
    assert pipe.position is not None
    assert pipe.position.entry.price == D("500.10")   # AT limit, not the open


def test_limit_entry_expires_unfilled(tmp_path):
    """A limit never traded through dies after fill_ttl_candles (6 M5 = 30
    M1): journal skip 'unfilled', no position, order cleared."""
    pipe, risk = make_pipeline(tmp_path)
    t0 = datetime(2026, 7, 14, 11, 0, tzinfo=IST)
    pipe.on_m1(m1("X", t0, 510, 510, 510, 510))
    _queue_limit(pipe, t0)
    for m in range(1, 30):                          # lows never reach 500
        pipe.on_m1(m1("X", t0 + timedelta(minutes=m), 510, 511, 505, 510))
    assert pipe._pending_plan is not None           # minute 29: still resting
    pipe.on_m1(m1("X", t0 + timedelta(minutes=30), 499, 511, 499, 510))
    assert pipe.position is None and pipe._pending_plan is None
    assert risk.trades_today == 0
    skips = [e for e in pipe.journal.read(t0.date()) if e["kind"] == "skip"]
    assert any(e["gate"] == "fill" and e["reason"] == "unfilled" for e in skips)


def test_journal_r_denominated_on_fill_risk(tmp_path):
    """Effective R (finding 5): the journaled r divides realized by the
    FILL->stop risk (10.10 off the 500.10 limit fill), never the plan-CE
    risk (10.00). RiskState's open-risk ledger uses the same denominator."""
    pipe, risk = make_pipeline(tmp_path)
    t0 = datetime(2026, 7, 14, 11, 0, tzinfo=IST)
    pipe.on_m1(m1("X", t0, 500, 500, 500, 500))
    _queue_limit(pipe, t0)                            # zone (495,505) stop 490
    pipe.on_m1(m1("X", t0 + timedelta(minutes=1), 500, 501, 499, 500))
    pos = pipe.position
    assert pos.risk_pts == D("10.10")                 # fill 500.10 - stop 490
    assert risk.open_risk == D("10.10") * 10
    pipe._pending_exits = [Action("EXIT_STOP", None, "close_beyond_stop")]
    pipe.on_m1(m1("X", t0 + timedelta(minutes=2), 489, 489, 488, 488))
    assert pipe.position is None and pos.realized < 0
    [close] = [e for e in pipe.journal.read(t0.date())
               if e["kind"] == "trade_close"]
    assert close["r"] == round(float(pos.realized / (D("10.10") * 10)), 3)


def test_pending_limit_blocks_entry_flow(tmp_path, monkeypatch):
    """While a limit rests, the M5 entry flow is paused -- a second arm must
    not clobber the working order."""
    pipe, _ = make_pipeline(tmp_path)
    t0 = datetime(2026, 7, 14, 11, 0, tzinfo=IST)
    pipe.on_m1(m1("X", t0, 510, 510, 510, 510))
    _queue_limit(pipe, t0)
    called = []
    monkeypatch.setattr(pipe, "_entry_flow", lambda *a: called.append(a))
    for m in (1, 5, 10):
        pipe.on_m1(m1("X", t0 + timedelta(minutes=m), 510, 511, 505, 510))
    assert not called and pipe._pending_plan is not None


# ------------------------------------------------------- 2c. feed gaps (A6)

def _spy_closes(monkeypatch):
    closes, orig = [], SymbolPipeline._on_m5_close
    monkeypatch.setattr(SymbolPipeline, "_on_m5_close",
                        lambda self, now, index:
                        closes.append(now) or orig(self, now, index))
    return closes


def test_multi_bucket_gap_closes_each_boundary(tmp_path, monkeypatch):
    """A6: an M1 jumping >1 M5 bucket evaluates every missed boundary in
    order; bar-scoped stages (levels/detectors) still run once per new bar."""
    closes = _spy_closes(monkeypatch)
    pipe, _ = make_pipeline(tmp_path)
    bars = []
    monkeypatch.setattr(pipe.level_engine, "update",
                        lambda levels, c5, atr: bars.append(c5.ts) or [])
    t0 = datetime.combine(DAY1, time(10, 0), tzinfo=IST)
    for m in range(5):
        pipe.on_m1(m1("X", t0 + timedelta(minutes=m), 100, 101, 99, 100))
    pipe.on_m1(m1("X", t0 + timedelta(minutes=17), 100, 101, 99, 100))   # gap
    assert closes == [t0 + timedelta(minutes=m) for m in (5, 10, 15)]
    assert bars == [t0]                    # one new closed M5, evaluated once


def test_open_position_force_closed_same_day_on_overnight_gap(tmp_path):
    """An open position whose next real M1 is NEXT DAY must be force-closed at
    the last SAME-DAY price, never filled against the new day's opening candle
    (the gap loop queues an EOD/stop exit, but it must not price off a
    different-date candle). Upholds the 'no overnight' guarantee."""
    pipe, risk = make_pipeline(tmp_path)
    t0 = datetime(2026, 7, 14, 14, 0, tzinfo=IST)      # before the 14:30 cutoff
    pipe.on_m1(m1("X", t0, 100, 100, 100, 100))        # warm-up: sets DAY1
    plan = TradePlan("X", Direction.LONG, (D("99"), D("101")), D("95"),
                     [D("107"), D("110"), D("115")], 10, 70.0, t0,
                     {"final": 70.0, "mults": {"align": 1.0}})
    pipe._pending_plan = plan                          # scripted resting limit
    pipe.on_m1(m1("X", t0 + timedelta(minutes=5), 100, 104, 100, 104))  # fill @~100
    pos = pipe.position
    assert pos is not None and pos.entry.price >= D("100")
    assert risk.open_risk > 0
    # next real M1 is NEXT DAY, gapping far down (overnight crash to 80): the
    # gap loop clamps to DAY1's close and queues EOD exits, then _end_session
    # force-closes at DAY1's last price BEFORE this candle can fill anything
    pipe.on_m1(m1("X", datetime(2026, 7, 15, 9, 15, tzinfo=IST), 80, 80, 80, 80))
    assert pipe.position is None and pipe._pending_exits == []   # closed + flushed
    [close] = [e for e in pipe.journal.read(DAY1) if e["kind"] == "trade_close"]
    assert close["reason"] == ExitReason.EOD.value
    assert close["at"][:10] == "2026-07-14"                      # SAME-day squareoff
    assert D(close["exit_price"]) > D("103")   # ~104 (last DAY1 price), NOT the 80 gap
    assert risk.open_risk == 0                                   # ledger released


def test_overnight_gap_stops_at_session_close(tmp_path, monkeypatch):
    """Overnight jumps close out the old session only -- no phantom
    boundary evaluations through the night."""
    closes = _spy_closes(monkeypatch)
    pipe, _ = make_pipeline(tmp_path)
    pipe.on_m1(m1("X", datetime(2026, 7, 14, 15, 25, tzinfo=IST), 100, 100, 100, 100))
    pipe.on_m1(m1("X", datetime(2026, 7, 15, 9, 15, tzinfo=IST), 100, 100, 100, 100))
    assert closes == [datetime(2026, 7, 14, 15, 30, tzinfo=IST)]


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
    # real content flows through: the trend day reads MARKUP at full strength
    # (trend stays NEUTRAL -- a monotonic mock day confirms no M15 swings,
    # and A9's m15_trend only speaks from real M15 swing structure)
    assert any(v.phase == "MARKUP" and v.strength >= 0.5 for v in views)
