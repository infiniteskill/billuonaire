# 46-HUL — FAILED-TRADE FORENSICS (re-verification of the HAVELLS findings)

**Question:** On HINDUNILVR, split firings by forward outcome (`hit` vs `loss`, symmetric-1ATR
bracket) and characterize why the losers fail. Does the HAVELLS story replicate — is `htf_nest` a
top LOSER signature (high b_hit, low realized win)? What separates HUL winners from losers, and is
the HAVELLS loser cluster (enter-before-sweep / AM shorts / blind strength / EQ-mid nests) present?

**Data:** firings-only study (HUL has NO hand-marks).
- `runs/validate/hul_study_2026/evidence.parquet` — 1225 rows, **19 sessions 2026-06-19→07-16**,
  1088 directional-decided (551 hit / 537 loss).
- `runs/validate/hul_study_2024/evidence.parquet` — 3577 rows, **61 sessions 2024-09-02→11-29**
  (finished writing mid-study), 3123 decided. Used as an out-of-regime robustness window.
- Raw 1m `data/wide/HINDUNILVR.csv` (2026) + `data/regime_2024q4/HINDUNILVR.csv`, resampled
  (pandas) to 15m/1h/1d for HTF nest-depth. RECOGNITION only — no pipeline / `derive_tradebook`.

**Outcome frame (verified, not assumed):** identical to HAVELLS. `hit∈{hit,loss,na,undecided}`;
decided = `{hit,loss}`. It is a **symmetric 1-ATR target / 1-ATR stop** bracket — every `loss`
has MAE ≥ 1.00 (min 1.001), every `hit` has MFE ≥ 1.00 (min 1.000). `mfe/mae/fwd*` are ATR-units.
- HUL 2026 book: **win 50.6%, net fwd12 +0.057R** (HAVELLS 50.3% / −0.089R) — the same coin-flip.
- HUL 2024 book: **win 53.2%.** Both HUL windows reconfirm the 0.52-AUC coin flip on a new symbol.

---

## VERDICT TABLE — does each HAVELLS finding replicate on HUL?

| # | HAVELLS finding | HAVELLS number | HUL 2026 | HUL 2024 | verdict |
|---|---|---|---|---|---|
| **b_hit** | dominant separator (AUC) | 0.691 | **0.739** | **0.741** | **REPLICATES — STRONGER** |
| **F1** | `htf_nest` = top loser: highest b_hit, lowest realized win (anti-signal) | b_hit 0.590 / win 41.7% / edge −(anti) | **b_hit 0.532 (highest) / win 44.7% / edge −8.4pp** | **b_hit 0.591 (highest) / win 31.2% / edge −27.9pp** | **REPLICATES** (2024 is dead-on) |
| F1-mech | the drag is **EQ-mid furniture** nests (~40% hit) | EQ-mid ~40% vs extreme 80% | drag = **PREMIUM SHORTS** 40.7%; no EQ-mid nests | drag = **PREMIUM SHORTS 17.1%** vs discount-longs 42.2% | **mechanism DIFFERS** (short-side, not mid) |
| **F2** | EXT anchored to latest swing, never re-anchors → best setup invisible (`zone_hi` never reaches true extreme) | zone_hi ≤1201.2 vs true 1234 (~14 ATR gap) | zone_hi 2231.5 vs true 2238.8 (**1.8 ATR** gap); zone_lo 2113 vs 2091 (5.5 ATR) | — | **WEAKER / mostly ABSENT** |
| **nest_depth** | real monotone discriminator (win 43→58%, fwd12 −0.65→+0.96, p≈5e-7) | depth 0/1/2/3 = 42.9/46.4/57.7/55.8 | **54.4/46.0/52.8/46.8 — flat/negative** (corr −0.05, fwd12 corr −0.15) | — | **ABSENT / INVERTED** |
| **T1** | OTE-gate base (short pos≥.62 / long ≤.38) → extreme nests 80% vs mid 40% | 80% vs 40% | **INVERTED**: extreme trades win **49.5%** vs mid/rest **53.5%** | — | **ABSENT** |
| **F3** | tiny outer-wick stop shaken out; SL-hold 30.3%; 62% of winners tag exact-edge stop; +0.25ATR → 44→55% | 30.3% / 62% / +11pp | SL-hold **33.4%**; winners-tag **28.9%**; buffer **54.8→60.6% (+5.8pp)** | — | **REPLICATES — WEAKER** |
| **F5** | enter-before-sweep, **AM shorts worst** (SHORT-AM 37.3%) | 37.3% (worst cell) | **SHORT-AM 48.8%** (worst cell is LONG-MID 39.3%) | SHORT-AM 48.0% (worst LONG-MID 46.5%) | **ABSENT** |
| **F6** | strength / zone-width / SL-dist / position are **blind** (AUC ≈0.48–0.50) | strength 0.495 etc. | strength **0.476**, zw/ATR 0.476, SL/ATR 0.472, pos 0.485 | strength **0.490** | **REPLICATES** |
| time | time-of-day 2nd lever, AUC 0.574; PM≫AM | 0.574; AM 43.6 / PM 57.2 | **0.528**; AM 49.6 / PM 55.2 (mild) | **FLAT** AM 52.8 / MID 54.1 / PM 52.7 | **WEAKER→ABSENT** |
| L1 | `b_hit==0` = biggest bleed | 22.3% / −1.495R / 20% | **22.6% / −1.072R / 23%** | 23.3% / (n627) | **REPLICATES** |
| L4/L5 | plain `fvg` (42.9%) & `CE_HOLD` (42.3%) losers | 42.9 / 42.3 | fvg **51.7%**, CE_HOLD **52.0%** | fvg 54.7% | **ABSENT** |

