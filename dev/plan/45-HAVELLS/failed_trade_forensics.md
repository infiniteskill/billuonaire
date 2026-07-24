# 45-HAVELLS — FAILED-TRADE FORENSICS

**Question:** On HAVELLS, split firings into positive (`hit`) vs negative (`b_hit`/`loss`) forward
outcome (fwd12 bracket) and characterize *why the losers fail*. What concretely separates
winners from losers?

**Data:** `runs/validate/precision_study/evidence.parquet` filtered `symbol=='HAVELLS'`
(2,778 firings) + `runs/validate/tools/registry.jsonl` (159 hand marks) + `dev/IMG/trades/*`.
Window **2026-06-25 → 2026-07-17**, 5m/intraday. RECOGNITION only — no pipeline run.

---

## 0. Outcome definition (verified, not assumed)

`hit` column takes `{hit, loss, na, undecided}`. Directional-outcome rows = **1,719**
(864 `hit`, 855 `loss`; 987 `na` = neutral/pool marks, 72 `undecided`).

It is a **triple-barrier bracket, stop ≈ 1R**:
- every `loss` row has **MAE ≥ ~1.0R** (min 1.009) → the stop was tagged first;
- every `hit` row has **MFE ≥ ~1.0R** (min 1.013) → the target was tagged first.

So "why losers fail" = **why price ran 1R against the entry before it ran 1R for it.**

| outcome | n | mean fwd12 (R) | mean MFE | mean MAE |
|---|---|---|---|---|
| hit  | 864 | **+0.87** | 3.45 | 1.95 |
| loss | 855 | **−0.98** | 1.68 | 3.39 |

Baseline book (all 1,719): **win 50.3%, net +(-0.089)R / trade** — a coin flip that bleeds cost.
That is the thing to be fixed.

---

## 1. What separates win/lose — the single most important table (AUC on entry-known features)

AUC = probability a random winner ranks above a random loser on that feature. 0.50 = noise.

