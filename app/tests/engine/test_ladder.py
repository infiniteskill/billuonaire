"""Ladder gate (research runs/long60/FACTS.md): rung computation, H1-zone
tracker (FVG + simplified-Lux OB birth/death/age), M5 EQ-pool sweep tracker
(fractal 5/5, 0.25xATR pools, wick-beyond-close-back), and the pipeline gate
(skip journaling, rung stamp on emitted plans, disabled = passthrough)."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from trader.config import LadderCfg
from trader.engine.confluence import ScoredZone
from trader.engine.context import DayState, StockContext
from trader.engine.gates import RiskState, Verdict
from trader.engine.ladder import H1Zone, Ladder
from trader.engine.pipeline import Orchestrator, SymbolPipeline
from trader.execution.manager import PositionManager
from trader.execution.paper import PaperBroker
from trader.feed.mock import ScenarioFeed, judas_reversal
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction
from trader.models.level import Level, LevelKind, LevelState
from trader.store.candles import CandleStore
from trader.store.journal import Journal

IST = ZoneInfo("Asia/Kolkata")
D = Decimal
DAY1, DAY2 = date(2026, 7, 14), date(2026, 7, 15)
M5 = timedelta(minutes=5)


def at(day, hh, mm):
    return datetime.combine(day, time(hh, mm), tzinfo=IST)


def c(ts, o, h, lo, cl, tf=Timeframe.M5):
    return Candle("X", tf, ts, D(str(o)), D(str(h)), D(str(lo)), D(str(cl)), 1000)


def h1bar(i, o, h, lo, cl):
    return c(at(DAY1, 9, 15) + timedelta(hours=i), o, h, lo, cl, Timeframe.H1)


def m5bar(i, o, h, lo, cl):
    return c(at(DAY1, 9, 15) + i * M5, o, h, lo, cl)


def flat(i):
    return m5bar(i, 100, 100.5, 99.5, 100)


class View:
    def __init__(self, m5=(), h1=()):
        self.series = {Timeframe.M5: list(m5), Timeframe.H1: list(h1)}

    def last(self, n, tf):
        return self.series[tf][-n:]


def ctx_for(view, session=DAY1):
    return SimpleNamespace(candles=view, day=DayState(session_date=session))


# ------------------------------------------------------- H1 zone tracker

def test_h1_fvg_bull_birth_then_far_edge_death():
    lad = Ladder()
    bars = [h1bar(0, 99, 100, 98, 99), h1bar(1, 100, 104, 99, 104),
            h1bar(2, 104, 106, 103, 105)]          # c3.low 103 > c1.high 100
    lad.update(ctx_for(View(h1=bars)))
    [z] = lad.h1_zones
    assert (z.lo, z.hi, z.bull, z.born) == (D("100"), D("103"), True, bars[2].ts)
    bars.append(h1bar(3, 103, 103.5, 101, 102))    # close inside: zone lives
    lad.update(ctx_for(View(h1=bars)))
    assert len(lad.h1_zones) == 1                  # and cursor: no duplicate birth
    bars.append(h1bar(4, 102, 103.5, 99, 99.5))    # close < lo: far edge crossed
    lad.update(ctx_for(View(h1=bars)))
    assert lad.h1_zones == []


def test_h1_fvg_bear_birth():
    bars = [h1bar(0, 101, 102, 100, 101), h1bar(1, 100, 101, 96, 96),
            h1bar(2, 96, 97, 94, 95)]              # c3.high 97 < c1.low 100
    lad = Ladder()
    lad.update(ctx_for(View(h1=bars)))
    [z] = lad.h1_zones
    assert (z.lo, z.hi, z.bull) == (D("97"), D("100"), False)


def test_h1_ob_simplified_lux_birth():
    """Pivot high 110 confirmed after 5 lower bars; close 112 breaking back
    over it anchors the bull OB at the leg's lowest-low bar (94..101)."""
    bars = [h1bar(0, 105, 110, 100, 105),
            h1bar(1, 104, 105, 98, 100), h1bar(2, 100, 105, 96, 100),
            h1bar(3, 100, 101, 94, 100), h1bar(4, 100, 105, 95, 100),
            h1bar(5, 100, 105, 96, 100), h1bar(6, 105, 115, 104, 112)]
    lad = Ladder()
    lad.update(ctx_for(View(h1=bars)))
    [z] = lad.h1_zones
    assert (z.lo, z.hi, z.bull, z.born) == (D("94"), D("101"), True, bars[3].ts)


