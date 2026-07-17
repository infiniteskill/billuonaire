# 26 — Deep Audit + Validation Findings (2026-07-17)

Result of the deep pass: 4 adversarial code audits + 2 validations (confluence-lift, RR) +
the 50-stock in-framework study. This is the honest state of truth. Governing law still holds:
**scratchpad edges ≠ framework edges; the clean 50-stock in-framework number is truth.**

## A. VALIDATION RESULTS

### A1. 50-stock in-framework accuracy (hit = MFE≥1ATR before MAE≥1ATR, edge vs same-bucket random)
6 of 7 v2 detectors clear temporal + cross-sectional holdout (all splits positive):
inducement **+11.8%**, turtle_soup +9.2%, compression_fade **+8.4%** (n=12787), mitigation +8.4%,
fvg_cb CE-hold +8.3%, ob_lux +5.9%, bpr +3.5%. Drop: fvg_cb RETEST (xB −0.1%, unstable).
Confirmed losers (same run): structure CHoCH/BOS −20%, breaker −7%, PO3 −15%.
**CAVEAT (audit A-h below):** these were measured with ALL 19 detectors enabled (shared-level
contamination) AND pre session-boundary-fix. The 5 signal-emitters are state-independent so their
numbers hold; ob_lux/fvg_cb + all numbers get a clean re-measure (v2-only + F-fix).

### A2. CONFLUENCE DOES NOT LIFT EDGE — leak-free, holdout-validated (the big one)
- The apparent "stacking lifts" is a **look-ahead artifact**: a signal only looks confluent because
  confirmers fire 1–3 bars AFTER it. Causal (backward-only) it vanishes.
- Causal: the FIRST detector at a zone is already at full edge (+0.095); k≥2 = +0.084; edge DRIFTS
  DOWN with more tests (a repeatedly-tested zone is a WORSE entry). e(k≥2)−e(k=1) = −0.010, neg in
  all 4 holdouts.
- Weighted score: flat, top tercile LOSES to best single (inducement +0.126). Pairing a strong
  detector DILUTES it (inducement +0.188 solo → +0.10 co-fired).
- Only holdout-stable pair: fvg_cb+mitigation +0.09 (small n=69) — rescues weak fvg_cb, doesn't boost strong.
- **THE ONE REAL LEVER — direction filter:** align with prevailing wyckoff-PHASE direction →
  56.2% hit vs 44.5% counter (+11.7pt, +0.029 edge, stable all 4 holdouts).
- **DESIGN CONSEQUENCE:** NOT a confluence-count/weighted-stack engine, NOT "≥2 confirmers".
  Trade ELITE detectors solo at full weight + a hard direction filter + fresh-zone weighting.

### A3. RR/expectancy (sniper signals, meta["sl"] tiny SL, EOD-truncated, holdout-stable)
| detector | n | win@3R | exp@3R | exp@5R | holdout |
|---|---|---|---|---|---|
| **bpr** | 495 | 33% | **+0.33R** | +0.25 | stable ✅ |
| **compression_fade** | 12787 | 31% | **+0.25R** | +0.07 | stable ✅ (= scratchpad +0.26R) |
| inducement | 947 | 22% | −0.13R | −0.36 | stable NEGATIVE ❌ |
| mitigation | 3288 | 22% | −0.14R | −0.33 | stable NEGATIVE ❌ |
| turtle_soup | 611 | 15% | −0.39R | −0.49 | stable NEGATIVE ❌ |

**CRUX — HIT-EDGE ≠ RR.** inducement has the BEST hit-edge (+11.8%) but NEGATIVE 3R RR: its
wins are too small vs the tiny SL to pay 3R. Only **compression_fade + bpr** are profitable 3R
sniper signals. inducement/turtle_soup/mitigation have real hit-edge → must be monetized at a
QUICK target (~1–1.5R) or used as direction/context, NOT held for 3R. (compression_fade decays
past 3R: exp@5R only +0.07 → ~3R target is its peak.) NOTE: executor doesn't honor meta["sl"]
yet (C-1) so this is POTENTIAL RR motivating the SL-wiring; and it's pre-F-fix (re-measure after).

### A4. Emergent system (what the DATA supports — not the initial confluence-engine vision)
- **RR sniper core:** compression_fade + bpr (tiny SL, ~3R, positive holdout-stable expectancy).
- **Hit-edge signals:** inducement/turtle_soup/mitigation/fvg_cb/ob_lux → quick-target (~1–1.5R)
  exit to monetize hit-edge, or direction/context; NOT 3R.
- **Direction filter (wyckoff-PHASE align): +11.7pt — apply to all.**
- **No confluence stacking** (proven not to lift causally).
- The combination grid (§C) now must sweep detector × filter × **exit-target** to find each signal's best config.

## B. CODE AUDIT — real bugs (ranked)

