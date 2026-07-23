# extremes

Validation of detector `app/trader/detectors/extremes.py` (class
`ExtremesDetector`, `name="extremes"`; fallback anchor `swings.py`,
`SwingsDetector`, `name="swings"`) against **every** hand-marked `extreme_swing`
instance in `runs/validate/tools/registry.jsonl` — **68 instances** across the
HAVELLS/HEROMOTOCO/DABUR/SBILIFE trade set plus schematic/forex reference charts.
Per-instance records: `runs/validate/tools/val_extremes.jsonl`.

Guardrail honoured: this validates **RECOGNITION** (does the zigzag confirm a
pivot on the candle the user drew, at the right price, right side) — **not
EDGE**. Nothing here claims profitability. Per RETHINK.md only t31 SBILIFE has a
firm year; every other date/year is a price-era guess, so marks were located by
**price era**, not by the registry's `resolved_date` (several of which are
demonstrably wrong — see below).

## Feature notes (structure & validity)

**What the user's `extreme_swing` mark is.** A pivot dot or horizontal line at
**the highest pivot high (or lowest pivot low) of a leg** — the taught structural
anchor and the resting-liquidity source the trade is built against (labels seen:
"EXTREME SWING LIQIUIDITY", "swing-high liquidity", "lowest swing low"). It is
NOT an entry or an SL object: in the registry every `extreme_swing` has
`entry=null, sl=null`. It is the pool that a later `sweep` runs and that a
`structure`/`ob_taught` entry is measured from. On the c01/c02/b8d2 schematics it
is the HH/HL/LH/LL sequence itself (dealing-range boundaries).

**What the code detects.** `extremes.py` is an **infrastructure detector** —
`detect()` always returns `[]` and instead writes `EXT_H`/`EXT_L` `Level`s onto
`ctx.levels` (born = pivot-bar ts, zone = wick band). The pivot engine is a
**causal percent-leg zigzag** (research `ext_zigzag.zigzag`, frozen `TUNE.md`):

- **Leg floor** (`_zigzag`, `extremes.py:84-160`): a pivot confirms only when the
  reversal leg from its extreme reaches `k[i] = K·ATR(14,Wilder)` with
  `K = clip(leg_pct / median(ATR/close), 3, 14)` (`_leg_K`, `:74-81`), default
  `leg_pct = 6.0` (`_DEFAULT_LEG_PCT`).
- **Alternation with replacement** (`:121-123, 141-143`): never two same-side
  pivots in a row; a deeper extreme before the reversal completes **replaces** the
  pending pivot — *the deepest extreme wins*.
- **Late confirmation** (`:157-160`): a pivot exists only once its reversal leg
  reaches the floor; a still-running extreme is emitted `pending` (unconfirmed).
- **Wick-beyond-bodies band** (`_band`, `:163-187`, lesson 13): `EXT_H` zone =
  `[max body of the pivot cluster … wick high]`; mirror at lows. The band **top/
  bottom is the true wick extreme** — i.e. the outer-wick price, exactly the
  liquidity/stop reference the method rests on.
- **Rank/master meta** (`:212-237`): `rank_atr = min(leg_in,leg_out)/ATR(pivot)`;
  `master` = the window's max-high / min-low confirmed pivot.
- **Params/defaults**: `{leg_pct:6.0, timeframes:("1h",)}` (`:42-43`); ATR period
  14 (`:44`).

**CONFLUENCE.** Since commit 8dc7cc8 the EXT pivot is the **taught liquidity
anchor** (swings the fallback). `EXT_H/EXT_L` are meant to be consumed by
`sweep`/`liquidity`/`structure` as the pool to run and the LH/HL that defines
structure. **Cross-ref gap:** `sweep.py`'s `_SIDE_BY_KIND` still has no
`EXT_H/EXT_L` (see `41-TOOLS/sweep.md` P1), so the taught anchor is not yet
sweepable — the marks currently reach `sweep` only via the `SWING_H/SWING_L`
fallback. The `extreme_swing` **birth is a pure structural pivot with NO sweep+BOS
gate** — and that is *correct* for an anchor (the anchor precedes the sweep). The
doc35 "born only after sweep+BOS" gap applies to the OB/FVG **zones**, not to this
feature; on birth semantics `extremes.py` is aligned with the teaching.

