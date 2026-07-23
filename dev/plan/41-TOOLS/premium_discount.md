# premium_discount

Status: **GAP — no detector exists.** `grep -rniE "premium|discount|equilibrium|dealing.?range"
app/trader/detectors/` returns nothing but the unrelated `breaker_msb` fib token. This doc specs
what SHOULD exist and validates the spec against EVERY hand-marked `premium_discount` instance
(8 total) in `runs/validate/tools/registry.jsonl`.

Guardrail (RETHINK.md): RECOGNITION (fires on the right price band) != EDGE. Nothing here claims
profitability — RETHINK B5 already flags the premium/discount tag as **fragile** (a fixed 40-bar
window put 5 trades on the WRONG side of the user's own rule). The two marks that validate below
are HTF, deep-extreme bands where the classification is robust; that robustness does NOT extend to
a fixed-window LTF gate.

## Feature notes (structure & validity)

**Candle / price geometry.** Premium/discount is not a candle pattern — it is a *positional
classification* of price inside a **dealing range**:

- Take a dealing range from a confirmed swing HIGH (`EXT_H`) down to a confirmed swing LOW
  (`EXT_L`). Range `[L, H]`, size `= H - L`.
- **Equilibrium (EQ) = 0.5 midpoint** `= (L + H) / 2`. Drawn as the 50% fib.
- **Premium = upper half** `[EQ, H]` (fraction 0.5..1.0) — "expensive", the SELL side.
- **Discount = lower half** `[L, EQ]` (fraction 0.0..0.5) — "cheap", the BUY side.
- **OTE (optimal-trade-entry) sub-bands**: deep discount `0.62..0.79` below EQ for longs; deep
  premium `0.21..0.38` (mirror) above EQ for shorts. (c29/c30 schematics teach the 0.5 split;
  OTE is the standard ICT deepening.)

**HOW / WHEN it "fires".** Unlike an OB/FVG this is a *persistent context gate*, not a one-candle
event. It should emit a live band pair (or write `range_pos` = fraction 0..1 into the tick meta)
that other detectors read: **gate longs to price in discount, shorts to price in premium.** It is
re-derived every tick from the current master dealing range and dies/reshapes when a new master
`EXT_H`/`EXT_L` prints.

**CONFLUENCE.** Premium/discount is a *filter over* the entry detectors, never a standalone entry:
the user's own thesis (t32a text) is "revisit swing -> FVG/OB response -> take liquidity -> next OB
-> reverse from **premium/distribution**." I.e. OB (`ob_taught`) / FVG (`fvg_n`) supply the entry
zone; premium/discount + Wyckoff phase (accumulation=discount, distribution=premium) supply the
directional permission. It also overlaps the fib-extension tool (T3a) used the other way — as a
premium *target/reference* projected beyond 100%.

## How the user draws it

Three distinct hand-draw dialects appear in the marks:

1. **Wyckoff range split (the real trade — t32b, SBILIFE 4h).** A big multi-year shaded band at the
   accumulation LOW labelled `DISCOUNT` (+ "ACCUMULATION PHASE / WYCKOFF") and a shaded band at the
   distribution HIGH labelled `DISTRIBUTION PHASE ,, PREMIUM`, with a red horizontal reference line
   near the top. No explicit 50% line is drawn — the halves are read by eye off the range extremes.
2. **Concept annotation (t32a, SBILIFE 30m).** No box at all — a red paragraph stating the method,
   ending "...it might reverse in future from there after reaching to **premium or say
   distribution zone**." Premium/discount named in prose only.
3. **Fib-extension as premium reference (T3a, HAVELLS 30m).** The fibonacci-*extension* tool
   (100% / 138.2% / 161.8% at ~1490 / 1790 / 1930) used as an upside premium/target scaffold —
   projection ABOVE the range, not the internal 0-100% split.
4. **Educational schematics (c27-c30).** ICT teaching diagrams: EQ dashed at 50%, Premium(expensive)
   above / Discount(cheap) below; percent axes, no NSE instrument.

## Accuracy verdict

**pct_match = 2 / 2 = 100%** (hit / (hit+partial+miss); uncheckable excluded from denominator).

| verdict | count | instances |
|---|---|---|
| hit | 2 | t32b_premium_discount_1, t32b_premium_discount_2 |
| partial | 0 | — |
| miss | 0 | — |
| uncheckable | 6 | T3a, t32a, c27, c28, c29, c30 |

The 100% is over a **tiny denominator (2)** and means only that both numerically-anchored zone
marks land on the correct side of EQ — recognition, not edge. Six of eight marks carry no scorable
NSE geometry (logged, not dropped).

**Per-stock breakdown**
- **SBILIFE (3 marks, daily proxy for 4h/30m):**
  - `t32b_1 DISCOUNT 1300-1500` -> **hit**. Dealing range on `SBILIFE_1d`: `EXT_L 1307.7`
    (2024-06-04) .. `EXT_H 2086.6` (2025-11-24), size 778.9, **EQ 1697.2**. Box occupies range
    fraction **-0.01 .. 0.247** (center 0.12) — wholly in the discount half, 197 pts below EQ.
  - `t32b_2 PREMIUM 1980-2080` -> **hit**. Same range. Box fraction **0.863 .. 0.992** (center
    0.93) — wholly premium, above even the 0.79 OTE (=1923); box-bottom 283 pts above EQ.
  - `t32a` concept text -> **uncheckable** (no box, prose only; daily-only 2020-21 era).
- **HAVELLS (1 mark):** `T3a` fib-extension -> **uncheckable**. Levels 1490/1790/1930 are all real
  HAVELLS touches but in **2024** (May-Oct; 2024 H 2106 / L 1280), NOT the label-resolved **2026**
  tape (~1200) — the registry's flagged "price-scale anomaly." Extension >100% has no EQ split to
  score against a range-split detector.
- **Reference (4 marks, c27-c30):** all **uncheckable** — foreign/educational, no NSE symbol/tf/axis.

**Structural gaps**
- **No detector at all** (the headline gap). The concept is currently unavailable to the pipeline.
- **Sub-type coverage.** A range-split (0-100%) detector will NOT reproduce T3a's fib-*extension*
  premium projection (100/138.2/161.8 above the range) — a distinct geometry family.
- **Birth model divergence.** The user's real marks (t32b) are born from **Wyckoff phase extremes**
  (accumulation low / distribution high), not a sweep+BOS. The range must be anchored on confirmed
  **master** `EXT_H`/`EXT_L` (extremes.py `masters` set), not a rolling fixed window.

**Numeric gaps (values seen in data)**
- SBILIFE EQ = **1697.2**; both boxes clear EQ by **197 pts (discount)** and **283 pts (premium)** —
  i.e. neither sits within ~0.25 of the 0.5 cutoff, so both are robust to the swing-pair choice.
  Contrast RETHINK B5's fragile trades that sat "within 0.06 of a cutoff" on a fixed 40-bar window —
  those flip; these do not.
- HAVELLS numeric gap = the **616-pt / ~50% price-scale mismatch** between the drawn fib (1490-1930)
  and the resolved-2026 tape (~1200) — unresolvable without the true era.

**Data limits**
- SBILIFE has **daily only** (no 4h/30m cache) — the EQ split is validated on the daily proxy; the
  bands are HTF so the daily range is a faithful stand-in, but the exact 4h swing pivots are
  unverifiable.
- Only t31 SBILIFE has a firm year; t32b_1's `2024-09-23` is an era-approx match to `SL_t31_short`
  and t32b_2's `2026` is label-year — dates approximate (RETHINK: year is a price-era guess for all
  but t31).
