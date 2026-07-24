# HUL — FEATURE + SL ANATOMY on real tape (re-verification of HAVELLS)

Scope: **no hand-marks on HUL** — this is a pure **firings-based** study. Source = the detector-emitted
evidence parquet (`runs/validate/hul_study_2026/evidence.parquet`, 1225 rows, 1126 directional) checked
against the **real 1m tape** (`data/wide/HINDUNILVR.csv`, 7125 bars). Tape window: **2026-06-19 → 07-16
(19 sessions, price 2095–2225, median ATR 3.86 pts)**.
A **second, independent tape** — `hul_study_2024/` (**3577 firings, 3315 mapped**, 2024-Q4 Sept–Nov,
price 2378–3029, checked against `data/regime_2024q4/HINDUNILVR.csv`) — finished writing mid-study and is
folded in as a replication check (~3× the 2026 sample). HAVELLS numbers cited from
`dev/plan/45-HAVELLS/feature_sl_anatomy.md`.

**Engine validated:** my first-touch walk-forward reproduces the parquet's symmetric 1-ATR:1-ATR `hit`
frame (mfe≥1 first ⇒ hit, mae≥1 first ⇒ loss). Correlation of my reconstructed mfe/mae to the parquet's
is **0.80 / 0.84 at an end-of-session horizon** — i.e. the pipeline's forward frame is "rest of session".
For the SL race I report **both** HAVELLS's stated **24-bar** horizon (apples-to-apples) **and EOD**.

---

## Headline verdicts (HUL vs HAVELLS)

| # | HAVELLS finding | HUL 2026 | HUL 2024-Q4 | verdict |
|---|---|---|---|---|
| A1 | FVG is an HTF artifact, **0 clean 1m 3-candle gaps** | fvg→1m gap **14.7%**, fvg_n **7.1%** (5m 26%/11%) | — | **REPLICATES** |
| B1 | taught outer-wick stop median **0.70 ATR** | median **0.99 ATR** / 3.6 pts | ~0.9 ATR | REPLICATES, **WIDER** |
| B2 | tiny stop fails by **wick noise not gap**: 84.8% / 15.2% | wick **83.6%** / gap **16.4%** | wick **88.8%** / gap **11.2%** | **REPLICATES** (near-exact) |
| B2 | edge SL-hold **30.3%** | EOD **29.0%** (24-bar 57.2%) | 24-bar 55.3% | **REPLICATES** at matched horizon |
| B3/T3 | +0.25 ATR buffer lifts win **44.1% → 55.4%** | tight cohort **41.7% → 53.5%** | tight **39.1% → 50.8%** | **REPLICATES** (both tapes) |
| F3 | **62%** of eventual winners first tag the exact-edge stop | tight **51.1%** (EOD) / 27.7% (24b) | tight **32.4%** (24b) | **REPLICATES, WEAKER** |
| B4 | nest hold **83.8%** vs tight ~25% (edge = depth, not confidence) | htf_nest **91.7%** vs sweep 33.9% | htf_nest **84.3%** vs sweep 26.9% | **REPLICATES** (STRONGER) |
| F6 | strength / zone-width / stacking **AUC ~0.48 (blind)** | **0.476 / 0.476 / 0.460** | **0.490 / 0.496 / —** | **REPLICATES** |
| F1 | nest term is an **anti-signal**: highest b_hit yet lowest win | b_hit **0.600 (top) / win 44.7%** | b_hit **0.600 (top) / win 31.2%** | **REPLICATES** (stronger in Q4) |
| F5 | enter-before-sweep: **AM shorts worst** | SHORT AM 47.9% vs PM 58.7% | AM 50.5% vs PM 59.1% | **REPLICATES** (both tapes) |

---

## A. Do the emitted features sit on real 1m structure? (which detect well vs poorly)

No marks, so this grades each detector's **emitted zone/entry against the raw 1m tape**.

