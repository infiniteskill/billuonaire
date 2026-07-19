# Researcher A — strict ordered SMC lineage study

Frozen policy: **P0_PRIMARY**. No policy met the preregistered development feasibility gate; froze P0_PRIMARY.

## Data and causal audit

- Symbols: 138, bars: 588,064, H1 bars: 47,046; invalid OHLC rows dropped: 0.
- Time cut: `2026-06-16`; 35 development sessions / 22 untouched time-holdout sessions.
- Lineage assertions: {"assertions": "vacuous", "rows": 0}
- Primary execution: resting child-CE limit, stop-first ambiguity, adverse gap-through stop, no favorable target-gap fill, same-session EOD exit, 6 bps round trip.

## Full recognizer funnel (all parent/child variants before policy filtering)

| stage | count |
|---|---:|
| roots | 30,988 |
| root_sweeps | 19,493 |
| root_reclaims | 11,974 |
| important_root_reclaims | 11,697 |
| h1_structure_breaks | 1,611 |
| parent_fvg | 655 |
| parent_ob | 1,369 |
| parent_first_revisits | 775 |
| m5_mss | 3 |
| children | 3 |
| child_fills | 0 |
| targeted_trades | 0 |

## Development-only policy selection

| policy | n | mean net R | TDEV0 | TDEV1 | SDEV0 | SDEV1 | qualifies |
|---|---:|---:|---:|---:|---:|---:|---|
| P0_PRIMARY | 0 | NA | NA | NA | NA | NA | False |
| P1_FVG_ONLY | 0 | NA | NA | NA | NA | NA | False |
| P2_OB_ONLY | 0 | NA | NA | NA | NA | NA | False |
| P3_DELAY_1 | 0 | NA | NA | NA | NA | NA | False |
| P4_DELAY_6 | 0 | NA | NA | NA | NA | NA | False |
| P5_CHILD_FVG | 0 | NA | NA | NA | NA | NA | False |
| P6_CHILD_OB | 0 | NA | NA | NA | NA | NA | False |
| P7_SWEEP_STOP | 0 | NA | NA | NA | NA | NA | False |
| P8_TARGET_R_1 | 0 | NA | NA | NA | NA | NA | False |
| P9_TARGET_R_1_5 | 0 | NA | NA | NA | NA | NA | False |
| P10_ALL_H1_SWINGS | 0 | NA | NA | NA | NA | NA | False |
| P11_CHILD_DELAY_3 | 0 | NA | NA | NA | NA | NA | False |

## Frozen-policy evaluation

| cell | n | net R | 95% session-bootstrap CI | gross R | win% | PF | MFE/MAE | optimistic net R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 0 | NA | [NA, NA] | NA | NA | NA | NA | NA |
| DEV_JOINT | 0 | NA | [NA, NA] | NA | NA | NA | NA | NA |
| TIME_HOLDOUT_ALL_SYMBOLS | 0 | NA | [NA, NA] | NA | NA | NA | NA | NA |
| SYMBOL_HOLDOUT_ALL_TIME | 0 | NA | [NA, NA] | NA | NA | NA | NA | NA |
| JOINT_HOLDOUT | 0 | NA | [NA, NA] | NA | NA | NA | NA | NA |
| TDEV_SDEV0 | 0 | NA | [NA, NA] | NA | NA | NA | NA | NA |
| TDEV_SDEV1 | 0 | NA | [NA, NA] | NA | NA | NA | NA | NA |
| THOLD_SDEV | 0 | NA | [NA, NA] | NA | NA | NA | NA | NA |

## Decision

Preregistered profitability gate passed: **False**.

A cell with fewer than 40 joint-holdout trades is inconclusive by rule. A non-positive untouched holdout or confidence lower bound fails the profitable-strategy claim; an optimistic target-first result cannot rescue it.

## Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 app/.venv/bin/python dev/CODEX/researcher_a/strict_smc_study.py
```

See `PREREGISTRATION.json`, `recognizer_audit.md`, `output/candidates.parquet`, `output/selected_trades.parquet`, `output/metrics.csv`, and `output/cost_sensitivity.csv` for the full audit trail.
