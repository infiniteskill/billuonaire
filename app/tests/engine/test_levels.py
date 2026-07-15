"""Tests for the level state machine (LevelEngine) and LevelStore.

Candle sequences are hand-built to drive every transition path from the
task-2 brief. Conventions used throughout (documented in trader/engine/levels.py):

- "high-kind" level (PDH, EQH, OB_BEAR, ...): price origin side is BELOW the
  zone; near edge = zone_lo, far edge = zone_hi.
- SWEPT = wick beyond far edge AND close fully back on origin side of near edge.
- Close inside the zone triggers nothing.
- 2-candle DEAD confirm via engine-internal PENDING_BREAK (not a LevelState).
- Reclaim window = 3 closed candles after the sweep; expiry leaves SWEPT terminal.
"""

import dataclasses
import json
from datetime import datetime, timedelta
from decimal import Decimal as D
from zoneinfo import ZoneInfo

import pytest

from trader.engine.levels import LevelEngine, LevelStore, LevelTransition, level_side
from trader.models.candle import Candle, Timeframe
from trader.models.level import Level, LevelKind, LevelState

T0 = datetime(2026, 7, 15, 9, 15, tzinfo=ZoneInfo("Asia/Kolkata"))


def mk(o, h, l, c, i=0, symbol="TEST"):
    return Candle(
        symbol=symbol, tf=Timeframe.M5, ts=T0 + timedelta(minutes=5 * i),
        open=D(str(o)), high=D(str(h)), low=D(str(l)), close=D(str(c)), volume=100,
    )


def mk_level(kind=LevelKind.PDH, lo="100", hi="101", lid="L1", symbol="TEST", **kw):
    return Level(id=lid, symbol=symbol, kind=kind, zone=(D(lo), D(hi)),
                 born=T0, tf=None, **kw)


def run(engine, level, candles, atr=None):
    out = []
    for c in candles:
        out.extend(engine.update([level], c, atr))
    return out


@pytest.fixture
def engine():
    return LevelEngine({})


# ---------------------------------------------------------------- side table

class TestLevelSide:
    def test_high_kinds_sit_below(self):
        for kind in (LevelKind.PDH, LevelKind.PWH, LevelKind.EQH, LevelKind.SWING_H,
                     LevelKind.OPEN_RANGE_H, LevelKind.OI_WALL_CE, LevelKind.OB_BEAR,
                     LevelKind.FVG_BEAR):
            assert level_side(mk_level(kind=kind), None) == "below", kind

    def test_low_kinds_sit_above(self):
        for kind in (LevelKind.PDL, LevelKind.PWL, LevelKind.EQL, LevelKind.SWING_L,
                     LevelKind.OPEN_RANGE_L, LevelKind.OI_WALL_PE, LevelKind.OB_BULL,
                     LevelKind.FVG_BULL):
            assert level_side(mk_level(kind=kind), None) == "above", kind

    def test_round_uses_reference_close(self):
        lvl = mk_level(kind=LevelKind.ROUND)
        assert level_side(lvl, D("99")) == "below"
        assert level_side(lvl, D("102")) == "above"
        # inside the zone: nearest half by midpoint
        assert level_side(lvl, D("100.2")) == "below"
        assert level_side(lvl, D("100.9")) == "above"


# ------------------------------------------------------------- ACTIVE→TESTED

class TestTested:
    def test_touch_close_on_origin_side(self, engine):
        lvl = mk_level()  # PDH zone 100-101, price below
        out = engine.update([lvl], mk(99, 100.5, 98.5, 99.5), None)
        assert len(out) == 1
        t = out[0]
        assert (t.level_id, t.old, t.new) == ("L1", LevelState.ACTIVE, LevelState.TESTED)
        assert t.ts == T0
        assert lvl.state is LevelState.TESTED
        assert lvl.touches == 1
        assert lvl.state_history == [(T0, LevelState.TESTED)]

    def test_touch_within_atr_tolerance(self, engine):
        lvl = mk_level()
        # high 99.95 is 0.05 below zone_lo; tol = 0.1 * atr(1) = 0.1 -> touch
        out = engine.update([lvl], mk(99, 99.95, 98.5, 99.5), D("1"))
        assert [t.new for t in out] == [LevelState.TESTED]

    def test_near_miss_without_atr_is_not_touch(self, engine):
        lvl = mk_level()
        out = engine.update([lvl], mk(99, 99.95, 98.5, 99.5), None)
        assert out == []
        assert lvl.state is LevelState.ACTIVE and lvl.touches == 0

    def test_close_inside_zone_triggers_nothing(self, engine):
        lvl = mk_level()
        out = engine.update([lvl], mk(99, 100.8, 98.5, 100.5), None)
        assert out == []
        assert lvl.state is LevelState.ACTIVE and lvl.touches == 0

    def test_second_touch_non_ob_increments_touches_no_transition(self, engine):
        lvl = mk_level()
        out = run(engine, lvl, [mk(99, 100.5, 98.5, 99.5, 0),
                                mk(99.5, 100.4, 99, 99.6, 1)])
        assert [t.new for t in out] == [LevelState.TESTED]
        assert lvl.touches == 2
        assert lvl.state is LevelState.TESTED

    def test_low_kind_mirror(self, engine):
        lvl = mk_level(kind=LevelKind.PDL)  # price above zone 100-101
        out = engine.update([lvl], mk(102, 103, 100.5, 101.5), None)
        assert [t.new for t in out] == [LevelState.TESTED]