---

## 1. The single best separator — `b_hit` (STRONGER than on HAVELLS)

AUC = P(random winner ranks above random loser). Table is HUL 2026 beside the HAVELLS number.

| feature (known at entry) | HUL AUC | HAVELLS AUC | verdict |
|---|---|---|---|
| **b_hit** (config baseline hit-prob) | **0.739** | 0.691 | **dominant separator — stronger on HUL** |
| b_fwd12 | 0.693 | 0.649 | ~same info as b_hit |
| time-of-day (hour) | 0.528 | 0.574 | weaker (see §3) |
| ATR (vol regime) | 0.516 | 0.485 | noise |
| price position in zone | 0.485 | 0.495 | noise |
| zone width / ATR | 0.476 | 0.478 | **noise** |
| **detector `strength`** | **0.476** | 0.495 | **noise (own confidence predicts nothing)** |
| SL distance / ATR (price→far edge) | 0.472 | 0.489 | **noise** |
| zone width (pts) | 0.475 | 0.475 | noise |

**b_hit is monotone and carries the whole edge** (HUL 2026 | HAVELLS 27.8/47.5/47.5/59.5/76.9):

| b_hit bin | HUL win | n |
|---|---|---|
| 0.00–0.10 | **23.1%** | 260 |
| 0.10–0.30 | 40.0% | 180 |
| 0.30–0.50 | 45.9% | 185 |
| 0.50–0.70 | 59.9% | 172 |
| 0.70–1.00 | **79.4%** | 291 |

`strength` is **anti-monotone** on HUL (win 60.0/55.3/49.7/47.3/52.1 across 0–.5/.5–.6/.6–.7/.7–.8/.8+)
— higher detector confidence, *lower* realized win. Never gate on strength. (**F6 REPLICATES**, and
the 2024 window confirms: strength AUC 0.490.)

**GRADE = (b_hit≥.5)+(isPM)** is still monotone on HUL despite the weaker time term
(HUL 2026 | HAVELLS 33.2/−0.773 · 55.3/+0.023 · 73.0/+1.745):

| grade | HUL win | HUL net fwd12 | n |
|---|---|---|---|
| 0 | 31.5% | **−0.528R** | 432 |
| 1 | 60.5% | +0.436R | 512 |
| 2 | **72.9%** | **+0.927R** | 144 |

The top tier lands at **72.9%**, essentially identical to HAVELLS 73.0% — but the lift is carried by
**b_hit**, not by the PM term (which is weak here).

---

## 2. Detector leaderboard + the `htf_nest` paradox (F1 — REPLICATES)

HUL 2026 decided, worst→best win%:

| detector | win% | b_hit | edge | fwd12 | n |
|---|---|---|---|---|---|
| ob_taught | 40.6% | 0.304 | +10.2pp | −0.61 | 69 |
| compression | 41.5% | 0.458 | **−4.3pp** | +0.05 | 65 |
| **htf_nest** | **44.7%** | **0.532 (highest)** | **−8.4pp** | −0.27 | 38 |
| sweep | 48.2% | 0.446 | +3.6pp | −0.17 | 56 |
| fvg | 51.7% | 0.456 | +6.1pp | +0.26 | 180 |
| fvg_n | 51.8% | 0.377 | +14.2pp | +0.07 | 245 |
| orderblock | 52.1% | 0.418 | +10.3pp | +0.16 | 217 |
| wyckoff | 53.9% | 0.450 | +8.9pp | +0.21 | 193 |
| propulsion2 | 60.0% | 0.342 | +25.8pp | −0.63 | 25 |

