# fvg (fvg_n) — PRECISION audit

Detector `fvg_n` · emitter `fvg_n` · events `FVG_N_RETEST`, `IFVG_RETEST` ·
feature `fvg` / `ifvg`.
Data: `runs/validate/precision_study/evidence.parquet` (8 stocks × 17d, 1m→5m),
marks `runs/validate/tools/registry.jsonl`. RECOGNITION/PRECISION only — no
edge/profit claim. Recall is already ~100% (per `41-TOOLS/fvg.md`: 0 outright
misses at native tf); the lever here is **precision = of all firings, how many
are the REAL taught object** (a large displacement gap, an OB-refined pocket
born after a sweep+BOS — not a mid-air micro-void).

## Firing picture (the over-fire)

**3376 total** `fvg_n` retest fires over 8 stocks × 17 sessions.
`FVG_N_RETEST` 1749 · `IFVG_RETEST` 1627 (**48%** of all fires are the flip twin).

| stock | fires | density (fires/session) |
|---|---:|---:|
| HDFCBANK | 451 | 26.5 |
| TITAN | 450 | 26.5 |
| DLF | 430 | 25.3 |
| HAVELLS | 430 | 25.3 |
| VOLTAS | 428 | 25.2 |
| HEROMOTOCO | 425 | 25.0 |
| SBILIFE | 392 | 23.1 |
| DABUR | 370 | 21.8 |
| **overall** | **3376** | **≈24.8 fires / stock / session** |

The user marks **≈0–1** FVG per stock per session. The detector emits **~25**.
Over-fire ratio ≈ **25:1**. Gap-size distribution of the firings (gap = zone_hi −
zone_lo, over ATR(14)): **p50 = 0.31×ATR**, p25 = 0.14, p10 = 0.06 — i.e. **half
of all firings are sub-0.31×ATR micro-gaps**, while every clean marked hit in
`41-TOOLS/fvg.md` was **1.4–3.7×ATR**. The firing swarm is a different, smaller
object than the taught one.

## In-window precision (honest n)

Window = **2026-06-25 .. 2026-07-17** (17 trading days). Of the 35 `fvg`/`ifvg`
marks, only those on a **firing-set stock** with `date_approx` inside the window
are checkable. **SBICARD carries most fvg/ifvg marks but is NOT in the firing
set** (the firing set has SBILIFE, not SBICARD), so all its marks are excluded.

**In-window checkable marks: ~3–4 unique objects across 2 stocks:**
- HDFCBANK **06/07** bull, box ~800–822 (30m) — 2 registry rows, one object.
- HDFCBANK **08/07** bear, box ~825–832 (30m) — 2 registry rows, one object.
- HAVELLS **08/07–13/07** FVG, box 1208–1224 (30m).
- HAVELLS **12/06–13/07** bull, box 1141–1148 (30m) — birth pre-window (borderline).

**In-window iFVG marks for the 8 firing stocks: ZERO.** (The only iFVG marks are
2× SBICARD/2025 — not in set — and HEROMOTOCO 09/02/2026 — out of window.) So the
**1627 `IFVG_RETEST` fires (48% of the total) have no ground-truth object to match
at all** — their measurable precision is 0.

**Match result (firing near a mark: same stock/session, zone overlaps the mark band):**

| mark | fires in session | overlap mark band | reading |
|---|---:|---:|---|
| HDFCBANK 06/07 bull 800–822 | 4 | **0** | 5m gaps that day sat elsewhere (tf/geometry) |
| HDFCBANK 08/07 bear 825–832 | 27 | 19 | swarm — **both** LONG & SHORT, 0.1–3pt boxes, many iFVG |
| HAVELLS 08/07 1208–1224 | 40 | 24 | swarm — both directions |
| HAVELLS 12/06–13/07 1141–1148 | 39 | **0** | 5m gaps sat elsewhere |

