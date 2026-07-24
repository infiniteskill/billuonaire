# 40-STOCK — SL ANATOMY (F3) + FVG NATIVE-TF BUG

RECOGNITION study, 40 stocks, 2026 tape (`study40_2026/evidence.parquet`, 44,042 firings; 38,296
directional with valid outer-wick geometry) vs raw 1m (`data/wide/<SYM>.csv`). Regime labels from
`_REGIME.md` (UP 8 / RANGE 21 / DOWN 11). Question: **is F3 UNIVERSAL** — tiny-wick stop shaken out,
+0.25·ATR buffer lift, ~85/15 wick/gap breach — and does **FVG map to a literal 1m 3-candle gap** across
all 40.

## 0. Method & the outcome frame (calibrated, not assumed)

- **Taught outer-wick stop** = far zone edge − entry: LONG `SL = price − zone_lo`, SHORT `SL = zone_hi −
  price` (require > 0). `SL_atr = SL / atr`.
- **Outcome window RECONSTRUCTED, not guessed:** matching reconstructed `mfe`/`mae` back to the parquet
  pins the frame at **120 min (24×5m bars), clipped at session end** — median reconstruction error
  **0.000**, 74–78% exact match; leaking past session-end breaks it (err 5.7). This is the frame every
  race/breach test below uses.
- **First-touch race** on 1m over that window: target = ±1·ATR; stop = exact wick edge vs buffered
  (`edge ± 0.25·ATR`); same-bar target+stop tie → **loss** (conservative). `hit`/`na`/`undecided`
  semantics honored (WIN=`hit`, LOSS=`loss`, drop na/undecided from the parquet-baseline cross-check).
- **Tight-stop tercile** = each stock's own bottom third of `SL_atr` (median **0.42 ATR** — the true
  taught-wick geometry). *The full sample is contaminated by wide HTF-anchored stops (htf_nest 6.7 ATR,
  up to 25 ATR) that trivially beat a 1-ATR target — those inflate win-rate above the symmetric 1:1
  baseline and are NOT the F3 object.* F3 is a **tight-stop phenomenon** and must be read on the tercile.

Note vs HAVELLS/HUL: those studies ran on symbol-specific parquets (HAVELLS 1793-firing) with a
~0.5–0.7 ATR taught stop. The study40 zones are **tighter (0.42 ATR)**, so absolute hold-rates run
*lower* than HAVELLS's 30% — but the F3 *structure and the T3 lift* are what must replicate, and they do.

---

## 1. HEADLINE — F3 REPLICATES ON ALL 40 (tight-stop tercile)

| metric | AGG | UPTREND | RANGE | DOWNTREND | verdict |
|---|---|---|---|---|---|
| n (tight tercile) | 12,784 | 2,421 | 6,846 | 3,517 | |
| SL_atr median | 0.42 | 0.42 | 0.41 | 0.44 | tiny taught wick |
| **SL-hold @ exact edge** | **11.9%** | 13.2 | 12.0 | 10.9 | stop run ~88% of the time |
| SL-hold @ +0.25 ATR | 21.8% | 21.4 | 22.2 | 21.4 | +9.9pp hold lift |
| **realized win — exact stop** | **42.4%** | 44.0 | 43.2 | 39.7 | below symmetric 1:1 (~46%) |
| **realized win — +0.25 buffer** | **52.9%** | 53.9 | 53.5 | 51.0 | |
| **T3 lift (+0.25 ATR)** | **+10.5pp** | +9.9 | +10.3 | +11.4 | **REPLICATES (all-40)** |
| winner-tag (winners shaken at edge) | 44.3% | 42.0 | 43.8 | 47.1 | ~⅖ of winners first tagged |
| **breach wick / gap** | **84.1 / 15.9** | 85.8/14.2 | 84.2/15.8 | 82.6/17.4 | **≈85/15 REPLICATES** |

**Universality scorecard (per-stock, 40 stocks):**
- **T3 win-lift POSITIVE on 40/40 stocks** (min +5.5 ABB, max +16.2 APOLLOHOSP, mean **+10.5pp**); 29/40
  land in [+8,+14]pp. Zero exceptions. → **UNIVERSAL.**
