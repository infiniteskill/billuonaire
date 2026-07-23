# fvg

Validation of the **fvg** detector (and its two siblings `fvg_cb`, `fvg_n`) against **every**
hand-marked `fvg`/`ifvg` instance in `runs/validate/tools/registry.jsonl` (32 fvg + 3 ifvg = 35).
Per-instance record: `runs/validate/tools/val_fvg.jsonl`. Guardrail (RETHINK.md): this validates
**RECOGNITION** (fires on the right candle/geometry) only — it makes **no** profitability claim.

## Feature notes (structure & validity)

**What the feature is.** A Fair Value Gap = a 3-candle imbalance where candle-1 and candle-3 do
**not** overlap, leaving an unfilled price void the market tends to revisit. Bull: `c3.low > c1.high`
(zone `= c1.high .. c3.low`). Bear: `c3.high < c1.low` (zone `= c3.high .. c1.low`). It is drawn
**wick-to-wick** (outer wicks of c1/c3), born on c2. The user's "liquidity void" / "inefficiency
to fill" marks are the same object (r1301, r1316, b8d2_c11).

**Three detectors ship** (`app/trader/detectors/`):
- **`fvg.py`** (name `fvg`, the target). Loosest: any 3-candle wick-gap with `gap >= min_gap_atr*ATR`
  (**default 0.3**), **no displacement or sweep requirement** — fires mid-air. Emits: `CE_HOLD`
  (0.7, ttl 12) = close back inside the gap holding the **CE/midpoint** on the gap side; full-fill
  → `DEAD`; `IFVG` (0.75) = inverted gap retested breaker-style; `BPR` (0.8) = close inside a
  bull×bear overlap. **Emits no SL.**
- **`fvg_cb.py`** (name `fvg_cb`, LuxAlgo port). Adds two birth gates: (a) c2 **CLOSES beyond** the
  origin edge (displacement) and (b) `gap% > running-mean bar-range%` (auto threshold, `thr_mult`
  1.0). Events `FVG_RETEST` (0.6), `FVG_CE_HOLD` (0.75). No SL.
- **`fvg_n.py`** (name `fvg_n`, frozen taught successor). Generalized 1..`mmax`(6) middle-candle
  **displacement burst** (every middle close beyond the near flank), a **merge rule** (continuous
  gaps = ONE zone), the **break-depth lifecycle** (`taught.step_zone`: close through the far edge by
  `>= depth_atr*ATR`, default 0.5, kills; shallower = second life), and **kill→iFVG flip** (same box,
  opposite dir). **This is the only one that emits an SL** — `meta.sl = z.lo/z.hi` (the box **far
  edge**) with `sl_atr_floor` 0.15; entry = the **whole box** (edge entry, `zone=(lo,hi)`).

**HOW/WHEN it fires.** On every newly-closed bar the 3-candle window is tested; a passing gap
creates a Level (`fvg`/`fvg_cb`) or Zone (`fvg_n`); retest/CE-hold events fire once per
episode/level on later bars.

**CONFLUENCE.** In the tape the marked FVG almost always sits **inside an OB / demand-supply zone**
(T2a "inside the demand OB", c05 "inside the ORDER BLOCK", t28 "upper half of the pink zone", t30
"the demand base") and is born **off a swept swing extreme** after a displacement leg — i.e. the
user's FVG is the *refined entry pocket within a bigger zone born after a sweep+BOS*, not a
stand-alone mid-air gap.

## How the user draws it

- **Box = outer wicks**, wick-to-wick, of the imbalance (matches `fvg.py` geometry).
- **Born off a swept swing extreme + displacement**, not mid-air (h4143/t1b off the swing high,
  t30 off the 18/08 low). Frequently **nested inside an OB** and used as the *refined* entry.
- **Entry ≈ CE (midpoint)**, not the edge: t26 entry 520.3 vs CE 520.5; t27 entry 490.7 vs CE 490.25.
  (b8d2_c05 explicitly labels the CE/midpoint.)
- **SL beyond the outer edge** of the box: t26 SL 522.3 = 0.8pt above box-hi 521.5; t27 SL 486 =
  2.5pt below box-lo 488.5 (= the exact swing low). t30b SL 793 = box-low edge.
