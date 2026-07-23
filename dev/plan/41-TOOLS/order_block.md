# order_block

Validation of the **order_block detector family** against **every** hand-marked
`order_block` instance in `runs/validate/tools/registry.jsonl` — **145 instances**
across 12 symbols (the single largest feature in the registry). Three
implementations were read and judged:

- `app/trader/detectors/ob_taught.py` (`ObTaughtDetector`, `name="ob_taught"`) —
  **the taught OB**, the object this doc validates against (lessons 3/12 + frozen
  `runs/taught/TUNE.md`).
- `app/trader/detectors/ob_lux.py` (`ObLuxDetector`, `name="ob_lux"`) — the ported
  LuxAlgo internal OB (swing-pivot + structure-break anchor).
- `app/trader/detectors/orderblock.py` (`OrderblockDetector`, `name="orderblock"`)
  — the displacement/mid-air OB (a candle followed by ≥`displacement_atr`·ATR).

Per-instance records: `runs/validate/tools/val_order_block.jsonl` (one JSON row
per instance, no silent drops).

**Guardrail honoured (RETHINK.md):** this validates **RECOGNITION** — does an OB
fire on the candle/zone the user drew, at the right price, right direction — and
**never claims EDGE**. The measured null tested a *mis-built proxy* (ATR stop,
body-edge SL), so this validates the **user's geometry**, not the shipped default
economics. Only **t31 SBILIFE has a firm year (2024)**; every other date/year is a
price-era guess (`tools/ytrades.json`, `runs/validate/results.json`), so dates are
approximate and several "gaps" below are registry mislabels, not detector faults.

## Feature notes (structure & validity)

**What the user's `order_block` mark is.** A box on the **last opposite-colour
candle(s) before a displacement move** — the origin of the leg that broke
structure. Demand OB = the down/base candle(s) before a rally (LONG); supply OB =
the up candle(s) before a drop (SHORT). The taught birth is **sweep → BOS/CHoCH →
the OB is the origin candle of the displacement**, entered on a **retest** of the
zone, CE (50% midpoint) as the trigger, SL beyond the **outer wick**.

**What `ob_taught` detects (the validated object).**
- **Zone geometry — BODIES only.** `_cluster` (`ob_taught.py:91-109`) tracks a run
  of bars whose closes stay inside an evolving **body** box; the first close
  beyond the box is the continuation break. If the pause held ≥1 candle *opposite*
  to the break direction, the zone is `min/max` of the **bodies** (`bb[0]`/`bb[1]`)
  from that first-opposite candle onward — **wicks excluded** (bodies-only is
  frozen: +3.46..+3.83 vs the full box, `ob_taught.py:8-12`). Born at the break
  bar.
- **Birth trigger — bodies-cluster break WITH counter-pressure**, not sweep+BOS.
  `k = next(j … bb[2]==-d)` (`ob_taught.py:99`) requires the pause to contain a
  candle opposite the break — a *reaction proxy*. There is **no liquidity-sweep
  gate and no BOS/CHoCH confirmation**. A break with no opposite candle is just
  trend and resets the run (no zone).
- **Grade (not a filter).** `_grade` (`ob_taught.py:138-153`) writes
  `pivot_dist_atr` = ATR distance from the zone's origin edge to the nearest
  same-side **EXT** pivot (`_PIV`, extremes-first, SWING fallback — commit 8dc7cc8
  made extremes the taught anchor). `far_dist_atr=99` when no pivot/ATR. TUNE froze
  `maxd=any`, so distance **grades, never gates**.
