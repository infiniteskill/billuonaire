# DGRID — definitive combination x geometry sweep (4H + DAILY, pure SMC)

Question: does any zone-type x elimination-flag x stop/exit geometry cell at 4H or
DAILY carry edge **in excess of matched drift**? Anchor: LADDER.md (M15/H1/H4 excess~0,
buy-hold 18.4%/yr beat every config); fade thesis already falsified at 5m.

## Design

- **4H arm**: `l4_h1.parquet` H1, session-aware 2 buckets/day (09:15-12:15, 12:15-15:30),
  138 syms, 2023-08-16 -> 2026-07-17 (~3y).
- **DAILY arm**: `dailymax.parquet`, NIFTY dropped, cut >= 2001-07-01 (25y; pre-2001
  thin-universe years excluded), 138 syms, 2001-07-23 -> 2026-07-17.
  Residual early-era thinness handled by the matched null (same symbol, same quarter).
- **Data hygiene**: splice guard (LADDER rule) — symbol history cut at >25% close->open
  jumps; nothing spans a splice (kills unadjusted single-row spikes, e.g. BEL 2005-07-28
  7.6->251->7.6, GLENMARK 2003-04-02). ATR-eligibility floor 0.2% of close (D1) /
  0.14% (4H) on real signals AND null pool, symmetric (tiny-SL blowup guard).
- **Zones** (native-TF, ports of hulinv_run/chartpar_run): FVG (wick-valid 3-candle gap,
  displacement close + adaptive range%-threshold), OB (lux swing-break origin box),
  BREAKER (EmreKb zz9 MSB swept-swing origin candle), iFVG (FVG closed-through,
  flipped zone born at invalidation). Entry: first retest (band overlap, zone not
  closed-through on the touch bar) -> next-bar open, fade direction. Dedup (type,dir,entry-bar).
- **Flags**: F1 birth in a prior bar-period (4H: prior session; DAILY: prior ISO week)
  than the retest. F2 HTF-nest: zone midpoint inside a live direction-matched HTF OB/FVG
  (4H: D1 zones from the same H1, prior sessions only; DAILY: W-FRI weekly zones, prior
  weeks only; live = confirmed and no HTF close beyond far edge yet). F3 sweep-aligned:
  birth <=3 bars after the first sweep (wick-through + close-back) of an EQ pool (2+
  same-side 5/5 fractal swings within 0.25xATR14), direction-aligned. F4 gap-origin:
  |open(birth) - close(birth-1)| >= 0.5xATR14.
- **Geometry**: stop k in {1.5, 2.5} x ATR(14,TF) (SMA-TR, detector formula); exits
  {2R tgt + 10-bar time-stop, 3R tgt + 20-bar}. Gap-through stop AND target fill at the
  actual next open, both directions — daily gaps are the whole risk, modeled honestly
  (post-guard worst single trade ~ -7R).
- **Costs** (delivery): STT 0.1% both legs, exch 0.004%, DP Rs15/sell, slip 2bp/leg;
  Rs1L capital, 0.5% risk (Rs500), notional cap 5x; R = actual rupee risk; fractional
  qty. Shorts costed identically (futures-only in practice; slightly overstated).
- **Nulls (mandatory)**: per trade, 5 random entries from the SAME symbol + calendar
  quarter, same direction/geometry/costs. Two stop conventions: `null` = the null bar's
  own ATR (task spec); `null_vol` = same stop-%-of-price as the real trade (controls the
  artifact where real entries carry post-displacement elevated ATR, so drift costs them
  fewer R than it costs low-ATR random bars). excess = net_R - null; exV = net_R - null_vol.
- **Gauntlet**: temporal thirds (4H: ~1y each; DAILY: 2001-07/2009-11/2018-03, ~8.3y)
  x crc32(sym)%2 symbol halves. ALIVE = excess>0 pooled AND >0 in all 3 eras AND both
  halves (task-spec, ATR-null based).

**Multiple testing**: 96 cells/arm defined (4 zones x 6 flagsets x 2 stops x 2 exits),
192 populated total; directions inspected inside each => ~384 looks (and the 2 stop
widths share identical signal sets, so cells are heavily correlated). Isolated excess>0
is expected by chance; only gauntlet survivors with coherent structure count.

## Pooled per arm: net vs the two nulls, costs

| arm | rows | net_R | null(ATR) | excess | null(vol) | exV | cost_R | cost k=1.5 | k=2.5 |
|---|---|---|---|---|---|---|---|---|---|
| H4 | 108740 | -0.097 | -0.114 | +0.017 | -0.115 | +0.018 | 0.108 | 0.128 | 0.089 |
| D1 | 267372 | -0.084 | -0.112 | +0.027 | -0.120 | +0.036 | 0.071 | 0.082 | 0.061 |

Costs at these TFs are small in R (stops are a few % of price), ~0.06-0.13R/trade,
k=2.5 cheaper than k=1.5 (smaller notional per R).

