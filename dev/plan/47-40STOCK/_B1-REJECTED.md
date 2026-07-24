# 47-40STOCK — B1 anchor fix (additive emit_live): ATTEMPTED, REJECTED by the gate (2026-07-24)

B1 was the deep-study's #1 bug + red-team-pinned: `extremes.py:218` `if p.confirm_idx is None: continue`
skips the PENDING (live, unmitigated) extreme → it's never an EXT parent → htf_nest can't nest the
terminal-extreme mitigation (the taught +8..26R short at the true high) → `nest_depth==0` hard-caps grade
at 4. Hypothesis (red-team): re-anchoring to the live extreme promotes the user's demoted marks + raises
net-R.

## What I implemented (additive, gated, edge-safe)
`extremes.py`: when `emit_live` (config or `EXT_EMIT_LIVE=1`, default OFF), also emit the pending extreme
as a live EXT_H/EXT_L parent (band to current bar), so htf_nest can nest against the true running extreme.
Default-off → 346 tests green, frozen config identical. A/B'd via the gate harness on 2026.

## RESULT — REJECTED (fails the gate + fails its purpose)
| metric (deduped, eod) | B1 OFF | B1 ON |
|---|---|---|
| hi≥5 net-R | **+6.94R** | **+4.78R** (−2.2) |
| hi≥5 n | 162 | **340** (2×) |
| hi≥5 + min-RR≥3 net-R | **+7.34R** | **+5.37R** (−2.0) |
| the 1221 short (target case) | g4, nest_depth 0 | **STILL g4, nest_depth 0** |

1. **Net-R DROPS ~2R** — B1-ON doubles the hi-tier population (recall↑) but the promoted trades are
   genuinely lower-quality (net-R↓). min-RR does NOT rescue it (they're not just tinyRR).
2. **The target case is NOT fixed** — the 1221 HAVELLS short STILL grades 4 / nest_depth 0 with B1 ON.
   The live-extreme parents did not surgically nest the terminal-extreme mitigation they were meant to.

## Diagnosis + learning
The naive `emit_live` is TOO BROAD: emitting the running extreme on every TF every bar creates ~170
spurious new containments → many low-quality nests that dilute net-R, WITHOUT nesting the specific
terminal mitigation. B1 needs a SURGICAL re-anchor (nest the mitigation at the terminal extreme only),
not a blanket live-parent. Why 1221 still doesn't nest (live EXT_H at 1234 present but base not nested)
needs digging into htf_nest containment + level lifecycle — a deeper rabbit hole.

## Verdict
- **REJECTED. Reverted** (`git checkout extremes.py`) — don't leave an unproven change in the crown-jewel
  emitter. Production unaffected (min-RR still shipped).
- **The gate did its job** — caught a plausible, deep-study-endorsed "fix" that actually degrades the edge.
- **Reframes the B1 upside**: it is NOT a quick win. The deep-study/red-team "B1 promotes marks + raises
  net-R" is now "attempted naively → degrades; needs a targeted re-anchor whose payoff is uncertain."
  Priority DOWN until a surgical approach + a reason to expect net-R gain.

## Open (unchanged by this)
Local-window premium/discount (direction lever), 12 prior-year marks, walk-forward, live pilot. The
proven edge (min-RR-shipped, regime-agnostic, window-robust, ~+6-7R deduped) stands.