def test_h1_zone_age_cap_five_sessions():
    lad = Ladder()
    lad.h1_zones = [H1Zone(D("94"), D("101"), True, at(DAY1, 12, 15))]
    lad.update(ctx_for(View(), session=date(2026, 7, 20)))   # 4 sessions: lives
    assert lad.h1_zones
    lad.update(ctx_for(View(), session=date(2026, 7, 21)))   # 5 sessions: pruned
    assert lad.h1_zones == []


# ------------------------------------------------- M5 EQ-pool sweep tracker

def test_eq_pool_sweep_detected_and_consumed():
    lad = Ladder()
    bars = [flat(i) for i in range(18)]
    bars[5] = m5bar(5, 100, 105, 99.5, 100)        # fractal swing high 105
    bars[11] = m5bar(11, 100, 105.2, 99.5, 100)    # eq swing high 105.2
    bars[17] = m5bar(17, 100, 105.5, 99.5, 100)    # wick 105.5 > 105.2, close back
    lad.update(ctx_for(View(m5=bars)))
    assert lad.sweeps == [(bars[17].ts, True)]
    assert lad.swing_hi == []                      # pool consumed by the sweep


def test_single_swing_is_no_pool():
    lad = Ladder()
    bars = [flat(i) for i in range(13)]
    bars[5] = m5bar(5, 100, 105, 99.5, 100)
    bars[12] = m5bar(12, 100, 105.4, 99.5, 100)    # wick beyond the lone swing
    lad.update(ctx_for(View(m5=bars)))
    assert lad.sweeps == [] and lad.swing_hi == [D("105")]


def test_close_beyond_pool_breaks_not_sweeps():
    lad = Ladder()
    bars = [flat(i) for i in range(18)]
    bars[5] = m5bar(5, 100, 105, 99.5, 100)
    bars[11] = m5bar(11, 100, 105.2, 99.5, 100)
    bars[17] = m5bar(17, 100, 106.5, 99.5, 106)    # CLOSES beyond: break, no sweep
    lad.update(ctx_for(View(m5=bars)))
    assert lad.sweeps == [] and lad.swing_hi == []


def test_eq_pool_lows_sweep():
    lad = Ladder()
    bars = [flat(i) for i in range(18)]
    bars[5] = m5bar(5, 100, 100.5, 95, 100)
    bars[11] = m5bar(11, 100, 100.5, 94.8, 100)
    bars[17] = m5bar(17, 100, 100.5, 94.5, 100)    # wick under 94.8, close back
    lad.update(ctx_for(View(m5=bars)))
    assert lad.sweeps == [(bars[17].ts, False)]
    assert lad.swing_lo == []


# ------------------------------------------------------- rung computation

def zone_lv(kind=LevelKind.OB_BULL, lo="99", hi="101", born=None, hist=()):
    lv = Level(id="z", symbol="X", kind=kind, zone=(D(lo), D(hi)),
               born=born or at(DAY1, 11, 0), tf=Timeframe.M5)
    lv.state_history = list(hist)
    return lv


def grade(lad, lv, direction=Direction.LONG, cluster=(D("99"), D("101")),
          now=None):
    ctx = SimpleNamespace(candles=None, now=now or at(DAY2, 11, 30),
                          day=DayState(session_date=DAY2), levels=[lv])
    return lad.grade(ctx, direction, cluster)


def test_rung1_prior_session_first_touch():
    assert grade(Ladder(), zone_lv()) == 1


def test_rung0_same_session_birth():
    assert grade(Ladder(), zone_lv(born=at(DAY2, 10, 0))) == 0


def test_rung0_already_retested():
    lv = zone_lv(hist=[(at(DAY2, 10, 0), LevelState.TESTED)])   # earlier bar
    assert grade(Ladder(), lv) == 0


def test_rung1_transition_on_firing_bar_still_first_touch():
    lv = zone_lv(hist=[(at(DAY2, 11, 30), LevelState.TESTED)])  # this bar
    assert grade(Ladder(), lv, now=at(DAY2, 11, 30)) == 1


def test_rung0_terminal_zone_or_no_zone():
    lv = zone_lv()
    lv.state = LevelState.MITIGATED
    assert grade(Ladder(), lv) == 0
    assert grade(Ladder(), zone_lv(lo="90", hi="95")) == 0      # cluster disjoint
    assert grade(Ladder(), zone_lv(), direction=Direction.SHORT) == 0  # wrong dir


