# ASSEMBLE — measured hit-rate + net profitability of the assembled taught system

2026-07-19. This is a **measurement of frozen configs**, not a new sweep. **0 new
configs examined**: the recognizer is the frozen `tune_frozen.json` (pct 0.06 / body-OB /
FVG mmax6 q0 / **death 0.5 second-life** / dedup stack≥4 / parent-linked PRP / edge entry).
The only pre-registered economic choices are the taught **zone-height stop (far edge, lesson-9
geometry)** with a **1.5×ATR fallback/baseline**, targets **1:1 & 2R**, and one **slow-trail**
runner. Costs & sizing are the standing `dgrid_lib` model (STT 0.1%×2, exch 0.004%, DP ₹15/sell,
slip 2bp/leg, R0=₹500 risk on ₹1L @0.5%, ₹5L notional cap).

## Provenance — which library backs each number (important)
- **All headline numbers recomputed live** from the current `dev/research/tune_lib.py` (the lib that
  implements the FIXED dedup merge, `death=0.5` break-depth **second-life**, and parent-link), via
  new scratchpad drivers `asm_h1.py` / `asm_daily.py` (+`asm_sim.py` R-sim, `asm_report.py`).
- The re-run **reproduces `tune_full.parquet` exactly** (identical episode counts by type, resp, r2,
  blow, nst0, plive on a 5-sym audit and 207,763-episode full match) — my zone geometry = the frozen
  detector's. The economic R-layer is the only thing added on top.
- **`ts2_eps.parquet` predates the fixes and is NOT used for the headline.** `ts2_lib.first_touch`
  kills a zone on **any** close through the far edge (D=0, no second-life) and its `nst` is a **raw
  (non-deduped) overlap count**. It backs the ZONES.md recognition tables only. Everything here backs
  off `tune_lib`/`tune_full` (D=0.5 + dedup + parent-link), the version that matches the engine
  detectors `app/trader/detectors/{extremes,fvg_n,ob_taught,propulsion2,taught}.py`.
- Composite grade realized as the three frozen discriminating binaries
  **g = 1{nst0≥4} + 1{parent_ok} + 1{dist≤2}**, g∈{0,1,2,3}. (The task's "depth_alive" slot is the
  break-depth-alive gate, which is **structural** — every episode exists only while the zone is alive
  under D=0.5 — so it is always-on; I substitute the actual frozen 3rd grade **pivot-near (dist≤2)**
  per TUNE §Composite, and isolate the second-life contribution separately via `life>0`.) Under dedup,
  `nst0≥4` (88%) and `parent_ok` (99.96%) are near-universal, so the discriminating tier is `dist≤2`:
  g≥2 = TUNE's top tier (184,744 eps), g=3 = the dist-near refinement (24,980).

---

## (H1 / intraday-hourly) — l4_h1, 138 syms, 2023-08→2026-07, 207,763 first-retest episodes

Horizon 70 H1 bars (~10 sessions). 83% of trades use the zone-height stop, 17% the 1.5×ATR fallback.

| tier g | n | respect | null | lift(pp) | t | win 1:1 | win 2R | net 1:1 | net 2R | net trail | gross 2R | trades/qtr |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 23,004 | 59.4% | 57.8% | +1.33 | 6.0 | 56.6% | 37.9% | −0.314 | −0.303 | −0.319 | +0.148 | 1,865 |
| 2 | 159,764 | 58.5% | 55.6% | **+2.78** | 18.5 | 51.7% | 31.4% | −0.245 | −0.266 | −0.293 | +0.064 | 12,951 |
| 3 | 24,980 | 58.7% | 56.3% | +2.15 | 6.5 | 49.2% | 28.7% | −0.256 | −0.278 | −0.178 | +0.031 | 2,025 |
| **g≥2 (top)** | **184,744** | **58.5%** | **55.7%** | **+2.69** | **19.4** | **51.4%** | **31.1%** | **−0.247±0.014** | **−0.268±0.015** | **−0.277±0.026** | +0.069 | **14,976** |

