# 47-40STOCK — Z3 FAITHFULNESS VERDICT (synthesis of 3 red-team passes) (2026-07-24)

Synthesis of: `_Z3-FAITHFULNESS.md` (hypothesis), `z3_redteam.md` (adversarial), `z3_null_baseline.md`
(placebo test), `z3_b1_recall_gap.md` (mechanism). The question: are the hi-grade +6–7R WINNERS the
USER's own taught method, or profitable LOOKALIKES the grader rewards? The three passes converge more than
they read: redteam KILLS the structural + 2% co-location evidence as circular/chance; null-baseline confirms
2% is density but rescues a tight-band residual; B1 supplies the one externally-anchored fingerprint.

---

## 1) IS THE EDGE THE TAUGHT METHOD, A LOOKALIKE, OR UNDECIDABLE?
**Answer: UNDECIDABLE from this data — leaning "taught setup-TYPE yes, taught-specific-EVENTS unproven."**
Not proven to be the user's method; not proven to be a pure lookalike either. The redteam's flat "LOOKALIKE"
verdict OVERCLAIMS (its own words: "consistent-with-lookalike, *unproven*"); the honest-read's "it IS the
method" also overclaims. Confidence: **it's literally the user's own trades = LOW; it's the taught
setup-GEOMETRY = MODERATE; it's a disconnected lookalike = LOW.**

Evidence sorted by what it actually is:
- **TAUTOLOGICAL (zero information, by construction):** the ENTIRE structural anatomy table. `ote=100%` is a
  hard `decide()` gate on all 22,226 trades; `bos=0%` is constant; `nest>0` is the grade gate itself; `sweep`
  and `phase` are **monotone in grade = grade INPUTS**, so "sweep 67%" is baked in (g1=exactly 0%). The
  grader was BUILT to encode the taught method → its output tautologically resembles the method. The
  honest-read's claim that sweep/farRR were "non-required real signals" is FALSE.
- **CHANCE (indistinguishable from null):** the 20/32 co-location headline at 2% (see §2). And `farRR>3`,
  cited as the "taught far target," is a **flat universal present on grade-1 trash** and is actually an
  **ANTI-signal** — hi-grade LOSERS carry it MORE than winners in all 3 tapes (97>93, 95>71, 94>79).
- **REAL (survives adversarial pressure) — but thin:** (a) win-rate monotone in grade (13→46% / 30→56% /
  27→62%) = the EDGE, real but citing it as faithfulness is circular; (b) the **tight-band co-location
  residual** at 0.2–0.5% (p≈0.02, §2) — weak; (c) the **B1 mechanism + mark geometry** (§3) — the one
  externally-anchored pro-faithfulness signal, since the marks are the user's own ground truth.

The faithfulness test as posed is **UNFALSIFIABLE**: the taught method (sweep→nest@OTE→tight stop→far target)
maps 1:1 onto the grade inputs, so "hi-grade" IS the operational definition of "taught" — there is no
hi-grade trade the system could take that would be labelled "not the method." A test that cannot be violated
cannot pass. That is why the top-line is UNDECIDABLE, not a verdict either way.

## 2) NULL BASELINE — is 20/32 co-location real signal or chance?
**Largely CHANCE (tape-density artifact) at the cited 2% band.** Placebo (shuffle marks to random in-range
same-dir prices, 5000 iters): real 20 vs placebo **mean 16.5 / p95 20 / p≈0.10** — real sits AT the p95 edge,
INSIDE the null. HAVELLS alone carries 133 short entries blanketing 1200–1450, so at 2% tol almost any price
co-locates (band coverage 60–98% per stock+dir). **Downgrade the 20/32 headline — it is not evidence above a
random grader.** The ONLY defensible instance signal is the **tight-band residual: at 0.2–0.5% (20–50 bps),
real exceeds placebo-p95 with p≈0.02** — the user's marked prices sit closer to actual fills than random.
Real but weak, and it proves price-level proximity, NOT setup identity. Collapses at 0.1% (marks are round
numbers). Year-ambiguity compounds everything: a 2023-tape trade "matching" a possibly-different-year mark is
pure price coincidence.

## 3) B1 RECALL GAP — how many marks demoted, and does a fix raise edge + faithfulness together?
**15/16 fired-but-low marks are extreme-hugging mitigations the B1 anchor bug demotes** (entry within ~5 ATR
of the swept/era direction-extreme; **all 16 have nest_depth==0**; the 4 hi-grade marks all have nest==2 —
perfect separation on the exact field B1 corrupts). Mechanism is ROCK-SOLID: `nest_depth==0` hard-caps grade
at 4 with **0 exceptions across 6,283 trades**, and `extremes.py:218` writes EXT anchors only for *confirmed*
pivots, so the anchor sits ~K·ATR inside the true extreme and zeroes the nest for extreme-hugging entries.
The textbook **H_jul_short** (+8R live) is the archetype: fires, WINS, but grade 4 / nest 0.

