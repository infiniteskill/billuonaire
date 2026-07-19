# CHARTPARITY — hand-drawn Zerodha zones vs our detectors

**Question:** do `ob_lux` + `fvg_cb` find the zones the user hand-drew on ASIANPAINT 15m and
HINDUNILVR 30m, and how much extra do they emit around them (noise ratio)?

**Method / route.** Core zone rules were **replicated standalone** from the detector sources —
`app/trader/detectors/ob_lux.py` (LuxAlgo internal OB: swing pivot size=5, close-cross structure
break, anchor = min parsed-low / max parsed-high over [pivot..confirm] with the ≥2×trailing-ATR(14)
high-volatility low/high swap) and `app/trader/detectors/fvg_cb.py` (3-candle gap, c2 close beyond
origin edge, gap% > running mean bar-range% threshold, ATR-availability gate) — rather than wiring
StockContext/LevelEngine. Both detectors are documented faithful ports of standalone reference scans
(luxob.py / fvg2.py), so the standalone re-scan IS the validated behavior; counts below are raw
zone-creation events (live overlap-dedupe / mitigation changes what is *concurrently visible*, not
how many zones the rules *emit*). Data: `data/long5m/*.csv` (2026-04-27 → 2026-07-17, 57 sessions),
plain OHLC resample 5m→15m and 5m→30m anchored to the 09:15 session open (matches Zerodha bars).
Script: scratchpad `chartpar_run.py` / `chartpar_swings.py`.

**Match rule.** FOUND = one of our zones covers ≥50 % of the user band and is born within ±3
sessions of the stated birth; PARTIAL = ≥50 % cover out-of-window, or 20–50 % cover in-window;
side-correct = demand→`*_BULL`, supply→`*_BEAR`. "Union" = user-band coverage by the union of all
side-correct in-window zones.

## 1. Zone verdicts

### ASIANPAINT 15m

| zone | user band (born) | our best side-correct zone | verdict | union |
|---|---|---|---|---|
| A1 supply | 2755–2778 (~15/06) | OB_BEAR [2763.8, 2771.0] b.16/06 10:45 (31 %) + OB_BEAR [2752.0, 2762.0] b.17/06 | **PARTIAL** | 62 % |
| A2 demand | 2605–2628 (05–08/06) | FVG_BULL [2615.2, 2634.8] b.02/06 12:30 (56 %); also OB_BULL [2607.9, 2614.5] b.02/06 q=0.83 | **FOUND** | 84 % |
| A3 demand | 2558–2578 (~18/05) | FVG_BULL [2514.0, 2571.0] b.13/05 09:15 (65 %); also OB_BULL [2556.0, 2567.8] b.**18/05** 10:15 (49 %, q=0.78) | **FOUND** | 65 % |
| A4 demand | 2408–2440 (27/04–04/05) | OB_BULL [2416.4, 2423.5] b.05/05 12:30 (22 %) | **PARTIAL** | 40 % |
| A5 demand | 2115–2155 (23–30/03) | — data starts 27/04 | **OUT-OF-DATA** | — |

Direction-agnostic footnote: A1 and A4 are each 60–100 % covered by an opposite-direction gap FVG
born on the right bar (A1: FVG_BULL [2750.0, 2785.9] b.15/06 09:15 gap-up; A4: FVG_BEAR
[2419.6, 2444.4] b.30/04 gap-down). Geometry is there; the emitted *side* is not what the user drew.

### HINDUNILVR 30m

| zone | user band (born) | our best side-correct zone | verdict | union |
|---|---|---|---|---|
| H1 FVG | 2185–2212 (03–06/07) | FVG_BEAR [2180.6, 2203.1] b.08/07 09:15 (67 %) | **FOUND** | 81 % |
| H2 OB/prop | 2103–2132 (09–12/06) | OB_BULL [2100.2, 2109.6] b.08/06 13:15 (23 %) — its **first retest lands mid-July**, exactly the user's story; the 2114–2132 body only gets drawn later (OB_BULL [2114.5, 2124.6] b.30/06 = user's first-retest date; FVG_BULL b.17/07) | **PARTIAL** | 23 % |
| H3 FVG | 2108–2136 (16–17/07) | FVG_BULL [2102.6, 2127.2] b.17/07 09:15 (69 %) | **FOUND** | 69 % |
| H4 demand | 2050–2097 (early June) | OB_BULL [2073.0, 2091.0] b.03/06 (38 %); + OB_BULL b.02/06 [2066.0, 2076.9], b.04/06 [2074.3, 2084.1] | **PARTIAL** | 53 % |

