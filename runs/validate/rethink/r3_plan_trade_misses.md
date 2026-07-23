# r3 — DEEP RE-READ: missed patterns & contradictions across the taught-method docs
(2026-07-23; no code, no build — audit only. Sources: dev/plan/30–36, runs/validate/dates/a1–a5,
runs/validate/ANALYSIS.md. "ANALYSIS" below = runs/validate/ANALYSIS.md, whose headline is
"RANGE-EXTREME FADE of a COILED market / the user is a mean-reversion extreme-fader.")

The single load-bearing finding: **ANALYSIS collapsed a TWO-MODE method into one mode.** The docs
themselves (lesson 20, lesson 21, tool-tweaks T6/T10/T21) describe a second, equal half — the
draw-on-liquidity / Wyckoff-markup RIDE (continuation, cascades, pyramids) — that ANALYSIS's five
dimensions do not represent. Roughly 40% of the corpus lives in that erased half.

---

## SECTION 1 — COUNTER-EXAMPLE TRADES (do NOT fit "fade the extreme of a mature ranging/coiled market")

ANALYSIS's own numbers already contradict its headline:
- **Dim-1 regime**: RANGE = 18, but **TREND_DOWN = 5 + TREND_UP = 7 = 12/30 are in a TRENDING
  regime (ADX ≥ 22)**, not the "coiled/ranging" market the headline names. 40% of the corpus is
  the counter-example, admitted in the same table that crowns ranging.
- **Dim-3**: **CONTINUATION = 3** (with the trend) and **REVERSAL = 9** (counter-trend fade into a
  live strong trend, "ADX 24–57"). Only the 18 "RANGE_FADE" are the pure headline trade; 12 are not.

Concrete counter-example trades and what they actually are:

1. **TITAN T22 long** (a4): entry ~4010 off a demand zone after a low-sweep → *"vertical rally past
   4250," "steep up trendline."* This is momentum / trend-continuation (a markup ride), not a fade
   of a coiled range. Explicitly a runaway up-leg.

2. **HAVELLS "OB cascade" T10** (a2 #9/#10/#11): TWO sequential shorts — OB1 16/06 (~1363) then OB2
   23/06 (~1328), 10 days apart, each a fresh post-BOS block down a trend. Tool-tweaks T10 itself
   calls it *"NOT one trade: TWO sequential shorts… captures a big trend move via a SERIES of tight
   entries."* Trend-continuation cascade, not a single range-extreme fade.

3. **HAVELLS T6 stacked-OB + trendline + PYRAMIDING** (tool-tweaks): *"Sequential BOS (BOS after BOS
   up) = continuation ladder,"* two entries on the same trend (OB + trendline-retest add). Explicit
   pyramided continuation.

