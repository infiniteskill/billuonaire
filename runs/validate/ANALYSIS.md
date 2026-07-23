> ⚠️ SUPERSEDED — see runs/validate/RETHINK.md. "RANGE-fade of a coil is the edge" is a
> winners-only tautology: regime is DAILY for a 5m/30m method, RANGE is the default bucket,
> target_reached=29/30 has no outcome variance, corr(ADX,move)=−0.26 is n=30 p≈0.16 (NS), and
> premium/discount tags are window-fragile (5 trades violate the rule). The full-sample
> compression detector measures NEGATIVE (BOX_ON_LEVEL −2.3pp), contradicting the coil-edge
> thesis. Treat below as a description of WINNERS, not a proven filter.

# ANALYSIS — what SITUATION made the 30 taught trades perform (real data, 2026-07-23)

User's own trade criteria, restated: trade **EXTREMES** (never mid premium/discount),
let retail get swept first, enter the **valid reversal block + retest**, and read
**TRENDING vs RANGING**. This doc measures those exact axes on real cached Yahoo data
(daily HTF + finest LTF) for all 30 and asks: what made the best ones best.
Per-trade rows: `runs/validate/analysis.json`. Tool: `tools/yanalyze.py`.

## THE HEADLINE (one line)
The best trades are **RANGE-EXTREME FADES of a COILED market**: low-ADX (ranging /
compressed) daily context, price parked at the **extreme** of the range (premium for
shorts, discount for longs), retail liquidity swept, then reversal — the tighter the
coil, the bigger the move. Trend-continuation is rare and worst. The user is a
**mean-reversion extreme-fader, not a trend-follower** — and the data agrees.

## DIMENSION 1 — TRENDING vs RANGING (the biggest separator)
Regime = daily ADX(14) + net drift over 40 bars.
| regime | n | mean mfe% | median mfe% |
|--------|---|-----------|-------------|
| **RANGE** | 18 | **15.3** | **14.8** |
| TREND_DOWN | 5 | 12.3 | 11.8 |
| TREND_UP | 7 | 10.2 | 7.7 |
- **ADX < 22 (coiled/ranging): median 14.8%  vs  ADX ≥ 22 (trending): 10.2%.**
- **corr(ADX, move size) = −0.26** — the FLATTER/quieter the market, the BIGGER the
  eventual move on the fade. This is the compression→expansion thesis, quantified.
- 7 of the TOP 8 moves are RANGE regime. Ranging is where the edge lives.

## DIMENSION 2 — PREMIUM / DISCOUNT (your "extremes, never mid" claim — CONFIRMED)
entry_pos = (entry−lo)/(hi−lo) over the pre-entry swing window.
| location | n | median mfe% |
|----------|---|-------------|
| PREMIUM (≥.66) | 15 | 11.6 |
| DISCOUNT (≤.34) | 12 | 13.5 |
| **MID (.34–.66)** | **3** | **7.3** |
- **22/30 (73%) entered at the extreme** (short@PREMIUM or long@DISCOUNT). Only 3 at MID
  — and MID has the **worst median** (7.3%). You do what you say: extremes, not middle.
