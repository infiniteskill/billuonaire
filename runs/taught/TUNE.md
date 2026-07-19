# TUNE — armored parameter sweep of the surviving taught tools

2026-07-19. Data: `runs/artifacts-data/l4_h1.parquet` (138 NSE syms × H1, 2023-08 → 2026-07),
splice-guarded. Scripts: scratchpad `tune_lib.py` / `tune_sweep.py` / `tune_po3.py` /
`tune_report.py` / `tune_labels.py` (reuse `dev/research/{tob_lib,ext_zigzag}` zigzag/ATR and the
ts2 respect-race + time-local path-clean matched-null method verbatim). Episode parquets:
`tune_ep_{A..G}.parquet`, `tune_full.parquet`, `tune_po3.parquet`, per-stage CSVs `tune_res_*.csv`,
frozen knobs `tune_frozen.json`.

**THE ARMOR.** TRAIN = temporal third 1 ∩ crc32(sym)%2==0 only (touch-time attribution for
episode stages, birth-time for detected counts). All knob selection on train; configs then frozen
and validated on the 5 untouched cells (t1/h1, t2/h0, t2/h1, t3/h0, t3/h1). Objective =
DETECTION quality: respect-lift vs path-clean null (≥1×ATR favorable before adverse at first
armed retest of the proximal edge, 70-bar window, tie=adverse), never netR. **48 distinct configs
examined** (A:9, B:12, C:9, D:3, E:6, F:3, G:2, H:4; 62 config-evaluations counting the
re-scores of D–G after the OB re-freeze, see caveat 2). Overfit flag = validation lift < 70% of
train lift. Funnel stages per the ask: detected → %retested → %respected(1×ATR) → %reached-2×ATR
→ %violated-first (close through far edge before the favorable 1×ATR).