## How the user draws it

A single pivot dot / horizontal line at the extreme of a swing leg, often drawn
2-3× across zoom levels of the same trade (t1d-h, T3a/T3b, T13a-c). The wick tip
is the liquidity; the user's line frequently sits a few points **inside** the wick
(drawn at the body/close cluster), so the detector's wick-extreme pivot is usually
a hair beyond the drawn line. Directionality is implicit: a swing-**high** anchor
is overhead liquidity for a short (or an old-high a long reclaims); a swing-**low**
anchor is the pool below for a long.

## Accuracy verdict

**pct_match = 17/29 = 58.6%** (hit / (hit+partial+miss); the 39 uncheckable
excluded from the denominator, reported separately).

| verdict | count | instances |
|---|---|---|
| hit | 17 | t1d, t1f, t1g, t1h, T2a, T3a_2, T3b_2, T4b, T15a, T15b, t8a, t8b, t32a, c01_1, c01_4, c01_5, c01_8 |
| partial | 5 | T3a_1, T3b_1, c01_2, c01_3, c01_7 |
| miss | 7 | t7a, T13a, T13b, T13c, t26, t27, c01_6 |
| uncheckable | 39 | c02_1-8, and all b8d2_c05/c07/c08/c10/c12/c13 + c28/c30/c32 schematic/forex |

**Per-stock breakdown** (checkable rows only; uncheckable = no tape)

| stock | hit | partial | miss | uncheck | note |
|---|---|---|---|---|---|
| HAVELLS | 12 | 2 | 4 | 0 | major daily/5m leg tops reproduced exactly; 2010 shoulder partial; 4 intraday-only bounces (t7a,T13×3) unseeable on daily |
| HEROMOTOCO | 4 | 3 | 1 | 8 | 5m swing sequence: majors hit, finer swings snapped/skipped; c02 (Dec25-Mar26) has no tape |
| SBILIFE | 1 | 0 | 0 | 0 | firm-year t31 lowest-low HIT (in-band) |
| DABUR | 0 | 0 | 2 | 0 | both are mid-rise intermediate highs below the 1h floor |
| XAUUSD / EURUSD | 0 | 0 | 0 | 5 | forex, no NSE tape |
| (schematic) | 0 | 0 | 0 | 26 | HH/HL/LL teaching diagrams, no tape |

The 17 hits collapse to ~12 distinct swings once duplicate zoom-views merge
(t1d-h = one 07-08 top; T3a_2/T3b_2 = one 24/06 top; T15a/b, t8a/b = one top
each). **On the correct-era tape the zigzag reproduces every MAJOR leg extreme on
the exact/adjacent candle, side-correct, to within ≤0.5% or in-band.** It weakens
only on finer, sub-leg-floor swings.

**NUMERIC gaps seen in real data (values):**

- *The leg floor is NOT the nominal 6% — the `[3,14]` K-clip distorts it by TF.*
  Measured `K` and resulting floor (as % of price):
  - **5m native**: `K` **clips to the 14 cap** (ATR/close so small that
    `6.0/median ≈ 24`) → floor **2.78%** HAVELLS, **2.95%** HERO.
  - **1h**: `K ≈ 7.7-8.9` → floor **6.03-6.06%**.
  - **daily**: `K` **clips to the 3 floor** (`6.0/median ≈ 2.4`) → floor **7.77%**
    HAVELLS, **8.53%** SBILIFE.
  So the "6% leg" the config names is actually **~2.8% at 5m and ~8% at daily**.
  The detector therefore confirms only ~3-8% reversal legs — genuine *major*
  swings — and silently drops the 1-3% intraday swings the user marks on 30m/5m
  charts. This single mechanism explains every partial/miss below.
- *Major leg extremes — exact.* t1d-h: pivot **1234.0 @07-08 11:30** (mark ~1231-
  1233 @ "~11:15") → **+0.08-0.20% / 0.32-0.80 ATR**, mark in-band for 1232/1233.
  T2a: **1125.9 @06-11** vs mark 1125 → +0.08%. T4b: **2106.0 @2024-09-23** vs
  mark 2100 → +0.29%, **in-band**. T3a_2/T3b_2: **1968.9 @2024-06-25** vs mark
  1975 (day-of-month exact) → −0.31%. T15a/b: **1344.7 @2022-04-27** vs 1343-1348
  → ≤0.25%, 1343 in-band. t8a/b: **1465.85 @2023-09-11** vs 1453-1455 → +0.75-
  0.88% (0.36-0.42 ATR — same-day same-top, user line under the wick). t32a:
  low **825.2 @2020-12-22** with band top **840.85** → the ~840 mark is **in-band**
  on the firm-year t31 trade.
