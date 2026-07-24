# 47-40STOCK — PRO SYNTHESIS: the 40-stock deep study, resolved (2026-07-24)

Rolls up the six 40-stock studies (`forensics`, `htf_nest_bug`, `sl_anatomy`, `structural_tunes`,
`t1_and_bughunt`, `_REGIME`) against the two single-stock replications (`45-HAVELLS/_SYNTHESIS`,
`46-HUL/_SYNTHESIS`) and the build loop (`42-REFINE-LOOP`, iter-8: ungated **+0.52R**, high-grade tier ≥5
**+6.13R / win 49%**, all-4-quadrant holdout-stable @40 stocks).

**Data spine.** `runs/validate/study40_2026/evidence.parquet` — 44,042 firings, 40 symbols, ONE ~17-day
tape (2026-06-19..07-17); 38,462 decided (hit/loss). Regime labels (`_REGIME.md`): **RANGE 21 / UPTREND 8
/ DOWNTREND 11**, coarse 16-bar-D1 snapshot — **ADX cannot seat on 16 bars**, so every trend label is
provisional. Outcome frame = symmetric **1·ATR : 1·ATR** bracket on M5, same session (a coin-flip frame:
every detector wins 47–52%). `b_hit` = the config's own null-model baseline hit-prob. Realized **edge =
mean(win) − mean(b_hit)**. The three-way cross (HAVELLS = the one *range* stock with hand-marks · HUL = two
*downtrend* windows · 40-stock = 21 range / 19 trend) is what promotes a finding from "single-stock" to
**STRUCTURAL** or exposes it as **regime-specific**.

---

## THE SPINE — one sentence

> The wired system's detectors add **zero geometric edge** (0.52 AUC coin-flip, mirror MFE/MAE); the only
> ex-ante separator is `b_hit`, and **it is anti-calibrated** (alpha lives in its *low* tail). Every
> "SMC lever" that looked like edge — nest_depth, OTE, at-extreme — is a **range-fade tool whose sign FLIPS
> with trend direction**, which a regime-blind grader averages into mush. The program's one real,
> holdout-stable edge (the +6.13R nest_depth tier) is a *conjunction* that must be measured inside a
> regime frame, not a universal grade term. **We are not missing a detector; we are missing a mode switch.**

---

## (a) FINAL REPLICATION TABLE — every finding × [40-stock number | regime-split | verdict]

Verdict legend: **STRUCTURAL** = regime-free, replicates on range+trend and both single-stock windows ·
**RANGE-ONLY** / **TREND-ONLY** = holds in one regime, absent/inverted in the other · **SPLIT** = holds one
way (e.g. within-direction) but inverts another (e.g. portfolio-blind) · **ABSENT** = does not replicate.