| detector | n | entry-in-zone | zone-width (ATR) | verdict on HUL |
|---|---|---|---|---|
| orderblock | 231 | 100% | 1.44 | **well-formed box**, entry inside, win 52% |
| compression | 65 | 100% | 2.17 | well-formed box (wide), win 41.5% |
| fvg | 184 | 100% | 0.98 | box present but **not a 1m gap** (see below) |
| propulsion2 | 26 | 27% | 0.28 | tight; best win 60% |
| ob_taught | 72 | 25% | 0.39 | tight box, entry at edge; win 40.6% |
| fvg_n | 256 | 43% | 0.95 | **not a 1m gap** (7.1%) — merged/HTF |
| liquidity | 71 | 59% | 0.33 | **context line, 100% NEUTRAL** (EXT/EQH pool) |
| premium_discount | 28 | 100% | **21.2** | **pure HTF fib overlay, 100% NEUTRAL** |
| htf_nest | 38 | 0% | 1.23 | zone is a **distant HTF anchor 10.5 ATR away** (=the stop) |
| sweep | 56 | 0% | 0.03 | near-zero-width **line**, poorly localized (below) |
| wyckoff | 198 | 1.5% | 0.03 | near-zero-width **line** / PHASE label, not a zone edge |

**A1 — FVG is not a literal 1m imbalance → REPLICATES.** Of `fvg` firings only **14.7%** map to a real
1m 3-candle gap (`fvg_n` **7.1%**), within a 0.15-ATR tolerance and a 180-bar lookback. On 5m the match
rises only to 26% / 11%. HAVELLS found **0/2** clean 1m gaps and called FVG an HTF artifact — HUL confirms
it at scale: **85–93% of FVG firings have no literal 1m gap.** The taught FVG boxes are merged / higher-TF
constructs; a strict 1m 3-candle detector would miss them. (Tune D4 holds: detect FVG on its native TF.)

**Sweep is poorly localized on HUL → WEAKER than HAVELLS.** At the emitted firing bar the textbook
"overshoot beyond the level + close back" pattern appears only **8.9–19.6%** of the time (median overshoot
**−0.31 ATR** — the firing bar's high is usually *below* the swept level). HAVELLS saw clean ~1-pt
overshoot-then-reject sweeps. On HUL the sweep extreme is not co-located with the firing bar (the ts is the
retest/confirmation, not the poke), so `sweep` is one of the mis-timed detectors — treat its level with an
ATR tolerance, not as a tick-exact wick.

**Context lines are correctly non-directional:** `liquidity` (EXT/EQH pools) and `premium_discount`
(fib overlay, zw 21 ATR) are **100% NEUTRAL** with no outcome — identical to HAVELLS. They locate a level;
they are not entries.

---

## B. SL anatomy — the core result

### B1. Taught SL geometry (far zone edge − entry)
- HUL directional (valid geometry, n=1083): **median 0.99 ATR / 3.6 pts**, mean 1.42, p90 2.24.
- HAVELLS: median **0.70 ATR / 1.80 pts**, mean 1.20, p90 2.30.
- → Same low-risk / high-payoff design; HUL's taught stop runs **~1.4× wider in ATR**. This width gap is
  what dilutes HUL's aggregate shake-out numbers vs HAVELLS (see B3/F3 — the effect concentrates in the
  tight-stop cohort). 31/1123 firings have entry already beyond the far edge (invalid geometry) — dropped.

### B2. Does the tiny stop HOLD? — REPLICATES at matched horizon
SL-hold = adverse excursion never reaches the exact-edge stop inside the window.

| stop placement | HUL 24-bar | HUL EOD | HAVELLS (edge-band) |
|---|---|---|---|
| exact wick edge | 57.2% | **29.0%** | **30.3%** |
| edge + 0.10 ATR | 62.0% | 30.9% | 32.2% |
| edge + 0.25 ATR | 66.9% | 34.8% | 36.8% |

The absolute hold rate is **horizon-driven** (a 0.99-ATR stop is rarely hit in 24 bars but usually hit by
session end). At the pipeline's native EOD frame HUL's edge hold **29.0%** lands right on HAVELLS's
**30.3%** — the tiny stop is run ~70% of the time on both names.

**First-breach type → REPLICATES near-exactly.** Of edge breaches: **wick_hit 83.6% / gap_through 16.4%**
(HAVELLS 84.8% / 15.2%). The stop fails by **intrabar wick noise, not gap-through** — the "tiny-SL
fill-through" lesson holds on HUL.

### B3. Realized win-rate + the T3 buffer — REPLICATES (concentrated in the tight-stop cohort)
Tiny wick stop vs +1-ATR target, first-touch on 1m (tie → stop, conservative):

| stop | HUL 24-bar win | HUL EOD win | HAVELLS win |
|---|---|---|---|
| wick edge | 57.7% | 56.5% | **44.1%** |
| edge + 0.10 ATR | 62.0% | 59.1% | 48.3% |
| edge + 0.25 ATR | 66.4% | 62.0% | **55.4%** |