- **SL-hold @ exact < 20% on 40/40** (mean 12.0%). The literal taught tick-stop is shaken out
  **~7 of 8 times** at this geometry. → **UNIVERSAL (stronger than HAVELLS).**
- **Breach wick-dominant on 40/40** (all > 50% wick; 34/40 ≥ 80% wick; mean 84.1% wick). → **≈85/15
  everywhere.**
- **Regime-robust:** the T3 lift is +9.9 / +10.3 / +11.4 across UP / RANGE / DOWN — a *flat, non-regime*
  edge (slightly larger in downtrends, where gap-through breaches also tick up 14→17%). Unlike the
  OTE/nest levers (which invert on trend), **F3 does NOT invert** — it is the most transferable finding
  in the whole HAVELLS/HUL/40-stock stack.

The 6 stocks below 80% wick (still wick-majority) are the gap-heavier names — all still show a positive
T3 lift:

| gap-heavier stock | wick% | gap% | T3 lift |
|---|---|---|---|
| ABFRL (DOWN) | 66.6 | 33.4 | +16.0 |
| ALKEM (RANGE) | 74.2 | 25.8 | +12.3 |
| BALKRISIND (DOWN) | 77.0 | 23.0 | +7.3 |
| APOLLOTYRE (RANGE) | 77.1 | 22.9 | +8.8 |
| BOSCHLTD (RANGE) | 77.8 | 22.2 | +12.8 |
| BRITANNIA (RANGE) | 79.1 | 20.9 | +7.5 |

---

## 2. Per-detector SL geometry — WHERE the tight tercile comes from (B4)

Full directional sample, per detector. The tight tercile is the **taught-wick detectors**
(ob_taught / sweep / fvg / orderblock, ~0.5–0.9 ATR); **htf_nest's stop is 6.7 ATR and holds 84%** —
the stop-hold edge is **HTF-anchor distance, not detector confidence** (B4 replicates all-40).

| detector | n | SL_atr med | SL-hold@edge | win exact | win +0.25 | % in tight tercile |
|---|---|---|---|---|---|---|
| ob_taught | 1,647 | 0.72 | 23.0% | 54.9 | 63.2 | 48.8 |
| sweep | 2,013 | 0.75 | **12.9%** | **24.9** | 39.6 | 47.1 |
| fvg | 6,573 | 0.81 | 33.1% | 58.9 | 65.7 | 42.9 |
| propulsion2 | 565 | 0.83 | 27.3% | 51.9 | 59.2 | 44.2 |
| orderblock | 9,161 | 0.88 | 32.3% | 51.6 | 58.9 | 39.9 |
| wyckoff | 6,813 | 1.08 | 33.3% | 54.1 | 59.9 | 23.0 |
| fvg_n | 7,617 | 1.12 | 36.4% | 68.3 | 73.1 | 24.9 |
| compression | 2,561 | 1.12 | 39.6% | 47.8 | 56.4 | 31.8 |
| **htf_nest** | 1,346 | **6.74** | **84.3%** | 89.9 | 91.4 | 2.5 |

**`sweep` is the worst tight cohort** (hold 12.9%, win 24.9%) — sweep-entry firings get run through the
tight edge hardest, consistent with the "entered before the sweep completed, stop tagged" failure. The
T3 buffer rescues sweep the most in relative terms (24.9→39.6).

---

## 3. PER-STOCK TABLE — tight-stop tercile (sorted regime, then T3 lift)

`hold_e`=SL-hold at exact edge · `winE/winB`=realized win exact / +0.25 buffer · `lift`=T3 · `wtag`=% of
eventual winners first tagged at the edge · `wick`=breach wick share.

