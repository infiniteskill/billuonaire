# propulsion — precision audit (propulsion2 / PROPULSION2)

RECOGNITION/PRECISION only. No edge/profit claim. Precision = of all firings,
how many are the REAL taught object (the deliberate propulsion block). Recall is
already ~100% at the system level via the conjunction; the concern here is
over-fire diluting each firing's grade-stack.

Source: `runs/validate/precision_study/evidence.parquet`
(`detector==propulsion2`, `event==PROPULSION2`), 8 marked stocks, 17d 1m
(window 2026-06-25..2026-07-17). Marks: `runs/validate/tools/registry.jsonl`
(`feature==propulsion`). Code: `app/trader/detectors/propulsion2.py` +
`app/trader/detectors/ob_taught.py` (`ObZones`).

## Firing picture

**131 fires** over 8 stocks × 17 sessions. Direction split LONG 62 / SHORT 69.

| stock | fires | density (fires/session) |
|---|---|---|
| HDFCBANK | 22 | 1.29 |
| VOLTAS | 22 | 1.29 |
| HAVELLS | 18 | 1.06 |
| TITAN | 18 | 1.06 |
| DABUR | 16 | 0.94 |
| DLF | 12 | 0.71 |
| HEROMOTOCO | 12 | 0.71 |
| SBILIFE | 11 | 0.65 |

**Overall density ≈ 0.96 fires per stock-session — roughly one propulsion
firing per stock per day.** On the 67 stock-sessions that fire at all, the mean
is ~2 fires (max 6 in one stock-session). The taught object is a *deliberate*
launch block: across the whole window the user drew **one** propulsion block on
DABUR (`t25`). So the detector emits ~1/stock/day against a truth rate of ~1
block/stock per 5–6 weeks — an ~20× over-fire.

**Child boxes are micro-zones.** Bodies-only single-candle box width:
median **0.42 ATR**, 25th pct 0.20 ATR; **33% of fires are <0.25 ATR wide**,
**20% are <0.15 ATR**. These are single-bar bodies, not the ~1.7pt launch
cluster the user draws.

## In-window precision

**In-window checkable marks: n = 1 (honest, and marginal).**
Of the 15 registry `propulsion` marks, only one can be checked in the 17d window
on the 8 marked stocks:

- **DABUR** box **420.3–422**, 5m, `~24/06-02/07` — the `t25` block. Overlaps
  the window only at its left edge (06-25..07-02).
- HDFCBANK box 990–982 (30m) is **Oct-2025** → out of window (and no tape).
- SBILIFE ×2 are **projection lines** (leg primitive), 2024–25 → out of window
  AND wrong output type for a block detector.
- SBICARD ×6 are Dec-Jan / Sep-2025 and SBICARD isn't among the 8 stocks.
- BTC/EUR/schematic ×3 have no NSE tape / no date.

**Match against the one in-window mark: 0/1.** No propulsion2 fire lands in the
420.3–422 band. DABUR's earliest fire in the dataset is 07-02 at **445**; its
entire fired price range is **427.15–449.15** — DABUR had already run up out of
the mark band by the time it fires. So the one deliberate block is **not
reproduced** (band-miss), while 16 unrelated fires appear above it. This matches
the 41-TOOLS finding (bodies-only micro-box, wrong-direction children near the
zone, SL sitting above the swept low).

**Precision-against-marks is therefore degenerate (0/1) → use DENSITY as the
proxy.** At ~0.96 fires/stock-session and a taught truth rate of ~1 block per
stock per 5–6 weeks, **at most ~5% of firings can be the real taught object**
(precision ceiling ~5%). Recall on the one in-window mark is 0 here, but system
recall is carried by the conjunction; the problem for propulsion is precision.

## Over-fire root cause

The birth gate has **no parent-quality filter** — the child is spawned off *any*
live taught-OB, and those parents are ungated fractal micro-OBs.

