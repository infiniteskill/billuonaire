"""GOLDEN-PATH regime chains (bull + bear) — extends test_golden_path to 3 regimes.

Calibrated 2026-07-26 from /tmp/gcal2.out on the final stage2 profile. Same contract:
any dead chain link kills a named taught-style trade loudly. Run: -m golden."""
from pathlib import Path

import pytest

from trader.config import check_detector_deps, load_settings
from trader.engine.decision import _ZONE_DETS, _ZONE_EVENTS, decide
from trader.engine.pipeline import Orchestrator
from trader.feed.file import FileFeed
from trader.models.candle import Timeframe

ROOT = Path(__file__).resolve().parents[2]
FIXROOT = Path(__file__).parent / "fixtures"
TAUGHT = ["extremes", "swings", "liquidity", "sweep", "structure", "wyckoff",
          "orderblock", "fvg", "compression", "ob_taught", "fvg_n", "propulsion2",
          "premium_discount", "htf_nest"]

pytestmark = [pytest.mark.golden, pytest.mark.slow]


def _run(fixdir, syms, tmp):
    s = load_settings(ROOT / "runs/validate/stage2_profile/config.json")
    s.detectors.enabled = list(TAUGHT)
    check_detector_deps(s.detectors.enabled)
    orch = Orchestrator(s, FileFeed(FIXROOT / fixdir, s.market_spec()), syms,
                        index_symbol=None, max_qty=1, journal_dir=tmp)
    takes = []
    for pipe in orch.pipelines.values():
        orig = pipe.registry.run_all

        def mk(pipe, orig):
            def run_all(ctx):
                evs = orig(ctx)
                if any(e.detector in _ZONE_DETS and e.meta.get("event") in _ZONE_EVENTS
                       for e in evs):
                    w = ctx.candles.last(20, Timeframe("5m"))
                    cutoff = w[0].ts if w else ctx.now
                    d = decide(ctx, list(evs) + [e for e in ctx.evidence_history
                                                 if e.ts >= cutoff], 4, 3.0)
                    if d.take:
                        takes.append({"sym": pipe.symbol, "ts": ctx.now,
                                      "dir": d.direction.name, "entry": float(d.entry),
                                      "target": float(d.target), "grade": d.grade})
                return evs
            return run_all
        pipe.registry.run_all = mk(pipe, orig)
    orch.run()
    return takes


@pytest.fixture(scope="module")
def bull(tmp_path_factory):
    return _run("golden_bull", ["ADANIPORTS", "BAJAJ-AUTO"],
                tmp_path_factory.mktemp("gb"))


@pytest.fixture(scope="module")
def bear(tmp_path_factory):
    return _run("golden_bear", ["BANKBARODA", "BERGEPAINT"],
                tmp_path_factory.mktemp("gq"))


def test_bull_chain_alive(bull):
    assert len(bull) > 40, f"bull chain produced only {len(bull)} takes"


def test_bull_buy_dip(bull):
    """BAJAJ-AUTO 2023-12-07 buy-dip LONG 5852 -> 6057, grade>=5 (with-trend
    continuation in bull — the chameleon's bull mode)."""
    hits = [t for t in bull if t["sym"] == "BAJAJ-AUTO" and t["dir"] == "LONG"
            and t["ts"].strftime("%m-%d") == "12-07"
            and 5840 <= t["entry"] <= 5865 and t["target"] >= 6000]
    assert hits and max(t["grade"] for t in hits) >= 5


def test_bear_chain_alive(bear):
    assert len(bear) > 40, f"bear chain produced only {len(bear)} takes"


def test_bear_with_trend_short(bear):
    """BANKBARODA 2024-10-21 SHORT 233.5 -> 224, grade>=5 (sell-rip in bear)."""
    hits = [t for t in bear if t["sym"] == "BANKBARODA" and t["dir"] == "SHORT"
            and t["ts"].strftime("%m-%d") == "10-21"
            and 232 <= t["entry"] <= 235 and t["target"] <= 226]
    assert hits and max(t["grade"] for t in hits) >= 5


def test_bear_reversal_long(bear):
    """BERGEPAINT 2024-10-21 LONG 551 -> 586, grade>=6 (deep-discount fade)."""
    hits = [t for t in bear if t["sym"] == "BERGEPAINT" and t["dir"] == "LONG"
            and 549 <= t["entry"] <= 553 and t["grade"] >= 6]
    assert hits
