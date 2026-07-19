"""Executable invariants for the current SMC recognizers.

This script does not modify production code.  It exercises actual classes in
``app/trader`` and writes a machine-readable audit beside itself.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "app"))

from trader.detectors.bpr import BprDetector, _Gap
from trader.detectors.fvg import FvgDetector
from trader.detectors.orderblock import OrderblockDetector
from trader.detectors.propulsion_block import PropulsionBlockDetector
from trader.detectors.structure import StructureDetector
from trader.detectors.swings import SwingsDetector
from trader.engine.confluence import ConfluenceEngine
from trader.engine.entry import EntryFSM
from trader.engine.levels import LevelEngine
from trader.engine.pipeline import SymbolPipeline
from trader.models.candle import Candle, Timeframe
from trader.models.evidence import Direction, Evidence
from trader.models.level import Level, LevelKind, LevelState
from trader.models.market import NSE

D = Decimal
IST = timezone(timedelta(hours=5, minutes=30))


@dataclass
class Finding:
    id: str
    passed_expected_invariant: bool
    observed: object
    expected: object
    consequence: str


class View:
    def __init__(self, candles: list[Candle]):
        self.candles = candles

    def last(self, n: int, tf: Timeframe) -> list[Candle]:
        data = [c for c in self.candles if c.tf is tf]
        return data[-n:] if n > 0 else []


class Ctx(SimpleNamespace):
    def atr(self, tf: Timeframe, period: int = 14):
        return getattr(self, "fixed_atr", D("1"))


def candle(ts: datetime, o, h, l, c, tf=Timeframe.M5) -> Candle:
    return Candle("TEST", tf, ts, D(str(o)), D(str(h)), D(str(l)), D(str(c)), 100)


def base_ctx(candles: list[Candle], levels: list[Level] | None = None) -> Ctx:
    now = candles[-1].ts + timedelta(minutes=5)
    return Ctx(symbol="TEST", now=now, candles=View(candles),
               levels=levels or [], evidence_history=[], spec=NSE,
               fixed_atr=D("1"),
               day=SimpleNamespace(session_date=candles[-1].ts.date()))


def ifvg_reachability() -> Finding:
    """Production ordering is LevelEngine.update then FvgDetector.detect."""
    t = datetime(2026, 7, 1, 10, 0, tzinfo=IST)
    lv = Level("fvg", "TEST", LevelKind.FVG_BULL, (D("100"), D("101")),
               t - timedelta(hours=2), Timeframe.M5, LevelState.RECLAIMED)
    breaking = candle(t, 101, 101.2, 99.2, 99.5)
    ctx = base_ctx([breaking], [lv])
    engine = LevelEngine({})
    detector = FvgDetector({})
    engine.update(ctx.levels, breaking, D("1"))
    state_after_engine = lv.state.name
    detector.detect(ctx)
    state_after_detector = lv.state.name
    later = candle(t + timedelta(minutes=5), 99.5, 100.5, 99.3, 99.7)
    ctx.candles = View([later])
    ctx.now = later.ts + timedelta(minutes=5)
    transitions = engine.update(ctx.levels, later, D("1"))
    emitted = detector.detect(ctx)
    reachable = lv.state is LevelState.INVERTED or any(
        e.meta.get("event") == "IFVG" for e in emitted
    )
    return Finding(
        "fvg_ifvg_reachable_in_pipeline_order",
        reachable,
        {"after_engine": state_after_engine,
         "after_fvg_detector": state_after_detector,
         "next_transitions": [x.new.name for x in transitions],
         "next_events": [e.meta.get("event") for e in emitted]},
        "RECLAIMED should be allowed to complete the two-close INVERTED transition",
        "The FVG detector marks the level DEAD on the first beyond-edge close, so the "
        "LevelEngine cannot complete INVERTED and normal pipeline execution cannot emit IFVG.",
    )


def structure_sweep_ancestry() -> Finding:
    t = datetime(2026, 7, 1, 11, 0, tzinfo=IST)
    bars = [candle(t + timedelta(minutes=5 * i), 100, 101, 99, 100)
            for i in range(6)]
    unrelated = Level("unrelated", "TEST", LevelKind.ROUND,
                      (D("200"), D("201")), t, Timeframe.M15,
                      state=LevelState.RECLAIMED,
                      state_history=[(bars[-1].ts, LevelState.SWEPT)])
    ctx = base_ctx(bars, [unrelated])
    observed = StructureDetector({})._swept_recently(ctx, Timeframe.M5)
    return Finding(
        "choch_requires_related_same_tf_sweep",
        not observed,
        observed,
        False,
        "Any recent SWEPT transition, including an unrelated M15 round number, upgrades an "
        "M5 CHOCH. Direction, swing ID, level kind and timeframe ancestry are not checked.",
    )


def swing_availability_provenance() -> Finding:
    t = datetime(2026, 7, 1, 9, 15, tzinfo=IST)
    highs = [101, 102, 103, 110, 103, 102, 101]
    bars = [candle(t + timedelta(minutes=5 * i), 100, h, 99, 100)
            for i, h in enumerate(highs)]
    ctx = base_ctx(bars)
    SwingsDetector({"strength": 3, "timeframes": ["5m"]}).detect(ctx)
    lv = next(x for x in ctx.levels if x.kind is LevelKind.SWING_H)
    confirmation_time = bars[-1].ts + timedelta(minutes=5)
    has_availability_field = hasattr(lv, "available_at")
    return Finding(
        "swing_records_confirmation_availability",
        has_availability_field,
        {"born": lv.born.isoformat(),
         "runtime_confirmation": confirmation_time.isoformat(),
         "lag_minutes": int((confirmation_time - lv.born).total_seconds() / 60),
         "has_available_at": has_availability_field},
        "Store both pivot/origin time and causal confirmation time",
        "The pivot is causally created only after three right bars close, but Level stores only "
        "the old pivot timestamp. Parent-child lineage and restart reconstruction cannot tell "
        "when the swing became usable.",
    )


def orderblock_requires_bos() -> Finding:
    t = datetime(2026, 7, 1, 10, 0, tzinfo=IST)
    bars = [
        candle(t, 99.5, 100.0, 99.0, 99.7),
        candle(t + timedelta(minutes=5), 100.0, 100.2, 98.8, 99.0),
        candle(t + timedelta(minutes=10), 99.1, 100.4, 99.0, 100.2),
        candle(t + timedelta(minutes=15), 100.2, 100.5, 100.0, 100.3),
        candle(t + timedelta(minutes=20), 100.3, 100.4, 100.1, 100.2),
    ]
    ctx = base_ctx(bars)
    detector = OrderblockDetector({"displacement_atr": 1.0, "lookback": 3})
    detector.detect(ctx)
    obs = [x for x in ctx.levels if x.kind in (LevelKind.OB_BULL, LevelKind.OB_BEAR)]
    has_structure_parent = any("swing" in x.id.lower() or "bos" in x.id.lower() for x in obs)
    return Finding(
        "orderblock_requires_displacement_bos_and_parent_swing",
        len(obs) == 0 or has_structure_parent,
        {"created": len(obs), "zones": [[str(v) for v in x.zone] for x in obs],
         "input_swing_levels": 0},
        "No OB without a displaced structure break tied to a known swing",
        "The baseline OB rule needs only opposite candle color plus net displacement. It can "
        "create an OB with no swing, BOS, liquidity event or parent identifier.",
    )


def fvg_first_visit_only() -> Finding:
    t = datetime(2026, 7, 1, 10, 0, tzinfo=IST)
    lv = Level("fvg", "TEST", LevelKind.FVG_BULL, (D("100"), D("102")),
               t - timedelta(days=2), Timeframe.M5)
    detector = FvgDetector({})
    c1 = candle(t, 103, 103, 100.5, 101.5)
    ctx = base_ctx([c1], [lv])
    first = detector._ce_hold(ctx, lv, c1, True)
    detector.on_session_end()
    c2 = candle(t + timedelta(days=1), 103, 103, 100.5, 101.5)
    ctx.now = c2.ts + timedelta(minutes=5)
    second = detector._ce_hold(ctx, lv, c2, True)
    observed = len(first) == 1 and len(second) == 0
    return Finding(
        "fvg_signal_is_first_unmitigated_visit_only",
        observed,
        {"first_day_emissions": len(first), "next_day_emissions": len(second)},
        {"first_day_emissions": 1, "next_day_emissions": 0},
        "Session reset deliberately allows the same carried FVG to fire again, conflicting with "
        "a strict fresh/unvisited-POI strategy.",
    )


def clustering_preserves_separate_locations() -> Finding:
    t = datetime(2026, 7, 1, 10, 0, tzinfo=IST)
    evs = [
        Evidence("a", Direction.LONG, 1.0, (D("0"), D("1")), t, 3),
        Evidence("b", Direction.LONG, 1.0, (D("1.2"), D("2.2")), t, 3),
        Evidence("c", Direction.LONG, 1.0, (D("2.4"), D("3.4")), t, 3),
    ]
    clusters = ConfluenceEngine._cluster(object(), evs, D("0.25"))
    separated = len(clusters) > 1
    return Finding(
        "confluence_does_not_bridge_distant_pois",
        separated,
        {"cluster_count": len(clusters),
         "bounds": [[str(x[0]), str(x[1])] for x in clusters]},
        "The first and last non-overlapping locations remain separate",
        "Single-link chaining lets intermediate evidence manufacture one wide confluence zone.",
    )


def entry_keeps_scored_lineage() -> Finding:
    t = datetime(2026, 7, 1, 10, 0, tzinfo=IST)
    unrelated = Level("round", "TEST", LevelKind.ROUND, (D("104"), D("105")),
                      t, Timeframe.M15)
    ctx = SimpleNamespace(symbol="TEST", levels=[unrelated])
    chosen = EntryFSM._traded_zone(object(), (D("100"), D("110")), ctx, D("104.5"))
    preserved = chosen == (D("100"), D("110"))
    return Finding(
        "entry_zone_must_descend_from_scored_parent",
        preserved,
        [str(chosen[0]), str(chosen[1])],
        ["100", "110"],
        "Any narrower overlapping level, even an unrelated M15 round number, can replace the "
        "scored zone. Detector, direction, timeframe and parent ID are ignored.",
    )


def cross_day_swing_continuum() -> Finding:
    """A strict HTF liquidity map must not delete every swing at midnight."""
    t = datetime(2026, 7, 1, 14, 0, tzinfo=IST)
    swing = Level("swing", "TEST", LevelKind.SWING_H, (D("100"), D("100.1")),
                  t, Timeframe.M15)
    pipe = object.__new__(SymbolPipeline)
    pipe.levels = [swing]
    pipe.day = SimpleNamespace(session_date=(t + timedelta(days=1)).date())
    pipe._zone_max_age = 5
    carried = SymbolPipeline._carry_over(pipe)
    observed = swing in carried
    return Finding(
        "cross_day_swing_liquidity_continuum", observed,
        {"carried": observed, "kind": swing.kind.name, "tf": swing.tf.value},
        "Confirmed important swing liquidity remains available until swept/invalidated",
        "Session pruning carries OB/FVG and selected liquidity kinds but deletes every "
        "SWING_H/SWING_L. The production tree cannot revisit prior-session swing liquidity.",
    )


def propulsion_parent_lifecycle() -> Finding:
    t = datetime(2026, 7, 1, 10, 0, tzinfo=IST)
    parent = Level("parent-ob", "TEST", LevelKind.OB_BULL, (D("100"), D("101")),
                   t - timedelta(minutes=10), Timeframe.M5)
    tap = candle(t, 101.1, 101.4, 100.5, 101.2)
    propel = candle(t + timedelta(minutes=5), 101.2, 102.5, 101.1, 102.3)
    revisit = candle(t + timedelta(minutes=10), 102.2, 102.3, 100.7, 100.8)
    det = PropulsionBlockDetector({"propel_bars": 3, "propel_atr": 1.0})
    ctx = base_ctx([tap], [parent])
    det.detect(ctx)
    ctx.candles = View([tap, propel])
    ctx.now = propel.ts + timedelta(minutes=5)
    det.detect(ctx)
    parent.record_state(propel.ts, LevelState.DEAD)
    ctx.candles = View([tap, propel, revisit])
    ctx.now = revisit.ts + timedelta(minutes=5)
    evs = det.detect(ctx)
    return Finding(
        "propulsion_child_requires_live_parent_ob", not evs,
        {"events_after_parent_dead": [e.meta.get("event") for e in evs],
         "event_meta": [e.meta for e in evs]},
        "No propulsion signal after its parent OB is DEAD/MITIGATED",
        "Propulsion state loses parent level_id/state, so a child can fire after "
        "the parent thesis is invalid.",
    )


def bpr_requires_common_delivery() -> Finding:
    t = datetime(2026, 7, 1, 10, 0, tzinfo=IST)
    det = BprDetector({})
    det._gaps = [
        _Gap(t - timedelta(days=4), D("100"), D("102"), True),
        _Gap(t - timedelta(minutes=10), D("101"), D("103"), False),
    ]
    last = candle(t, 102, 102.5, 100.5, 101.5)
    ctx = base_ctx([last])
    evs = det._overlaps(ctx, last, D("0.15"))
    has_lineage = bool(evs) and all(
        {"bull_id", "bear_id", "parent_swing_id"} <= set(e.meta) for e in evs
    )
    return Finding(
        "bpr_requires_common_delivery_lineage", not evs or has_lineage,
        {"events": len(evs), "meta": [e.meta for e in evs]},
        "Opposing gaps must identify compatible parents/leg before directional BPR",
        "Any live bull/bear FVG overlap can fire; newer birth time chooses direction. "
        "No shared swing, displacement leg, timeframe or parent thesis is required.",
    )


def detector_level_ownership() -> Finding:
    t = datetime(2026, 7, 1, 10, 0, tzinfo=IST)
    fvg_foreign = Level("TEST-FVG_BULL-5m-fvg_cb-x", "TEST", LevelKind.FVG_BULL,
                        (D("100"), D("102")), t - timedelta(hours=1), Timeframe.M5)
    last = candle(t, 103, 103, 100.5, 101.5)
    fctx = base_ctx([last], [fvg_foreign])
    fevs = FvgDetector({}).detect(fctx)
    fcont = any(e.meta.get("level_id") == fvg_foreign.id for e in fevs)
    ob_foreign = Level("TEST-ob_lux-OB_BULL-5m-x", "TEST", LevelKind.OB_BULL,
                       (D("100"), D("102")), t - timedelta(hours=1), Timeframe.M5)
    octx = base_ctx([last], [ob_foreign])
    oevs = OrderblockDetector({})._evidence(octx, last)
    ocont = any(e.meta.get("level_id") == ob_foreign.id for e in oevs)
    return Finding(
        "alternative_detectors_own_their_levels", not (fcont or ocont),
        {"fvg_claimed_fvg_cb": fcont, "orderblock_claimed_ob_lux": ocont},
        "Each implementation emits and mutates only its own zones",
        "Shared LevelKind values have no producer field. Generic FVG/OB can claim the "
        "alternative detector's zone, corrupting attribution and apparent confluence.",
    )


def capture_density() -> dict:
    path = ROOT / "runs/artifacts-data/signals60.parquet"
    s = pd.read_parquet(path, columns=["detector", "event", "symbol", "session", "ts", "direction"])
    per_day = s.groupby(["symbol", "session"]).size()
    duplicate = s.duplicated(["symbol", "ts", "direction"])
    return {
        "rows": int(len(s)),
        "detector_event_counts": {
            f"{a}:{b}": int(n) for (a, b), n in s.groupby(["detector", "event"]).size().items()
        },
        "signals_per_symbol_session": {
            "mean": float(per_day.mean()), "median": float(per_day.median()),
            "p95": float(per_day.quantile(0.95)), "max": int(per_day.max())
        },
        "same_symbol_bar_direction_duplicate_rows": int(duplicate.sum()),
        "same_symbol_bar_direction_duplicate_fraction": float(duplicate.mean()),
        "provenance_warning": "This capture is a raw-detector research artifact, not current production trades."
    }


def main() -> None:
    findings = [ifvg_reachability(), structure_sweep_ancestry(),
                swing_availability_provenance(), orderblock_requires_bos(),
                fvg_first_visit_only(), clustering_preserves_separate_locations(),
                entry_keeps_scored_lineage(), cross_day_swing_continuum(),
                propulsion_parent_lifecycle(),
                bpr_requires_common_delivery(), detector_level_ownership()]
    report = {
        "head_scope": "current app recognizer classes plus machine-readable signal capture",
        "tests": [asdict(x) for x in findings],
        "capture_density": capture_density(),
        "summary": {
            "invariants_passed": sum(x.passed_expected_invariant for x in findings),
            "invariants_failed": sum(not x.passed_expected_invariant for x in findings),
            "unit_suite_note": "The repository's 782 tests pass; these are cross-component SMC-lineage invariants absent from that suite."
        }
    }
    out = Path(__file__).with_name("recognizer_audit.json")
    out.write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report["summary"], indent=2))
    for x in findings:
        print(f"{'PASS' if x.passed_expected_invariant else 'FAIL'} {x.id}: {x.observed}")
    print(out)


if __name__ == "__main__":
    main()