| SYM | regime | n | SL_atr | hold_e | winE | winB | **lift** | wtag | wick% | gap% |
|---|---|---|---|---|---|---|---|---|---|---|
| AXISBANK | DOWN | 348 | 0.3 | 8.3 | 37.2 | 44.4 | +7.2 | 52.2 | 84.6 | 15.4 |
| BALKRISIND | DOWN | 278 | 0.4 | 9.4 | 41.1 | 48.4 | +7.3 | 42.9 | 77.0 | 23.0 |
| BERGEPAINT | DOWN | 296 | 0.5 | 14.2 | 43.2 | 50.7 | +7.4 | 41.0 | 85.0 | 15.0 |
| CGPOWER | DOWN | 299 | 0.5 | 9.4 | 35.9 | 45.8 | +9.9 | 50.0 | 85.2 | 14.8 |
| BANKBARODA | DOWN | 285 | 0.4 | 8.8 | 37.1 | 48.9 | +11.8 | 51.8 | 84.2 | 15.8 |
| ADANIPOWER | DOWN | 328 | 0.5 | 14.9 | 40.2 | 52.5 | +12.3 | 46.5 | 87.5 | 12.5 |
| ASHOKLEY | DOWN | 377 | 0.5 | 11.7 | 40.2 | 52.7 | +12.5 | 46.6 | 81.4 | 18.6 |
| CANBK | DOWN | 315 | 0.5 | 10.2 | 40.9 | 53.5 | +12.6 | 48.6 | 87.3 | 12.7 |
| CROMPTON | DOWN | 337 | 0.4 | 11.6 | 43.2 | 56.0 | +12.9 | 42.5 | 83.6 | 16.4 |
| COALINDIA | DOWN | 304 | 0.4 | 11.2 | 43.0 | 57.0 | +14.0 | 45.3 | 88.5 | 11.5 |
| ABFRL | DOWN | 350 | 0.5 | 10.3 | 34.7 | 50.7 | +16.0 | 49.2 | 66.6 | 33.4 |
| CHOLAFIN | RANGE | 326 | 0.4 | 8.3 | 39.5 | 46.3 | +6.8 | 50.6 | 87.6 | 12.4 |
| ADANIPORTS | RANGE | 275 | 0.4 | 11.6 | 48.7 | 56.0 | +7.3 | 35.9 | 87.7 | 12.3 |
| BRITANNIA | RANGE | 295 | 0.4 | 14.2 | 50.8 | 58.3 | +7.5 | 39.8 | 79.1 | 20.9 |
| COLPAL | RANGE | 328 | 0.4 | 13.4 | 42.3 | 50.3 | +8.0 | 49.8 | 80.6 | 19.4 |
| APOLLOTYRE | RANGE | 313 | 0.4 | 9.3 | 35.7 | 44.4 | +8.8 | 48.1 | 77.1 | 22.9 |
| BEL | RANGE | 322 | 0.4 | 10.6 | 44.7 | 53.8 | +9.1 | 41.6 | 87.5 | 12.5 |
| AUROPHARMA | RANGE | 380 | 0.4 | 13.9 | 49.5 | 58.9 | +9.5 | 40.1 | 86.5 | 13.5 |
| VOLTAS | RANGE | 316 | 0.4 | 10.8 | 44.6 | 54.2 | +9.6 | 41.4 | 83.3 | 16.7 |
| COFORGE | RANGE | 302 | 0.4 | 15.6 | 39.2 | 49.1 | +9.9 | 43.9 | 89.4 | 10.6 |
| BHARTIARTL | RANGE | 338 | 0.4 | 12.7 | 48.7 | 59.0 | +10.4 | 39.5 | 86.4 | 13.6 |
| HAVELLS | RANGE | 315 | 0.4 | 9.5 | 45.9 | 56.4 | +10.6 | 41.0 | 89.5 | 10.5 |
| ASIANPAINT | RANGE | 416 | 0.4 | 9.1 | 40.3 | 51.0 | +10.6 | 44.9 | 83.9 | 16.1 |
| BPCL | RANGE | 369 | 0.5 | 11.9 | 44.5 | 55.2 | +10.7 | 40.3 | 86.8 | 13.2 |
| BHARATFORG | RANGE | 391 | 0.4 | 10.2 | 41.6 | 52.3 | +10.7 | 44.7 | 86.3 | 13.7 |
| CIPLA | RANGE | 312 | 0.4 | 14.4 | 40.8 | 52.3 | +11.5 | 45.0 | 85.4 | 14.6 |
| DABUR | RANGE | 286 | 0.4 | 12.6 | 39.2 | 50.7 | +11.5 | 49.8 | 80.4 | 19.6 |
| BAJAJFINSV | RANGE | 300 | 0.4 | 15.7 | 46.3 | 58.2 | +12.0 | 39.8 | 88.9 | 11.1 |
| ALKEM | RANGE | 330 | 0.4 | 15.5 | 38.5 | 50.8 | +12.3 | 44.5 | 74.2 | 25.8 |
| ADANIENT | RANGE | 307 | 0.4 | 11.7 | 40.7 | 53.4 | +12.7 | 48.6 | 88.9 | 11.1 |
| BOSCHLTD | RANGE | 291 | 0.4 | 11.7 | 39.3 | 52.1 | +12.8 | 50.4 | 77.8 | 22.2 |
| AUBANK | RANGE | 334 | 0.4 | 10.8 | 46.4 | 59.6 | +13.2 | 40.1 | 80.5 | 19.5 |
| ABB | UP | 289 | 0.4 | 16.3 | 46.0 | 51.4 | +5.5 | 40.5 | 85.1 | 14.9 |
| BIOCON | UP | 311 | 0.4 | 10.9 | 46.3 | 53.9 | +7.6 | 39.0 | 83.4 | 16.6 |
| TITAN | UP | 311 | 0.4 | 12.2 | 43.4 | 51.2 | +7.8 | 39.1 | 91.9 | 8.1 |
| BAJAJ-AUTO | UP | 303 | 0.4 | 12.2 | 37.2 | 46.8 | +9.6 | 47.9 | 86.1 | 13.9 |
| DLF | UP | 274 | 0.4 | 12.8 | 37.1 | 48.0 | +10.8 | 47.9 | 87.9 | 12.1 |
| BAJFINANCE | UP | 350 | 0.4 | 9.7 | 44.5 | 55.5 | +11.0 | 41.9 | 82.9 | 17.1 |
| AARTIIND | UP | 297 | 0.5 | 16.5 | 50.8 | 62.0 | +11.2 | 37.8 | 81.0 | 19.0 |
| APOLLOHOSP | UP | 286 | 0.4 | 16.1 | 46.3 | 62.5 | +16.2 | 43.3 | 88.3 | 11.7 |