def test_rung2_h1_nested_same_direction_only():
    lad = Ladder()
    lad.h1_zones = [H1Zone(D("98"), D("100"), True, at(DAY1, 10, 15))]
    assert grade(lad, zone_lv()) == 2
    lad.h1_zones = [H1Zone(D("98"), D("100"), False, at(DAY1, 10, 15))]
    assert grade(lad, zone_lv()) == 1                           # opposite dir
    lad.h1_zones = [H1Zone(D("90"), D("95"), True, at(DAY1, 10, 15))]
    assert grade(lad, zone_lv()) == 1                           # no overlap


def test_rung3_sweep_aligned_within_three_bars():
    lad = Ladder()
    lad.h1_zones = [H1Zone(D("98"), D("100"), True, at(DAY1, 10, 15))]
    born = at(DAY1, 11, 0)
    lad.sweeps = [(born - 2 * M5, False)]           # lows sweep -> bull zone
    assert grade(lad, zone_lv(born=born)) == 3
    lad.sweeps = [(born - 4 * M5, False)]           # too early
    assert grade(lad, zone_lv(born=born)) == 2
    lad.sweeps = [(born - 2 * M5, True)]            # misaligned (highs -> bear)
    assert grade(lad, zone_lv(born=born)) == 2
    lad.sweeps = [(born + M5, False)]               # sweep AFTER birth
    assert grade(lad, zone_lv(born=born)) == 2
    lad.sweeps = [(born, False)]                    # sweep bar births the zone
    assert grade(lad, zone_lv(born=born)) == 3


def test_bear_zone_short_direction_mirrors():
    lad = Ladder()
    lad.h1_zones = [H1Zone(D("100"), D("102"), False, at(DAY1, 10, 15))]
    lv = zone_lv(kind=LevelKind.FVG_BEAR)
    lad.sweeps = [(lv.born - M5, True)]             # highs sweep -> bear zone
    assert grade(lad, lv, direction=Direction.SHORT) == 3


# ------------------------------------------------------- pipeline gate

def cfg(min_rung=3, enabled=True, min_grade=0):
    from tests.harness import ALL_IMPLEMENTED, scenario_settings
    s = scenario_settings(ALL_IMPLEMENTED)
    return s.model_copy(
        update={"ladder": LadderCfg(enabled=enabled, min_rung=min_rung,
                                    min_grade=min_grade)},
        deep=True)


def make_pipe(tmp_path, s):
    spec = s.market_spec()
    return SymbolPipeline("X", s, CandleStore(tmp_path / "candles", spec),
                          Journal(tmp_path / "journal"), PaperBroker(s),
                          PositionManager(s, spec), RiskState(s), 50)


def entry_flow(pipe, monkeypatch, lv, arm_result=None):
    """Run _entry_flow with gates passing on a rung-1 (or given) zone level."""
    monkeypatch.setattr(pipe.gates, "check",
                        lambda *a: Verdict(True, "chain", "ok"))
    armed = []

    def arm(top, ctx, max_qty, opps):
        armed.append(top)
        return arm_result or SimpleNamespace(armed=True,
                                             plan=SimpleNamespace(meta={}))
    monkeypatch.setattr(pipe.fsm, "arm", arm)
    monkeypatch.setattr(pipe.fsm, "step",
                        lambda ctx, ev: SimpleNamespace(action=None, reason=""))
    pipe.day = DayState(session_date=DAY2)
    zone = ScoredZone((D("99"), D("101")), Direction.LONG, [], 5, 90.0, 90.0, {})
    ctx = StockContext("X", at(DAY2, 11, 30), None, [lv] if lv else [], [],
                       pipe.day)
    pipe._entry_flow(ctx, [zone], ("RANGING", 0.5), [])
    return armed


def test_gate_skips_below_min_rung_with_reason(tmp_path, monkeypatch):
    pipe = make_pipe(tmp_path, cfg(min_rung=3))
    armed = entry_flow(pipe, monkeypatch, zone_lv())            # rung 1 < 3
    assert not armed
    [skip] = [e for e in pipe.journal.read(DAY2) if e["kind"] == "skip"]
    assert skip["gate"] == "ladder" and skip["reason"] == "ladder_rung_1"


def test_gate_passes_at_min_rung_and_stamps_plan(tmp_path, monkeypatch):
    pipe = make_pipe(tmp_path, cfg(min_rung=1))
    plan = SimpleNamespace(meta={})
    armed = entry_flow(pipe, monkeypatch, zone_lv(),
                       arm_result=SimpleNamespace(armed=True, plan=plan))
    assert armed and plan.meta["ladder_rung"] == 1
    assert not [e for e in pipe.journal.read(DAY2) if e["kind"] == "skip"]


