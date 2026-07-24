# HANDOFF → FABLE: how we got win% 30 → 68, step by step (2026-07-24)

Purpose: a chronological operations log so the next phase (Fable) can RE-CHECK each code change and
RE-VALIDATE each research finding independently. Every step has: what · why · code/commit · result ·
**RE-VERIFY command**. All commands: `cd <repo>; source ~/miniconda3/etc/profile.d/conda.sh; conda
activate base` first (pandas). 45 commits today — `git log --since="2026-07-24" --reverse --oneline`.

## THE ARC (what drove 30 → 68)
- **Start:** ungated system ~28-30% win, net ≈ −3R (LOSS). Detectors individually forward-negative.
- **+ GRADING** (select grade≥5 conjunction): 28% → ~49% win, net → +6.13R (intrabar).
- **+ INTRADAY squareoff** (eod mode): 49% → **68%** win (cuts multi-day losers at 15:10).
- **+ DEDUP** (honesty): raw was ~40% clustering-inflated → honest +6-7R executable.
- **+ min-RR≥3** (drop tinyRR noise): the one shipped tune; window-robustifier.
- **Net result:** grade≥5 INTRADAY = 68% hit, 1:4.7 RR, **+7.5R/trade**, breakeven only 17.5%.
The win% jump is SELECTION (grade + intraday), NOT accuracy tuning. Detectors add ZERO geometric edge.

## THE 3 TOOLS (re-run/validate anything with these)
1. `tools/derive_tradebook.py <SYM,...> [min_grade]` — honest sim: runs wired taught profile over 1m,
   decide()-take = a trade, forward-sims gap-aware, applies rupee costs, reports net-R by grade + holdout.
   Env: `DERIVE_DATA` (data dir), `DERIVE_MIN_RR` (RR gate), `DERIVE_JOURNAL`, `DERIVE_TB_OUT` (persist CSV).
2. `tools/derive_parallel.py <SYM,...> <nshards> <out.csv>` — shards the above across cores (~4-8x),
   verified == serial. Same env. Use for big tapes.
3. `tools/ab_tradebook.py <tradebook.csv> <filter> [arg]` — offline gate A/B on a persisted tradebook
   (dedup default, recomputes global holdout quads). Filters: none/no_blind/bhit_gt0/min_rr/dir/regime/
   nest_ge/strength_ge. THE GATE: a change ships only if hi≥5 net-R holds/improves AND all 4 quads +.

## STEP-BY-STEP LOG (phase · commit · result · RE-VERIFY)

### PHASE A — REFINE LOOP: build the graded edge (iter 2-8)
- ob_taught gate_mode='sweep' (range-fade fires on sweep) `f29a6a5,2be0ee8`: ob_taught 0→689 fires.
- derived-tradebook sim `0392902`: user's idea (derive winners+losers from tools) — honest sim built.
- grade enrichment (OTE-depth + phase) `24b34d7`: grade still non-monotone → needed nest_depth.
- **htf_nest EXT-band parents → nest_depth SEPARATES winners** `24dd07b`: FIRST discrimination.
- honest edge verdict `81fdc6b`: graded tier monotone −9R→+6R after real costs.
- **40-stock robustness** `b89d8fe`: high-tier +4.57R, ALL 4 holdout quadrants +.
- 6 precision tunes (ob disp gate, min_depth=2, p/d edge-trigger, sweep min_touches, fvg_n min_gap, liq
  gate) `5e9b840,8d7ba58,137ddf9,839836a`: high-tier +4.57→+5.40→**+6.13R**, win 37→45→49%, ungated FLIPS +0.52R.
- RE-VERIFY: `python3 tools/derive_tradebook.py <40 syms> 1` → intrabar hi tier should be ~+6.13R/49%.

### PHASE B — PRODUCTION PARITY (does it survive real execution?)
- ChatGPT code-audit verified `26e3872`: 9 CONFIRMED/3 PARTIAL/0 false — none contaminate the edge.
- m5_close stop mode `bb00d31,6760965`: edge survives M5-close stops +6.13→+5.80R (−5%).
- F1 wire decide() into pipeline `d8bb8c9,2d267e9`: engine=taught toggle, end-to-end.
- eod intraday-exit `3b0968b,1d0fe3f`: **BETTER intraday — +6.53R win 67% under 15:10 squareoff**.
- RE-VERIFY: derive_tradebook runs all 3 modes (intrabar/m5_close/eod); compare to these numbers.

### PHASE C — STUDIES (understand WHY it works)
- multi-regime fetcher + 2024-Q4 `9b28481`: jugaad data pull (tools/fetch_jugaad.py, conda base).
- HAVELLS deep-dive (5 agents) `be6a6fb`: htf_nest mis-anchors (B1); T1 OTE-gate.
- HUL replication `e0b56ba`: split along REGIME; T1 falsified as universal.
- **40-STOCK deep study** `8a9a86e`: detectors AUC 0.49 (zero geom edge); b_hit sole separator (0.76) but
  ANTI-CALIBRATED; htf_nest anchor bug; 3 structural tunes. dev/plan/47-40STOCK/_SYNTHESIS.md.
