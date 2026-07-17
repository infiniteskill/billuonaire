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
| S3 | structure weight 15→0 (context/direction only) | **CONFIRMED both defs anti: ours −18.6%, LuxAlgo −17.1%, all splits** — concept not code | validated(OOS,2axes) | portfolio replay |
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
| S15 | INVERT level strength: fade FRESH (low-touch) levels, penalize heavily-touched | measured high-touch sweep −10.6% vs low-touch +6.5% (17pt spread) | proposed | confirm on production sweep + holdout |

## From the Pine reference comparison (theory-backed, UNMEASURED on our data)

| # | Hypothesis | Rationale | Status | Bar to clear |
|---|---|---|---|---|
| P1 | **Premium/Discount gate** (buy discount/sell premium) | **TESTED: +3.3% standalone, holdout-stable** (16-OB-VALIDATION) — modest; best as a filter on other signals | validating | test as GATE on armed signals, portfolio replay |
| P2 | Vol-adjusted OB anchor (swap H/L on ≥2×ATR bars; extreme-of-leg, size 8) | **VALIDATED 2 axes**: +10.4% vs our +4.4%; temporal val +9.3%, x-sect both stock-sets +10.1/+10.8% (`16-OB-VALIDATION.md`) | **validated(OOS, 2 axes)** | remaining: bootstrap CI + portfolio replay + forward month |
| P3 | FVG: adopt CLOSE-BEYOND requirement (dedicated LuxAlgo FVG) | **TESTED: WINS** — lux-dedicated retest +6.7 vs ours +2.7 (M5), +12.3 vs +8.7 (M10); close-beyond filter is the ingredient | validating | portfolio replay |
| P4 | EQH/EQL tolerance → ATR-relative | **TESTED: mild win** (−3.0 vs −5.5% on naive sweep, both axes) | validating | confirm on production sweep |
| P5 | Volume-in-zone liquidity strength | **TESTED: doesn't help** (high-vol −5.0 vs low-vol −1.1). BUT touch-count is INVERTED (high −10.6 / low +6.5) — fresh levels win | rejected(volume); NEW S15 (invert touches) |
| P6 | Strong/Weak High/Low tagging (trend-relative wall vs draw) | sharper targets + sweep direction | parked | design later |

## Earlier deferred (from gap audits — engineering, not signal science)

| # | Item | Status |
|---|---|---|
| E1 | Broker ABC extraction (Phase-6 blocker) | proposed |
| E2 | cage/options detector (needs Kite OI) | parked (Phase 6) |
| E3 | Position/RiskState persistence (crash recovery) | proposed (live phase) |
| E4 | NSE holiday calendar | proposed |
| E5 | Decision-TF | **TESTED multi-TF: edge GROWS with TF; M10-M15 sweet spot** (OB +13.8% M15, FVG +12.4% M10, cost-viable stops). Go SLOWER not faster. Big rebuild candidate | validating(strong) | portfolio replay at M10/M15 |

## The overriding risk
Every S-row was tuned on ONE regime (rangebound Jun–Jul 2026, contiguous split). The
"validation" split shared that regime. **Cross-sectional (stock-holdout) + longer-coarse
(15m/2yr) + forward-accrued fresh days are the real tests.** Until an idea clears those,
it stays here.