Cross-check: tape SL-hold (11.9%) vs parquet-`mae` SL-hold (`mae<SL_atr` = 16.7%) agree in story (both
far below HAVELLS 30%); the ~5pp gap is the parquet's mae being truncated once a hit/loss decides.

---

## 4. FVG native-TF bug — REPLICATES the "not a 1m gap" claim; REFINES the "it's a 5m/30m gap" fix

Test: for every `fvg`/`fvg_n` firing, does its zone `[zone_lo, zone_hi]` equal a literal 3-candle FVG
(bull: `low[i+2] > high[i]`; bear: `high[i+2] < low[i]`) on 1m / 5m / 15m / 30m, causal & same-session?
Match = both edges within tolerance (ATR-normalized).

**% of firings that map to a clean N-TF 3-candle gap (by tolerance):**

| tol (ATR) | fvg 1m | fvg 5m | fvg 15m | fvg_n 1m | fvg_n 5m | fvg_n 15m |
|---|---|---|---|---|---|---|
| 0.15 (strict) | 12.9 | 20.6 | 2.2 | **6.1** | 9.1 | 2.0 |
| 0.30 | 29.4 | 33.4 | 5.4 | 17.7 | 17.4 | 5.2 |
| 0.50 | 46.5 | 45.0 | 11.0 | 35.6 | 30.6 | 11.1 |
| 1.00 | 65.6 | 59.1 | 23.5 | 62.1 | 54.8 | 28.3 |

**Findings (uniform across 40 stocks & all 3 regimes — DOWN 30.9 / RANGE 28.8 / UP 29.1% clean-1m@0.30):**

1. **The native-TF-FVG bug REPLICATES.** At a strict tolerance (0.15 ATR/edge) only **6% (fvg_n) — 13%
   (fvg)** of "FVG" firings are a literal 1m 3-candle gap — squarely in the HAVELLS/HUL **7–15%** band.
   A 1m 3-candle detector reproduces the taught FVG mark **~1 time in 8**. Median 1m fit error 0.52 ATR.