- **Two extra use-cases the detector doesn't model:** FVG-**as-target** / draw-on-liquidity
  (T19_2: the FVG *below* is the short's objective, price fills it as TP), and **iFVG** = a filled
  bear FVG flipped to support (c04, t30 ~798).

## Accuracy verdict

**pct_match = hit / (hit+partial+miss) = 9 / 18 = 50.0%** (uncheckable excluded from denominator).

| verdict | count |
|---|---|
| hit | 9 |
| partial | 9 |
| miss | 0 |
| **uncheckable** | **17** (reported, not in pct) |
| total | 35 |

**No outright misses:** wherever native (or coarse-but-sufficient) tape exists, a same-direction
3-candle gap **does** appear on the marked leg. The 50% "partial" half is **precision/plumbing**, not
absence: box-edge offset, tf-granularity, entry (CE vs edge), SL (beyond-wick vs none/inner),
birth-gate, and unmodeled use-cases.

**Per-stock breakdown** (hit / partial / uncheckable):
- **HDFCBANK** 2 / 2 / 0 — h4143/h4147 (06/07 bull, 08/07 bear), 5m→30m native. **Bull hit**
  (802.20–815.30 @06/07, 3.66×ATR; box low within 2pt). **Bear partial** (818.50–826.80 @08/07;
  box 825–832 sits ~5–6pt **above** the wick-gap — user boxed the impulse-candle *range*, not the gap).
- **HAVELLS** 1 / 3 / 0 — **t1b hit** (bear 1209.90–1221.10 @08/07 = box 1208–1224, both edges <3pt).
  **T2a partial** (gap is a **5m** object 1142–1146 inside box 1141–1148; at the **labeled 30m** there
  is **no** gap). **T4a/T4b partial** (bear FVG 2042–2058 @Sep-**2024**; price 2045 only ever traded
  Sep-2024 → mark's "2026" year is wrong; box lo 2035 unmatched).
- **SBICARD** 6 / 4 / 0 — **t28b/c/j hit** (bull 2H FVG @12/06/2026, present on 2h **578–601**, 1h
  **578–587**, 15m **582–586**; box 581–588 within ~3pt). **t30a/b/c_fvg_1 hit** via 1h-proxy (bull
  3.6×ATR gap 790–807 @18/08/2025 at the demand base; edges ~5pt). **t30b/c_fvg_2 partial**
  (hand-refined "fvg entry" pocket 793–800 — detector emits the whole gap, not the sub-pocket).
  **t30b/c_ifvg partial** (parent bear gap 797–805 @28/08 reclaimed → flips; concept modeled, flip
  timing needs native tf).
- **DABUR** 0 / 0 / 2 — **t26, t27 uncheckable**: 5m marks in Feb-2026 / Nov-2025; native 5m tape
  starts **2026-05-25**. A negative 1h scan **cannot falsify** a 5m gap. But the marks themselves
  confirm the method geometry: **entry ≈ CE**, **SL 0.8–2.5pt beyond the box** (t27 SL 486 = exact low).
- **DLF** 0 / 0 / 1 — **T19_2 uncheckable + structural**: FVG-**as-target**; native 5m absent; 1h
  shows an *opposite*-direction gap at the level. Detector has no target/magnet output.
- **HEROMOTOCO** 0 / 0 / 4 — no yahoo tape at all; long5m does not reach Feb/Sep/2020 marks.
- **Reference/foreign** 0 / 0 / 10 — r1301, r1316, 6× b8d2 schematics, 2× BTC: no NSE tape.
  Conceptually the schematics ARE the detector's rule (b8d2_c06 = literal 3-candle bull/bear; c05
  labels the CE that `CE_HOLD` uses).

**Structural gaps (with the numbers seen):**
1. **Birth-gate absent → over-detection.** `fvg.py` fires on **every** ≥0.3×ATR wick-gap mid-air.
   Measured: **4 qualifying FVGs in ONE 30m session** (HDFCBANK 2026-07-06); the user marked **1**.
   The user's FVG is gated by *sweep+BOS off a swing extreme, inside an OB* — the detector has none
   of that.
2. **Box anchor: impulse-range vs wick-gap.** At swing extremes the user boxes the **displacement
   candle's range**; the 3-candle wick-gap forms **~5–6pt lower/inner** (HDFCBANK 08/07: box 825–832
   vs gap 818.5–826.8). Systematic top-edge offset on bearish marks.
3. **tf-granularity.** T2a's FVG lives on **5m**, not the charted 30m; the detector reproduces it
   only when `tf` matches the imbalance's real timeframe. A mark's chart-tf ≠ the gap's tf.
4. **Entry = CE, not edge.** `fvg.py` `CE_HOLD` fires at the CE (correct); but `fvg_n` (the frozen
   successor) uses **edge entry** (`zone=box`) — contradicts the user's CE entries (t26/t27).
5. **SL = beyond outer wick, not none/inner.** `fvg.py` emits **no SL**; `fvg_n` emits the **box far
   edge** (inner). The user's SL sits **0.8–2.5pt beyond** the box (t26 522.3, t27 486). Neither
   detector emits the beyond-outer-wick stop.
6. **iFVG modeled but flip-driving unclear.** `fvg.py` `IFVG` needs the Level in `INVERTED` state
   (set by the harness, not by `fvg.py` itself); `fvg_n` flips on kill. Concept present (t30 ~798,
   c04), flip event unverified at available tf.