- (Caveat: location is measured vs a 40-bar DAILY window, not your exact drawn dealing
  range. A few "discount shorts" are just local-premium in a smaller frame the daily
  window can't see — so treat premium/discount as directional, not to the decimal.)

## DIMENSION 3 — REVERSAL vs CONTINUATION (you are a FADER)
| setup type | n | median mfe% |
|------------|---|-------------|
| **RANGE_FADE** (fade the extreme of a range) | 18 | **14.8** |
| REVERSAL (counter-trend fade at extreme) | 9 | 11.6 |
| CONTINUATION (with the trend) | 3 | **8.9** |
- **RANGE_FADE @ a true extreme: median 15.4%** vs everything else 11.6%.
- CONTINUATION is the **rarest (3) and weakest** — you almost never trade with the trend;
  when you do, it pays least. Your money is in fading exhausted extremes.
- The 7 counter-trend shorts into strong UPtrends (ADX 24–57) worked but paid LESS
  (median 7.7%) — fading a live strong trend is harder than fading a coiled range.

## DIMENSION 4 — COMPRESSION / MATURITY (the magnitude dial)
| condition | n | median mfe% |
|-----------|---|-------------|
| contracting range | 18 | 14.3 |
| non-contracting | 12 | 11.7 |
- Contraction + low ADX = the biggest expansions. The monster moves (S_t29 +36%, H_570
  +27%, D_nov +25%, Da_feb +22%, S_t30 +21%) are ALL low-ADX RANGE_FADEs off a coil.
- Combined with Dim-1: **tight coil (low ADX, contracting) at an extreme → largest run.**

## DIMENSION 5 — LIQUIDITY SWEEP + MULTI-TF NESTING
- Swept extreme confirmed on real tape in **27/30** (from the daily validation).
- Where LTF data exists, the deepest compressions nest RANGE-on-RANGE across TFs
  (daily RANGE + LTF RANGE = S_t29, D_nov, Da_feb — the monsters), OR daily RANGE with
  the LTF still trending DOWN into the discount extreme (V_may_long, S_t30) = you buy the
  exact LTF reversal at the HTF extreme. The HTF gives the WHERE (extreme), the LTF gives
  the WHEN (reversal block + retest).

## THE COMPOSITE WINNER PROFILE (what your best trade looks like, in numbers)
1. Daily regime = **RANGE, ADX < 22** (quiet / coiled), range **contracting**.
2. Price at the **extreme** of that range — PREMIUM to short, DISCOUNT to long (not MID).
3. An **obvious retail liquidity** level at the extreme gets **swept** (wick through, close back).
4. Reversal confirmed, entry on the **retest** of the valid block — tight structural stop.
5. Target = the far side of the range. Bigger coil → bigger payout (ADX inversely ∝ move).
=> Rank order of edge: **RANGE-fade @ extreme  >  counter-trend reversal @ extreme  >
   trend-continuation**;  and  **MID entries = avoid** (fewest, weakest).

## HONEST CAVEATS
- These 30 are your executed WINNERS. This characterises WHAT THE WINNERS LOOKED LIKE
  (exactly what you asked) — it does not by itself prove the same profile FILTERS OUT
  losers. The build test is: does "RANGE + extreme + swept + contracting" separate your
  wins from the setups you SKIP (the ones that looked similar but you vetoed).
- Regime/position are computed on a fixed 40/60-bar window, a proxy for your hand-drawn
  dealing range; directional, not exact. n per cell is small.

## OUT-OF-SAMPLE CONFIRMATION — T31 SBILIFE (7th stock, added AFTER the conclusions)
A fresh trade on a NEW stock (SBILIFE, 30m), resolved on real data to **2024-09-23**,
fits the winner profile point-for-point and is one of the biggest moves in the corpus:
- **SHORT (FVG+OB supply, retest after sweep)**: swept equal-highs liquidity (~1925, poke
  0.21 ATR, clean), range 15% **contracting**, ranging coil → **+27.9% / +24R** to 1750 by
  2024-10-07. RANGE-fade @ the premium extreme, stacked reversal block, far discount target
  = the exact composite profile above, out-of-sample.
- **LONG (BB demand)** earlier: swept the range low, ran to the liquidity (1925) +5.1% — the
  mirror leg. Full cycle (BB-long to sweep the high → FVG+OB-short to the discount) on one chart.
=> the "range + contracting + swept extreme + stacked block" profile predicted a top-tier
trade on a stock not used to derive it. Encouraging, still winners-only (see caveat).

## WHAT THIS GIVES THE BUILD (a concrete, measurable filter)
The decision engine's top gate is now numeric, not vibe:
- **regime gate**: prefer daily ADX < 22 + contracting range (rank the coil).
- **location gate**: entry must be PREMIUM (short) / DISCOUNT (long); **reject MID**.
- **sweep gate**: require the extreme's liquidity swept (already have it, 27/30).
- **grade / size ∝ coil tightness** (lower ADX + more contraction = bigger expected move).
This turns your eagle-eye read into three thresholds the engine can enforce, and gives the
loser-separation test its exact features.