**F1 REPLICATES.** `htf_nest`/NEST has the **single highest b_hit of any detector (0.532)** yet the
**most-negative edge among real-n detectors (−8.4pp)** — the config prices it as a top-quality signal
and it under-delivers. This is the HAVELLS 0.590/41.7% anti-signal, on HUL. It gets *cleaner and
stronger in 2024-Q4*: **htf_nest b_hit 0.591 (again the highest), win 31.2%, edge −27.9pp, n=80** —
a near-exact match to the HAVELLS 0.590/41.7% paradox (even more extreme). Two independent HUL
windows both flag `htf_nest` as the same over-priced anti-signal.

**But the MECHANISM differs from HAVELLS.** On HAVELLS the drag was *EQ-mid furniture* nests (~40%).
On HUL there are **no EQ-mid nests** — all 38 are polarized (27 premium-shorts, 11 discount-longs).
The drag is entirely the **PREMIUM-SHORT side**:
- HUL 2026: premium-short nests **40.7%** (n27) vs discount-long nests **54.5%** (n11).
- HUL 2024: premium-short nests **17.1%** (n35) vs discount-long nests **42.2%** (n45).

So `htf_nest`'s anti-signal on HUL is not furniture-depth; it is that **shorts taken into the D1
premium extreme fail** on this symbol. Same outcome as HAVELLS, opposite cause — which is exactly
why the HAVELLS *fix* (T1 OTE-gate, §4) does **not** transfer.

Worst *events*: BRK_RETEST 35.7% (n14), MIT_RETEST 38.9% (n18), BOX_ON_LEVEL 41.5%, **NEST 44.7%**.
Note MIT_RETEST was HAVELLS' *best* event (59.7%) — **ABSENT/reversed** here.

---

## 3. Time-of-day — the HAVELLS 2nd lever is WEAK on HUL, gone in 2024

| session | HUL 2026 win | n | HAVELLS |
|---|---|---|---|
| open 09:15–09:45 | 47.3% | 146 | 42.4% |
| morning 09:45–11:00 | 50.9% | 265 | 44.4% |
| midday 11:00–13:00 | 47.4% | 340 | 47.3% |
| early-PM 13:00–14:30 | 52.3% | 222 | 53.8% |
| **close 14:30–15:30** | **60.9%** | 115 | **64.1%** |

The PM-close is still the best bucket (60.9% vs HAV 64.1%), so the *sign* survives, but AM is **not**
depressed (open 47.3, morning 50.9) — AM 49.6% vs PM 55.2% (HAV 43.6 / 57.2). AUC 0.528 vs 0.574.
**In 2024-Q4 the effect is entirely flat: AM 52.8 / MID 54.1 / PM 52.7.** ⇒ time-of-day **REPLICATES
WEAKLY in 2026, ABSENT in 2024** — treat it as HAVELLS-window-specific, not a portable lever.

---

## 4. nest_depth & the OTE gate (T1) — DOES NOT replicate on HUL

Replicated the `htf_alignment` method exactly: resample 1m → 15m/1h/1d, `merge_asof` each firing to
the last **closed** HTF bar, `pos = (price−swLo)/(swHi−swLo)` on each HTF causal swing range, aligned
if LONG `pos≤0.5` / SHORT `pos≥0.5`, `depth` = count of the 3 HTFs aligned.

| depth | HUL win% | HUL fwd12 | n | HAVELLS win% | HAVELLS fwd12 |
|---|---|---|---|---|---|
| 0 | 54.4% | +0.320 | 384 | 42.9% | −0.646 |
| 1 | 46.0% | +0.585 | 202 | 46.4% | −0.293 |
| 2 | 52.8% | −0.439 | 233 | 57.7% | +0.025 |
| 3 | 46.8% | −0.291 | 269 | 55.8% | +0.962 |

