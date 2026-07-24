# Z3 FAITHFULNESS — B1 recall-quality gap (2026-07-24)

**Q:** Of the user's marks the system FIRES but UNDER-grades (grade<5), how many are extreme-mitigations
(entry hugging the era/tape direction-extreme) that the B1 EXT-anchor bug demotes below hi-tier — and if a
B1 fix re-anchored the nest to the live extreme, how many more of the user's marks become hi-grade winners?

Method: 32 marks (`tools/ytrades.json`) co-located into the 3 deduped tradebooks by closest-entry
sym+dir match (rel tol 2%); this re-derivation reproduces the parent table EXACTLY (FIRED 20/32, same 12
misses, same grades). 1h Wilder-ATR per stock+tape from the source 1m tapes (`data/{wide,regime_bull,regime_2024q4}`),
`ATR_local = median(ATR/close)*entry`. All claims below are number+n; no pipeline was re-run.

## 1) The nest_depth HARD GATE (why B1 caps grade) — measured over all 7,598 deduped trades
| nest_depth | n | P(grade>=5) | max grade |
|---|---|---|---|
| 0 | 6,283 | **0.000** (0 exceptions) | **4** |
| 2 | 1,165 | 0.821 | 7 |
| 3 | 150 | 1.000 | 8 |

`nest_depth==0` caps grade at 4 with **zero** exceptions across 6,283 trades; **no** grade>=5 trade anywhere
has nest==0. So hi-tier is gated on nest>=2. The B1 bug (`extremes.py` writes EXT_H/EXT_L only for
**confirmed** pivots — `if p.confirm_idx is None: continue`, line 218 — so the anchor sits ~K·ATR *inside*
the true swing extreme) zeroes the nest for any entry that hugs the live extreme. This is the exact lever.

**Smoking gun:** every one of the 16 fired-but-low marks has `nest_depth==0`; every one of the 4 hi-grade
marks has `nest_depth==2`. Perfect separation on the very field B1 corrupts.

## 2) Fired-but-low (grade<5, n=16) — B1-clip test
`eraX` = era-high (short)/era-low (long) = the direction extreme; `dEraATR` = |eraX−entry|/ATR_local;
`dSwATR` = |swept−entry|/ATR_local; extMit = price-position ppX>=0.70; B1clip = dEraATR<=5.

| id | dir | g | out | sysR | ppX | dEraATR | dSwATR | extMit | B1clip |
|---|---|--|---|--|--|--|--|--|--|
| T_jan_short | s | 3 | stop | -1.0 | 0.87 | 1.90 | 1.43 | Y | Y |
| H_feb_short | s | 4 | **win** | 40.1 | 0.86 | 1.23 | 1.02 | Y | Y |
| H_nov_long | l | 2 | stop | -1.0 | 0.82 | 0.85 | 0.60 | Y | Y |
| D_nov_short | s | 1 | **win** | 3.4 | 0.82 | 1.33 | 0.89 | Y | Y |
| D_aug_short | s | 1 | **win** | 3.4 | 0.80 | 1.78 | 0.59 | Y | Y |
| H_apr_short | s | 1 | stop | -1.0 | 0.79 | 3.16 | 2.03 | Y | Y |
| H_feb_range | s | 4 | **win** | 12.2 | 0.78 | 4.05 | 1.45 | Y | Y |
| H_aug_short | s | 3 | stop | -1.0 | 0.78 | 1.70 | 1.13 | Y | Y |
| H_may_short | s | 3 | stop | -1.0 | 0.77 | 2.55 | 0.00 | Y | Y |
| H_jun_long | l | 3 | **win** | 50.5 | 0.76 | 2.87 | 1.54 | Y | Y |
| H_t14_short | s | 3 | stop | -1.0 | 0.75 | 2.73 | 1.42 | Y | Y |
| Da_jul_short | s | 2 | stop | -1.0 | 0.72 | 2.11 | 0.60 | Y | Y |
| **H_jul_short** | s | **4** | **win** | 40.1 | 0.68 | 2.99 | 1.13 | n | **Y** |
| H_jan_short | s | 3 | gap | -1.0 | 0.63 | 3.44 | 1.56 | n | Y |
| H_jun_short_b | s | 3 | stop | -1.0 | 0.63 | 3.85 | 0.45 | n | Y |
| H_old_short | s | 2 | gap | -8.6 | 0.68 | **5.85** | 5.27 | n | **N** |

