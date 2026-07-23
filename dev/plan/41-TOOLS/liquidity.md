# liquidity

Validation of detector `app/trader/detectors/liquidity.py` (class
`LiquidityDetector`, `name="liquidity"`) against **every** hand-marked
`liquidity_pool` instance in `runs/validate/tools/registry.jsonl` — **58
instances** across 5 NSE symbols (HAVELLS, VOLTAS, DLF, DABUR, SBILIFE) plus 23
foreign/educational reference graphics. Per-instance records:
`runs/validate/tools/val_liquidity.jsonl`.

Guardrail honoured (RETHINK.md): this validates **RECOGNITION** (does the
detector place a pool level on the price/structure the user drew) — **not
EDGE**. Nothing here claims profitability. Only t31 SBILIFE has a firm year; all
other years are price-era guesses, so several "gaps" are registry date/year
ambiguities, not detector faults.

## Feature notes (structure & validity)

**What the user's `liquidity_pool` mark is.** A horizontal line (or pivot dot)
at resting liquidity — a price other traders' orders sit on. Four sub-shapes
appear in the marks:
- (A) **Equal-highs / equal-lows shelf** (BSL / SSL): a rail across ≥2 matching
  extremes tapped repeatedly (most HAVELLS marks 1213/1215/1300/1330, VOLTAS
  1393/1357, DLF 770, SBILIFE 1932/948). This is the dominant shape.
- (B) **A single swing-high / swing-low EXTREME** (EXT) — "external liquidity
  above/below the range", a lone pivot (HAVELLS t1a 1234.34/1125.51, DLF pivot
  786, DABUR pivot 419, SBILIFE 985, the swept spike 1322).
- (C) **A prior support/resistance level** the block sits on (HAVELLS 1375, the
  1330 base).
- (D) **A draw-on-liquidity TARGET / SL** (HAVELLS 1770 target, 1140 downside
  target, 1221/1223 SL-above, DABUR 419 SL).
The tradeable read: the pool is the fuel — price is drawn *to* it, sweeps it,
then reverses; the pool doubles as the SL anchor or the take-profit for the trade
coming from the other side.

**What the code creates.** `liquidity.py` is a **static level factory** writing
to `ctx.levels` (side-channel, like `swings.py`), then emits ≤2 NEUTRAL proximity
`Evidence`. It manufactures five level families:
- **PDH/PDL** — prior-day high/low from M1 `prev_day` (`_create_pdh_pdl`,
  `:59-62`).
- **PWH/PWL** — prior ISO-week D1 max-high / min-low, one pair per iso-week
  (`_create_pwh_pwl`, `:64-79`).
- **OPEN_RANGE_H/L** — first `or_minutes=15` of the session (`_create_open_range`,
  `:81-87`).
- **ROUND** — nearest multiple of `round_steps=[50,100,500]` within
  `round_within_pct=2.0` of close (`_create_round`, `:98-119`).
- **EQH/EQL** — clusters of `SWING_H`/`SWING_L` levels grouped when adjacent mids
  are within `eq_tolerance=0.001` (**0.1%**), requiring **≥2** members
  (`_create_eq`, `:123-170`). This is the **only** mechanism that targets the
  user's equal-highs shelf.

**Zone geometry.** Session/round pools are `(p - tick, p + tick)` — a razor-thin
band, so a horizontal *line* mark is reproduced to ±1 tick when a level exists.
EQH/EQL zone = min-to-max span of the clustered swing zones (`:147-151`).

**HOW/WHEN it fires as Evidence.** `_proximity_evidence` (`:174-215`): for the
nearest ACTIVE/TESTED pool **above** and **below** price, if within
`proximity_atr=1.0 * ATR(M5)`, emit one `Direction.NEUTRAL` Evidence
(`strength = _pool_strength * 0.5`, `ttl=12`, `meta.event="POOL_NEAR"`).
`_pool_strength` (`:217-227`): EQH/EQL by touches+48h-recency; OR/weekly `0.7`;
PD `0.6`; else `0.4`.

