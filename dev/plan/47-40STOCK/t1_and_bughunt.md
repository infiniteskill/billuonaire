# 47-40STOCK — T1 OTE-GATE (regime-conditional) + WIRED-SYSTEM BUG HUNT

Scope: 40 stocks, one 17–19-day 2026 tape. Source `runs/validate/study40_2026/evidence.parquet`
(44,042 firings; 38,462 decided = hit/loss; na+undecided dropped). Regimes from `_REGIME.md`
(RANGE 21 / UPTREND 8 / DOWNTREND 11). Raw 1m `data/wide/<SYM>.csv` resampled to 1m/5m/15m for the
structural audits. `range_pos` = the **wired** premium/discount reading: causal `merge_asof` of each
firing onto the last `premium_discount` band, `rp = (price − pd_lo)/(pd_hi − pd_lo)`; premium = `rp≥0.62`,
discount = `rp≤0.38`. WIN = `hit=='hit'`; realized edge = `mean(win) − mean(b_hit)`.

## 0. READ-FIRST caveats (govern every number below)
- **Coin-flip frame.** On the symmetric 1-ATR:1-ATR outcome frame every detector wins **47–52%**
  (`orderblock 49.8`, `wyckoff 50.4`, `fvg 49.6`, `sweep 52.2`, `htf_nest 47.2`). The uniform **+6…+13pp
  "edge" over b_hit is a near-constant baseline offset**, not absolute skill — `mfe/mae` are near-identical
  positive magnitudes (median 1.64 / 1.62). So all claims here are about **relative** ranking, not a proven
  win rate. This reconfirms the HAVELLS/HUL "AUC 0.52 coin flip".
