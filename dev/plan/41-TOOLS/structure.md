# structure

Validation of the `structure` feature (BOS / CHoCH) against **EVERY** hand-marked
instance in `runs/validate/tools/registry.jsonl` whose `feature ==
"structure_bos_choch"` — **61 instances** across 34 charts (HAVELLS, DABUR, DLF,
TITAN, SBICARD, SBILIFE + 20 educational/foreign schematics). Detector read:
`app/trader/detectors/structure.py`, which depends on the swing anchors written by
`app/trader/detectors/swings.py` (fractal 2N+1) — **not** the taught extremes from
`extremes.py`. Per-instance records: `runs/validate/tools/val_structure.jsonl`.

Numeric checks replicate `swings.py` (strength 3) + the `structure.detect()` trend
gate and BOS/CHoCH close-beyond-swing-mid logic causally over the real tape:
5m-native (`HAVELLS_5m`,`DABUR_5m` + `long5m/`, 2026 legs), 1h proxy
(`{DLF,TITAN,SBICARD,HAVELLS}_1h`, back ~2024-07) for pre-60d 5m/15m marks, daily
(`SBILIFE_1d`) where that is all that exists.

**Guardrail (RETHINK.md).** RECOGNITION (fires on the right candle / at the right
level) != EDGE. The already-measured record for this feature is **negative**:
`structure CHOCH -20pp`, `structure BOS -22pp` (forward-return, taught-ingredient
sweep). Nothing below claims profitability — this is a geometry/recognition audit
only. Year is firm for **t31 SBILIFE (2024)** alone; every other era is a
price-era guess (`results.json` `cand_years`), so dates are approximate and some
verdicts are necessarily `uncheckable`.

## Feature notes (structure & validity)

**Candle / price geometry the detector targets.** `structure` is an *evidence*
detector (it emits `BOS`/`CHOCH` Evidence; it does **not** emit entry/SL/target).
Per tick, on `tf` (default `5m`):
- Gather `SWING_H`/`SWING_L` Levels of that tf (from `swings.py`), sorted by birth.
- `_trend(last trend_swings=4 swings)` — `LONG` iff the last-4 swing **mids** are
  *strictly* `rising(highs) and rising(lows)`; `SHORT` iff strictly falling; else
  `NEUTRAL` ⇒ **returns nothing** (lines 57-58, 80-91).
- `with_ = highs[-1]` (up) / `lows[-1]` (down); `against` = the opposite last swing.
- **CHoCH wins** (line 66): `close < mid(against)` (up-trend) / `> mid(against)`
  (down-trend) ⇒ `CHOCH`, dir reversed, strength `0.8` if a level was `SWEPT`
  within `trap_window=6` candles else `0.5`, ttl 24.
- **BOS** (line 70): `close > mid(with_)` (up) / `< mid(with_)` (down) ⇒ `BOS`,
  dir = trend, strength `0.6`, ttl 12; the break is pushed to `_pending` for
  fake-BOS tracking.
- Swing `zone = (extreme±tick)` (swings.py L76) ⇒ `_mid(zone) ≈ the exact swing
  high/low`. So the BOS/CHoCH **trigger price is the swing EXTREME**, and the
  emitted Evidence `zone = (mid−tick, mid+tick)` sits on that extreme.
- Dedup per `swing_id` (one BOS + one CHoCH per swing). Fake-BOS memory
  (`_update_fake`, L111-126): a pending break that closes back beyond its level
  within `fake_window=5` candles tags future evidence `fake_bos_recent` (it does
  **not** suppress emission). All memory clears on session change.
- Defaults: `{tf:5m, trend_swings:4, trap_window:6, fake_window:5}`.

**HOW / WHEN it fires (measured).** On the 5m-native tape the detector fires
**correctly but very often**: in the single HAVELLS 2026-07-07 session it emitted
**8** BOS/CHoCH events where the user drew **1** BOS box; DABUR 2026-07 fired a
BOS/CHoCH roughly every 3-6 bars. The *level* geometry is excellent — the nearest
fractal swing to a user BOS line was within **0.02-0.21 %** in 9 of 10 checked
levels (0.1-0.9 pt) — but *which* break is emitted and *when* is driven by the
last-swing + monotonic-trend logic, which diverges from the user's chosen anchor.

