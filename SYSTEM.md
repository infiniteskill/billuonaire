# THE SYSTEM — What It Is, How It Works, What It Achieved, How Reliable It Is
*(2026-07-19 · 828 tests green · github.com/infiniteskill/billuonaire)*

---

## 1. WHAT IT IS

Two things in one repo:

1. **A trading engine** — a config-driven NSE intraday/positional trading machine: data feeds,
   10 SMC/ICT detectors, level lifecycle, confluence scoring, gated entries, resting-limit
   execution, position management, risk caps, journaling, replay. Live and backtest run the
   SAME code path (a backtest that runs different code lies).
2. **A research platform** — the honest measurement machinery around it: leak-free studies,
   realistic-fill simulation, cost models, temporal + cross-sectional holdouts, parity gates,
   null baselines. It answers "does X work?" in hours, and it cannot be flattered.

The second turned out to be the more valuable machine.

---

## 2. HOW IT WORKS — THE FLOW

```
DATA        yfinance → CSV archives (doctor-verified) → FileFeed → CandleStore
            M1 → M5/M15/H1/D1 aggregation, no-lookahead proven, splice-guarded

DETECT      each closed M5 bar → LevelEngine updates zone states
            (ACTIVE→TESTED→MITIGATED/DEAD; zones carry across sessions until killed)
            → 10 detectors emit Evidence(direction, strength, zone, meta{sl, sl_floor})

SCORE       ConfluenceEngine: spatial clustering → weighted directional score
            → D1/M15/template/time multipliers → threshold

GATE        time window (post-template-lock 11:30–14:45) · template · trend/chase/cooldown
            · risk caps (daily lock, heat, correlation, trades/day, per-stock)
            · cost/reward gate (real exit-count brokerage, mapped-R reward)
            · LADDER (research-validated elimination, runs/long60/FACTS.md):
              rung 1 zone born a PRIOR session + first touch · rung 2 nested in a
              live H1 zone · rung 3 born ≤3 bars after an aligned liquidity sweep.
              min_rung 3 ⇒ ~10 signals/day across 138 stocks (52.1% hit measured,
              4-way holdout-stable — the recognition ceiling; NOT net-positive)

ENTER       resting LIMIT at the zone CE (never chases) · structural stop
            (signal meta-sl honored, side-validated) · fill-time caps re-checked
            · fills AT the limit exactly

MANAGE      1R breakeven · per-source targets (config) · ratchet trail (never widens)
            · stealth close-confirmed stops · counter-signal/stall exits

PROTECT     EOD force-close 15:10 (+ feed-end close) · no overnight
            · restart watermark (no double-processing)

LEARN       every decision journaled → replay/report/calibrate → the research loop
```

**The 10 detectors** (all parity-locked bit-exact to their validated reference code):
`ob_lux` (LuxAlgo order block) · `fvg_cb` (close-beyond FVG + CE-hold) · `compression_fade` ·
`inducement` (CHoCH+grab, stateful FSM) · `bpr` · `mitigation` · `turtle_soup` ·
`propulsion_block` · `breaker_msb` (EmreKb Pine breaker, +19.6pp — strongest ingredient) ·
plus context: structure, wyckoff, swings, liquidity, timestats.

---

## 3. WHAT IT ACHIEVED

### 3a. Engineering (verified)
- **782 passing tests**; every detector proven bit-exact against the code that produced its
  measured numbers (parity gates on real data).
- **4 independent external audits reconciled** — 63 findings verified one by one; every real
  bug fixed with a regression test (limit-fill guarantee, session-boundary leaks, EOD
  force-close, fill-time gate parity, stop-side validation, watermark restart, data-layer
  doctor, and ~30 more).
- Sub-millisecond warm decision path per symbol (139-stock universe tick ≈ 30 ms).
- Data layer: `trader doctor` integrity CLI; archives verified; split/splice guards; two
  genuinely corrupted files found and repaired.

### 3b. Research (the honest map — the core achievement)
Measured across **300,153 intraday signals / 138 stocks / 8.4M realistic-fill simulations /
25 years of daily data**, with holdouts everywhere:

| question | answer |
|---|---|
| Do SMC/ICT tools predict? | **YES** — +5–15pp hit-edge over matched random, out-of-sample stable |
| Do they profit? | **NO** — the tape's excursions are symmetric (MFE/MAE ≈ 1.0 at every TF); pre-cost expectancy ≈ **+0.01R** (a breakeven machine); friction 0.05–1.4R/trade decides the sign |
| Any timeframe rescue? | NO — full ladder 5m→weekly: edge-over-drift ≈ 0 at every rung |
| Any stop/target/refinement rescue? | NO — entire plane swept; every RR combo is a fair lottery idealized; tighter stops = bigger toll (1m stops = −4.2R/trade) |
| Confluence/selection/ML rescue? | NO — stacking, cascades, top-K, and a 44-feature gradient-boosted learner: chart features add +.004 AUC; no out-of-sample decile net-positive |
| Stop-hunt thesis? | **PROVEN + quantified** — the stop is the harvested product; hunts 82–93% front-loaded; every stop placement taxed |
| **The one validated edge (free data)** | **12-1 cross-sectional momentum** — beats the random-rotation null (p100) AND buy-and-hold of the same stocks (+0.4–0.65%/mo active, t≈2), perfectly monotone deciles, ~30 min/month. GO with crash-rule prerequisite. |
| PEAD (earnings drift) | NO-GO — exposed as momentum in disguise by the regime-matched null |

**Bottom line achieved:** the finder was perfected (it catches the user's own best trades to
the tick); the market on free OHLCV pays ≈ zero for perfect finding; the one thing free data
pays is drift/momentum, captured by holding and monthly rotation, not by intraday churn.
Learned in dry-run. **Total real money lost: ₹0.**

---

## 4. HOW RELIABLE IT IS

### Strong (verified, trust it)
- **No-lookahead**: proven at store, detector, and study level (audited 3×).
- **Parity**: every detector's behavior locked to its measured reference by tests on real data.
- **Reproducibility**: replay is deterministic; watermark prevents restart double-processing;
  all research scripts preserved in `dev/research/` + results in `runs/` + `dev/plan/artifacts/`.
- **The negative results**: extremely reliable — replicated across independent datasets,
  methods (grids, event studies, ML), and 4 hostile audits. Where selection bias could
  inflate, we found nothing anyway (bias inflates positives, not nulls).
- **The momentum result**: pre-registered from 30 years of literature (not mined here),
  monotone mechanism, dual nulls — the anti-snooping design. Reliability: good, not
  bulletproof (t≈2; survivorship-inflated absolutes — trust the ACTIVE spread).

### Known limits (documented, non-blocking)
- Market model staleness: fixed ₹0.05 tick (NSE now tiered), levy details approximated,
  expiry holiday-shift unmodeled — irrelevant to the null verdicts, matters if trading resumes.
- Restart: engine state beyond levels/watermark/timestats is memory-only (live-readiness debt).
- Scanner (`--auto`) is a liquidity heuristic, not a validated selector (measured: no picker
  skill exists in the data anyway).
- Fills modeled from OHLC touch (no order-book queue) — conservative on limits, honest on stops.
- One structural bias impossible to remove free: today's-survivors universe (quantified: ~11pp/yr).

### How much to trust each number
| number | trust |
|---|---|
| "no intraday edge on free OHLCV" | **very high** — the most-replicated result in the repo |
| hit-edges (+5–15pp) | high (OOS-stable) |
| momentum GO | moderate-high — run small, judge on active-vs-EW, add crash rule |
| any single small-n cell anywhere | low — the repo's graveyard is full of them (mom7, H4 sweep, PEAD Q5) |

---

## 5. WHERE EVERYTHING LIVES
- Orientation: `PROJECT.md` → this file → `dev/plan/28-FINAL-SYNTHESIS.md` (the map)
- Audits + findings: `dev/plan/26`, `29`, `dev/plan/artifacts/*`
- Results: `runs/{long60,daily,ladder,pine,m1refine,diag5,learn,factor}/`
- The validated strategy: `runs/factor/MOMENTUM.md`
- Research code: `dev/research/` · engine: `app/trader/` · tests: `app/tests/` (782)
- Run it: `trader init` → `trader fetch` → `trader replay` / `trader watch` · data health:
  `trader doctor` · accrual: `tools/accrue5m.py`

## 6. THE ONE-PARAGRAPH SUMMARY
This system set out to be an intraday SMC sniper. It became something rarer: a machine that
finds setups as well as public data allows (proven to the tick on the user's own trades),
executes them faithfully, and — most importantly — measures the truth about them without
mercy. The truth it found: the chart's patterns predict a little and pay nothing after the
market's toll, at every timeframe, under every refinement; the only free-data edge is the
old boring one (drift/momentum), which it validated properly and can run in 30 minutes a
month. It cost zero rupees to learn what most traders pay their accounts to learn, and the
machine now stands ready for better data, the validated factor, or the next hypothesis —
whichever its owner chooses.
