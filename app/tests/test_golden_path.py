"""GOLDEN-PATH chain test (48-VISUAL _ERROR-PROPAGATION doctrine #3).

Runs the FULL taught pipeline (14 detectors -> LevelEngine -> decide) over frozen
1m fixtures (HAVELLS/DABUR/SBICARD 2026-06-01..07-16, the taught-mark windows) and
asserts the ground-truth trade chains reproduce end-to-end. Any regression in ANY
link of the chain (extremes -> liquidity -> sweep states -> zones -> nest -> p/d
permit -> grade -> RR) breaks one of these loudly.

Slow (~4 min): run explicitly or in CI/battery cadence:
    pytest tests/test_golden_path.py -m golden
Calibrated 2026-07-25 from /tmp/golden_cal.out (149 takes; assertions target the
STABLE reproduced chains, tolerant bands to avoid brittleness)."""
from pathlib import Path

import pytest

from trader.config import check_detector_deps, load_settings
from trader.engine.decision import _ZONE_DETS, _ZONE_EVENTS, decide
from trader.engine.pipeline import Orchestrator
from trader.feed.file import FileFeed
from trader.models.candle import Timeframe

ROOT = Path(__file__).resolve().parents[2]
FIX = Path(__file__).parent / "fixtures" / "golden"
TAUGHT = ["extremes", "swings", "liquidity", "sweep", "structure", "wyckoff",
          "orderblock", "fvg", "compression", "ob_taught", "fvg_n", "propulsion2",
          "premium_discount", "htf_nest"]

pytestmark = [pytest.mark.golden, pytest.mark.slow]


@pytest.fixture(scope="module")
def takes(tmp_path_factory):
    s = load_settings(ROOT / "runs/validate/taught_profile/config.json")
    s.detectors.enabled = list(TAUGHT)
    check_detector_deps(s.detectors.enabled)
    syms = ["HAVELLS", "DABUR", "SBICARD"]
    orch = Orchestrator(s, FileFeed(FIX, s.market_spec()), syms, index_symbol=None,
                        max_qty=1, journal_dir=tmp_path_factory.mktemp("golden_j"))
    out = []
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
                        out.append({"sym": pipe.symbol, "ts": ctx.now,
                                    "dir": d.direction.name, "entry": float(d.entry),
                                    "sl": float(d.sl), "target": float(d.target),
                                    "grade": d.grade})
                return evs
            return run_all
        pipe.registry.run_all = mk(pipe, orig)
    orch.run()
    return out


def _sel(takes, sym, dir_, d0, d1):
    return [t for t in takes if t["sym"] == sym and t["dir"] == dir_
            and d0 <= t["ts"].strftime("%m-%d") <= d1]


def test_chain_alive(takes):
    """The whole pipeline produced graded takes at all (any dead link -> 0)."""
    assert len(takes) > 50, f"only {len(takes)} takes — a chain link died"


def test_dabur_taught_short(takes):
    """t24 mark: 450.9 equal-high swept 07-08 -> supply OB short -> 439 draw.
    Chain proves: liquidity line + sweep + zone birth + p/d premium permit + grade."""
    hits = [t for t in _sel(takes, "DABUR", "SHORT", "07-09", "07-13")
            if 449.5 <= t["entry"] <= 453.5 and t["target"] <= 441]
    assert hits, "DABUR taught short (451 -> 439) vanished"
    assert max(t["grade"] for t in hits) >= 5, "DABUR short lost its high grade"


def test_sbicard_t28_long(takes):
    """t28 mark: nested long at the 583.6-587.3 band on 07-09.
    Chain proves: HTF context + nest + discount permit + grade>=5."""
    hits = [t for t in _sel(takes, "SBICARD", "LONG", "07-08", "07-10")
            if 583.0 <= t["entry"] <= 588.5]
    assert hits, "SBICARD t28 long band vanished"
    assert max(t["grade"] for t in hits) >= 5


def test_havells_far_draw_shorts(takes):
    """HAVELLS premium shorts drawing to the 1172-1178 far liquidity, grade>=5.
    Chain proves: EXT range + runway targeting + RR gate survive."""
    hits = [t for t in _sel(takes, "HAVELLS", "SHORT", "07-07", "07-15")
            if t["target"] <= 1178.5 and t["grade"] >= 5]
    assert hits, "HAVELLS far-draw graded shorts vanished"


def test_rr_floor(takes):
    """decide(min_rr=3) honored: no take with RR < 3."""
    for t in takes:
        rr = abs(t["target"] - t["entry"]) / abs(t["entry"] - t["sl"])
        assert rr >= 2.99, f"RR gate leaked: {t}"
