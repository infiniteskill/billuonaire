# liquidity — precision audit

Scope: RECOGNITION / PRECISION only (never edge/profit). Precision = of all firings, what
fraction are the REAL taught object (low over-fire). Recall is already saturated (~100%). Data:
`runs/validate/precision_study/evidence.parquet` (8 marked stocks, 1m, 2026-06-19..2026-07-17;
checkable intraday window 2026-06-25..2026-07-17). Marks: `runs/validate/tools/registry.jsonl`
(feature `liquidity_pool`, 58 instances). Code: `app/trader/detectors/liquidity.py`. Spec:
`dev/plan/41-TOOLS/liquidity.md`. Event: `POOL_NEAR`.

## Firing picture

- **Total fires: 2404** — 5th-largest emitter (premium_discount 4634, fvg_n 3376, ob_taught 2949,
  sweep 2613 ahead). All `Direction.NEUTRAL`; emitted `strength` = `pool_strength * 0.5`
  (mean 0.31, min 0.14, max 0.50).
- **Per stock / density (fires ÷ that stock's sessions):**
  TITAN 462 (**24.3**/sess), HDFCBANK 368 (19.4), HEROMOTOCO 283 (17.7), DABUR 278 (17.4),
  HAVELLS 276 (17.3), VOLTAS 253 (15.8), DLF 243 (15.2), SBILIFE 241 (15.1).
  **Mean density ≈ 17.7 fires / stock / session.**
- **Cadence:** 2227 distinct (symbol, session, ts) bars fire — 2050 emit 1, 177 emit 2 (the nearest
  pool **above** + nearest **below**, `_proximity_evidence` `:198`). Unlike premium_discount this is
  not literally every bar (~24% of the 75 M5 bars), but it re-surfaces a pool ~18×/session.
- **Pool universe is bloated:** distinct pool mids surfaced per stock = **29–88** (TITAN 88,
  HEROMOTOCO 68, SBILIFE 63). At almost any price SOME pool sits within 1 ATR.
- **Kind mix (inferred from zone width + round-number test):** the clustered **EQH/EQL equal-highs
  shelf — the dominant taught object — is only 38.7%** of fires (zone span ≥0.05%). The remaining
  **61.3% are tick-thin single-price furniture** (p±tick): **ROUND ≈10%** (zmid on a 50/100/500
  multiple) and **PDH/PDL + PWH/PWL + ORH/ORL + lone-EXT ≈53%**.
- **Distance is ~uniform across the whole gate:** price-to-pool `dist_atr` median **0.535**, spread
  flat 0→1.0. Only **27.7%** of fires are within 0.3 ATR of the pool (price actually testing it);
  the other ~72% are ambient neighborhood proximity, not a pool being reached.

Read: liquidity is a **static level factory whose proximity emitter has no conviction gate**. It
catalogs dozens of pool families, then surfaces the nearest one of *any* kind within a wide 1.0-ATR
band — so ~61% of firings are structural furniture (rounds, prior-day/week, opening-range) the user
never marked, and ~72% fire while price is merely *near*, not *at*, the pool.

## In-window precision

- The 17d intraday window is **2026-06-25..2026-07-17**. Of 58 `liquidity_pool` marks: 23 are
  foreign/reference schematics (EURUSD/GBPUSD/BTC/XAU), 11 unlabeled reference, and most NSE marks
  are 2020–2025 **daily-only** eras. NSE marks exist only for HAVELLS/VOLTAS/DLF/DABUR/SBILIFE —
  **TITAN, HDFCBANK, HEROMOTOCO have ZERO `liquidity_pool` marks** (yet emit 1113 fires, 46% of all).
- **In-window checkable n = 8 registry rows → 4 distinct taught objects, on just 2 stocks:**
  HAVELLS **1230/1229.5 EQH-sweep shelf** (resolved 2026-07-06, ×5 rows), HAVELLS **1770 TARGET**,
  VOLTAS **1393 EQH**, VOLTAS **1357 EQL** (resolved 2026-07-15). (DABUR ~24/06 resolves 2026-06-23,
  one day *outside* the window.)
- **Recall = 2 / 4 distinct objects (50%)** — and recall is not the problem here:
  - HAVELLS 1230 shelf → **HIT** (firings with pool mid ~1226.8/1228.8 within tol=3.7).
  - VOLTAS 1357 EQL → **HIT** (firings with pool mid ~1355–1358).
  - HAVELLS 1770 target → **MISS** (far draw-on-liquidity; HAVELLS tape max = 1229, price never near;
    proximity gate suppresses far targets — 41-TOOLS gap P4).
  - VOLTAS 1393 EQH → **MISS** (VOLTAS tape max = 1388.7, ~4.3 pt = just beyond 1.0×ATR ≈ 3–4 pt).
- **Precision-by-marks is unmeasurable and low-n:** only **~18 of 2404 fires (0.75%)** land on the 2
  matched in-window objects — but **78% of all fires are on 6 stocks with no in-window ground-truth
  pool at all**, so there is nothing to score them against. With only 4 objects on 2 stocks, a marks
  precision % is not meaningful → **use DENSITY as the precision proxy.**
- **Density proxy:** ~17.7 fires/stk/session against a realistic **1–3 taught pools** (equal-highs
  shelves / ranked extremes) in play per stock per session ⇒ **~6–15× over-fire**. Independently, the
  kind mix says only **~39%** of firings are even the EQ-shelf family; the rest is furniture.

## Over-fire root cause

`_proximity_evidence` (`liquidity.py:178-220`) has **no birth/conviction gate** — two coupled leaks:

1. **No kind gate — the dominant lever.** The emitter surfaces the nearest ACTIVE/TESTED pool of
   **any** of 11 `_PROXIMITY_KINDS` (`:22-27`) — PDH/PDL, PWH/PWL, ORH/ORL, ROUND, EQH/EQL, EXT — with
   the *only* filter being the lone-EXT-master rule (`:192-193`). ROUND (`_pool_strength` 0.4),
   opening-range and prior-day/week all emit POOL_NEAR identically to the taught equal-highs shelf.
   41-TOOLS validation already showed **ROUND coincided with a real mark exactly once (1300) and
   OR/PW never** — yet they are 61% of fires. There is no test for "is this pool the taught object
   (EQH/EQL shelf touches≥2, or a ranked EXTREME)."

2. **The pool universe never shrinks, so a furniture pool is always ≤1 ATR away.** ROUND mints a level
   at every multiple of **50/100/500** within `round_within_pct=2.0` (three step sizes,
   `_create_round` `:102-123`); PDH/PDL (`:63-66`) and ORH/ORL (`:85-91`) are minted **fresh each
   session and never expire** — `_create_once` dedups on a *date-stamped* id (`:235-243`), so 16 days
   accumulate ~32 prior-day + ~32 opening-range levels all left `ACTIVE`. Result: **29–88 distinct
   pools/stock** → at essentially any price some pool is within the band → POOL_NEAR ~18×/session.

3. **Proximity band too wide (compounding).** `proximity_atr=1.0` (`:32,186-187`). `dist_atr` is
   ~uniform 0→1.0, so **72% of fires are >0.3 ATR** from the pool — ambient proximity, not price
   testing/sweeping the pool (the taught event the whole chain rests on).

Not the cause: geometry is fine (tick-thin lines reproduce a horizontal mark to ±1 tick; EQ spans are
correct). The leak is purely (1) every kind emits, (2) the catalog never expires, (3) a wide gate.

## The precision tune + expected effect

**Single highest-leverage change: give `_proximity_evidence` a taught-object birth gate — emit
POOL_NEAR only for the pool families the user actually marks.**

- **The gate.** Split `_PROXIMITY_KINDS` into an **EMIT set = {EQH, EQL, EXT_H, EXT_L}** (the
  equal-highs/lows shelf with `touches≥2`, and ranked EXTREME masters — commit 8dc7cc8's "extremes
  are the taught anchor") and a **CATALOG-ONLY** remainder {ROUND, PDH/PDL, PWH/PWL, ORH/ORL}. Keep
  cataloging *all* of them on `ctx.levels` (so `sweep.py` still reads their SWEPT transitions — no
  downstream loss), but let **only the EMIT set surface `POOL_NEAR`**. This is the missing birth gate.
- **Numeric target:** fires **2404 → ~930** (the EQ/EXT share, **−61%**); density **17.7 → ~7.0**
  fires/stk/session. Taught fraction of survivors **~39% → ~90%+**.
- **Paired numeric knob (concentrate on *tested* pools):** tighten **`proximity_atr` 1.0 → 0.35** so
  POOL_NEAR fires only when price is within 0.35×ATR(M5) of the pool — i.e. price is actually
  reaching/sweeping it. Measured on the raw stream this alone keeps 32% (−68%); **EQ/EXT-only AND
  prox≤0.35 together keep ~17.5% ≈ ~420 fires** (density **~3.2**/stk/session, near the realistic
  1–3 taught pools/session).

**Expected precision:** every surviving fire is *price arriving at an equal-highs/lows shelf or a
ranked extreme* — the exact taught liquidity object — instead of an ambient round-number or
stale prior-day level. Over-fire drops ~6–15× → ~1×.

**Effect on the high-grade tier.** The pool is leg-0 of the taught chain
`liquidity → sweep → BOS → OB/FVG entry`. Today the emitter dilutes that conjunction: it stamps a
NEUTRAL POOL_NEAR whenever price drifts within 1 ATR of any of 88 furniture pools, so the "pool
present" term is almost always on and adds no conviction. Restricted to the swept EQ shelf / extreme,
POOL_NEAR fires rarely and *coincidentally with a genuine sweep target* — sharpening the CONJUNCTION
that iter-6 measured at high-grade **+4.57R** (`dev/plan/42-REFINE-LOOP.md`,
`runs/validate/REFINE.md`) rather than washing it out. Fewer, higher-conviction firings ⇒ more of
each firing's grade-stack is the real taught object.
