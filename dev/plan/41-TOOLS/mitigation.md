# mitigation

Validation of the `mitigation` feature against **EVERY** hand-marked instance in
`runs/validate/tools/registry.jsonl` (feature == "mitigation") — **16 instances**,
no sample. Two detectors carry this object and are graded as one family:
`app/trader/detectors/mitigation.py` (the ICT displacement-origin block — the
named detector, run at 5m) and `app/trader/detectors/ob_taught.py` (the taught OB
whose lifecycle FLIPS to a `MIT` zone on a deep break that never swept — the
schematic-faithful "No Break" mitigation). Numeric checks run on
`data/yahoo/HAVELLS_5m.csv` and `TITAN_5m.csv` (Yahoo 5m from 2026-05-25 → the
Jun/Jul 2026 windows are in-window), `data/yahoo/DLF_1h.csv` (1h back to
2024-07 → the Aug-2025 DLF era), and `HAVELLS_1d.csv` (daily, for the 2022 mark).

Guardrail (RETHINK.md): **RECOGNITION (fires on the right candle) != EDGE.** The
already-measured record is flat/negative for the LTF retest surface and that null
tested a MIS-BUILT proxy (body-edge SL, ATR stop). Nothing below claims
profitability — this is a geometry/recognition audit of the USER's drawn
mitigation block only. Dates are era-approximate for every mark except t31; the
`H_jul_short`/`H_jun_long` "resolved" dates are circular-year guesses and, as the
numeric work below shows, several are **off by weeks** (the geometry still lives
in-tape, just on a different day).

## Feature notes (structure & validity)

**The taught mitigation block (from the marks + the reference schematics).** An
**unmitigated order block** — the last opposite-colour candle a displacement leg
leaves behind — that price returns to *without breaking the prior structure*, taps
to fill the resting orders, and continues. The one gate that separates it from a
**breaker** is explicit in `c31_mitigation_1`: a mitigation block is retested with
**"No Break"** of the prior swing; a breaker requires the opposing **"Break"**.
`c32` shows the bearish case on real candles (a down-candle OB before swing-high
B, retested on the B-C rally *without breaking*, then markdown); `b8d2_c04` shows
the gap-fill leg ("Price Returns to Fill the Gap" = high-probability retracement
entry).

**Two codebase definitions — they are NOT the same object:**

**(1) `mitigation.py` — the ICT displacement-origin block (the named detector).**
Faithful port of `ict_pieces.py::mitigation_block`.
- **Geometry**: the last opposite-colour candle immediately before a displacement
  leg, with **no intervening opposite candle** across `lookback` bars, whose net
  displacement `≥ disp_atr·ATR`. The candidate is `window[-(lookback+1)]` on a
  `last(lookback+2)` window — so it is confirmed `lookback` bars *after* it forms.
- **Zone = BODY only** `(min(O,C), max(O,C))` — differs from `orderblock`'s full
  range. **Direction = displacement direction**: down-candle → up-move = **LONG**;
  up-candle → down-move = **SHORT**.
- **Birth is MID-AIR**: any 1·ATR/3-bar displacement qualifies. There is **no
  sweep gate, no BOS gate, and no No-Break test** — this is the key divergence
  from the taught object and from `ob_taught`.
- **Retest** = first later closed candle whose *range overlaps* the body zone
  (`touch.low ≤ hi and touch.high ≥ lo`) → **proximal-edge** fill, not CE.
- **SL = OUTER WICK**: `min(blk.low, touch.low)` for LONG / `max(blk.high,
  touch.high)` for SHORT, floored at `sl_atr_floor·ATR`. The block's wick extreme
  is tracked in the `extreme` var. **This is the one place any detector emits the
  doc35 outer-wick stop** — but note it is used only for `sl`, never for the
  emitted *zone*.
- ATR is the block's **own-bar** ATR (`_atr_of(hist[:15])` = `ict_pieces` `atrs[i]`,
  not the current tick's). Pure signal-emitter, **no liquidity target**, ttl 6,
  strength = ramp of displacement excess over `disp_atr`.
- Defaults `{tf:5m, disp_atr:1.0, lookback:3, sl_atr_floor:0.15}`; `_collapse`
  dedups same-direction clashes per tick.

