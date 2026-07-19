"""Taught-detector pipeline integration: a config enabling fvg_n + ob_taught
works end-to-end -- scripted synthetic feed through the real Orchestrator,
both detectors' Evidence landing in the journal as verdict members.

The scripted session (M5 plan, expanded to M1s) births a merged bull FVG
[101, 104] (bar 16, extended bar 17-blocked), arms and retests it (bar 20),
then pauses into a consolidation whose upside break births a taught OB
(bar 21) that is armed (bar 22) and retested (bar 23). Only fvg_n and
ob_taught are enabled (distinct < min_zone_detectors keeps final scores 0:
verdicts journal, nothing trades)."""

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from trader.config import Settings
from trader.engine.pipeline import Orchestrator
from trader.feed.mock import Scenario, ScenarioFeed
from trader.models.candle import Candle, Timeframe, tick

CONFIG = Path(__file__).resolve().parent.parent / "trader" / "templates" / "config.baseline.json"
DAY = date(2026, 7, 15)

FLAT = (100, 101, 99, 100)
M5_PLAN = [FLAT] * 15 + [
    (100, 105, 100, 105),                    # displacement middle
    (105, 109, 104, 108),                    # right flank -> FVG [101, 104]
    (108, 110, "100.5", "100.9"),            # burst breaker (shallow, zone lives)
    ("100.9", 107, "100.8", "106.5"),        # recovery; consolidation begins
    ("106.5", 108, "105.9", 107),            # fully above the gap -> armed
    (107, 107, "103.8", "104.5"),            # dips back -> fvg_n retest (LONG)
    ("104.5", 109, "104.4", "108.5"),        # breaks the pause -> OB born
    ("108.5", 110, "108.05", "109.5"),       # fully above the OB -> armed
    ("109.5", 110, "107.5", 109),            # dips back -> ob_taught retest
] + [(109, 110, 108, 109)] * 51              # 75 M5 bars = full NSE session


def script(scenario):
    """Each planned M5 -> 1 shaped M1 + 4 flats at its close (aggregate
    equals the plan bar exactly; every M5 bucket is complete)."""
    t0, out = scenario.session_open(), []
    for k, (o, h, l, c) in enumerate(M5_PLAN):
        qo, qh, ql, qc = tick(o), tick(h), tick(l), tick(c)
        out.append(Candle(scenario.symbol, Timeframe.M1, t0 + timedelta(minutes=5 * k),
                          qo, qh, ql, qc, 10))
        out += [Candle(scenario.symbol, Timeframe.M1,
                       t0 + timedelta(minutes=5 * k + j), qc, qc, qc, qc, 1)
                for j in range(1, 5)]
    return out


def test_taught_detectors_journal_through_pipeline(tmp_path):
    raw = json.loads(CONFIG.read_text())
    raw["detectors"]["enabled"] = ["fvg_n", "ob_taught"]
    raw["confluence"]["weights"].update({"fvg_n": 10, "ob_taught": 10})
    settings = Settings.model_validate(raw)
    feed = ScenarioFeed([Scenario("taught", "TT", DAY, [], 100, script=script)])
    orch = Orchestrator(settings, feed, ["TT"], max_qty=1, journal_dir=tmp_path)
    res = orch.run()
    assert res["trades"] == 0                      # observation-only session
    verdicts = [e for e in orch.journal.read(DAY) if e["kind"] == "verdict"]
    members = {(m[0], m[1]) for v in verdicts for m in v["members"]}
    assert ("fvg_n", "FVG_N_RETEST") in members
    assert ("ob_taught", "OB_RETEST") in members
    # the two taught zones overlap in price: they fuse into one scored zone
    assert any({"fvg_n", "ob_taught"} <= {m[0] for m in v["members"]}
               for v in verdicts)