**Precision verdict.** The "19/24 overlaps" are **not** 19 detections of one taught
object — they are 19 different micro-gaps (both directions, half of them iFVG
flips) that happen to lie in the same price band as the single 30m taught box.
Correcting for it: each in-window taught object is buried under **20–40
same-session firings, of which ~1 is the taught grade → within-session precision
≈ 1/25–1/40 ≈ 3–4%**. Recall is fine (a same-direction firing does sit near each
matchable mark, consistent with the doc's ~100% recall), but **precision is the
inverse of the density**: **≈24.8 fires/stock/session vs ≈0–1 taught object → a
density-proxy precision of ~4%.** (n is tiny and stated honestly; density is the
proxy exactly because the checkable in-window count is ~2–4 objects.)

## Over-fire root cause (code)

`app/trader/detectors/fvg_n.py` + `taught.py`:

1. **No minimum gap size — the #1 volume driver.** `FvgZones._keep` accepts a
   candidate on `burst and hi > lo` **with no `min_gap_atr` gate** (the frozen
   TUNE config is `q = 0`, "any size"). A 0.1pt / 0.06×ATR void arms and fires
   (seen: 829.30–829.40, 828.05–828.65). p50 firing = 0.31×ATR; **48% of fires
   are below 0.3×ATR, 69% below 0.5×ATR** — none are the 1.4–3.7×ATR taught grade.

2. **kill→iFVG flip auto-doubles the population.** `step` creates
   `Zone("IFVG", -z.dir, z.lo, z.hi, …)` for **every** killed FVG (`fvg_n.py:63`).
   Each micro-gap therefore spawns an opposite-direction twin that then arms and
   fires its own `IFVG_RETEST`. This manufactures the **1627 (48%)** iFVG fires
   against **zero** in-window iFVG marks, and puts **both** LONG and SHORT firings
   in the same price band (HDFCBANK 08/07). The user teaches iFVG rarely; the
   detector emits it half the time.

3. **No structural birth gate.** The taught FVG is "the refined pocket **inside a
   live OB**, born in the **displacement leg that swept a liquidity extreme and
   broke structure**" (`41-TOOLS/fvg.md` §CONFLUENCE, P1). `fvg_n` requires none of
   sweep / BOS / OB-nesting — it fires on every mid-air displacement burst.

4. **`mmax = 6` × 5m tf multiplies fragments.** For each ending bar `step` tests
   m = 1..6 (`fvg_n.py:67`); on 5m a 30m displacement fragments into many small
   sub-gaps. The merge/dedup rule only drops same-window **same-band** overlaps, so
   different-m windows still survive as distinct micro-boxes. The taught object was
   drawn on **30m**; running on **5m** manufactures the swarm and offsets geometry.

Root causes 2 and 4 are amplifiers; **root cause 1 (no gap-size birth gate) is the
generator** — and because an iFVG can only be born from a killed FVG, gating FVG
births by size **cascades**: no micro-FVG → no micro-kill → no micro-iFVG twin.

## The precision tune + expected effect

**THE single highest-leverage change: add a `min_gap_atr` birth gate in
`FvgZones._keep`, target `0.7`.** Require the birth gap to clear
`0.7 × ATR(14)` (`self.tape.atr` is already maintained at the birth bar):

```
# fvg_n.py, in _keep (or guarding the _keep calls in step):
if self.tape.atr is not None and (hi - lo) < Decimal("0.7") * self.tape.atr:
    return                      # sub-grade void — do not arm
```
Wire `min_gap_atr` into `_DEFAULTS` (currently frozen q=0) and thread it into
`FvgZones`.

**Why this one.** It attacks the generator, not a symptom, and is a single
numeric constant with a data-anchored target: every clean marked hit was
1.4–3.7×ATR, so 0.7 keeps the entire taught grade with margin while cutting the
sub-0.3×ATR half of the tape. Because the iFVG twin inherits the killed FVG's box,
gating **FVG** births at 0.7 also gates every future iFVG — one gate throttles
**both** populations at the source (no separate flip switch needed).

**Expected firing reduction (measured on this dataset):**
- Fires with gap ≥ 0.7×ATR: **708 of 3369 → 79.0% eliminated** (3376 → ~708;
  density **24.8 → ~5.3** fires/stock/session).
- Survivors are the marked-grade tail; surviving iFVGs are only those flipped from
  a **large** killed gap (the genuine breaker/iFVG concept the user does teach).
- Effect on the high-grade tier: precision (fraction of firings that are the real
  taught object) rises mechanically **~3.7×** (≈4% → ≈15–20% within a marked
  session, since the ~1 taught object now competes with ~5 firings, not ~25).
  **Recall preserved**: the checkable marks are 7pt (HDFCBANK 08/07, ≈7×ATR) and
  16pt (HAVELLS, ≈16×ATR) wide — far above the 0.7×ATR floor.

**Stronger variants (if 0.7 leaves residual noise), in leverage order:**
- Raise to **1.0×ATR** → 428 survive (**87.3% cut**, density ≈3.1). Still keeps
  every 1.4–3.7×ATR marked hit; trims recall margin.
- Add the **structural P1 gate** (arm only when nested in a live `ob_taught` zone
  and born in a swept+BOS leg) on top — highest conceptual precision, most code.
- Combined (drop-all-iFVG + FVG≥0.7) collapses to **11.3% survivors (88.7% cut)**,
  but the single-constant gap gate already delivers ~79% with one line and no
  behavioural surprises, so it is the recommended first move.
