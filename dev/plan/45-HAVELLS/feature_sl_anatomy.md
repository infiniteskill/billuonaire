# HAVELLS — FEATURE + SL ANATOMY on real tape

Scope: 159 HAVELLS registry marks vs raw 1m + the 2778-firing precision parquet (1793 directional),
all over the same tape: **2026-06-25 → 07-17 (16 sessions, price 1140–1234)** plus 2024-Q4 regime (Sept–Nov, 1587–2106).
RECOGNITION study — measured, not hyped.

## 0. What is actually checkable

The raw 1m only covers 16 sessions of 2026 + one 2024-Q4 block. Registry marks span 4 eras:

| era (resolved_year) | marks | raw 1m available? |
|---|---|---|
| 2026 | 70 | yes (June25–Jul17 window) |
| 2023 | 50 | no |
| 2022 | 36 | no |
| 2020 | 3 | no |

By **price band**: 74 marks land in the 2026-wide band (1140–1234), 19 in the 2024 regime band, 65 in other-era prices, 1 spans both.
Date-resolvable **and** in-window = **41 marks** actually checkable on the 1m tape (heavily duplicated — the same July 7–9 supply zone is re-drawn across the t3/t4/t5 drill screenshots). The parquet's 1793 directional firings are the clean, un-hand-picked structural sample and carry the SL statistics.

Parquet units decoded: `mfe`/`mae`/`fwd*` are **ATR-normalised**. The parquet's `hit`/`loss` is a **symmetric 1-ATR target / 1-ATR stop** frame (hit ⇔ mfe≥1.01 ATR reached first; loss ⇔ mae≥1.01 first). That is NOT the taught tiny stop — I reconstruct the taught outer-wick stop separately below.

---

## A. Does the drawn feature actually show the structure on 1m?

| feature | checked | shows structure | verdict |
|---|---|---|---|
| liquidity_pool (EXT / EQH lines) | 5 | 5 (100%) | **real** — line 1230 touched 18×, **swept** (wick above, close back below), penetration ~1 pt |
| sweep | (within liq) | — | **real** — tiny sweeps, ~1 pt of overshoot then reject |
| structure_bos_choch | 5 | 5 (100%) | level is genuinely traded/broken |
| breaker | 6 | 6 (100%) | displacement candle present at box price |
| mitigation | 6 | 6 (100%) | OB-retest displacement present |
| order_block | 13 | 10 (77%) | real displacement candle at box; 3 "misses" are out-of-window era boxes (1955–1900, 1157–1141) |
| extreme_swing (pivots) | 4 | within <1 ATR | **near-exact** — drawn pivot is 0.1 / 0.6 / 1.0 / 1.0 pts (0.09–0.87 ATR) from the nearest real 1m fractal |
| **fvg** | 2 | **0 clean 1m gaps** | **HTF artifact** — box 1224–1208 & 1148–1141 do **not** map to any 1m 3-candle gap (fit error 11.5 / 49 pts) |

Ground-truth from the hand charts confirms: the two "LIQUIDITY EXTREME RED LINE" marks sit exactly at 1234.34 / 1125.51 range extremes; `premium_discount` is a pure HTF fib overlay (matches its 709 NEUTRAL, no-outcome parquet rows).

**Finding A1 — features are drawn on real structure**, with two caveats: (1) `extreme_swing` pivots are accurate to well under 1 ATR but not tick-exact — grade pivot distance with an ATR tolerance, not equality. (2) **FVGs are an HTF feature**: the taught FVG boxes are 5m/30m gaps and are invisible as literal 1m 3-candle imbalances. Detecting FVG on 1m will not reproduce the taught mark — FVG must be detected on its native TF.

---

## B. SL anatomy — the core result

### B1. Taught SL geometry
- Taught outer-wick stop (parquet, far zone edge − entry): **median 0.70 ATR / 1.80 pts**, mean 1.20 ATR, p90 2.30 ATR.
- Registry marks with explicit entry+sl (n=33): SL dist **median 7 pts**, and **R:R median 6.1× (mean 7.6×)** — tiny stop, target = opposing liquidity. This is a low-win / high-payoff design by construction.

### B2. Does the tiny stop HOLD on the real tape? (mostly no)

SL-hold = adverse excursion never reaches the stop inside the forward window:

| stop placement | SL-hold | breached |
|---|---|---|
| exactly at wick edge | **30.3%** | 69.7% |
| wick edge + 0.10 ATR | 32.2% | 67.8% |
| wick edge + 0.25 ATR | 36.8% | 63.2% |

**First-breach type on raw 1m (24-bar horizon):** held 667 (37%), breached 1126 (63%). Of breaches: **wick_hit 84.8% vs gap_through 15.2%.**
→ The tiny stop fails by **intrabar wick noise, not by gap-through.** This is the "tiny-SL fill-through" lesson, now measured on HAVELLS.

