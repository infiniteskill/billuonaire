# audit_zones — ob_taught + fvg_n + propulsion2 vs the visual spec (2026-07-25)

Method: paper-trace of `ObZones._cluster`/`FvgZones`/`step_zone` vs obs_a/b/c boxes, then
step-fed recognition test (resampled marks_2026 bars straight into the classes, no pipeline)
against the annotated ground-truth boxes. Harness: `audit_zones_harness.py` (this dir).
HIT = both edges within ±0.4%; frozen = ob_taught min_disp_atr=1.0 / fvg_n min_gap_atr=0.7.

## 1. CODE-VS-SPEC (paper trace + live confirmation)

**Variant (a) — last-opposite-bodies before impulse.** Code anchors at the FIRST
counter-sign candle in the pause and boxes ALL bodies from there to the run end — not the
LAST opposite cluster. Tight pauses match exactly (t25: +0.04%/+0.26%); a pause with an
early counter candle then same-direction drift inflates the box toward the drift. PARTIAL match.

**Variant (b) — post-sweep basing cluster, wick outside.** Wick exclusion is automatic
(bodies-only box) ✓. But the basing cluster itself is usually structurally unmintable:
(i) every sub-ATR close-break during the base WIPES `_run` (min_disp gate resets instead of
tolerating), and (ii) an all-same-sign base (red drift after a gap-down sweep) has no
counter-sign candle → `k is None` → no zone under ANY min_disp. Live proof t24 DABUR 08/07:
trader's box 450.8/448.6 = gap-bar close + basing bodies; code minted 454.0/453.15 (pre-gap
tail bodies = variant (a) of the wrong cluster) and nothing else all morning — the 09:20
break (disp 0.8 < 1.0×ATR 1.15) wiped the run, the 09:25 mint-eligible break found run=[red]
only. MISMATCH.

**T13 case — sweep candle IS the run-breaker.** Trace: the sweep's up-close is itself a
continuation break → wipes the run (minting a wrong-way demand zone from the pre-sweep pause
if a red candle is present, later rescued only via the BRK/MIT flip); the next-bar engulf
then breaks DOWN against run=[sweep body] → supply OB = the sweep candle's body ALONE.
Trader: top = post-sweep body highs ✓(≈sweep close), bottom = engulf body — code EXCLUDES the
break bar by construction, so the box floats above the trader's (proximal edge too shallow).
Confirmed live at t24 09:15 (box 454.0/453.15 vs 450.8/448.6).

**fvg_n merged-gap vs single-impulse boxes.** Wick-to-wick edges ✓ (bear: flank3.high↔
flank1.low). Keep-first dedup prevents chain-merge ✓. Both in-data FVG GTs hit frozen at
the right bar (t26 12/02 10:15 +3 bars, errs −0.08/+0.17%; t1 30m 08/07 14:15 −1 bar,
−0.01/+0.04%). Extra strictness vs visual (middles must CLOSE beyond the near flank wick) —
no observed cost. MATCH. The real FVG gap is TF (G2, quantified in §2).

**step_zone 0.5×ATR vs "invalidated OB".** t1 30m FVG survived the whole July window incl.
wick pierces (second-life), dies only on the deep close-through and flips BRK/MIT/IFVG kept
with same box = "broken OB kept, relabeled" (T3 lesson). MATCH (G10 confirmed).

## 2. DETECTION ACCURACY

