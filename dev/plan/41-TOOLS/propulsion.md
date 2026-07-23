# propulsion

Validation of the shipped propulsion detectors against **every** hand-marked
`propulsion` instance in `runs/validate/tools/registry.jsonl` (15 instances, no
sampling). Code: `app/trader/detectors/propulsion2.py` (LIVE, parent-linked) and
`app/trader/detectors/propulsion_block.py` (legacy/orphaned, kept for parity).
Per-instance records: `runs/validate/tools/val_propulsion.jsonl`.

RECOGNITION-only scope (per `runs/validate/RETHINK.md`): this doc asks "does the
detector reproduce the drawn object?" It makes NO profitability claim.

## Feature notes (structure & validity)

**What the user means by "propulsion".** Across the 15 marks the word covers TWO
different drawing objects:
- a **propulsion BLOCK** — a small horizontal zone (box) that launches an impulse
  leg (4 marks: `t25`, `h4621` explicit-labelled, schematics `c35`/`c36`).
- a **propulsion/markup LEG** — a slanted projection **line/arrow** tracing the
  impulse itself (11 marks: `t29*`, `t30*`, `t31*`, BTC/EUR/schematic `b8d2_*`).

The shipped detectors model ONLY the block. This is the dominant structural gap:
**11/15 hand-marks are projection lines the block detector cannot draw.**

**propulsion2 (LIVE) geometry & rules.**
- Candle/price geometry: a **body-range box** (`min(O,C), max(O,C)`) — bodies-only,
  wick excluded. Runs a private `ObZones` (identical taught-OB computation to
  `ob_taught`, `tf=5m`, `depth_atr=0.5`).
- BIRTH: on the parent taught-OB's **first armed retest** (`ObZones.step` yields
  `retest`, zone still `alive`), IF the retest candle **closes away** beyond the
  zone in the parent direction with a directional body
  (`c.close>z.hi and c.close>c.open` for demand; mirror for supply). Child =
  that candle's body range, carrying `meta["parent"]=z`.
- DEATH: child dies **instantly with its parent** (death cascade runs BEFORE the
  child's own bar step) and under the same break-depth law (`step_zone`,
  `>=0.5*ATR` close-through kills). Orphan emission is forbidden by construction
  (the +43.4pp "parent-live respect 60.2% vs orphaned 16.8%" law, lesson 14).