**Non-monotone, sign-inverted.** SHALLOW(0-1) 51.5% vs DEEP(2-3) 49.6% — deep is *worse*.
`corr(depth,win)=−0.046`, `corr(depth,fwd12)=−0.149` (HAVELLS +0.112 / +0.187, p≈5e-7). The
OTE-strict variant (1/3, 2/3) is the same story (51.3/52.8/50.6/**45.2**, deep 48.0 vs shallow 51.8).

**Direction split** (HAVELLS LONG 37.8/41.4/50.9/**62.1** ; SHORT 45.3/52.7/**72.2**/48.0):
- HUL LONG: 41.6/43.1/48.3/**51.9** — monotone-up but *weak* (tops 51.9 vs HAV 62.1). Discount-nesting
  for longs is the only piece that survives, faintly.
- HUL SHORT: 60.6/47.7/66.1/**39.6** — depth-3 premium shorts **crater to 39.6%** (n111). The deep
  premium-extreme short is the loser, not the winner. This is the §2 htf_nest drag, re-derived causally.

**Within-detector shallow→deep lift** (HAVELLS retest detectors +17–22pp):

| detector | HUL lift | HAVELLS lift |
|---|---|---|
| ob_taught | **−8.1pp** | +21.9 |
| fvg_n | +2.6pp | +17.4 |
| wyckoff | +4.9pp | +18.3 |
| fvg | +2.5pp | +11.9 |
| orderblock | **−21.4pp** | +3.8 |
| compression | +22.8pp | −7.1 |

The clean +17–22pp retest-detector lift is **ABSENT** (retests show +2–5pp noise; orderblock inverts).

**T1 OTE-gate (the HAVELLS #1 recommendation) is INVERTED on HUL.** Gating the base zone to the
correct-side D1 extreme (short pos≥.62 / long pos≤.38, causal daily range):

| cohort | win% | net fwd12 | n |
|---|---|---|---|
| PASS OTE gate (correct-side D1 extreme) | **49.5%** | −0.245R | 408 |
| FAIL (EQ-mid / wrong side) | **53.5%** | +0.352R | 579 |

On HUL the **extreme** trades are the *worse* half — the exact opposite of HAVELLS' "extreme nests hit
80% vs mid 40%." SHORT-premium 50.0% vs rest 56.2%; LONG-discount 49.2% vs rest 49.8% (no lift).
⇒ **nest_depth, the depth×extreme rule, and the T1 gate are HAVELLS-specific and must NOT be applied
to HUL as-is.** (Proxy caveat: causal swing-range, not the live EXT-band overlap — but the sign is
robust across both the half and 1/3-2/3 definitions, and is corroborated by the raw htf_nest rows.)

---

## 5. F2 — EXT anchoring: WEAKER on HUL (the extreme is mostly reached)

HUL 2026 raw D1 dealing range = **2091.0 – 2238.8** (EQ 2164.9, span 147.8pt ≈ 37 ATR).
Across all 38 `htf_nest` rows, `zone_hi` reaches **2231.5** — only **7.3pt (1.8 ATR)** below the true
D1 high (HAVELLS: 33pt / ~14 ATR short of the extreme). `zone_lo` reaches 2113.3, 22.3pt (5.5 ATR)
above the true low. ⇒ On HUL the EXT anchor **does** track the upper extreme; the "best setup is
structurally invisible" failure is **WEAK on the high side, mild on the low side** — largely a
HAVELLS-specific artifact of that stock's late 1234 spike. (And here reaching the extreme does not
help — §4 — so re-anchoring would not buy HUL anything.)

---

## 6. F3 — tiny outer-wick stop: REPLICATES, weaker

1m first-touch race, forward 120 min, stop = zone far edge (outer-wick proxy), target = entry ±1 ATR:

| stop placement | HUL win | HAVELLS win |
|---|---|---|
| exact wick edge | 54.8% | 44.1% |
| edge + 0.10 ATR | 57.7% | 48.3% |
| edge + 0.25 ATR | **60.6%** | **55.4%** |

- **SL-hold at exact edge (adverse never tags stop): HUL 33.4%** (HAVELLS 30.3%) → the tiny taught
  stop is breached **~67%** of the time on HUL too. **REPLICATES.**
- **+0.25 ATR buffer lifts win 54.8→60.6% (+5.8pp)** — same sign as HAVELLS (+11pp) but **weaker**,
  because far fewer eventual winners are wicked out: **28.9% of eventual winners first tag the
  exact-edge stop on HUL vs 62% on HAVELLS.** The shakeout is real but milder here.

Net: the "buffer the outer-wick stop by ~0.25 ATR" tune is directionally confirmed on HUL (free
+5.8pp), the strongest *transferable* structural tune from the HAVELLS set.

---

## 7. HUL loser signatures (ranked) vs HAVELLS L1–L6

| # | signature | HUL win | HUL net R | n / share | HAVELLS | verdict |
|---|---|---|---|---|---|---|
| **L1** | **`b_hit==0`** | **22.6%** | **−1.072R** | 252 / 23% | 22.3% / −1.495 | **REPLICATES (biggest bleed)** |
| L2 | AM & b_hit<0.3 | 26.7% | −0.526R | 165 / 15% | 28.3% | REPLICATES |
| — | `b_hit==0` & MID | **21.5%** | **−1.214R** | 93 / 9% | — | HUL variant of L1 |
| — | LONG in MID (11–13) | 39.3% | −0.629R | 173 / 16% | — | **HUL-specific worst cell** |
| L6 | `htf_nest`/NEST | 44.7% | −0.266R | 38 / 3% | 41.7% | REPLICATES (anti-signal) |
| — | ob_taught | 40.6% | −0.606R | 69 / 6% | 53.8% (a HAV *winner*) | **HUL-specific loser** (but low b_hit = priced-in) |
| — | compression | 41.5% | +0.052R | 65 / 6% | 54.4% (a HAV winner) | **HUL-specific loser** |
| **L3** | SHORT in AM | **48.8%** | +0.223R | 211 | **37.3%** | **ABSENT** |
| **L4** | plain `fvg` | **51.7%** | +0.261R | 180 | 42.9% | **ABSENT** |
| **L5** | `CE_HOLD` | **52.0%** | +0.230R | 173 | 42.3% | **ABSENT** |

`b_hit==0` = **23% of the HUL book at 22.6% / −1.072R** — the single largest, cleanest bleed, and the
one dominant, transferable gate. `b_hit≥0.5` = 72.1% / +0.903R (n463). The HAVELLS "enter-before-
sweep" cluster (L3 AM-shorts, L5 CE-hold) is **absent** on HUL; HUL's own worst cells are
**b_hit==0 / b_hit==0-in-midday / LONG-midday**, plus the priced-in ob_taught & compression.

---

## 8. 2024-Q4 out-of-regime robustness (n=3123 decided, 61 sessions)

The second HUL window (3× the sample, different price regime 2091→2795) **sharpens the portable
findings and kills the non-portable ones**:
- **b_hit AUC 0.741** (2026 0.739, HAV 0.691) — dominant separator, stable across both windows.
- **b_hit==0 win 23.3% / b_hit≥0.5 win 73.0%** — L1 bleed + grade tiers reproduced exactly.
- **strength AUC 0.490** — F6 (blind confidence) reproduced.
- **`htf_nest` b_hit 0.591 (highest) / win 31.2% / edge −27.9pp, n80** — a near-perfect match to the
  HAVELLS 0.590/41.7% paradox, driven by **premium-shorts 17.1%** vs discount-longs 42.2%.
- **time-of-day FLAT** (AM 52.8 / MID 54.1 / PM 52.7) and **SHORT-AM 48.0%** (not worst) —
  time-lever and AM-short signature are confirmed **not portable**.

---

## 9. The concrete tune this implies for HUL

1. **Gate on `b_hit` — the one lever that transfers.** Drop `b_hit==0` (23% of book @ 22.6% /
   −1.072R); prefer `b_hit≥0.5` (72.1% / +0.903R). AUC 0.739/0.741 across both windows. Do **not**
   gate on `strength`/width/SL-dist/position (all AUC ≈0.47–0.52; strength is anti-monotone).
2. **Demote `htf_nest` on HUL and re-derive its parents — do NOT apply the HAVELLS T1 OTE gate.**
   htf_nest is the over-priced anti-signal here too (b_hit highest, edge −8.4/−27.9pp), but the cause
   is **premium-short failure**, not EQ-mid furniture, so OTE-gating to the extreme *hurts* (49.5% vs
   53.5%) and nest_depth is flat/inverted (corr −0.05). The depth×extreme=80% rule is HAVELLS-specific.
3. **Buffer the outer-wick stop by ~0.25 ATR** — the one *structural* HAVELLS tune that transfers:
   +5.8pp realized win (54.8→60.6%), tiny-stop breached ~67% on HUL too.
4. **Skip the session gate on HUL** — time-of-day is weak (2026) to absent (2024); AM-shorts are not a
   loser here (48.8%). HUL's own worst non-b_hit cell is **LONG-midday 39.3%**, not AM-shorts.

**Best single separator on HUL = `b_hit` (AUC 0.739 / 0.741), stronger than on HAVELLS.** The HAVELLS
*b_hit / F6 / F3 / L1 / htf_nest-anti-signal* findings **replicate**; the *nest_depth discriminator,
T1 OTE gate, F2 EXT-invisibility, AM-shorts (F5), plain-fvg/CE_HOLD (L4/L5), and time-of-day* are
**HAVELLS-specific and do not transfer to HUL.**