**Dataset coverage first (blocking finding):** 3 of the 6 requested GTs annotate Kite charts
scrolled to a period ABSENT from marks_2026 — the file's HAVELLS on those dates trades a
different price era: 2026-01-20 O1426 H1454 L1337 C1345 (T13 chart shows 1150–1224),
2026-02-10 H1390 L1367 (T12 shows 1216–1241). No day in the whole file matches the T13/T12
signatures. Untestable as dated → N/A, not detector misses. The in-data corpus was restored
with 4 supplementary boxes from the same obs set (T18, t25, t19, t1-30m; t1's 1234.0 high
08/07 and T2's 1125.5 wick 11/06 14:45 match the file exactly, proving those charts ARE this data).

| GT (obs box, born) | frozen best | err T/B | frozen | disp=0/gap=0 best | err T/B | open |
|---|---|---|---|---|---|---|
| T13 supply 1213.9/1198.8 20/01 | — | — | **N/A** (data era ≠ chart) | — | — | N/A |
| T13 demand 1159.5/1150.5 20/01 | — | — | **N/A** | — | — | N/A |
| T12 supply 1232.9/1225.8 10/02 | — | — | **N/A** | — | — | N/A |
| T2 demand 30m 1154.8/1134.7 12/06 | 1136.0/1135.1 | −1.63/+0.04 | MISS | same | same | MISS |
| t24 supply 450.8/448.6 08/07 | 446.3/446.15 | −1.00/−0.55 | MISS | 449.05/448.0 (09/07!) | −0.39/−0.13 | HIT* |
| t26 bear fvg 521.9/519.5 12/02 | 521.5/520.4 @10:15 (+3 bars) | −0.08/+0.17 | **HIT** | same | same | HIT |
| T18 demand 1214.5/1204.2 18/05 | 1246.8/1243.3 | +2.66/+3.25 | MISS | 1211.6/1208.1 @10:50 | −0.24/+0.32 | **HIT** |
| t25 ob+prop 422.1/420.3 24/06 | 422.25/421.4 | +0.04/+0.26 | **HIT** | 422.4/420.8 | +0.07/+0.12 | HIT |
| t19 supply 1394.5/1388.5 ~18/07 | 1378.2/1377.1 | −1.17/−0.82 | MISS | 1393.2/1389.4 @16/07 11:40 | −0.09/+0.06 | **HIT** |
| t1 30m fvg 1225.3/1209.5 08/07 | 1225.2/1210.0 @14:15 (−1 bar) | −0.01/+0.04 | **HIT** | same | same | HIT |

**Totals (7 testable): frozen 3/7, open 6/7. mean|errTop| 0.95%→0.38%, mean|errBot|
0.73%→0.11%.** *t24 open "hit" is edges-only, born a day late — the true 08/07 basing box is
unmintable under any config (all-red pause, §1b). t19's chart "18/07" (a Saturday) = the
file's 16/07 top (H1403); open mints 1393.2/1389.4 there, frozen gates it. Birth timing on
hits: −1..+3 bars ✓. FVG gate cost = zero on both FVG GTs (count only: 2658→1210/stock).
OB firing: frozen 2.6/day/stock, disp0 21.2/day (emission still separately gated by
require_sweep_bos + decision min_grade, so birth inflation ≠ trade inflation).

**P4 anatomy (only open-config miss):** code box = the literal candle-before-impulse body
(12/06 12:45, bottom edge +0.04% exact); trader's 30m box spans the whole 2-day down-leg
column (top 1154.8 ≈ 11/06 09:15 body top). SL edge agrees; proximal edge differs — but the
trader's executed entry (1141, nested FVG) sits near the code box. HTF leg-column boxes are
G1 territory, not a 5m cluster bug.

**Tested-and-rejected tweak:** keeping the run on a gated break (no wipe) at disp=1.0 →
blob boxes (T18 1238.7/1198.7), P4 zero births, 1.6/day. Worse. The lever is the gate
itself, not the wipe alone.

**G2 quantified (t1):** the trader's 30m gap = 15.2 pts (1225.2/1210.0, exact hit when FED
30m bars); the engine's 5m-only fvg_n best fragments there: 1215.4/1210.1, 1210.1/1206.1
(h 4–5.3) — the upper ~10 pts incl. the 1225 edge are unreachable on 5m. Multi-TF param
(G1/G2) confirmed CRIT with numbers.

## 3. ISSUES + SURGICAL TWEAKS (A/B each; no config change, no commits)

Baseline for every edge A/B: `python3 tools/derive_tradebook.py <SYMS> 4` (frozen profile),
gate per _SPEC C.3 (hi-tier net-R + 4 quadrants + monotone ladder). Recognition A/B:
`python3 dev/plan/48-VISUAL-SPEC/audit_zones_harness.py <disp> <gap>`.

**I1 CRIT — min_disp single-bar displacement wipes the pause.** Frozen kills recognition of
the taught post-sweep OBs (3/7 vs 6/7). Tweak: demote displacement to a GRADE (birth
ungated, `meta["disp_atr"]` graded downstream like pivot_dist_atr — TUNE's own "dist as
GRADE not filter" law applied to disp). A/B:
`jq '.detectors.params.ob_taught.min_disp_atr=0' runs/validate/taught_profile/config.json > /tmp/ab_disp0.json && DERIVE_PROFILE=/tmp/ab_disp0.json DERIVE_DATA=data/wide python3 tools/derive_tradebook.py <SYMS> 4` vs baseline.

**I2 HIGH — counter-pressure requirement forbids monotone basing clusters.** t24's real box
can never mint (run of same-sign bodies → k=None). Tweak: `ObZones._cluster` — when
`k is None and len(self._run) >= 2`, take `k=0` behind new param `mono_run` (default off →
zero behavior change). A/B: enable in a scratch profile copy, same derive_tradebook pair;
recognition via harness (expect t24 08/07 morning box to appear).

**I3 MED — break bar excluded from the box.** T13/t24: trader's proximal edge = the impulse
candle's close; code stops at the pause bodies. Tweak: param `include_break_bar` (off) —
on mint, extend the box with the break bar's body toward price only (proximal edge). A/B:
scratch profile + derive_tradebook pair; watch entry-fill rate and SL unchanged (far edge untouched).

**I4 MED — propulsion2 parent-universe drift (config bug).** `propulsion2` builds
`ObZones(depth)` with min_disp=0 while frozen ob_taught runs 1.0 → parent universes diverge
358 vs 2919 births (8.2×, HAVELLS 5m): children arm off parents ob_taught never journals,
silently breaking the +43.4pp parent-link premise. Tweak: add `"min_disp_atr": 0.0` to
propulsion2 `_DEFAULTS`, pass to ObZones, mirror ob_taught's value in profile. A/B:
`jq '.detectors.params.propulsion2={"min_disp_atr":1.0}' ... > /tmp/ab_prp.json` + derive_tradebook pair.

**I5 — no change:** fvg_n geometry+dedup+min_gap (both GTs hit), step_zone break-depth law,
BRK/MIT flip. **G1/G2 multi-TF** remains the top fidelity item (P4 + t1 both resolve on 30m).

## 4. Repro

Harness `dev/plan/48-VISUAL-SPEC/audit_zones_harness.py` (frozen `1.0 0.7`, open `0 0`);
traces in session scratchpad (audit2/audit3.py) — key traces reproduced in §1/§2.
