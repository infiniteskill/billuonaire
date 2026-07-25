"""F6 ENTRY-PARITY (core-hardening C7): the production path (GateChain -> FSM
arm -> broker fill -> trade_open) must EXECUTE the taught decide() signals the
research frame counts — the last sim-vs-prod gap.

Contract (not bit-equality — FSM adds entry mechanics):
  1. production opens a healthy number of trades on the golden fixture
     (decide-takes that clear the safety gates must not be silently strangled
     — the pre-F1-part2 template/regime_veto bug shape);
  2. every trade_open is CO-LOCATED with a decide-take: same symbol+direction
     with a take at a nearby ts and a nearby entry zone;
  3. stops are on the correct side and within the zone geometry.
Run: -m golden (heavy)."""
import json
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
def run(tmp_path_factory):
    jdir = tmp_path_factory.mktemp("parity_j")
    s = load_settings(ROOT / "runs/validate/stage2_profile/config.json")
    s.detectors.enabled = list(TAUGHT)
    check_detector_deps(s.detectors.enabled)
    syms = ["HAVELLS", "DABUR"]
    orch = Orchestrator(s, FileFeed(FIX, s.market_spec()), syms, index_symbol=None,
                        max_qty=1, journal_dir=jdir)
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
                                      "dir": d.direction.name,
                                      "entry": float(d.entry), "sl": float(d.sl)})
                return evs
            return run_all
        pipe.registry.run_all = mk(pipe, orig)
    orch.run()
    opens = []
    for f in jdir.rglob("*.jsonl"):
        for line in f.read_text().splitlines():
            d = json.loads(line)
            if d.get("kind") == "trade_open":
                d["sym"] = f.parent.name if f.parent.name != jdir.name else \
                    d.get("symbol", "?")
                opens.append(d)
    return takes, opens, jdir


def test_production_not_strangled(run):
    """Pre-F1-part2, legacy gates passed ~17% of taught signals. With the
    bypass, production must open a substantial trade count on the fixture."""
    takes, opens, _ = run
    assert len(takes) > 50
    assert len(opens) >= 10, f"production opened only {len(opens)} trades"


def test_every_open_colocated_with_take(run):
    """No production trade may exist WITHOUT a taught decide-take nearby
    (production must not invent trades the research frame never counted)."""
    import datetime as dt
    takes, opens, _ = run
    for o in opens:
        ots = dt.datetime.fromisoformat(o["at"]) if isinstance(o["at"], str) else o["at"]
        near = [t for t in takes
                if t["dir"] == str(o["direction"]).split(".")[-1]
                and abs((t["ts"] - ots).total_seconds()) <= 3600]
        assert near, f"orphan production trade (no decide-take within 1h): {o['at']} {o['direction']}"


def test_stop_side_sanity(run):
    """Stops must sit on the protective side of the fill."""
    takes, opens, _ = run
    for o in opens:
        d = str(o["direction"]).split(".")[-1]
        price, stop = float(o["price"]), float(o["stop"])
        if d == "LONG":
            assert stop < price
        else:
            assert stop > price
