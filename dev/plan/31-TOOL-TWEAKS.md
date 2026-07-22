# 31 — TOOL-TWEAK MAP (lesson → exact code/logic change → test)

PLAN (user-set 2026-07-22): collect ~50 worked trade examples (dev/IMG/trades/) → refine
tools/study from the full corpus → THEN build. NO build until 50 examples studied. Current: 12.
Each trade: read back (prove understanding) → confirm/add rule → map to code change + test →
commit + archive image. Standing order: keep committing continuously.

Accumulator for the deep tool-tweak session. Each row: the taught finding, the specific
detector/engine change it demands, and the measurement that must gate it. Source lessons in
dev/plan/30-LESSONS.md; worked trades in dev/IMG/trades/ (HAVELLS T1 short 1:8, T2 long 1:6).

Guiding discipline (unchanged): detection parity first; NO profit language until measured with
4-way holdouts + matched null. Everything measured so far = recognition real (58-61%), bankable
net ~0 after toll on free data; these tweaks target the RUNWAY/MAGNITUDE gap (which zone runs 1:5).

## T1 — SWEEP-SEQUENCED VALIDITY (lesson 17) — HIGHEST PRIORITY
- WHAT: the valid zone is the freshest one born from/after the FINAL same-direction liquidity
  sweep before reversal; an earlier zone a later sweep ran PAST is `superseded` (dead as entry).
- CODE NOW: ob_taught/fvg_n kill a zone only on close-through its OWN far edge (break-depth law);
  ob_taught/breaker_msb do breaker-vs-mitigation (swept test) but NOTHING invalidates a zone when
  a later sweep runs beyond it. We emit run-past stale zones = the shitpile.
- CHANGE: track same-dir sweep events (wick beyond a prior extreme + close back, or price
  exceeding a prior EXT pivot). On a new further-extreme same-dir sweep, mark all earlier same-side
  zones between the old zone and the new sweep extreme `superseded=True`. Emit/grade only
  non-superseded (decisional) zones. Reuse extremes.py pivots + ts3 sweep machinery.
- WHY BIG: fixes (a) which-zone-to-act-on, (b) fewer signals, (c) MAGNITUDE — post-sweep zone has
  swept liquidity as fuel behind + far target ahead = the 1:5+ runner (both HAVELLS trades).
- TEST: does the "decisional (non-superseded) zone" tier concentrate reach-5R share ex-ante and
  beat the current grade, 4-way holdout.

## T2 — ENTRY/SL MECHANICS (lesson 18) — HAVELLS T2
- WHAT: entry = FVG MIDPOINT (half height) INSIDE the OB; SL = BELOW the whole OB/FVG at the
  swing extreme (risk = OB height, not FVG height); continuation direction.
- CODE NOW: fvg_n/ob_taught emit edge-entry Evidence, sl = zone far edge. No "FVG-inside-OB" pairing,
  no OB-height stop.
- CHANGE: when an FVG sits inside an OB (band containment), emit a combined signal: entry = FVG CE,
  sl_floor = below OB far edge (swing-extreme side). Add as an entry-policy variant, not default.
- TENSION: TAUGHT_OB measured edge>=CE>>OTE — BUT with SL tied to the zone, not below-OB. User's
  SL-below-OB makes CE entry = more reward at fixed structural risk; fill-rate is the open question.
- TEST: exact combo (entry=FVG-CE, SL=below-OB) on sweep-valid zones vs edge-entry baseline.

## T3 — OTE 70.2% CONFLUENCE (lesson 19)
- WHAT: valid zone retest that ALSO lands at ~70.2% (60-75%) fib retracement of the impulse leg =
  optimal fill. Confluence FILTER, not standalone entry. Multi-TF (HTF leg fib + LTF zone).
- CODE NOW: no fib/retracement computation anywhere.
- CHANGE: compute retracement % of the entry against the impulse leg (extremes pivot -> displacement
  -> zone); attach `ote_pct` to signal meta; optional grade component / gate at 60-75%.