| feature (known at entry) | AUC | win mean | loss mean | verdict |
|---|---|---|---|---|
| **b_hit** (baseline hit-prob of the config) | **0.691** | 0.515 | 0.294 | **dominant separator** |
| b_fwd12 (baseline fwd return) | 0.649 | +0.10 | −0.93 | ~same info as b_hit |
| time-of-day (hour) | **0.574** | 12:29 | 12:01 | **2nd lever, orthogonal** |
| zone width (pts) | 0.475 | 2.41 | 2.59 | noise |
| zone width / ATR | 0.478 | 0.884 | 0.884 | **noise** |
| price position in zone | 0.495 | — | — | noise |
| **SL distance / ATR** (price→far edge) | 0.489 | 1.16 | 1.16 | **noise** |
| ATR (volatility regime) | 0.485 | 2.94 | 2.95 | noise |
| **detector `strength` score** | 0.495 | 0.677 | 0.681 | **noise (the system's own confidence does NOT predict outcome)** |

### Three honest, load-bearing negatives
1. **Zone geometry is NOT the lever.** Width, width/ATR, wick-vs-body (proxied by width &
   in-zone position), and **SL-distance-in-ATR all sit at AUC ≈ 0.48–0.49**. Winners and losers
   have statistically identical zones. "Draw a tighter/fatter box" or "pick a wickier zone" buys
   nothing on HAVELLS.
2. **`strength` is dead weight.** AUC 0.495 and non-monotonic across bins
   (0.55 / 0.49 / 0.51 / 0.53 / 0.47 for strength 0–.5/.5–.6/.6–.7/.7–.8/.8+). The detector
   confidence score separates nothing — keep it for display, never for gating.
3. **ATR/volatility does not separate.** Losers are not "high-vol" trades.

### b_hit is monotonic and strong (the whole edge lives here)
| b_hit bin | actual win | n |
|---|---|---|
| 0.00–0.10 | **27.8%** | 418 |
| 0.10–0.30 | 47.5% | 375 |
| 0.30–0.50 | 47.5% | 337 |
| 0.50–0.70 | 59.5% | 247 |
| 0.70–1.00 | **76.9%** | 342 |

---

## 2. Time-of-day — the second lever, and it is NOT inside b_hit

Win rate climbs cleanly across the session:

| session | win rate | n |
|---|---|---|
| open 09:15–09:45 | **42.4%** | 224 |
| morning 09:45–11:00 | 44.4% | 304 |
| midday 11:00–13:00 | 47.3% | 476 |
| early-PM 13:00–14:30 | 53.8% | 481 |
| **close 14:30–15:30** | **64.1%** | 234 |

Crucially, **b_hit is flat across sessions** (AM mean 0.443, PM mean 0.384 — AM is even *higher*),
yet AM wins 43.6% and PM wins 57.2%. The config-quality score cannot see the time effect, so the
two are **additive**:

| | b_hit ≥ .5 | b_hit < .5 |
|---|---|---|
| **AM (9:15–11)** | 61.4% | **30.0%** |
| MID (11–13) | 65.5% | 36.5% |
| **PM (13–15:30)** | **73.0%** | 48.2% |

**Combined GRADE = (b_hit ≥ .5) + (session == PM):**

| grade | win | net R/trade | n |
|---|---|---|---|
| 0 | 33.2% | **−0.773** | 599 |
| 1 | 55.3% | +0.023 | 861 |
| 2 | **73.0%** | **+1.745** | 259 |

---

## 3. TOP LOSER SIGNATURES (ranked by badness × size)

| # | signature (all known at entry) | win | net R | n | share |
|---|---|---|---|---|---|
| **L1** | **`b_hit == 0`** — baseline-dead config | **22.3%** | **−1.495** | 337 | 20% of book |
| **L2** | **AM (9:15–11) & b_hit < 0.3** | 28.3% | −0.910 | 212 | 12% |
| **L3** | **SHORT in AM (9:15–11)** | **37.3%** | — | 279 | 16% |
| **L4** | **plain `fvg` detector** (not fvg_n) | 42.9% | — | 154 | 9% |
| **L5** | **`CE_HOLD`** (premium_discount midline hold) | 42.3% | — | 137 | 8% |
| **L6** | **`htf_nest` / NEST** (see paradox below) | 41.7% | — | 36 | 2% |

Detector leaderboard (worst→best): `htf_nest` 0.417 · `fvg` 0.429 · `sweep` 0.490 ·
`fvg_n` 0.495 · `orderblock` 0.506 · `ob_taught` 0.538 · `wyckoff` 0.541 · `compression` 0.544.
Worst events: `NEST` 0.417 · `CE_HOLD` 0.423 · `FVG_N_RETEST` 0.477. Best: `MIT_RETEST` 0.597.

Direction × session (the worst single cell is **SHORT-AM 37.3%**):

| | AM | MID | PM |
|---|---|---|---|
| LONG | 0.506 | **0.389** | 0.539 |
| SHORT | **0.373** | 0.638 | 0.603 |

### The htf_nest / NEST paradox (honest caveat to the "edge = nest_depth" thesis)
NEST carries the **highest baseline b_hit (0.590)** of any detector yet delivers the **lowest
realized win (41.7%)**. Proximity test: a setup with an aligned NEST within 120 min wins **43.6%**
vs **52.4%** with no nest nearby — i.e. on HAVELLS in this window HTF-nest alignment is a mild
*anti*-signal, driven by the AM cohort (nest-AM b_hit 0.58 → win 31%, n=29). Small n (36 own /
404 aligned), so this is a flag to re-check nest_depth grading *on this symbol*, not a refutation
of the portfolio-level +6.13R tier.

---

## 4. Cross-check vs the user's own failed/adjustment marks (registry + images)

The hand-marks that carry loss/adjustment language line up exactly with L3/L5 (stops swept in the
morning around premium-discount / sweep entries):

- **T11a/b — "ALL SL TAKEN BY BANK AS LIQUIDITY SWEEP", "ALL LONG ENTRIES DESTROYED".**
  CE entry ~1300 (mid of box); user's note: the **true outer-wick SL is the sweep high ~1320**,
  not the box top. Entering the mid *before* the buy-side sweep completes = stopped by the sweep,
  then price drops to the target you were right about. This IS the L3 (SHORT-AM) / L5 (CE_HOLD)
  failure mode.
- **T10b — "03/07 spike tags SL then drops."** Tiny stop parked inside the wick range gets tagged,
  then the trade works — the fill-through / stop-placement lesson (matches L1: the config the
  system priced at b_hit≈0 is exactly these wick-tagged entries).
- **T3a — "ORDERBLOCK THAT GETS BROKEN AND INVALIDATED AS ORDER BLOCK."** Teaching example that a
  live OB can be invalidated — the plain-`fvg`/broken-OB family (L4).
- **t7 (proto-scratch)** — supply-OB short **entry 1270 / SL 1277 (7pt above SWING 1276) / tgt
  1252**; demand-OB long **entry 1246 / SL 1243 (3pt)**. Near-breakeven ("scratch") with a fragile
  3–7pt stop sitting just past the swing — the same "stop-inside-the-noise" fragility. Note the SL
  distance itself did NOT predict outcome (§1); it's *where* it sits (inside the sweep range)
  combined with AM timing that kills it.
- **T19 (DLF, same taught template):** visually the canonical winning shape — SWING LIQUIDITY
  **swept first**, THEN OB/ENTRY with SL *above* the swept extreme, then the drop. Losers are the
  same picture with entry placed *before* the sweep.

**Synthesis of the user's own notes:** the recurring hand-marked failure is **"entered before the
liquidity sweep, stop tagged by the sweep."** Our numbers render this as *AM shorts / CE-holds /
b_hit=0 wick-entries*.

---

## 5. THE CONCRETE TUNE THIS IMPLIES

1. **Gate on b_hit, not on strength or geometry.** Hard-drop `b_hit == 0` (removes 337 trades @
   22.3%/−1.495R — the single biggest bleed, 20% of the book). Prefer `b_hit ≥ 0.5`
   (keeps 39%, lifts to 67.0% / +1.05R). **Stop using `strength`, zone-width, and SL/ATR as gates
   — measured AUC ≈ 0.49.**
2. **Add a session gate (orthogonal, free lift).** Block/della-weight AM (9:15–11:00), especially
   **AM shorts (37.3%)**. Favor PM (13:00–15:30). The `GRADE = (b_hit≥.5) + (isPM)` score is
   monotonic 33% → 55% → **73%** and turns net R from −0.77 to **+1.745**.
3. **Enforce sweep-then-enter on the entry logic** (user's T11 lesson): require the buy/sell-side
   liquidity to be *taken* before arming a CE/OB entry, and anchor the stop **beyond the outer-wick
   sweep extreme**, not the box edge. This attacks the L3/L5/L1 cluster at the mechanism, not by
   widening the stop (widening alone is measured-neutral).
4. **Demote HTF-nest baseline weight on HAVELLS** (or re-derive nest_depth grading here): NEST's
   high b_hit is not earned on this symbol/window (41.7% realized, anti-signal AM). Re-check before
   trusting nest as a HAVELLS grader.
5. **Detector hygiene:** retire/di­scount plain `fvg` (42.9%) and `CE_HOLD` (42.3%) in favor of
   `ob_taught`/`wyckoff`/`compression`/`MIT_RETEST` (54–60%).

**Best single separator on HAVELLS = `b_hit` (AUC 0.691).** The best separator *not already in the
config score = time-of-day*, and stacking the two (GRADE) is the concrete, orthogonal win.