# -------------------------------------------------------------------- SWEPT

class TestSwept:
    def test_active_to_swept_wick_through_close_back(self, engine):
        lvl = mk_level()
        out = engine.update([lvl], mk(99.5, 101.5, 99, 99.5), None)
        assert len(out) == 1  # precedence: SWEPT wins, no extra TESTED
        assert (out[0].old, out[0].new) == (LevelState.ACTIVE, LevelState.SWEPT)
        assert lvl.state is LevelState.SWEPT

    def test_tested_to_swept(self, engine):
        lvl = mk_level()
        out = run(engine, lvl, [mk(99, 100.5, 98.5, 99.5, 0),      # TESTED
                                mk(99.5, 101.5, 99, 99.5, 1)])     # SWEPT
        assert [t.new for t in out] == [LevelState.TESTED, LevelState.SWEPT]

    def test_low_kind_sweep(self, engine):
        lvl = mk_level(kind=LevelKind.PDL)  # price above; far edge = zone_lo
        out = engine.update([lvl], mk(101.5, 102, 99.5, 101.5), None)
        assert [t.new for t in out] == [LevelState.SWEPT]

    def test_wick_through_but_close_inside_zone_is_not_swept(self, engine):
        lvl = mk_level()
        out = engine.update([lvl], mk(99.5, 101.5, 99, 100.5), None)
        assert out == []
        assert lvl.state is LevelState.ACTIVE


# --------------------------------------------------------- SWEPT→RECLAIMED

class TestReclaim:
    def sweep(self, engine, lvl):
        out = engine.update([lvl], mk(99.5, 101.5, 99, 99.5, 0), None)
        assert [t.new for t in out] == [LevelState.SWEPT]

    def test_reclaimed_within_window(self, engine):
        lvl = mk_level()
        self.sweep(engine, lvl)
        out = engine.update([lvl], mk(99.5, 99.9, 99, 99.4, 1), None)
        assert [t.new for t in out] == [LevelState.RECLAIMED]
        assert lvl.state is LevelState.RECLAIMED

    def test_reclaimed_on_third_candle(self, engine):
        lvl = mk_level()
        self.sweep(engine, lvl)
        inside = [mk(100.2, 100.8, 100, 100.5, i) for i in (1, 2)]
        out = run(engine, lvl, inside)
        assert out == []
        out = engine.update([lvl], mk(100.2, 100.3, 99, 99.5, 3), None)
        assert [t.new for t in out] == [LevelState.RECLAIMED]

    def test_window_expiry_leaves_swept_terminal(self, engine):
        lvl = mk_level()
        self.sweep(engine, lvl)
        inside = [mk(100.2, 100.8, 100, 100.5, i) for i in (1, 2, 3)]
        assert run(engine, lvl, inside) == []
        # 4th candle after sweep closes back on origin side -> too late
        out = engine.update([lvl], mk(100.2, 100.3, 99, 99.5, 4), None)
        assert out == []
        assert lvl.state is LevelState.SWEPT


# ------------------------------------------------------ 2-candle DEAD confirm