- TEST: does "zone retest AND ote_pct in 60-75%" concentrate runners vs zone-retest alone (recall
  OTE-alone was <=+2pp; the question is OTE-as-confluence-on-sweep-valid-zone).

## T2 UPDATE — MID-BLOCK ENTRY now CONFIRMED 2x (HAVELLS T2 long + T3 short)
- "ENTRY IN MID OF BLOCK" taught in BOTH T2 and T3 -> this is the user's CONSISTENT entry rule,
  not a one-off. Entry = CE (mid) of the OB/FVG; SL beyond the block (swing-extreme side).
- Raises priority of the CE-entry re-test: our edge>=CE finding (TAUGHT_OB) tied SL to the zone;
  user ALWAYS pairs mid-entry with SL-beyond-block. Must measure the user's exact construction
  before trusting edge over CE. Treat mid-entry as the default to beat, not the challenger.

## T1 UPDATE — BROKEN OB = INVALIDATED (HAVELLS T3, "very crucial")
- Once price closes through an OB, its ORIGINAL role is DEAD — do not trade it as that OB.
  (May flip to BREAKER if the L12 sweep test passes; else fully dead.) This is the same
  anti-shitpile mechanism as sweep-sequenced validity (T1): the valid zone is always the FRESH
  one; broken/run-past zones are removed. Engine currently emits them -> must suppress.
- T3 target = prior structure liquidity (the swept low) -> confirms target = far liquidity pool.

## T4 — MITIGATION ENTRY + MID-ENTRY now 3x IRONCLAD (HAVELLS T4 short)
- Mitigation block (no-sweep-above case, L12) is a valid entry zone — mirror of T1's breaker.
  ob_taught already EMITS MIT retests (_EVENT["MIT"]) -> code handles it; keep.
- ENTRY IN MID confirmed a 3rd time (T2 long, T3 short, T4 short) -> DEFINITIVE. STANCE FLIP:
  mid-block entry (CE) with SL beyond the block is now the PRIMARY entry config to test; the
  measured edge>=CE (TAUGHT_OB) becomes the challenger (it used zone-tied SL, never SL-beyond-
  block). Caveat: shown trades are user-picked WINNERS -> measure mid-entry on ALL setups
  (win+loss), 4-way holdout, before claiming it beats edge.
- Skeleton now seen 4x identical: [swing extreme] -> [flip-family or fresh block: breaker/
  mitigation/OB with FVG inside] -> [retest, enter MID, SL beyond block] -> [target = prior
  structure liquidity / far pool]. Both directions, both flip types. This is THE setup to build.

## T5 — LONG sequence + LTF TIGHT-STOP (HAVELLS T5 long, 5m, paper 1:9)
- Bullish mirror: liquidity SWEEP of lows + swing -> BOS UP -> demand OB -> retest, ENTER MID,
  SL just below block, target far. (Shorts = sweep-of-highs -> BOS down.) Mid-entry now 4x.
- LTF (5m) refinement = tight STRUCTURAL stop (entry 1875 / SL 1870 = 5pt/0.27%) -> paper 1:9.
  This is HOW the 1:5+ RR is achieved: refine to LTF where the stop is tiny but still below
  valid structure.
- CRITICAL HONEST FLAG (measured): the tiny-LTF-stop class realizes FAR below paper RR because
  price FILLS THROUGH the stop next-candle (REFINE.md: 1-2m structural stops = -4.2R/trade from
  gap/slippage, not filled AT stop). A 5pt/5m stop ~ 1xATR = danger zone. BUT T5's stop is
  STRUCTURAL (below sweep-valid demand), better than arbitrary sub-ATR.
- THE MAKE-OR-BREAK TEST: does a sweep-valid zone + structural tight LTF stop realize paper RR
  after gap-through fills (our sims model this), or does fill-through eat it like arbitrary
  tight stops did? This decides whether "1:9 via LTF refinement" is real or a paper mirage.
  If real -> this is the profit lever (tiny risk, big target on the decisional zone).

