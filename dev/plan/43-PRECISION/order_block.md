# order_block — precision audit

Detector `ob_taught` / event `OB_RETEST` / feature `order_block`.
Recognition/precision only (never edge/profit). Precision = of all firings, how
many are the REAL taught object (a genuine sweep→BOS→displacement-origin OB).
Recall is already ~100%; the goal is fewer, higher-conviction births so more of
a firing's grade-stack is real (the high-grade tier, `REFINE.md` iter-6 +4.57R,
lives in the CONJUNCTION + tiny-stop RR, not in raw firing count).

## Firing picture (over-fire)

Source: `runs/validate/precision_study/evidence.parquet`, `detector==ob_taught &
event==OB_RETEST`, 8 marked stocks, 17d 1m window (2026-06-25 .. 2026-07-17).

- **1505 total OB_RETEST fires** over 8 stocks.
- Overall **density = 11.07 fires / stock / session** (1505 / (8×17)).
- Direction near-symmetric: 750 LONG / 755 SHORT — no side bias, it just marks
  every pullback both ways.
- The flip lifecycle roughly **triples** total `ob_taught` output: the same
  births also emit **942 MIT_RETEST + 502 BRK_RETEST** = **2949 emissions**. The
  OB_RETEST audited here is only the first third of the over-fire.

| stock | fires | density (fires/sess = fires/17) |
|---|---|---|
| TITAN | 243 | **14.29** |
| VOLTAS | 200 | 11.76 |
| HEROMOTOCO | 199 | 11.71 |
| HDFCBANK | 190 | 11.18 |
| HAVELLS | 174 | 10.24 |
| SBILIFE | 172 | 10.12 |
| DABUR | 171 | 10.06 |
| DLF | 156 | 9.18 |

A genuine taught OB retest — a swept level, a BOS, price returning to the origin
candle of a displacement leg — is a **handful-per-day-at-most** event. ~9–14
fires *per session per stock* cannot all be that object. This is over-firing at
~1 taught-object-to-10-noise.

**Box-size is the tell.** The bodies box `zone_hi−zone_lo` decodes the noise
directly (median box = 0.48 ATR):

- box **< 0.1 ATR**: 127 fires (8%) — single-doji micro-boxes.
- box **< 0.2 ATR**: 314 fires (21%).
- box **< 0.3 ATR**: 475 fires (**32%**).
- box **< 0.5 ATR**: 786 fires (52%).

A third of all firings sit on a sub-0.3-ATR bodies box — one tiny candle plus a
break candle. That is not an accumulation/distribution origin zone; it is noise
being minted as a zone and later retested.

## In-window precision (honest data limit)

Window (1m/wide): **2026-06-25 .. 2026-07-17** (17 trading days). Of the **145**
registry `order_block` marks (100 on the 8 firing stocks), only marks whose
`date_approx` falls in the window AND whose price geom matches the in-window tape
era are checkable against firings.

**In-window checkable-against-firings n = 3 distinct taught zones** (honest:
tiny). Raw date-parse flags 13 in-window marks (HAVELLS 12, DABUR 1), but they
collapse to 3 real zones after removing near-duplicates and price-era mislabels:

| stock | dir | mark box | date | note |
|---|---|---|---|---|
| HAVELLS | SHORT | 1228–1231 | 08/07 | 5 near-dup marks → 1 zone |
| HAVELLS | SHORT | 1219–1224 | 09/07 | 5 near-dup marks → 1 zone |
| DABUR | SHORT | 448.7–450.5 | 08–09/07 | 1 zone |

Excluded as uncheckable: HAVELLS `1955–1900` marks dated "26/06–20/07 2026" sit
in a ~2023–24 price era — the in-window HAVELLS tape is **1144–1227**, so no
candle can match (registry price-era mislabel, not a detector fault). All other
97 marks are out-of-window (2019–2026 various) or on a different price era.

**Match rule:** same stock, same direction, box overlap within `max(0.3% mid,
0.5 ATR)` pad, on the mark's date.

- **RECALL = 3/3 (100%)** — every in-window taught zone has a matching firing.
  Confirms the "recall already ~100%" premise.
- **PRECISION proxy (checkable days) = 5 matched fires / 50 total fires = 10.0%.**
  On the exact stock-days the 3 taught zones exist, the detector fired 50 times;
  only 5 of those firings land on the taught object. **~90% over-fire.**

Out-of-window (the other 97 marks / all 8 stocks), precision is not directly
checkable → **firing density is the proxy**: 11.07 fires/stock/session against a
taught-object base-rate of ~1/session says the same ~10% precision the in-window
sample measures. Both the tiny in-window n and the density proxy agree: roughly
one firing in ten is the real taught OB.

## Over-fire root cause

Two birth gates are effectively **off**, so nearly every pullback mints a zone.