- **b_hit is partly circular** (the config's own historical baseline hit-prob); it is the one thing that
  ranks (AUC 0.76) but must never be the sole gate.
- **One regime per stock, thin tape.** Regime labels are a coarse 16-bar snapshot (`_REGIME.md` caveat).
  Per-stock cells are small-n; trust the **pooled/regime** numbers, read per-stock as consistency checks.
- `htf_nest` in the parquet is **99.8% depth-2** (`strength 0.667`; only 3 rows depth-3). The depth-ladder
  is not recoverable from `strength`; the depth analysis uses the anti-signal + range-location tests.

---

# PART (a) — T1 OTE-GATE, REGIME-CONDITIONAL

**Gate (T1 as specified):** count a base only on the correct D1-OTE side — SHORT `rp≥0.62` (premium),
LONG `rp≤0.38` (discount). PASS = meets it; FAIL = mid or wrong side.

## A1. Aggregate PASS vs FAIL win% by regime (all directional firings, decided, rp not-null)
| regime | PASS n | PASS win% | PASS edge | FAIL n | FAIL win% | FAIL edge | **PASS−FAIL** | z |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| **RANGE** | 5233 | **53.0** | +8.5 | 10519 | 48.7 | +7.2 | **+4.3** | 5.1 |
| **UPTREND** | 2181 | **51.6** | +7.0 | 3301 | 46.7 | +5.0 | **+5.0** | 3.6 |
| **DOWNTREND** | 3250 | 48.2 | +6.9 | 4693 | **52.0** | +6.9 | **−3.8** | 3.3 |

Retest-only universe {ob, ob_taught, fvg, fvg_n, wyckoff} gives the same signs
(RANGE +3.3 / UP +3.6 / DOWN −4.5).

**Naïve read = the HUL falsification replicates:** the gate lifts win% in RANGE, and in DOWNTREND
**PASS (49.5-ish) < FAIL** — the gated half is worse. **BUT this aggregate is a Simpson's paradox**, and
it is *not* replicated in UPTREND (gate *helps* +5.0). §A2 dissolves it.

## A2. THE SIMPSON'S PARADOX — within-direction the OTE lever helps EVERYWHERE
| regime | dir | PASS n | PASS win% | FAIL n | FAIL win% | lift | z |
|---|---|--:|--:|--:|--:|--:|--:|
| RANGE | LONG | 2011 | 50.9 | 5920 | 45.9 | **+5.0** | +3.8 |
| RANGE | SHORT | 3222 | 54.3 | 4599 | 52.3 | +2.0 | +1.8 |
| UP | LONG | 470 | 48.5 | 2453 | 47.8 | +0.7 | +0.3 |
| UP | SHORT | 1711 | 52.5 | 848 | 43.4 | **+9.1** | +4.3 |
| DOWN | LONG | 2796 | 46.8 | 1097 | 42.8 | **+4.1** | +2.3 |
| DOWN | SHORT | 454 | 56.8 | 3596 | 54.8 | +2.0 | +0.8 |

**Every one of the six cells is ≥ 0** (SHORT still prefers premium, LONG still prefers discount) — three
are significant, none is negative. The location lever is a robust **within-direction** improvement in all
three regimes. What flips the DOWNTREND aggregate is **composition**:

| regime | LONG-share of PASS | LONG-share of FAIL |
|---|--:|--:|
| RANGE | 38% | 56% |
| UP | 22% | 74% |
| DOWN | **86%** | 23% |

In a downtrend price *sits* at discount, so the OTE gate's PASS bucket is **86% counter-trend LONGs**
(discount-longs = catching the falling knife, 46.8%), while the winning direction (with-trend shorts,
54.8%) *fails* the premium requirement because price rarely retraces to premium. **The gate isn't
selecting losing *locations* — it is selecting the losing *direction*.** HUL's "T1 selects the losers"
is real as a number but the mechanism at 40-scale is direction-mix, not a location inversion.

## A3. Per-stock consistency
- **Within-direction OTE lift (median of L,S per stock):** RANGE **+4.8pp (15/21 stocks >0)**,
  UP **+6.1 (5/6)**, DOWN **+9.3 (7/9)** — positive median in **every** regime.
- **Pooled-per-stock lift (L+S mixed, the composition-confounded view):** RANGE 15/21 (med +5.5),
  UP 4/8 (med +3.1), DOWN **3/11 (med −3.7)** — the downtrend "hurt" is entirely the mixing artifact.

## A4. Continuation gate (the trend alternative: SHORT@discount / LONG@premium)
| regime | cont-side win% (n) | other win% (n) | lift |
|---|--:|--:|--:|
| RANGE | 48.4 (5909) | 51.1 (9843) | −2.8 |
| UP | 46.7 (2403) | 50.1 (3079) | −3.5 |
| DOWN | **53.1 (3529)** | 48.3 (4414) | **+4.8** |

Momentum/continuation location beats fade location **only in the downtrend**. (Uptrend continuation looks
weak only because its "other" bucket contains the good LONG-at-discount dip-buys.)

## A5. VERDICT on T1 — **REPLICATE-with-refinement (RANGE-ONLY as a portfolio lift; UNIVERSAL as a within-direction lever)**
1. As a **within-direction** term (short→premium, long→discount) T1 is a **positive-or-neutral edge in all
   3 regimes and all 6 cells** — safe to apply universally. This *upgrades* the HAVELLS claim: the
   location lever is not range-only; it is a real, stock-general within-direction sorter.
2. As a **portfolio gate applied blind to direction**, T1's value is **regime-conditional and
   composition-driven**: lifts RANGE (+4.3) and UP (+5.0), *hurts* DOWN (−3.8) — because in a downtrend the
   gate over-selects counter-trend discount-longs. **This is the HUL falsification, confirmed at 40-scale
   and re-explained** (Simpson's paradox, not location inversion).
3. **Ship rule:** apply OTE *inside* a direction/regime frame — in a trend, choose the direction by drift
   first (continuation, §A4: +4.8 down), *then* apply OTE within it. Never let OTE pick the direction.
   HUL's "ship behind a trend/range classifier" stands; the classifier's job is **direction selection**,
   after which OTE helps.

---

# PART (b) — WHERE THE WIRED SYSTEM IS WRONG (40-stock bug audit)

## Bug scoreboard
| # | bug | evidence (40-stock) | code / mechanism cause | verdict |
|---|---|---|---|---|
| **B1** | **htf_nest single-swing anchor → invisible extreme** | parent/base band capped a **median 4.87 ATR** *inside* the true causal extreme; **90%** of nests capped >0.5 ATR, **62%** >3 ATR; **92% of stocks NEVER re-anchor a nest to the true high** (median 4.2 ATR gap; BANKBARODA 57 ATR) | `extremes.py` writes EXT Levels **only for confirmed pivots** (`:218 continue` when `confirm_idx is None`); the live extreme stays `pending` (`:154–156`) until a reversal leg ≥ `K·ATR` (leg_pct **6%**) completes → the unmitigated extreme is never a parent. `htf_nest.py:76–85` emits the **base** 5m zone and only ACTIVE bases survive → nests cluster mid-structure | **REPLICATES (all-40, structural)** |
| **B2** | **sweep bar mis-localized** | only **13%** of sweep firings sit on the true poke bar; poke **precedes** firing (median −1 min) by a median **0.73 ATR** shortfall (mean 1.00) | `sweep.py` fires on the **5m candle *close* that reclaims** the swept level (`detect`: latest closed 5m bar + reclaim logic) → the evidence ts/price is the confirmation/retest, not the intra-candle poke | **REPLICATES (all-40, structural)** |
| **B3** | ~~FVG on 1m not native TF~~ | **NOT present here:** `fvg` zones are **99% genuine 5m 3-candle gaps**, `fvg_n` 79%; only ~9% of fvg_n are synthetic (no gap on any TF) | detector default **`tf:"5m"`** (`fvg.py:26`, `fvg_n.py:42`) — FVG already runs on its native TF | **ABSENT** (my first-pass undercount fixed; see B3 note) |
| **B4** | **held-extreme graded as A-setup** | correct-side at-extreme win: RANGE 55.6% → **DOWN 49.6%**; `htf_nest`@extreme **RANGE 60.0% (n70) vs DOWN 32.4% (n34)** — inverts | no sweep+BOS-reversal conjunct on the extreme gate; extreme *location* is scored the same whether swept-and-reversed (range) or tagged-and-held (trend) | **REGIME-CONDITIONAL (RANGE-only edge, inverts on trend)** |
| **F1** | **htf_nest is an over-priced anti-signal** | the **only** detector with negative edge (**−4.7**), **highest b_hit (51.9)**, lowest directional win (47.2); underperforms its own-stock pool by **−1.2 / −4.8 / −4.1** (RANGE/UP/DOWN) | consequence of B1 — nest inherits the parents' high historical b_hit but grades the **capped mid-structure** object | **REPLICATES (all-40)** |
| **F6** | **native confidence is blind; only b_hit ranks** | AUC: `strength` **0.497**, `zone_width` 0.493, `stacking` 0.492 (all blind, regime-invariant); `b_hit` **0.760** (0.758/0.761/0.764 by regime) | `htf_nest` strength is quantized to depth (≈constant); width/stacking carry no outcome signal | **REPLICATES (all-40, strongly)** |
| **L1** | **b_hit==0 firehose** | **23.7% of the book** fires at `b_hit==0` and wins **18.7%**; every retest detector floods it (fvg_n 22%, ob 22%, wyckoff 19%, fvg 17% of the b0-book) and craters within-detector (ob 16.1%, wyckoff 13.8%, **compression 4.8%**) | detectors emit on structure without self-suppressing when their own baseline scores the setup at 0 | **REPLICATES (all-40)** |

### B1 — the invisible-extreme anchor (headline structural bug)
For each nest, `gap = (causal running-max high − zone_hi)/ATR` for SHORTs (mirror for LONGs); positive =
parent band sits **inside** the true extreme.

| regime | n | median gap (ATR) | %>0.5 ATR | %>1 | %>3 |
|---|--:|--:|--:|--:|--:|
| ALL | 1385 | **+4.87** | 90 | 84 | 62 |
| RANGE | 786 | +5.26 | 90 | 85 | 63 |
| UP | 251 | +5.05 | 90 | 83 | 61 |
| DOWN | 348 | +4.38 | 91 | 84 | 59 |

Worst cell = **DOWN SHORT** (median +6.94 ATR, 95% capped): in a persistent downtrend the true high recedes
and the confirmed-pivot anchor never follows. Per-symbol: SHORT nests leave the true high a median **4.2
ATR** above the highest zone_hi *any* nest ever reaches (**92% of stocks**, 56% >2 ATR). This is the
faithful F2 replication at scale, and it is **regime-free** (a code bug, not a regime effect). It also *is*
the root of F1: the nest grades a ~5-ATR-too-low object, so its high baseline never pays off. **Fix = T2:
emit the live *unmitigated* extreme as a parent (don't wait for the 6% reversal-leg confirmation).**

### B2 — sweep localization
Sweep fires on the 5m reclaim close, so tick-exact "swept-the-stop" geometry is **0.73 ATR / ~1 bar off**
the real poke in 87% of cases — regime-invariant (13–14% on-poke everywhere). Consequence: a stop parked at
the sweep *level* is on the wrong side of the actual liquidity grab; **grade sweep/wyckoff levels with an
ATR tolerance, never tick-equality** (confirms HUL D4).

### B3 note — why the FVG "1m bug" is ABSENT (and my first pass was wrong)
A naïve test (does a 3-candle gap exist in the last 3 bars *before the retest firing*?) returned only
3–20% and looked like a bug — but the retest fires long after the gap's birth, so that test is invalid.
Matching each firing's **zone endpoints** (the zone *is* the gap) to any causal 3-candle gap within 0.25
ATR: `fvg` **99% 5m / 72% 1m / 40% 15m** (28% are 5m-gaps invisible on 1m — exactly why 5m is correct),
`fvg_n` **79% 5m / 73% 1m / 43% 15m** (9% synthetic). The detectors already use native 5m; the only residual
is **HTF recall** — a taught 15m/30m FVG is under-emitted (15m match only 40–43%) because tf is fixed at 5m.
So: *not* a 1m-mislocation bug; a *missing-higher-TF-FVG* gap.

### B4 — held-extreme (the regime-conditional trap)
Correct-side firings by range-location × regime:
| regime | AT-EXTREME (≥.85/≤.15) | OTE (.62–.85/.15–.38) | MID |
|---|--:|--:|--:|
| RANGE | 55.6% (1836) | 51.5% (3397) | 49.1% (4610) |
| UP | 54.2% (1054) | 49.2% (1127) | 46.5% (898) |
| DOWN | **49.6% (1350)** | 47.3% (1900) | 48.7% (1164) |

`htf_nest`@extreme: **RANGE 60.0% (n70) vs mid 43.1%** (the range-fade "extreme=A-setup" pattern, +17pp) →
**UP 44.4% < mid 48.9%** → **DOWN 32.4% (n34) < mid 46.5%** (inverts hard). By direction the killers are
**DOWN LONG at-extreme = 48.8% (n1247, knife-catch)** and **UP SHORT at-extreme = 52.8% (n897, held top)**.
Confirms the NEW failure mode: **extreme-location alone grades held-tops/knife-catches as A-setups; conjoin
a confirmed sweep+BOS reversal.**

### F6 detail — the confidence blindness + the b_hit ladder
`strength` quartile win%: 50.0 / 49.4 / 49.0 / 49.9 (flat). `b_hit` bins: **0→18.7 · 0–.25→38.6 · .25–.5→49.6
· .5–.75→64.0 · .75+→82.0** (monotone). Ship: gate on b_hit (drop `b_hit==0`), never on strength/width/stacking.

### ABSENT items (do NOT ship as universal loser-filters)
- **plain `fvg` / `CE_HOLD` as losers — ABSENT at scale**: fvg 48–51% by regime, fvg_n 49%, `CE_HOLD` edge
  **+9.3** (49.6% win). The HAVELLS 42.9/42.3% was stock-specific.
- **F5 "AM-shorts worst" — not tested here** (no intraday session split run; HUL already broke it).

---

## Per-stock table (decided firings; OTE lift = within-direction PASS−FAIL, mean of L,S)
| SYM | reg | n | win% | OTE within-dir lift | htf_nest edge vs pool | b_hit=0 % |
|---|---|--:|--:|--:|--:|--:|
| ABFRL | DOWN | 1123 | 47.6 | −9.3 | +6.5 | 25 |
| ADANIPOWER | DOWN | 972 | 52.4 | +5.1 | −14.9 | 21 |
| ASHOKLEY | DOWN | 1150 | 46.7 | +3.7 | −3.7 | 24 |
| AXISBANK | DOWN | 1046 | 46.3 | +26.5 | +12.6 | 28 |
| BALKRISIND | DOWN | 802 | 54.1 | −4.0 | −3.0 | 22 |
| BANKBARODA | DOWN | 865 | 50.5 | . | . | 26 |
| BERGEPAINT | DOWN | 893 | 49.4 | +41.6 | . | 27 |
| CANBK | DOWN | 956 | 50.5 | +12.5 | +7.2 | 23 |
| CGPOWER | DOWN | 887 | 46.9 | +18.0 | . | 26 |
| COALINDIA | DOWN | 911 | 55.9 | +9.3 | −5.9 | 19 |
| CROMPTON | DOWN | 1032 | 48.2 | . | −10.2 | 22 |
| ADANIENT | RANGE | 935 | 53.0 | +19.5 | −15.5 | 17 |
| ADANIPORTS | RANGE | 837 | 53.6 | +9.5 | −24.0 | 21 |
| ALKEM | RANGE | 992 | 50.8 | +2.1 | +0.4 | 23 |
| APOLLOTYRE | RANGE | 919 | 44.5 | +2.7 | +6.9 | 27 |
| ASIANPAINT | RANGE | 1248 | 46.7 | +11.5 | −1.7 | 28 |
| AUBANK | RANGE | 984 | 53.4 | −4.1 | +5.0 | 22 |
| AUROPHARMA | RANGE | 1150 | 50.3 | +7.8 | −0.3 | 23 |
| BAJAJFINSV | RANGE | 896 | 52.0 | −8.9 | −13.9 | 24 |
| BEL | RANGE | 975 | 48.9 | −6.4 | +2.0 | 28 |
| BHARATFORG | RANGE | 1165 | 48.2 | +1.0 | +4.0 | 23 |
| BHARTIARTL | RANGE | 1031 | 49.8 | +6.2 | +0.2 | 24 |
| BOSCHLTD | RANGE | 868 | 52.4 | −6.7 | . | 22 |
| BPCL | RANGE | 1128 | 52.3 | +21.6 | +6.6 | 22 |
| BRITANNIA | RANGE | 898 | 47.6 | +14.8 | . | 28 |
| CHOLAFIN | RANGE | 969 | 49.8 | +5.6 | −8.8 | 20 |
| CIPLA | RANGE | 938 | 52.6 | +4.8 | +18.9 | 22 |
| COFORGE | RANGE | 889 | 49.0 | +41.5 | −10.9 | 25 |
| COLPAL | RANGE | 990 | 48.2 | +4.2 | +3.5 | 24 |
| DABUR | RANGE | 873 | 51.2 | −6.2 | +15.5 | 22 |
| HAVELLS | RANGE | 954 | 49.5 | +20.3 | −1.1 | 19 |
| VOLTAS | RANGE | 953 | 49.0 | −2.4 | +11.0 | 27 |
| AARTIIND | UP | 890 | 47.2 | +12.9 | −4.3 | 26 |
| ABB | UP | 872 | 50.3 | +19.1 | +7.0 | 24 |
| APOLLOHOSP | UP | 834 | 54.2 | . | −27.9 | 19 |
| BAJAJ-AUTO | UP | 925 | 49.5 | −11.1 | +14.8 | 25 |
| BAJFINANCE | UP | 1033 | 49.2 | +6.0 | −19.5 | 25 |
| BIOCON | UP | 950 | 46.6 | +3.6 | −16.6 | 22 |
| DLF | UP | 818 | 49.5 | +6.2 | +3.1 | 24 |
| TITAN | UP | 911 | 46.7 | . | +3.3 | 30 |

Note the per-stock **htf_nest edge** has high variance (losers crater −15…−28, winners +10…+19); the anti-
signal is a *pooled/regime* fact (17/35 stocks negative but the negatives are far larger), not every-stock.

---

## Tune / bug implications (ranked)
1. **T2 [infra] — emit the live unmitigated extreme as a parent** (don't gate the anchor on a 6% confirmed
   reversal leg). Fixes B1 (median 4.87-ATR cap, 92% of stocks) AND its downstream F1 anti-signal in one move.
2. **L1 — drop `b_hit==0`** (23.7% of book @18.7%). Cleanest, regime-free, all-40. Pair with never gating on
   strength/width/stacking (F6).
3. **Keep `htf_nest` OFF solo** (F1: only negative-edge detector) until T2 lands.
4. **OTE as a within-direction sorter, not a direction picker (T1 refined):** apply short→premium /
   long→discount *inside* a drift-chosen direction. Universal within-direction; regime-conditional in aggregate.
5. **Conjoin extreme-gate with sweep+BOS reversal (B4)** — extreme location alone grades held-tops (UP-SHORT
   52.8%) and knife-catches (DOWN-LONG 48.8%) as A-setups.
6. **ATR tolerance on sweep/wyckoff levels (B2)** — firing is the 5m reclaim, 0.73 ATR off the poke.
7. **[infra] emit 15m/30m FVG** — the only real FVG gap (B3): 5m-only detection under-recalls taught HTF gaps.

## REPLICATE / RANGE-ONLY / TREND-ONLY / ABSENT
- **REPLICATES (all-40, structural, regime-free):** F1 htf_nest anti-signal · F6 confidence-blind /
  b_hit-only · L1 b_hit==0 bleed · **B1 invisible-extreme anchor** · **B2 sweep mis-localization** ·
  **OTE lever within-direction** (A2).
- **RANGE-ONLY / regime-conditional:** T1 as a *portfolio* gate (helps RANGE+UP, hurts DOWN via composition) ·
  **B4 held-extreme / nests-at-extreme** (60% range → 32% downtrend) · nest_depth-as-discriminator (unrecoverable
  here, but the extreme-location proxy inverts on trend).
- **TREND-ONLY:** continuation-location edge (§A4, +4.8 downtrend only).
- **ABSENT:** FVG-on-1m mislocation (detector is native 5m) · plain-`fvg`/`CE_HOLD` as losers ·
  the literal "T1 hurts in *all* trends" claim (uptrend gate *helps* +5.0).
