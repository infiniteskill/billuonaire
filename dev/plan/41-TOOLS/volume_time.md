# volume_time

Bundle of two shipped detectors — `app/trader/detectors/volume.py` (VSA) and
`app/trader/detectors/timestats.py` (intraday time-of-day danger). Validated against
**all 3** hand-marked `volume_time` instances in `runs/validate/tools/registry.jsonl`
(t9b, t9c on HAVELLS; c28 a reference schematic). Verdict up front: the bundle name
promises "volume + time" but **matches 0 of the marks** — the marks are OB *maturity*
measurements and a *killzone* line, objects neither detector codes.

## Feature notes (structure & validity)

### What the code actually does

**`volume` (VSA booster)** — params `{tf:"5m", sma:20, z_hi:1.5}`.
- Classifies the **latest closed candle** (first match wins):
  - `climax`  : `range > 2*ATR` **and** `vol > 2*sma`
  - `stopping_volume` : bearish, `vol > 1.5*sma`, `lower_wick >= range/2`
  - `no_demand` : bullish, `vol < 0.7*sma`
  - `absorption` : `z = (vol-sma)/pstdev > z_hi(1.5)` and `body < 0.3*ATR`
- Emits **one** confirming Evidence (strength **0.3**, ttl **6**) **only** when another
  detector's evidence in `ctx.evidence_history` overlaps the candle's `(low,high)` within
  the last 6 closed candles (nearest ts wins). Direction/zone are **copied** from that
  evidence. It is a *pure booster* — never speaks alone (`_colocated()` returns `None` -> `[]`).
- Geometry it targets: **one candle's volume vs its own 20-bar SMA/stddev + range/wick/body
  vs ATR**. No box, no multi-bar span.
- Birth/death/retest: none. It re-classifies each new closed candle; ttl 6; dedup by `ts`.

**`timestats` (time-of-day danger)** — params `{bucket_min:5, prior_weight:20, path:None}`.
- `bucket = (minutes since session open) // 5`. NSE prior table `_NSE_TABLE`
  `[(75,0.8),(105,0.5),(225,0.3),(285,0.6),(None,0.8)]` — first ~75min and last ~90min are
  "dangerous" (0.8). Only applies when `session_minutes == 375`; else flat 0.5.
- `danger = (prior*20 + sweeps)/(20 + total)` (Laplace blend of prior with learned per-symbol
  sweep counts). Emits **one NEUTRAL Evidence per new M5 candle**, strength `1 - danger`,
  ttl **1**, zone = that candle's `(low,high)`.
- Geometry it targets: **the clock only** (minutes since open). No price geometry, no box.

### What the marks actually are
- **t9b / t9c (`maturity-bars-percent`)** — Kite rectangle-tool readout on the **outer OB**:
  tooltip `6.46 (-0.48%) 89 Bars`. i.e. a box **89 5m-bars wide** (~1.19 NSE sessions) and
  **6.46 pt = 0.48% tall**. This is a **maturity + compression** measurement of a distribution
  zone before a HAVELLS short (entry ~1330, Aug-2023). t9c is the same tooltip on the same box
  one screenshot later (a duplicate).
- **c28 (`time-of-delivery marker`)** — a green vertical dashed line labelled `TIME` on a
  reference/teaching schematic: the *time component* (killzone) that gates price delivery.

### CONFLUENCE
The user's "time" is **not** the clock-of-day that `timestats` models — it is **zone age /
bars-span** (t9b/t9c) or a **killzone delivery gate** (c28). The user's marks carry **no volume
readout at all** (the "-0.48% / 89 Bars" is price-height and bar-count from the rectangle tool,
not volume). So `volume` (VSA) is orthogonal to every mark, and `timestats` is a soft danger
prior, not a maturity meter and not a hard killzone gate. The confluence the marks imply — a
**tight, mature OB** (few points tall, many bars wide) sitting at a **specific delivery time** —
is exactly the pair of objects the bundle is missing.

## How the user draws it
1. Marks the **outer order block** (the distribution/accumulation zone before the move).
2. Drops Kite's **rectangle measurement** over it and reads the tooltip: `<pts> (<pct%>) <N> Bars`
   — here `6.46 (-0.48%) 89 Bars`. The **tightness** (small % height) + **duration** (large bar
   count) is the signal: a long, compressed zone = a *mature, well-formed* OB worth trading.
3. Separately (c28 schematic) draws a **vertical TIME line** marking the killzone/session window
   in which the delivery is expected — a time gate layered on top of the price zone.

## Accuracy verdict

**pct_match = 0/2 = 0.0%** over the checkable instances (hit + partial + miss; uncheckable
excluded).

| verdict | count | instances |
|---|---|---|
| hit | 0 | — |
| partial | 0 | — |
| miss | 2 | t9b, t9c (HAVELLS maturity boxes) |
| uncheckable | 1 | c28 (reference schematic, no tape) |

Per-stock breakdown:
- **HAVELLS** (t9b, t9c): 0 hit / 0 partial / **2 miss**. Both are OB maturity annotations
  (`6.46 / -0.48% / 89 Bars`). Neither `volume` nor `timestats` emits a box, a bars-width, or a
  %-height, so neither can reproduce the mark. Structural miss, determinable without tape.