**(2) `ob_taught.py` — the OB→MIT flip (the schematic "No Break").** A bodies-box
OB is born at a continuation break with ≥1 counter-candle. On a **deep break**
(`≥ depth_atr(0.5)·ATR` close-through, `step_zone`) the box is KILLED and FLIPS:
if the birth leg's running extreme took the prior same-side extreme
(`meta["pex"]`, the `swept` test in `ObZones.step`) → `BRK`, **else → `MIT`**. The
flipped `MIT` zone (opposite dir, SAME bodies box, parent grade) emits on the
first armed retest from the other side. Entry = **edge**; **SL = far edge raw**
(`z.lo`/`z.hi`, i.e. BODY, not wick); `sl_floor=0.15·ATR`; strength 0.7, ttl 6.
**This is the faithful `c31`/`c32` No-Break definition** — but it carries the
doc35 body-edge SL, the opposite trade-off from `mitigation.py`.

**Confluence.** The user's mitigation blocks ride on: a prior **liquidity sweep**
(TITAN `t22` bottom 3990 = "the SSL sweep before reversal"; HAVELLS T15 "below the
1348 swing"), the **nested/refined OB** (`T20`, `t22` "darker inner box" inside
the big supply/demand OB), an **FVG** to fill (`T2a` "OB+FVG base", `b8d2_c04`),
and the parent `order_block`. The distinguishing feature vs `breaker` is the
absence of a structure break (`c31`).

## How the user draws it

A tight horizontal box at the unmitigated OB level, retest expected then continue:
- **HAVELLS (t1d–t1h, 5 redraws of one trade).** "RETEST FOR ENTRY" band
  ~**1219–1223.5** at the 8-Jul-2026 top; **short, entry 1221** (box **midpoint** =
  CE), SL **1224** (just above box), target ~1197. This is the *same* trade
  breaker.md grades as a breaker — sweep+BOS present — which is exactly why the
  pure mid-air mitigation detector mishandles it (below).
- **HAVELLS (T2a).** "OB+FVG entry", **long, entry 1141.02** (box top), **SL
  1133.07** (box bottom) — an 8pt demand base, no target marked.
- **HAVELLS (T4a/T4b).** "MITIGATION BLOCK", box **2065–2035**, short, entry 2050,
  SL 2075, target 1920 — flagged **price anomaly** in the registry.
- **HAVELLS (T15a/T15b).** "MITIGATION BLOCK / ENTRY", box **1335–1330**, short,
  entry 1332, SL implied above swing 1348, target 1228. T15b carries the user's
  own tooltip: **3.43 pt / −0.26% / 157 bars** — a 5m-scale object.
- **DLF (T20_1/T20_2).** "refined supply / mitigation block (nested)", inner box
  **782–776**, short, diagonal 21/08→01/09 "before the 26/08 drop".
- **TITAN (t22_1).** "refined demand / mitigation block (nested)", inner box
  **4030–3990**, long, bottom 3990 = the SSL sweep.
- **References (b8d2_c04, c31, c32).** Textbook schematics defining the object
  (gap-fill retrace; mitigation = No-Break vs breaker = Break; bearish example).

Entry ≈ box CE/midpoint (1221 on HAVELLS), SL **beyond the outer wick**, target at
far liquidity (never on the block itself).

## Accuracy verdict

**pct_match = hit / (hit + partial + miss) = 1 / 9 = 11.1%.**
Counts over ALL 16 instances: **hit 1, partial 8, miss 0, uncheckable 7.**

| stock | instances | verdict | note |
|---|---|---|---|
| HAVELLS | t1d,t1e,t1f,t1g,t1h | **5 partial** | 5m tape; short body floats above box + direction inversion inside box |
| HAVELLS | T2a | **1 hit** | 5m tape; long body inside base, outer-wick SL within 0.9pt, proximal entry |
| TITAN | t22_1 | **1 partial** | 5m tape; long body inside box but upper-half, sweep low not spanned |
| DLF | T20_1,T20_2 | **2 partial** | 1h proxy; block forms with SL=box-top EXACT but sliver never retested |
| HAVELLS | T4a,T4b | **2 uncheckable** | price anomaly — no HAVELLS tape at 2000–2100 |
| HAVELLS | T15a,T15b | **2 uncheckable** | 5m mark on daily-only 2022 tape |
| (reference) | b8d2_c04,c31,c32 | **3 uncheckable** | schematics, no NSE tape |

The **11.1%** is a full-reproduction rate; the real story is the **8 partials** —
the detector *recognises* the region and direction (or the SL anchor) but the
body-only geometry, the mid-air birth, and the edge entry each pull it off the
user's mark. Recognition is high, **selectivity is near-zero** (see over-production
below). This is a geometry audit only — none of it speaks to edge.

