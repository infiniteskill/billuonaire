# mitigation — precision audit

Tool: emitter `ob_taught`, event **`MIT_RETEST`**, feature `mitigation` (the taught
OB→MIT "No Break" flip). Recognition/precision only — never edge/profit. The edge
lives in the conjunction + tiny-stop RR (`runs/validate/SCORECARD.md`,
`dev/plan/42-REFINE-LOOP.md` iter-6 high-grade tier +4.57R); the goal here is
**fewer, higher-conviction firings so more of a firing's grade-stack is real**.

Data window: 1m/wide = 2026-06-25 … 2026-07-17 (17 trading days; parquet actually
carries 20 sessions back to 06-19). 8 marked stocks.

## Firing picture (the over-fire)

`ob_taught` MIT_RETEST fires: **942 total** (900 inside the 17d window).

| stock | fires | fires/session (17d density) |
|---|---|---|
| TITAN | 174 | **8.94** |
| VOLTAS | 134 | 7.88 |
| HAVELLS | 130 | 7.65 |
| HEROMOTOCO | 122 | 7.18 |
| SBILIFE | 107 | 6.12 |
| HDFCBANK | 120 | 6.06 |
| DABUR | 79 | 4.65 |
| DLF | 76 | 4.47 |

Window density = **6.6 MIT fires per stock per session** (900 / (8·17)). Every fire
carries the same fixed `strength=0.7` — there is **no conviction ranking at all**,
so nothing in the stack separates a real taught mitigation from noise.

Sibling events on the same detector: **OB_RETEST 1505, MIT_RETEST 942, BRK_RETEST
502.** The tell: **MIT:BRK = 1.88** — the "No Break" bucket is nearly twice the
"Break" bucket, which is backwards for a rarer object and points straight at MIT
being a *fallback* bin (below).

Zone geometry of the fires: median MIT zone is **0.40 ATR** wide; **29%** are
< 0.25 ATR and **9%** are sub-0.1-ATR slivers; only 39% reach ≥ 0.5 ATR. The user's
marked mitigation boxes are wide (HAVELLS 1219–1223.5 ≈ 4.5 pt ≈ 1.5 ATR; DLF
776–782 = 6 pt; TITAN 3990–4030 = 40 pt) — the detector is firing on bodies-box
slivers the taught object never draws.

## In-window precision (honest n)

Registry `feature=="mitigation"` = **16 marks**, but only a sliver is checkable in
the 17d window:

- **In-window: 5 HAVELLS short redraws** at ~**1219–1223.5**, dated 07-09/07-10 —
  these are one physical trade drawn 5×, so **≈ 1 distinct taught object**.
- HAVELLS long line **1141.02** dated "29/06-Jul" is nominally in-window, but
  `41-TOOLS/mitigation.md` establishes its true print is **06-08…06-12** (out of
  window; 06-29 barely tags 1140.5). Treat as out-of-window.
- **Out-of-window (10):** HAVELLS 2065–2035 (Sept, price-anomaly), HAVELLS
  1335–1330 (Apr), DLF 782–776 (Aug), TITAN 4030–3990 (02-04/06, before window),
  plus 3 reference schematics (no NSE tape).

So **checkable in-window n ≈ 1 distinct object** → far too small for a real
precision/recall number. What the match test shows anyway, for that one object:

- Near the 1219–1223.5 box (±0.3% and ±0.5 ATR): the only MIT fires are on
  **07-08** (the day *before* the marked retest) and they are **LONG** —
  direction-inverted vs the user's SHORT. On 07-09/07-10 price had already dropped
  to 1185–1211, so there are **0 MIT fires at the box** on the marked day.
- **Matched correct-direction fires for the mark = 0.** Recall for this specific
  short = **miss** (the MIT flip did not reproduce it — it emitted the opposite
  trade one day early).

Because in-window marks ≈ 0 usable, **firing density is the precision proxy**:
900 in-window fires against ~1 checkable taught object ⇒ precision (fraction of
firings that are the real taught object) is effectively floor-level; recall is
already ~100% elsewhere in the family. The problem is purely **selectivity**.

## Over-fire root cause (code)

`app/trader/detectors/ob_taught.py`:

1. **MIT is a FALLBACK bucket, not a gated object** (`ObZones.step`, line 79):
   ```
   swept = pex is not None and (ext > pex if dir==1 else ext < pex)
   kind  = "BRK" if swept else "MIT"
   ```
   `swept` is False whenever **`pex` (the prior opposite-side extreme) is unknown at
   birth** — which happens constantly (thin early-session pivots, sparse EXT
   levels). Every such "can't-tell" OB death is dumped into **MIT**. So MIT collects
   both the genuine No-Break flips *and* all the pex-unknown noise → MIT:BRK = 1.88.
   The c31 "No Break" law is never actually tested in the fallback branch.

2. **The retest arms unconditionally** (`_gated`, lines 139-158): `require_sweep_bos`
   **defaults False**, so `_gated()` returns True and *every* first retest of a MIT
   zone fires. There is no confluence gate on the emission.

3. **The wired sweep gate is mis-tuned for 5m and can't rescue it.** With
   `require_sweep_bos=True`: `gate_mode="sweep"` checks for any SWEPT level in the
   last 20 candles — but sweeps are ubiquitous here (sweep detector 16.3/stock-
   session + liquidity POOL_NEAR 15.0), so the gate passes ~100% of the time and
   filters almost nothing. `gate_mode="sweep_and_bos"` (the default when the flag is
   on) additionally requires an `e.detector=="structure"` BOS/CHoCH — but **no
   `structure` detector runs in this config**, so that mode gates to **0 fires**
   (kills recall entirely). The one wired gate is therefore either a no-op or a
   guillotine — neither raises precision.

4. **No zone-quality floor** (`_evidence`): the MIT zone is the parent OB's
   bodies-box (frozen bodies-only), so 29% of fires are sub-0.25-ATR slivers that
   arm on a single edge touch — nothing like the user's wide wick-inclusive box.

Net: MIT over-fires because it is the **default outcome of every un-swept OB death**,
armed by a retest gate that is off (or ineffective), with no size or conviction
filter.

## The precision tune (+ expected effect)

**THE single highest-leverage tune — make the MIT flip a genuine No-Break test
instead of a fallback.** In `ObZones.step` (line 77-82), require `pex` to be known
before creating a MIT zone; when the prior opposite extreme is unknown, the OB
simply **dies with no flip** (it is not a checkable taught mitigation):

```
pex = z.meta.get("pex")
if pex is None:
    kind = None                       # cannot establish No-Break -> no MIT/BRK flip
elif (z.meta["ext"] > pex if z.dir==1 else z.meta["ext"] < pex):
    kind = "BRK"                      # took prior extreme = Break
else:
    kind = "MIT"                      # prior extreme held = genuine No-Break (c31)
# only append the flip Zone when kind is not None
```

- **Numeric target:** MIT:BRK from **1.88 → ≤ 1.0**; window density from **6.6 →
  ~2.5–3.0 fires/stock-session** (≈ **50–60% fewer MIT fires**, 942 → ~400–470).
  Every surviving MIT then references a *real* prior same-side extreme — the exact
  c31 "unmitigated OB retested without breaking prior structure" object.
- **Why this over the wired sweep gate:** the sweep gate is data-proven ineffective
  at 5m (§root-cause 3); the pex-known gate attacks the actual over-fire source (the
  fallback branch) and is faithful to the taught definition, at zero config
  dependency on a `structure` detector that isn't running.
- **Expected effect on the high-grade tier:** MIT firings entering the grade-stack
  become ~2× more likely to be the real taught object, so conjunctions built on a
  MIT retest are far less diluted by pex-unknown noise. The high-grade tier's MIT
  contribution becomes higher-conviction per firing (fewer, cleaner). No edge/R
  claim — recognition/precision only.

**Second, once (1) lands** (not the single lever, logged for the loop): floor the
emitted zone at **≥ 0.5 ATR** by widening the bodies-box to the birth-leg wick
(`min(lo, ext_wick)/max(hi, ext_wick)`) — removes the 29% sub-0.25-ATR slivers and
matches the user's wide wick-inclusive box (the 41-TOOLS P1 finding), turning the
direction-inverted, floats-above-the-box misses into on-box arms. Keep
`require_sweep_bos=False` — the wired sweep gate does not help here.