| # | finding | 40-stock number | regime-split | verdict |
|---|---|---|---|---|
| **F6** | native confidence blind; only `b_hit` ranks | `b_hit` AUC **0.760** (40/40 > 0.55); strength 0.497 / width 0.493 / stacking 0.496 (35–37/40 blind) | AUC flat **.758/.761/.764** (RANGE/UP/DOWN) | **STRUCTURAL** (stronger than single-stock 0.69/0.74) |
| **L1** | `b_hit==0` firehose | **23.7%** of book fires at b_hit=0, wins **18.7%**; dropping it: **+9.6pp / −0R → +0.19R** (40/40) | flat, b0-win 19.7/18.8/16.9; share 23–24% every regime | **STRUCTURAL** — the single cleanest gate |
| **F6-cal** | `b_hit` anti-calibration paradox | top decile (>0.80, n6730) win 0.842 but **edge −0.121**; bottom (≤0.15) win 0.234 **edge +0.204**; realized +0.075 comes ENTIRELY from the low tail | replicates-all (LOW/HIGH edge +0.197/−0.09 in all 3) | **STRUCTURAL** — alpha is in LOW-b_hit taught firings |
| **F1** | `htf_nest` is an over-priced anti-signal | only **negative-edge** detector (**−4.7pp**), highest b_hit (**0.519**), lowest win (47.2%); 23/39 stocks negative | −8.6 / −2.7 / −6.4 UP/RANGE/DOWN (**worst in UP**, not range) | **STRUCTURAL** (pooled) but **HETEROGENEOUS** (big negatives are low-n) |
| **B1/F2** | invisible-extreme anchor (EXT capped inside true extreme) | median gap **+4.87 ATR**; 90% >0.5 ATR, 62% >3 ATR; **92% of stocks never re-anchor** the true high | +5.05 / +5.26 / +4.38; worst = DOWN-SHORT **+6.94 ATR** | **STRUCTURAL** (a code bug, regime-free) |
| **F3/T3** | tiny outer-wick stop shaken; +0.25·ATR buffer lift | exact-edge hold **11.9%**; T3 win-lift **+10.5pp (40/40**, +5.5..+16.2); breach **84/16 wick/gap** | flat +9.9 / +10.3 / +11.4 — **does NOT invert on trend** | **STRUCTURAL** — most transferable finding in the stack |
| **—** | fade / symmetric MFE–MAE / coin-flip entries | win **0.498**; win-mfe ≈ loss-mae (Δ≤0.18); median mfe/atr ≈ mae/atr ≈ 0.64 | mirror in all 3 (Δ 0.18 / 0.01 / 0.03) | **STRUCTURAL** (falsified-fade replicates at scale) |
| **B2** | sweep bar mis-localized | only **13%** of firings on the true poke; poke leads by ~1 bar / median **0.73 ATR** | 13–14% on-poke every regime | **STRUCTURAL** — grade sweep/wyckoff with ATR tolerance |
| **B4** | held-extreme graded as A-setup | at-extreme correct-side win RANGE **55.6%** → DOWN **49.6%**; `htf_nest`@extreme RANGE **60.0%** → DOWN **32.4%** | inverts hard: RANGE + / UP ~0 / DOWN − | **RANGE-ONLY** (edge inverts on trend) |
| **nest_depth** | HTF-alignment depth as discriminator | range-vs-trend framing **REFUTED**; HTF-aligned pays **+10.5pp UP / +2.7 RANGE(ns) / −8.5 DOWN** (z +3.2 / −3.6) | **sign-flips with TREND DIRECTION**, not range-vs-trend | **regime-conditional** (UP edge / DOWN anti-edge) |
| **dir** | direction lever inverts on trend | SHORT edge ~**+0.08 all regimes**; absolute SHORT>LONG **11/11 DOWN stocks**; LONG>SHORT in strongest UP (DLF/BAJFIN/TITAN) | LONG win 0.480→**0.443** into DOWN; SHORT 0.503→**0.549** | **regime-conditional** (the biggest per-regime lever after b_hit) |
| **T1** | OTE gate (short→premium / long→discount) | **within-direction** lift +4.8 / +6.1 / +9.3 (all 6 cells ≥0); **portfolio-blind** helps RANGE +4.3 / UP +5.0, **hurts DOWN −3.8** (Simpson's: PASS = 86% counter-trend longs) | within-dir universal; blind gate RANGE+UP only | **SPLIT** — universal as a within-direction sorter, RANGE/UP-only as a blind gate |
| **cont** | continuation-location beats fade-location | cont-side (short@discount/long@premium) **+4.8 DOWN**; RANGE −2.8, UP −3.5 | DOWN only | **TREND-ONLY** |
| **ppos** | price at bottom-of-zone wins | DOWN low→high quartile **0.547 → 0.447** (10pp); RANGE mild; UP flat | DOWN only | **DOWN-ONLY** lever |
| **hour** | avoid the 9–11h open | RANGE 9–11h ~0.47 vs 11–15h 0.51–0.525; UP/DOWN flat | RANGE only | **RANGE-ONLY** (weak) |
| **B3** | FVG on 1m not native TF | **ABSENT as a 1m bug** — `fvg` zones are **99% genuine 5m** 3-candle gaps (zone-endpoint match), fvg_n 79%; native tf already 5m | uniform (DOWN 30.9 / RANGE 28.8 / UP 29.1 clean-1m@0.30) | **ABSENT** (1m mislocation); refined → *missing HTF 15m/30m recall* + CE_HOLD/BPR/IFVG **derived-level mislabel** |
| **—** | plain-`fvg` / `CE_HOLD` as losers | ABSENT — fvg 48–51%, CE_HOLD edge **+9.3** (49.6% win); the HAVELLS 42.9% was stock-specific | flat | **ABSENT** |
| **F5** | AM-shorts-worst | not re-tested (no session split); HUL already broke it | — | **ABSENT** (per HUL) |
| **nest tier** | nest_depth-graded high tier (build loop, derived tradebook) | high-tier ≥5 **+6.13R / win 49%**; ungated **+0.52R**; all-4-quadrant holdout positive @40-stock/7392-trade | holdout = time-halves × stock-groups **within one 17d regime** | **MEASURED, robust in-sample; regime-UNPROVEN** |

**One-line read of the table:** the top block (F6 · L1 · F6-cal · F1 · B1 · F3 · coin-flip · B2) is
**STRUCTURAL** — ship/fix these blind. The middle block (B4 · nest_depth · direction · T1 · cont · ppos ·
hour) is **regime-conditional and mostly sign-flips UP↔DOWN** — this is the mode-switch's entire payload.
The bottom block is **ABSENT** — do not ship as universal filters.

---

## (b) WHERE WE ARE WRONG — ranked wired-system bugs (cross-stock evidence + fix)

Ranked by leverage. Each bug is confirmed on the 40-stock parquet AND cross-checked against HAVELLS/HUL.

### B1 — `htf_nest` anchors to the latest CONFIRMED pivot, not the live unmitigated extreme *(highest leverage)*
- **Evidence (all-40):** parent/base band caps a **median +4.87 ATR *inside*** the true causal extreme; **90%** of nests capped >0.5 ATR, **62%** >3 ATR; **92% of stocks NEVER re-anchor** a nest to the true high (median 4.2 ATR gap; BANKBARODA 57 ATR). HAVELLS: `zone_hi` never exceeds 1201.2 vs true 1234 (33pt / ~14 ATR) — the user's textbook +8..+26R short is **literally unemittable**. HUL: bites only on the *fresh* extreme (low side, 5.5 ATR gap).
- **Code cause:** `extremes.py` writes EXT levels **only for confirmed pivots** (`:218 continue` when `confirm_idx is None`); the live extreme stays `pending` until a ≥6% reversal leg completes → the unmitigated extreme is never a parent. `htf_nest.py:76–85` then nests the base inside stale mid-structure bands.
- **This IS the root of F1.** The nest grades a ~5-ATR-too-low object, inherits its parents' high historical b_hit (0.519), and under-delivers → the −4.7pp anti-signal. Fix B1 and F1 dissolves.
- **Fix — T2 [infra]:** emit the live *unmitigated* highest-high / lowest-low as EXT_H/EXT_L parents; do not gate the anchor on the 6% confirmed-reversal leg.

### B2 — `htf_nest` is regime-blind: it averages a +UP / −DOWN sign-flip into net mush
- **Evidence:** HTF-alignment (recomputed depth ladder, n=22,903) pays **+10.5pp in UPTREND, −8.5pp in DOWNTREND** (both significant, z +3.2 / −3.6), ~0 in RANGE. The wired detector fires from same-direction *containment* with **zero trend context** → the two halves cancel to −4.7pp. Replicates across independent detectors (fvg +17.4 UP / −9.9 DOWN, wyckoff +17.8 / −14.6).
- **Fix:** conjoin the nest with the D1 trend — count HTF-alignment **WITH** the trend (continuation), **suppress/invert counter-trend** (never buy discount in a downtrend; require sweep+BOS reversal at the extreme). This is the mode-switch (c).

### B3 — dead conviction knob: nest depth is quantized to a constant
- **Evidence:** `strength = min(1, nest_depth/3)` under `min_depth=2` on a 16-bar D1 tape ⇒ **99.8% of firings emit the identical 0.667** (only 3/1385 reach depth-3; D1 never seats both pivots). This is F6 proven at the code level for htf_nest.
- **Fix:** stop using depth as a monotone conviction multiplier; use it as a **regime-conditioned** feature (deep-alignment good in UP, ~0 in RANGE, bad in DOWN). Validate depth-≥3 only on longer history.

### B4 — the grader spends confidence on blind features (F6, universal)
- **Evidence:** `strength` AUC **0.497**, zone-width 0.493, stacking 0.496 — all inside [0.45,0.55] on 35–37/40 stocks, flat across regimes. Only `b_hit` separates (0.760). Any grade term reading strength/width/confluence-count is scoring **noise**.
- **Fix:** strip strength/width/stacking from the grade entirely; gate on `b_hit` + the regime-conditional levers only.

### B5 — no baseline floor: the `b_hit==0` firehose (L1)
- **Evidence:** **23.7% of the book** fires into a session/time-bucket whose null model had zero follow-through, and wins **18.7%**; every retest detector floods it (fvg_n 22%, ob 22%). Dropping it flips −0R → **+0.19R** (40/40).
- **Fix:** hard `b_hit > 0` gate (ideally prefer ≥0.5) — the single cleanest, most universal change.

### B6 — `b_hit` is anti-calibrated: the grader optimizes the wrong objective
- **Evidence:** `b_hit` ranks win but is over-confident >0.65 (edge −0.12 at the top) and under-confident ≤0.4 (edge +0.20 at the bottom), **identically in every regime**. Selecting high-b_hit maximizes raw hit-rate but **destroys alpha**; the +0.075 edge comes entirely from LOW-b_hit taught firings.
- **Fix:** recalibrate `b_hit` (isotonic/Platt — shrink top, lift bottom); **select for alpha on LOW-b_hit taught firings**, not high raw hit-rate. (Keep the `b_hit>0` floor from B5 — the very-bottom `==0` bucket is a different, dead cell.)

### B7 — no regime-direction gate: counter-trend longs in downtrends
- **Evidence:** LONG win collapses 0.480 → **0.443** into DOWN (+10.6pp loser-share); SHORT>LONG in **11/11 DOWN stocks**. The single biggest per-regime loser marker. The system fires LONG/SHORT symmetrically.
- **Fix:** in TREND mode choose direction by drift first; suppress counter-trend longs in DOWN / shorts in UP.

### B8 — held-extreme graded as A-setup (B4 in the study docs)
- **Evidence:** extreme-location alone grades **held-tops** (UP-SHORT at-extreme 52.8%, n897) and **knife-catches** (DOWN-LONG at-extreme 48.8%, n1247) as A-setups; `htf_nest`@extreme inverts RANGE 60% → DOWN 32.4%. HUL's headline new failure (3035 held for a week).
- **Fix:** conjoin the extreme gate with a **confirmed sweep + BOS reversal**; never score extreme *location* alone.

### B9 — sweep localization: firing is the 5m reclaim, not the poke (B2 in docs)
- **Evidence:** only 13% of sweep firings sit on the true poke; median 0.73 ATR / ~1 bar off. A stop parked at the sweep *level* is on the wrong side of the actual grab. `sweep` is also the worst tight-stop cohort (hold 12.9%, win 24.9%).
- **Fix:** ATR-tolerance on sweep/wyckoff levels; arm sweep entries only *after* the pool is taken, or anchor SL **beyond the pool**.

### B10 — "FVG" labels derived levels that are not gaps (refined B3)
- **Evidence:** the 1m-mislocation bug is **ABSENT** (native tf is 5m; zones 99% match 5m gaps). But strict-tolerance matching shows only 6–13% are clean 1m gaps because most `fvg` firings are **CE_HOLD midlines (5,917) + BPR overlaps (715)** and most `fvg_n` are **IFVG/inverse retests** — *derived* objects that reproduce no 3-candle void on any TF; 41% best-match no TF within 0.5 ATR. HTF 15m/30m gaps are under-recalled (15m match 40–43%).
- **Fix:** separate raw-gap retests from midline/inverse/overlap retests; emit 15m/30m FVG; grade zones with an ATR tolerance so the name means what it says.

---

## (c) THE MODE-SWITCH DESIGN — regime classifier gates fade vs momentum

The middle block of table (a) is one object: **a fade edge that inverts into a momentum edge as the tape
trends.** A regime-blind grader nets the two to ~0. The design is a classifier that flips the *sign and
membership* of the SMC levers per mode. The grade terms don't get down-weighted — **they flip**.

### The classifier
- **Inputs:** Wyckoff phase (accumulation/distribution vs mark-up/mark-down) · **D1 close-position-in-range** (`close_pos`, the workable one on this tape) · D1 drift% · ADX **once ≥28 D1 bars exist** (ADX cannot seat on 16 — do NOT trust it on the current tape).
- **Rule (from `_REGIME.md`):** UPTREND `drift>+3 & close_pos>65` · DOWNTREND `drift<−3 & close_pos<35` · else RANGE. Intraday tie-break toward drift only if `samedir≥0.70 & itrend≥0.45`.
- **Output:** {RANGE, UPTREND, DOWNTREND} per symbol per day. Coarse today; upgrade to a rolling multi-week classifier when longer history lands.

### RANGE mode — FADE (this is where the +6.13R nest edge lives)
- **Direction:** symmetric LONG/SHORT (mild universal short-tilt +0.08 ok).
- **Location = FADE side:** OTE gate SHORT→premium (`rp≥0.62`) / LONG→discount (`rp≤0.38`) — within-direction lift +4.8pp.
- **At-extreme = A-setup:** correct-side at-extreme is the *best* bucket (55.6%, `htf_nest`@extreme 60%) — the swept-and-reversed spike. Score it up.
- **nest_depth:** **hump** — peaks at shallow depth-1 (+13.4pp), decays to ~0 by depth-3 (deep multi-TF alignment pins price at a shared extreme that fails). Reward depth-1/2, not depth-3.
- **Session:** de-weight the 9–11h open (RANGE-only, ~−4pp).

### TREND mode — MOMENTUM / CONTINUATION
- **Direction = with-trend, chosen FIRST by drift:** SHORT-only in DOWN, LONG-only in UP. Suppress counter-trend (kills the DOWN-LONG knife-catch, the single biggest loser marker).
- **Location = CONTINUATION side (the sign FLIPS):** SHORT@discount / LONG@premium — continuation-location beats fade-location **+4.8pp in DOWN**. OTE is applied *inside* the drift-chosen direction, never to pick direction.
- **At-extreme requires proof:** the aligned extreme is **HELD, not swept** — extreme-location alone is the *worst* bucket in DOWN (32.4%). Gate on **confirmed sweep + BOS reversal** before any counter-trend entry at an extreme; otherwise skip.
- **nest_depth / HTF-alignment:** **monotone-rising in UP** (deeper alignment better, +10.5pp) — reward depth. **Inverted/anti in DOWN** (−8.5pp) — being "at your side of the HTF extreme" loses; **do not reward depth in DOWN** unless sweep+BOS confirms.
- **ppos (DOWN-only):** prefer firings priced at the **bottom** of their zone (low ppos, 0.547 vs 0.447 at top).

### Regime-FREE terms (identical in BOTH modes)
- `b_hit > 0` floor + recalibrated `b_hit` as the ranker (select LOW-b_hit taught alpha, not high raw prior).
- **T3** wick ± 0.25·ATR stop buffer (does not invert; +10.5pp everywhere).
- **Never** gate on strength / zone-width / stacking.
- ATR tolerance on sweep/wyckoff levels.

### How the grade terms change per mode (the crux)
| term | RANGE (fade) | UPTREND (momentum) | DOWNTREND (momentum) |
|---|---|---|---|
| direction | symmetric | **LONG only** | **SHORT only** |
| OTE / premium-discount | **fade** (short@prem / long@disc) | continuation (long@prem) | **continuation** (short@disc) |
| at-extreme | **+A-setup** (swept-reversed) | require sweep+BOS | require sweep+BOS (else worst bucket) |
| nest_depth / HTF-align | **hump** (peak d1, ~0 by d3) | **monotone +** (reward depth) | **anti** (do not reward) |
| ppos | flat | flat | **prefer low (zone bottom)** |
| session | de-weight 9–11h | flat | flat |
| b_hit floor · T3 buffer · no-blind | **same** | **same** | **same** |

---

## (d) SHIP-NOW vs BUILD vs MEASURE

### SHIP-NOW — structural, proven on all 40, regime-free (measurable on the parquet, no new regime data)
1. **`b_hit > 0` gate** — drop the 23.7% `b_hit==0` firehose. −0R → **+0.19R, +9.6pp, 40/40, flat across regimes.** Single strongest, most universal tune.
2. **T3 stop buffer** — park every taught wick stop at `wick ± 0.25·ATR`. **+10.5pp win, 40/40, does not invert.** (Win-rate/geometry tune; earns net-R only paired with the taught large-R target — re-race on 1m before quoting a net-R.)
3. **No-blind** — strip `strength` / zone-width / stacking from the grade. AUC 0.49–0.50 on 35–37/40; they score noise.
4. **Keep `htf_nest` OFF solo** — the only negative-edge detector until B1/T2 lands.
5. **ATR tolerance on sweep/wyckoff levels** (B9) + **stop separating CE_HOLD/BPR/IFVG from raw-gap FVG** (B10) — labelling hygiene, no regime dependence.

### BUILD — the regime gate + the anchor/localization bug fixes (net-new code)
1. **Regime classifier** (Wyckoff phase / D1 close-position / ADX-when-it-seats) → the mode switch of (c). **This is the program's central missing piece.**
2. **T2 [infra] — re-anchor EXT to the live unmitigated extreme** (fixes B1 *and* its F1 downstream in one move). Highest-leverage single build.
3. **Regime-conjoin `htf_nest`** — align WITH trend (reward depth in UP), suppress/invert counter-trend (DOWN), hump in RANGE.
4. **T1 as a within-direction sorter** inside the drift-chosen direction (never a direction picker).
5. **Conjoin extreme-gate with confirmed sweep + BOS reversal** (B8) — kills held-tops / knife-catches.
6. **Recalibrate `b_hit`** (isotonic/Platt) and select for **LOW-b_hit taught alpha** (B6).
7. **Emit 15m/30m FVG**; separate raw-gap from derived-level retests (B10) [infra].

### MEASURE — the gates that block "PROVEN"
1. **MULTI-REGIME / multi-month 1m data — the binding gate.** Everything is ONE 17-day tape; the +6.13R holdout is time-halves × stock-groups *within one regime*, not across regimes. Re-derive the nest tier, T1, and all mode-switch magnitudes **split by regime across regimes**.
2. **Faithfulness** — are the high-grade winners the user's 467 hand-marks? (co-location check).
3. **Re-race T3 on 1m with the taught large-R targets** for a real net-R (the symmetric-frame ΔExpR is −0.03R; the value is the tiny-wick geometry, not a blanket stop-widen).
4. **nest_depth full ladder** on history long enough that D1 seats depth-3 (currently inert — only 23% of firings even have an HTF dealing range).
5. Confirm the **ppos (DOWN)** and **hour (RANGE)** secondary levers survive as grade terms; **tick-granular fills** to replace the 1m gap-aware model.

---

## (e) THE SINGLE HIGHEST-CONFIDENCE ACTION + THE SINGLE BIGGEST OPEN RISK

**Highest-confidence action:** ship the **`b_hit>0` gate** (drop the `b_hit==0` quartile). It is the only
tune that is 40/40, regime-flat (RANGE/UP/DOWN 19.7/18.8/16.9% win in the dropped bucket, share 23–24%
everywhere), replicated on both single stocks, and flips a break-even book to **+0.19R** with zero new
infra and zero regime assumptions. Bundle T3 (+10.5pp) and no-blind with it — the three regime-free
structural tunes — but if only one thing ships, it is the b_hit floor.

**Biggest open risk:** **everything rests on ONE 17-day tape = one market regime.** ADX cannot seat on 16
D1 bars, so the regime labels the entire mode-switch depends on are a coarse snapshot; the headline +6.13R
nest edge is holdout-stable only across *time-halves within that one regime*; and the mode-switch's central
claim (fade in RANGE / momentum in TREND) is inferred from a **21-range / 19-trend cross-section on a single
window**, not from watching one name transition regimes. If the fade↔momentum sign-flip is an artifact of
which *stocks* trended in this window rather than of the *regime itself*, the mode-switch could be curve-fit
to this tape. Multi-month, multi-regime 1m data is the one experiment that turns the whole stack from
"promising, in-sample" to "proven."

---

## 10-LINE PRO VERDICT

1. **Detectors add no edge.** 0.52-AUC coin-flip, mirror MFE/MAE across win/loss in all 40 stocks / 3 regimes — entries carry no directional excursion edge; only which barrier is tagged first.
2. **`b_hit` is the sole separator (AUC 0.760, 40/40) — and it is anti-calibrated:** the realized +0.075 edge comes ENTIRELY from its *low* tail; the high-b_hit "obvious" setups destroy edge (−0.12).
3. **The three STRUCTURAL, ship-now tunes are proven 40/40, regime-flat:** drop `b_hit==0` (−0R→+0.19R), buffer the wick stop ±0.25·ATR (+10.5pp), and never grade on strength/width/stacking.
4. **`htf_nest` is the one broken detector** — only negative edge (−4.7pp), highest b_hit — and its root is a **code bug**: EXT anchors to the last confirmed pivot, capping the nest a median **4.87 ATR inside the true extreme** on 92% of stocks. T2 (re-anchor to the live extreme) fixes it and F1 together.
5. **Every "SMC lever" is regime-conditional and sign-flips UP↔DOWN, not range↔trend:** nest_depth pays +10.5pp in UP / −8.5pp in DOWN; at-extreme inverts 60%→32%; direction inverts (SHORT>LONG 11/11 DOWN stocks).
6. **A regime-BLIND grader averages that sign-flip into net-zero mush** — the wired system's core defect is not a missing detector but a **missing mode switch**.
7. **T1/OTE is falsified as a universal gate but confirmed as a within-direction sorter** (Simpson's paradox: blind, it over-selects counter-trend discount-longs in downtrends).
8. **The mode-switch is the build:** RANGE → fade (OTE-fade, at-extreme A-setup, hump depth); TREND → momentum (with-trend direction first, continuation-location, extreme only on sweep+BOS, reward depth in UP / veto in DOWN).
9. **The program's one real edge — the +6.13R nest_depth tier, ungated +0.52R, all-4-quadrant holdout-stable @40 stocks — is robust IN-SAMPLE but regime-UNPROVEN** (holdout is time-halves within one 17-day window).
10. **Verdict: ship the three regime-free structural tunes now; build the regime classifier + T2 anchor fix next; and treat "one 17-day tape" as the make-or-break — multi-regime data is the single experiment between "promising" and "proven."**