4. **DLF two-era split:**
   - Era ~730–790 (Trade F / T19-DLF, ~2024): short from mitigation ~778 → down to 740, then a
     REVERSAL long ~748 to ~790. A two-sided rotation whose long leg is a continuation to opposite
     liquidity.
   - Era ~380–420 (Trade G / T20–T21): DLF long ~388–390 with **entries ×2 (25/11 AND 30/11)** →
     rally to ~418. A **pyramided multi-entry cascade** (tool-tweaks T21: *"2 long entries on
     successive retests → big expansion"*), not one fade.

5. **DABUR two-era split:**
   - Era ~420–455: T24 short (~448) fits; but **T25 long** (~421, *"ob+propulsion block… rally to
     ~450 old-high liquidity"*) = full low-liquidity→high-liquidity **traversal** = the
     draw-on-liquidity RIDE (lesson 20), a continuation.
   - Era ~480–525: T26 short (FVG); **T27 long** (~491 → ~525) with a **2nd higher demand catching
     the pullback (cascade)** per tool-tweaks T27.

6. **SBICARD t28 / t29 / t30 (a5) — all three LONGS:** these are **trend-REVERSAL bottoms of a large
   decline** (t28 daily: *900→567 then base*) taken via **deep multi-TF nesting** (5m OB ⊂ 2H/15m OB
   ⊂ daily base). They numerically land in RANGE+DISCOUNT so ANALYSIS absorbs them, but their
   *taught* headline feature is HTF-ALIGNMENT / MTF nesting (doc 36), which is NOT one of ANALYSIS's
   dimensions. Mechanistically "catch the base after a downtrend," not "fade a coiled range extreme."

7. **SBILIFE t31 (ANALYSIS's own OOS trade):** contains a **continuation LONG leg** — *"swept the
   range low, ran to the liquidity (1925) +5.1% — the mirror leg"* = draw-on-liquidity ride to the
   opposite pool, under-weighted by the "fader" framing.

8. **The DUAL-ZONE (short-OB + long-OB on ONE chart) trades:** a2 #3 (Nov), a2 #12/#13 (May
   breakout-trap), a3 #1 (Jan), a3 #14/#15 (DLF), HAVELLS T7/T13, DLF T20, DABUR T20/T27. Each is a
   two-sided range where the short's target IS the long's entry — a coupled pair, not a single
   directional fade. ANALYSIS counts each leg as an independent trade and never records the pairing.

9. **HAVELLS "Trade A" Jan–Feb long** (a2 #1/#2): *"rallied to 1355+ on steep trendline," BOS ×2* =
   momentum continuation off stacked OBs.

10. **HAVELLS T7 (the proto-LOSER):** fits "fade the extreme" but is the ONE range that SCRATCHED
    because it was YOUNG/OPEN (no compression). It is a counter-example to "mature/coiled" — a fade
    that did NOT run. Doc 34 leans on it as the compression-separator, yet it sits inside the
    "winners" corpus (see §3.8 contradiction).

11. **Non-trades counted as trades:** a1 Trade A = HAVELLS fib/OTE map (#1) + liquidity-extreme range
    lines (#2), explicitly *"HTF context… not an executable entry."* Two of the "trades" are context
    maps, not entries.

---

## SECTION 2 — MISSED FEATURE DIMENSIONS (present in the extraction tables; absent from ANALYSIS)

ANALYSIS captures only: ADX-regime, premium/discount, reversal/continuation, contraction, sweep+nesting.
The extraction tables (a1–a5) carry these dimensions it never touched:

1. **TIME-OF-DAY of entry (tooltips).** Exact intraday entry times are recorded and CLUSTER:
   VOLTAS 18/05 10:20, 02/06 13:45, 03/06 12:25; DLF 28/11 13:15, 10/11 14:00, 25/11 13:20, 30/11
   15:10; SBICARD 09/07 10:55 / 13:10, 07/07 14:40, 30/12 14:29; HAVELLS 03/07 12:45, 14/07 10:15,
   01/02 10:35, 08/11 14:35, 17/02 12:30. Concentrated in the FIRST hour (09:45–10:55) and the
   AFTERNOON/last hour (13:10–15:10) — the classic liquidity-run windows. ANALYSIS never looks at
   intraday timing. (And it collides with the doc-30 "no session logic" rule — see §3.4.)

2. **DAY-OF-WEEK.** Never extracted or analyzed at all.

3. **GAP / OVERNIGHT behavior.** Zones persist across sessions and retests fire days–weeks after
   birth (VOLTAS OB 18/05 → entry 02–03/06; DLF OB 10–11/11 → entry 25/11). Whether the retest/fill
   happens at or through a gap is never measured — even though the WHOLE RR edge (docs 34/36) rides
   on the tiny stop surviving gap-through. ANALYSIS measures no gaps.

4. **The BAR-COUNT / rectangle tooltips = the user's OWN maturity measurement.** The images contain
   Kite measurement readouts the user drew: **"157 Bars"** (a3 #5 mitigation block), **"89 Bars"**
   (a2 #7 internal OB, "6.46 / −0.48%"), "Rectangle 3.43 (−0.26%) 157 Bars", "Ellipse 158.80 (−25%)
   2863 bars / 954 bars", "Rectangle 25.25 (−4.3%)", "Rectangle 12.67 (−2.2%)". These bar counts ARE
   doc-34's "range DURATION in bars" maturity feature — **hand-measured by the user in the images** —
   and the % readouts are the box height = the STOP distance / consolidation tightness (−0.26%,
   −0.48% = extremely tight coils). ANALYSIS's "contraction" proxy never uses these explicit,
   literal user-drawn maturity/tightness numbers.

5. **The "ALL SL TAKEN BY BANK" / breakout-trap causal text** (a2 #12/#13): *"ALL SL TAKEN BY BANK AS
   LIQUIDITY SWEEP," "ALL LONG ENTRIES DESTROYED IN BREAKOUT."* This is the user's stated WHY
   (trapped-breakout crowd = fuel; tool-tweaks T11). ANALYSIS encodes only a generic "sweep gate" and
   never represents failed-breakout / trapped-crowd as a dimension — despite doc 36 later calling it
   one of the THREE unified runner-flags.

6. **MULTI-ENTRY PYRAMIDS / CASCADES collapsed to "single trade."** a3 #16/#19 DLF ("entry ×2"),
   a2 #9–11 HAVELLS (OB1+OB2), HAVELLS T6/T21. The "30 trades" count hides that several charts hold
   2 entries; ANALYSIS treats every trade as one entry, so per-leg accounting (tool-tweaks T6:
   *"measure add legs separately"*) is impossible from ANALYSIS.

7. **DIRECTIONAL ASYMMETRY (long vs short shape).** Doc 34 conclusion C: shorts cascade in ONE clean
   leg; **longs GRIND, needing REPEATED floor taps / pyramids** (VOLTAS double-sweep, DLF pyramid,
   SBICARD multi-touch). The extraction tables show it plainly. ANALYSIS never splits behaviour by
   side — it lumps median-mfe% by regime only.

8. **TARGET = unfilled FVG (imbalance-fill), not just a liquidity pool.** a4 T19-DLF target ~748 =
   FVG; DABUR T27 "ob-fvg" (tool-tweaks T19b). ANALYSIS's "target = far side of range" misses the
   FVG-fill target type.

9. **TOUCH-COUNT of the zone.** Doc 34 lists touch-count as maturity feature (b); the extraction has
   it (persistent OBs "tested ~6×", "5–6 touches"). ANALYSIS's contraction dimension never uses the
   explicit touch count.

10. **CROSS-ERA / CROSS-YEAR robustness axis.** Extraction stresses two-era stocks (HAVELLS ~570 vs
    ~1150–1350; DLF ~380 vs ~730; DABUR ~420 vs ~480; TITAN ~3250 vs ~3950). Doc 34 uses cross-time
    as a robustness argument; ANALYSIS does not exploit it.

11. **DATA-HYGIENE landmine:** a4 + doc 34 both flag the cleanest Lesson-7 composite (DLF short) is
    **MISFILED inside a VOLTAS (T19) folder.** Any automated extraction keyed on folder=stock will
    mislabel it. ANALYSIS does not account for the misfile.

---

## SECTION 3 — INTERNAL CONTRADICTIONS across the plan docs

1. **"Fade is falsified" (MEMORY / measured record) vs "fade is the edge" (ANALYSIS).** MEMORY:
   *"Fade thesis falsified — SMC fades symmetric MFE/MAE + sub-cost."* Tool-tweaks T8: premium/
   discount was *"falsified… as a CHoCH-follow-through GATE (STRUCT.md, inverted)."* Yet ANALYSIS
   crowns the "extreme-FADER" profile as the winner. The measured program says fade = symmetric /
   toll-bound / dead; the winners-only ANALYSIS says fade = the edge. This is the biggest
   unreconciled tension and ANALYSIS's own caveat concedes it ("does not prove the profile FILTERS
   OUT losers").

2. **What drives RR: STOP (doc 34) vs COMPRESSION/TARGET (doc 32 + ANALYSIS).** Doc 34 §6:
   *"RR IS MANUFACTURED BY THE STOP, NOT THE TARGET… targets are ~constant (50–90pt HAVELLS)."* But
   ANALYSIS Dim-1/Dim-4 + doc 32 §3 say the MOVE size scales with compression (**corr(ADX,move) =
   −0.26**, "tighter coil → bigger move"). If targets are ~constant per stock, ADX cannot correlate
   with move size. Doc 34 (constant runway, all edge in the stop) and ANALYSIS (variable move driven
   by coil) are in direct tension about where the reward comes from.

3. **Doc 36 says ANALYSIS's own features are NOISE.** Doc 36 §3: LTF chart features measured at the
   entry bar = **0.52 AUC = noise**; *"the signal is on the HTF."* ANALYSIS's three enforced gates
   (regime ADX, entry-location, contraction) are exactly such at-entry chart features. So doc 36
   implicitly invalidates ANALYSIS's "three thresholds the engine can enforce," and further notes the
   nesting filter it prefers was ALREADY measured at only **+2.74pp (didn't clear toll)**. The two
   docs propose different discriminators and each undercuts the other.

4. **"CONTINUOUS TAPE — NO day/session logic anywhere" (doc 30 ground rule) vs the evidence.** Every
   executed trade is 5m with specific intraday entry times that cluster (§2.1). If timing matters,
   that is session structure the ground rule forbids examining. Separately, the ONLY measured
   net-positive cell (lesson 10 DGRID, +0.09R) is at DAILY/positional scale (weeks–months holds), but
   ALL 30–32 taught trades are 5m-refined intraday entries → **the profitable measured regime and the
   taught execution grain do not match.**

5. **Doc 35's "bodies-only is only HALF" is NOT propagated.** Doc 35 (OB section): the user draws
   TWO boxes — OUTER wick box (for the STOP) + INNER body box (for the ENTRY-CE) — and explicitly
   *"REVISES the TUNE.md 'bodies-only frozen'."* But the shipped detector (git log / MEMORY:
   "bodies-box OB") emits the inner body box only, with SL at the body edge. Doc 34 §4 then computes
   its RR headline from *"SL just beyond the swept EXTREME (outer wick), 3–5pt"* — a stop the
   built bodies-only detector does NOT produce. So **doc 34's RR numbers assume a stop geometry the
   engine doesn't emit**, and doc 33's decision tree still says only a vague "SL just beyond it." The
   35 correction lives in 35 alone; 30/32/33/34 don't consistently encode it.

6. **"You are a FADER, continuation is rarest/weakest" (ANALYSIS Dim-3) vs lessons 20/21.** Lesson 20
   (draw-on-liquidity) and lesson 21 (Wyckoff markup/markdown RIDE) establish continuation/target-
   chaining as HALF the method; tool-tweaks T6/T10/T21 document the cascades/pyramids. Lesson 20 even
   states outright it *"reconciles the fader-vs-trend tension (ANALYSIS.md)"* — an explicit
   acknowledgement that ANALYSIS's headline is incomplete — yet ANALYSIS was never revised to the
   two-mode model.

7. **Corpus size & composition drift, never reconciled.** Doc 32 §1: *"20 trades, 3 stocks (HAVELLS
   ~15, VOLTAS ~3, DLF ~2)."* Doc 34: *"27 trades,"* and corrects that **t1–t17 are ALL HAVELLS
   across different years** (not 15+cross-stock as 32 framed). ANALYSIS: "30 taught trades" (+ t31 =
   31; task says ~32 incl. SBICARD/SBILIFE = 7 stocks). Doc 32's synthesis — the "what the method
   REALLY is" step-back — was written on a mis-counted 20-trade / 3-stock corpus and never updated.

8. **"T7 is the only near-scratch" (doc 34) vs ANALYSIS's several weak cells.** Doc 34: *"T7 is the
   ONE non-runner… the single most valuable trade."* But ANALYSIS shows 3 CONTINUATION trades at
   median 8.9% and 3 MID entries at 7.3% — multiple weak performers. Also all are called hand-picked
   WINNERS, so a "scratch/proto-LOSER" (T7) sitting inside the winners set is itself inconsistent.

9. **iFVG≡OB co-location merge (doc 35, t30) not guaranteed in the shipped stack.** Doc 35 says
   co-located iFVG-flip + OB must MERGE into one graded zone and flags fvg_cb has no iFVG flip; the
   git-log "merged FVG-N + bodies-box OB" doesn't confirm the iFVG-flip merge was built. (Minor.)

---

## SECTION 4 — UNFINISHED / NEVER-VERIFIED THREADS (marked "test/verify/untested" and left open)

- **Lesson 19:** *"T1 short entry ~70.2% retrace of its leg (verify numerically at test time)."* —
  never verified.
- **Lesson 18 / tool-tweak T2:** entry=FVG-CE + SL-below-OB *"NOT covered by prior measurement →
  test the EXACT combo before accepting/rejecting."* — untested.
- **Lesson 10:** *"Full assembled positional backtest pending once lessons complete."* — pending.
- **Every tool-tweak T1–T3, T5, T9–T12, T15/16 ends in a "TEST:" that was never run.** The headline
  unsolved one (T12, echoed T5/T9/T10/T11): *"what ex-ante feature flags the touch that becomes the
  breakout runner vs another range-fade… the ONE thing to crack."* Unresolved.
- **32-SYNTHESIS §6 "the two numbers that decide everything"** — (A) does compression flag runners
  ex-ante on ALL setups incl. losers, (B) fill-through — *"neither is measured yet."*
- **Doc 34:** *"measure A(maturity flags runners ex-ante on losers too) + B(fill-through)."* — unmeasured.
- **Doc 36:** the ENTIRE HTF-alignment-depth loss model is a TEST SPEC never executed; §6C's required
  causal check (*"verify HTF context is knowable PRE-entry, not drawn post-hoc"*) never done.
- **Doc 35:** every detector DIFF (add outer-wick box, CE-entry+hold, born-after-sweep+BOS gate, add
  5m/15m/30m TFs, LONE-extreme liquidity path, sweep lifecycle, void-union) is a worklist; git log
  shows only PARTIAL build (extremes + bodies-box OB), so outer-wick box / CE-entry / structure-gate
  per 35's spec appear unbuilt.
- **ANALYSIS's own build test:** *"does 'RANGE + extreme + swept + contracting' separate your wins
  from the setups you SKIP."* — impossible today: no loser/veto set exists.
- **Tool-tweak T6:** TRENDLINE detector (*"We have NO trendline detector"*) and PYRAMIDING management
  variant — unbuilt/untested.
- **Volume (lesson 21 Wyckoff):** *"a real, untested confirmation layer… add volume to the sweep +
  LPS gates."* — never added; volume is entirely absent from ANALYSIS.
- **CHoCH distance-confirm vs structure-confirm (lesson 6):** *"both should coexist… measure which
  [fires first]."* — unmeasured.
- **Fill-through at the ACTUAL entry TF (doc 36, t29):** whether a STRUCTURAL 1m stop survives where
  an ARBITRARY 1m stop lost −4.2R — flagged as THE deciding number — unresolved.
- **The YEAR of nearly every trade is UNRESOLVED.** The entire purpose of a1–a5 was to date trades
  against OHLCV, yet NO year is printed anywhere; years are INFERRED from price era (a5 gives
  confidence high/medium). ANALYSIS resolved only t31 SBILIFE to a real date (2024-09-23); the bulk
  of the "real-data" validation still rests on price-era date GUESSES, not confirmed OHLCV matches.

---

## SECTION 5 — THE TEACHING'S OWN GAPS (what the USER never showed or explained)

1. **NO LOSING TRADES.** All ~32 examples are hand-picked WINNERS. The user never showed a single
   loss or a setup that failed. Doc 36 *constructs* a loser class (HTF-misaligned) but that is the
   analyst's invention, not the user's teaching. The losing twin was never demonstrated.

2. **NO VETO / SKIP examples.** The user never showed a setup that LOOKED valid but he PASSED on, and
   why. ANALYSIS explicitly needs the "setups you SKIP… that looked similar but you vetoed" — the
   actual discriminator — and the user supplied none. His no-trade logic is entirely absent.

3. **EXIT / MANAGEMENT is one sentence.** Lesson 11 is the whole of it: *"Trail SL SLOWLY… 1:3 good,
   keep trailing toward 1:5+."* Never shown: the exact exit rule (the "EXIT" arrows in images have no
   stated trigger — target? trail? discretion?), what structure he trails under, partial/scale-out
   rules, or what he does when price moves against him pre-target.

4. **POSITION SIZING is completely absent.** No lesson covers risk-per-trade, how conviction/grade
   maps to size, or how to size the ADD legs in the pyramids/cascades (T6/T10/T21 add exposure with
   no sizing rule). Doc 33 node-5 "size up / skip" is the analyst's, not the user's.

5. **REAL-TIME IDENTIFICATION never demonstrated.** Every chart is a POST-HOC markup drawn on
   2026-07-22/23 over completed historical windows. The user never identified a setup LIVE at the
   hard right edge before the outcome was known — which is exactly where the unsolved "which touch is
   the runner / is this the FINAL sweep / is the range mature ENOUGH" judgment (T12) has to be made.

6. **FAILURE-IN-FLIGHT never shown.** He taught that broken OBs die and a structure-break flips the
   thesis (lesson 20), but never showed a trade he ENTERED that then FAILED — how he recognized it
   failing and what he did. No demonstrated stop-out.

7. **STRUCTURE-TF SELECTION is unoperationalized.** Lesson 10: *"whichever of 1D/1H/30m gives the
   CLEANEST swings"* — "cleanest" is never defined and he never showed a TF he REJECTED as unclean.

8. **UNIVERSE / STOCK SELECTION unshown.** 7 stocks were shown; how he scans and picks WHICH stocks
   to watch (the build assumes a 138-stock scan) was never taught.

9. **FREQUENCY / patience unquantified.** Doc 36 cites the user's aside "3 trades from 50 stocks," but
   expected trade frequency and how long to sit flat were never taught.

10. **NO honest own-record.** All RR figures (1:8, 1:9, 1:15) are PAPER, read off the hindsight
    markups. The user never gave his actual realized hit-rate, R-distribution, or drawdowns.

11. **FILL / SLIPPAGE reality never acknowledged.** He draws entries at exact zone-mid lines and SLs
    at exact ticks, assuming perfect fills. The entire fill-through problem (the whole edge, docs
    34/36) is the analyst's worry; the user trades as if the 3–5pt stop always holds.

12. **PORTFOLIO / CORRELATION risk.** Simultaneous demand-longs across DLF/VOLTAS/SBICARD = correlated
    NSE-beta exposure; never addressed.

---

## BOTTOM LINE
The docs quietly know more than ANALYSIS admits: lessons 20/21 and tool-tweaks T6/T10/T21 describe a
whole continuation/RIDE mode (cascades, pyramids, draw-on-liquidity, Wyckoff markup) that ANALYSIS's
"pure fader" headline erased, and ~40% of the trades live there. Meanwhile the RR that makes the
method attractive is (a) contradicted between "all in the tiny stop" (34) and "all in the coil-driven
move" (32/ANALYSIS), (b) computed on a stop geometry (outer-wick) the shipped bodies-only detector
doesn't emit (35), and (c) resting on YEAR-guesses, zero losers, zero exits, zero sizing, and a
never-run fill-through test — the four numbers every doc says decide everything.