| # | sev | where | bug | status |
|---|---|---|---|---|
| A-h | CRIT | study.py:120 | force-enables all 19 detectors → shared ctx.levels contamination (ob_lux+orderblock double OB pool; inflates volume/sweep). Numbers reflect 19-detector soup. | FIXED: `--only` added; v2-only re-run in flight |
| B-1 | CRIT | levels.py + pipeline._end_session | LevelEngine memories (_since_swept/_pending_break/_pending_invert/_prev_close/_round_side) never reset at session boundary → day-2 first bar emits RECLAIMED treating overnight as "1 candle"; determinism break | fixer in flight |
| B-2 | CRIT | pipeline._end_session/_fill_pending | EOD/exit can fill against NEXT day's open on a feed gap → overnight risk + misstated P&L; breaks "no overnight" | fixer in flight |
| C-1 | CRIT | entry.py + 5 detectors | executor does NOT honor meta["sl"]; real stop = generic ATR/zone + min_stop_atr=1.0 floor → measured tiny-SL RR NOT achievable until wired (Wave-3) | Wave-3 SL-wiring |
| C-2 | CRIT | orderblock._upsert / fvg.detect | baseline orderblock↔ob_lux and fvg↔fvg_cb MUTUALLY delete/DEAD-stamp each other's Level state (no owner filter) | v2 config MUST drop baseline orderblock+fvg |
| D-1 | CRIT | compression_fade/turtle_soup/bpr/mitigation | session-boundary window exposure: `.last()` mixes yesterday+today candles at session start (turtle_soup first ~1.7h daily) → distorts edges | fixer in flight (→ re-measure) |
| E-1 | IMP | entry.arm() | ZeroDivisionError when ATR None + zero-width zone → crashes pipeline | fixer in flight |
| E-2 | IMP | config free-rider | v2 name in detectors.enabled without confluence.weights entry → weight-0 but counts toward `distinct` (min_zone_detectors) → free-rider unlocks zones | Wave-3 config (moot if not stacking) |
| F | IMP | meta contract | sl/entry/sl_floor/os write-only, inconsistent (only compression_fade has entry/sl_floor; inducement buffers ±tick; os redundant) | standardize with SL-wiring |
| G | IMP | multiplicity | bpr/mitigation/ob_lux multi-emit per tick across non-merged zones → trade-count inflation | dedupe before execution |

CONFIRMED CLEAN by audit: M1→M5 no-lookahead, hit/EOD-truncation/baseline mechanics (numbers not
leaked, only contaminated), cost accounting (sell-side STT), limit-fill realism (no chase), level
state-machine transitions, the 5 signal-emitters don't touch ctx.levels.
NOTE: there is **no M10 timeframe** in the code (M5/M15/H1/D1) — plan's "M10 decision-TF" → M15.

## C. COMBINATION / PERMUTATION PLAN (user: "check each combination permutation, which work together best")
Stacking proven NOT to lift causally (A2), and RR≠hit-edge (A3), so the grid has THREE axes:
**detector × filter × exit-target**.
1. **Base:** each detector's solo causal edge AND RR-expectancy (both metrics), holdout.
2. **× EXIT-TARGET** (the A3 lever): sweep target ∈ {1R,1.5R,2R,3R,5R,MFE-trail} per detector — find
   each signal's best exit (compression_fade/bpr → ~3R; inducement/turtle_soup/mitigation → ~1–1.5R?).
3. **× FILTER** — full matrix, each filter's Δ(edge, expectancy) per detector:
   filters = {wyckoff-PHASE align (the proven +11.7pt lever), premium/discount, fresh>obvious zone,
   kill-zone/time-of-day, HTF trend, volatility regime, per-stock cleanliness}.
4. **× filter-pairs/triples** — do filters COMPOUND (direction+fresh+time) or saturate?
5. **Detector-pair co-fire** (re-confirm A2 on clean data) + **sequence** (A→B causally) — expect ~none.
Output `runs/val50/combos.md`: ranked best (detector, exit-target, filter-set) configs by causal
holdout expectancy. RUN ON CLEAN DATA ONLY (v2-only + F-fix) — contaminated/pre-fix evidence misleads.

## D. EXECUTION ORDER (remaining)
1. Land fixers (B-1/B-2/E-1 engine safety; D-1 session-boundary) → merge → suite green.
2. FINAL clean measurement: v2-only + F-fixed study → definitive A1 numbers + RR (A3).
3. COMBINATION/PERMUTATION grid (section C) on the clean data → best combos.
4. Wave-3 build (data-driven, NOT a stack-voter): direction filter + elite-solo selection + SL-wiring
   (C-1) + meta contract (F) + v2 config drop baseline (C-2) + nonzero weights (E-2).
5. Economic replay gate on holdout stocks with costs; ship only if it earns.
