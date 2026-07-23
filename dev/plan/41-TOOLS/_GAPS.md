# _GAPS — completeness audit (2026-07-23)

Machine cross-check of `runs/validate/tools/{registry.jsonl, val_*.jsonl}` against
`MATRIX.md` + the 14 `41-TOOLS/*.md` tool docs + doc 40. Verdict: **coverage is
complete — every mark is accounted for.** Nothing was silently dropped. What is
*missing* is not coverage but **buildable detector surface** (2 tools don't exist,
7 tools score 0% recognition).

Guardrail carried through: every count here is **RECOGNITION** (does the detector
fire on the right object), never EDGE. No profitability is claimed anywhere.

---

## 1. Coverage stats (instances validated / total)

| metric | value |
|---|---|
| registry rows | **467** (distinct instance_id 467, **0 duplicates**) |
| distinct charts | **139** |
| vocab features | **16** (all with ≥1 instance) |
| val_*.jsonl files | **14** · total rows **467** · distinct instance_id **467** |
| **instances validated (have a verdict)** | **467 / 467 = 100.0%** |
| — every registry id in EXACTLY ONE val row w/ verdict | ✔ (0 miss, 0 orphan, 0 double-validated, 0 blank-verdict) |
| **checkable (hit+partial+miss)** | **218 / 467 = 46.7%** |
| uncheckable (no native tape / reference / foreign) | **249 / 467 = 53.3%** |
| hit / partial / miss | 82 / 102 / 34 |
| hit-rate over checkable | 82 / 218 = **37.6%** |

Per-tool verdict counts in all 14 tool docs and in `_CONFLUENCE.md §2` were
recomputed from the val files and **reconcile exactly** — no numeric drift.

## 2. The uncovered list

**Instances with NO verdict: NONE.** The "miss-nothing" contract holds — every one
of the 467 marks carries a hit/partial/miss/uncheckable verdict.

**Charts with zero validated marks: NONE** (all 139 charts have every mark verdicted).

**Charts contributing ZERO *checkable* evidence (all marks uncheckable): 60 / 139.**
Not a coverage miss — these are structurally unscorable (no NSE tape / reference /
foreign / daily-only for an intraday mark). Breakdown:
`31 reference-graphic · 8 HEROMOTOCO(dev) · 6 HDFCBANK(dev) · 4 HAVELLS · 4 DLF ·
2 EURUSD · 1 each GBPUSD/BTC/BTCUSD/XAUUSD/TSLA`. Root cause = native 5m only <60d.

**Features with zero instances (never marked): NONE.** All 16 vocab features have
≥1 mark (min = `spring_utad` n=1).

**Features with zero *hits* (0% recognition even where checkable):**
`compression (0/2) · ifvg (0/2) · propulsion (0/9) · spring_utad (0/0) ·
volume_time (0/2) · wyckoff_phase (0/2) · htf_ltf_nesting (0/8)`. These are the
build-blocking tools of §4.

## 3. Doc-consistency flags

- **No contradiction between any two 41-TOOLS docs on the numbers.** Every
  `pct_match` and verdict tally (breaker 6/7=85.7, sweep 15/18=83.3, extremes
  17/29=58.6, structure 8/16=50, fvg 9/18=50, ob 22/62=35.5, mit 1/9=11.1,
  liquidity 2/34=5.9, p/d 2/2=100, and the five 0% tools) matches the val files
  and `_CONFLUENCE §2` bit-for-bit.
- **One structural discrepancy (minor).** Doc 40 (`40-TOOL-ACCURACY-PLAN.md`
  lines 13-15, 67-68) promises **16** feature columns and `{<16 tools>.md}`, but
  only **14** tool docs exist. `ifvg` (n=3) and `spring_utad` (n=1) have **no
  standalone doc** — they are folded into `fvg.md` (denominator 18 = 16 fvg + 2
  ifvg checkable) and `wyckoff.md` (denominator 2 pools the spring). Their
  instances ARE validated (in `val_fvg`/`val_wyckoff`), so coverage is intact;
  the deliverable count is 14, not 16. Their pooled pct hides that ifvg is 0/2
  and the spring is uncheckable.
- **No re-introduced optimism.** Every tool doc + `_CONFLUENCE` + doc 40 carries
  the explicit RECOGNITION≠EDGE guardrail. All "edge" tokens are either geometric
  ("box edge") or negated ("not an edge"/"claims edge → never"). The lone 100%
  (`premium_discount`, n=2) is repeatedly qualified "spec-only, treat as unbuilt,
  recognition not edge." No profitability survives.
- **Stale paths (data-integrity, not coverage).** 2 registry chart paths no
  longer exist on disk (`.../trades/t23/...11-09-13.png`,
  `.../trades/T9/...09-34-32.png`); their marks were validated analytically, so
  no verdict is lost, but the paths need re-pointing before any re-run.

## 4. Build-blocking gaps — what data / spec each needs

