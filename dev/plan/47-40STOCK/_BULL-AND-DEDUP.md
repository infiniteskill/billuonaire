# 47-40STOCK — BULL TEST (Z2) + THE DEDUP CORRECTION (2026-07-24)

## Z2 — the bull adversarial test PASSES (frozen config, unseen tape)

Tape: `data/regime_bull` = 2023-11-01..2024-01-31, **+22.4% median drift, 31/40 UP** (mirror of the
2024-Q4 bear). The single fragility the edge-preserve rethink flagged ("low-oscillation bull melt-up →
far target stops filling → the RR harvester deflates"). Frozen config, sharded derive (`derive_parallel`,
verified == serial).

RAW hi-tier (grade≥4): intrabar **+7.82R/61%**, m5_close **+7.66R/63%**, **eod +8.80R/74%** — all 4
holdout quads +, grade ladder monotone out-of-sample (g1/g2 neg → g5 +10.6 → g7 +13.1R).

**Three regimes now pass with the ONE frozen config** (raw eod hi-tier): 2026-mixed +6.53R · 2024-Q4-bear
+8.07R · 2023-bull +8.80R.

## BUT — the dedup correction (scrutiny of the "too good" bull number)

The bull eod hi-tier looked short-dominated (SHORT +10.54R/80% vs LONG +9.10R) — shorts *best* in the
most-bullish tape is backwards. Investigation:
- Data clean (1/40 has a >12% gap; not systemic).
- **~70% of trades are DUPLICATES** — the same zone re-fires 2-3× within the gate window (COFORGE
  1031.2/1032.5/1013.5 at 10:50 AND 11:45; BAJFINANCE 739/740/737.8 ×3 in 40min). Counted independently.
- A **tinyRR** subset (target <2R away, `_runway` picks the nearest far extreme which is sometimes very
  near) trivially hits and pads win%.

### Deduped by unique (sym,entry,sl,target), eod grade≥5:
| tape | RAW net/win | DEDUP net/win | dup% | uniq n |
|---|---|---|---|---|
| 2026-mixed | +8.18R/74% | **+7.46R/69%** | 69% | 177 |
| 2023-bull | +10.26R/79% | **+6.47R/71%** | 74% | 459 |

### Where the edge lives — RR bucket (deduped):
| RR | 2026 | bull |
|---|---|---|
| tinyRR <2 | +0.12R | **−1.43R** (noise/neg) |
| midRR 2-5 | +0.11R | +0.97R |
| **farRR >5** | **+8.50R (n155, 70%)** | **+9.44R (n318, 69%)** |

## HONEST re-statement of the edge

1. **The edge is REAL and regime-agnostic** — survives dedup AND the bull tape. Deduped far-RR ≈ **+8.5R
   mixed / +9.4R bull, ~70% win**. Three regimes hold.
2. **The headline +8R was ~40% CLUSTERING-INFLATED.** True per-unique-setup edge ≈ **+6.5–7.5R eod**.
   Corrects BREAKTHROUGH-3's magnitude (was quoting raw +8.20R).
3. **The holdout claim needs re-checking deduped** — duplicates of one setup all land in the same
   quadrant, so raw "all-4-quads +" overstates independence. **Deduped holdout quads = the real test
   (pending).**
4. **Shorts-in-bull is NOT a bug** — intraday fade-shorts at swept highs → far lower liquidity, tagged on
   intraday pullbacks + eod squareoff; stocks trended up over 3mo but had ample red intraday legs. Deduped
   it's 69%, not the inflated 80%.

## TWO discoveries → actions
- **DEDUP** (measurement + pipeline): one entry per zone. The A/B harness + all reported numbers must
  dedupe by default; the pipeline should enforce one-entry-per-zone (production reality).
- **min-RR gate**: RR<2 is net-neutral/negative and not the taught setup. Gate on RR≥~3 → sharpens edge +
  de-inflates win%. Pure filter, A/B in seconds.

## Reordered plan (post-dedup)
1. **Deduped 3-regime holdout re-baseline** (the decider) — recompute hi-tier + 4 quads deduped, all 3
   tapes. Re-derive 2024-Q4 for its CSV (pre-instrument, no CSV yet; parallel ~15min).
2. **min-RR gate A/B** (edge-safe, seconds).
3. **Harness dedup mode** (gate baseline moves to deduped frame).
4. Then Z3 faithfulness, Z4 walk-forward, G3-G6.