net columns are symbol-clustered mean ± 95% CI (R/trade); trades/qtr across 138 syms (12.34 quarter-eqs).

**4-way holdout (2 temporal × 2 crc-half), g≥2:** net 2R = −0.270 / −0.260 / −0.278 / −0.262 and
respect-lift = +2.75 / +2.94 / +2.60 / +2.49 pp — **recognition sign-consistent (all 4 +), net R
sign-consistent NEGATIVE (all 4 −).**

**Why net is so negative — costs, not misses.** Pooled 2R **gross = +0.069R** but **net = −0.272R**:
the round-trip delivery cost is **≈0.34R/trade**. A tight zone-height stop implies a large notional
per unit risk, so STT (0.1% each leg) on that notional dominates. Recognition is real; the geometry
is uneconomic on hourly.

**1.5×ATR baseline geometry (edge entry, 2R) — apples-to-apples with pre-fix TAUGHT_OB (+0.13g/−0.06n):**
ALL types gross +0.022 / net **−0.205**; OB-only gross +0.039 / net **−0.184**. The assembled
full set's gross edge (+0.02–0.04R) is *weaker* than the old OB-only +0.13R because it folds in the
weaker flip/band/fvg types (per-type net 2R: OB −0.251, IFVG −0.252, BRK −0.252, PRP −0.174 best,
FVG −0.329, MIT −0.310, BAND −0.349 worst).

**Did the new code move H1? No (economically).** Second-life episodes (`life>0`, alive only thanks to
the 0.5×ATR law): net 2R −0.318 vs pristine −0.265 — **worse**. Grade refinement g=3 (dist-near): net
2R −0.278 ≈ g=2 −0.266 — **no economic gain**. Dedup/parent-link/second-life sharpen *recognition*
(restore the graded, monotone deep-stack tail; keep PRP the strongest tool) but do **not** create H1
profitability.

---

## (Daily positional) — dailymax, 139 syms, ~30y, 307,991 episodes, horizon 40d (~8 wk)

**Survivorship warning: dailymax is survivors only → trust the EXCESS-over-drift number, not absolutes.**
Matched drift null = 5 random same-symbol same-direction entries per trade with the **same %-of-price
stop** (kills vol/drift-dilution), same 2R target / horizon / costs. Excess = real − null.

| tier g | n | respect | null | lift(pp) | t | win 2R | net 2R | drift-null | **2R EXCESS** | **trail EXCESS** |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 22,221 | 61.7% | — | +0.56 | 2.4 | 40.8% | +0.105 | −0.129 | +0.234±0.069 | +0.222±0.054 |
| 2 | 190,947 | 61.6% | — | +2.58 | 21.6 | 34.3% | +0.043 | −0.138 | **+0.181±0.022** | +0.211±0.058 |
| 3 | 94,819 | 61.3% | — | +2.32 | 14.0 | 32.8% | +0.033 | −0.123 | +0.157±0.023 | +0.164±0.045 |
| **g≥2 (top)** | **285,766** | **61.5%** | **58.8%** | **+2.58** | **21.6** | **33.8%** | **+0.040±0.011** | −0.133 | **+0.173±0.020** | **+0.195±0.048** |

net/excess = symbol-clustered mean ± 95% CI (R/trade). Daily trades ≈ **16.8/sym/quarter (~2,340/qtr)**.

**Absolute net (top tier):** 2R = **+0.040R (clustered t=7.2 — significantly positive pooled)**; trail
= +0.008R (t≈0, indistinguishable from 0). **Excess over drift:** 2R = **+0.173R**, trail = +0.195R.