**USER-SPECIFIED MERGE RULE (applied throughout, incl. the composite):** continuous/overlapping
gaps from the SAME displacement burst (same direction, candle windows overlapping or contiguous)
are merged into ONE FVG, box = union of the fragments. Stack counting de-dups by structure id
(merged burst = one member; a propulsion child shares its parent's id) — fragments/children can
never inflate a stack. Consequences quantified in §FVG-N and §Stacking.

Machinery notes: zone death gates episodes in all configs (a zone closed-through ≥D×ATR before
its retest offers no episode — slightly stricter than ZONES's first_touch, so counts are not
1:1 comparable with ZONES.md); flips (IFVG/BRK/MIT) are born at the kill bar under the frozen
death law; t3-born zones have less time to be retested (mild %retested censoring in t3 cells).

## Frozen configs (chosen on train)

| tool | knobs swept | chosen | why |
|---|---|---|---|
| zigzag extremes | leg floor {3.5,4.7,6.0}% × band {wick,0.5×ATR} | **6.0% + wick band** | OB-anchor lift monotone in floor: +1.97/+2.28/+2.80 (t 4.6→5.1). Band: lift head-to-head underpowered (t<1, sign flips by floor); wick band beats ATR band on violated-first at EVERY floor (35-37% vs 44-45%) and won STRUCT's paired 6/6 — wick kept as anchor geometry |
| taught-OB | box {full,bodies} × join {0,.25×ATR} × maxdist {≤2,≤6,any} | **bodies-only box, join 0 (no-op), dist any** | bodies box wins at every dist cap (+3.46..+3.83 vs +2.80..+1.69 full). Join tolerance is a PROVABLE no-op: a bar gapping fully beyond the box always also closes beyond it, and close-beyond already ends the cluster (identical numbers, 0/12 differ). Dist cap: ≤2 train +3.83 vs any +3.46 = statistical tie (Δ0.37pp); tie broken FOR recall (4.8× zones, t 6.5 vs 3.0) + user-label recovery (§labels) — dist≤2 stays in the composite as a GRADE, not a detection filter |
| FVG-N (merged) | burst span mmax {1,3,6} middles × min gap {0,.1,.25}×ATR | **mmax 6, min gap 0** | best train lift +2.21 (vs +2.14 for strict-3 q=.25 — near-tie); wide bursts + no size floor consolidate into the fewest, cleanest corridors: violated-first 23% vs 35-38% for strict-3 variants |
| break-depth law | kill zone on close-through {any, ≥0.5, ≥1.0}×ATR | **≥0.5×ATR** | train lift +3.06 vs +2.84 (any) / +2.88 (1.0); +22% more episodes than any-depth. Second-life episodes (retests after a shallow violation that used to kill the zone): train +2.20, **validation +2.69 (t 10.0), all 5 cells +** — shallow breaks genuinely shouldn't kill zones |
| overlap stacking | merge tol {exact,.25×ATR} × min stack {2,3,4} | **exact overlap, nst≥4 (dedup)** | best tier lift train +3.26; dedup ladder finally monotone on train (+0.84/+2.18/+2.74/+3.26 for 1/2/3/4+) |
| sweep-aligned birth | window {2,3,5} bars | **NOT SELECTABLE** (W=2 kept as diagnostic only) | train underpowered and sign-unstable: W=2 +5.09 (n=93), W=3 −1.90, W=5 −0.11. Validation shows +3.3..+3.8 at all windows (n 656-1349) vs +2.56 baseline — weakly encouraging but no train-selected knob exists; excluded from composite gating |
| PO3 gate | body {.35,.5} × wick {.5,.6} | **body<0.5, wick>0.5** | train lift +1.91 (D1 1×ATR race, ts1 forward-window null) vs taught .35/.5 +1.34. **OVERFIT flag on validation** (see below) |
| entry reference | edge vs edge+0.1×ATR inside | **edge** | inset +2.74 vs edge +2.80 (train) — no gain from entering deeper; consistent with ZONES P4 (the working level is the edge). CE not tested (dead) |
| propulsion | no free knobs; parent linkage mandatory | **parent-linked only** | orphans validate as anti-signal again: −5.81 lift (t −2.2), 4/5 cells negative |

## Per-tool funnels — train (t1∩h0) vs validation (5 untouched cells), frozen configs

det = zones; ret% = zones ever armed-retested; resp/2R/blow = % of episodes; lift = paired
respect − matched-null (pp); cells = per-cell lift t1h1/t2h0/t2h1/t3h0/t3h1.

| tool | cell | det | ret% | eps | resp | 2R | viol-first | null | lift | t | cells |
|---|---|---|---|---|---|---|---|---|---|---|---|
| OB | TR | 6,906 | 88.1 | 6,882 | 61.1 | 37.5 | 29.1 | 57.7 | **+3.13** | 6.3 | |
| | VAL | 37,995 | 87.2 | 38,070 | 58.9 | 35.7 | 30.7 | 56.2 | **+2.50** | 11.3 | +2.1 +1.8 +2.8 +2.9 +2.7 |
| FVG-N | TR | 12,827 | 44.2 | 6,249 | 56.3 | 33.1 | 28.0 | 53.8 | **+2.43** | 4.9 | |
| | VAL | 63,713 | 45.1 | 31,993 | 56.6 | 32.9 | 27.6 | 54.5 | **+1.96** | 8.6 | +2.3 +1.9 +2.0 +2.6 +0.9 |
| zigzag band | TR | 933 | 82.2 | 875 | 57.5 | 34.3 | 34.9 | 57.3 | −0.25 | −0.2 | |
| | VAL | 6,028 | 79.9 | 5,657 | 57.5 | 35.6 | 39.6 | 57.3 | −0.26 | −0.4 | −1.6 −1.1 −0.3 +0.2 +1.3 |
| PRP live-par | TR | 994 | 60.8 | 658 | 60.9 | 37.1 | 26.4 | 55.0 | **+6.28** | 4.1 | |
| | VAL | 5,584 | 59.9 | 3,695 | 58.9 | 36.5 | 23.8 | 54.9 | **+3.83** | 5.7 | +1.7 +2.3 +4.7 +4.8 +5.4 ⚠ |
| PRP orphan | VAL | 147 | 100 | 158 | 34.8 | 20.9 | 55.7 | 41.3 | **−5.81** | −2.2 | +1.1 −8.2 −7.6 −5.5 −5.9 |
| IFVG | TR | 10,796 | 91.3 | 11,203 | 60.2 | 36.7 | 31.0 | 57.0 | +2.99 | 7.8 | |
| | VAL | 60,390 | 91.2 | 63,339 | 59.2 | 35.8 | 30.7 | 56.3 | **+2.77** | 16.8 | +2.8 +2.4 +3.6 +2.6 +2.6 |
| BRK | TR | 2,751 | 89.6 | 2,775 | 61.1 | 35.0 | 31.0 | 56.1 | +4.60 | 5.8 | |
| | VAL | 20,182 | 89.6 | 20,850 | 58.8 | 35.3 | 31.7 | 55.8 | +2.88 | 10.1 | +3.6 +2.6 +2.8 +2.5 +3.3 ⚠ |
| MIT | TR | 1,952 | 90.0 | 1,999 | 57.0 | 34.7 | 33.0 | 54.7 | +2.10 | 2.3 | |
| | VAL | 12,875 | 90.0 | 13,329 | 58.6 | 34.2 | 32.7 | 56.0 | +2.41 | 6.7 | +3.0 +2.3 +2.2 +3.2 +1.5 |
| ALL constructive | TR | 36,243 | 73.0 | 29,797 | 59.4 | 35.8 | 30.0 | 56.2 | **+3.06** | 13.0 | |
| | VAL | 200,847 | 74.7 | 171,434 | 58.5 | 35.1 | 30.3 | 55.8 | **+2.56** | 25.4 | +2.6 +2.2 +2.9 +2.7 +2.4 |
| 2nd-life (D=0.5) | TR | 2,881 | — | 3,349 | 57.0 | 33.8 | 39.0 | 54.5 | +2.20 | 3.3 | |
| | VAL | 18,750 | — | 21,900 | 57.2 | 34.9 | 37.5 | 54.4 | **+2.69** | 10.0 | +1.8 +1.7 +3.2 +3.3 +3.2 |
| PO3 (D1) | TR | 5,087 | n/a | 5,087 | 51.9 | 36.1 | 48.1* | 50.0 | +1.91 | — | |
| | VAL | 24,954 | n/a | 24,954 | 50.2 | — | — | 49.5 | +0.73 | — | +1.5 −0.1 +2.4 −0.4 +0.5 ⚠⚠ |

*PO3 has no retest stage (next-candle race funnel); viol-first = adverse-1×ATR-first.
BRK vs MIT on validation: +2.88 vs +2.41 — the sweep-split ranking stays dead (ZONES P2 stands).

### Per-config train funnels (selection tables, condensed)

**A zigzag** (band zones; OB-check rows = OB tool at each floor):
| cfg | det | ret% | resp | viol | lift | t |
|---|---|---|---|---|---|---|
| 3.5% wick | 2,990 | 90.1 | 58.7 | 37.2 | +0.42 | 0.5 |
| 3.5% atr | 1,741 | 89.0 | 57.4 | 45.1 | −1.08 | −0.9 |
| 4.7% wick | 1,608 | 86.3 | 58.5 | 36.4 | +1.18 | 0.9 |
| 4.7% atr | 897 | 84.2 | 58.2 | 44.5 | +1.26 | 0.7 |
| 6.0% wick | 933 | 82.2 | 57.4 | 35.3 | −1.17 | −0.6 |
| 6.0% atr | 502 | 78.7 | 57.7 | 44.3 | +0.62 | 0.2 |
| OB@3.5% | 10,735 | 84.6 | 59.8 | 23.2 | +1.97 | 4.6 |
| OB@4.7% | 8,588 | 84.9 | 60.6 | 22.1 | +2.28 | 4.7 |
| OB@6.0% | 6,938 | 84.6 | 61.0 | 21.4 | **+2.80** | 5.1 |

**B taught-OB** (join collapsed — no-op, 6 distinct rows):
| box | maxd | det | ret% | resp | viol | lift | t |
|---|---|---|---|---|---|---|---|
| full | ≤2 | 1,658 | 89.0 | 60.3 | 16.1 | +1.69 | 1.4 |
| full | ≤6 | 3,759 | 87.8 | 61.3 | 19.9 | +2.44 | 3.1 |
| full | any | 6,938 | 84.6 | 61.0 | 21.4 | +2.80 | 5.1 |
| body | ≤2 | 1,446 | 88.9 | 63.8 | 20.1 | **+3.83** | 3.0 |
| body | ≤6 | 3,585 | 88.8 | 62.5 | 24.9 | +3.61 | 4.6 |
| body | any | 6,907 | 86.9 | 61.6 | 27.7 | **+3.46** | 6.5 |

**C FVG-N** (merged bursts):
| mmax | q×ATR | det | ret% | resp | viol | lift | t |
|---|---|---|---|---|---|---|---|
| 1 | 0 | 16,855 | 68.4 | 55.3 | 38.3 | +1.77 | 5.1 |
| 1 | .10 | 14,915 | 70.8 | 55.6 | 37.0 | +1.99 | 5.5 |
| 1 | .25 | 12,026 | 74.3 | 56.4 | 34.7 | +2.14 | 5.3 |
| 3 | 0/.10/.25 | 13-16k | 50-58 | 55.4-55.7 | 30 | +1.13..+1.37 | ~3 |
| 6 | 0 | 12,866 | 36.0 | 56.5 | 23.4 | **+2.21** | 3.8 |
| 6 | .10/.25 | 11-12k | 38-42 | 56.2 | 23 | +1.73/+1.78 | 3.0 |

**D break-depth** (all constructive tools): any → +2.84 (23,961 eps) | **0.5 → +3.06 (29,797)** |
1.0 → +2.88 (33,625). **E/F/G** tables in §Stacking / §Sweep / frozen table above.

## FVG-N recall under the merge rule (user correction #1)

Full universe, frozen floor: strict-3 fragments 161,475 → N-burst fragments 875,237 (**+442%
fragment count**); after same-burst merging: strict-3 102,582 → FVG-N **76,438 merged structures
(−25%)**. The ZONES "+138% recall" figure was an artifact of fragment counting: the N-candle
generalization finds almost no new structures — it consolidates and widens the corridors strict-3
already saw (fewer, bigger boxes; equal per-episode quality: train lift +2.21 vs +2.14). Detection
coverage in price×time is what grows, not structure count.

## Stacking under structure de-dup (user correction #2)

Old fragment counting made the grade meaningless: nso≥4 captured 99.1% of validation episodes
(168,070 of 169,602) — "deep stack" was near-universal, its tier lift +2.58 ≈ the unconditional
+2.56. Under dedup counting the grade discriminates again and the law SURVIVES:

| tier (dedup) | TR n | TR lift | VAL n | VAL resp | VAL lift | cells |
|---|---|---|---|---|---|---|
| nst=1 | 873 | +0.84 | 2,184 | 66.6 | +1.88 | +2.5 +1.1 +0.3 +1.5 +3.1 |
| nst=2 | 2,147 | +2.18 | 6,395 | 57.7 | +0.72 | mixed |
| nst=3 | 2,779 | +2.74 | 9,716 | 57.8 | +0.96 | mixed |
| nst≥4 | 23,660 | +3.26 | 151,307 | 58.3 | **+2.75** | +2.8 +2.3 +3.2 +3.0 +2.5 |
| nst≥6 | 17,419 | +3.65 | 124,444 | 58.4 | **+2.99** | +3.1 +2.6 +3.4 +3.3 +2.6 |

Plainly: the deep-stack lift was NOT same-burst inflation — after removing fragment/child
double-counting the 4+ tier still clears the low tiers in all 5 validation cells and the
tail stays graded (≥6 > ≥4). What WAS inflation is the claim that most zones are deeply stacked;
with honest counting the low tiers (1-3) carry ~0.7-1.9pp and are noisy, exactly as ZONES found.

## Sweep-aligned birth (not selectable)

Train: W=2 +5.09 (n=93) / W=3 −1.90 (n=143) / W=5 −0.11 (n=224) — no window clears noise, sign
unstable. Validation diagnostic: +3.38 / +3.78 / +3.34 (n 656/845/1,349) vs +2.56 unconditional.
A real increment may exist (~+1pp) but the train cell cannot select a window; left out of the
composite gates, revisit with more data or at lower TF.

## User-label validation (HDFCBANK, hand-drawn 30m, verified at H1, ±1.5% price / ±4d)

FVG labels: **5/5 FOUND** by merged FVG-N (May 05 / May 14 / May 22 / Jul 06 / Jul 08-09 windows;
verified by orchestrator). OB/PRP/BRK labels vs frozen config:

| label | spec | verdict | detail |
|---|---|---|---|
| (f) | bear OB 1005-1012.5, ~21-22 Oct 25 | **FOUND** | OB [1010.5-1018.6] born 23 Oct, dist 0.31 |
| (g) | bull OB 910-920, ~27-28 Jan 26 | **MISS at 6.0% floor** | at the taught 4.7% floor it IS found: OB [911.4-918.6] born 23 Jan, dist 0.93 — the 6% zigzag has no anchor leg there. Known cost of the tuned floor |
| (h) | bull OB 946-954, ~30 Sep-1 Oct 25 | **FOUND** | OB [948.6-952.5] born 29 Sep, dist 1.88 |
| (i) | bull OB 975-980, ~16-17 Oct 25 | **PARTIAL** | detected as flip-zone [979.2-988.7] born 16 Oct (full-box view), not as a fresh OB; nearest fresh OB same day is 993.6 |
| (j) | PRP 982-990, ~20 Oct 25, on top of (i) | **FOUND + parent-link verified** | PRP [987.0-997.8] born 17 Oct, parent OB [970.0-989.0] born 07 Oct — the parent box contains label (i)'s band, so (j)→(i) pairing holds in substance. NOTE: under the earlier maxd=2 cap this label was LOST (parent dist 6.17) — decisive evidence for freezing maxd=any |
| (k) | BREAKER 969.5-974.5, born 18-19 Sep 25, retest 22-23 Sep → down | **PARTIAL** | box found almost exactly: flip-zone [969.2-974.3] born 18 Sep — but classified MIT with direction +1 (support), opposite the user's bearish continuation read. Box/date exact, type/direction disagree; flip-direction grammar needs a look |

Score: 3 FOUND, 2 PARTIAL (box-level exact, type/direction disagreements), 1 MISS (recovered at
the taught floor). Mitigation defn restated by user ("breaker with the higher low", no-break
variant) matches the implemented sweep-test split — no change; note validation says BRK ≈ MIT
anyway.

## Composite final shape (tuned recognizer, validation cells only)

Grade components per episode: stack (nst-dedup ≥4) + parent-ok (PRP live / non-PRP) + pivot-near
(dist ≤2 ATR) + sweep-aligned (W=2, diagnostic). Break-depth-alive is structural (episodes only
exist while the zone is alive under D=0.5).

| grade | VAL n | resp | 2R | viol-first | lift | cells |
|---|---|---|---|---|---|---|
| 1 | 17,367 | 58.9 | 35.8 | 42.0 | +0.97 | mixed |
| 2 | 134,486 | 58.4 | 34.7 | 29.8 | **+2.81** | all + |
| 3 | 17,308 | 58.1 | 34.4 | 23.8 | +2.23 | all + |
| 4 | 430 | 57.7 | 35.4 | 24.0 | +1.84 | mixed |
| **top tier g≥2** | **152,224** | **58.3** | **34.7** | **29.1** | **+2.74 (t 25.4)** | **+2.7 +2.3 +3.2 +3.0 +2.5** |
| refined g≥3 | 17,738 | 58.1 | 34.5 | 23.8 | +2.22 (t 6.6) ⚠ | +2.8 +1.2 +2.6 +2.9 +1.8 |

Trades/quarter across 138 syms (validation episodes / 9.77 full-universe quarter-equivalents):
**g≥2 ≈ 15,600/quarter** (~113/sym/quarter — recognition events, not trades); g≥3 ≈ 1,800/quarter
(~13/sym/quarter). Higher grades buy cleaner funnels (viol-first 29.1→23.8%) but NOT more lift on
validation — the train monotonicity of grades 3-4 (+4.80/+8.48) collapses out of sample (+2.23/
+1.84): grade refinement beyond deep-stack is at least partly overfit. The dependable shape is:
constructive zone, alive under the 0.5×ATR break-depth law, deep de-duplicated stack — +2.7pp
respect over matched null at 58.3% absolute, in every validation cell, t≈25.

## Overfit flags & honest caveats

1. **⚠⚠ PO3 gate**: train +1.91 → validation +0.73 (38% retained, 2/5 cells negative). Chosen and
   taught variants both degrade; the D1 wick-signature edge is regime-fragile. Keep only as a
   weak tiebreak, never a gate.
2. **OB maxdist re-freeze**: the auto-selection took dist≤2 (train +3.83 vs +3.46, a statistical
   tie); it was re-frozen to dist=any AFTER inspecting user labels (the cap killed label (j)'s
   parent) — a documented deviation from pure train-argmax, tie-broken by recall + label
   fidelity, with dist≤2 retained as a composite grade component. Stages D–G re-run after the
   re-freeze (same grids, same winners).
3. **⚠ PRP** (61% retained, all cells +) and **⚠ BRK** (63%, all cells +): magnitudes shrink
   out of train but signs hold everywhere; PRP stays the strongest single tool (+3.83).
4. **⚠ g≥3 composite tier** (46% retained): see composite section.
5. Zigzag band zones are dead as an organ (−0.26 validation) — the band knob is anchor geometry
   only; rejection blocks stay falsified (not resurrected).
6. The 6.0% leg floor costs user-label (g) (found at 4.7%). If label fidelity ever outranks
   train lift, 4.7% is the fallback (train OB lift +2.28 vs +2.80).
7. Funnel %retested in t3 cells is mildly censored (zones born late have less time to retest).
8. Detection-grade magnitudes throughout (+2-4pp on a ~56% null); nothing here touches the
   standing economics verdicts (H1GRID/TAUGHT_OB: recognition real, net ≈ 0).
