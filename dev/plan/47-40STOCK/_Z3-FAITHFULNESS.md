# 47-40STOCK — Z3 FAITHFULNESS: is the +6-7R edge the USER's taught method, or a lookalike? (2026-07-24)

Question: the deduped edge is real + regime-agnostic — but are the hi-grade WINNERS the user's own
taught setups (the 32 hand-marked trades, `tools/ytrades.json`), or profitable *lookalikes*? If lookalike,
the "it's YOUR method" framing breaks. Data: 32 marks {stock, month/day (NO year), dir, entry, sl, target,
swept, era} vs the 3 deduped tradebooks (2026/bull/bear).

## 1) STRUCTURAL faithfulness — hi-grade(≥5) eod WINNERS anatomy (deduped)
| tape | n | ote | nest>0 | sweep | phase | bos | farRR>3 |
|---|---|---|---|---|---|---|---|
| 2026 | 110 | 100% | 100% | 67% | 32% | 0% | 95% |
| bull | 296 | 100% | 100% | 67% | 47% | 0% | 76% |
| bear | 365 | 100% | 100% | 69% | 45% | 0% | 84% |

The winners are sweep→nested-zone-at-OTE→far-liquidity-target = the taught method.
**CAVEAT (tautology):** `decide()` REQUIRES premium/discount OTE + a decisional zone + a far runway, and
hi-grade requires a nest → so ote=100% / nest=100% are BY CONSTRUCTION, not evidence. The NON-required,
informative signals: **sweep 67%** (taught sweep-first), **farRR>3 76-95%** (taught far target), phase 32-47%.

## 2) INSTANCE co-location — 32 marks vs system trades (same stock+dir, entry within 2%; year-ambiguous)
**FIRED 20/32 · MISSED 12/32.** Fired detail (mark → tape/grade/outcome):
- WIN: H_jul_short@1221→2026 **g4** · H_jun_long@1141→2026 g3 · H_jan_long@1290→bull **g5** ·
  H_sep_short@1442→bull **g7** · H_may_short@1300→bull g3 · H_feb_short@1230→2026 g4 · H_apr@1332→bull g1 ·
  H_feb_range@1211→2026 g4 · D_nov@781→bull g1 · D_aug@778→bull g1 · Da_feb@520→bull **g6**
- loss: H_old@1910→bear g2 · H_nov_long@1245→bull g2 · H_aug@1330→bull g3 · H_jun_short_a@1363→bull g5 ·
  H_jun_short_b@1328→bull g3 · H_jan_short@1207→2026 g3 · H_t14@1375→bull g3 · T_jan@3510→bull g3 · Da_jul@448→2026 g2
- MISSED (12): H_570_long, V_jul_short, V_may_long, D_nov_long, T_jun_long, Da_jun_long, Da_nov_long,
  S_t28/29/30_long (SBICARD not in 40), SL_t31_short/long (SBILIFE not in 40).

### The money data point — the B1 recall-quality gap
**H_jul_short @1221** (the user's textbook mitigation short, +8R live) → system FIRES it, WINs, but only at
**grade 4 — NOT hi-tier.** The HAVELLS study (`45-HAVELLS`) already diagnosed why: the **B1 EXT-anchor bug**
caps the nest ~5 ATR below the true 1234 extreme, so the 1221 mitigation grades 4 not 6-7. The system SEES
the user's best setup but the anchor bug DEMOTES it below the hi-tier it deserves.

## HONEST READ (pre red-team)
- **STRUCTURAL: faithful** — winners are the taught setup type; the non-required signals (sweep 67%, far-RR
  76-95%) confirm it's not incidental.
- **INSTANCE: faithful-but-limited** — fires at 20/32 mark price-locations (year-ambiguous), the fired
  setups are the right type, but **B1 under-grades some of the user's best marked extreme-mitigations**
  below hi-tier. 12 misses are mostly out-of-tape-era / uncovered stocks, not true recall failures.
- **Verdict (tentative): NOT a lookalike — it IS the taught method, imperfectly graded (B1).** Fixing B1
  should PROMOTE the user's best marks into the hi-tier → likely raise, not lower, the edge.

## Open for the red-team
1. Is the structural table circular (ote/nest required)? What survives as real evidence?
2. Year-ambiguity: 20/32 co-location is price-coincidence — what's the NULL baseline (random grader's rate)?
3. B1-promotion: of the demoted marks (fired but <hi-grade), how many are extreme-mitigations that a B1 fix
   would promote to hi-tier? Quantify the edge upside.