**T2a (HAVELLS Jun long) — the one clean reproduction.** ATR(5m,14) ≈ **2.07 pt**.
The "resolved" 2026-06-29 date is a circular-year artifact — the 1133–1141 base
actually printed **06-08…06-12** (06-29 barely tags 1140.5). On the real base the
detector forms LONG demand blocks INSIDE the box: **1136.9–1139.8** (06-08 14:20,
SL **1135.4**) and **1135.0–1136.0** (06-08 15:25, SL **1134.0**). Outer-wick SL
**1134.0 vs user 1133.07 = +0.93pt (0.45 ATR)**; entry is the proximal top-edge
~1139.8–1141 ≈ user **1141.02**; direction matches. All four dimensions align →
**hit**. Caveat: this block was one of **60 formed in 11 days on one symbol** — the
match is partly density, not selection.

**HAVELLS t1d–t1h (Jul short) — partial, and the sharpest diagnostic.** ATR(5m,14)
@08-Jul 11:25 = **2.94 pt**. The short supply blocks the detector forms sit at
**1225.5–1225.9** (SL 1226.8) and **1227.9–1231.6** (SL 1231.6) — i.e. **+2.4pt
(0.82 ATR) to +8pt ABOVE** the user's 1219–1223.5 box. Worse, **inside the exact
box the detector emits LONG** (bodies 1220.6–1221.7, 1221.0–1221.1) because the
local displacement there is *up* — a **direction inversion** vs the user's HTF
lower-high short. The outer-wick SL (1226.8) does match the user's 1224 within
0.95 ATR — the only faithful dimension. Root cause: **body-only excludes the lower
wick** (so the zone floats above the wick-inclusive box) and **mid-air birth reads
local direction** (so it inverts vs the sweep/BOS reading breaker.md confirms).

**TITAN t22_1 (Jun long) — partial.** ATR(5m,14) ≈ **12.24 pt**. LONG blocks form
inside the box: **4006.8–4012.0** (06-02 10:05, SL 4003.8) and **4026.1–4027.9**.
Direction and region match, SL is the outer wick. But the body sits in the
**upper half** — its floor is **+16.8pt (1.4 ATR) above the 3990 sweep low** that
anchors the user's 40pt box. The thin body (~5pt) cannot span the sweep-to-body
zone, and the **SSL sweep birth is not gated**.

**DLF T20 (Aug short) — partial, and the decisive body-only finding.** ATR(1h,14)
≈ **4.8 pt**. The supply block **does form** at the top: 08-21 11:15, body
**(779.0, 779.1)**, **extreme/SL = 782.0 = the user's box top EXACTLY**. But the
body is a **0.1pt sliver**; price ran straight down and only returned to 776–782 in
mid-September, so the sliver is **never retested → no signal**. The block that
*does* fire is 08-22's continuation block at **767.7–768.3**, **8–14pt (1.8–3.0
ATR) BELOW** the box. So the level and outer-wick SL are recognised, but the
body-only zone is too thin to catch the mitigation the user drew (a full 776–782
box would have armed). TF mismatch compounds it: a nested 5m block on 1h tape.

**Structural + NUMERIC gaps (doc35 residue, quantified):**
1. **Zone = body, not outer wick.** Numerically the body floats above the box on
   shorts (HAVELLS +2.4…8pt) and, worse, collapses to a **sliver** that valid
   retests miss (DLF 779.0–779.1, 0.1pt). The wick extreme is already computed
   (`extreme`) but only feeds `sl`, never the zone.
2. **Direction inversion (mid-air).** With no sweep/BOS anchor the detector labels
   the HAVELLS 1219–1223 zone LONG where the user reads SHORT — the mid-air rule
   can emit the **opposite trade** in the exact box.
3. **Entry edge, not CE.** User entries sit at the box **midpoint** (1221 = mid of
   1219–1223.5); the touch-overlap fills at the proximal edge. (T2a is the
   exception — a long whose proximal edge *is* the marked top.)
4. **SL is right (the lone win).** `mitigation.py`'s outer-wick SL matches the user
   within ≤1 ATR everywhere it fires (HAVELLS 1226.8 vs 1224; Jun 1134.0 vs
   1133.07; DLF extreme 782.0 exact). `ob_taught`'s MIT SL (body edge) does NOT.
5. **No No-Break gate in `mitigation.py`.** It fires on *any* displacement origin —
   it cannot make the `c31` mitigation-vs-breaker distinction (only `ob_taught`'s
   `swept`/`pex` flip does). It also **over-produces**: 60 blocks / 11 days / one
   symbol — recognition without selectivity.

