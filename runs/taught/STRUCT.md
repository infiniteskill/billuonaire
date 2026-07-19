# STRUCT — taught-spec structure tools: build + behavioral detection tests

2026-07-19. Spec: dev/plan/30-LESSONS.md lessons 1, 6, 7, 8, 13, 15.
Data: runs/artifacts-data/l4_h1.parquet (138 NSE syms × H1, 2023-08-04 → 2026-07-17);
secondary spot-check: data/long5m resampled 30m (Apr–Jul 2026, 139 syms).
Scripts: scratchpad ts1_struct.py (tools), ts1_events.py (events + respect tests),
ts1_report.py (cells/stats). 116,528 event rows.

## Build notes

**EXTREMES v2** — ext_zigzag causal zigzag with threshold = 4.7% × close[confirm bar]
(percent-leg floor, TF-invariant) replacing K×ATR. One edge fix vs prototype: guard for a
single bar whose own range ≥ threshold (empty-argmin crash, hit on 30m).
Parity vs hand-marked targets: chart B (H1) 5/8 strict (±3d/1.2%), 7/8 loose (±5d/1.5%);
chart A (30m) 6/8. Misses are tolerance-edge (B1 dp 1.40% vs 1.20% tol; B4 slid +7d to the
deeper low of the same decline; B5 −1d outside window) — same skeleton as the validated
ATR version, slight drift because ATR breathes and a fixed % doesn't.
**Rejection-block band (lesson 13)**: per confirmed pivot, cluster grown from the pivot bar
while neighbor wicks reach the running highest body edge (self-scaling, no ATR); band =
[highest open/close of cluster → wick high] at tops, mirror at lows. Bars restricted to
≤ confirm_idx (causal). Old 0.5×ATR cluster band kept for comparison. Wick band median
height 0.44×ATR vs old band 0.23×ATR; degenerate (no-wick) bands 3.3%.

**CHoCH/BOS (lesson 6)** — causal state machine per symbol. Major levels = zigzag pivots
(usable from confirm bar); minor levels = internal 3/3 fractal swings (confirm lag 3).
Trend seeded by first confirmed pivot, flipped only by major CHoCH. Events (first close
through a level, level then dead until a new pivot confirms): bullish CHoCH = trend-down
close > last major H (major) / last internal swing high (minor); BOS = with-trend break of
last major extreme. ~15 major CHoCH + 157 minor + 25 BOS per sym / 3y.

**Premium/discount (lesson 8)** — dealing range at bar t: hi = max(last two confirmed major
H), lo = min(last two confirmed major L); EQ 50%; pos = (close−lo)/(hi−lo). The literal
"last opposing pair" (1H+1L) makes every major bullish CHoCH sit at pos≥1 by construction,
so the 2H+2L bracket is used; majors are still geometrically pushed toward the "wrong" half
(a major break closes at the range boundary) — bull-only, minor-only and tercile views
reported to de-bias.

**PO3 signature (lesson 15)** — D1 (H1 session resample) candle: body < 0.35×range and one
wick > 0.50×range → completed PO3, predicted direction opposite the big wick. Flags 27% of
D1 candles (~25.7k events).

## Test method

Respect = favorable excursion ≥1×ATR14(TF) before adverse ≥1×ATR from trigger close, in
concept direction; tie-in-one-bar = fail (both real and null); horizon 300 H1 / 60 D1 bars;
undecided excluded. **Null = path-clean forward-window (H1GRID Null B)**: per event, 5
random bars in the event's own forward window (+7..+70 H1 bars ≈ 1–10 sessions; +2..+11 D1),
same direction, same test, trigger = that bar's close — NOT month-uniform (known
path-selection artifact). Splice guard: >20% close→open jumps invalidate any event/null
whose path crosses them. Paired stat: xᵢ = rᵢ − null-meanᵢ; z = mean/sem. Cells: pooled +
temporal thirds (y1/y2/y3 of global span) + crc32(symbol)%2 halves. PASS = prophecy lift
positive in pooled and all 5 cells.

## Results (H1 primary)

lift = event rate − matched null rate (pp/100). Cell signs: y1 y2 y3 | h0 h1.