## Long/short decomposition (pooled per arm, all zone types, all flags)

| arm | dir | n | net_R | null(ATR) | excess | null(vol) | exV |
|---|---|---|---|---|---|---|---|
| H4 | LONG | 54336 | -0.010 | -0.080 | +0.070 | -0.074 | +0.065 |
| H4 | SHORT | 54404 | -0.185 | -0.149 | -0.036 | -0.156 | -0.029 |
| D1 | LONG | 133596 | +0.014 | -0.027 | +0.041 | -0.029 | +0.043 |
| D1 | SHORT | 133776 | -0.183 | -0.196 | +0.014 | -0.211 | +0.028 |

Raw long net_R rides the India drift — the null carries the same drift, so only the
excess columns are evidence. Any 'long edge' whose null is equally positive is drift.

## Top-10 cells by excess (n >= 30)

| arm | zone | flags | k | exit | n | net_R | null | excess | t | exV | tV | eras | halves | exL(n) | exS(n) | ALIVE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H4 | BRK | F1+F3 | 1.5 | 3Rx20 | 38 | +0.231 | -0.248 | **+0.480** | +1.43 | +0.491 | +1.47 | +/+/+ | +/+ | +0.268(20) | +0.715(18) | **YES** |
| D1 | FVG | F1+F2+F3 | 2.5 | 3Rx20 | 135 | +0.093 | -0.234 | **+0.327** | +4.03 | +0.307 | +3.77 | +/+/+ | +/+ | +0.473(74) | +0.150(61) | **YES** |
| D1 | BRK | F1+F2+F3 | 1.5 | 3Rx20 | 38 | -0.032 | -0.341 | **+0.309** | +1.32 | +0.256 | +1.03 | −/+/+ | +/+ | +0.546(15) | +0.155(23) | no |
| H4 | IFVG | F1+F2+F3 | 2.5 | 3Rx20 | 138 | +0.042 | -0.239 | **+0.281** | +2.58 | +0.271 | +2.51 | +/+/+ | +/+ | +0.309(63) | +0.257(75) | **YES** |
| H4 | IFVG | F1+F2+F3 | 1.5 | 3Rx20 | 138 | +0.052 | -0.207 | **+0.259** | +1.84 | +0.271 | +1.96 | +/−/+ | +/+ | +0.273(63) | +0.247(75) | no |
| D1 | FVG | F1+F2+F3 | 1.5 | 3Rx20 | 135 | +0.106 | -0.130 | **+0.236** | +1.92 | +0.253 | +2.12 | +/+/+ | +/+ | +0.328(74) | +0.125(61) | **YES** |
| H4 | OB | F1+F3 | 1.5 | 3Rx20 | 652 | -0.032 | -0.255 | **+0.223** | +3.51 | +0.230 | +3.61 | −/+/+ | +/+ | +0.312(313) | +0.141(339) | no |
| D1 | OB | F1+F2 | 1.5 | 3Rx20 | 15400 | -0.133 | -0.352 | **+0.218** | +19.31 | +0.229 | +20.41 | +/+/+ | +/+ | +0.272(7432) | +0.169(7968) | **YES** |
| D1 | BRK | F1+F2+F3 | 1.5 | 2Rx10 | 38 | -0.081 | -0.290 | **+0.209** | +1.01 | +0.083 | +0.38 | −/+/+ | +/− | +0.467(15) | +0.041(23) | no |
| D1 | BRK | F1+F3 | 1.5 | 2Rx10 | 96 | +0.057 | -0.152 | **+0.209** | +1.64 | +0.158 | +1.24 | −/+/+ | +/+ | +0.375(44) | +0.068(52) | no |

## Flags=none baseline (the raw retest-timing effect, per zone type)

Excess of the UNFILTERED first-retest cells (mean over the 4 geometry variants; the
same signals underlie all four). If this is already positive, the elimination flags
are refinements of a generic pullback-timing effect, not its source.

| arm | zone | n/geom | net_R | null | excess | exV | exL | exS |
|---|---|---|---|---|---|---|---|---|
| H4 | FVG | 7160 | -0.070 | -0.032 | -0.038 | -0.042 | +0.027 | -0.120 |
| H4 | OB | 13221 | -0.104 | -0.173 | +0.069 | +0.074 | +0.108 | +0.031 |
| H4 | BRK | 667 | -0.109 | -0.216 | +0.108 | +0.099 | +0.079 | +0.127 |
| H4 | IFVG | 6137 | -0.114 | -0.074 | -0.040 | -0.042 | +0.044 | -0.111 |
| D1 | FVG | 9488 | -0.021 | +0.095 | -0.115 | -0.102 | -0.104 | -0.133 |
| D1 | OB | 47343 | -0.097 | -0.171 | +0.074 | +0.081 | +0.092 | +0.056 |
| D1 | BRK | 2183 | -0.089 | -0.182 | +0.092 | +0.099 | +0.117 | +0.076 |
| D1 | IFVG | 7829 | -0.081 | +0.018 | -0.099 | -0.089 | -0.076 | -0.115 |