**CONFLUENCE.** The pool is leg-0 of the taught chain
`liquidity(pool) → sweep → BOS → OB/FVG entry`. `liquidity.py` only *catalogs*
the pool and flags proximity — it has **no** sweep/BOS logic, **no** direction,
and **no** notion of the pool as a short-target or SL. Sweep consumption lives in
`sweep.py` (which reads these levels' SWEPT transitions); pairing with an OB lives
in `ob_taught`. So this detector's job is purely *"is there a pool here"*.

## How the user draws it

A single horizontal line dragged across the wicks of ≥2 equal extremes (BSL/SSL),
or a line/dot on one prominent swing extreme ("external liquidity"). The line is
placed on the **outer wicks**, and it carries a *purpose*: it is the sweep
target/anchor, and it frequently doubles as the **SL** (drawn just above the
equal-highs: T16 1221/1223; DABUR 419 below) or the **take-profit** (drawn below
as the short's draw-on-liquidity: T16b 1140, T3b 1770). Per doc35/commit 8dc7cc8
the *taught* anchor is the **EXTREME** (ranked pivot from `extremes.py`), not a
fractal swing — the user marks the range boundary, then expects price to reach for
it.

## Accuracy verdict

**pct_match = 2 / 34 = 5.9%** — hit / (hit+partial+miss); the 24 uncheckable
excluded from the denominator.

| verdict | count | meaning |
|---|---|---|
| hit | 2 | detector deterministically places a pool at the exact line |
| partial | 27 | correct mechanism (EQH/EQL) or a near ROUND, but a param/anchor/semantic gap blocks exact reproduction |
| miss | 5 | single extreme / SL-pivot / target — **no** detector mechanism can place a pool there |
| uncheckable | 24 | 23 foreign/reference schematics (no NSE tape) + 1 price-scale anomaly (HAVELLS T3b 1770) |

The two "hits" are both HAVELLS **1300** (T11a, T11b_2): 1300 is an exact
multiple of 50 and 100, so `_create_round` manufactures a pool at 1300 whenever
price is within 2% — reproducing the user's line at 0.0% by coincidence, *not*
via the equal-highs semantic the user intended. **On its own equal-highs
mechanism the detector reproduces the user's exact rail in essentially 0 of 34
NSE marks** — the 27 partials are all "the concept is right, the level as-built
lands off the line or won't group."

**Per-stock breakdown**

| stock | hit | partial | miss | uncheck | note |
|---|---|---|---|---|---|
| HAVELLS | 2 | 19 | 3 | 1 | 1300=ROUND hit; equal-highs shelves = partial; EXT lines/spikes = miss; 1770 anomaly |
| VOLTAS | 0 | 2 | 0 | 0 | 1393 EQH (0.06%) fires; 1357 line sits ~0.4% above the true lows |
| DLF | 0 | 3 | 0 | 0 | 786 pivot & 770 shelf — near-EQ pairs but tol/anchor gaps |
| DABUR | 0 | 0 | 1 | 0 | 419 single swing-low used as SL — no mechanism |
| SBILIFE | 0 | 3 | 1 | 0 | 1932 firm-year EQH just exceeds tol; 985 single high = miss |
| reference/foreign | 0 | 0 | 0 | 23 | EURUSD/GBPUSD/BTC/XAU + schematics |

**NUMERIC gaps seen in real data (values):**

- **`eq_tolerance=0.1%` is too tight for the user's "equal" eye.** Measured
  cluster widths at the drawn rails: SBILIFE **1932 = 0.17%** (highs 1936.0 /
  1932.8, 3.2 pt vs the 1.93-pt tol → **NOT grouped**), DLF **770 = 0.19%**
  (769.05 / 770.5), HAVELLS **1140 = 0.14%** (1140.05 / 1141.0 / 1141.6),
  HAVELLS **1218 = 0.15%** (1217.5 / 1219.3 / 1217.4), HAVELLS **1230 shelf =
  0.42%** (two pushes 1228.8 → 1234.0). The tight ones DO pass — HAVELLS 1213
  (0.05%), 1330 (0.05%), VOLTAS 1393 (0.06%), the 1231.0-1231.6 sub-shelf
  (0.05%). So the tol catches ~single-session micro-shelves but **splits the
  multi-day rails the user actually trades** (median observed width ≈ 0.15-0.2%).
- **ROUND rarely coincides.** Of 22 distinct NSE prices only **1300** is an exact
  round; **948→950 = 0.21%**, **604→600 = 0.66%** land nearby; all others are
  15-30 pt (1-2%) off the nearest step, so ROUND does not reproduce the marks.
- **Single extremes have no home.** The 5 misses are lone pivots: HAVELLS 1234.34
  (abs 5m high 1289.6; nearest ROUND 1250 = +1.3%), the 1322.9 swept spike
  (ROUND 1300 = −1.7%), 1387 (daily single 1389.65; ROUND 1400 = +0.9%), DABUR
  419.7 (no EQL pair within 0.42 pt; SL role), SBILIFE 983.75 (next high 974 =
  −1.0% → no pair). None are ≥2-equal, none near a round → **zero levels created**.

**STRUCTURAL gaps (root causes):**

1. **No single-swing-extreme (EXT) pool.** The user's EXT anchor (`extremes.py`
   `EXT_H`/`EXT_L`, made *the* taught liquidity anchor in commit 8dc7cc8) is
   never turned into a pool here — `_PROXIMITY_KINDS`/`_create_eq` know only
   PD/PW/OR/ROUND/EQH/EQL from **fractal** `SWING_H/SWING_L`. Every lone-extreme
   mark (all 5 misses + the EXT lines t1a) is structurally unreachable.
2. **EQ anchored on fractal swings, not extremes.** doc35: "liquidity from EXT
   not fractal." `_create_eq` sources `LevelKind.SWING_H/SWING_L` (`:53-54`), so
   even correct equal-highs are grouped from ZigZag pivots, not the ranked
   extremes the user drew from.
3. **NEUTRAL-only, no direction / no sweep-taken lifecycle / no target-or-SL.**
   `_proximity_evidence` emits `Direction.NEUTRAL` "POOL_NEAR" only. A pool that
   is the short's **draw-on-liquidity target** (T3b 1770, T16b 1140) or the
   long's **SL** (DABUR 419, T16 1221/1223) cannot be expressed — there is no
   `zone`-as-target/SL field and no "SWEPT/taken" state emitted from here.
4. **Proximity gate hides distant pools.** Even when a pool exists, Evidence only
   surfaces within `1.0*ATR(M5)`. The rail the user draws as a *far* target
   (10-20 pt away) is created but silent until price approaches — fine for
   "near" alerts, wrong for "this is the objective."

**Data limits (per RETHINK / no silent drops):**
- 5m native only < 60 d (`data/long5m` Apr27-Jul17 2026 + Yahoo 5m since
  2026-05-04); 1h from ~2024-07; daily full but **back-adjusted** (HAVELLS 2002 =
  1.61) — recent-decade prices verified ≈ real (DLF 786, SBILIFE 948, HAVELLS
  2020-23 all matched tape). So the **2026** marks (t1a, t1d-h, T19_1, t25) were
  checked on their native 5m; **2025** DLF on 1h/daily; **2020-24** HAVELLS /
  SBILIFE on **daily only** — the intraday equal-highs the EQH mechanism needs
  could not be observed, so those verdicts read the *daily envelope* and are
  flagged in `numeric_gap`.
- Years are price-era guesses except **t31 SBILIFE (firm 2024)**. HAVELLS **1213**
  matches an equal-highs cluster in the **2023-02** window (1213.25/1213.9), not
  the tagged **2022-01** window (a cascade with no 1213 shelf); HAVELLS **1387**
  matches **2023-09-01** (1389.65), not the tagged early-Aug — logged, not dropped.
- 23 foreign/reference charts (EURUSD, GBPUSD, BTC, XAUUSD, schematics) have no
  NSE tape → uncheckable. HAVELLS **T3b 1770** is a price-scale anomaly (HAVELLS
  ≈ 1200 in 2026) → uncheckable, logged with reason.

## Enhancement plan

Prioritised; exact params/functions referenced. RECOGNITION-scoped — none claims
edge.

**P1 — structural: add a SINGLE-EXTREME pool family (`EXT_H`/`EXT_L`).** The
single largest recognition hole (all 5 misses + the EXT-line partials). Create
pool `Level`s directly from `extremes.py` ranked pivots — not only from ≥2-equal
`SWING` clusters. Add `EXT_H`/`EXT_L` to `_PROXIMITY_KINDS` (`:22-26`) and a
`_create_ext(ctx)` that emits tick-thin zones `(p-tick, p+tick)` at each active
extreme. This makes lone swing highs/lows (t1a 1234/1125, DLF 786, DABUR 419,
SBILIFE 985, the 1322 spike) pools, and aligns with commit 8dc7cc8 ("extremes are
the taught anchor").

**P2 — structural: anchor EQH/EQL on extremes, widen tolerance.** Change
`_create_eq` source from `SWING_H/SWING_L` (`:53-54`) to the `EXT_H/EXT_L` ranks
(fractal swings as fallback), closing doc35's "EXT not fractal" gap. **Numeric
target:** raise `eq_tolerance` from `0.001` (0.1%) to **`0.0025`-`0.003`
(0.25-0.3%)**, or make it ATR-scaled (**≈0.25×ATR(tf)**). At 0.25-0.3% the
detector unites the measured user rails it currently splits — SBILIFE 1932
(0.17%), DLF 770 (0.19%), HAVELLS 1140 (0.14%) / 1218 (0.15%), and the HAVELLS
1230 sub-shelves — while still rejecting the genuinely loose SBILIFE 948 (0.58%).
This alone converts most of the 27 partials from "won't group" to "groups on the
line."

**P3 — structural: emit direction + target/SL + swept lifecycle.** Extend the
Evidence `meta` (`:206-213`) beyond `POOL_NEAR`: (a) a `role` = `TARGET` (opposite
side of price, the draw-on-liquidity objective) vs `SL_ANCHOR` (just past the
pool, the outer-wick stop), so the user's T3b-1770 target and DABUR-419 SL become
expressible; (b) surface the pool's `SWEPT`/taken transition here too (today only
`sweep.py` reads it), tagging `event="POOL_TAKEN"` when a wick pokes through and
closes back — the sweep-then-reverse the whole method rests on. Keep additive in
`meta` (non-breaking).

**P4 — numeric: relax/parameterise the proximity gate for targets.** Keep
`proximity_atr=1.0` for near-alerts, but do **not** suppress a pool tagged
`role=TARGET` when it is >1 ATR away — a draw-on-liquidity objective is *supposed*
to be far. Add `target_max_atr` (e.g. **8-10**, covering the observed 10-20 pt /
multi-ATR runways) so far pools are still emitted, distinctly, as objectives.

**P5 — config/data hygiene.** EQ/PW/OR/PD all assume an intraday stream; on
daily-only history `_create_eq` gets no `SWING` levels and produces nothing.
Document that pool recognition for HTF marks (30m/1h/daily) requires TF-matched
data, and (cross-cut with sweep.md P5 and RETHINK A2) re-resolve the ambiguous
years — HAVELLS 1213 (2022→2023) and 1387 (Aug→Sep) are demonstrable mislabels
found *by* this validation — before these marks are used as ground truth.
