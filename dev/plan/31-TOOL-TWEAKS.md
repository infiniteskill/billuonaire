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

## Cross-cutting note
The three tweaks compose into ONE thesis: the tradeable setup = a DECISIONAL zone (post-final-sweep,
lesson 17) entered at its FVG-CE with SL below the OB (lesson 18), confirmed by 70.2% OTE of the
impulse leg (lesson 19), aimed at a FAR liquidity target with clean runway (the magnitude lever).
Both HAVELLS winners fit this exactly. Build order: T1 (validity) -> T2 (entry/SL) -> T3 (OTE),
measuring reach-5R concentration + net-after-toll at each step, 4-way holdout, before any profit claim.