- RE-VERIFY: read dev/plan/47-40STOCK/*.md; every headline number is a pandas one-liner on
  runs/validate/study40_2026/evidence.parquet (schema in _SYNTHESIS.md).

### PHASE D — CROSS-REGIME (does it generalize?)
- **2024-Q4 bear holdout PASSES** `791474f`: frozen config, unseen bear tape, hi-tier +8.20R/62% (raw).
- **EDGE-PRESERVE rethink** `68a2309`: two studies are different FRAMES (symmetric vs graded); b_hit
  INVERTS (symmetric edge in low tail, large-R net-excursion monotone in HIGH b_hit) → "select low-b_hit"
  is a KILLER. dev/plan/47-40STOCK/_RETHINK-EDGE-SAFE.md.
- RE-VERIFY b_hit inversion: group study40 parquet by b_hit bin, show win% (symmetric) vs mfe-mae (large-R).

### PHASE E — TOOLING + DEDUP (make it honest + fast)
- Z1 instrument tradebook `0dcff29`; ab_tradebook harness `5b80688,c61c19d`; derive_parallel `b807f92`.
- **BULL test (Z2) PASSES + DEDUP correction** `ce93068`: raw +8R was ~40% clustering-inflated (same zone
  re-fires 2-3x). Deduped honest edge ~+6.5-7.5R. dev/plan/47-40STOCK/_BULL-AND-DEDUP.md.
- **TRIPTYCH** `17d6ab1`: deduped, ALL 12 quad-regime cells + (3 regimes).
- RE-VERIFY: `python3 tools/ab_tradebook.py runs/validate/tradebook_2026.csv none` → deduped hi≥5 quads.

### PHASE F — min-RR (the one shipped tune)
- gate in decide() (default-off) `76583e7`: implemented==A/B exactly (re-derive DERIVE_MIN_RR=3 reproduces filter).
- **SHIPPED to production** `eb07f3e`: taught_profile decision.min_rr=3, pipeline wired; window-ROBUSTIFIER
  (6-month context +3.44→+7.21R). dev/plan/47-40STOCK/_Z3-CONTEXT-FINDING.md.
- RE-VERIFY: `python3 tools/ab_tradebook.py runs/validate/tradebook_2026.csv min_rr 3` → SHIP-CANDIDATE.

### PHASE G — FAITHFULNESS Z3 (is it the user's method?)
- Z3 `06977d0,2830709`: structural=tautological, co-location 20/32=chance → UNDECIDABLE (red-teamed).
- **Z3 deeper** `81de741`: marks ARE dated (ytrades.json month/day, mostly 2026); premium_discount
  DIRECTION is lookback-window-sensitive (17-day→1221 SHORT +27.6R; 6-month→LONG). Faithfulness is
  CONTEXT-DEPENDENT — user's shorts fire as winners in LOCAL context.
- RE-VERIFY: temporal co-location — mark date = 2026-{month}-{day}, match tradebook_2026 by sym+dir+price.

### PHASE H — REJECTED tunes (the gate protecting the edge — STUDY THESE)
- **B1 anchor fix** (emit_live) `e44bb19`: net-R +6.94→+4.78R, didn't promote 1221. REVERTED. `_B1-REJECTED.md`.
- local-window p/d `0d966cf`: inconclusive small sample. UNPROVEN, not shipped.
- edge-by-regime `a518229`: p/d best in ranging (2026 RANGE +9.51R) but edge is a CHAMELEON (dominant regime).
- **mode-switch gate REJECTED** `397450f`: hurts bull. THE META-FINDING: 3 fixes rejected → edge at a
  ROBUST OPTIMUM; symmetric-frame findings are DIAGNOSTIC not a mandate. `_MODE-SWITCH-REJECTED.md`.
- LESSON FOR FABLE: every tool/gate "improvement" MUST pass ab_tradebook (hi≥5 net-R holds + quads +).
  Most plausible fixes HURT the already-optimal edge. Optimize NET-R, never win-rate/accuracy.

### PHASE I — VALIDATION (is it robust?)
- **WALK-FORWARD** `673eaff`: 19/19 sequential time windows POSITIVE (3 tapes, ~14 months). `_WALKFORWARD.md`.
- STATE-OF-PROJECT capstone `793105f`: full validation stack + paper-pilot spec. `_STATE-OF-PROJECT.md`.
- RE-VERIFY: split any tradebook's hi≥5 eod by sequential ts buckets → each window's net-R.

## THE FINAL STATUS (grade≥5, deduped, min-RR, pooled 3 tapes)
| frame | hit% | RR | net/trade | breakeven | verdict |
|---|---|---|---|---|---|
| INTRADAY (eod) | 68.4% | 1:4.7 | +7.5R | 17.5% | PROFITABLE |
| SWING (multi-day) | 51.6% | 1:7.2 | +6.8R | 12.2% | PROFITABLE |

## HOW FABLE SHOULD WORK (the discipline that got us here)
1. Two goals, keep separate: DETECTION FIDELITY (tools find what they claim → faithfulness) vs EDGE
   (graded net-R → money). They are DECOUPLED (proven). Know which you tune.
2. Every change → A/B on the graded frame via ab_tradebook → ship ONLY if hi≥5 net-R holds/improves AND
   all 4 quads + AND walk-forward windows stay +. Else REJECT + revert (like B1).
3. Optimize NET-R, never win-rate (high-prob setups had NEGATIVE edge — b_hit anti-calibration).
4. Honesty > tuning: the biggest win today was DEDUP (a correction), not a tune. Get measurement right first.
5. The edge is at a robust optimum. Correctness/fidelity fixes welcome; accuracy-chasing erodes it.