- **reference** (c28): **uncheckable** — no symbol/tf/axis; `TIME` killzone line. `timestats` is
  the nearest concept but is a per-bucket danger score, not a delivery gate; nothing to test.

Structural gaps:
- **No maturity/box-geometry detector in the bundle.** The single object the user draws
  (bars-span x %-height of an OB) has **no code path** anywhere in `volume.py` / `timestats.py`
  (`grep -iE 'matur|bars|age|width|span|percent|height|kill|deliver'` -> NONE).
- **`timestats` models the wrong "time."** It scores minutes-since-open danger; the user's time
  is (a) zone *age* in bars and (b) a *killzone* gate. Different axis entirely.
- **`volume` is a colocated booster.** Even for a genuine VSA candle it emits nothing unless
  another detector already fired on the same `(low,high)` within 6 bars — so it can never
  originate the maturity mark, only decorate an existing one.

NUMERIC gaps (values seen in data):
- Tooltip height `6.46 pt = 0.48%` reconciles with the tape: `0.48% * 1330 = 6.38 pt` (~1330 is
  the HAVELLS Aug-2023 short entry). Bars: `89 * 5min = 445min = 1.19 NSE sessions`. **The
  detector emits none of these numbers.**
- HAVELLS daily around the resolved date (`data/yahoo/HAVELLS_1d.csv`) confirms the price era:
  2023-08-07 O/H/L/C 1319.9/1323.4/1312.0/1319.9; the short drawn 08/08 fell to a 1262.9 low by
  08/16 (~5% down) — context consistent with `H_aug_short` (mfe 7.3%, target hit 08/13). Era
  confirmed; the **5m maturity box itself is not measurable** (no 5m tape for 2023).

Data limits:
- **No 5m tape before 2026** — `data/yahoo/HAVELLS_5m.csv` starts 2026-05-25,
  `data/long5m/HAVELLS.csv` starts 2026-04-27. t9b/t9c live on 2023-08 5m, so the exact
  `89-bar / 6.46pt` box **cannot** be numerically reconstructed; only daily context exists.
- Year is a **price-era guess** (per RETHINK: only t31 SBILIFE is firmly dated). Dates approximate.
- c28 is a **reference/educational graphic** — no NSE tape, no axis; permanently uncheckable.
- Verdict scope = **RECOGNITION only** (does the bundle reproduce the drawn object). No
  profitability/EDGE claim is made or implied.

## Enhancement plan

Priority 1 — **STRUCTURAL: add a `maturity` (OB compression) measure** (the missing t9b/t9c object).
- New detector (or a field on the OB emitters `ob_taught` / `orderblock`) computing, per zone:
  `bars_wide = (zone_end_ts - zone_start_ts)/tf_minutes` and
  `height_pct = (zone_hi - zone_lo)/zone_mid * 100` (and `height_atr = height/ATR`).
- Emit as meta on the zone Evidence: `{"bars": N, "height_pct": p, "height_atr": h}` so downstream
  gates can read it. Target the user's observed regime: **tight** `height_pct <= ~0.5%` and
  **long** `bars >= ~80` (t9b: 0.48% / 89 bars). Treat these as the initial thresholds to sweep,
  not fixed law.
- This is the object the user actually draws; without it `volume_time` is 0% on its own marks.

Priority 2 — **BIRTH-GATE / CONFLUENCE: gate the OB on maturity**.
- Only promote an OB to tradable when `bars >= bars_min` AND `height_pct <= pct_max` (mature +
  compressed). Wire this as a confluence flag alongside the existing sweep+BOS birth gate
  (doc35), not as a standalone signal.

Priority 3 — **TIME axis: separate "zone age" from "time-of-day"; add a killzone gate (c28)**.
- Keep `timestats` as-is for intraday danger, but add an explicit **killzone/session-window
  gate** (the `TIME` line): a boolean per candle for whether `ctx.now` falls in a configured
  delivery window (e.g. NSE 09:45-10:55, 13:10-15:10 clusters noted in RETHINK §C). This is the
  hard gate the schematic implies; `timestats.prior/_NSE_TABLE` is only a soft danger score.
- Do **not** conflate this with the Priority-1 maturity (age-in-bars) — they are different axes.

Priority 4 — **numeric thresholds to tune** (reference exact params):
- `volume.py` `_DEFAULTS {sma:20, z_hi:1.5}` and the class thresholds (`2*ATR`/`2*sma` climax,
  `1.5*sma` stopping, `0.7*sma` no_demand, `0.3*ATR` absorption body): unchanged by this
  validation (no volume mark to calibrate against) — leave frozen until a real VSA hand-mark
  exists.
- `timestats.py` `_NSE_TABLE` / `bucket_min:5` / `prior_weight:20`: unchanged; add the killzone
  window as new params rather than re-tuning the danger table.
- New maturity params (TARGET starting values from the one dimensioned mark): `bars_min ~= 80`,
  `height_pct_max ~= 0.5%`. Sweep once 5m tape exists for the marked trades (currently blocked by
  the no-5m-before-2026 data limit).