def test_disabled_is_passthrough(tmp_path, monkeypatch):
    pipe = make_pipe(tmp_path, cfg(enabled=False))
    assert pipe.ladder is None
    plan = SimpleNamespace(meta={})
    armed = entry_flow(pipe, monkeypatch, None,                 # rung would be 0
                       arm_result=SimpleNamespace(armed=True, plan=plan))
    assert armed and "ladder_rung" not in plan.meta             # no gate, no stamp
    assert "grade" not in plan.meta and "minor_ch_recent" not in plan.meta
    assert not [e for e in pipe.journal.read(DAY2) if e["kind"] == "skip"]


def test_min_rung3_blocks_judas_day_all_rung0(tmp_path):
    """Single-day run: every zone is same-session born, so the canonical judas
    trade is eliminated as ladder_rung_0 -- watch/replay emit nothing."""
    feed = ScenarioFeed([judas_reversal("ACME", DAY1, 100.0)])
    orch = Orchestrator(cfg(min_rung=3), feed, ["ACME"], capital=100000,
                        max_qty=50, journal_dir=tmp_path)
    assert orch.run()["trades"] == 0
    skips = [e for e in orch.journal.read(DAY1)
             if e["kind"] == "skip" and e["gate"] == "ladder"]
    assert skips and all(e["reason"] == "ladder_rung_0" for e in skips)


def test_min_rung0_emits_with_rung_stamp(tmp_path):
    feed = ScenarioFeed([judas_reversal("ACME", DAY1, 100.0)])
    orch = Orchestrator(cfg(min_rung=0), feed, ["ACME"], capital=100000,
                        max_qty=50, journal_dir=tmp_path)
    assert orch.run()["trades"] == 1                # canonical judas trade back
    [opened] = [e for e in orch.journal.read(DAY1) if e["kind"] == "trade_open"]
    assert opened["plan"]["ladder_rung"] == 0
    # min_grade 0 default: grade + components + tags journaled, never gated
    parts = opened["plan"]["grade_parts"]
    assert opened["plan"]["grade"] in range(4)
    assert set(parts) == {"nst", "parent_ok", "depth_alive", "pivot_dist"}
    assert {"minor_ch_recent", "po3_h1", "po3_d1"} <= opened["plan"].keys()


# --------------------------------------------------- grade gate (ladder v2)

def test_min_grade_gate_skips_with_grade_reason(tmp_path, monkeypatch):
    pipe = make_pipe(tmp_path, cfg(min_rung=0, min_grade=3))
    armed = entry_flow(pipe, monkeypatch, zone_lv())   # nst 1 -> g 2
    assert not armed
    [skip] = [e for e in pipe.journal.read(DAY2) if e["kind"] == "skip"]
    assert skip["gate"] == "ladder" and skip["reason"] == "grade_2"


def test_min_grade_passes_at_threshold_and_stamps(tmp_path, monkeypatch):
    pipe = make_pipe(tmp_path, cfg(min_rung=0, min_grade=2))
    plan = SimpleNamespace(meta={})
    armed = entry_flow(pipe, monkeypatch, zone_lv(),
                       arm_result=SimpleNamespace(armed=True, plan=plan))
    assert armed and plan.meta["grade"] == 2
    assert plan.meta["grade_parts"] == {"nst": 1, "parent_ok": True,
                                        "depth_alive": True, "pivot_dist": None}
    assert not [e for e in pipe.journal.read(DAY2) if e["kind"] == "skip"]


def test_rung_gate_precedes_grade_gate(tmp_path, monkeypatch):
    pipe = make_pipe(tmp_path, cfg(min_rung=3, min_grade=3))
    entry_flow(pipe, monkeypatch, zone_lv())           # fails both: rung first
    [skip] = [e for e in pipe.journal.read(DAY2) if e["kind"] == "skip"]
    assert skip["reason"] == "ladder_rung_1"


def test_disabled_run_journal_free_of_grading(tmp_path):
    feed = ScenarioFeed([judas_reversal("ACME", DAY1, 100.0)])
    orch = Orchestrator(cfg(enabled=False), feed, ["ACME"], capital=100000,
                        max_qty=50, journal_dir=tmp_path)
    assert orch.run()["trades"] == 1                   # pre-ladder behavior
    raw = (tmp_path / f"{DAY1.isoformat()}.jsonl").read_text()
    assert "grade" not in raw and "minor_ch_recent" not in raw
