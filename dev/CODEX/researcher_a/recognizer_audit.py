#!/usr/bin/env python3
"""Executable semantic audit of SMC recognizers and their ancestry contracts.

This does not claim that passing unit tests proves market semantics.  It
separates code/test parity from causal timing and downstream lineage.
"""
from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "output"


AUDIT = [
    {
        "recognizer": "HTF/M5 swings",
        "source": "app/trader/detectors/swings.py",
        "tests": "app/tests/detectors/test_swings.py",
        "parity_level": "unit-contract",
        "causal": "PASS",
        "lineage": "CONDITIONAL",
        "evidence": [
            "Strict symmetric window over fully closed candles; confirmation occurs only after N right bars.",
            "Level.born is pivot time, not confirmation time; Level has no confirmed_at or parent/origin metadata.",
            "Downstream code must reconstruct confirmation lag to avoid treating the pivot as known early."
        ],
        "required_tokens": ["window_size = 2 * strength + 1", "mid = window[strength]",
                            "born=mid.ts"]
    },
    {
        "recognizer": "external liquidity",
        "source": "app/trader/detectors/liquidity.py",
        "tests": "app/tests/detectors/test_liquidity.py",
        "parity_level": "unit-contract",
        "causal": "PASS",
        "lineage": "PASS_TO_LEVEL",
        "evidence": [
            "PDH/PDL, prior-week, opening-range and EQ levels have stable level_id values.",
            "EQ grouping consumes only already-confirmed swing Levels.",
            "The detector does not distinguish external/important H1 swings; that importance gate is a research-layer definition."
        ],
        "required_tokens": ["_create_pdh_pdl", "_create_pwh_pwl", "\"level_id\": lv.id"]
    },
    {
        "recognizer": "sweep/reclaim",
        "source": "app/trader/detectors/sweep.py",
        "tests": "app/tests/detectors/test_sweep.py",
        "parity_level": "unit-contract + LevelEngine tests",
        "causal": "PASS",
        "lineage": "PASS_TO_LEVEL",
        "evidence": [
            "Sweep and upgrade are keyed to exact level_id and SWEPT state timestamp.",
            "Reclaim upgrade requires the LevelEngine transition inside the configured closed-bar window.",
            "Episode base memory is instance-only and is cleared at session end/restart, so replay/live restart parity is conditional."
        ],
        "required_tokens": ["(level_id, swept ts)", "state_history", "\"level_id\": lv.id"]
    },
    {
        "recognizer": "BOS/CHOCH",
        "source": "app/trader/detectors/structure.py",
        "tests": "app/tests/detectors/test_structure.py",
        "parity_level": "unit-contract",
        "causal": "PASS",
        "lineage": "FAIL_STRICT",
        "evidence": [
            "Break evidence records the exact swing_id and uses closed-candle close breaks.",
            "CHOCH strength boost scans every Level.state_history, without filtering the level timeframe, kind, direction or same root episode.",
            "BOS/CHOCH does not require a displacement body, close location, or an FVG/OB born from the same break.",
            "All historical swing Levels are considered regardless of terminal state."
        ],
        "required_tokens": ["meta = {\"event\": event, \"swing_id\": swing.id}",
                            "for lv in ctx.levels for ts, st in lv.state_history"]
    },
    {
        "recognizer": "FVG/IFVG",
        "source": "app/trader/detectors/fvg.py",
        "tests": "app/tests/detectors/test_fvg.py",
        "parity_level": "unit-contract",
        "causal": "PASS",
        "lineage": "PASS_TO_FVG_LEVEL",
        "evidence": [
            "Three-closed-candle creation and IFVG inversion are keyed to exact FVG level_id and inversion timestamp.",
            "Generic FVG evidence episodes clear each session, allowing a carried zone to fire again; this is not first-lifetime-touch freshness.",
            "The shared Level stores origin bar as born but no explicit c3 confirmation time or parent structure-break id."
        ],
        "required_tokens": ["self._ifvg_seen", "meta={\"level_id\": lv.id, \"event\": \"IFVG\"}",
                            "m.clear()   # episodes are per-session"]
    },
    {
        "recognizer": "close-beyond FVG",
        "source": "app/trader/detectors/fvg_cb.py",
        "tests": "app/tests/detectors/test_fvg_cb.py",
        "parity_level": "real-data reference parity",
        "causal": "PASS",
        "lineage": "CONDITIONAL",
        "evidence": [
            "Actual c3 timestamp is separately retained and same-c3 entries are excluded.",
            "Real-data gap/event parity is tested against the durable reference.",
            "Session-end deliberately clears retest/CE dedupe so carried levels re-fire; reference-continuum parity test documents this as the sole divergence."
        ],
        "required_tokens": ["self._c3_ts[level_id] = c3.ts", "re-fire each event once per session"]
    },
    {
        "recognizer": "generic order block",
        "source": "app/trader/detectors/orderblock.py",
        "tests": "app/tests/detectors/test_orderblock.py",
        "parity_level": "unit-contract",
        "causal": "PASS_WITH_MOVING_WINDOW",
        "lineage": "FAIL_STRICT",
        "evidence": [
            "An opposite candle plus close displacement can form an OB without a causal swing break/BOS/CHOCH.",
            "Evidence carries level_id but no source swing_id, break timestamp, displacement event id or parent FVG id.",
            "Historical candidates in the small rolling window are thresholded with current ATR, not their own-bar ATR."
        ],
        "required_tokens": ["disp = max((c.close - ob.close) * sign",
                            "meta={\"level_id\": lv.id, \"hunt_born\": hunt"]
    },
    {
        "recognizer": "Lux order block",
        "source": "app/trader/detectors/ob_lux.py",
        "tests": "app/tests/detectors/test_ob_lux.py",
        "parity_level": "real-data reference parity",
        "causal": "PASS",
        "lineage": "CONDITIONAL",
        "evidence": [
            "Incremental pivot-break-anchor state and real-data birth parity are strongly tested.",
            "The internal pivot/confirm/anchor relationship is not serialized into Level or Evidence; downstream sees only level_id.",
            "It is parity to one LuxAlgo OB definition, not proof that it belongs to a separate liquidity-sweep event."
        ],
        "required_tokens": ["self._anchor", "self._decided", "meta={\"level_id\": lv.id"]
    },
    {
        "recognizer": "generic breaker",
        "source": "app/trader/detectors/breaker.py",
        "tests": "app/tests/detectors/test_breaker.py",
        "parity_level": "unit-contract",
        "causal": "PASS",
        "lineage": "CONDITIONAL",
        "evidence": [
            "Retest is tied to exact level_id and latest INVERTED episode.",
            "Eligible parents include OB, swing and opening-range Levels, so the label does not guarantee a swept-OB-to-MSS breaker lineage.",
            "No root sweep id or structure-break id is carried downstream."
        ],
        "required_tokens": ["_WATCH_KINDS", "LevelKind.OPEN_RANGE_H",
                            "meta={\"level_id\": lv.id, \"event\": \"BREAKER_RETEST\"}"]
    },
    {
        "recognizer": "MSB breaker block",
        "source": "app/trader/detectors/breaker_msb.py",
        "tests": "app/tests/detectors/test_breaker_msb.py",
        "parity_level": "real-data reference parity",
        "causal": "PASS",
        "lineage": "INTERNAL_PASS_EXTERNAL_FAIL",
        "evidence": [
            "The stateful zigzag -> swept older swing -> MSB -> breaker box -> later retest chain is internally ordered and parity-tested.",
            "Evidence metadata omits box id, source swing ids and MSB id, so it cannot be joined strictly to an external HTF root downstream."
        ],
        "required_tokens": ["if h0 > h1:  # swing high swept -> breaker",
                            "meta={\"event\": \"BREAKER_MSB\", \"sl\": str(sl)"]
    },
    {
        "recognizer": "propulsion block",
        "source": "app/trader/detectors/propulsion_block.py",
        "tests": "app/tests/detectors/test_propulsion_block.py",
        "parity_level": "unit-contract",
        "causal": "PASS",
        "lineage": "FAIL_STRICT",
        "evidence": [
            "Tap is checked only against live parent OBs and confirmation occurs on a later bar.",
            "Pending and confirmed blocks are keyed only by (tap timestamp, direction), not parent level_id; same-side parents can overwrite one another.",
            "Confirmed blocks retain no parent reference and are not invalidated when the parent OB later becomes terminal."
        ],
        "required_tokens": ["self._pending: dict[tuple[datetime, int], tuple]",
                            "self._blocks: dict[tuple[datetime, int], tuple]",
                            "self._blocks[key] ="]
    },
    {
        "recognizer": "mitigation block",
        "source": "app/trader/detectors/mitigation.py",
        "tests": "app/tests/detectors/test_mitigation.py",
        "parity_level": "real-data reference parity",
        "causal": "PASS",
        "lineage": "FAIL_STRICT",
        "evidence": [
            "Candidate formation uses the block candle's causal ATR and real-data parity is tested.",
            "It is a standalone displacement block with no root sweep, structure break, FVG or parent level id.",
            "Touch metadata exposes no block timestamp/id, so downstream cannot prove same-event ancestry."
        ],
        "required_tokens": ["self._blocks[blk.ts]", "meta={\"event\": \"MITIGATION\""]
    },
    {
        "recognizer": "shared level state/freshness",
        "source": "app/trader/models/level.py",
        "tests": "app/tests/engine/test_levels.py",
        "parity_level": "state-machine unit-contract",
        "causal": "PASS_WITH_RESTART_CONDITIONS",
        "lineage": "SCHEMA_FAIL",
        "evidence": [
            "State history timestamps transitions, but Level schema has no confirmed_at, parent_id, root_event_id, origin_break_id, first_touch_at or invalidation reason.",
            "A strict ordered strategy therefore cannot be proven from shared Level objects alone; it needs a lineage ledger such as the isolated study emits."
        ],
        "required_tokens": ["born: datetime", "state_history:", "def record_state"]
    }
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def junit_summary() -> dict:
    path = OUT / "recognizer_tests.xml"
    if not path.exists():
        return {"present": False}
    root = ET.parse(path).getroot()
    # pytest may use testsuites -> testsuite or a single testsuite.
    suites = list(root) if root.tag == "testsuites" else [root]
    return {
        "present": True,
        "tests": sum(int(s.attrib.get("tests", 0)) for s in suites),
        "failures": sum(int(s.attrib.get("failures", 0)) for s in suites),
        "errors": sum(int(s.attrib.get("errors", 0)) for s in suites),
        "skipped": sum(int(s.attrib.get("skipped", 0)) for s in suites),
        "path": str(path.relative_to(ROOT)),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in AUDIT:
        source = ROOT / item["source"]
        tests = ROOT / item["tests"]
        text = source.read_text()
        missing = [x for x in item["required_tokens"] if x not in text]
        row = {
            **{k: v for k, v in item.items() if k != "required_tokens"},
            "source_sha256": sha256(source),
            "tests_sha256": sha256(tests),
            "required_code_tokens_present": not missing,
            "missing_tokens": missing,
        }
        if missing:
            raise AssertionError(f"{item['recognizer']} source contract changed: {missing}")
        rows.append(row)
    result = {
        "separation": {
            "test_parity": "Does implementation match its current tests/reference port?",
            "causal_timing": "Can the event be known from closed bars at emission time?",
            "strict_lineage": "Can downstream prove every event belongs to the same root episode?"
        },
        "junit": junit_summary(),
        "recognizers": rows,
    }
    (OUT / "recognizer_audit.json").write_text(json.dumps(result, indent=2))

    lines = [
        "# Recognizer audit: parity is not lineage",
        "",
        f"JUnit: `{json.dumps(result['junit'], sort_keys=True)}`",
        "",
        "| recognizer | test/reference parity | causal timing | strict lineage |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['recognizer']} | {r['parity_level']} | "
                     f"{r['causal']} | {r['lineage']} |")
    for r in rows:
        lines += ["", f"## {r['recognizer']}", "",
                  f"Source: `{r['source']}` (`{r['source_sha256'][:12]}`)", ""]
        lines.extend(f"- {x}" for x in r["evidence"])
    lines += [
        "",
        "## Audit conclusion",
        "",
        "The current tests can all pass while a combined strategy still lacks "
        "same-event ancestry. Generic structure, OB, propulsion and mitigation "
        "outputs must not be joined merely because timestamps/directions/zones "
        "are nearby. The isolated study therefore reconstructs one explicit "
        "root_id -> H1 break -> parent -> first revisit -> M5 MSS -> child -> fill ledger.",
    ]
    (HERE / "recognizer_audit.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"junit": result["junit"], "recognizers": len(rows),
                      "strict_lineage_failures": sum("FAIL" in r["lineage"] for r in rows)},
                     indent=2))


if __name__ == "__main__":
    main()
