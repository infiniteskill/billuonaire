# 46-HUL — HTF-ALIGNMENT / nest_depth as winner/loser discriminator: RE-VERIFICATION (2026-07-24)

**Question (re-verify the 45-HAVELLS study on a second stock):** does HTF-alignment /
`nest_depth` — the premium/discount decisional-zone nesting that drove HAVELLS depth 0→3 win
**43→58%** — separate HUL winners from losers? And does **T1** (OTE-gate the base on the correct
D1 side: short `pos≥0.62` / long `pos≤0.38`) lift HUL win% like the HAVELLS prediction (LONG
48→70 / SHORT 31→70)?

**Answer: NO — the depth/premium-discount lever does NOT replicate on HUL; T1 does not lift.**
`nest_depth` is non-monotone and mildly *inverted* on HUL (corr(depth,win)=−0.05), and the
D1-OTE base gate produces **zero lift** (LONG 47.1→47.2, SHORT 54.0→**51.0**, i.e. slightly
*worse*). **Root cause is regime:** HUL 2026 is a **persistent downtrend** (net **−5.0%** over 19
sessions, close at the **5th percentile** of range) — *not* the range-bound tape HAVELLS was
(defined range, EQ midpoint). Premium/discount nesting is a **range-fade** tool; on a trending
tape it goes null-to-inverted (shorting from *discount*/momentum ties shorting from premium; buying
*discount* catches the falling knife). **The two mechanical, regime-free findings — F1 (htf_nest is
a mild anti-signal) and F6 (native confidence features are blind, b_hit dominates) — REPLICATE
cleanly.** The direction-lever findings (depth, T1, "nests-at-extreme") are **ABSENT** here, and the
stop/session findings (F2/F3/F5) replicate **weakly / same-sign**. HUL is a downtrend-regime
counter-sample: it does not refute the HAVELLS mechanism, it shows the lever **collapses
out-of-its-regime** — exactly the 45-SYNTHESIS "one 17-day regime" caveat, now measured.

---

## 0. Data & method (same recipe as 45-HAVELLS §1)
- **Firings+outcomes:** `runs/validate/hul_study_2026/evidence.parquet` — 1225 firings, ts
  2026-06-19→07-16 (19 sessions). Decidable set (`hit∈{hit,loss}`) = **1088** (551 hit / 537 loss;
  overall win% **50.6%** — the same 0.52-AUC coin flip HAVELLS reconfirmed at 50.3%). `na` (102) &
  `undecided` (35) excluded.
- **HTF context:** resampled `data/wide/HINDUNILVR.csv` (1m, 7125 bars) with pandas
  `resample(...).agg(OHLCV)` → **15m (475) / 1h (133) / 1d (19)**. Causal merge (`merge_asof`
  backward on bar close-time) to the last CLOSED HTF bar (doc-36 caution C).
- **Alignment per HTF (ZONE nest = premium/discount):** `pos=(price−swLo)/(swHi−swLo)`; LONG
  aligned if `pos≤0.5` (HTF discount), SHORT if `pos≥0.5` (HTF premium). `depth` = count of the 3
  HTFs aligned. Swing range = per-TF rolling lookback (primary 15m=24/1h=24/1d=20 bars); **result
  is robust to lookback 10/40** (below). The **D1 dealing range** for T1 uses the causal cumulative
  daily high/low (the unambiguous "D1 OTE" anchor).
- **NOTE on the confirmed-EXT variant:** the detector's own percent-leg zigzag (`leg_pct=6.0` →
  K clipped to 14·ATR) yields **~0 confirmed pivots** on this 19-day intraday window per TF — the
  live EXT bands are structurally **sparse** here (itself a data point for F2). So the reproduction
  uses the rolling-range proxy, as the HAVELLS study did ("alignment is a proxy", HAVELLS §7).
- **2024-Q4 (`hul_study_2024`):** outcome parquet **absent** — only 274 graded *verdict* jsonl rows,
  no `hit`. Its tape is **also a downtrend** (net **−10.8%**, close at 18th pct of range), so it
  offers no range-regime test either. 2026 is the sole outcome study.

---

## 1. HEADLINE — HUL win% + fwd-R by HTF nest depth (vs HAVELLS)
(directional decided set n=1088; primary lookback; `base%`=mean b_hit; fwd=mean fwd12-R)

| depth | HUL n | **HUL win%** | HUL base% | HUL fwd12 | | HAVELLS win% | HAVELLS fwd12 |
|---|---|---|---|---|---|---|---|
| **0** | 395 | **54.7** | 44.1 | +0.31 | | 42.9 | −0.65 |
| **1** | 184 | **46.2** | 41.2 | +0.85 | | 46.4 | −0.29 |
| **2** | 204 | **50.5** | 45.3 | −0.63 | | 57.7 | +0.03 |
| **3** | 305 | **48.2** | 37.3 | −0.32 | | 55.8 | +0.96 |

