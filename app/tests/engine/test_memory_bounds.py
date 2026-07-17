"""C10: detector instance memories (dedupe sets / episode maps) must stay
session-bounded across a long multi-day run -- on_session_end prunes them at
every session boundary; timestats ``_counts`` is exempt (learning data)."""

import time
from datetime import date, timedelta

from tests.harness import ALL_IMPLEMENTED, scenario_settings
from trader.engine.pipeline import Orchestrator
from trader.feed.mock import ScenarioFeed, judas_reversal, range_pin, trend_day

_CAP = 400   # ~one session of keys; 30 unpruned days would be ~30x this


def _weekdays(start: date, n: int):
    d = start
    while n:
        if d.weekday() < 5:
            yield d
            n -= 1
        d += timedelta(days=1)


def test_thirty_day_memory_bounded(tmp_path, capsys):
    mk = [judas_reversal, trend_day, range_pin]
    feed = ScenarioFeed([mk[i % 3]("SYNTH", d, 100.0)
                         for i, d in enumerate(_weekdays(date(2026, 6, 1), 30))])
    orch = Orchestrator(scenario_settings(ALL_IMPLEMENTED), feed, ["SYNTH"],
                        max_qty=1, journal_dir=tmp_path / "journal")
    t0 = time.perf_counter()
    orch.run()
    wall = time.perf_counter() - t0
    pipe = orch.pipelines["SYNTH"]
    for det in [*pipe.registry.detectors, pipe.wyckoff]:
        for attr, val in vars(det).items():
            if attr == "_counts" or not isinstance(val, (set, dict)):
                continue                     # timestats learning data: exempt
            assert len(val) < _CAP, f"{det.name}.{attr} grew to {len(val)}"
    assert len(pipe.evidence_history) <= 200  # existing window still holds
    assert pipe.day.session_date == date(2026, 7, 10)  # all 30 sessions ran
    # dated liquidity pairs: only the newest generation may carry, so the
    # level population stays flat instead of gaining one stale pair/session
    carried = pipe._carry_over()
    for kind in ("PDH", "PDL", "PWH", "PWL"):
        assert sum(lv.kind.name == kind for lv in carried) <= 1, kind
    assert len(pipe.levels) < 60
    with capsys.disabled():
        print(f"\n[memory-bounds] 30-day single-symbol run: {wall:.1f}s wall")