**Scoreboard (side-correct): 4 FOUND, 4 PARTIAL, 0 MISSED, 1 out-of-data.** Nothing the user drew
is invisible to the rules; the PARTIALs are ours being *narrower slices* of the user's fat
hand-drawn blocks (H4 is a 47-pt block, our OBs are 10–18-pt) or the right bar with the wrong side
(A1/A4 gap FVGs).

## 2. Noise ratio ("findings many, genuine few")

| symbol/tf | OB | FVG | total emitted | user drew (in-window) | ratio | per session |
|---|---|---|---|---|---|---|
| ASIANPAINT 15m | 118 (58▲/60▼) | 44 (30▲/14▼) | **162** | 4 | **40 : 1** | 2.8 |
| HINDUNILVR 30m | 58 (29▲/29▼) | 23 (13▲/10▼) | **81** | 4 | **20 : 1** | 1.4 |

Genuine proxy — first retest gets a ≥2×ATR(tf) favorable move within 12 bars:
ASIANPAINT **52/162 (32 %)** genuine, 11 never retested; HINDUNILVR **32/81 (40 %)**, 10 never
retested. So even by a generous mechanical standard, two-thirds of emissions are noise.

## 3. Filter experiment

| filter | ASIANPAINT kept | HINDUNILVR kept | user-matched zones kept |
|---|---|---|---|
| swing-adjacent (born ±5 bars of a ≥2 ATR-prominence 5/5 fractal swing) | 103/162 | 54/81 | A1 ✓ A2 ✗ A3 ✗ A4 ✗ · H1 ✗ H2 ✓ H3 ✓ H4 ✓ |
| revisit delay ≥1 h | 101/162 | 68/81 | A1 ✓ A2 ✓ A3 ✗ A4 ✓ · H1 ✓ H2 ✓ H3 ✓ H4 ✗ |
| **both** | **63/162** | **47/81** | **A: 1/4 · H: 2/4** |

**Verdict: the two filters do NOT reproduce the user's selection.** They shrink the pile only
~1.7–2.6×, still leaving 47–63 zones vs the user's 4, *and* they drop most of the zones that matched
the user's picks. Mechanism: the user's picks are dominated by **session-open gap FVGs (born
09:15)** — these sit far from any intraday fractal swing (fails swing-adjacency) and are often
touched within the first hour (fails the 1-h delay). The genuine-reaction proxy is equally
unaligned (True for A4/H2/H3/H4, False for A1/A2/A3/H1). Whatever the user's eye is selecting on,
it is not "born at a big swing" or "left alone for an hour" — the strongest common trait of their
set is *overnight-gap origin + revisited days-to-weeks later*, which none of the tested filters
encodes.

## 4. Swings (HINDUNILVR 30m, fractal 5/5 per `swings.py` strict rule)

All 4 user-marked swings are found: SH ~2225 → 2224.4 @ 17/06 10:45 (+2221.4 @ 18/06);
SH ~2245 → 2238.8 @ 03/07 09:15; SL ~2085 → 2080.0 @ 03/06 (+2091.7 @ 08/06);
SL ~2100 → 2091.0 @ 15/07 / 2096.2 @ 16/07 14:45.

Total emitted: **84 swings vs their 4 (21 : 1)**. Prominence filter sweep (prom = min flank
excursion, vs trailing ATR14):

| threshold | swings kept | user marks kept |
|---|---|---|
| ≥2.0 ATR | 48 | 4/4 |
| ≥2.5 ATR | 23 | 3/4 |
| ≥3.0 ATR | 8 | 1/4 |
| ≥4.0 ATR | 1 | 0/4 |

≥2 ATR keeps all 4 marks but only halves the pile (48 ≠ ~4); tightening sheds the user's marks
faster than it converges. **The extreme-swing filter does not isolate their marks either.**

## Caveats

- User bands transcribed ±0.3 %, births ±3 sessions; verdicts are tolerant by construction.
- Raw emission counts; ob_lux's live ACTIVE-overlap dedupe + LevelEngine mitigation thin the
  *simultaneously visible* set, but the per-session emission rate (1.4–2.8 zones/day/symbol) is the
  honest measure of the "findings many" complaint.
- HINDUNILVR 30m last bar of each session is the 15:15 partial (15:15–15:25), same as Zerodha.