## Gauntlet survivors (ALIVE, task-spec excess)

78 of 188 qualifying cells are ALIVE on the
task-spec (ATR-null) excess. Survivors with net_R>0 (the only economically live ones):

| arm | zone | flags | k | exit | n | net_R | excess | t | exV | tV | exL | exS | trades/qtr |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H4 | BRK | F1+F3 | 1.5 | 3Rx20 | 38 | +0.231 | +0.480 | +1.43 | +0.491 | +1.47 | +0.268 | +0.715 | 4.8 |
| D1 | FVG | F1+F2+F3 | 2.5 | 3Rx20 | 135 | +0.093 | +0.327 | +4.03 | +0.307 | +3.77 | +0.473 | +0.150 | 2.3 |
| H4 | IFVG | F1+F2+F3 | 2.5 | 3Rx20 | 138 | +0.042 | +0.281 | +2.58 | +0.271 | +2.51 | +0.309 | +0.257 | 11.5 |
| D1 | FVG | F1+F2+F3 | 1.5 | 3Rx20 | 135 | +0.106 | +0.236 | +1.92 | +0.253 | +2.12 | +0.328 | +0.125 | 2.3 |
| D1 | FVG | F1+F3 | 1.5 | 3Rx20 | 443 | +0.086 | +0.107 | +1.57 | +0.116 | +1.76 | +0.162 | +0.028 | 5.3 |
| D1 | FVG | F1+F3 | 2.5 | 3Rx20 | 443 | +0.044 | +0.051 | +1.04 | +0.062 | +1.33 | +0.092 | -0.006 | 5.3 |

The other 72 ALIVE cells all have net_R <= 0: their 'excess' means the real
entries lose LESS than matched random entries — timing without economics. Nothing
to trade there.

## Verdict

- **Search scale**: 192 populated cells (~384 directional looks), heavily correlated
  (stop widths share signal sets). Bonferroni bar for 192 tests at 5%: |t| >= ~3.7.
- **A real, non-drift timing regularity exists — and it is not money.** 140/188
  qualifying cells show excess>0 (137/188 on the vol-matched null too — so it is not
  the elevated-ATR artifact), 78 are ALIVE per the task gauntlet, and 42 clear the
  Bonferroni bar. But **38 of those 42 have net_R < 0**: zone-retest entries beat
  matched random same-quarter entries by +0.05..+0.22R (d1 OB F1+F2: excess +0.218,
  t=19.3, exV +0.229, tV=20.4, all eras +, both halves +, ~152 trades/qtr) while still
  LOSING −0.07..−0.25R per trade after delivery costs. Direction-symmetric (that cell:
  exL +0.27 / exS +0.17) and already present at flags=none — i.e. generic
  pullback/mean-reversion timing that the flags concentrate but did not create.
  Timing without economics: nothing to trade.
- **Drift owns the long side.** Pooled d1 longs: net +0.014 vs null −0.027; every raw
  long positive is matched by its null. Pooled shorts: net −0.18, negative in every
  large cell. There is no long edge beyond drift and no short edge at all.
- **The single positive-net multiplicity survivor** — d1 FVG F1+F2+F3 k=2.5 3Rx20
  (n=135 over 25y = **2.3 trades/quarter across 138 symbols**, net +0.093R, excess
  +0.327, t=4.03, exV +0.307): entirely long-driven (longs +0.389R net on 74 trades;
  shorts −0.267R on 61 — drift again), and its k=1.5 sibling on the SAME 135 signals
  drops to t=1.9 — the significance is geometry-dependent. Taken at face value it
  earns ~0.4%/yr on capital vs 18.4%/yr buy-hold. A curiosity, not a strategy.
  (h4 IFVG F1+F2+F3 k=2.5: net +0.042R, t=2.6 — below the multiplicity bar; h4 BRK
  F1+F3: n=38, t=1.4 — noise.)
- **Verdict: DEAD.** Pure-SMC zone fading (FVG / OB / BREAKER / iFVG, first-retest,
  fade) has no deployable excess-over-drift edge at 4H or DAILY under any elimination
  combination (F1 rest, F2 HTF-nest, F3 sweep-aligned, F4 gap-origin) or geometry,
  at delivery costs — completing the ladder: 5m, M15, H1, H4, 4H-native, DAILY all
  negative. The one measurable residue (~0.1−0.2R of retest-timing value, robust to
  both nulls) is consumed by costs + adverse selection; at most it is a component to
  recycle inside the momentum program, not a standalone system.

*Generated 2026-07-19 by dgrid_run.py / dgrid_report.py (scratchpad, prefix dgrid_).*
