"""Phase-3 exit gate: day-template scenario matrix over the FULL detector set.

All four flagship scenario days run through the real feed -> store ->
LevelEngine -> DetectorRegistry (all 12 implemented detectors) ->
TemplateClassifier pipeline with one persistent DayState per day, and the
gate asserts: the classifier locks each day's ground-truth template at
11:30 and holds it; the new detectors actually speak somewhere in the
matrix; detector isolation still holds with the full set; and no evidence
ever looks ahead of its view.
"""

from datetime import date, timedelta

import pytest

from tests.harness import ALL_IMPLEMENTED, Result, run_scenario
from trader.feed.mock import double_trap, judas_reversal, range_pin, trend_day

DAY = date(2026, 7, 15)
LOCK = timedelta(minutes=135)  # session open + 135min = 11:30 NSE
SCENARIOS = {
    sc.name: sc
    for sc in (judas_reversal("X", DAY, 100.0), trend_day("X", DAY, 100.0),
               range_pin("X", DAY, 100.0), double_trap("X", DAY, 100.0))
}

# index is enabled but inert here (requires ctx.index, never provided), so
# every detector that CAN speak in this harness is one of these 11.
MUST_FIRE = ("orderblock", "wyckoff", "timestats")   # each, somewhere
MAY_FIRE = ("fvg", "breaker", "compression", "volume")  # >=2 of, combined


@pytest.fixture(scope="module")
def matrix() -> dict[str, Result]:
    return {name: run_scenario(sc, ALL_IMPLEMENTED, classify=True)
            for name, sc in SCENARIOS.items()}


# 1. template lock: correct at 11:30 on all four days, then held forever
@pytest.mark.parametrize("name", list(SCENARIOS))
def test_template_locks_truth_and_holds(matrix, name):
    truth = SCENARIOS[name].truth["template"]
    lock_at = SCENARIOS[name].session_open() + LOCK
    locked = [run for run in matrix[name].runs if run.now >= lock_at]
    assert locked and locked[0].now == lock_at   # the 11:30 M5 close ticks
    assert [run.template for run in locked] == [truth] * len(locked)
    assert matrix[name].day.template == truth    # classifier wrote DayState


# 2a. the phase-3 detectors this matrix is shaped for all speak somewhere
@pytest.mark.parametrize("detector", MUST_FIRE)
def test_new_detector_fires_somewhere(matrix, detector):
    hits = {name: sum(e.detector == detector for e in r.history)
            for name, r in matrix.items()}
    assert sum(hits.values()) >= 1, f"{detector} silent on all four: {hits}"


# 2b. of the pattern-dependent detectors, at least two speak across the
# matrix combined (scripted days can't owe every exotic pattern); which
# ones fired is logged so a regression is visible in the test output.
def test_pattern_detectors_fire_across_matrix(matrix):
    fired = {d: sum(e.detector == d for r in matrix.values() for e in r.history)
             for d in MAY_FIRE}
    print(f"\npattern-detector evidence across matrix: {fired}")
    assert sum(1 for n in fired.values() if n) >= 2, fired


# 3. isolation re-proof at full strength: disabling breaker changes nothing
# for the other level/evidence detectors on the judas day
def test_breaker_isolation_on_judas(matrix):
    keep = ("swings", "liquidity", "structure", "sweep", "orderblock")
    reduced = run_scenario(SCENARIOS["judas_reversal"],
                           tuple(d for d in ALL_IMPLEMENTED if d != "breaker"),
                           classify=True)

    def stream(result: Result) -> str:
        return "\n".join(f"{i}|{e!r}" for i, run in enumerate(result.runs)
                         for e in run.evidence if e.detector in keep)

    full = matrix["judas_reversal"]
    assert stream(full) == stream(reduced)
    assert stream(full)                                   # non-vacuous
    assert [repr(lv) for lv in full.levels] == [repr(lv) for lv in reduced.levels]
    assert full.day.template == reduced.day.template == "TRAP_REVERSAL"


# 4. no lookahead anywhere in the matrix
def test_no_lookahead(matrix):
    for result in matrix.values():
        for run in result.runs:
            assert all(e.ts <= run.now for e in run.evidence)