**G1 — `premium_discount`: NO DETECTOR EXISTS (headline gap).**
`grep -rniE "premium|discount|equilibrium|dealing.?range" app/trader/detectors/`
returns nothing. Only 2/8 marks are scorable (both HTF SBILIFE, hit).
- **Spec to build** (`app/trader/detectors/premium_discount.py`): consume master
  `EXT_H`/`EXT_L` from `extremes.py`; range `[L,H]`, `EQ=(L+H)/2`,
  `range_pos=(price-L)/(H-L)`; emit a **context gate** (not Evidence) — long only
  `range_pos≤0.5`, short only `≥0.5`; OTE bands 0.62–0.79 / mirror 0.21–0.38.
- **Anti-fragility (RETHINK B5):** range must come from a **confirmed master EXT
  pair** (leg_pct 6.0), never a fixed 40-bar window; add `min_range_atr` (~8-10×
  ATR) + `eq_deadband` 0.10 so tiny ranges don't emit a side.
- **Data need:** add `4h`/`1d` to `extremes._DEFAULT_TIMEFRAMES` for positional
  marks (t32b). SBILIFE is daily-only → EQ validated on daily proxy only.

**G2 — `htf_ltf_nesting`: NO DETECTOR; scoring spec = 0/8 (0%).**
Scoring spec is well-formed (`hit/(hit+partial+miss)=0/8`, 1 uncheckable excluded;
hit 0, partial t28j/t29f, miss t28a/b/e/g/h/i). But the **denominator includes
instances on timeframes the engine cannot form**, so 0% is partly structural.
- **Spec to build:** new `detectors/htf_nest.py` — generalise `ladder._rung`
  (lines 199-206) from a single H1↔M5 overlap to a loop over `[D1,H1,M15,M5]`
  counting parents a child zone nests inside → `nest_depth` on level meta; entry =
  CE of innermost tier; SL beyond OUTER WICK of base. Add an HTF context-zone
  emitter (D1 accumulation box as a `Level`; must emit ~565-660 on SBICARD 1D
  May-Jul-2026).
- **Data/spec need:** (a) **3/9 marks sit on unsupported TFs** — 2H (t28b), 10m
  (t28h), 30m (t29f tier). Extend `Timeframe` enum + `store/candles._DERIVED`
  with M30/H2/M10, or a nearest-TF mapping. (b) `extremes._DEFAULT_LEG_PCT=6.0`
  drops t29f's ~4% intraday legs → add per-TF override (~3.5 on H1/M15). (c) t29
  is Dec-2025 → 1h-only; its 15m/5m/1m refinement is **intrinsically
  unverifiable** on available tape.

**G3 — Node-0 context tools all 0% (`wyckoff` 0/2, `compression` 0/2,
`volume_time` 0/2).** No HTF macro box, no range-box aggregator, no
bars×height maturity meter exist. This is the TOP of the taught tree — without
it the context/directional-permission gate cannot fire.
- **Data/spec need:** D1 range-box emitter (reuse `wyckoff._event` band logic but
  *emit* the band); a `range_box` aggregator with `min_touches≥2`/edge; a maturity
  scalar. `volume_time` misses (t9b/t9c) are maturity boxes with no detector.

**G4 — `propulsion` 0/9.** 11/15 marks are slanted **projection LINES**; the
detector emits only a horizontal body-range block (no object to compare). The
block path over-fires (504 OB → 50 PRP children → 23 evidences vs 1 marked launch)
and inverts direction. Needs a line/vector primitive + a sweep-gated birth, not a
looser block.

**G5 — systemic: the EXT wire is half-built (`_CONFLUENCE §4`, highest leverage).**
One fix lifts four nodes: add `EXT_H:"below", EXT_L:"above"` to
`sweep._SIDE_BY_KIND` + an **EXT pool family** in `liquidity` (currently sources
only SWING → 5.9%) + **EXT-anchoring** in `structure` (currently grades vs fractal
SWING → 8:1 over-fire). This also unblocks G1 (premium_discount needs the master
EXT pair) and hands every node the outer-wick SL the method rests on. Second
systemic defect: the node-4 entry family (`ob_taught`/`mitigation`/`fvg`/
`propulsion`) births with **no sweep/BOS gate** → recall ~100%, precision is the
gap; gate births on an upstream sweep+structure event within N bars + `pivot_dist
_atr ≤ gate` of an EXT.

## 5. Build gate

Coverage is provably complete (467/467), so the audit clears. The **blocking**
work before doc-33 final build is detector surface, not more validation:
1. Build `premium_discount` (G1) and `htf_nest` (G2) — the two absent tools.
2. Land the EXT wire (G5) — unblocks liquidity/sweep/structure/premium_discount at once.
3. Build node-0 context detectors (G3) so a taught stack can co-fire end-to-end.
4. Fix propulsion's line primitive + all node-4 birth gates (G4/G5).
Only ~46.7% of marks are checkable on today's tape; treat the 53.3% uncheckable as
permanently unscorable until longer native 5m history exists — do not build edge
claims on them.

_source: registry.jsonl (467) · val_*.jsonl (14 files, 467) · MATRIX.md · doc40 ·
14 tool docs + _CONFLUENCE · RECOGNITION only, never edge._
