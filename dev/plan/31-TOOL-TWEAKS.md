# 31 — TOOL-TWEAK MAP (lesson → exact code/logic change → test)
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

## Cross-cutting note
The three tweaks compose into ONE thesis: the tradeable setup = a DECISIONAL zone (post-final-sweep,
lesson 17) entered at its FVG-CE with SL below the OB (lesson 18), confirmed by 70.2% OTE of the
impulse leg (lesson 19), aimed at a FAR liquidity target with clean runway (the magnitude lever).
Both HAVELLS winners fit this exactly. Build order: T1 (validity) -> T2 (entry/SL) -> T3 (OTE),
measuring reach-5R concentration + net-after-toll at each step, 4-way holdout, before any profit claim.