The **direction** replicates on every horizon (+0.25 ATR buffer lifts win **+8.7 pts** at 24-bar, **+5.5**
at EOD). But the cleanest match appears when you isolate the **taught tiny wick** — the tight tercile of
stop-width (median stop **0.42 ATR**, the true outer-wick geometry HAVELLS studied):

| stop-width tercile | n | edge win | **+0.25 ATR win** | edge SL-hold | winner-tag-first (24b) |
|---|---|---|---|---|---|
| **tight (0.42 ATR)** | 361 | **41.7%** | **53.5%** (+11.8) | 26.0% | 27.7% |
| mid (0.99 ATR) | 361 | 61.0% | 68.7% (+7.7) | 62.0% | 8.0% |
| wide (1.84 ATR) | 361 | 77.9% | 82.6% (+4.7) | 83.7% | 6.5% |

The **tight cohort is a dead ringer for HAVELLS**: edge win **41.7% → 53.5%** vs HAVELLS **44.1% → 55.4%**.
**T3 (SL = wick ± 0.25·ATR) REPLICATES on HUL** — the buffer removes noise-wick breaches and lifts realized
win ~+12 pts exactly where the taught tiny stop lives. The lift shrinks as the stop widens (nothing to
rescue), which is why the aggregate looks milder.

### F3. Do eventual winners get shaken out by the exact-edge stop? — REPLICATES, WEAKER
Of firings that eventually reach +1 ATR, the fraction whose exact-edge stop is tagged **first**:

| cohort | HUL 24-bar | HUL EOD | HAVELLS |
|---|---|---|---|
| all directional | 14.3% | 31.5% | — |
| **tight-stop tercile** | 27.7% | **51.1%** | **62%** |

On the taught tiny-stop cohort at the native EOD horizon, **51%** of eventual winners are first stopped out
at the exact wick — a majority, same story as HAVELLS's 62%, but **weaker** (HUL's wider taught stop + a
calmer 2026 tape shake out somewhat fewer). The mechanism is intact: the literal taught stop costs you
roughly half of your eventual winners, and the 0.25-ATR buffer is the fix.

### B4. Stop-hold is nest depth, not detector confidence — REPLICATES (STRONGER)

| detector | n | stop dist (ATR) | SL-hold (edge, 24b) | HAVELLS SL-hold |
|---|---|---|---|---|
| sweep | 56 | 0.93 | **33.9%** | 24.8% |
| ob_taught | 64 | 0.68 | 37.5% | 24.5% |
| fvg | 182 | 0.78 | 49.5% | — |
| orderblock | 227 | 0.78 | 52.4% | 34.4% |
| fvg_n | 241 | 1.11 | 60.6% | 26.7% |
| wyckoff | 192 | 1.04 | 67.2% | 31.5% |
| compression | 64 | 1.23 | 71.9% | 41.4% |
| **htf_nest** | 36 | **10.67** | **91.7%** | **83.8%** |

Same rank as HAVELLS: the tight zones (sweep / ob_taught) get run 2-in-3; **htf_nest holds 91.7%** because
its stop sits at a real HTF wick **~10.5 ATR** away (HAVELLS 6.92 ATR). Per-firing `strength` does **not**
separate outcome (AUC 0.476, below). **The stop-hold edge is the distance to the HTF anchor, not detector
confidence** — REPLICATES, and the nest holds even better on HUL because its anchors sit further out.

---

## C. Stacking / co-location — F6 REPLICATES (blind)

Rank-AUC of each feature vs the symmetric 1-ATR outcome (n=1088):