## T6 — STACKED OBs + TRENDLINE + PYRAMIDING (HAVELLS T6 long, 5m)
CONFIRMS:
- Stacked/nested OBs (two demand zones overlapping) = the strong zone; entry in the OVERLAP.
  Live proof of the deep-stack law (grade.py nst already does this). Keep.
- Sequential BOS (BOS after BOS up) = continuation ladder; ties to minor->major sequencing (z=32).
- Mid-entry 5x.
NEW (not in toolset):
- TRENDLINE tool: user connects higher-lows into a trendline; a 2nd entry sits at its RETEST.
  We have NO trendline detector. Add: fit a trendline through consecutive same-side EXT pivots
  (higher-lows / lower-highs); its retest = re-entry/trail reference. Grade component TBD.
- PYRAMIDING / scaling-in: two entries on the same trend (OB entry + trendline-retest add). All
  prior work was single-entry; management model has no adds. New management variant to spec+test:
  add on continuation (BOS or trendline retest) with SL trailed under the new higher-low.
TEST: does adding on trendline/BOS retest improve net R vs single-entry (measure add legs
separately; adds can inflate winners but also add exposure -> honest per-leg accounting).

## T7 — TWO-SIDED RANGE + ZONE LONGEVITY (HAVELLS T7, 5m: short + long)
- Fade BOTH edges: supply OB short at top (entry mid ~1270), demand OB long at bottom (entry
  mid ~1248); the short's target = the long's entry zone. This is zone-based range fading, NOT
  the falsified fib-50 premium/discount -> use the actual EXT-anchored zones at range extremes.
- Zone longevity confirmed live: demand formed 02/11, traded 08/11 (6 sessions later) -> zones
  carry across sessions, valid on later retest (matches measured later-revisit + touch-2 laws).
- Mid-entry 6x. No new tool; strengthens deep-stack/longevity + adds "range = fade both zone
  edges" as a regime the engine should recognize (both a supply and a demand alive & respected).

## T8 — OB CANDLE DEF (confirms code) + NEAR-SWING/PREMIUM-DISCOUNT VALIDITY (HAVELLS T8)
- OB candle def CONFIRMED = ob_taught code: opposite-color candle(s) before the impulse
  (positive candle in down-move = supply; negative candle in up-move = demand), multi-candle
  cluster, TF-agnostic. `_cluster` finds first sign==-d candle in the run. Keep, no change.
- NEW VALIDITY FILTER (user explicit): a valid OB/FVG must form NEAR the swing extreme =
  "premium or discount" (supply OB near swing HIGH / in premium; demand OB near swing LOW / in
  discount). Code NOW: ob_taught grades pivot_dist but maxd=any (emits ALL OBs, no location
  filter). CHANGE: add a location validity filter — OB/FVG valid only if born in the
  premium/discount extreme of its dealing range (or within N-ATR of an EXT pivot).
- KEY: premium/discount was falsified ONLY as a CHoCH-follow-through GATE (STRUCT.md, inverted).
  It is UNTESTED as an OB-LOCATION filter ("valid supply forms in premium"). Different claim.
  TEST: does "OB born in premium(supply)/discount(demand) third of range" beat emit-all + does
  it concentrate the runners (a valid location may be the missing MAGNITUDE/runway proxy).

