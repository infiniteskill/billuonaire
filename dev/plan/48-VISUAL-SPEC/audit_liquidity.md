# audit_liquidity — liquidity + sweep + LevelEngine sweep states vs the taught visual language (2026-07-25)

Method: 1m marks_2026 -> real pipeline pieces (CandleStore M5 loop -> LevelEngine -> extremes/swings/
liquidity/sweep in taught_profile order+params, faithful session-end prune incl. `_CARRY`). Windows:
HAVELLS 01-01..01-23 / 01-27..02-27 / 06-08..07-17, DABUR 06-15..07-10. Instrumented: level births,
transitions, EQ zone/touch updates, EQ group members (monkeypatched `_create_eq`), sweep Evidence.
Branch stage2 (poke_ts/poke_price meta live). Harness: scratchpad `audit_harness.py` / `audit_members.py`.

## 1. CODE-VS-SPEC

| # | visual truth | code truth | verdict |
|---|---|---|---|
| L1 | line at WICK price of 2+ pivots | EQ clusters on `_mid(zone)`: SWING zone=wick±tick (mid≈wick, ok) but EXT zone=[body-top..wick] band -> mid sits half-band below the wick; two pivots with EQUAL WICKS but different body-tops miss the 0.001 tolerance; EQ zone = min-max UNION of member zones (band up to 4.2pt seen: EQL [1125.50,1129.70]) vs the user's single line | **DIVERGES** |
| L2 | 2-touch lines valid | `touches` at birth = group size INCLUDING same-pivot TF echoes: **74/86 (86%) of DABUR EQ groups are ONE physical pivot seen on 5m+15m** (e.g. the 451.00 line group = 5m@07-02T09:25 + 15m@07-02T09:15). sweep `min_touches=3` then blocks 69% of real EQ sweeps (82/119 across windows) and 96% of swing sweeps (300/312); only the `_DAILY_WEEKLY` exemption lets taught sweeps signal (via a coincident PDH/PWH) | **DIVERGES** |
| L3 | lines live for weeks (t17/t27) | `_pool_strength` EQ recency zeroes at 48h -> weeks-old line strength caps at touches/5*0.7 (=0.28 for a 2-touch line; sweep q≈0.47) | diverges (weight only) |
| L4 | segment ENDS at sweep candle; zone at origin becomes breaker | SWEPT->RECLAIMED->INVERTED matches conceptually (verified: EQH-1228.90 INVERTED exactly on the 1234 extreme bar = taught breaker seed) | **MATCH** |
| L5 | sweep can take hours-days (spike day 1, collapse day 2: t24, T12 09-10/02) | LevelEngine is fed M5 only; PENDING_BREAK resolves in 2 M5 closes, reclaim window 3 -> any excursion holding >10-15min beyond the line goes DEAD (break), never SWEPT | **DIVERGES** (root cause of the DABUR miss) |
| L6 | dead line stays dead; new lines can form later at same price | SWEPT/RECLAIMED EQ are non-terminal and in `_CARRY` -> carry forever AND `_create_eq`'s overlap check treats them as "existing", blocking new pool birth at that price; meanwhile EXT/SWING sources are pruned nightly (not in `_CARRY`) but extremes RE-CREATES all pivots from recompute -> dead EXT/EQ resurrect each open and re-die (EXT_H DEAD x169 in 25 sessions HAV-Feb, x63 DABUR; same EQ id logs ACT->DEAD 6 days running) | **BUG-class** |

## 2. DETECTION ACCURACY (ground truths)

Dataset reality check: marks_2026 HAVELLS trades 1420-1455 on 19-20/01, 1250-1442 in Feb, 1414-1439 on
17/02 — the T12/T13/T16 charts are Kite historical-scroll from a prior year; those 3 truths are NOT in
this dataset. The t1 July episode IS (07-08/07/2026 matches to ~0.3pt), and is the same visual pattern,
so it is tested as the in-data analog. DABUR t24 matches exactly (July high = 456.0).

| truth | level exists pre-sweep (±0.3%)? | SWEPT on right bar? | offset | Evidence |
|---|---|---|---|---|
| HAV EQH ~1213.5 (19/01) swept 20/01 14:30 | — not in dataset | — | — | — |
| HAV EQH ~1215.9 (02/02=07/02) swept 09-10/02 | — not in dataset | — | — | — |
| DABUR 450.9 (02/07 pivot) poke 07/07 14:30 H456.0, collapse 08/07 | **HIT**: SWING_H 5m+15m [450.95,451.05] confirmed 02/07 09:45; EQH-451.00 born 02/07; EXT_H 1h [448.30,451.00] | **MISS**: EQH DEAD 07/07 09:20, EXT_H DEAD 07/07 10:30 (2-close break confirm); price held above 451 all of 07/07 (close 454.0) -> 5m engine can only call it a break; no SWEPT ever | n/a (wrong terminal label, ~1 day before the collapse-confirm) | none (would also be min_touches-blocked) |
| HAV 1221.9 swing 17/02 | — not in dataset | — | — | — |
| **analog** HAV EQH ~1229.2 (07/07 pm) swept 08/07 spike 1234 | **HIT**: EQH-1228.90 born 07/07 14:05, ~18h pre-sweep (data top 1228.9 vs chart 1229.2) | **HIT (early-poke)**: SWEPT 08/07 11:00 (poke wick 1231.8, close-back); visual sweep candle = 11:25/11:30 extreme to 1234.0; then RECL 11:05, INVERTED 11:30 = breaker seed ON the extreme bar | **-5 bars** (engine takes first poke, trader marks deepest) | EQH evidence **BLOCKED** (touches=2 TF-echo < 3); twin PDH-2026-07-08 (exempt) fired SHORT q=0.70@11:05 + 0.80 upgrade, poke_ts=11:00 ✓ G3 meta works |
| **analog** HAV extreme 1234.34 line (t1) | **HIT**: EXT_H 1h [1228.40,1234.00] — wick edge 1234.0 (vendor Δ0.34) | correctly unswept in window (LTP approaches from below, as in t1) | — | — |
| **analog** HAV extreme low 1125.51 (t1/T2) | **HIT**: EXT_L 5m/15m/1h/1d bands, edge exactly 1125.50; + PWL/PDL/SWING_L | correctly unswept | — | — |