1. **The parent set is unfiltered fractal furniture.** `ObZones._cluster`
   (`ob_taught.py`) births an OB on essentially every swing: a single opposite
   candle counts as the degenerate "pause with counter-pressure" run, so nearly
   every mild pullback-and-continue mints a bodies-only micro-zone (the 33%
   <0.25 ATR tail). The 41-TOOLS simulation logged **504 OB → 50 children → 23
   evidences** on one symbol in 5 weeks.

2. **propulsion2 strips even the OB quality gates that ob_taught exposes.**
   `ObTaughtDetector` has `require_sweep_bos`, `gate_mode`, `far_dist_atr`, and a
   `pivot_dist_atr` grade — but those live in the *wrapper*, not in `ObZones.step`.
   propulsion2 constructs `ObZones(depth_atr)` **directly** (`propulsion2.py`
   L45) and never feeds `ctx.levels` EXT pivots, so its parents carry **no `pex`,
   no `pivot_dist_atr`, no swept flag, no width floor**. Every parent is "any
   live OB."

3. **The birth condition is trivially met.** `propulsion2.py` L69–79 births a
   child on the parent's first armed **retest** that **closes away with a
   directional body** (`c.close>z.hi and c.close>c.open`). Any candle that dips
   into a micro-OB and closes back out in-trend qualifies — this is a routine
   continuation bar, not a launch. Nothing requires the parent to sit on **swept
   liquidity / an EXT pivot**, which is what makes a *real* propulsion block.

Net: the parent-linkage the +43.4pp law relies on barely constrains anything,
because "linked to a live OB" is nearly always true. Geometry gaps (bodies-only
box, body-edge SL, edge-not-CE entry) are real but are recall/quality issues;
they do **not** cause the over-fire. The over-fire is **missing parent-quality
gating at birth**.

## The precision tune + expected effect

**THE single highest-leverage tune — gate child birth on a swept-EXT parent of
real width.** In `propulsion2.py` at the birth loop (L69–79), before appending
the child `Zone`, require BOTH:

- **parent is a swept-EXT OB.** Wire `ctx.levels` EXT_L/EXT_H pivots into
  propulsion2's private `ObZones` exactly as `ob_taught` does (attach nearest
  same-side EXT as `pex` at OB birth), and reuse the **`swept` boolean already
  computed in `ObZones.step` L75–78** (birth-leg running extreme `z.meta["ext"]`
  exceeded `pex`). Spawn a child ONLY if `parent.swept is True`. This encodes the
  taught truth "propulsion launches off swept liquidity / EXT, not fractal
  furniture."
- **parent width ≥ 0.5·ATR** (`z.hi − z.lo >= 0.5*self._obz.tape.atr`) — drops
  the bodies-only micro-OBs that make up the 33% of fires under 0.25 ATR.

**Numeric target.** Cut the parent set from "any live OB" to "swept-EXT OB,
≥0.5 ATR wide." Expected firing reduction **~85%**: total **131 → ~15–25**
(density **0.96 → ~0.12–0.18 fires/stock-session**, i.e. from ~1/stock/day to
~1–3/stock across the whole 17d window). The width floor alone removes the ~33%
<0.25 ATR tail; the swept-EXT gate removes the fractal-furniture majority
(mirrors the 41-TOOLS #3 target of 23/5wk/symbol → O(1–3)).

**Expected effect on the high-grade tier.** The fraction of firings that are the
REAL taught object rises from the ~5% density ceiling toward **~30–40%**: a
firing now means "a body launched out of a *swept-EXT* OB of real size," which is
the drawn object. Fewer, higher-conviction propulsion firings means each survives
into the conjunction with a genuine parent behind it, so the propulsion
contribution to the high-grade grade-stack (iter-6 high-grade tier +4.57R) is
real signal rather than one-per-day micro-OB noise. No edge claim — this is a
recognition/precision change only.

Secondary (not the single tune, tracked in 41-TOOLS): outer-wick box + sub-sweep
SL and a CE-entry option raise geometry fidelity but do not address over-fire.
