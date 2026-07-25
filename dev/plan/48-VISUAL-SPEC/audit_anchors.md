# 48 AUDIT — anchors: extremes + swings + structure (2026-07-25)

Method: real module functions (`_wilder_atr/_leg_K/_zigzag/_band`, structure/swings logic replicated
line-for-line), HAVELLS 1m → session-anchored resample, **per-bar causal recompute** (K/ATR drift with
prefix, replacement→DEAD tracked). Frozen params: extremes `leg_pct=2.0 tfs=[5m,15m,1h,1d]`,
structure `anchor=ext trend_swings=2 tf=5m`, swings defaults `strength=3 tfs=[5m,15m]`.

## 1. CODE-VS-SPEC

Matches (verified numerically, not just by reading): zigzag confirm-on-reversal-leg ✓ · alternation
with deepest-extreme replacement ✓ · lesson-13 wick-beyond-bodies band ✓ (5m EXT_H band
**1231.70/1234.00** vs drawn "ORDER BLOCK SWING" 1231.0 body-top + wick excluded, t1/08-24-55;
EXT_L band 1125.50/1127.40) · swings zone = wick±tick ✓ (= drawn BOS line at swing wick, G9).

| # | where | visual truth | code truth | sev |
|---|---|---|---|---|
| D1 | structure.py:61 + :83-94, config `trend_swings:2` | BOS drawn on every broken pivot | `_trend` needs ≥2 highs AND ≥2 lows inside the last `trend_swings` levels; anchors alternate → 2 levels = 1H+1L → **always NEUTRAL → structure emits NOTHING**. Verified: 0 evidence Jan02–Jul15, both anchors. decision.py:97 "bos" grade point unreachable; template.py:60, grade.py:132 tags dead. ob_taught survives only because `gate_mode:"sweep"` (ob_taught.py:158-160) skips the BOS leg | **CRIT** |
| D2 | structure.py:70,74,104-106 | BOS line AT the broken swing wick | break test + Evidence zone = `_mid(zone)`; with `anchor=ext` zone is the wick BAND → graded level = band mid, off the drawn wick by half the band (1d band 1123.6-1133.0 → 4.7pt) ; swing anchor mid==wick ✓ | MED |
| D3 | structure.py:51-54,64-67 | human breaks a CHOSEN shelf (t1: 07/07 lows 1210.6-1214.5) | only `highs[-1]/lows[-1]` ever graded; older shelves never; no state filter → DEAD/replaced pivots still trend/BOS anchors | MED |
| D4 | structure.py:45-80 (birth) | segment ends AT break candle | BOS can only fire once the pivot level EXISTS → inherits extremes confirm lag (B1); measured ext ts4: down-CHoCH for the 08/07 break fired **13/07 09:15 @1177.0** vs drawn 1210.6 on 08/07 09:35 = +3 sessions, −33pt | HIGH |
| D5 | extremes.py:212-213 → liquidity.py:195, premium_discount.py:54-62 | extreme = wick of the TRADED range (1234.34/1125.51) | `master` = whole-window max/min → 1h masters = **1514.7 (09/01) / 1123.6 (02/06)**, EQ 1319 vs taught EQ 1179.8; 1234.00 master=False on every tf → lone-EXT liquidity pool never emitted for it; p/d dealing range stale by 139pt | **HIGH** |
| D6 | extremes.py:42-43 | — | module defaults `leg_pct=6.0, tfs=("1h",)` vs frozen 2.0/[5m,15m,1h,1d]: at 6.0 the 1125.5 pivot **doesn't exist** on 15m/30m/1h (replaced by 02/06 1123.6 anchor, confirm 15-17/06) — param-missing run silently draws a different map | MED |
| D7 | extremes.py:81 | — | K=clip(pct/med,3,14) saturates: 1h pct≤2 rides FLOOR K=3 (leg_pct 1.0≡2.0, identical 61 pivots); 5m pct≥4.7 rides CEILING K=14 (4.7≡6.0) → leg_pct knob near-dead outside a narrow tf-dependent window | MED |
| D8 | candle.py:14; structure tf=5m only | context TF = 30m (t1,T2,T3,T4) | no 30m Timeframe exists; 1h is the proxy (adequate: both extremes HIT on 1h, see §2); 1d is the misfit (wrong anchor + weeks-late, §2); structure single-tf 5m | LOW |
| D9 | swings.py:71-73,81-86 | equal-high shelf used as BOS line | strict `>` → EQH never a swing (by design → liquidity's job, OK); overlap-block: months-old ACTIVE level blocks re-formation at same price (sim: 1212.5 slot held by level born 07/04) | LOW |

## 2. DETECTION ACCURACY (frozen params unless noted)

Ground-truth corrections from raw data: drawn 1234.34 → real wick **1234.00 08/07 11:30** (obs axis
calibration ±1pt); drawn 1125.51 "12/06" → real wick **1125.50 on 11/06 15:05**. T13/T12/T16/T10
obs_b charts are HISTORICAL scrolls, not in marks_2026 (2026-01-20 HAVELLS traded 1337-1454, not
~1190): T13 1189.7/1165.0 untestable → replaced by in-data analogs (t1 BOS band 1214.5/1210.6 broken
08/07 09:37; T5-analog up-BOS = last 5m swing-high 1143.3 before the low, broken 12/06 09:15).

### extremes (pivot at price ±0.3%?)

| target | tf | hit | pivot bar | first visible (lag) |
|---|---|---|---|---|
| EXT_H 1234.34 | 5m | **HIT** @1234.00 | 08/07 11:30 | 08/07 14:10 (+32b) |
| | 15m | **HIT** | 08/07 11:30 | 08/07 14:00 (+10b) |
| | 30m* | **HIT** | 08/07 11:15 | 08/07 13:45 (+5b) |
| | 1h | **HIT** | 08/07 11:15 | 08/07 13:15 (+2b) |
| | 1d | HIT(late) | 08/07 | **17/07** (+7 sessions) |
| EXT_L 1125.51 | 5m | **HIT** @1125.50 | 11/06 15:05 | 12/06 11:35 (+33b) |
| | 15m | **HIT** | 11/06 15:00 | 12/06 09:15 (+2b) |
| | 30m* | **HIT** | 11/06 14:45 | 12/06 09:15 (+2b) |
| | 1h | **HIT** | 11/06 14:15 | 12/06 09:15 (+2b) |
| | 1d | **MISS** | nearest = 1123.60 born 02/06 | 07/07 (+24 sessions) |

*30m resampled for the audit only — not a production tf. Extremes: **9/10 HIT**; both drawn lines
exist on 1h by next-open after the wick. Confirm-lag (pct=2.0, all confirmed pivots, batch): med
5m=45b(~3.8h) 15m=15b 30m=8b 1h=7b 1d=5 sessions. leg_pct=6.0 (module default): 1125.5 MISS on
15m/30m/1h; 1234 lag balloons to +81b(30m)/+46b(1h) — frozen 2.0 is right, default is the hazard.

### structure BOS (event at level ±0.3% near break time?)

| ground truth | FROZEN ext ts2 | ext ts4 | swing ts4 |
|---|---|---|---|
| t1 BOS 1212.55 (band 1210.6-1214.5) brk 08/07 09:35 | **MISS (0 events ever)** | MISS — nearest CHOCH S @1177.0 **13/07** | PARTIAL — CHOCH S @1225.6 08/07 12:05 (right day/dir; last-swing level, +13pt above drawn shelf) |
| T5-analog BOS-up 1143.3 brk 12/06 09:15 | **MISS** | MISS (BOS S @1132.2 11/06 — opposite side) | **EXACT HIT** — CHOCH L @1143.3 fired 12/06 09:15, same bar same level (labeled CHoCH; human labels it BOS — naming only) |
| totals Jan02–Jul15 | 0 BOS / 0 CHOCH | 11/7 | 109/101 |

Structure frozen: **0/2 + zero output for 6.5 months** (D1). Best variant (anchor=swing, ts=4) is the
only one that reproduces a drawn BOS at the exact bar+price.

## 3. ISSUES (ranked)

1. **structure is dead in production** — `trend_swings:2` mathematically forbids trend (D1). Every
   taught decision runs one grade point short (decision.py:97); every A/B that "tested" structure
   variants was comparing silence to silence.
2. **master/dealing-range staleness** (D5) — liquidity lone-EXT pools + premium_discount read
   all-history masters (1514.7/1123.6); taught range extremes (1234/1125.5) invisible to both.
   Existing param `range_lookback_days` (premium_discount.py:36, default 0) already encodes the fix.
3. **B1 pending-pivot invisibility, quantified** — cost is tf-shaped: 1h ≈ +2 bars (benign, line
   available next open), 5m ≈ +32/33 bars, **1d ≈ +7..24 sessions AND wrong anchor** → 1d in
   `extremes.timeframes` contributes only stale/mislocated bands to pivot-distance grading and
   liquidity. (No emit_live rebroadcast — B1 broad fix stays rejected; drop-1d is the surgical cut.)
4. **leg_pct clip saturation** (D7) + default mismatch (D6): on 1h the frozen 2.0 already sits at the
   K=3 floor (can't go finer); on 5m the default 6.0 sits at the K=14 ceiling. Tuning leg_pct without
   knowing the clip regime per tf is a no-op or a cliff.
5. tf coverage: 30m context is served by 1h (verified equal hits); structure locked to 5m — 30m/1h
   BOS the human draws (T3/T4 charts) has no producer.

## 4. SURGICAL TWEAKS (param-only; NO production config change, NO commits; gate = ab_tradebook)

AB=/tmp/claude-ab; mkdir -p $AB/{ts4,swing4,pd45,no1d}; CFG=runs/validate/taught_profile/config.json (cwd = repo root)

| # | tweak | rationale | A/B command |
|---|---|---|---|
| T1 | `structure.trend_swings: 2→4` | minimum value at which `_trend` can ever be non-NEUTRAL (needs 2H+2L in window); un-deadens the "bos" grade point | `jq '.detectors.params.structure.trend_swings=4' $CFG > $AB/ts4/config.json && DERIVE_PROFILE=$AB/ts4/config.json DERIVE_TB_OUT=$AB/ts4/tb.csv python3 tools/derive_tradebook.py HAVELLS,DABUR,DLF,SBICARD,SBILIFE,TITAN,VOLTAS && python3 tools/ab_tradebook.py $AB/ts4/tb.csv none` |
| T2 | `structure.anchor: ext→swing` (with ts=4) | only config that reproduced a drawn BOS at exact bar+price (§2); ext pivots (2% legs) are too coarse to hold the human's shelf | `jq '.detectors.params.structure={"anchor":"swing","trend_swings":4}' $CFG > $AB/swing4/config.json && DERIVE_PROFILE=$AB/swing4/config.json DERIVE_TB_OUT=$AB/swing4/tb.csv python3 tools/derive_tradebook.py HAVELLS,DABUR,DLF,SBICARD,SBILIFE,TITAN,VOLTAS && python3 tools/ab_tradebook.py $AB/swing4/tb.csv none` |
| T3 | `premium_discount.range_lookback_days: 0→45` | localizes masters to the traded range: 1h masters within 45d of July = 1234.0/1123.6 → EQ 1178.8 ≈ taught 1179.75 (vs stale 1319) | `jq '.detectors.params.premium_discount.range_lookback_days=45' $CFG > $AB/pd45/config.json && DERIVE_PROFILE=$AB/pd45/config.json DERIVE_TB_OUT=$AB/pd45/tb.csv python3 tools/derive_tradebook.py HAVELLS,DABUR,DLF,SBICARD,SBILIFE,TITAN,VOLTAS && python3 tools/ab_tradebook.py $AB/pd45/tb.csv none` |
| T4 | `extremes.timeframes: drop "1d"` | 1d anchors are wrong-pivot + 7-24 sessions late (§2); they only feed stale bands into pivot-distance grade + liquidity | `jq '.detectors.params.extremes.timeframes=["5m","15m","1h"]' $CFG > $AB/no1d/config.json && DERIVE_PROFILE=$AB/no1d/config.json DERIVE_TB_OUT=$AB/no1d/tb.csv python3 tools/derive_tradebook.py HAVELLS,DABUR,DLF,SBICARD,SBILIFE,TITAN,VOLTAS && python3 tools/ab_tradebook.py $AB/no1d/tb.csv none` |

Do NOT tune `leg_pct` before mapping the clip regime (D7): on 1h any pct≤2.0 is identical; recognition
step (spec §C.1) first via `trader study --data data/marks_2026 --out <dir> --symbols HAVELLS --only extremes,swings,structure --dir <ab-config-dir>`.
Ship gate stays spec §C.3: hi-tier net-R holds + 4 quadrants + walk-forward, else revert.
