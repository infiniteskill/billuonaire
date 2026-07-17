# Head-to-Head: Pine (LuxAlgo) concept defs vs Ours (2026-07-17)

All measured identically (study `outcome`/`baseline`; retest-into-zone event where a
zone applies; temporal split derive/validate + cross-sectional stock-set A/B holdout).
Scripts: scratchpad `luxob.py`, `h2h.py`.

## Full head-to-head summary (edge = hit% − time-bucket random baseline)

| Concept | Ours | LuxAlgo | temporal val (ours/lux) | x-sect A/B (lux) | Verdict |
|---|---|---|---|---|---|
| **Order Block** | +4.4% | **+10.4%** | +4.3 / +9.3 | +10.8 / +10.1 | **ADOPT LuxAlgo** (2.4×, both holdouts) |
| **FVG** (same retest rule) | +2.4% | +2.8% | +3.4 / +3.6 | +2.7 / +2.8 | **TIE — keep ours.** Gap def barely matters; FVG edge lives in the CE-hold event (+8.8% in study), not the gap criteria |
| **Structure BOS/CHoCH** | −18.6% | −17.1% | −18.4 / −17.1 | −16.8 / −17.5 | **BOTH anti-signal** — inherent to SMC, not our bug. Demote structure to context/direction-only (confirms S3) |
| **Premium/Discount** (buy discount / sell premium, tight f=.15) | — (we lack it) | +3.3% | val +2.5 | +3.4 / +3.3 | **NEW, modest, holdout-stable.** Fade-extension as a positional FILTER, not standalone entry |

Reads: OB is the one decisive definitional win. FVG's value is the event rule we already
have, not LuxAlgo's stricter gap. Structure is a dead entry-signal by concept (both
implementations). Premium/Discount confirms the fade-extension law positionally — best as
a gate on other signals.

---

# Order Block detail — LuxAlgo (Pine) vs Ours

User trusted the LuxAlgo Pine OB visually. Tested it head-to-head on our real month
(20 NIFTY stocks × 19 sessions M5), scored with the IDENTICAL study machinery
(`outcome`/`baseline` from `tools/study.py`: hit = MFE≥1×ATR before MAE≥1×ATR vs
time-bucket random baseline). Script: scratchpad `luxob.py`.

## Result — LuxAlgo OB wins ~2.4×, and survives BOTH holdout axes

| Method | overall edge | temporal der→val | cross-sect A / B | n |
|---|---|---|---|---|
| Ours (last-opposite candle + quality score) | +4.4% | +4.5 → +4.3 | +4.5 / +4.3 | 3804 |
| **LuxAlgo size=5** (vol-adj leg extreme) | +8.9% | +9.4 → +8.5 | +10.5 / +7.3 | 1569 |
| **LuxAlgo size=8** | **+10.4%** | +11.7 → +9.3 | +10.8 / +10.1 | 1038 |

Both methods are STABLE across splits (ours ~+4.4 everywhere, Lux ~+9-11 everywhere) —
so both are real, but LuxAlgo carries ~2.4× the edge. **This is the first idea in the
project to clear cross-sectional (unseen-stock) holdout — the hardest gate.**

## Why LuxAlgo's OB is better (algorithm diff)
- **Anchor**: the volatility-adjusted EXTREME candle of the impulse leg (min parsed-low
  for a bullish OB, from the broken swing pivot to the break bar), NOT our "last opposite
  candle before displacement".
- **Spike exclusion**: on bars with range ≥ 2×ATR it SWAPS high/low (`parsedHigh = low`),
  so violent spike bars can never anchor an OB. This is exactly why our study found "small
  subtle OBs win" — Lux structurally excludes the volatile ones our quality score rewarded.
- **No quality score**: OB exists until mitigated (price low < OB low for bull). Our
  quality formula was measured inverted (body terms backwards, hunt bonus falsified).
- Tied to a real structure break (crossover close of an internal swing pivot, size 5–8).

## Validation status (per 15-VALIDATION-METHODOLOGY.md)
- [x] Temporal holdout — PASS (+8.5 to +9.3% on validate days)
- [x] Cross-sectional stock holdout — PASS (both unseen stock-sets +7.3 to +10.8%)
- [ ] Block-bootstrap CI (whole-stock-day resample) — not yet run
- [ ] Economic significance (portfolio replay net-R vs frozen baseline) — not yet run
- [ ] Forward-accrued fresh month — pending data

**Verdict: strongest-validated idea so far.** Cleared the two hardest gates. Ledger P2
promoted `validating → validated(OOS, 2 axes)`. Recommend implementing the LuxAlgo OB
anchor (size 8) to REPLACE our OB anchoring + quality score, then confirm at portfolio
level on the cross-sectional holdout stocks before committing to production weights.

## Caveat
One 2026 window, 20 survivor-selected liquid names. "Validated" = validated on THIS.
Forward accrual still required before treating as proven. But 2-axis holdout stability
is a genuinely strong signal — much stronger than anything tuned on the time split alone.