- **Lifecycle — break-depth law + flip.** `taught.step_zone` (`taught.py:65-80`): a
  zone dies when a bar **closes** through its far edge by ≥`depth_atr`(0.5)·ATR;
  shallower = "second life". On kill the box **FLIPS** to the opposite direction
  (same box, parent's grade): **BRK** if the birth leg's running extreme took the
  prior same-side extreme (`pex`, swept) else **MIT** (`ob_taught.py:74-81`). Retest
  = arm (a bar fully beyond the box on the origin side) then first touch of the
  proximal edge, one-shot.
- **Entry / SL — EDGE + body-edge.** `_evidence` (`ob_taught.py:155-165`) emits
  `zone=(z.lo,z.hi)`, `direction` LONG/SHORT, `strength=0.7`, `ttl=6`,
  `meta.sl = z.lo (long) / z.hi (short)` = the **bodies far edge**, plus
  `sl_floor = 0.15·ATR`. Entry is the zone **edge**, not CE.
- **Params/defaults** (`ob_taught.py:47`): `{tf:"5m", depth_atr:0.5,
  sl_atr_floor:0.15, far_dist_atr:99.0}`. Full-history cursor; Evidence only from
  the latest closed bar.

**HOW/WHEN it fires (measured behaviour).** On real tape `ob_taught` is
**promiscuous**: it births a same-side OB on nearly every pullback. Measured
counts in the validation windows — **138–159 same-side births in a ~1125-bar 5m
window** (e.g. HAVELLS 5m 138 short; VOLTAS 142 long; DABUR 145; SBICARD 159);
**~19 demand OBs in 112 daily SBILIFE bars**. `ob_lux` fires ~⅓ as often
(pivot+BOS gated: 40–51 per window), `orderblock` in between (54–72). So *recall
is trivially high and precision is the real problem* — the detector almost always
overlaps a hand-marked zone because it marks so many.

**CONFLUENCE.** The taught OB is the entry leg of `sweep → BOS → OB/FVG`.
`ob_taught` collapses that chain into a single local rule (cluster-break +
counter-pressure) and **carries neither the sweep nor the BOS gate** — those live
in `sweep.py`/`structure.py`/`breaker_msb.py`. `pivot_dist_atr` (vs EXT) is the
only confluence term, and it grades rather than gates.

## How the user draws it

A rectangle on the origin candle(s) of a displacement leg, after a liquidity
sweep and a break of structure. Read: price returns to the box, taps **CE (50%)**,
continues in the displacement direction; the **stop sits a few points beyond the
OUTER WICK** of the OB candle (not the body). On tight intraday OBs the box is
essentially the single origin candle (≈ its body, sometimes body-plus-a-wick); on
HTF/base marks the user draws a **wide accumulation/distribution zone** spanning
several candles (VOLTAS 25 pt, TITAN 45 pt, HAVELLS T2a 16 pt). The same zone is
often redrawn across several zoom levels (t1×5, t28×10, t29×11) — 145 marks
collapse to far fewer distinct zones.

## Accuracy verdict

**pct_match = 22 / 62 = 35.5%** — `hit / (hit+partial+miss)`, uncheckable excluded
from the denominator. Uncheckable (**83**) reported separately.

| verdict | count | what it means here |
|---|---|---|
| hit | 22 | fires same-side OB whose **bodies box ≈ the drawn box within ≤~1 ATR**, matching-tf-era tape |
| partial | 40 | fires same-side near the zone but **box off >1 ATR** (wide zone under-covered) **or only coarser-tf tape** (1h vs 5m) — birth-on-the-exact-candle unverifiable |
| miss | 0 | none — the detector over-fires, so it never *fails* to overlap a marked zone (see caveat) |
| uncheckable | 83 | no NSE tape / pre-data era / price-era-inconsistent label / intraday mark with daily-only tape |

**The 0 misses is not a strength — it is the finding.** `ob_taught` births so many
same-side OBs that *any* hand-marked zone is overlapped by *some* birth. Recall is
~100% of checkable; the discriminating number is the **35.5% tight-box HIT rate**
— only about a third of the drawn boxes are reproduced to OB scale; the rest are
wide-zone or tf-coarse partials. Precision (does it fire *only* where the user
would) is untested here and, given 138–159 births/window, is the open risk.

**Per-stock breakdown**

| stock | hit | partial | miss | uncheck | note |
|---|---|---|---|---|---|
| HAVELLS | 10 | 5 | 0 | 40 | t1 supply OBs reproduce to <0.3 ATR; T2a/t6 partial; 2020–23 era + T3/T5 price-era-mislabel all uncheckable |
| SBICARD | 7 | 16 | 0 | 0 | t28 5m/10m/15m HITs; t29/t30 1h-confirmed but tf-coarse; t28 HTF box partial |
| DABUR | 2 | 3 | 0 | 0 | t24/t25 tight HITs (<0.8 ATR); t27 1h-confirmed (tf) |
| SBILIFE | 2 | 2 | 0 | 0 | t32a daily HITs; **t31 (firm 2024)** supply confirmed on daily but no intraday tape |
| VOLTAS | 1 | 4 | 0 | 0 | T19_1 tight HIT; T18 wide demand zones under-covered |
| TITAN | 0 | 3 | 0 | 0 | t22 wide zone; t23 big-body cluster overshoots the drawn supply |
| DLF | 0 | 5 | 0 | 5 | 2025 legs 1h-confirmed (tf); 2022 t21 pre-1h → uncheckable |
| HDFCBANK | 0 | 2 | 0 | 6 | h4256/h4315 native-30m fire (over-fire, box ~2–5 pt off); 2025 legs no tape |
| HEROMOTOCO | 0 | 0 | 0 | 10 | no Yahoo tape; all marks pre-native or 2019–20 |
| EURUSD/GBPUSD | 0 | 0 | 0 | 4 | foreign, no NSE tape |
| (reference) | 0 | 0 | 0 | 18 | educational schematics, no axis/tape |

**NUMERIC gaps seen in real data (values, bodies-box vs drawn-box):**

- *Tight OB marks reproduce to sub-ATR.* HAVELLS 08/07 supply — mark `1231–1228`,
  `ob_taught` bodies **`1227.9–1231.7`**, edge gap **<0.7 pt (<0.07 ATR≈11.3)**;
  its **wick span 1227–1234 is WIDER than the user's box**, i.e. here the user drew
  ≈ the bodies, *not* the outer wick. DABUR t24 short — mark `450.5–448.7`, bodies
  `449.1–450.05`, gap **0.45/0.4 pt (<0.7 ATR≈0.62)**, and the birth **wick span
  448.3–450.5 == the user's box exactly**. DABUR t25 long gap 0.8/0.5 (<0.8 ATR).
  VOLTAS T19_1 short gap 2.8/1.8 (<0.6 ATR≈3.4). SBICARD t28 5m gap 1.25/0.7 (<0.7
  ATR≈1.83). SBILIFE t32a daily demand OB `840.8–858` overlaps drawn `843–865`
  within ~0.5%. **On tight marks the box mismatch is ≈ one wick and the ≈-bodies
  drawing style means the doc35 "outer-wick box" gap is small.**
- *Wide-zone marks are systematically under-covered.* VOLTAS T18 — 25 pt demand
  zone `1230–1205`, bodies box only **1.8 pt** (`1215.5–1217.3`) sitting inside it,
  edge gap **12.7/10.5 pt (~4 ATR)**. TITAN t22 — 45 pt zone `4045–4000`, bodies
  3 pt, gap 21.9/19.7 (~1.7 ATR). HAVELLS T2a — 16 pt zone, bodies 0.8 pt, gap
  4.5/10.7. **This is the real box gap: a single-candle bodies box cannot represent
  a multi-candle accumulation zone.** `orderblock`/`ob_lux` (full-candle range)
  would cover more of these but still not a merged multi-candle span.
- *Big-body overshoot (opposite failure).* TITAN t23 supply — mark `3525–3500`,
  `ob_taught` bodies **`3493.95–3555` ENGULF** the mark (hi_gap −30 = 1.3 ATR≈22.7):
  a large-bodied cluster anchored a wider box than the tight supply the user drew.
- *Over-fire signature.* SBILIFE daily 2020–21: 19 demand OB births in the t32a
  window; both drawn zones (`843–865`, `865–885`) are hit, but so are ~17 others —
  recognition is real, selectivity is absent.

**STRUCTURAL gaps (doc35 checklist):**

1. **OUTER-WICK box vs INNER-BODY block.** `_cluster` emits **bodies only**
   (`ob_taught.py:102-106`). Confirmed against tape: the detector zone is the body
   span; the drawn box is between body and outer wick. On tight marks these
   nearly coincide (small gap); on wide zones the body box is far too tight. `sl`
   is likewise the **bodies far edge** — the outer-wick low/high the user stops
   beyond is **never emitted**. (doc35 gap #1 + #3.)
2. **CE entry not emitted — EDGE only.** `_evidence` returns `zone=(z.lo,z.hi)` and
   a retest fires on the **proximal-edge touch** (`step_zone` "first touch of the
   proximal edge"). The user's **CE (50% midpoint)** trigger is not computed; there
   is no `entry` field in `meta`. (doc35 gap #2.)
3. **Birth is cluster-break, not sweep+BOS.** `ob_taught` births "mid-structure"
   on a bodies-cluster break with counter-pressure; `ob_lux` births on **pivot +
   structure-break** (closer to BOS, still no sweep); `orderblock` births purely
   **mid-air on displacement** (no sweep, no BOS — the weakest). None gate on a
   prior **liquidity sweep**. (doc35 gap #4.)
4. **Liquidity from EXT — wired, as grade only.** `_grade`/`_PIV` read `EXT_H/EXT_L`
   first (SWING fallback), so the taught anchor IS used — but only to write
   `pivot_dist_atr`, which TUNE froze to `maxd=any` (never a filter). The EXT
   relationship does not shape birth or the box. (doc35 gap #5 — half-closed.)
5. **SL is dangerously tight.** `sl = z.lo/z.hi` (bodies edge) is **inside** the
   outer wick, exactly the fill-through-exposed stop the falsified-fade memory
   warns about. `sl_floor=0.15·ATR` is the only cushion.

**Data limits (per RETHINK / no silent drops):**
- Native 5m only < 60 d (`data/long5m` 2026-04-27→07-17 + Yahoo 5m since
  2026-05-25); Yahoo 1h from ~2024-07-24; Yahoo daily full. **No Yahoo intraday for
  HDFCBANK, HEROMOTOCO, SBILIFE.** So: HAVELLS/DLF 2020–23 5m marks, DLF t21 2022,
  all HEROMOTOCO, HDFCBANK 2025 legs → **no matching-tf tape → uncheckable**.
- **tf-granularity mismatch** downgrades to *partial*: t6/T19_2/T20/t23/t27 (5m
  marks) and t29/t30 (5m–30m marks) were reproduced on **1h** tape (right side,
  right zone, box within tolerance) but the **exact 5m birth candle is
  unverifiable**. t31 (firm 2024, 30m) has only **daily** tape: the supply
  `1900–1912` is confirmed by the 2024-09-23 daily bar (O1882 **H1925** rejected,
  next bar closed 1864), but no 30m candle is checkable.
- **Price-era / label conflicts (registry, not detector):** HAVELLS T3a/T3b/T5a
  boxes `1955–1900 / 1875 / 1885` are a ~2023–24 era, yet dated 2026 where the tape
  is `1120–1234` — no candle can match; logged uncheckable. (Same circular
  year-resolution RETHINK A2 flags.)
- **T18_3** shows the registry `resolved_date` pointing at the **entry leg**
  (02–03/06) not the **OB origin** (18/05) — the sibling May zone (T18_1/2/4) does
  fire, so the mark is real but its date field mislocates the birth candle.

## Enhancement plan

Prioritised; exact params/functions referenced. RECOGNITION-scoped — none of this
claims edge. Because recall is already ~100% and precision is the gap, the theme is
**tighten selectivity and emit the taught geometry**, not "fire more".

**P1 — structural: emit the OUTER-WICK SL and the CE entry.**
In `ob_taught._cluster`, alongside the bodies box, retain the sub-run's **outer
wick** (`min low / max high` of the OB candles — already computed as `wlo/whi` in
the validation harness). In `_evidence` (`ob_taught.py:155-165`) add
`meta.sl_wick = outer-wick ± tick` and `meta.entry_ce = (z.lo+z.hi)/2` (the 50%
midpoint). This is the single highest-value change: it produces the
**physically-different stop object** (past the wick, where fill-through exhausts)
that the whole method and RETHINK §D2 rest on, and the CE trigger the user
actually uses — neither of which any OB detector currently emits. Keep bodies-only
as the box (it is frozen-validated) but carry both the wick and CE in `meta`
(non-breaking).

**P2 — structural / numeric: a merged multi-candle zone for wide marks.**
The wide-zone partials (VOLTAS T18 4 ATR, TITAN t22 1.7 ATR, HAVELLS T2a) fail
because one origin candle's body cannot span a 15–45 pt accumulation zone. Add an
optional **zone-merge**: when consecutive same-side births overlap within
`merge_atr` (**TARGET ≈ 0.5 ATR**, matching the break-depth constant), coalesce
their boxes into one zone (lo=min, hi=max). This lifts T18/T22/T2a from partial
toward hit without touching the tight-OB path. Reference the `flips`/`zones` list
maintenance in `ObZones.step` (`ob_taught.py:66-89`).

**P3 — numeric threshold: a birth-selectivity gate (precision, not recall).**
138–159 births/window is the precision problem. Add params to `_cluster`, defaulted
so the 22 hits survive:
- `min_disp_atr` ≈ **1.0** — require the continuation break to displace ≥1 ATR from
  the box (the `orderblock` idea, `displacement_atr=1.5`, but softer). Measured
  hits all sat before real displacement legs; nuisance micro-breaks do not.
- `min_pause_bars` ≈ **2** — require the counter-pressure pause to be ≥2 bars, not
  the current ≥1 (`ob_taught.py:99`), so a single opposite candle in noise is not a
  zone.
- Keep `depth_atr=0.5` (frozen, validated) for the kill law.
These cut the 138→(target ~30–50) births/window and are expected to cost **0 of the
22 hits** (all sit at genuine reaction→displacement origins).

**P4 — birth-gate / confluence: wire the sweep+BOS the marks require.**
`ob_taught` births without the sweep or BOS the user demands. Rather than re-derive
them, **gate birth on confluence already produced upstream**: only arm a zone whose
origin edge is within `pivot_dist_atr ≤ gate_atr` of an **EXT** pivot AND has a
`sweep`/`structure` Evidence within N bars. `pivot_dist_atr` is already computed
(`_grade`) but frozen to grade-only (`maxd=any`); expose `maxd` (**TARGET ≈ 2.0
ATR** to start) as a real gate under a flag. This is the "liquidity from EXT" +
"born after sweep+BOS" pair (doc35 #4/#5) turned into an actual filter — test it
*only* against constructed losers (RETHINK §D1), since the 3-TF stack alone is
already ~dead.

**P5 — config hygiene: timeframe + detector selection.** Default `tf="5m"`; HTF
marks (30m/1h/2h/daily) only reproduce on their own TF — document that `tf="5m"` on
daily-only data yields nothing. For the box geometry, note the trade-off: `ob_taught`
(bodies) is tightest and matches tight OBs best; `ob_lux`/`orderblock` (full-candle
range) cover wide/wicky marks better but birth differently (`ob_lux` pivot+BOS is
the closest to the taught birth). A per-run choice — or running `ob_taught` for the
box + `ob_lux` for the birth-structure gate — is the pragmatic combination.

*Cross-cut for the whole registry:* re-resolve dates against the **actual OB origin
candle** the detector finds (T18_3's date points at the entry, not the origin; T3/T5
prices are a different era), rather than the outcome-maximising year (RETHINK A2),
before any of these are used as ground truth for edge work.