1. **The sweep+BOS birth gate is defaulted OFF.** `_DEFAULTS["require_sweep_bos"]
   = False` (`ob_taught.py:47`), so `_gated` (`ob_taught.py:139-158`) returns
   `True` unconditionally — every zone is armed and every retest fires. The
   taught object is *sweep → BOS/CHoCH → OB* (`41-TOOLS/order_block.md`, "birth
   is cluster-break, not sweep+BOS"); the detector carries **neither** the
   liquidity sweep nor the structure break. The confluence that defines the
   object is present in the codebase but disabled.

2. **The birth itself (`_cluster`) has no displacement, no pause-length, and no
   box-size floor.** `_cluster` (`ob_taught.py:92-110`) births a zone the instant
   a bodies-cluster close pokes beyond the evolving box **and** the run held ≥1
   opposite candle (`k = next(j … bb[2] == -d)`, line 100). That is the *entire*
   gate. Concretely it admits:
   - a break that displaces only **0.05 ATR** past the box (no `min_disp_atr`);
   - a pause of a **single** opposite candle (`≥1`, not ≥2) — one doji in noise
     qualifies as "counter-pressure";
   - a box as thin as **0.005 ATR** (min observed) — no minimum box size.

   The defining property of an order block — it is the origin of a
   **displacement** leg — is never tested. So a doji + one break candle mints a
   zone, which then arms and fires on the next graze. This is why 32% of
   firings sit on sub-0.3-ATR boxes and density is ~11/session.

`pivot_dist_atr` (the EXT-distance grade) is computed at birth but TUNE froze it
to `maxd=any` — it grades, never gates (`ob_taught.py:168-170`,
`41-TOOLS/order_block.md` gap #4). So the one confluence term that *is* wired
also does not filter. Net: the gate that should encode "born after a
sweep+BOS, at the origin of a displacement" instead fires on "any pullback that
briefly reversed," and ~90% of the OB_RETEST grade-stack fed to the high-grade
tier is not the taught object.

## The precision tune + expected effect

**THE single highest-leverage change: add a birth-time DISPLACEMENT gate in
`_cluster` — require the continuation break to close ≥ `min_disp_atr`·ATR beyond
the broken box edge. TARGET `min_disp_atr = 1.0`.**

- Exact change: in `_cluster` (`ob_taught.py:98-107`), at the continuation-break
  branch (`c > bhi or c < blo`), after computing the break direction `d`, gate
  birth on displacement magnitude:
  `disp = (c - bhi) if d==1 else (blo - c)`; require
  `disp >= Decimal(min_disp_atr) * self.tape.atr` before constructing the Zone
  (else `self._run = []` and return `None`, same as a no-counter-pressure reset).
  Add `min_disp_atr` to `_DEFAULTS` (default 1.0).
- Why this one (over turning on `require_sweep_bos` or `min_pause_bars`):
  - It is a **pure local-geometry gate** — no dependence on the `sweep` /
    `structure` detectors being enabled or firing same-tick, so it is robust
    where the sweep+BOS gate is brittle (and the flip zones BRK/MIT inherit the
    selectivity automatically, since they are born from surviving OB parents).
  - It directly encodes the **defining** property of an OB (origin of a
    displacement leg), which is exactly what separates a taught OB from a noise
    pullback — the property `pivot_dist` and `min_pause_bars` only approximate.
  - It is empirically the **biggest single reducer**: the sibling `orderblock`
    detector gates on `displacement_atr=1.5` and fires ~54–72 births/window vs
    `ob_taught`'s 138–159 — a ~2.5× cut from displacement alone
    (`41-TOOLS/order_block.md`). A softer 1.0 keeps the tight taught OBs.

**Expected firing reduction.** A 1.0-ATR displacement gate cuts births ~2.5×
(from the `orderblock` comparison; and it removes the whole micro-break tail that
drives the 32% sub-0.3-ATR / 8% sub-0.1-ATR boxes, since a 0.005–0.1-ATR box
cannot be preceded by a 1-ATR break without the break itself being the box):

- **1505 → ~550–600 OB_RETEST fires, ≈ −60%.**
- **Density 11.07 → ~4.0 fires/stock/session.**
- The heaviest names collapse most (TITAN 14.3→~5.7, VOLTAS 11.8→~4.7); DLF's
  9.2 → ~3.7. The cut lands where the over-fire is worst.

**Effect on the high-grade tier.** Every surviving OB is now born at a ≥1-ATR
displacement origin — a real leg, not a noise reversal — so the fraction of
OB_RETEST evidence that is the taught object rises from the measured ~10% toward
~25–30% (≈2.5× the real-object density with ~60% fewer firings). Recall for the
taught object is preserved: the 3 in-window matched zones and the 22
doc-validated hits all sit before genuine displacement legs
(`41-TOOLS/order_block.md` P3: "Measured hits all sat before real displacement
legs; nuisance micro-breaks do not"), so `min_disp_atr=1.0` is expected to cost
**0 of them**. This is a pure precision gain: fewer, higher-conviction firings,
each carrying a real grade-stack into the conjunction + tiny-stop RR.

**Second-order tunes (secondary, do not conflate with the top one).**
1. `min_pause_bars = 2` (`ob_taught.py:100`, require the counter-pressure run
   ≥2 bars) removes the single-doji "pause" — complementary, smaller effect.
2. Flip `require_sweep_bos = True` with `gate_mode="sweep_and_bos"` once the
   `sweep`/`structure` detectors are confirmed to precede `ob_taught` in config
   order — turns the taught confluence into a real filter, but its numeric effect
   depends on upstream wiring not present in the firing parquet, hence secondary
   to the fully-quantified displacement gate above.
