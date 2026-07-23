# breaker — precision audit (ob_taught / BRK_RETEST)

Detector `ob_taught`, event `BRK_RETEST`, feature `breaker`. RECOGNITION/PRECISION
only — recall is already ~100%; the question here is *of all BRK_RETEST firings,
how many are the REAL taught breaker* (a failed OB that flipped after a genuine
liquidity sweep). Data: `runs/validate/precision_study/evidence.parquet`
(8 stocks, 20 sessions, 1m→5m continuum), marks `runs/validate/tools/registry.jsonl`.
Honest window for numeric checks: **2026-06-25..2026-07-17** — only marks with
`date_approx` in that window are checkable; everything else uses firing DENSITY
as the precision proxy.

## Firing picture

**502** BRK_RETEST fires over 8 stocks. Per stock (fires, density = fires/17):

| stock | fires | fires/session |
|---|---|---|
| HDFCBANK | 78 | 4.59 |
| DLF | 73 | 4.29 |
| DABUR | 71 | 4.18 |
| HEROMOTOCO | 65 | 3.82 |
| HAVELLS | 64 | 3.76 |
| TITAN | 58 | 3.41 |
| SBILIFE | 54 | 3.18 |
| VOLTAS | 39 | 2.29 |

Mean **3.69 fires/session/stock** (all strength 0.7; 301 SHORT / 201 LONG). The
taught breaker is a **rare** object — the user marked ~one genuine failed-OB flip
per stock at a major structural top/bottom (14 registry rows = ~4 distinct real
objects + reference schematics). A detector firing ~3.7×/session/stock is
over-producing the object by **~30–60×**.

**Secondary over-fire (duplication):** the 502 fires land on only **340 distinct
firing candles** — 98 of those candles carry **>1** BRK evidence (up to **9** on
one candle) from overlapping flipped zones. Unlike `breaker_msb` (which has
`_collapse`), `ob_taught` has no per-tick de-dupe of overlapping BRK zones, so one
real retest emits several near-identical evidences (e.g. HAVELLS 9-Jul 09:15 →
3 fires, zones 1220.6–1222.6 / 1220.0–1222.2 / 1217.0–1220.0 on the same candle).

## In-window precision

**In-window marks: only HAVELLS is checkable.** SBILIFE `t31b` is 2024-09,
HDFCBANK `h4648/h4758` is 2025-09 — both **out of window**. The five reference /
no-stock schematic marks have no tape. So the in-window ground truth is the
HAVELLS breaker: **6 registry rows = ONE real object** (6 redraws of the same
box ~**1217–1224**, SHORT, 8-Jul-2026 top).

| stock | in-window marks | distinct objects |
|---|---|---|
| HAVELLS | 6 rows | **1** |
| all others | 0 | 0 |

**Match against HAVELLS fires (64 total).** On the mark's window (8–9 Jul) there
are **7** fires; **5** are SHORT within tol (0.3% / 0.5·ATR) of the 1217–1224 band:

- 8-Jul 10:35 SHORT 1222.6 (zone 1223.4–1224.5)
- 9-Jul 09:15 SHORT 1220.8 ×3 (zones 1220.6–1222.6 / 1220.0–1222.2 / 1217.0–1220.0)

The 9-Jul 09:15 fire reproduces `41-TOOLS/breaker.md` exactly (retest into the box,
then −37.7 pt rejection). **RECALL of the taught object = 100%** (fired, in fact
3–5×). **PRECISION is the problem:** of 64 HAVELLS BRK_RETEST fires only **1** real
object exists → ~**1.6%** precision by object (~**11%** if the whole 8–9 Jul
cluster of 7 is credited). The in-window n is tiny (1 object), so density is the
honest proxy: **3.7 fires/session/stock** against a true-breaker base rate of
~1 per stock per multi-week window.

## Over-fire root cause

The BRK zone is **minted on nearly every deep OB death**, gated by the loosest
possible sweep test:

1. **Zero-margin sweep gate (`ob_taught.step`, lines 77–78).**
   ```python
   pex = z.meta.get("pex")
   swept = pex is not None and (z.meta["ext"] > pex if z.dir == 1
                                else z.meta["ext"] < pex)
   kind = "BRK" if swept else "MIT"
   ```
   `swept` is **strict-greater with margin 0** — the birth-leg extreme need only
   nudge **one tick** past `pex`. On a 5m continuum an OB is born on a continuation
   break (its birth leg is, by construction, a new local extreme), so it almost
   always sits past the nearest opposite pivot → **BRK handed out on nearly every
   deep OB death**, not on the rare genuine liquidity grab.

2. **`pex` is the NEWEST opposite pivot (`_grade`, line 175):**
   `z.meta["pex"] = max(opp, key=lambda lv: lv.born).zone[0]` — the most **recent**
   (closest, easiest-to-exceed) opposite swing, and it **falls back to fractal
   SWING pivots** when EXT pivots are absent (lines 172–173). So a tiny 5m wiggle
   counts as the "swept liquidity pool." The taught breaker requires sweeping a
   **real** swing (HAVELLS: prior swing-high 1228.8 → high 1234.0 = **+5.2 pt =
   1.07·ATR**), not a 1-tick overtake of the newest wiggle.

3. **No confluence gate on the retest arm.** `_gated` returns `True` unless
   `require_sweep_bos` is set — and it defaults **off**. Even if turned on,
   `gate_mode="sweep_and_bos"` needs the `structure` detector to emit BOS/CHoCH;
   **`structure` is not in this pipeline** (absent from the parquet), so that gate
   would zero the detector (recall collapse). It is therefore *not* a safe single
   tune here.

Net: `BRK` = "any bodies-box OB that died by ≥0.5·ATR close-through and whose birth
leg poked past the newest opposite wiggle" — a routine event — instead of "an OB
that failed after a genuine sweep + opposing break."

## The precision tune + expected effect

**Tighten the BRK/MIT `swept` gate to demand a real liquidity-grab margin, and
source `pex` from EXT pivots only.** Self-contained in `ob_taught` (no cross-detector
dependency — important, since `structure` is absent):

- `ob_taught.step` lines 77–78 — replace the zero-margin test with a
  **≥ 0.5·ATR** margin (reuse the existing `depth` constant the lifecycle already
  uses for the kill):
  ```python
  atr = self.tape.atr
  m = (z.meta["ext"] - pex) if z.dir == 1 else (pex - z.meta["ext"])
  swept = pex is not None and atr is not None and m >= self.depth * atr
  ```
- `_grade` lines 171–173 — drop the SWING fallback for `pex` (EXT pivots only), so
  a fractal wiggle can never be counted as the swept pool.

**Numeric target:** sweep margin **≥ 0.5·ATR** (a genuine liquidity grab). On the
HAVELLS ground-truth object the real sweep is **1.07·ATR** → still fires (recall of
the one checkable object preserved); the sub-0.5·ATR majority demote **BRK→MIT**.

**Expected effect:** BRK_RETEST **~502 → ~150–250** (a **50–70% cut**), with the
survivors concentrated on real failed-OB-after-sweep reversals. Precision of the
BRK tier rises from ~2–11% toward the majority. Every BRK in a high-grade
grade-stack (the +4.57R conjunction, `42-REFINE-LOOP.md` iter-6) then represents a
genuine taught breaker instead of a routine mitigation death mislabeled as a break.

**Second, cheap win (de-dupe):** add a `_collapse`-style per-tick merge of
overlapping same-direction BRK evidences (as `breaker_msb._collapse` already does),
collapsing the ≤9-per-candle duplicates to the single tightest zone — removes the
340-vs-502 inflation without touching recognition.