- **HUL win% is NON-MONOTONE** (54.7 / 46.2 / 50.5 / 48.2) — depth-0 is the *highest* cell; HAVELLS
  was cleanly monotone-up 42.9→57.7.
- **Shallow(0-1) 52.0% (n=579) vs Deep(2-3) 49.1% (n=509): z=−0.94 (NS) — deep is *worse*.**
  HAVELLS: shallow 44.8 vs deep 57.0, z=+5.0, **p≈5e-7**.
- **corr(depth,win)=−0.046, corr(depth,fwd12)=−0.166** (both NEGATIVE). HAVELLS: +0.112 / +0.187.
- **Robust to swing-window:** lookback 10/10/20 → deep 50.9 vs shallow 50.4 (flat); 40/40/20 → deep
  49.8 vs shallow 51.4 (flat). No window produces a HAVELLS-style monotone.
- **Direction split** (why it cancels): LONG depth 0→3 = 43.4/47.2/48.0/49.1 (weak +5.7pp monotone —
  deeper discount-nesting *does* help longs, the HAVELLS sign); **SHORT** depth 0→3 =
  **60.6/45.5/57.1/47.0** (anti — shorting the deep-premium nest is *worse*, opposite sign). They
  net to zero.

> **VERDICT — nest_depth discriminator: ABSENT (mildly inverted).** Same headline number HAVELLS
> tested (50.3 vs 50.6 coin-flip) but the depth separation is gone; only the LONG half keeps the
> HAVELLS sign, the SHORT half inverts, net-null.

---

## 2. T1 — OTE-gate the base zone on the correct D1 side (the headline test)
Base-zone mid position in the causal cumulative **D1** range; gate SHORT `pos≥0.62` (premium) /
LONG `pos≤0.38` (discount). D1-pos available for 1044/1088; OTE-correct share 44.0%.

| side | HUL ungated | **HUL OTE-gated** | HAVELLS prediction |
|---|---|---|---|
| LONG | 47.1 (n=529) | **47.2 (n=282)** | 48 → **70** |
| SHORT | 54.0 (n=559) | **51.0 (n=210)** | 31 → **70** |

- **T1 delivers ZERO lift on HUL** — LONG flat (+0.1pp), SHORT **negative** (−3.0pp). The predicted
  +22/+39pp lift is entirely absent.
- **Why (premium/discount is flat, not a discriminator, on this tape):** win% by side × D1
  price-tercile —
  - LONG: discount 45.3 / mid 51.5 / **premium 44.4** — buying discount does **not** beat buying
    premium (both ~45); the taught "long the discount" edge is gone.
  - SHORT: **discount 52.0** / mid 48.6 / premium 52.4 — shorting *discount* (momentum
    continuation down) equals shorting premium; the taught "short the premium" edge is gone.
  Location (premium/discount) carries **no** signal; **side** (short>long, the downtrend) carries it
  all. Gating on OTE-side just throws away half the shorts for no gain.

> **VERDICT — T1: ABSENT.** The single highest-leverage HAVELLS tune does not transfer to HUL's
> trending tape. It needs a range/EQ-defined regime to bite; HUL 2026 doesn't have one.

---

## 3. Per-finding replication scorecard (HUL numbers beside HAVELLS)

| # | HAVELLS finding | HAVELLS number | **HUL number** | verdict |
|---|---|---|---|---|
| **F1** | `htf_nest` grades EQ-mid furniture → **anti-signal** (highest baseline, lowest realized win) | win **41.7** / b_hit **0.590** / anti | win **44.7** / b_hit **0.532** / edge **−8.4pp**; fires at D1 pos median **0.33** (lower-mid furniture) | **REPLICATES** |
| **nest@extreme** | nests AT a D1 extreme hit **80%** vs EQ-mid **40%** (+40pp) | 80 vs 40 | D1-extreme **56.1** (n=380) vs EQ-mid **52.8** (n=229) = **+3.3pp**; SHORT-at-premium-extreme **35.7** (worst) | **ABSENT / WEAK** |
| **F2** | EXT anchored to latest swing, never re-anchors range extreme (`zone_hi` capped ~33pt below the true high) | zone_hi ≤ 1201.2, true 1234 | zone_hi within **7.3pt** of window high **but** zone_lo stays **22.3pt above** the fresh (trend-side) low; EXT pivots ~0 on window | **WEAKLY REPLICATES** |
| **F3** | tiny outer-wick stop shaken out: **62%** of winners tag the exact edge; +0.25ATR buffer 44→55% | 62% ; +11pp | **45.9%** of winners' MAE reaches the exact edge; +0.25ATR buffer saves **6.7%** of winners (2.8% of losses rescuable) | **WEAKER** (same sign; MAE-proxy) |
| **F5** | enter-before-sweep: **AM shorts worst** (37.3%), PM better | AM-short 37.3 | SHORT **AM 48.8 vs PM 57.2** (−8.4pp, same sign) — but not the single worst cell (PM-long 45.0 lower) | **WEAKER / PARTIAL** |
| **F6** | strength / zone-width / stacking **AUC ~0.48 = blind**; b_hit dominates | 0.495 / 0.478 / 0.489 ; b_hit 0.691 | strength **0.476** / width **0.476** / sl-dist **0.472** ; **b_hit 0.739** | **REPLICATES (strong)** |

