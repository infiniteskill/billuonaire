# 47-40STOCK — STRUCTURAL TUNES: 40-stock validation of the 3 SHIP-NOW tunes (2026-07-24)

Validates the three regime-free "ship-now" tunes from `45-HAVELLS/_SYNTHESIS.md` §E and
`46-HUL/_SYNTHESIS.md` §B across **all 40 stocks** (`runs/validate/study40_2026/evidence.parquet`,
44,042 firings, 38,462 decided directional) and per regime (`_REGIME.md`: RANGE 21 / UPTREND 8 /
DOWNTREND 11). Every number below is measured on this parquet — no pipeline run.

- **T3** — SL wick ± 0.25·ATR buffer (F3: taught tiny-wick stop shaken ~70% by noise → +12pp).
- **b_hit gate** — drop `b_hit==0`, prefer `b_hit≥0.5` (F6/L1).
- **no-blind** — strength / zone-width / stacking are non-predictive; never gate on them (F6).

## Outcome frame (from `app/trader/tools/study.py`)
`hit` = **symmetric 1·ATR : 1·ATR** bracket walked bar-by-bar on M5, same session: WIN (`hit`) if
favorable excursion reaches +1 ATR before adverse reaches +1 ATR; LOSS if adverse first (same-bar =
loss, conservative); else `undecided`/`na`. **mfe/mae are max fav/adv excursions in ATR units**
(verified: row with mfe 1.4767 = (zone_hi−price)/atr). **b_hit** = null-model hit-rate over K seeded
random same-session, same-30-min-bucket bars, same direction (a "when/where you traded" baseline).
Realized **edge** = mean(`hit`=='hit') − mean(`b_hit`). R below = 1 ATR (the frame's stop).

---

## TUNE 1 — T3: SL wick ± 0.25·ATR buffer  → **GO (structural, universal), magnitude ~½ the claim**

Measured two ways. **(A)** widen the study's own 1-ATR stop to 1.25 ATR (order-safe, zero assumptions —
only base-`loss` rows with `mae<1.25 & mfe≥1` flip to a clean win). **(B)** re-grade against the *actual
taught wick stop* (adverse zone-edge distance in ATR), target = 1 ATR, on the tight cohort `sl≤1.0`
where the mechanism lives; residual order-ambiguity ({win & mae≥sl} = 63% of winners) reported as a
[pessimistic..optimistic] band.

### A. Symmetric 1-ATR frame (robust headline)
| bucket | n | base win% | buffered win% | **lift** | ΔExpR (R=1ATR) |
|---|---|---|---|---|---|
| **ALL 40** | 38,462 | 49.8 | 54.0 | **+4.2pp** | **−0.028** |
| RANGE | 20,592 | 50.1 | 54.3 | +4.2pp | −0.028 |
| UPTREND | 7,233 | 49.1 | 53.4 | +4.3pp | −0.028 |
| DOWNTREND | 10,637 | 49.6 | 53.9 | +4.2pp | −0.029 |