class TestDead:
    def test_two_closes_beyond_far_edge_kill_level(self, engine):
        lvl = mk_level()
        out = engine.update([lvl], mk(100.5, 101.6, 100, 101.5, 0), None)
        assert out == []                       # PENDING_BREAK is engine-internal
        assert lvl.state is LevelState.ACTIVE  # not a LevelState
        out = engine.update([lvl], mk(101.5, 102.2, 101.2, 102, 1), None)
        assert len(out) == 1
        assert (out[0].old, out[0].new) == (LevelState.ACTIVE, LevelState.DEAD)
        assert out[0].ts == T0 + timedelta(minutes=5)  # confirming candle's ts
        assert lvl.state is LevelState.DEAD

    def test_break_then_reclaim_goes_swept_then_reclaimed(self, engine):
        lvl = mk_level()
        out = run(engine, lvl, [
            mk(100.5, 101.6, 100, 101.5, 0),   # close beyond -> pending
            mk(101.5, 101.6, 99.2, 99.5, 1),   # close back on origin -> SWEPT
            mk(99.5, 99.9, 99, 99.4, 2),       # holds origin side -> RECLAIMED
        ])
        assert [t.new for t in out] == [LevelState.SWEPT, LevelState.RECLAIMED]

    def test_pending_break_fizzles_on_close_inside_zone(self, engine):
        lvl = mk_level()
        out = run(engine, lvl, [
            mk(100.5, 101.6, 100, 101.5, 0),   # pending
            mk(101.5, 101.6, 100.2, 100.5, 1), # close inside zone: cancelled
        ])
        assert out == []
        assert lvl.state is LevelState.ACTIVE
        # level is still alive: a later touch tests it
        out = engine.update([lvl], mk(100.4, 100.5, 99, 99.5, 2), None)
        assert [t.new for t in out] == [LevelState.TESTED]

    def test_dead_level_is_never_processed_again(self, engine):
        lvl = mk_level(state=LevelState.DEAD)
        out = engine.update([lvl], mk(99, 100.5, 98.5, 99.5), None)
        assert out == []


# ------------------------------------------------------ RECLAIMED→INVERTED

class TestInverted:
    def reclaim(self, engine, lvl):
        out = run(engine, lvl, [mk(99.5, 101.5, 99, 99.5, 0),   # SWEPT
                                mk(99.5, 99.9, 99, 99.4, 1)])   # RECLAIMED
        assert [t.new for t in out] == [LevelState.SWEPT, LevelState.RECLAIMED]

    def test_close_through_held_one_candle_inverts(self, engine):
        lvl = mk_level()
        self.reclaim(engine, lvl)
        out = engine.update([lvl], mk(100.5, 101.6, 100, 101.5, 2), None)
        assert out == []                       # first close beyond: pending hold
        out = engine.update([lvl], mk(101.5, 102, 101.2, 101.8, 3), None)
        assert len(out) == 1
        assert (out[0].old, out[0].new) == (LevelState.RECLAIMED, LevelState.INVERTED)
        assert lvl.state is LevelState.INVERTED

    def test_failed_hold_stays_reclaimed(self, engine):
        lvl = mk_level()
        self.reclaim(engine, lvl)
        out = run(engine, lvl, [
            mk(100.5, 101.6, 100, 101.5, 2),   # close beyond: pending hold
            mk(101.5, 101.6, 99.2, 99.5, 3),   # falls back: hold failed
        ])
        assert out == []
        assert lvl.state is LevelState.RECLAIMED
        # a later successful attempt still inverts
        out = run(engine, lvl, [
            mk(100.5, 101.6, 100, 101.5, 4),
            mk(101.5, 102, 101.2, 101.8, 5),
        ])
        assert [t.new for t in out] == [LevelState.INVERTED]


# ------------------------------------------------------- OB mitigation

class TestMitigated:
    @pytest.mark.parametrize("kind,candles", [
        # OB_BEAR zone 100-101, price below
        (LevelKind.OB_BEAR, [mk(99, 100.5, 98.5, 99.5, 0),
                             mk(99.5, 100.4, 99, 99.6, 1)]),
        # OB_BULL zone 100-101, price above
        (LevelKind.OB_BULL, [mk(102, 103, 100.5, 101.5, 0),
                             mk(101.5, 102.5, 100.6, 101.4, 1)]),
    ])
    def test_second_test_mitigates_ob(self, engine, kind, candles):
        lvl = mk_level(kind=kind)
        out = run(engine, lvl, candles)
        assert [t.new for t in out] == [LevelState.TESTED, LevelState.MITIGATED]
        assert lvl.touches == 2
        assert lvl.state is LevelState.MITIGATED
        # mitigated levels are done: further touches do nothing
        assert engine.update([lvl], candles[0], None) == []
        assert lvl.touches == 2


# ----------------------------------------------------------- ROUND levels

