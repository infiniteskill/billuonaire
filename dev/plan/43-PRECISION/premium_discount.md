# premium_discount — precision audit

Scope: RECOGNITION / PRECISION only (never edge/profit). Precision = of all firings, what
fraction are the REAL taught object (low over-fire). Recall is already saturated (~100%). Data:
`runs/validate/precision_study/evidence.parquet` (8 marked stocks, 1m, warm sessions
2026-06-30..2026-07-17). Marks: `runs/validate/tools/registry.jsonl`. Code:
`app/trader/detectors/premium_discount.py`. Spec: `dev/plan/41-TOOLS/premium_discount.md`.

## Firing picture

- **Total fires: 4634** — the largest emitter in the whole study (fvg_n 3376, ob_taught 2949 next).
- **Per stock:** HEROMOTOCO 888, TITAN 864, HAVELLS 709, DABUR 661, DLF 574, HDFCBANK 483,
  VOLTAS 252, SBILIFE 203.
- **Density: 34.1 fires / stock / session** (÷17). But this understates it — the harness only warmed
  the master EXT range on 14 of 17 days; on a **warm** (stock,session) the median is **74–75 fires**.
  A 1m NSE session = 375 min = **75 five-minute bars**, so once the range exists the detector fires
  on **~100% of bars**. Cadence is a strict 5.0-min grid (all inter-fire gaps = 5.0 min).
- **The zone is static:** distinct (lo,hi) per stock-session ≈ **1.01**. It re-emits an essentially
  identical NEUTRAL context stamp every single bar.
- **Side mix:** premium 3114 (67%), discount 887 (19%), **mid 633 (13.7%)**. The 633 "mid" fires sit
  inside the EQ deadband and carry `permits=None` — they license nothing yet still emit an Evidence.
- **Taught-band coverage:** only **42%** of fires (1946) land in the OTE deep-extreme band
  (range_pos 0.62–0.79 / 0.21–0.38); only 32% have strength ≥ 0.5. Range height is fine (median
  **42× ATR**, min 6.6× — the `min_range_atr=8` guard is NOT the leak).

Read: this is a **persistent-state gate that has been implemented as a per-bar event**. It does not
over-fire because its geometry is wrong — it over-fires because it re-stamps a static classification
75×/session and across the entire premium/discount half rather than at the taught extreme.

## In-window precision

- **8 `premium_discount` marks total; in-window checkable n ≈ 0.** The 17d intraday window is
  2026-06-25..2026-07-17. Only one mark's date overlaps it — HAVELLS "Apr-Aug 2026 (yr?)" — and that
  mark is a **fib-EXTENSION** projection (100/138.2/161.8% at 1490/1790/1930), a different geometry
  family (projection ABOVE the range, no internal EQ split) plus the registry's flagged price-scale
  anomaly vs the ~1200 2026 tape. It is not scorable against a range-split detector.
- The three SBILIFE marks are **daily/positional** (2020-21, 2024-25, 2026-label boxes at
  1300-1500 / 1980-2080) — outside the intraday window. Four marks are educational ICT schematics
  (no NSE symbol/tf). So **0 scorable in-window marks → use DENSITY as the precision proxy.**
- **Recall is trivially ~100%** and uninformative here: price visits both premium and discount every
  session and the gate fires on ~every bar, so it cannot miss. **Precision is the entire problem.**
- **Precision proxy (density):** of 4634 fires, the fraction that are the REAL taught object is small.
  The taught marks (t32b) sit at **deep extremes** — discount center 0.12, premium center 0.93,
  i.e. OTE-or-deeper. Only 42% of fires are OTE-or-deeper, and each is duplicated ~75×. Collapsing
  duplicates to state-changes leaves **158 unique OTE-arrival episodes** (1.72 / stock-session) and
  **107 deep-quarter arrivals** (rp≤0.25 | ≥0.75). So the effective precision — unique taught-object
  events ÷ total fires — is **≈ 3.4%** (158/4634). ~97% of firings carry no new taught information.

## Over-fire root cause

Two coupled defects, both a departure from the 41-TOOLS spec:

1. **Emission model wrong — the dominant lever.** Spec P1 (lines 121-124) explicitly said "emit as a
   **context gate**, not Evidence … born = later of the two pivot bars, dying when either master
   pivot is replaced." The implementation instead returns a fresh
   `Evidence(direction=NEUTRAL, ttl_candles=1)` on **every M1 bar** (`detect()` runs each bar;
   `premium_discount.py:66-73`). Because the zone is static within a session, this re-fires the same
   state ~75×. There is **no edge-trigger and no state-change gate** → ~96% of fires are redundant
   duplicates of the previous bar.

2. **Birth gate too loose — fires across the whole half, not the taught deep band.** The only
   suppression is the 0.10 EQ deadband (`eq_deadband`, removes the middle 10% → 13.7% "mid" still
   emit). Side is set the instant `range_pos` clears 0.45/0.55 (`premium_discount.py:64-65`), so it
   emits across the **entire** premium/discount half. But the taught object (t32b marks; doc P2's
   OTE band) is price **AT a deep extreme** (0.62-0.79 / 0.21-0.38, marks even deeper at 0.12/0.93).
   **58% of fires are shallow-half or mid — not the taught object.**

Not the cause: range-height guard (`min_range_atr=8`) passes with median 42× ATR headroom; geometry
(the range anchored on master EXT_H/EXT_L) is correct. The leak is purely (a) per-bar re-emission and
(b) half-wide birth instead of OTE-band birth.

## The precision tune + expected effect

**Single highest-leverage change: convert to an edge-triggered OTE-band-entry event.**

- **(a) Birth gate = OTE band.** Only emit when `meta['ote']` is True, i.e. `range_pos` ∈ [0.62,0.79]
  (discount → permits LONG) or [0.21,0.38] (premium → permits SHORT). Numeric target: **`ote_only`
  gate at the doc-sanctioned P2 bands.** (Optional tighter cut: deep-quarter rp≤0.25 | ≥0.75, which
  matches the marks' 0.12/0.93 exactly and drops another ~0.5 fire/session.)
- **(b) Edge-trigger.** Emit ONE Evidence on the bar price first **enters** the OTE band (state
  0→1); suppress while it dwells; re-arm on exit. Keep the NEUTRAL side-permission available to
  downstream consumers by writing `range_pos`/`side`/`permits` to **ctx tick-meta** (spec P1's
  "context gate"), NOT as a per-bar Evidence.

**Expected firing reduction:** 4634 → **~158 fires (-96.6%)**; density 34 → **~1.7 taught-object
events / stock / session**. The 633 "mid" fires and the 2688 shallow-half fires are eliminated
outright; the ~75×/session duplicates collapse to one-per-arrival.

**Expected precision:** every surviving fire is a fresh "price has just arrived at a deep extreme" —
the exact taught geometry — so the fraction of firings that are the real taught object rises from
**~42% (≈3.4% unique) → ~100%**.

**Effect on the high-grade tier.** Today the gate contributes a constant NEUTRAL background stamp on
every bar; because it is always-on it inflates every bar's grade-stack equally and washes out —
adding noise, not conviction. Edge-triggered, it contributes a **rare, high-conviction side
permission exactly when an entry detector (`ob_taught`/`fvg_n`) coincides with a deep extreme** —
sharpening the CONJUNCTION that iter-6 measured at high-grade +4.57R
(`dev/plan/42-REFINE-LOOP.md`, `runs/validate/REFINE.md`), instead of diluting it. Fewer, higher-
conviction firings ⇒ more of each firing's grade-stack is real.