7. **FVG-as-target unmodeled.** T19_2: the FVG is the short's **objective**, never an entry. No
   detector emits an FVG as a draw-on-liquidity target.

**Data limits (no silent drops).** 17/35 uncheckable: 10 reference/foreign (no NSE tape); 4
HEROMOTOCO (no yahoo file, long5m 2026-04-27..07-17 only); 3 DABUR/DLF (native 5m only from
2026-05-25, so Feb-2026/Nov-2025 5m marks can't be reproduced — 1h is too coarse to resolve a 5m
gap, and a **negative** coarse scan does not falsify a fine-tf gap). Year labels for 2025/2024/2020
marks are price-era guesses (RETHINK: only t31 SBILIFE is firmly dated — and it is not an FVG); T4's
"2026" is demonstrably the wrong era (2045 traded only Sep-2024). SBICARD t30 hits rest on a
**positive** 1h corroboration (gaps 3.6×ATR — too large to be a resample artifact); native 15m/5m
granularity is unverified.

## Enhancement plan

Prioritized. References exact params/functions.

**P1 — Structural: gate birth on sweep+BOS inside a zone (kills over-detection).**
The single biggest miss is 4-per-session vs 1. Add a birth gate so an FVG only arms when it forms
**in the displacement leg that swept a liquidity extreme and broke structure**, and preferably
**nests inside a live OB**. Concretely: require the FVG's c1..c3 window to (a) follow a `sweep`
detector event on the near extreme (from EXT, not fractal), and (b) sit inside a live
`ob_taught`/`ob_lux` zone. Implement as an optional confluence filter consuming those detectors'
Levels before `fvg.py._create` appends, or as a post-filter in the ensemble. `fvg_cb`/`fvg_n`
displacement gate is a *partial* proxy (it cut nothing structural here) — displacement ≠ sweep+BOS.

**P2 — Structural: box from outer wick, entry at CE, SL beyond the outer wick.**
- Keep the wick-to-wick box (already correct in all three).
- **Entry**: standardize on **CE** (fvg.py `CE_HOLD` is right; change `fvg_n`'s edge entry — its
  `_evidence` `zone=(z.lo,z.hi)` — to also surface a CE anchor).
- **SL**: emit `meta.sl` = **beyond the outer wick** of the origin candle, i.e. `c1.low - buf`
  (bull) / `c1.high + buf` (bear), NOT the box far edge. Target buffer from the marks:
  **≈ 0.8–2.5pt** or **0.15–0.3×ATR** past the outer wick (t26 0.8pt, t27 2.5pt). Add `sl_mode:
  "outer_wick"` to `fvg_n._DEFAULTS` and compute it in `_evidence` (currently `sl = z.lo/z.hi`).
  `fvg.py` should emit an SL at all (today it emits none).

**P3 — Numeric thresholds (TARGET values from the data).**
- `min_gap_atr` (fvg.py, default **0.3**): every clean hit was **1.4–3.7×ATR** (t1b 1.44, HDFCBANK
  3.66, t30 3.61, t28 3.34). The micro-gaps that inflate the count are 0.3–0.9×ATR. **Raise the
  default to ≈ 0.7–1.0×ATR** to keep the marked-grade gaps and drop the noise. (This mirrors
  `fvg_cb`'s auto mean-range% gate, which achieves the same effect adaptively — prefer porting that
  gate over a fixed constant if adopting one detector.)
- `depth_atr` (fvg_n break-depth, default **0.5**): unchallenged by this data; leave frozen.
- Add a **tf-set sweep**: run the detector on the imbalance's true tf, not the chart label. T2a
  needs 5m; t28 shows the 2H gap survives 15m→2h. A multi-tf pass (5m + 15m + 30m + 2h) with the
  merge rule would have caught T2a. Wire `tf` as a list in `fvg_n`.

**P4 — New outputs for the two unmodeled use-cases.**
- **FVG-as-target** (T19_2): emit unfilled far-side FVGs as **magnet/target** metadata (a
  `draw_on_liquidity` Evidence or a target field), so an entry detector can aim at them. New, small.
- **iFVG** (t30 ~798, c04): make the flip self-contained. `fvg_n` already flips on kill (good);
  for `fvg.py`, drive the `INVERTED` state internally (on full-fill-then-reclaim) rather than
  depending on the harness, so `IFVG` (0.75) actually arms.

**P5 — Confluence scoring.** Because the FVG is almost always the *refined pocket inside an OB born
after a sweep*, its strength should scale with confluence: +weight when nested in a live OB, when
born in a swept+BOS leg, and when it is the CE-side pocket. This is the ensemble's job, but expose
the flags (`in_ob`, `swept_birth`, `is_ce_pocket`) from the FVG Evidence `meta` so the combiner can
use them.