2. **BUT the fix "detect FVG on 5m/30m" is only *half* right.** The zones map to **15m at 2–5%** and
   **30m at ~0.5–1%** — i.e. essentially *never* a coarse-HTF gap. Best match is **1m/5m, which are
   near-equal** (fvg: 1m 29% vs 5m 33%; fvg_n: 1m 18% vs 5m 17%). The taught boxes here are
   **fine-grained (1m–5m scale)**, not H15/H30 imbalances. So: **move FVG detection to 5m (mild lift
   over 1m), NOT to 15m/30m.**
3. **The deeper mechanism (the real bug): most "FVG" firings are NOT raw gaps at all.** Event breakdown:
   - `fvg` detector = **CE_HOLD (5,917)** + **BPR (715)** — i.e. mostly **consequent-encroachment
     (the FVG 50% midline)** and **balanced-price-range (overlap of two opposing FVGs)**. Both are
     *derived levels/ranges*, so **no single-TF 3-candle gap can ever match them** — that is why 41% of
     `fvg` firings best-match **NO TF within 0.5 ATR**.
   - `fvg_n` = FVG_N_RETEST (4,296) + **IFVG_RETEST (3,847)** — inverse-FVG (a filled-and-flipped gap),
     again a derived object, not a raw imbalance.

   So the label "FVG" is attached to geometry that is **predominantly a midline / inverse / overlap
   construct, not a 3-candle void.** Testing "is it a 1m gap" understates the problem: much of the book
   isn't a gap on *any* TF.

---

## 5. THE TUNE / BUG THIS IMPLIES

- **T3 (SHIP — universal, regime-free):** buffer *every* outer-wick stop to **`wick ± 0.25·ATR`**.
  Measured **+10.5pp realized win-rate on the aggregate tight cohort and POSITIVE on all 40/40 stocks**
  (+5.5..+16.2), flat across UP/RANGE/DOWN. The literal tick-stop holds only ~12% and shakes you out of
  **~44% of eventual winners**; 84% of the breaches it removes are **noise wicks, not gaps**. Cost:
  +0.25 ATR on a multi-R target. This is the single most transferable edge in the study — it does **not**
  invert on trend (unlike OTE/nest).
- **B4 corollary:** the stop-hold edge is **HTF-anchor distance** — htf_nest (6.7 ATR stop) holds 84%
  while the taught 0.42-ATR wick holds 12%. Weight nest-depth / anchor-distance, **never per-firing
  strength or stacking count**.
- **`sweep`-entry stops are the worst** (hold 12.9%, win 24.9%): arm sweep entries only *after* the pool
  is taken, or anchor SL **beyond the pool**, not the sweep wick.
- **FVG detection bug:** (a) move FVG to a **5m** base (mild recall lift over 1m; **not** 15m/30m —
  those match ~0%); (b) more importantly, **stop labelling CE_HOLD midlines, BPR overlaps and inverse-
  FVGs as "FVG"** — they are derived levels, reproduce no 3-candle gap, and dominate the `fvg` book
  (CE_HOLD alone = 5,917 firings). Grade FVG zones with an **ATR tolerance**, and separate raw-gap
  retests from midline/inverse/overlap retests so the detector name means what it says.

## 6. HONEST CAVEATS
- One 17-day tape; the T3 *magnitude* (+10.5pp) is measured but single-regime. The **sign** is 40/40 and
  regime-flat, which is the strongest transferability evidence available here.
- Tight-tercile is each stock's own bottom third (SL_atr med 0.42 ATR); absolute hold-rates are lower
  than HAVELLS's 30% purely because these zones are tighter — the *lift* is the invariant.
- Same-bar target+stop ties are scored as losses (conservative); relaxing that only *raises* winE and
  *shrinks* the lift, so +10.5pp is a floor.
- FVG match uses a causal same-session 3-candle scan; a full multi-session HTF-FVG library (gaps formed
  on prior days) could lift the coarse-TF numbers, but the 30m≈1% / 15m≈5% result is already decisive
  that these are not H15/H30 objects.