- *Deeper-extreme snap (alternation "deepest wins").* c01_2: mark low 4985 →
  pivot **4953 @same day** (−0.64%, deeper). c01_7: mark 4715 → pivot **4672.5**
  (the true session low, −0.90%). The zigzag's replacement rule pulls the pivot to
  the deepest low of the leg, so a shallower marked low is not its own pivot.
- *Skipped sub-floor swing.* c01_6: mark high ~5030 (06-25 top 5043) is a counter-
  trend bounce **inside** the 5073→4672 down-leg; nearest confirmed H pivots are
  **11 days** either side — the ~2.9% floor merges it away. Same mechanism for
  DABUR **t26** (522.9 @1h 02-11 vs a 6.0% 1h floor; nearest H 533.7 @01-05,
  +2.2%) and **t27** (514.9 @10-23 mid-rise; nearest 529.9 @11-17, +3.2%).
- *Shoulder between pivots.* T3a_1/T3b_1: mark 2010 sits between confirmed daily
  pivots **1985.4 @06-03** (−1.22%) and the **2106 @09-23** top (+4.78%); the
  coarse ~7.8% daily floor doesn't isolate it → partial.
- *Registry date/year mislabels (not detector faults).* T3a_2/T3b_2 are labelled
  in the registry as `matched H_jun_long / resolved 2026-06-29` — but price 1975
  is a **2024** level; the detector nails it on **2024-06-25** (day-of-month
  matches "24/06"). t26/t27 `resolved_date`s likewise borrow the opposite-leg
  trade's date. Located by price era, the geometry lands; by the registry date it
  would not.

**STRUCTURAL gaps:**

1. **Single default timeframe.** `_DEFAULT_TIMEFRAMES = ("1h",)` (`:43`). At 1h
   the floor is ~6% of price, so a 6-month window yields only **4-6 pivots** —
   far too coarse to reproduce a 30m/5m swing sequence (this is why DABUR t26/t27
   and the c01 finer swings miss/partial). The marks live on 4m/5m/30m; the
   detector as-shipped scans only 1h.
2. **The K-clip fights the leg_pct intent.** `clip(pct/median(ATR/close),3,14)`
   converts a % target into an ATR-multiple then clips it — but the clip is where
   the value actually lands on both intraday (hits 14) and daily (hits 3), so
   `leg_pct` barely controls anything at the extremes and the true floor swings
   from 2.8% to 8.5% purely with TF/vol. A trader asking for "1.5% legs" cannot
   get them.
3. **No multi-scale output.** One `leg_pct` = one swing scale. The user's chart
   simultaneously shows the *major* anchor and the *minor* HH/HL/LL that hang off
   it (the whole c01/c12 sequences); the detector can render one or the other, not
   the nested set, in a single pass.
4. **EXT not yet consumed as the sweep anchor.** `extremes.py` emits the right
   object (wick-band `EXT_H/EXT_L`), but `sweep.py` cannot read it
   (`_SIDE_BY_KIND` gap, sweep.md P1). The taught "liquidity from EXT not
   fractal" wiring is half-built: the producer exists, one consumer is deaf.

**Data limits (per RETHINK / no silent drops):**
- 5m native only < 60 days (`data/long5m` 2026-04-27→07-17 + yahoo 5m since
  2026-05-04); 1h from ~2024-07 (HAVELLS/DABUR/etc.); daily full (2002+). So the
  2026 HAVELLS/HERO marks were checked on **5m native** (finest), 2024-26 HAVELLS/
  DABUR on **1h/daily**, and 2020-23 HAVELLS/SBILIFE on **daily** — coarser than
  the 4m/5m/30m the user drew (TF caveat noted per instance).
