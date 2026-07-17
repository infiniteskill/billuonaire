# Idea Ledger — Hypotheses Awaiting Validation (living doc)

**Rule: nothing here touches production detectors until it clears the bar in
`15-VALIDATION-METHODOLOGY.md`.** Current production = original detectors + the
execution bug-fixes (limit-fill, cost-viable stops, effective-R, STT sell-only) which
are VALIDATED (0→9 trades, cost drag 7R→0.23R) and stay. Everything below is an IDEA.

Status: `proposed` → `validating` → `validated(OOS)` → `applied` | `rejected` | `parked`.

## From the 64k-evidence study (ONE month, partly in-sample — must re-clear on holdout)

| # | Hypothesis | Evidence so far | Status | Bar to clear |
|---|---|---|---|---|
| S1 | sweep quality → `0.45 + 0.30·fade_setup` (against 60m drift AND ≥105min) | top tier +11.2% OOS(time) n=1633 | proposed | cross-sectional + bootstrap CI>0 |
| S2 | sweep reclaim-upgrade emits at BASE strength (drop +0.1) | upgrade +0.1% vs base +10.7% | proposed | low-risk; still confirm |
| S3 | structure weight 15→0 (context/direction only) | BOS/CHoCH −22%/−20% both splits; LuxAlgo bar-0 confirms inherent | proposed | strong; confirm no template harm |
| S4 | liquidity weight 10→0 (POOL_NEAR targets only) | pool-strength corr ~0 | proposed | confirm |
| S5 | breaker strength 0.85→0.5, weight 10→5 | −9%/−6.8% both splits | proposed | confirm; against-move slice only? |
| S6 | FVG CE_HOLD graded strength (gap/fill/counter-drift) | +12.7/+14.1% OOS(time) | proposed | our best; cross-sectional |
| S7 | FVG iFVG dead-path bug fix (DEAD races INVERTED) | n=0 in 64k — never fired | proposed | BUG — fix + measure the now-live signal |
| S8 | OB quality rewrite (disp + inverse-body + inverse-body_pct; drop hunt +0.15) | body terms inverted; hunt falsified | proposed | cross-sectional |
| S9 | OB exhaustion penalty −0.2 when aligned with >0.5×ATR 30m move | with-move OB −11%/−2.6% | proposed | confirm |
| S10 | wyckoff params 30/4.0/1.25/upper-third + session-open/last-bar guard | SPRING +23%, UPTHRUST +32% OOS(time) n≈169/mo | proposed | cross-sectional; n still modest |
| S11 | cut VSA +3 booster except fvg-confirmed | VSA degrades every family but fvg | proposed | confirm |
| S12 | timestats priors flatten [.55/.50/.45/.45/.55], prior_weight 20→10 | measured danger curve far flatter | proposed | confirm |
| S13 | compression/PO3 weight 12→0 (PO3_DIST −15..29% even loosened) | park; structurally late | parked | redesign entry (manipulation-reclaim) before revisit |
| S14 | BOX_ON_LEVEL zero-weight | −3.7/−1.1% n=956 | proposed | confirm |

## From the Pine reference comparison (theory-backed, UNMEASURED on our data)

| # | Hypothesis | Rationale | Status | Bar to clear |
|---|---|---|---|---|
| P1 | **Premium/Discount gate** (reject longs in top-5% swing range, shorts in bottom) | LuxAlgo canonical + study "against-move carries all edge" | proposed | MEASURE edge as a filter first, then holdout |
| P2 | Vol-adjusted OB anchor (swap H/L on ≥2×ATR bars; extreme-of-leg, size 8) | **VALIDATED 2 axes**: +10.4% vs our +4.4%; temporal val +9.3%, x-sect both stock-sets +10.1/+10.8% (`16-OB-VALIDATION.md`) | **validated(OOS, 2 axes)** | remaining: bootstrap CI + portfolio replay + forward month |
| P3 | FVG requires displacement bar CLOSE-beyond + adaptive body-% threshold | LuxAlgo stricter FVG | proposed | measure edge lift on our best detector |
| P4 | EQH/EQL tolerance → ATR-relative (0.1×ATR) | LuxAlgo; ours over-groups high-priced | proposed | measure EQ-sweep edge before/after |
| P5 | Volume-in-zone liquidity strength (Liquidity Swings) | replaces useless touch-count | proposed | does volume-strength predict? measure |
| P6 | Strong/Weak High/Low tagging (trend-relative wall vs draw) | sharper targets + sweep direction | parked | design later |

## Earlier deferred (from gap audits — engineering, not signal science)

| # | Item | Status |
|---|---|---|
| E1 | Broker ABC extraction (Phase-6 blocker) | proposed |
| E2 | cage/options detector (needs Kite OI) | parked (Phase 6) |
| E3 | Position/RiskState persistence (crash recovery) | proposed (live phase) |
| E4 | NSE holiday calendar | proposed |
| E5 | M2/M4 decision-TF | parked (study said not the constraint) |

## The overriding risk
Every S-row was tuned on ONE regime (rangebound Jun–Jul 2026, contiguous split). The
"validation" split shared that regime. **Cross-sectional (stock-holdout) + longer-coarse
(15m/2yr) + forward-accrued fresh days are the real tests.** Until an idea clears those,
it stays here.
