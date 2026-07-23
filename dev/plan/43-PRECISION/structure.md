# structure — precision audit (BOS / CHoCH)

Detector `structure` (emits `BOS` / `CHoCH` Evidence). Dataset:
`runs/validate/precision_study/evidence.parquet` — 21298 firings, 8 stocks,
20 sessions (2026-06-19..2026-07-17), 1m tape (`data/wide`), run under the
**taught profile** (`runs/validate/taught_profile/config.json`:
`structure.params = {anchor:"ext", trend_swings:2}`, extremes tf
`[5m,15m,1h,1d]` leg_pct 2.0). Marks: `runs/validate/tools/registry.jsonl`
(`feature=="structure_bos_choch"`).

## Firing picture

**structure fired ZERO times.** It appears in neither `evidence.parquet` nor
`summary.csv` — no `BOS`, no `CHoCH`, on any of the 8 stocks.

| stock | fires | density (fires/session) |
|---|---|---|
| DABUR, DLF, HAVELLS, HDFCBANK, HEROMOTOCO, SBILIFE, TITAN, VOLTAS | **0** each | **0.00** |
| total | **0** | **0.00** |

This is the **opposite** of the over-fire the brief anticipated. The 41-TOOLS
doc's "8:1 over-fire" (8 events vs 1 mark, HAVELLS 2026-07-07) was measured on
the **`anchor="swing"` (fractal 2N+1)** default. The **deployed `anchor="ext"`
profile fires nothing.** Over-fire (precision problem) and this silence (recall
problem) are two different failure regimes of the same detector at two anchors.

## In-window precision / recall

Window 2026-06-25..2026-07-17. `structure_bos_choch` marks on the 8 parquet
stocks with a `resolved_date` in-window: **9 raw** (HAVELLS 7, DABUR 2), but
these collapse to **~3 unique checkable BOS shelves**:

- HAVELLS ~1211/1213 BOS box, 2026-07-06 — marked 5× (`t1d..t1h`, five
  screenshots of the **same** 4m BOS box).
- HAVELLS "line 1840" ×2 (`T3a/T3b`, 2026-06-29) — **price-scale anomaly**,
  1840 is outside the resolved HAVELLS 2026 range 1124-1234; no matching
  candles ⇒ **uncheckable**.
- DABUR "box 446-445" + "line 437.5", 2026-07-05 (`t24_1`, `t24_2`).

**Precision = undefined (0 firings to match). Recall = 0 / ~3 checkable = 0 %.**
No structure firing exists to sit near any mark. Nothing to score; the detector
contributes **zero** rows to the confluence grade-stack. For the 45 out-of-window
marks the density proxy is likewise **0.0 fires/session** — silent everywhere.

## Over-fire root cause (here: under-fire → silence)

Traced to code, not data. The taught profile sets `trend_swings: 2`. In
`structure.py`:

```
_trend(swings[-2:])            # detect() L61
def _trend(recent):            # L83-94
    highs = [_mid(lv.zone) for lv in recent if lv.kind is self._hk]
    lows  = [_mid(lv.zone) for lv in recent if lv.kind is self._lk]
    if len(highs) < 2 or len(lows) < 2:
        return Direction.NEUTRAL      # L86-87
```

EXT swings **alternate** H/L, so any window of **2** consecutive swings holds
exactly **1 high + 1 low** → `len(highs)=1 < 2` → **`NEUTRAL` on every tick** →
`detect()` returns `[]` **always** (L62). This is **structural, data-independent**:

| trend_swings | max H/L split in an alternating window | can reach ≥2H & ≥2L? |
|---|---|---|
| 2 | 1 / 1 | **NO — guaranteed NEUTRAL** |
| 3 | 2 / 1 | NO |
| 4 | 2 / 2 | yes |
| 5 | 3 / 2 | yes |

So the REFINE iteration-2 tune "lower `trend_swings` 4→2" made `_trend`
**mathematically incapable of firing**, and REFINE.md's own note ("17d rangy
data has no EXT trend") mis-diagnosed the cause — it is the **param**, not the
tape. EXT anchors are present on the tape (liquidity `POOL_NEAR` fired 2404×,
which draws on the same EXT pools), so the gate would have material to fire on if
it could evaluate.

Second-order (would surface once `trend_swings≥4`): `_trend` still demands
**strict monotonic** `rising(highs) AND rising(lows)` over the whole window
(L88-91) — a single pullback → NEUTRAL. On rangy 17d 1m EXT this is near-zero,
while the fractal `anchor="swing"` variant swings the other way (8:1 over-fire,
latching minor pivots). Neither anchor lands on "fires ~once on the real EXT
shelf."

## The precision tune + expected effect

**Single highest-leverage change — rewrite `_trend` to the SMC first-HH+HL
definition and decouple it from the `trend_swings` window.** Concretely, in
`structure.py` L83-94, compute trend from the **last two EXT_H and last two
EXT_L** (not a fixed N-swing slice):

- `LONG` iff `EXT_H[-1] > EXT_H[-2]` **and** `EXT_L[-1] > EXT_L[-2]` (one
  confirmed HH+HL); `SHORT` iff both strictly lower; hold the trend until a
  `CHoCH` flips it; else `NEUTRAL`.
- This needs only 2 highs + 2 lows (4 EXT swings) and is **immune to
  `trend_swings=2`**. Keep `anchor="ext"` (taught shelf) and dedup-per-`swing_id`.

Minimal fallback if the rewrite is deferred: set **`trend_swings: 2 → 4`** and
relax strict-monotonic to "last HH+HL pair" — the one-line param fix that at
least lets the gate evaluate.

**Numeric target:** density **0.0 → ~0.2-0.5 fires/session/stock** (≈ 30-80
EXT-anchored fires over 8 stocks × 20 sessions), i.e. ~1 major BOS per trending
session — matching the taught cadence (~1 marked BOS/session), and **10-40× fewer
than the fractal anchor's 8:1** over-fire.

**Expected effect (recognition/precision only):**
- **Precision ~100 % by construction:** every fire is anchored on a real EXT
  shelf (the taught object) and gated on a genuine structural break, so the
  fraction of firings that are the REAL taught BOS/CHoCH goes from *undefined
  (0 fires)* to essentially all of them.
- **Recall:** the ~3 unique in-window BOS shelves (HAVELLS ~1211 07-06, DABUR
  ~445.5 / 437.5 07-05) become reachable; target ≥2/3 matched (the 1840 anomaly
  stays uncheckable).
- **High-grade tier:** structure currently feeds the confluence grade-stack
  **nothing**; the tune supplies a genuine EXT-BOS confluence vote to the ~1
  taught setup/session that anchors the high-grade tier (iter-6 +4.57R). Keep it
  a **low-weight CONTEXT node** (confluence weight 2), never an entry trigger —
  structure's own forward edge is negative (BOS -22pp, CHoCH -20pp); the value is
  a clean *recognition* member, not standalone edge.

**Guardrail.** This is RECOGNITION/PRECISION only. Do not add entry/SL to
`structure` (CE-entry + outer-wick-SL belong to the OB/propulsion detectors). The
fix un-silences a dead gate and makes each fire the taught object; it does not
claim profit.