- **39 uncheckable, all logged:** `c02_1-8` — HEROMOTOCO has **no** Yahoo daily/1h
  cache and long5m starts 2026-04-27, so its Dec-2025..Mar-2026 marks have no
  tape; `b8d2_*`, `c28/c30/c32` — schematic teaching diagrams (no symbol);
  `b8d2_c10` (XAUUSD) / `b8d2_c13` (EURUSD) — forex, no NSE tape.
- **t7a, T13a-c (miss, data-limited):** these are **intraday** swing-highs (1276
  Nov-2023; 1222 Jan-2022) with **daily-only** tape. On daily they are counter-
  trend bounces inside a larger leg (1222 sits inside the 1419→1037 decline; 1276
  inside a 1232→1472 rise), below the ~7.8% daily floor, so no daily pivot forms.
  Graded miss (uniform rule: tape exists at *some* TF → grade it), but the root
  cause is the TF/data limit, not necessarily the geometry — with 5m tape and a
  ~2% floor they might confirm. Year-ambiguity compounds it: if t7a's era were
  2022, daily pivot **1270.6 @2022-12-01** would be a −0.42% hit.

## Enhancement plan

Prioritised; references exact params/functions. RECOGNITION-scoped — none of this
claims edge.

**P1 — numeric threshold: make the leg floor track the intended %, and lower it.**
The `[3,14]` clip in `_leg_K` (`extremes.py:81`) is the root distortion. TARGET
behaviour: a configured `leg_pct` should produce a floor of that % of price
regardless of TF. Concretely — replace the ATR-multiple-then-clip with a direct
percent floor `k[i] = leg_pct/100 · close[i]` (still causal, still per-bar), or at
minimum **widen the clip to `[1.5, 30]`** so intraday can go finer than 2.8% and
daily can go finer than 8%. To reproduce the 30m swing sequence (the c01/DABUR
misses), the floor needs to reach **~1.5-2.0%**: at that floor DABUR t26 (522.9,
a ~1.8% leg off the 533.7 high) and c01_6 (5043 bounce) become confirmable pivots.
Keep the 6% default for the *master/major* pass so today's 17 hits are unchanged.

**P2 — structural: multi-timeframe + multi-scale passes.** Change
`_DEFAULT_TIMEFRAMES` from `("1h",)` to run the mark's native scale — at least
`("5m","30m","1h","1d")` — and/or emit **two nested scales** (major `leg_pct≈6`
for the anchor, minor `leg_pct≈1.5-2` for the HH/HL/LL sequence), tagging each
`EXT_H/EXT_L` `Level.meta` with its `scale`. This directly closes gaps #1/#3: the
c01/c12 marks are a *sequence* of swings the single 1h pass can never render, and
DABUR/HERO intermediate highs are only visible at ≤30m.

**P3 — birth-gate / confluence: keep birth structural, wire EXT into `sweep`.**
Do **not** add a sweep+BOS gate to the anchor birth — validation confirms the
pure structural pivot is the correct object for `extreme_swing` (17/17 hits birth
with no gate). The confluence fix is downstream: add `EXT_H:"below", EXT_L:"above"`
to `_SIDE_BY_KIND` (`engine/levels.py:80-89`) so the taught anchor becomes
sweepable (sweep.md P1). Because the `_band` top/bottom is already the **outer
wick** (`extremes.py:171-187`), the EXT level *also* supplies the outer-wick SL
reference the sweep detector currently lacks (sweep.md P2, RETHINK §D2) — the
producer is already correct; only the consumer wiring is missing.

**P4 — numeric hygiene: expose `atr_period` and the K bounds as params.** The
warm-up-backfilled `_wilder_atr` (`:60-71`) and the hard-coded `[3,14]` bounds
should be `self.params`-driven so a per-symbol / per-TF calibration (needed once
P1 lands) doesn't require a code edit. Reference `_ATR_PERIOD=14` (`:44`) and
`_leg_K` (`:74-81`).

*Cross-cut for the whole registry:* T3a_2/T3b_2 (year 2026→2024, fixed by day-of-
month + price) and t26/t27 (dates borrowed from the opposite-direction trade) are
hard evidence that the circular year/price-era resolution (RETHINK A2) placed
marks on wrong candles. Re-resolve `extreme_swing` dates against the actual
confirmed pivot the zigzag finds, not the outcome-maximising year, before any of
these are used as ground truth for edge work.