### B3. Realized win-rate — tiny SL vs +1-ATR target (proper first-touch race on 1m)

| stop | target-first | SL-first | win-rate |
|---|---|---|---|
| wick edge | 751 | 953 | **44.1%** |
| edge + 0.10 ATR | 817 | 874 | 48.3% |
| edge + 0.25 ATR | 914 | 736 | **55.4%** |
| (pipeline 1ATR:1ATR ref) | — | — | 50.3% |

A **0.25-ATR buffer beyond the taught wick lifts realized win-rate 44% → 55% (+11 pts)** — because the breaches it removes are noise wicks. Of firings that eventually reached +1 ATR, **62% first touched the exact-edge stop** (i.e. the literal taught stop shakes you out of ~⅗ of eventual winners).

### B4. Stop-hold is a function of zone width / nest depth

| detector | n | SL dist (ATR) | SL-hold (edge) |
|---|---|---|---|
| ob_taught | 368 | 0.54 | 24.5% |
| sweep | 322 | 0.71 | 24.8% |
| fvg_n | 430 | 0.47 | 26.7% |
| wyckoff | 143 | 0.98 | 31.5% |
| orderblock | 244 | 0.80 | 34.4% |
| compression | 70 | 0.99 | 41.4% |
| **htf_nest** | 37 | **6.92** | **83.8%** |

The tight zones (fvg_n / ob_taught / sweep, ~0.5 ATR stop) get run 3-out-of-4 times; the **HTF-nested zone holds its stop 84%** because the stop sits at a real HTF wick 6.9 ATR away. Per-firing `strength` does NOT separate outcome (win-rate flat ~46–50% across strength quartiles; SL-hold flat ~29–34%). **The stop-hold edge comes from nest depth, not from detector confidence.**

### B5. Registry SL placement errors (the sweep-the-stop trap)
Of the 3 in-window marks with explicit sl:
- 2 supply shorts placed sl at the **OB box edge (1224)** which is **inside the liquidity extreme (1234)**. On the tape price ran to 1234 to grab that pool — **the OB-edge stop is taken out by the very sweep the setup is waiting for.** `sl_beyond_wick = False`.
- 1 demand long placed sl (1133) correctly **beyond** the session low (1140.5). `sl_beyond_wick = True`.

→ When a liquidity pool sits just past the OB, the taught "outer wick of the OB" stop is **too shallow** — it must sit beyond the *pool*, not the box.

---

## C. Stacking / co-location

**Registry (in-window):** the taught A+ zones are explicit multi-feature confluence stacks:
- **2026-07-08 @ ~1219.5** — `order_block + breaker + mitigation` (3 features, 16 marks)
- **2026-07-07 @ ~1229.5** — `extreme_swing + liquidity_pool + order_block` (3 features, 12 marks)

**Parquet:** detectors co-locate heavily — **mean 3.6 distinct detectors fire within ±10 min & ±0.4 ATR** (median 4, max 7). But **stacking depth does not lift outcome**:

| stack depth | n | win (1ATR) | loss |
|---|---|---|---|
| 1 | 68 | 63.2% | 33.8% |
| 2 | 278 | 45.7% | 48.6% |
| 3 | 471 | 50.3% | 45.4% |
| 4 | 472 | 45.1% | 49.6% |
| 5+ | 504 | 48.4% | 49.4% |

→ Raw confluence **count** is not an edge (flat ~45–50%). The taught method stacks features at a level to *locate* it, but count-of-overlaps ≠ profitability. Consistent with the published edge living in the **nest_depth grade**, not in stacking or strength.

---

## D. Concrete tune this implies

1. **Buffer the stop off the wick.** Place the outer-wick SL at `wick_extreme ± 0.25·ATR`, not on the exact tick. Measured lift: realized win 44% → 55%; 85% of the breaches removed are noise wicks, not gaps. Cost: +0.25 ATR of risk per trade — still a tiny stop against a 6× R target.
2. **When a liquidity pool sits beyond the zone, anchor the stop beyond the POOL.** OB/mitigation-edge stops get swept into the pool (measured 1224→1234). Detect the nearest EXT/EQH pool on the stop side and extend SL past it.
3. **Weight nest_depth, not stacking count or per-firing strength.** htf_nest stops hold 84% vs 25% for tight zones; stack-depth and strength are flat on outcome. Keep the grade = HTF-alignment depth; do not add a raw "number of overlapping detectors" bonus.
4. **Detect FVG on its native TF (5m/30m), not 1m.** Taught FVG boxes have no 1m 3-candle equivalent; a 1m FVG detector will not reproduce the mark.
5. **Grade pivot/extreme distance with an ATR tolerance** (~0.5–1 ATR), not price equality — drawn pivots land 0.1–1.0 pt (<1 ATR) off the true fractal.