| test | n | rate | null | lift | z | cells | verdict |
|---|---|---|---|---|---|---|---|
| T1 CHoCH major follow-through | 3,253 | .514 | .483 | +.031 | 3.2 | + + − \| + + | **FAIL** (y3) |
| T1 CHoCH minor follow-through | 23,590 | .506 | .483 | +.023 | 6.3 | + + − \| + + | **FAIL** (y3) |
| T1x BOS follow-through (bonus) | 2,960 | .516 | .486 | +.030 | 2.9 | + + + \| + + | PASS |
| T2 gate all CHoCH (Δlift right−wrong half) | 16.0k/10.5k | — | — | **−.011** | −1.5 | − + − \| − + | **FAIL** |
| T2 gate bull-only (discount−premium) | 6.7k/5.1k | — | — | −.005 | −0.4 | + − − \| − + | **FAIL** |
| T2 gate major-only | 479/2,774 | — | — | −.009 | −0.3 | − + − \| + − | **FAIL** |
| T3 wick-band retest rejection | 8,096 | .478 | .488 | −.010 | −1.6 | − − + \| − − | **FAIL** |
| T3 atr-band retest rejection (old) | 6,182 | .468 | .488 | −.020 | −2.8 | − − + \| − − | **FAIL** |
| T3 head-to-head wick − atr | — | — | — | **+.010** | — | + + + \| + + | wick > atr, all 6 cells |
| T4A PO3 next-candle direction | 25,731 | .514 | .498 | +.016 | 4.6 | + + + \| + + | **PASS** |
| T4B PO3 wick-zone retest respect | 19,864 | .494 | .496 | −.002 | −0.4 | + − − \| − − | **FAIL** |
| T5B majors preceded by minor ≤50 bars | 3,271 | .935 | — | — | — | .90 .94 .96 \| .94 .93 | sanity OK |
| T5P minor CH → major CHoCH ≤50 bars | 23,581 | .290 | .183 | **+.107** | 32.5 | + + + \| + + | **PASS** |

T2 tercile sensitivity (direction-normalized pos; taught law predicts lift falling
left→right): deep-favorable +.015 (z 2.3) < mid +.028 (z 5.0) < deep-unfavorable +.034
(z 4.7) — **monotone in the WRONG direction**. The photon gate is not merely unproven; on
this tape location-right CHoCHs follow through slightly worse.

## 30m secondary spot-check (Apr–Jul 2026, pooled only)

Every H1 sign replicates: T1 minor +.023 (z 2.2), T1 major +.013, T3 wick −.011 / atr
−.034 (wick > atr again), T5P +.080 (z 10.4), T5B 95.6%, T2 right-half +.017 <
wrong-half +.029 (inverted again). Behavior is TF-invariant.

## Verdicts per tool

1. **EXTREMES v2 (4.7% zigzag + wick band)** — build OK, parity near the validated ATR
   version. As a *zone* the extreme band FAILS detection (retest-rejection ≤ null; the old
   band significantly anti, −.020 z −2.8). But the lesson-13 wick band beats the 0.5×ATR
   guess in **all 6 cells** (+.010 pooled): the taught band is the better band — of a tool
   that doesn't clear null. Keep as anchor geometry, not as entry zone.
2. **CHoCH/BOS** — real but small and decaying follow-through: +2–3pp over matched null,
   z 3–6, positive in 4/5 cells, sign flips in the final third (y3) → strict FAIL. BOS
   (continuation) passes all cells — consistent with the momentum pivot in MEMORY. Major >
   minor pooled (+.031 vs +.023) as taught, weakly. Sequencing grammar is the strongest
   finding: 93.5% of majors are preceded by a same-direction minor (T5B), and a minor CH
   raises P(major flip ≤50 bars) from 18.3% → 29.0% (T5P, z 32, all cells; caveat below).
3. **Premium/discount gate** — **FALSIFIED** on this tape: Δlift negative pooled, mixed
   cells, tercile gradient monotone opposite the taught law, replicated at 30m. The
   "bullish CHoCH in premium = false signal" claim does not detect; if anything late/deep
   breaks (already-moved) follow through more — momentum, not mean-reversion to EQ.
4. **PO3 signature** — the only clean taught PASS: small-body/big-wick candle predicts next
   D1 candle opposite the wick at 51.4% vs 49.8% matched null (z 4.6, all cells, both
   halves, all thirds). Tiny edge, real sign. Its wick range as a retest zone: dead (T4B ≈ 0).

## Honest caveats

- T5P lift is partly mechanical: after the major flip fires, same-direction majors can't
  re-fire, so forward-window null bars are depressed by the state machine's own ordering.
  The robust claim is T5B (93.5% sanity) + sign; the +10.7pp magnitude is an upper bound.
- All passing lifts are 1.6–3pp on a ~50% base — detection-grade recognition, nowhere near
  toll-clearing economics (consistent with FACTS/H1GRID: recognition real, net ≈ 0).
- T2 majors are geometrically biased toward the wrong half by the break itself; bull-only
  and tercile views correct for this and still fail.
- pos uses the 2H+2L bracket, one pragmatic step beyond the literal "last opposing pair"
  (which is degenerate for major CHoCH); minor-only gate (cleanest geometry) also fails.
- y3 (Aug-2025→Jul-2026) kills T1: structure follow-through decayed in the most recent
  year. Any use of CHoCH as a trigger must assume regime fragility.