- c27-c30 have no NSE tape; T3a's 5m native is <60d and post-dates the drawn (2024) levels.

## Enhancement plan

Prioritized. References real symbols/params.

**P1 — Structural: build the detector `premium_discount` (new file
`app/trader/detectors/premium_discount.py`).**
- Consume `ctx.levels` `EXT_H`/`EXT_L` from `extremes.py` (it already tags a `master` in `meta`).
  Dealing range = `[master EXT_L.price, master EXT_H.price]` on the configured HTF (default `1h`,
  matching `extremes._DEFAULT_TIMEFRAMES`; add `4h`/`1d` for positional marks like t32b).
- Compute `EQ = (L+H)/2`; `range_pos(price) = (price - L)/(H - L)`.
- Emit as a **context gate**, not Evidence: write `ctx` tick meta `range_pos`, `zone in
  {premium, discount, eq}`, plus optional `Level`s `PREMIUM`/`DISCOUNT` (add two `LevelKind`
  members mirroring `EXT_H/EXT_L`) with `zone=[EQ,H]` / `[L,EQ]`, `born = later of the two pivot
  bars`, dying when either master pivot is replaced (reuse extremes' DEAD-on-vanish pattern).
- Follow `base.Detector` (`name="premium_discount"`, register, `requires=frozenset()`); list it
  AFTER `extremes` in `settings.detectors.enabled` so the pivots exist when it runs.

**P2 — Numeric thresholds (TARGET values).**
- `eq = 0.5` (fixed by definition). Gate: **long only if `range_pos <= 0.5`, short only if
  `range_pos >= 0.5`.** Validated: both SBILIFE marks satisfy this by a wide margin (0.12 long-side,
  0.93 short-side).
- `ote_lo = 0.62`, `ote_hi = 0.79` deep-discount band (mirror `0.21`/`0.38` for premium); a
  "strong" flag when `range_pos` is inside OTE. t32b_2's premium box (0.86-0.99) is beyond OTE —
  keep the band as a preference, not a hard cut.
- **Anti-fragility guard (addresses RETHINK B5):** require the range to come from a **confirmed
  master** `EXT` pair (leg_pct 6.0 frozen) — NOT a fixed 40/`N`-bar window. Add a param
  `min_range_atr` (default ~8-10x ATR at the pivot) so tiny ranges (where a 0.06 wobble flips the
  side) don't emit a gate. Log `range_pos` distance-to-0.5 in meta so downstream can drop
  within-`eq_deadband` (default 0.10) calls as "no signal."

**P3 — Birth-gate / confluence.**
- Do not fire standalone. Surface `range_pos`/`zone` for consumers: gate `ob_taught` / `fvg_n`
  entries by side (short OB valid only if its zone center is premium; long OB only if discount),
  encoding the user's t32a thesis (accumulation->discount long / distribution->premium short).
- Optional confluence with `wyckoff.py` PHASE: discount∩accumulation and premium∩distribution
  raise a `wyckoff_pd_align` flag (this is the t32b geometry exactly).

**P4 — Sub-type: fib-extension premium projection (covers T3a).**
- Add mode `extension` that projects `100/138.2/161.8%` ABOVE (or below) the last impulse leg as
  premium *targets/reference*, distinct from the internal split. Reuse the leg from the same
  `EXT` pivots; emit target `Level`s rather than a gate. Guard against the T3a price-scale anomaly
  by binding the projection to the resolved-era tape, not the drawn label.

**Non-goals / honesty (RETHINK).** This detector improves RECOGNITION and gives a clean side-gate;
it is NOT an edge. It must be measured as a *filter* (does gating OB/FVG by side change net-R on
CONSTRUCTED losers, 4-way holdout) before any profitability claim. The measured null never tested
the user's outer-wick-SL / far-liquidity-target engine, so nothing here is falsified — but nothing
here is proven either.