class TestRound:
    def test_side_below_from_first_candle_open(self, engine):
        lvl = mk_level(kind=LevelKind.ROUND)
        out = engine.update([lvl], mk(99, 101.5, 98.5, 99.5), None)
        assert [t.new for t in out] == [LevelState.SWEPT]

    def test_side_above_from_prev_close(self, engine):
        lvl = mk_level(kind=LevelKind.ROUND, lid="R1")
        # candle 0 establishes prev_close=102 without touching the level
        assert engine.update([lvl], mk(102, 102.5, 101.8, 102, 0), None) == []
        # candle 1: wick below zone_lo, close back above zone_hi -> SWEPT
        out = engine.update([lvl], mk(102, 102.2, 99.5, 101.5, 1), None)
        assert [t.new for t in out] == [LevelState.SWEPT]

    def test_side_is_cached_per_level(self, engine):
        lvl = mk_level(kind=LevelKind.ROUND)
        engine.update([lvl], mk(99, 99.5, 98.5, 99, 0), None)   # side fixed: below
        # even though price now sits above, sweep semantics stay side=below
        out = engine.update([lvl], mk(99, 102, 98.9, 99.5, 1), None)
        assert [t.new for t in out] == [LevelState.SWEPT]


# ---------------------------------------------------- engine housekeeping

class TestEngineMisc:
    def test_other_symbol_levels_ignored(self, engine):
        lvl = mk_level(symbol="OTHER")
        assert engine.update([lvl], mk(99, 100.5, 98.5, 99.5), None) == []
        assert lvl.touches == 0

    def test_multiple_levels_one_candle(self, engine):
        a = mk_level(lid="A", lo="100", hi="101")
        b = mk_level(lid="B", lo="99.9", hi="100.5")
        out = engine.update([a, b], mk(99, 100.5, 98.5, 99.5), None)
        assert {t.level_id for t in out} == {"A", "B"}
        assert all(t.new is LevelState.TESTED for t in out)

    def test_at_most_one_transition_per_level_per_candle(self, engine):
        lvl = mk_level()
        # sweep candle also satisfies the touch rule; only SWEPT is emitted
        out = engine.update([lvl], mk(99.5, 101.5, 99, 99.5), None)
        assert len(out) == 1

    def test_transition_is_frozen(self):
        t = LevelTransition(level_id="x", old=LevelState.ACTIVE,
                            new=LevelState.TESTED, ts=T0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            t.level_id = "y"


# -------------------------------------------------------------- LevelStore

class TestLevelStore:
    def make_levels(self):
        a = Level(id="A", symbol="NIFTY", kind=LevelKind.PDH,
                  zone=(D("22150.05"), D("22160.10")), born=T0, tf=None)
        b = Level(id="B", symbol="NIFTY", kind=LevelKind.OB_BULL,
                  zone=(D("22000"), D("22020.55")), born=T0, tf=Timeframe.M15,
                  state=LevelState.SWEPT, touches=3,
                  state_history=[(T0, LevelState.TESTED),
                                 (T0 + timedelta(minutes=5), LevelState.SWEPT)])
        return [a, b]

    def test_roundtrip_reconstructs_exactly(self, tmp_path):
        store = LevelStore(tmp_path)
        levels = self.make_levels()
        store.save("NIFTY", levels)
        loaded = LevelStore(tmp_path).load("NIFTY")
        assert loaded == levels
        b = loaded[1]
        assert isinstance(b.zone[0], D) and b.zone == (D("22000"), D("22020.55"))
        assert b.tf is Timeframe.M15
        assert b.born.tzinfo is not None
        assert b.state_history[1] == (T0 + timedelta(minutes=5), LevelState.SWEPT)

    def test_file_layout_and_encoding(self, tmp_path):
        store = LevelStore(tmp_path)
        store.save("NIFTY", self.make_levels())
        path = tmp_path / "NIFTY" / "levels.json"
        assert path.exists()
        raw = json.loads(path.read_text())
        assert raw[0]["zone"] == ["22150.05", "22160.10"]   # Decimal -> str
        assert raw[0]["kind"] == "PDH"                       # Enum -> name
        assert raw[1]["state"] == "SWEPT"
        assert raw[0]["born"] == T0.isoformat()              # datetime -> iso
        assert raw[0]["tf"] is None and raw[1]["tf"] == "M15"

    def test_load_missing_symbol_returns_empty(self, tmp_path):
        assert LevelStore(tmp_path).load("BANKNIFTY") == []

    def test_save_overwrites(self, tmp_path):
        store = LevelStore(tmp_path)
        levels = self.make_levels()
        store.save("NIFTY", levels)
        store.save("NIFTY", levels[:1])
        assert store.load("NIFTY") == levels[:1]