## T9 — INTERNAL ORDER BLOCK (OB-within-OB refinement) (HAVELLS T9 short, 5m)
- CONFIRMS T8: bearish OB = the UPWARD-move (positive) candles before the drop ("was upward move
  before going to down"). ob_taught already gets this. Keep.
- NEW: INTERNAL ORDER BLOCK — an OB nested INSIDE the outer OB (finer than FVG-inside-OB). The
  outer OB is coarse; the internal OB is the refined sub-zone where ENTRY goes. Entry = mid of
  the INTERNAL OB, not the whole outer OB.
- CODE NOW: ob_taught finds one cluster per run; no OB-within-OB. CHANGE: within a birthed OB,
  locate the internal OB = the last/finest opposite-candle sub-cluster nearest the departure
  point (the bar where price leaves the zone); emit it as the refined entry sub-zone (parent =
  the outer OB). This is the OB-native HTF->LTF refinement (matches lesson-9 nesting: coarse
  zone -> finer zone inside for the precise entry+tight SL).
- Ties to T5: the internal OB gives the tight structural stop (SL below internal OB) -> the 1:5+
  RR. So internal-OB + structural-stop is the mechanism behind the big-RR winners. TEST with
  the fill-through make-or-break (T5): does internal-OB entry + SL-below-internal-OB realize
  paper RR after gap-through?

## T10 — OB CASCADE / sequential re-entry down a trend (HAVELLS T10, 5m, ~87pt in 2 trades) **HIGH VALUE**
- NOT one trade: TWO sequential shorts. Sweep ~1370 -> OB#1 1360-67 -> ENTRY#1 1363 (21/06) ->
  ride to ~1325 -> BOS -> OB#2 1325-32 (born 23/06) -> ENTRY#2 1330 (03/07, ~10 DAYS later,
  SL above) -> EXIT ~1280. Each leg forms a FRESH decisional OB; each retest = a NEW entry with
  its OWN tight stop above that OB.
- DISTINCT from pyramiding (T6 = add to one position): cascade = SEPARATE trades at successive
  OBs as the trend steps down. Captures a big trend move via a SERIES of tight-risk entries
  instead of one wide-stop hold.
- WHY POTENTIALLY THE PROFIT LEVER: the measured death was "one entry, symmetric excursion, wide
  stop, toll eats it." Cascade re-entry = many tight-stop entries each riding one leg -> could
  compound trend capture while keeping per-trade risk tiny (and per-trade toll is fixed, so more
  R per trade helps). Directly attacks the toll/symmetry problem.
- TEST (high priority): does OB-cascade re-entry (short each fresh post-BOS OB retest in a
  downtrend; mirror up) beat single-entry-hold on trending legs, net after fill-through + toll,
  4-way holdout? Confirms extreme longevity (10-day retest). Mid-entry 8x.
- CODE: needs trend-context (sequence of same-dir BOS / EXT pivots) + emit a fresh signal on
  EACH new decisional OB retest along the trend, not just the first. Ties T1 (each OB is the
  decisional zone for its leg) + T5/T9 (tight internal-OB stop) + management (re-entry engine).

## T11 — THE ENGINE / WHY IT WORKS + failed-breakout filter (HAVELLS T11 short)
- RATIONALE (unifies everything): smart money SWEEPS liquidity resting above an OBVIOUS retail
  level (old high, equal-highs, breakout point = clustered buy-stops + short SLs), TRAPS the
  breakout longs, sells into them -> the OB forms AT the sweep (where they transacted) -> retest
  = short; the trapped crowd's stops below = the runway/fuel. Mirror for longs (sweep of lows).
