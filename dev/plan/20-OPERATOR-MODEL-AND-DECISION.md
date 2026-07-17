# Operator Model + Implementation Decision Matrix (2026-07-17)

The philosophical core + the data-decided "which implementation to build." Merges the
seek-&-destroy operator thesis (user's charts) with every measured head-to-head (all txt
in `dev/h2h/`) and the RR dry-run. This is the build spec.

## PART 1 — The Operator Model (seek & destroy)
Algos fill large positions cheaply using the only free fuel: **resting stop orders**, whose
location they already know (retail stops sit in the same obvious spots). So price is not
random — it is **magnetized to stop-clusters, harvests them (triggers the stops), fills
against the trapped crowd, then moves the other way.**

**Where stops rest (the SL-cluster map = the magnet/target layer):** below base/swing lows
(long stops), above equal/swing highs (short stops + breakout buy-stops), round numbers,
PDH/PDL, opening-range edges, the "obvious" S/R everyone draws. **The more obvious/touched
a level, the FATTER the cluster → bigger magnet → more certain to be destroyed.**

**This is the theory of everything we measured:**
- obvious/heavy levels lose as entries (fresh>obvious) → they ARE the fattest clusters, so
  they get sought & destroyed; trading into them parks your SL where the algo is headed.
- breakout / structure-break / breaker(our impl) lose → they're the destroy itself (a hunt).
- inducement-sweep / OB-retest / compression-fade / real-breaker win → they enter AFTER the
  destroy, against the trapped.
- "no hunt = no trust" → a real move must be preceded by a destroy (needs the fuel).

**The trade:** be the one who profits from the destroy, not the stop that gets destroyed.
seek (map fat cluster) → wait for destroy (sweep/failed-break + reclaim, volume burst) →
enter reversal on 2m, **SL just beyond the destroyed extreme (tiny)** → target the NEXT
cluster (opposite liquidity). Direction from the ~6× HTF. Max RR by construction.

## PART 2 — Decision Matrix (best implementation per concept)
Measured on 20 NIFTY stocks × 19 sessions, holdout temporal + cross-sectional, multi-TF.
Edge = hit% vs random baseline; RR = mean max-R at tiny SL, expectancy at 3R target.

| Concept | BUILD THIS | Measured | Role |
|---|---|---|---|
| **Order Block** | **LuxAlgo** vol-adj leg-extreme (spike-excluded), size 8. SD-zone (Forex_Steward) as M5/M10 alt | +10.4→13.8% hit (robust to M15); SD +13.7% M5/M10 | ENTRY (grab/retest) |
| **FVG** | **LuxAlgo dedicated** (displacement CLOSE-beyond + auto mean-range% thr) | +12.4% M10 (vs ours +8.7) | ENTRY (CE-hold) |
| **Compression** | **FADE the breakout** (never follow) | +9% hit; **+0.33R exp @3R**, 9% run 10R+ — RR CHAMP | ENTRY (tightest SL) |
| **Inducement/sweep** | **LuxAlgo IDM sniper** (HTF CHoCH dir + LTF inducement grab, len20) | +14–20% hit (best); RR pending | ENTRY (the sniper) |
| **Breaker** | our impl WRONG (−8%); build the **seek-destroy harvest** (failed-break/sweep + reclaim), NOT the inverted-zone-retest | real-breaker marginal alone → fold into harvest | ENTRY (via harvest) |
| **CHoCH / BOS structure** | keep ours for DIRECTION only; NEVER as entry | −18% universal (4 defs: ours/LuxAlgo-fractal/TFlab/EmreKb) | DIRECTION/context |
| **Liquidity / pools** | **INVERT strength** (fresh>obvious); build the SL-cluster fatness map | touches AND volume inverted (heavy −11.6 vs light −2.2) | SL-map + SL-flip |
| **Wyckoff spring/upthrust** | retuned 30/4.0/1.25/upper-third + bar guards | +23/+32% (small n) | ENTRY (confluence) |
| **MTF direction** | HTF ≈ **6× entry TF** (M5→M30), agree-filter | RR 1.0→1.4, MAE↓ | DIRECTION gate |
| **Decision TF** | **M10 primary**; M2/M5 for tightest SL; M15/M30 direction | edge grows with TF + cost-viable | architecture |
| REMOVE | VSA booster (except FVG), PO3-distribution, heavy-level bonus, breaker(current), structure-break-entry | all measured ≤0 | — |

## PART 3 — Build spec (the v2 engine)
- **DIRECTION layer**: HTF (~6× TF) structure bias + premium/discount + wyckoff-HTF veto. No trade against it.
- **SL-CLUSTER MAP**: rank levels by fatness (obviousness × touches × roundness × recency).
  Nearest fat untapped cluster = the draw (predicted hunt). Fresh clusters preferred for entry zones.
- **HARVEST ENTRY** (one unified detector, replaces breaker + structure-entry): fat cluster
  swept / failed-break + reclaim (+ volume burst) ⇒ enter reversal on 2m/5m; SL beyond the
  destroyed extreme; ONLY if HTF direction agrees. Confluence of grab-signals at the zone:
  inducement-sweep, LuxAlgo-OB/SD retest, FVG-close-beyond, compression-fade, wyckoff-spring.
- **TARGET**: next opposite SL-cluster (avoid the most-obvious one — it gets run); partials at
  3R (expectancy peak), runner to 5–10R.
- **RISK**: tiny SL (0.15–0.5×ATR) ⇒ high RR by construction; the user's 1:10–1:30 comes from
  the 8–9% of harvests that run 10R+, funded by the +0.33R base expectancy.

## Status / next
All rows = validated 2-axis on ONE month; RR confirmed for compression-fade, pending for
OB/inducement (agent running). Then: economic portfolio replay of the v2 engine vs baseline
on holdout stocks (the final gate) before it ships. Build style: v2 ALONGSIDE + A/B replay,
plug-n-play core (per user: portable/modular). Nothing ships until it beats the baseline economically.