**CONFLUENCE.** `structure` is a confirmation node: BOS = continuation evidence
(trend side), CHoCH = reversal evidence (counter-trend), CHoCH gets a strength
bump only when a sweep (`LevelState.SWEPT`) happened in the last 6 candles — the
one place the taught **sweep→BOS birth order** is even partially wired. It is
meant to be stacked under the order-block / propulsion entry detectors, which own
the CE-entry and outer-wick-SL geometry (doc35 gaps #2/#3 are **not** this
detector's job — structure never proposes an entry or stop).

## How the user draws it

The user draws BOS/CHoCH as a **horizontal line or thin box at the exact prior
swing high/low that price closed through** — the structural "shelf" (e.g. 1243,
1176, 1190, 766, 3475, 815, 1882). Recurring patterns in the 61 marks:
- **BOS = break of the last structural swing in the trend direction** (39 marks
  labelled `BOS`/`bos`), drawn as the broken level, no entry/SL attached (57/61
  have `entry=null, sl=null`).
- **Nested internal + major BOS** on one chart (T13: internal 1190 + major 1165;
  t6: upper 1323 + lower 1312) — the user distinguishes *internal* vs *major*
  structure; the detector has only one BOS/CHoCH tier.
- **CHoCH is range-position aware** (schematic c29): "Bullish CHoCH in **premium**
  = false; in **discount** = higher-probability" — a validity gate on top of the
  raw break.
- **Diagonal trendlines and swing-sequence zig-zags** (t6a_3, t6b_3, t32a) and a
  **standing range-high resistance** (t32b, ~1900) are all filed under
  `structure_bos_choch` for lack of a trendline/level vocabulary — the user's
  "structure" is broader than horizontal BOS/CHoCH.
- Schematics also teach **mSS / MSS / failure-to-swing / break-vs-no-break**
  (c31, c32, c33, c34) — a finer market-structure grammar than BOS/CHoCH binary.

## Accuracy verdict

**pct_match = 50.0 %** = hit / (hit+partial+miss) = **8 / 16** (uncheckable
excluded from the denominator per the brief).

| verdict | n | of 61 |
|---|---|---|
| hit | 8 | 13 % |
| partial | 4 | 7 % |
| miss | 4 | 7 % |
| uncheckable | 45 | 74 % |

**Per-stock breakdown**

| stock | hit | partial | miss | uncheckable | note |
|---|---|---|---|---|---|
| HAVELLS | 5 | 0 | 2 | 21 | 5 hit = the one 5m-native t1 BOS box (×5 views); 2 miss = diagonal trendlines; 21 unchk = daily-only 2022/23 + 1h/circular-year t6 + 1840/1885 anomalies |
| DABUR | 1 | 2 | 0 | 0 | all 5m-native, fully checked |
| DLF | 0 | 1 | 0 | 0 | 1h proxy of 5m |
| TITAN | 0 | 0 | 0 | 2 | 5m mark, 1h-only, silent proxy |
| SBICARD | 2 | 1 | 0 | 0 | 1h proxy of 15m |
| SBILIFE | 0 | 0 | 2 | 2 | 2 miss = trendlines + standing 1900; 2 unchk = t31 30m on daily (level real, event not) |
| (schematic/foreign) | 0 | 0 | 0 | 20 | no NSE tape/axis |

**Structural gaps (definitive, data-independent)**
1. **Wrong swing source.** `structure.detect()` L48 grades against `SWING_H/
   SWING_L` (fractal 2N+1) — but the taught anchor is **EXT** (percent-leg zigzag,
   `extremes.py`; commit 8dc7cc8 / doc35: "extremes are the taught anchor, not
   fractal furniture"). Fractal 3-bar swings are why the detector over-fires 8:1
   and latches minor pivots the user never marks.
2. **Trend gate too strict** (`_trend`, L80-91). *Strict* monotonic 4-swing
   (`all rising` AND `all rising`) returns `NEUTRAL` on any single pullback ⇒ the
   whole detector goes silent. Measured: TITAN t23 1h **silent** in-window;
   HAVELLS t6 emitted the **opposite**-direction BOS. Real BOS = break of the last
   confirmed extreme once trend is set by *one* HH+HL, not four monotonic swings.
3. **No internal/major tier** (T13, t6, t30b_2, schematic b8d2_c11 minor-CH) — one
   flat BOS/CHoCH; the user nests internal-vs-major.
4. **No premium/discount validity gate on CHoCH** (c29): CHoCH fires at any break;
   the taught rule voids premium-CHoCH longs / discount-CHoCH shorts.
5. **Diagonal + standing-level features unmodeled** (t6a_3, t6b_3, t32a, t32b — the
   4 misses): a horizontal-break detector cannot draw a trendline or emit a
   non-broken resistance.
6. **mSS / failure-to-swing / break-vs-no-break unmodeled** (c31_2, c32_1, c32_2).
7. **Sweep→BOS birth only half-wired**: `_swept_recently` gates CHoCH *strength*
   only (L67); BOS emits with no sweep precondition, so it fires "mid-air".

**Numeric gaps (values seen in tape)**
- Level fidelity is **high**: nearest fractal swing to the user line — HAVELLS
  1212→**1211.3 (0.7pt/0.06%)**, DABUR 445.5→**445.6 (0.02%)**, DABUR 422→**421.85
  (0.04%)**, DLF 766→**765.65 (0.05%)**, SBICARD 815→**815.9 (0.11%)**, TITAN
  3475→3481.7 (0.19%, but a HIGH not the marked low). So *swing extreme == user's
  BOS line* holds to ~1 tick.
- **Which break fires diverges**: DABUR 437.5 — swing present (438.3, 0.8pt) but
  **0 BOS emitted** through it; DABUR 422 — BOS-long fired on the next-higher swing
  **428.3 (6.3pt away)**; DLF 766 — BOS-short fired on the lower swing **759.55
  (6.45pt)**; SBICARD internal 810 — swing present (0.65pt) but **0 BOS**. Root:
  structure only ever breaks the **last** same-side swing, so intermediate/internal
  levels the user marks are skipped.
- **Over-fire**: 8 events vs 1 mark in the HAVELLS 2026-07-07 session (a
  significance/rank gate is absent).

**Data limits (why 45 are uncheckable)**
- Native 5m exists only <60d (`long5m` + Yahoo since 2026-05-04). The 2022/23
  HAVELLS legs (T10-T16b, T13) and 2020/24 SBILIFE are **daily-only** — a 5m/30m
  intraday BOS cannot be reproduced at daily resolution; years are era-approx
  (circular `cand_years`). *(t31 SBILIFE 1882 is the exception: level **confirmed**
  in the firm-2024 daily tape — open 2024-09-23 = 1882.0 — but the 30m break itself
  is not daily-reproducible.)*
- **Price-scale anomalies**: HAVELLS T3a/b (1840) and T5a (1885) sit far outside the
  resolved HAVELLS 2026 range **1124-1234** (1h) — no matching candles.
- 5m marks with only 1h tape (TITAN t23, HAVELLS t6): the 5m fractals that would
  trigger the BOS are invisible on 1h — the coarse proxy was silent/opposite, so
  the native-TF behaviour is inconclusive.
- **20 schematic/foreign** graphics (b8d2_*, c29-c34) have no price axis / are
  EURUSD — concept-checkable only, not numerically.

## Enhancement plan

Prioritized. References are to exact params/functions in
`app/trader/detectors/structure.py` unless noted.

**P1 — structural: swap the anchor to EXT (biggest lever).** In `detect()` L47-49
grade against `EXT_H/EXT_L` (from `extremes.py`, the taught percent-leg zigzag)
first, falling back to `SWING_H/SWING_L` only when no EXT exists — mirror
`ob_taught`'s EXT-first pattern (commit 8dc7cc8). Expected: kills the 8:1
over-fire and makes the emitted break coincide with the user's major shelf. Keep
`_mid(zone)` on the EXT wick-band mid (its band already = wick-beyond-bodies).

**P2 — structural: replace the monotonic-4 trend gate.** Rewrite `_trend`
(L80-91) from "strictly rising 4 swings" to the SMC definition: trend flips `LONG`
on the first `HH & HL` (close beyond the last confirmed EXT_H after a higher EXT_L)
and stays until a `CHoCH`. TARGET: eliminate the `NEUTRAL`-silence that made TITAN
t23 emit nothing and HAVELLS t6 emit the opposite side. If a monotonic form is
kept, allow a tolerance (e.g. a pullback that holds ≥ 50 % of the prior leg does
not break the trend) and reduce `trend_swings` 4→2.

**P3 — numeric: significance / rank gate on emission.** Only emit BOS/CHoCH when
the broken swing's `meta["rank_atr"]` (already computed by `extremes.py`, L235) is
≥ a threshold — TARGET `rank_atr ≥ 1.0` (leg ≥ 1×ATR) for a "major" BOS, a lower
tier for "internal". This directly cuts the 8-events-vs-1-mark over-fire and
supplies the internal/major distinction (P4).

**P4 — structural: internal vs major tier.** Emit two strengths — `event:"BOS"`
(major, EXT-anchored) and `event:"iBOS"` (internal, SWING-anchored, lower strength)
— so nested marks (T13 1190/1165, t6 1323/1312, t30b_2 810) both reproduce.

**P5 — birth-gate/confluence: enforce sweep→BOS for BOS, not just CHoCH.** Extend
`_swept_recently` (L105-109) to BOS: emit `meta["swept_before"]=True/False` and
optionally require a `SWEPT` level within `trap_window` for full strength — encodes
the taught birth order (sweep liquidity → BOS confirm) instead of firing mid-air.

**P6 — confluence: premium/discount gate on CHoCH** (c29). Given the active
dealing range (EXT_H..EXT_L), void a bullish CHoCH formed in the premium half /
bearish CHoCH in discount, or down-weight strength (0.8→0.4). Reuse the
`premium_discount` tool's range midpoint.

**P7 — scope-out the unmodeled features.** Diagonal trendlines (t6a_3, t6b_3,
t32a) and standing range-high resistance (t32b) are **not** BOS/CHoCH — route them
to a future `trendline` detector / to `extremes`+`liquidity` respectively, and
stop filing them under `structure` so the recognition denominator is honest. mSS /
failure-to-swing (c32) remain out of scope until an internal-structure grammar
(P4) exists.

**Non-goal (guardrail).** Do **not** add entry/SL to `structure` — CE-entry and
outer-wick-SL (doc35 #2/#3) belong to the order-block/propulsion entry detectors.
`structure` stays an evidence node; its job is *recognising the break*, which P1-P2
fix, not proposing a trade.