Net: line EXISTENCE is good (every in-data taught line has a catalog level at the wick within 0.5pt,
well before the sweep). Sweep RECOGNITION fails at swing scale (L5) and sweep SIGNALING is strangled
by min_touches on echo-inflated counts (L2) — the July analog only signaled because a PDH coincided.

## 3. ISSUES (ranked)

1. **min_touches=3 blocks the taught 2-touch line** — and today's `touches` don't even mean touches
   (86% single-pivot TF echoes). 69% of EQ sweeps, 96% of swing sweeps emit nothing.
2. **5m-only sweep state machine**: multi-hour/overnight sweeps (the taught norm: t24, T12, t23)
   resolve DEAD. A D1-scale pass would resolve DABUR as PENDING(07/07 close 454>451) -> SWEPT on the
   08/07 collapse with poke_ts=07/07 — exactly the taught marking.
3. **EQ zone is a union band, not a line**: EXT members widen it to 4pt+; sweep then needs close fully
   beyond the far band edge; equal-WICK pairs with unequal bodies fail the mid-tolerance (L1).
4. **Zombie churn / blocked re-formation** (L6): nightly prune + extremes recompute resurrects dead
   pivots (~7 phantom DEAD/day), while carried SWEPT EQ blocks fresh pools at the same price.
5. 48h recency decay mis-prices weeks-old untapped lines (L3). Low: weight-only.

## 4. SURGICAL TWEAKS (code-level; NO config change, NO commits)

Baseline A for every pair (frozen tree):
`cd app && python -m trader.cli study --data ../data/marks_2026 --out /tmp/aud_A --symbols HAVELLS,DABUR,DLF,TITAN,VOLTAS,SBILIFE,SBICARD --from 2026-06-01 --to 2026-07-17 --only extremes,swings,liquidity,sweep --dir ../runs/validate/taught_profile`

- **S1 — true-touch EQ, wick-keyed** (`liquidity.py::_create_eq`): dedupe candidates that are the same
  pivot (same/adjacent born bar across TFs) before grouping; cluster on the WICK edge (zone hi for H,
  zone lo for L) not `_mid`; EQ zone = group wick edge ± tick; touches = distinct pivots.
  A/B: apply edit -> same command `--out /tmp/aud_s1_B`; compare summary.csv liquidity/sweep rows
  (n, hit%, edge) + EQ pool count/median width (evidence.parquet).
- **S2 — kind-aware sweep gate** (`sweep.py`): EQH/EQL pass at `touches>=2` (real touches post-S1),
  SWING/EXT keep 3; config `min_touches:3` untouched.
  A/B: same pair `--out /tmp/aud_s2_B`; SWEEP n must rise, watch hit% vs base%. Edge gate:
  `python3 tools/derive_tradebook.py HAVELLS,DABUR,DLF,TITAN,VOLTAS` then
  `python3 tools/ab_tradebook.py <tradebook.csv> none` (hi-tier net-R + 4 quadrants >= baseline, else revert).
- **S3 — session-scale sweep pass**: second LevelEngine instance fed D1 closes for
  {EQH,EQL,EXT_H,EXT_L,PDH,PDL,PWH,PWL} (or per-kind pending/reclaim windows ≈1 session on M5);
  sweep detector consumes both engines' SWEPT + poke meta.
  A/B: `... --out /tmp/aud_s3_B --symbols DABUR --from 2026-06-15 --to 2026-07-10`; acceptance = the
  451 line yields SWEPT with poke_ts=2026-07-07 (today: DEAD 07/07 09:20, silence).
- **S4 — kill zombie churn** (`pipeline.py`): add EXT_H/EXT_L to `_CARRY` so state/touches persist and
  extremes' id-dedupe stops re-creation; dead stays dead.
  A/B: same pair `--out /tmp/aud_s4_B`; metric = EXT DEAD transitions/day (169/25d -> ~0) + POOL_NEAR
  count sanity; edge via ab_tradebook GATE as above.
- **S5 (opt) — recency floor** (`_pool_strength`): floor EQ recency at 0.5 (untapped age ≈ neutral).
  A/B: same pair; read sweep `edge t1/t2/t3` strength tiers.

Order: S1 -> S2 (S2 without S1 fires on echo pools). S3 independent. Each behind the study pair first,
ab_tradebook GATE second (48-SPEC test ladder C).