- This is the WHY behind: T1 valid-zone-at-sweep (that's where SM transacted), breakouts-are-
  traps, and post-sweep-OB-runs-far (trapped stops fuel it).
- TESTABLE FILTER (new specificity): require the swept level to be OBVIOUS retail liquidity
  (EXT-pivot old high/low, EQ-pool, round number) whose breakout FAILED (turtle_soup shape:
  wick/close beyond then reversal). Fade the failed breakout via the post-sweep OB. Pieces exist:
  turtle_soup + EQ pools + sweep->reversal (LIQ.md +2.2pp measured). 
- TEST: does "post-sweep-of-OBVIOUS-liquidity + failed-breakout + OB retest" beat generic OB
  retest on hit% AND reach-5R (the failed-breakout context may be the magnitude/runway proxy —
  trapped crowd = guaranteed opposing fuel toward the far target).

## T12 — PERSISTENT OB (range ceiling, multi-touch, 13-day longevity) (HAVELLS T12 short)
- Sweep (~1242) -> OB (~1228-33, born 10/02) tested ~6x over ~2 weeks, holds each time (range
  ceiling), final touch 23/02 (~13 days later) breaks DOWN to ~1158 (the runner).
- Reinforces: extreme longevity (13d, never closed-through -> break-depth law keeps it alive
  correctly, code OK); persistent OB = repeated fade (like T7 range); final touch = breakout
  runner.
- HONEST TENSION (must resolve, do NOT ignore): LEARN measured touch-3+ DRAGS netR. Here ~6
  touches "all valid" = small RANGE-FADES (price returns to range) + ONE breakout runner. Both
  true ONLY if you catch the runner touch; distinguishing range-fade-touch vs breakout-runner-
  touch ex-ante is the UNSOLVED magnitude question. Persistent-OB repeated fade is NOT free money
  -> small scratches waiting for an unidentifiable runner. 
- TEST: on a persistent OB (multi-touch), what ex-ante feature flags the touch that becomes the
  breakout runner vs another range-fade? Candidates: T11 (trapped-breakout/failed-breakout at
  the touch), runway to far liquidity (nothing below until the target), touch after a range
  compression. This is the SAME magnitude problem across T5/T9/T10/T11/T12 -> the ONE thing to
  crack. If a runner-flag exists + holds out-of-sample -> the profit lever; if not, method stays
  scratch-plus-toll.

## T13 — FULL BIDIRECTIONAL CYCLE (confirmation) (HAVELLS T13, 5m: short then long)
- SHORT: sweep-SL ~1214 -> swing ~1223 -> supply OB 1200-1213 w/ INTERNAL OB (~1207) -> ENTRY
  ~1208 -> BOS-after-BOS down -> ~1150. LONG: demand OB 1150-60 (swept low liquidity) -> ENTRY
  ~1157 -> back to ~1210. Short's target = long's entry.
- Confirms: internal OB (T9), sweep->OB engine both ways (T11), BOS cascade (T10), two-sided
  (T7). The market rotates between swept liquidity extremes; trade each turn, mirrored. Mid 9x.
- No new rule. Reinforces the engine is DIRECTION-SYMMETRIC (sweep-high->short, sweep-low->long).

## T14 — sweep range-high -> supply OB -> drop (confirmation) (HAVELLS T14 short, 5m)
- Range 1370-1400 -> dip 1365 -> rally back to ~1390 sweeping ~1385 range-high liquidity ->
  supply OB 1375-90 -> ENTRY mid ~1382 (retest 15/09) -> ~77pt drop, clean runway. Mid 10x.
  No new rule; clean sweep->supply-OB->retest->drop. Same engine as T10-12.

## T15 + T16 — PERSISTENT ZONE -> MASSIVE breakdown + COMPRESSION runner-flag candidate
- T15: mitigation block (no-sweep) ~1328-35 held ~157 bars -> final retest ENTRY ~1330 -> −105pt.
- T16: supply ceiling ~1205-18 held 16-24/02 (~6-8 touches) -> ENTRY ~1212 -> BOS -> −137pt.
- Both = T12 persistent-zone at extreme scale; huge runners (105-137pt). Mitigation confirmed.
- SLAMS the unsolved problem: breakdown touch looked identical to prior range-fade touches.
- NEW RUNNER-FLAG CANDIDATE (both charts): breakdown came after price COILED/COMPRESSED under
  the zone (lower highs tapping the ceiling, range tightening) then broke. "Compression-under-
  resistance -> break" (mirror: coil-above-support -> break up). Distinct from open two-sided
  range. TESTABLE: does a zone touch PRECEDED by range-compression-into-the-zone (falling ATR /
  narrowing range / lower-highs-into-ceiling) break/run more than a touch in an open range?
  Add to the magnitude-flag test battery alongside T11 (failed-breakout/trapped-crowd) + runway.

## T17 — LONG MIRROR confirmation (HAVELLS T17 long, 5m, ~49pt rally)
- Persistent demand OB floor ~567-70, held 16-30/07 (~2wk, coiled above), final retest ENTRY
  ~569 -> +49pt rally to ~618. Exact mirror of T15/T16 (supply ceiling -> breakdown). Confirms
  user's "long = short mirrored on water": same mid-entry, longevity, final-touch-runner,
  compression-before-break. Code is already d=+1/d=-1 symmetric -> one direction's rule = other's.
  No new rule; validates direction-symmetry + compression runner-flag both ways. 17/50.

## T18 — CROSS-STOCK GENERALIZATION (VOLTAS long, 5m — first non-HAVELLS)
- VOLTAS: liquidity sweep of lows ~1200 -> demand OB 1205-18 -> persistent support 18/05-03/06
  (~2wk multi-touch) -> ENTRY mid ~1210 (final retest) -> big rally to ~1325. Same as T17 on a
  DIFFERENT STOCK.
- KEY: kills the "HAVELLS-specific" worry (T1-T17 all HAVELLS). The sweep->OB->persistent->retest
  pattern is GENERAL market structure, not a stock quirk -> justifies the universe-wide (138-stock)
  scanner in the build. No new rule; the cross-stock validation the corpus needed. 18/50.

## T19 — VOLTAS short (cross-stock, short side) (5m)
- Range 1357-1400 (~2wk) -> rally sweeps ~1395 range-high -> supply OB 1388-95 -> retest ~1390
  -> −80pt to ~1310. Same as T14/T10 on VOLTAS. VOLTAS now shows BOTH sides (T18 long + T19
  short) -> method is direction-symmetric AND stock-general. No new rule. 19/50.

## T19b — DLF short (THIRD stock) + target=FVG refinement (5m)
- DLF: swing liquidity ~785 swept -> supply OB 778-84 -> ENTRY mid ~782 (retest 04/11) -> −32pt
  to ~750, target = an unfilled FVG (745-50) from the earlier rally. THIRD stock (HAVELLS+VOLTAS
  +DLF) -> generalization definitive.
- NEW small refinement: TARGET can be an unfilled FVG (imbalance to rebalance), not only a swing
  low / liquidity pool. Target = far liquidity pool OR unfilled FVG. Add FVG-fill as a target
  candidate in the target/runway logic. ~20/50.

## T20 — DLF full cycle (confirmation) (5m, short then long)
- Supply OB 773-85 w/ internal OB -> short -> ~740 demand OB -> long -> rally to ~785+. Range
  oscillation supply<->demand (short target = long entry). Internal OB (T9) + bidirectional
  cycle (T13) + range (T7) all confirmed on DLF (3rd stock). No new rule. ~21/50.

## T21 — DLF long multi-entry cascade (CONFIRMS SYNTHESIS §2/§3) (5m)
- Demand OB ~388-90 held 11-30/11 (~3wk consolidation) -> 2 long entries (25/11, 30/11) on
  successive retests -> big expansion 388->420. Confirms 32-SYNTHESIS: compression->expansion
  magnitude (§3), cascade/re-entry long-side (§2, mirror of T10), persistent-zone longevity.
  Synthesis proving predictive on the next trade. No new rule. ~22/50.

## t22 + t23 — TITAN both sides (4th stock, confirmation) (5m)
- t22 long: demand 4000-50 + internal OB -> ~2-3d consolidation -> +260pt rally (compression->
  expansion). t23 short: liquidity-sl-taken ~3560 -> supply OB 3510-30 -> entry ~3515 -> BOS ->
  −235pt. 4 stocks now (HAVELLS/VOLTAS/DLF/TITAN) both directions. Fits synthesis exactly. No
  new rule. ~24/50.

## Cross-cutting note
The three tweaks compose into ONE thesis: the tradeable setup = a DECISIONAL zone (post-final-sweep,
lesson 17) entered at its FVG-CE with SL below the OB (lesson 18), confirmed by 70.2% OTE of the
impulse leg (lesson 19), aimed at a FAR liquidity target with clean runway (the magnitude lever).
Both HAVELLS winners fit this exactly. Build order: T1 (validity) -> T2 (entry/SL) -> T3 (OTE),
measuring reach-5R concentration + net-after-toll at each step, 4-way holdout, before any profit claim.