**Reading the scorecard:** the two findings that are **mechanical and regime-free** — F1 (the wired
`htf_nest` mis-grades → mild anti-signal) and F6 (the detectors' own confidence scores are blind,
only the config baseline `b_hit` predicts) — **replicate cleanly and are the durable HUL result.**
Every finding that depends on the **premium/discount fade** working (depth, T1, nest@extreme)
is **ABSENT** on the downtrend. The stop/session micro-findings (F2/F3/F5) replicate **weakly,
same-sign** but milder.

---

## 4. Root cause — regime, not stock (the honest synthesis)
- HUL 2026: daily open→close **2208 → 2098, net −5.0%**, window 2091–2239 (7.1% range), close at
  the **5th percentile** — a clean **downtrend**. HAVELLS 2026 was **range-bound** (1140–1234, EQ
  1180), which is *exactly* the tape where "buy discount / sell premium, nested" is designed to win.
- On a trend, **the location lever inverts/nulls and the direction lever (momentum) dominates**:
  HUL SHORT 54.0% > LONG 47.1% (short-the-downtrend), and depth/OTE — which encode *fading the
  range* — separate nothing. This is not a HAVELLS error; it is the lever operating **out of its
  regime**.
- **HUL cannot confirm OR refute the HAVELLS range mechanism** — both available HUL windows (2026
  −5.0%, 2024-Q4 −10.8%) are downtrends, and 2024 has no outcome parquet. What HUL *does* prove:
  (a) the wired `htf_nest`/confidence blindness (F1/F6) is **stock-general**, and (b) the
  premium/discount direction-edge is **regime-gated** — it must be paired with a trend/range filter
  before it is trusted on a new symbol.

---

## 5. What this implies for the tune stack
1. **The F1+F6 fixes are safe to generalise** — `htf_nest` mis-grades furniture on HUL too (keep it
   off solo; it is a mild anti-signal, edge −8.4pp), and native strength/width/stacking are blind on
   HUL too (AUC ~0.47) while **b_hit is even stronger here (0.739 vs HAVELLS 0.691)** — the
   "gate on b_hit, never on strength/width" rule holds.
2. **T1 (and depth-≥2) must carry a regime gate.** On HUL's trend the OTE base-gate is inert-to-
   negative. Before shipping T1 as a universal grade term, pair it with a trend/range classifier
   (e.g. D1 close-position-in-range, or an ADX/EMA-slope filter) so premium/discount only *counts*
   on range-defined tape — otherwise it will bleed edge on trending symbols.
3. **The direction (momentum) lever is the live edge on trends** — SHORT>LONG by ~7pp on HUL,
   monotone with the daily drift. A regime-aware system should *flip* from fade (range) to
   continuation (trend), not apply premium/discount blindly.
4. **F3 SL-buffer still net-positive** (fewer rescues here, 6.7% of winners, but same sign) — a
   cheap, regime-independent add.

## 6. Honest caveats
- **One stock, one 19-day downtrend regime; 2024-Q4 outcomes absent.** The ABSENT verdicts are
  "absent *on a downtrend*", not "the HAVELLS mechanism is false" — they are the complementary
  regime to HAVELLS's range, and together they argue the lever is **regime-conditional**.
- **Swing-range is a rolling-lookback proxy** (the confirmed-EXT zigzag is too sparse on this
  window); depth non-monotonicity is robust across lookback 10/24/40 but the exact cell win%s would
  shift under the true detector.
- **F3 is an MAE-proxy** (did realized adverse excursion reach the exact edge), not a 1m
  first-touch race; direction is trustworthy, the 45.9% magnitude is approximate.
- **Small-n cells:** SHORT-at-premium-extreme n=28, htf_nest n=38 — treat with the usual suspicion.
