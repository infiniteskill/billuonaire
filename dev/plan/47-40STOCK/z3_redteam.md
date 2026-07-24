# 47-40STOCK — Z3 FAITHFULNESS RED-TEAM: the +6-7R edge is a LOOKALIKE, not proven to be the user's method (2026-07-24)

Default-skeptical adversarial pass on `_Z3-FAITHFULNESS.md`. Reproduced from the 3 deduped tradebooks
(dedup by sym,entry,sl,target: 2026 n=3053 / bull 8123 / bear 11050 logical trades) + 32 marks
`tools/ytrades.json`. Reproduction OK: my ALL-hi(≥5) sweep 66/65/70% and farRR>3 94/78/86% match the
`.md` structural table's 67/67/69% and 95/76/84% — so the critique below runs on the SAME numbers.

## VERDICT: LOOKALIKE. Faithfulness is NOT established.
Every column in the "anatomy" table is either a hard gate on 100% of trades, a grade INPUT, or a
non-discriminating universal. The one non-circular test — co-location vs a null — lands **exactly at
chance**. Nothing shown separates "the user's taught method" from "any OTE+sweep fade the grader rewards."

---

## 1) TAUTOLOGY — every anatomy column collapses (n=43,185 raw / 22,226 deduped rows)
| feature | what it actually is | verdict |
|---|---|---|
| **ote=100%** | `True` on **ALL 22,226** deduped trades (hard `decide()` gate) | zero information — losers, grade-1 trash, everything is "at OTE" |
| **bos=0%** | `False` on **ALL** trades | constant — zero information |
| **nest>0** | 0% at grade≤3 → **100% at grade≥5** (step gate) | grade-REQUIRED by construction |
| **sweep** | **monotone in grade**: g1=0%, g2=41%, g3=68%, g6=76%, g7=88-100% (all 3 tapes) | sweep is a **grade INPUT**, not an independent signal — "sweep 67%" is by construction |
| **phase** | also monotone in grade (0.0 at g1 → ~1.0 at g7) | grade input, not independent |
| **farRR>3** | **flat 80-95% across EVERY grade** incl. grade-1 (2026 93%, bull 84%, bear 86%) | universal far-target rule — present on the throwaway trades too; **not a hi-grade property at all** |
| **win-rate** | the ONLY thing that tracks grade (13%→46%, 30%→56%, 27%→62%) | this is the edge — but citing it as "faithfulness" is circular |

The honest-read named sweep and farRR>3 as the "NON-required real signals." Both fail: sweep IS baked
into grade (monotone, g1=exactly 0%), and farRR>3 is a flat universal that grade-1 garbage has in equal
measure. **No column is independent evidence that hi-grade winners are the USER's setup.**

## 2) DISCRIMINATOR — winners vs losers vs grade-1 trash (do the "signals" separate taught-vs-not?)
| tape | seg | sweep | farRR>3 |
|---|---|---|---|
| 2026 | hi WIN | 74% | 93% |
| 2026 | hi **LOSS** | 56% | **97%** |
| 2026 | grade-1 trash | 0% | 93% |
| bull | hi WIN | 68% | 71% |
| bull | hi **LOSS** | 56% | **95%** |
| bear | hi WIN | 69% | 79% |
| bear | hi **LOSS** | **72%** | **94%** |

- **farRR>3 is an ANTI-signal**: losers carry it MORE than winners in all 3 tapes (97>93, 95>71, 94>79).
  The "taught far target" does not distinguish winners; it's just where the target rule points.
- **sweep separation is weak + tape-flipping**: WIN−LOSS = +18 / +12 / **−3** pp. In the bear book
  losers sweep more than winners. And it's a grade input anyway, so it cannot be independent evidence.
- Winner-anatomy ≈ loser-anatomy on the cited signals. The features do NOT discriminate the taught setup
  from a losing OTE+sweep fade — they only describe what `decide()` emits.

## 3) FALSIFIABILITY — the claim is unfalsifiable as posed
Taught method (memory) = sweep an extreme → nested zone at OTE → tight stop → far target. That maps 1:1
onto the grade inputs: sweep→grade, nest→grade gate, OTE→100% gate, far target→farRR. **There is no
hi-grade trade the system could take that would be labelled "not the taught method"** — hi-grade IS the
operational definition of "taught." Loose form ("fade at an extreme" = sweep+OTE) matches **~45% of ALL
trades** (ote=100%, sweep≈45% overall), including the losers. A definition that admits half the book —
and cannot be violated — is not testable faithfulness.

## 4) CO-LOCATION IS AT CHANCE — the decisive test (kills the 20/32 headline)
NULL: draw a random price in each mark's own era band [lo,hi]; what fraction land within 2% of SOME
system entry (same sym+dir)? That is the rate a *random grader* would "co-locate."

- **Actual fired 20/32 = 62%** (in-universe 20/27 = **74%**).
- **NULL random-price coverage: mean 71%, median 74%** (in-universe).
- **Above chance ≈ 0.** 74% actual vs 71% null. The 20/32 co-location is indistinguishable from random.
- **Why**: HAVELLS carries **133 distinct short entries** blanketing 1200-1450; at 2% tol the WHOLE band
  is within reach of some entry → null = **100%** for most HAVELLS marks. Co-location is guaranteed by
  trade DENSITY, not setup match. Reverse check: 55% of all 133 HAVELLS-short system trades sit within 2%
  of some mark — the marks blanket the band too. Both sides just crowd the same obvious liquidity range.
- Year-ambiguity compounds it: a system trade in the 2023 bull tape "matches" a mark that may be a
  different year — pure price coincidence, not the same event.

## 5) THE "MONEY" MARK COLLAPSES — H_jul_short @1221
`.md` framing: "system FIRES it, WINs at grade 4, B1 bug demotes it below hi-tier." Reality at 1197-1245
HAVELLS short: the system takes **6 trades, grades 1/3/4 (none hi), outcome 3 target / 1 stop / 2 gap =
~breakeven**. It is not a +8R winner the grader under-ranked; it's a low-grade scatter that does NOT
reproduce the user's outcome. "The system sees your best setup" overstates a mediocre cluster at a
year-ambiguous price band.

## 6) SURVIVORSHIP — strongest case it's a lookalike
The 32 marks are trades the USER hand-picked as WINNERS. Co-location at those prices proves only that both
the user and a dense mean-reversion book crowd the same obvious equal-H/L bands — which the null confirms
is inevitable. Consistent-with-lookalike, unproven-as-method: (a) anatomy = grade inputs (circular),
(b) co-location = chance, (c) definition unfalsifiable, (d) the flagship mark isn't even reproduced.
To BREAK the lookalike you would need evidence co-location can't fake: same swept-level identity, same
nested-zone object, dated (year-known) event alignment, and a signal that separates winners from losers
and is NOT a grade input — none of which exists in the current tables.

## What would actually prove faithfulness (falsifiable tests to run next)
1. Year-dated marks → require same-week temporal alignment, not just price ±2%. Recompute co-location
   above the temporal null.
2. Find ≥1 feature that (a) separates hi-grade winners from hi-grade losers AND (b) is not a grade input.
   Without it, "winners are taught" is circular.
3. Verify the system's swept-level == the mark's `swept` price (structural identity), not just entry.
4. Re-state the taught method as a predicate the system CAN fail, then show hi-grade trades that fail it.
