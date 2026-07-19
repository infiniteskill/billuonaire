# Researcher A — strict ordered SMC lineage study

Frozen policy: **P0_PRIMARY**. No policy met the preregistered development feasibility gate; froze P0_PRIMARY.

## Data and causal audit

- Symbols: 138, bars: 588,064, H1 bars: 47,046; invalid OHLC rows dropped: 0.
- Time cut: `2026-06-16`; 35 development sessions / 22 untouched time-holdout sessions.
- Lineage assertions: {"child_fill_after_mss": true, "m5_swing_confirmed_before_mss": true, "mss_after_parent_touch": true, "nested_child_mid": true, "parent_touch_after_confirm": true, "positive_delays": true, "reclaim_before_h1_break_close": true, "rows": 22, "sweep_before_reclaim": true}
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
| m5_mss | 62 |
| children | 71 |
| child_fills | 23 |
| targeted_trades | 22 |

## Development-only policy selection

| policy | n | mean net R | TDEV0 | TDEV1 | SDEV0 | SDEV1 | qualifies |
|---|---:|---:|---:|---:|---:|---:|---|
| P0_PRIMARY | 3 | 3.618 | 13.835 | -1.490 | -1.543 | 6.199 | False |
| P1_FVG_ONLY | 0 | NA | NA | NA | NA | NA | False |
| P2_OB_ONLY | 3 | 3.618 | 13.835 | -1.490 | -1.543 | 6.199 | False |
| P3_DELAY_1 | 3 | 3.618 | 13.835 | -1.490 | -1.543 | 6.199 | False |
| P4_DELAY_6 | 1 | -1.437 | NA | -1.437 | NA | -1.437 | False |
| P5_CHILD_FVG | 0 | NA | NA | NA | NA | NA | False |
| P6_CHILD_OB | 3 | 3.618 | 13.835 | -1.490 | -1.543 | 6.199 | False |
| P7_SWEEP_STOP | 1 | -1.211 | NA | -1.211 | NA | -1.211 | False |
| P8_TARGET_R_1 | 3 | 3.618 | 13.835 | -1.490 | -1.543 | 6.199 | False |
| P9_TARGET_R_1_5 | 3 | 3.618 | 13.835 | -1.490 | -1.543 | 6.199 | False |
| P10_ALL_H1_SWINGS | 3 | 3.618 | 13.835 | -1.490 | -1.543 | 6.199 | False |
| P11_CHILD_DELAY_3 | 2 | 6.146 | 13.835 | -1.543 | -1.543 | 13.835 | False |

## Frozen-policy evaluation

| cell | n | net R | 95% session-bootstrap CI | gross R | win% | PF | MFE/MAE | optimistic net R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 5 | 1.510 | [-1.691, 7.705] | 2.069 | 20.0 | 2.201 | 3.281 | 1.510 |
| DEV_JOINT | 3 | 3.618 | [-1.543, 13.835] | 4.116 | 33.3 | 4.642 | 6.130 | 3.618 |
| TIME_HOLDOUT_ALL_SYMBOLS | 1 | -1.465 | [NA, NA] | -1.000 | 0.0 | 0.000 | 1.029 | -1.465 |
| SYMBOL_HOLDOUT_ALL_TIME | 2 | -1.653 | [-1.841, -1.465] | -1.000 | 0.0 | 0.000 | 1.087 | -1.653 |
| JOINT_HOLDOUT | 1 | -1.465 | [NA, NA] | -1.000 | 0.0 | 0.000 | 1.029 | -1.465 |
| TDEV_SDEV0 | 1 | -1.543 | [NA, NA] | -1.000 | 0.0 | 0.000 | 0.869 | -1.543 |
| TDEV_SDEV1 | 2 | 6.199 | [-1.437, 13.835] | 6.673 | 50.0 | 9.625 | 8.775 | 6.199 |
| THOLD_SDEV | 0 | NA | [NA, NA] | NA | NA | NA | NA | NA |

## Decision

Preregistered profitability gate passed: **False**.

A cell with fewer than 40 joint-holdout trades is inconclusive by rule. A non-positive untouched holdout or confidence lower bound fails the profitable-strategy claim; an optimistic target-first result cannot rescue it.

## Reproduction

```bash
PYTHONDONTWRITEBYTECODE=1 app/.venv/bin/python dev/CODEX/researcher_a/strict_smc_study.py
```

See `PREREGISTRATION.json`, `recognizer_audit.md`, `output/candidates.parquet`, `output/selected_trades.parquet`, `output/metrics.csv`, and `output/cost_sensitivity.csv` for the full audit trail.