- **B1-clip candidates (within 5 ATR of the direction extreme): 15/16.** Only `H_old_short` (5.85 ATR,
  an older 2024q4 higher-vol regime) sits outside. By distance to the *swept* liquidity level, 15/16 are
  within ~2 ATR and all 16 within 5.3 ATR — these are genuinely extreme-hugging mitigations.
- **Price-position extremes (ppX>=0.70): 12/16.** The 4 below (incl. H_jul_short at 0.68) still sit in the
  upper third of their era; they fail only because the normalized band penalizes wide eras — the ATR test
  (the one that maps to the bug) passes them. Lead with the ATR test.
- H_jul_short (the user's textbook +8R short) is the archetype: fires, WINS, but grade 4 / nest 0, entry
  2.99 ATR under the era-high and 1.13 ATR off the swept 1232 — squarely a B1-clip.

## 3) Promotion estimate — how many more marks become hi-grade winners
Promotion cohort = the 15 B1-clip candidates. Assume a B1 fix moves their nest 0→2 (the value every current
hi-grade mark shows); P(hi-tier | nest2, ote) = 0.82.

| | winners | losers | hit-rate | net sysR |
|---|--|--|--|--|
| current hi-grade marks (n=4) | 3 (H_jan_long, H_sep_short, Da_feb) | 1 (H_jun_short_a) | 75% | +34 |
| B1 promotion cohort (n=15) | 6 | 9 | 40% | **+140.5** (win +149.5 / loss −9.0) |
| **after B1 (discounted 0.82)** | **~8** (3+5) | ~8 | **~47%** | **~+175** |

- **Hi-grade WINNERS ~3 → ~8** (undiscounted 9): a ~2.7x lift. The 6 promoted winners are H_jul_short,
  H_feb_short, H_feb_range, H_jun_long, D_nov_short, D_aug_short — all far-target setups (mark planned RR
  6.5–35, tight structural stop) = the taught payoff shape.
- **RECALL up, PRECISION diluted.** B1 promotes the *whole* extreme-mitigation cohort, not just winners:
  6 winners AND 9 losers. Hi-tier mark hit-rate would fall 75% → ~47%. The 9 losers each stop at exactly
  −1R; the edge survives **only via R-asymmetry** (+149.5R winners vs −9R losers = +140.5R net), which is
  itself the taught far-target/tight-stop signature — not via hit-rate.

## 4) Skeptical caveats (do NOT over-claim)
1. **Promotion is UNVERIFIED.** No pipeline re-run (forbidden). nest 0→2 is inferred from the mechanism +
   the fact that all 4 hi-grade marks show nest=2; a fix could yield nest=1 or leave other grade terms
   binding. P(hi | nest2)=0.82, not 1.0 — 16% of nest-2 trades still grade 4.
2. **sysR is tiny-stop-inflated.** sysR 40–50 (H_jul, H_feb, H_jun_long) comes from the system's sub-mark
   stop (fill-through risk, per the falsified-fade lesson). At the marks' own planned RR the cohort is
   ~+39R net (6·~8R − 9·1R) — still strongly positive, but the +140R headline is inflated.
3. **B1 is a recall fix, not a precision fix.** It does not make hi-tier *more selective* on the marks; the
   non-required signals (sweep 67%, farRR 76–95% from the parent structural table) must do the discriminating.

## VERDICT
The B1 recall gap is **REAL and mechanistically pinned**: hi-tier is a hard nest_depth gate (nest0 → grade
<=4, n=6,283, 0 exceptions), and **15/16 fired-but-low marks — including the textbook H_jul_short — are
extreme-hugging mitigations (entry within 5 ATR of the swept/era direction-extreme, all nest=0) that the
confirmed-pivot-only EXT anchor demotes.** A B1 fix re-anchoring the nest would lift ~5–6 of the user's own
textbook setups into hi-tier, taking hi-grade winners ~3 → ~8 and adding large net-R. This **supports "it IS
the user's taught method, imperfectly graded — not a lookalike"**: the system already fires the right
extreme-mitigations and only the anchor bug keeps them out of the hi-tier. **But** the fix raises RECALL, not
precision (it promotes 9 losers alongside 6 winners, hit-rate 75%→~47%); its value is purely the taught
R-asymmetry, and the promotion itself is inferred, not re-run-verified.