lift>0 in **40/40** stocks (range +2.6 → +5.9pp); tight-wick tercile +4.6pp vs wide +4.1pp.
**ΔExpR is negative in 38/40** — in a symmetric 1:1 frame the buffer pays 0.25 R on 17,422 deep losers
to rescue 1,324 wins. The win% lift is real and universal; the *net-R* only turns positive with a
taught reward:risk ≫ 1 (see B — the buffer's value is the tiny-wick geometry, not a blanket stop-widen).

### B. Taught-wick frame, cohort `sl≤1.0` (faithful F3 test)
| bucket | n | exact-edge **hold%** | winners-**tag-edge%** | lift (pess) | lift (opt) |
|---|---|---|---|---|---|
| **ALL 40** | 20,913 | **20.1** | **63.1** | **+6.9pp** | **+4.9pp** |
| RANGE | 11,308 | 19.6 | 63.9 | +7.3pp | +4.8pp |
| UPTREND | 3,976 | 21.6 | 60.1 | +6.0pp | +5.1pp |
| DOWNTREND | 5,629 | 19.9 | 63.6 | +6.7pp | +4.6pp |

Both `hold%` (**20%** vs HAVELLS 30.3% / HUL 29–33%) and `winners-tag-edge` (**63.1%** vs HAVELLS 62%)
land on the single-stock numbers. lift>0 in **40/40** on *both* bounds. Per-stock tight-wick lift(pess)
ranges +2.9pp (ABFRL) → +10.3pp (ADANIENT); median **+7.0pp**.

**VERDICT: REPLICATES (all-40), STRUCTURAL / regime-free.** Mechanism (taught stop tagged 80% of the
time, 63% of eventual winners tag the exact edge first) is confirmed on every regime. Magnitude is
**~+5–7pp, roughly half the single-stock +11–12pp** — the single-stock studies over-stated it.
**GO — ship the ±0.25·ATR buffer**, but it is a win-rate/geometry tune, not a free-R tune: it earns net-R
only paired with the taught large-R targets (in a 1:1 frame it is −0.03R). **Bug it implies:** the wired
exit parks the stop *at the exact zone/wick edge* (`slwick` median ≈0.9 ATR, 20% hold) → noise shakes out
80% of taught stops and 63% of winners. Buffer the stop off the wick by 0.25 ATR.

### Per-stock T3 (symmetric-frame lift | wick-frame lift pess/opt)
```
sym         rg   n(sym) A-lift  B-pess B-opt  hold  wtag
ADANIENT   RANGE  935   +.042   +.103  +.048  .226  .616
CIPLA      RANGE  938   +.047   +.097  +.036  .212  .622
ASHOKLEY   DOWN  1150   +.046   +.090  +.046  .179  .665
COFORGE    RANGE  889   +.040   +.090  +.064  .233  .578
BALKRISIND DOWN   802   +.058   +.088  +.044  .169  .741
APOLLOHOSP UP     834   +.051   +.086  +.048  .250  .613
AUBANK     RANGE  984   +.047   +.086  +.038  .186  .687
HAVELLS    RANGE  954   +.040   +.084  +.055  .173  .677
BHARTIARTL RANGE 1031   +.053   +.084  +.071  .197  .627
ASIANPAINT RANGE 1248   +.032   +.080  +.049  .140  .714
...(all 40; full CSV in scratchpad/perstock_t3.csv + t3 wick)...
ABFRL      DOWN  1123   +.044   +.029  +.037  .230  .548  (weakest)
```
Universality: A-lift>0 **40/40** (all regimes 21/21, 8/8, 11/11); B-lift>0 **40/40** both bounds.

---

## TUNE 2 — b_hit gate: drop `b_hit==0`, prefer `b_hit≥0.5`  → **GO (unconditional, strongest tune)**

### Global (decided, n=38,462) and per regime
| bucket | share | win% | realized edge (win−b_hit) |
|---|---|---|---|
| **b_hit==0** | **23.7%** | **18.7** | +0.187* |
| 0<b_hit<0.5 | 33.4% | 43.5 | +0.162 |
| b_hit≥0.5 | 42.9% | **71.8** | −0.055 |

\*edge vs a literal-0 baseline; 18.7% absolute is still a bleed. Per regime the buckets are near-identical
(b==0 win: RANGE 19.7 / UP 18.8 / DOWN 16.9 — share 23–24% everywhere).

### Effect of the gate
| bucket | drop b==0: win% | ExpR (R=1ATR) | b_hit AUC |
|---|---|---|---|
| **ALL 40** | 49.8 → **59.4 (+9.6pp)** | −0.005 → **+0.188 (+0.19R)** | **0.760** |
| RANGE | 50.1 → 59.4 (+9.3) | +0.001 → +0.187 | 0.758 |
| UPTREND | 49.1 → 58.8 (+9.7) | −0.018 → +0.176 | 0.761 |
| DOWNTREND | 49.6 → 59.9 (+10.3) | −0.007 → +0.198 | 0.764 |

Dropping the `b_hit==0` quartile flips a **break-even book to +0.19R**, universally. `b_hit≥0.5` = 72% win.
**b_hit AUC 0.760** (vs single-stock 0.69/0.74) and is **regime-flat (.758/.761/.764)**.

### Per-stock (40/40 clean)
- win(b==0) < win(b>0): **40/40** — median 18.1% vs 60.0%.
- win(b≥0.5) > stock overall win: **40/40** — median 71.1%.
- b_hit AUC > 0.55: **40/40** — median 0.758, range 0.715 (HAVELLS) → 0.820 (BEL).

**VERDICT: REPLICATES (all-40), STRUCTURAL / regime-free — the single most universal tune.** GO
unconditionally: **drop `b_hit==0` (−0R → +0.19R, +9.6pp, 40/40); gate/prefer `b_hit≥0.5` (72% win).**
**Bug it implies:** the wired system takes the 23.7%-of-book `b_hit==0` firings — signals fired into a
session/time-bucket whose *null model* had zero follow-through — with **no baseline floor**. Add a
`b_hit>0` (ideally `≥0.5`) gate.

**Deep caveat (the real F6):** realized **edge is +0.075 overall but −0.055 at `b_hit≥0.5`** — the
detectors **do not beat their own baseline at the high end**; every detector wins 0.49–0.52 *regardless
of which detector it is* (compression edge −0.000; **htf_nest −0.047**, the only negative-edge detector →
F1 anti-signal replicates at scale). b_hit is a superb **ranker** of *when/where*, but the pattern adds
~0 edge over "was this a live tape." Use b_hit as a filter; do not read the 72% as detector skill.

---

## TUNE 3 — no-blind: strength / width / stacking are dead → **GO (universal), never gate on them**

AUC = P(feature higher on a win than a loss). Width = (zone_hi−zone_lo)/ATR; stacking = # concurrent
firings at the same (symbol, ts).

| feature | GLOBAL AUC | RANGE | UP | DOWN | per-stock median | in [.45,.55] |
|---|---|---|---|---|---|---|
| **strength** | 0.497 | 0.500 | 0.483 | 0.501 | 0.495 | **35/40** |
| **zone-width/ATR** | 0.493 | 0.489 | 0.498 | 0.497 | 0.486 | **36/40** |
| **stacking count** | 0.496 | 0.496 | 0.488 | 0.503 | 0.498 | **37/40** |
| **b_hit** (ref) | **0.760** | 0.758 | 0.761 | 0.764 | 0.758 | 0/40 (**40/40 > 0.55**) |

Win% by tercile (global) is flat/non-monotone: strength 50.5 / 49.4 / 49.6; width 50.5 / 49.9 / 48.9
(mildly *anti*: wider = slightly worse); stacking 50.2 / 49.1. No feature has a usable slope.

**VERDICT: REPLICATES (all-40), STRUCTURAL / regime-free.** strength, zone-width, and stacking are
**coin-flips (AUC 0.49–0.50, within noise of 0.5 on 35–37 of 40 stocks, all regimes)**; only `b_hit`
separates (0.76, 40/40). GO — **never gate/rank on strength, width, or stacking; gate on `b_hit`.**
**Bug it implies:** any grade/ranking term that reads detector `strength`, zone width, or confluence
count is spending confidence on **noise** — the wired grader's own scores predict nothing. Strip them;
put b_hit (+ the T3 stop-buffer) in the grade.

---

## 40-STOCK GO / NO-GO SUMMARY
| tune | 40-stock number | universality | regime split | verdict |
|---|---|---|---|---|
| **T3** SL wick ±0.25 ATR | tight-wick **+6.9pp** (pess) / hold 20% / 63% winners tag edge; sym-frame +4.2pp but −0.03R | **40/40** (both frames) | flat (R +7.3 / U +6.0 / D +6.7) | **GO** — ship; win-rate/geometry tune, needs large-R target for net-R; magnitude ~½ the +12pp claim |
| **b_hit gate** | drop b==0: **+9.6pp / −0R→+0.19R**; AUC **0.760**; b≥.5 = 72% win | **40/40** (all three tests) | flat (R/U/D +9.3/+9.7/+10.3) | **GO** — unconditional, strongest & most universal |
| **no-blind** | strength/width/stack AUC **0.49–0.50** (35–37/40 blind); b_hit 0.76 | **40/40** | flat | **GO** — never gate on them; gate on b_hit |

**All three hold universally on both range and trend stocks.** They are exactly the three the HUL
downtrend flagged as regime-free, and the 40-stock tape (21 range / 19 trend) confirms it: none of the
three shifts more than ~1pp / 0.01 AUC across RANGE↔UP↔DOWN. (The regime-*specific* levers — nest_depth
discriminator, T1 OTE-gate, nests-at-extreme — are out of scope here and remain range-only per §46-HUL.)

## HONEST CAVEATS
- One 17-day tape (≈16 D1 bars); regime labels are coarse (`_REGIME.md` §CAVEAT). Universality here means
  "stable across the 3 coarse buckets on this window," not multi-regime-proven.
- **T3** is measured in the study's **1-ATR outcome frame**, not the 1m 6-R re-race the single-stock
  studies used; that is *why* my lift (+5–7pp) is below their +11–12pp and why the symmetric-frame ΔExpR
  is negative. The mechanism (hold 20% / 63% winners-tag) matches to the point — ship it — but re-race on
  1m with the taught targets before trusting a net-R figure.
- **b_hit** is the config's own historical baseline → partly circular, and it is *high* on exactly the
  anti-signal detector (htf_nest, b_hit 0.519 / edge −0.047). Use it as a floor+ranker, never solo, and
  never read `b_hit≥0.5`'s 72% as detector edge (edge there is −0.055).
- Per-stock CSVs: `scratchpad/perstock_t3.csv`, `perstock_bhit.csv`, `perstock_auc.csv`.