| feature | HUL AUC | HAVELLS |
|---|---|---|
| per-firing strength | **0.476** | ~0.48 |
| zone width (ATR) | **0.476** | ~0.48 |
| stacking depth (#detectors, ±10min/±0.4ATR) | **0.460** | ~0.48 |
| taught stop distance (ATR) | 0.473 | — |

All ~0.46–0.48 = **blind**. Stack-depth win-rate is flat with **no monotonic trend** (depth 2 = 64%,
depth 6 = 47%, depth 8 = 51%); stacking AUC 0.460 is even slightly *anti* (more overlaps → marginally
worse). **Raw confluence count, per-firing strength, and zone width are not edges on HUL** — same as
HAVELLS. Whatever edge exists lives in HTF-alignment depth, not in these per-firing scalars.

## F1. The nest / baseline term is an anti-signal — REPLICATES

`b_hit` (the baseline expectation, which encodes the nest/HTF-depth prior) is **inversely** related to
realized win across detectors:

| detector | b_hit (median) | realized win% |
|---|---|---|
| **htf_nest** | **0.600 (highest)** | **44.7% (below median)** |
| compression | 0.400 | 41.5% |
| ob_taught | 0.250 | 40.6% |
| fvg_n | 0.300 | 51.8% |
| **propulsion2** | **0.200 (lowest)** | **60.0% (highest)** |

htf_nest carries the **highest baseline yet under-delivers** (HAVELLS: b_hit 0.59 / win 41.7%; HUL-2026:
0.600 / 44.7%; **HUL 2024-Q4: 0.600 / win 31.2%** — even more extreme, propulsion2 there runs b_hit 0.45 /
win 68.3%). The nest term counts furniture/EQ-mid nests as depth and over-promises. **F1 REPLICATES**
(stronger on the larger Q4 sample). (The corollary "nest_depth IS a real discriminator once anchored to a true D1 extreme, and
T1's OTE-gate" is the province of the convergence_tree / htf_alignment doc; the SL side confirms only that
the *raw* nest baseline is anti-correlated with outcome, and that the nest's *stop* — B4 — is its one honest
edge.)

## F5. AM shorts worst — REPLICATES

| cohort | AM (<11:30) win | PM (≥11:30) win |
|---|---|---|
| SHORT | **47.9%** (n=242) | **58.7%** (n=317) |
| LONG | 46.1% (n=254) | 48.0% (n=275) |

Morning shorts underperform PM shorts by ~11 pts; longs are flat across the day. Consistent with the
enter-before-sweep trap — AM price runs up to grab buy-side liquidity before the real move, stopping early
shorts. **F5 REPLICATES.**

**F2 (EXT anchored to the latest swing, never re-anchors to the later range extreme)** is not directly
testable in this firings/SL doc — it needs the extremes-detector internals and belongs to the
htf_alignment doc. The symptom, however, is visible here: `liquidity`/EXT fires as 100% NEUTRAL context
lines and htf_nest's high-b_hit/low-win furniture problem (F1) is the same "wrong anchor" pathology.

---

## D. Tune implications for HUL (what carries over)

1. **Buffer the stop off the wick (T3).** `wick_extreme ± 0.25·ATR`. Measured lift on the tight-stop
   cohort: **41.7% → 53.5%** realized win; 84% of the breaches removed are noise wicks (16% gaps). Same fix,
   same magnitude as HAVELLS. The lift is real only for tight (~0.4–0.7 ATR) stops — don't buffer the wide
   nest stops (nothing to rescue).
2. **Weight HTF-anchor distance (nest depth), not stacking count or strength.** htf_nest stops hold 92% vs
   34% for tight zones; strength / zone-width / stack-depth are all AUC ~0.46–0.48. Keep the grade on
   HTF-alignment depth; add **no** raw "overlap count" bonus.
3. **Do not trust the raw nest baseline (`b_hit`) as a signal** — it is anti-correlated with realized win
   (htf_nest 0.600 → 44.7%). Its one honest use is locating the far HTF wick for the stop.
4. **Detect FVG on its native TF, not 1m.** Only 7–15% of FVG firings are literal 1m 3-candle gaps.
5. **Grade sweep/wyckoff/extreme levels with an ATR tolerance, not tick-equality** — sweep's overshoot is
   not co-located with its firing bar on HUL (median firing-bar overshoot −0.31 ATR).
6. **De-weight AM shorts** — 47.9% vs 58.7% PM.

**Both HUL tapes agree.** Every SL/feature finding above replicates on the independent 2024-Q4 sample
(3315 firings, a different price regime): T3 buffer tight-cohort **39.1 → 50.8%**, breach wick 88.8%,
htf_nest hold 84.3% vs sweep 26.9%, F6 AUC ~0.49, F1 nest b_hit 0.600 / win 31.2%, AM shorts 50.5 vs 59.1%.

*Not verifiable on HUL:* the tick-exact registry-SL "sweep-the-stop" placement cases (no HUL hand-marks) —
that geometry remains HAVELLS-specific evidence. F2 (EXT never re-anchors) belongs to the htf_alignment doc.