**Data limits (why 7 are uncheckable).**
- **T4a/T4b** — box 2065–2035 has **no matching HAVELLS candle** (spot ~1209,
  adjusted all-time-high ~1830). Registry-flagged symbol/date anomaly → almost
  certainly a mislabeled/foreign symbol.
- **T15a/T15b** — a **5m** block (user dims 3.43pt / −0.26% / 157 bars) on
  **daily-only 2022** tape (1h only reaches 2024-07). A daily body-block = the
  27-Apr up-candle body ~**1313–1320**, ~**15pt below** the 1330–1335 wick box.
  The HTF structure IS present and recognition-positive: supply **1330–1344**
  (late Apr 2022) → markdown to **1193–1228** (05-05…05-09), matching the user's
  1228 target. The 5m block geometry itself is simply below daily resolution.
- **b8d2_c04, c31, c32** — foreign educational schematics, no symbol/tf/axis. They
  validate the *definition* (esp. `c31`: mitigation = OB retested **without** a
  break — the exact `ob_taught` MIT flip law).

No silent drops: every uncheckable is logged with its reason in
`runs/validate/tools/val_mitigation.jsonl`.

## Enhancement plan

Prioritized; references exact params/functions. Goal = make `mitigation.py`
reproduce the user's block (**wick-inclusive box** + **CE entry** + **No-Break/
direction-correct birth**) while keeping the one thing it already gets right (the
outer-wick SL). All changes A/B-gated — re-measure with the corrected geometry
before trusting any number (the measured null tested the mis-built proxy).

**P1 — Structural: emit a WICK-inclusive zone, not the body sliver.**
`mitigation.py` already tracks the wick `extreme`; extend the emitted zone to it.
In `_form`, store `zone_lo/zone_hi = min(lo, extreme) / max(hi, extreme)` (a
`zone_wick=True` param) so the box spans body→wick. TARGET: DLF becomes
**779.0–782.0** (not 779.0–779.1) → a 776–782 retest arms instead of sailing past;
HAVELLS short box reaches down toward 1223 wick instead of floating at 1225.9.
This directly fixes the sliver-never-retested miss and the +2.4…8pt body offset.

**P2 — Numeric threshold: CE (50%) entry option.** Add `entry_mode ∈ {edge, ce}`.
For `ce`, fire the touch at box mid `(lo+hi)/2` instead of range-overlap. TARGET:
HAVELLS (1219.4+1223.5)/2 = **1221.5 ≈ user 1221**; keep `edge` default for the
A/B. The user's entries sit at the midpoint on every numbered short.

**P3 — Birth-gate: add an optional sweep/No-Break gate to kill the inversion +
over-production.** The mid-air `_form` is what emits LONG inside a SHORT supply and
what produces 60 blocks/11d. Gate births on a **prior liquidity sweep** (reuse the
`extremes` EXT pivots / `inducement` signal): require the displacement leg to
originate *after* the block's side swept a resting extreme **without** closing
through the opposing structure (the `c31` "No Break"). This anchors direction to
the HTF read (HAVELLS 1219–1223 → SHORT) and drops the incidental mid-tape blocks.
Where a Break *did* occur, defer to `breaker`/`ob_taught` `BRK` — do not emit
mitigation (the `c31` split).

**P4 — Selectivity: raise `disp_atr` and/or require OB confluence.** Lift
`disp_atr` from **1.0 → 1.5–2.0** (TARGET: ≤ ~10 blocks / 11d / symbol) and/or only
emit when the body zone overlaps a live `ob_taught` OB or an EXT pivot. This trades
recall for the near-zero precision the density exposes.

**P5 — Port the No-Break test into `mitigation.py` (parity with `ob_taught` MIT).**
`mitigation.py` has **no** mitigation-vs-breaker test; `ob_taught` has the correct
one (`swept = ext > pex`). Either (a) seed `mitigation.py` births with the same
`pex` prior-extreme lookup and suppress births where the leg swept-and-broke, or
(b) route all No-Break mitigation through `ob_taught`'s MIT flip and give **that**
path the P1 wick zone + P2 CE entry + the outer-wick SL from `mitigation.py`
(replacing `ob_taught._evidence`'s body-edge `sl = z.lo/z.hi`). Option (b) unifies
the two definitions into one detector that carries the No-Break gate, the wick box,
CE entry, and the outer-wick SL — the full taught geometry.

**Data to unblock the 7 uncheckables.** Verify the T4 symbol (the 2065–2035 box is
not HAVELLS) and re-file it. T15a/T15b need 2022 HAVELLS **5m** tape (unavailable —
likely permanently uncheckable at native TF). The schematics stay definitional.