**4-way holdout, g≥2 — 2R EXCESS = +0.214 / +0.217 / +0.136 / +0.124 (all 4 +); trail EXCESS all +.**
Sign-consistent. Absolute net is +0.10R in the two early cells but −0.02R in the two **late** cells
(the edge decays: temporal-third EXCESS +0.241 → +0.154 → +0.124) — so **absolute** profitability is
regime-fragile, while the **excess** stays positive everywhere. The prior net-positive daily cell
(DGRID full-ladder **+0.09R**) is now **+0.17R excess / +0.20R trail-excess** — the assembled taught
recognizer improved the daily edge.

---

## THE DELIVERABLE (plain)

**(a) Hit / respect rate, top tier (g≥2).** H1 **58.5%** vs 55.7% matched null → **+2.69pp** (t=19.4,
all 4 holdout cells +). Daily **61.5%** vs 58.8% → **+2.58pp** (t=21.6). Recognition is real and holds
out of sample.

**(b) Win rate at real targets, top tier.** H1: **1:1 = 51.4%, 2R = 31.1%** (zone-height stop).
Daily: **2R = 33.8%**.

**(c) Net R after costs, top tier.**
- **H1/intraday: −0.247R (1:1), −0.268R (2R), −0.277R (trail)** per trade — negative in all 4 holdout
  cells. Gross +0.069R; the ~0.34R round-trip cost on tight stops swamps it. (1.5×ATR geometry: −0.205R.)
- **Daily positional: +0.040R absolute (2R, t=7.2)** but survivorship-inflated; the trustworthy number
  is **+0.173R EXCESS over matched drift (2R) / +0.195R (trail)** — positive in all 4 holdout cells.

**(d) IS IT PROFITABLE — yes/no.**
- **H1/intraday: NO.** −0.27R/trade after costs (95% CI [−0.282, −0.253]); costs, not hit-rate, kill it.
- **Daily positional: MARGINALLY / conditionally.** It clears a matched-drift null by **+0.173R ±0.020**
  per trade at 2R (all holdouts +, t large) — a *real, survivorship-robust edge* — but **absolute** net
  is only **+0.040R ±0.011** and turns slightly negative in the late-period holdouts. Real edge, thin
  bankable P&L.

**(e) Did the new code (dedup, second-life, parent-link) move it vs pre-fix (+0.13g/−0.06n H1; +0.09 daily)?**
- **Recognition: yes** — dedup restored a graded, monotone deep-stack tail; parent-link keeps PRP the
  strongest tool; second-life adds +2.6pp of extra episodes. **Economics on H1: no** — net went from
  −0.06R (old OB-only 1.5×ATR) to −0.18…−0.27R (assembled: weaker types folded in + tighter stops);
  second-life episodes are economically *worse* (−0.318R) and grade-refinement adds no net R.
  **Economics on daily: yes** — the assembled recognizer's excess-over-drift is **+0.17R (2R) / +0.20R
  (trail)** vs the prior **+0.09R** daily cell, holding positive in every holdout.

### One-line answer — "are we profitable now?"
**Not intraday (−0.27R/trade after costs); on daily the taught zones beat a matched-drift null by
+0.17R/trade at 2R (all 4 holdouts positive) but net only ~+0.04R absolute — a real, robust recognition
edge that barely clears delivery costs, not yet a bankable P&L.**

## Honesty ledger
- n stated on every cell; net R symbol-clustered (episodes overlap within a symbol → naive SE understates).
- Positive claims gated on 4-way holdout sign-consistency: H1 net is uniformly negative; daily EXCESS is
  uniformly positive (absolute daily net is NOT — flagged).
- Survivorship: daily absolutes untrustworthy (only surviving names, upward drift); the drift-null EXCESS
  is the reported edge.
- Configs examined here: **0 new** (frozen-config measurement). Pre-registered economic choices only:
  zone-height stop (+1.5×ATR fallback/baseline), 1:1 & 2R targets, one trail rule.
- Consistent with the standing verdict (H1GRID/TAUGHT_OB): recognition real, intraday net ≈ 0-to-negative;
  the daily positional frame is the only place a positive, holdout-stable edge appears.