Would a fix raise both? **Partly, and it's INFERRED not re-run.** A B1 fix (nest 0→2, P(hi|nest2,ote)=0.82)
lifts hi-grade WINNERS **~3 → ~8 (≈2.7×)**. BUT it raises **RECALL, not precision**: it promotes the whole
cohort — **6 winners AND 9 losers** — so hi-tier mark hit-rate FALLS 75%→~47%. The edge survives only via
**R-asymmetry** (+140R net headline, but sysR is tiny-stop-inflated per the falsified-fade lesson; at the
marks' own planned RR it's ~+39R net). So a B1 fix would **raise the edge (more taught setups captured, net
R up) and raise RECALL-faithfulness (stops demoting the user's own textbook extreme-mitigations) — but NOT
precision-faithfulness** (does not make hi-tier selectively the user's method). And the mark-link leans on
co-location, which §2 shows is chance-heavy at 2%; 83% of ALL trades are nest0, so "16/16 low marks = nest0"
is partly just the baseline.

## 4) THESIS + SHIP DECISION
**Faithfulness does NOT PASS (no green-light) and does NOT cleanly FAIL as "lookalike, re-frame." Honest
call: NEEDS MORE/BETTER (DATED) MARKS.** The current data is structurally incapable of deciding — circular
anatomy + chance 2% co-location + unfalsifiable definition. Actions: (i) **Keep the EDGE thesis** — it is a
SEPARATE, stronger finding (regime-agnostic, cost-surviving +R); it does not depend on faithfulness. (ii)
**Do NOT ship on the "it's YOUR method" framing** — that specific claim is unproven. Re-frame to the
defensible version: *"the system trades the taught setup-GEOMETRY (extreme-mitigation / OTE / sweep / far
target), which the user also trades; whether the specific +6–7R winners are the user's own events is
undecidable without dated marks."* (iii) **Fix B1 regardless** — the bug is code-real and demotes the taught
geometry; but VALIDATE by pipeline re-run (promotion is currently inferred), and expect recall-not-precision.

## 5) SINGLE MOST IMPORTANT FOLLOW-UP
**Get the YEARS on the 32 marks and recompute co-location with same-WEEK temporal alignment against a
temporal null.** That is the one test that can break the density/chance artifact and turn co-location from
price-coincidence into event-identity evidence — it is the pivot the whole verdict hinges on. Secondary, in
order: (b) verify swept-LEVEL identity (system's swept price == mark's `swept`, not just entry); (c) find ≥1
feature that separates hi-grade winners from hi-grade LOSERS and is NOT a grade input (without it, "winners
are taught" stays circular); (d) enlarge the dated mark set (>32; add SBICARD/SBILIFE to the 40 so the 12
misses become testable, not structural).

---

## 10-LINE VERDICT
1. Top-line: **UNDECIDABLE.** The system trades the taught setup-GEOMETRY, but whether the +6–7R winners are the user's OWN events vs profitable lookalikes cannot be decided from this data.
2. The whole structural "anatomy" table is **tautological** — ote/bos/nest are gates, sweep/phase are grade inputs; it is zero independent evidence.
3. `farRR>3` is not a winner signature — it's a flat universal and an **anti-signal** (hi-grade losers carry it MORE than winners in all 3 tapes).
4. The 20/32 co-location at 2% is **chance** (placebo mean 16.5, p≈0.10) — a tape-density artifact, not faithfulness. Downgrade it.
5. Only a **tight-band residual (0.2–0.5%, p≈0.02)** survives: marks sit nearer actual fills than random — real but weak, and it's price-proximity, not setup identity.
6. The test as posed is **unfalsifiable**: hi-grade IS the operational definition of "taught," so it cannot be violated and cannot truly pass.
7. The **B1 gap is real and mechanistically pinned**: nest0 hard-caps grade at 4 (0/6,283 exceptions); 15/16 fired-but-low marks — incl. textbook H_jul_short — are extreme-mitigations demoted by the confirmed-pivot-only EXT anchor.
8. A B1 fix would take hi-grade winners ~3→~8 and raise net R + **RECALL** faithfulness — but it raises recall NOT precision (promotes 6 winners + 9 losers, hit-rate 75%→~47%), the edge survives only via R-asymmetry, and the promotion is **inferred, not re-run-verified**.
9. Ship call: faithfulness **does not green-light**; keep the (separate, stronger) regime-agnostic EDGE thesis, drop the "it's YOUR method" framing for "it's the taught GEOMETRY," and fix+re-run B1.
10. The one follow-up that decides it: **get the marks' YEARS → recompute co-location on same-week temporal alignment vs a temporal null;** without dated marks, faithfulness stays undecidable.