- SIGNAL (one-shot, child's first armed retest): parent direction, **edge entry**
  (`zone=(k.lo,k.hi)`), `ttl=4`, `strength=0.8`,
  `sl = k.lo (LONG) / k.hi (SHORT)` = **child body far edge**, `sl_floor=0.15*ATR`.
- Dep: config requires `ob_taught` enabled before it (`check_detector_deps`).

**propulsion_block (LEGACY, orphaned).** Kept "untouched for parity history."
Materially different geometry that is actually CLOSER to the user in two ways:
box = tapping candle **full range `(low, high)`** (includes the wick), and
`sl = tap low/high` (the **wick**, not the body edge). But it consumes any live
`OB_BULL/OB_BEAR` Level with **no parent linkage** (`propel_atr=1.0` displacement
gate over `propel_bars=3`) — i.e. it is the anti-signal orphan the +43.4pp law
forbids, hence deprecated.

**CONFLUENCE.** Parent = taught OB born from a swept extreme + continuation break
(BOS). `ob_taught` grades pivot-distance against `EXT_L/EXT_H` first, swings as
fallback — so liquidity is anchored on **extremes, not fractal furniture**
(doc35's "liquidity from EXT not fractal" is satisfied on the parent side).

## How the user draws it

Two hands:
1. **Block hand** (`t25`, `h4621`, `c35`, `c36`): a box on the last down/up-candle
   cluster that price *re-drives out of* after mitigation. `t25` is explicitly
   merged with the OB ("ob+propulsion block", box 420.3-422). `h4621` is
   explicitly labelled **"PROPULSUION BLOCK"** (box 990-982). The box wraps the
   **outer wick** of the sweep, entry near **CE**, and SL sits **beyond the outer
   wick** (`t25`: SL 419, below the 419.25 swept low).
2. **Leg hand** (`t29*`, `t30*`, `t31*`, `b8d2_*`): a **projection line/arrow**
   from the launch point to the target, tracing the whole markup (or markdown)
   — e.g. `t29` 833->903, `t30` 795->858, `t31` 1825->1932 up then 1932->1740 down.

## Accuracy verdict

**pct_match = 0.0%** (hit / (hit+partial+miss) = 0 / 9). Counts over ALL 15:
**hit 0 · partial 1 · miss 8 · uncheckable 6.**

| verdict | n | instances |
|---|---|---|
| hit | 0 | — |
| partial | 1 | `t25` (DABUR, block, simulated) |
| miss | 8 | `t29b/c/d/e`, `t30b/c` (SBICARD lines), `t31b_1/2` (SBILIFE lines) |
| uncheckable | 6 | `h4621` (no data), `c35`/`c36` (schematic, structural match), `b8d2_c02`/`c04`/`c13` (foreign/schematic) |

Per-stock: DABUR 1 (partial) · HDFCBANK 1 (uncheckable) · SBICARD 6 (miss) ·
SBILIFE 2 (miss) · BTCUSD/EURUSD/schematic 5 (uncheckable ×4 + counted above).

### Structural gaps
- **Primitive mismatch (8 of the 9 gradable marks).** The 11 leg-marks are
  projection lines; the detector emits a horizontal block. It structurally cannot
  reproduce them. Data confirms the legs are real (SBICARD 1h: `830->906` Dec25-Jan26,
  `788->905` Sep25; SBILIFE daily: `1818->1928` then `1928->1733` 2024) — the marks
  are faithful, the detector's OUTPUT TYPE is wrong for them.
- **Bodies-only box + body-edge SL** (propulsion2) vs the user's **outer-wick box
  + sub-wick SL** (doc35 gaps #1, #3). The legacy `propulsion_block` had the
  wick geometry but was deprecated for losing parent-linkage — the geometry the
  user wants and the linkage the edge-law wants currently live in different files.
- **Edge entry, not CE** (doc35 gap #2).
- **Retest-dependency.** propulsion2's child needs the parent OB's *post-launch*
  first-armed-retest. A **vertical launch** (the user's actual setup) leaves the
  zone and never returns, so the launching block is never emitted at the mark.

### Numeric gaps (from real-candle simulation of ObZones+propulsion2 on `t25`)
DABUR 5m, 2026-05-25..07-02, driven through the exact shipped logic:
- **Massive over-firing:** **504 taught-OB zones -> 50 propulsion children -> 23
  emitted evidences** in ~5 weeks on ONE symbol, vs the user's **1** deliberate
  block. The parent-linkage barely constrains because bodies-only 5m OB births a
  micro-zone on nearly every swing.
- **The mark is not reproduced:** NO long child births at the user's **420.3-422**
  zone off the **06-23 sweep to 419.25**. Children near the zone are **short**
  (`06-23T15:15` `[419.75,419.95]`, `06-24T10:15` `[419.50,419.65]`) — wrong
  direction. The nearest LONG evidences are `06-19T14:55` `[421.20,421.70]`
  (unrelated pre-sweep swing, coincidental overlap) and `06-24T15:25`
  `[423.20,423.35]` (**above** the box). The 07-01 vertical launch (423->447)
  emits only a **short** counter-trend child (`07-01T12:25` `[442.05,444.80]`);
  long children appear only on 07-02 at **445-447**, chasing.
- **Box:** children are **0.15-0.5pt** single-candle bodies vs the user's **1.7pt**
  cluster; bodies-only excludes the 419.25 sweep wick.
- **SL:** child body-edge + `0.15*ATR(0.63)≈0.09` floor ≈ **420-421**, sitting
  **above** the 419.25 swept low. User SL **419** is **below** the outer wick →
  detector SL is **~1-2pt too tight and gets stopped by the very sweep** that
  makes the setup.

### Data limits (logged, no silent drops)
- `h4621` (HDFCBANK, the highest-confidence tag — user-written label) is a real
  block but **Oct-2025 has no data** (long5m only <60d since ~2026-04; no Yahoo
  HDFCBANK). Uncheckable purely on data — priority backfill.
- `t31` (SBILIFE 2024) is **daily-only**; native-5m block cannot even be computed.
- `t29*`/`t30*` on 1h; `t29` year is ambiguous (registry label 2025 vs
  `results.json` `S_t29_long`=2020) — moot, the primitive mismatch dominates.
- `b8d2_c02/c04/c13` (BTC/EUR/schematic) and `c35/c36` (schematic) have no NSE
  tape. `c35`/`c36` are **positive controls**: they ARE propulsion2's schematic
  (child block nested on the parent OB), so "uncheckable" here is not a failure.

## Enhancement plan

Prioritised. References exact params/functions in `propulsion2.py` unless noted.

1. **[STRUCTURAL, highest] Outer-wick box + sub-sweep SL — port the legacy
   geometry into the live detector.** Replace the bodies-only child box
   `lo,hi = sorted((c.open, c.close))` (propulsion2 L76) with the tapping candle's
   **full range `(c.low, c.high)`** (propulsion_block's object), and set
   `_evidence` `sl` to the child **wick** far edge (`k` low for LONG / high for
   SHORT) instead of the body edge (L91-92). TARGET on `t25`: SL below the
   **419.25** sweep low (≈419, matching the user) instead of ≈420.5. Keep the
   `0.15*ATR` floor as a floor only. This unifies "the linkage the edge-law wants"
   (propulsion2) with "the wick geometry the user draws" (propulsion_block) —
   then the legacy file can finally be retired.

2. **[STRUCTURAL] Emit at the launch/BOS bar, not only on a later retest.**
   Add a birth mode where the child fires on the **parent's first armed retest
   candle itself** (the close-away bar), rather than requiring the *child's* own
   subsequent armed retest before emission (propulsion2 L64-68 gates the evidence
   on `step_zone(k,...)=="retest"`). The user's vertical launches never retest;
   emitting on the close-away candle captures them. Guard with the parent being a
   **swept-EXT OB** so this stays a launch signal, not noise.

3. **[NUMERIC-THRESHOLD] Kill the over-firing (504 OB -> 50 -> 23 vs 1 mark).**
   Gate child birth on parent quality, not "any live OB":
   - require `parent.meta["pivot_dist_atr"]` within a max (parent anchored near a
     real EXT pivot — the swept liquidity), TARGET `<= ~1.0` ATR;
   - require a minimum parent zone width, TARGET `>= ~0.5*ATR` (drop the 0.05-0.15pt
     micro-OBs that dominate the 504);
   - require the parent's birth leg to have **swept** its `pex` (reuse the
     `swept` test already computed in `ob_taught.ObZones.step` L75-78) so only
     post-sweep OBs spawn propulsion children.
   TARGET: reduce ~23 evidences/5wk/symbol toward O(1-3), i.e. one deliberate
   block ≈ one signal.

4. **[ENTRY] CE option.** Add a `entry="ce"` param so the evidence anchors the
   entry at the zone midpoint (`(k.lo+k.hi)/2`) instead of the edge (doc35 gap #2).
   On `t25` CE≈421.15 matches the user's ~421; edge does not by rule.

5. **[SCOPE/PRIMITIVE] Decide leg vs block explicitly.** 11/15 marks are
   markup/markdown **projection lines** the block detector cannot represent.
   Either (a) formally scope `propulsion` to the BLOCK and re-file the leg-marks
   under a `markup_leg`/impulse-leg tracer (a slope+extent object, not a zone), or
   (b) add a companion leg detector. Without this, `propulsion` will always score
   ~0% against the registry because most of its instances are a different object.

6. **[DATA] Backfill `h4621` (HDFCBANK Oct-2025) and `t31` intraday.** The one
   real-tape pure BLOCK we could not verify (`h4621`) and the SBILIFE 2024 legs
   are data-gated, not logic-gated — fetch the tape to convert 2 uncheckables into
   graded results before trusting the pct_match denominator.
