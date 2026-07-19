# CASCADE — elimination-cascade hypothesis test (zone revisit delay × extreme swing)

**Hypothesis (user, from manual charts)**: a genuine OB/FVG zone is NOT retested immediately.
First retest <30min after creation ⇒ small-TF noise, invalid. First retest ≥1hr later, or on a
LATER DAY ⇒ genuine — price returns with direction. Extra filter: zone must sit near an EXTREME
swing (one that produced a ≥2 ATR move), not a minor swing.

## Method

- **Data**: `signals60` (300,153 signals) + `data/long5m/*.csv` (native 5m continuum, 57 sessions).
- **Detectors**: `fvg_cb`, `ob_lux`, `mitigation` — the three whose zone birth is exactly
  reconstructable from the signal's `zone_lo/zone_hi` against the 5m series (fvg: 3-bar gap
  `(c1.high, c3.low)`, born = c2; ob_lux: anchor bar's raw `(low, high)`, born = anchor;
  mitigation: block candle body `(min(O,C), max(O,C))` + color, born = block). Backward
  most-recent-match with causality guards. **Match rates: fvg_cb 99.9%, ob_lux 99.9%,
  mitigation 100.0%** (158.6k signals matched). **Dropped**: `bpr` (zone = overlap of two gaps —
  composite bounds, not cleanly recoverable) and `compression_fade`/`inducement`/`turtle_soup`
  (not created-zone-retest detectors; hypothesis doesn't apply). Not faked, just excluded.
- **Unit of analysis**: FIRST retest per zone (80,636 zones) — the hypothesis classifies zones by
  their first-retest delay. All-signals view checked too (same conclusions).
- **Delay** = signal bar − birth bar (5m trading bars); same-session buckets <30m / 30–60m /
  1–4h / >4h; different session ⇒ next-day+.
- **Outcome sim** (uniform, per task spec): entry next-bar open, stop 1.5×ATR(5m,14), fixed 1R
  target, intrabar stop-first, EOD close 15:10, costs 0.06% notional round-trip. MFE/MAE = full
  entry→EOD excursions in ATR. (Lighter costs than RESULTS.md's realistic-fill engine, hence
  base netR −0.19 here vs −0.24..−0.30 there; hit% consistent.)
- **Extreme swing**: 5/5 fractal on the 5m continuum; prominence = excursion from swing before
  violation, measured only with pre-signal data (no lookahead); "near" = swing within 1 ATR of
  zone, prominence ≥2 ATR. Strict variant: ≥3 ATR prominence, ≤0.5 ATR distance.
- **Holdouts**: temporal split at 2026-06-08 (T1/T2) + `crc32(symbol)%2` (C0/C1). Lift counts
  only if same-sign in all four cells. Bar: **+6pp over base hit% ≈ breakeven** at this cost scale.

## Delay distribution — the premise itself is wrong-shaped

First retest per zone (share %, same-day delay quartiles):

| detector | zones | q25/med/q75 same-day | <30m | 30–60m | 1–4h | >4h | next-day+ |
|---|---|---|---|---|---|---|---|
| fvg_cb | 15,225 | 10/10/25 min | **64.5** | 9.3 | 9.6 | 1.4 | 15.2 |
| mitigation | 42,955 | 20/30/60 min | 28.8 | 21.1 | 16.8 | 1.1 | 32.2 |
| ob_lux | 22,456 | 35/50/85 min | 9.9 | 29.7 | 29.3 | 1.7 | 29.4 |

Most zones are retested fast (fvg median 10 min). Only 15–32% survive to a later day.

## Bucket outcomes (first retest per zone, k=1.5 stop / 1R target, net of costs)

| bucket | n | hit% | netR | MFE | MAE | | fvg hit% | mit hit% | ob hit% |
|---|---|---|---|---|---|---|---|---|---|
| <30m | 24,385 | 45.8 | −0.183 | 2.67 | 2.63 | | 46.9 | 44.9 | 45.8 |
| 30–60m | 17,148 | 45.1 | −0.202 | 2.60 | 2.68 | | 44.1 | 44.7 | 45.8 |
| 1–4h | 15,276 | 44.9 | −0.218 | 2.60 | 2.78 | | 44.6 | 43.9 | 46.1 |
| >4h | 1,089 | **34.8** | **−0.259** | 1.78 | 2.13 | | 43.9 | 30.7 | 33.6 |
| next-day+ | 22,738 | **48.4** | **−0.156** | 3.17 | 3.26 | | 47.5 | 48.5 | 48.7 |
| **base (all)** | 80,636 | 46.1 | −0.186 | 2.78 | 2.84 | | 46.4 | 45.8 | 46.6 |

Three of the hypothesis's four claims fail on contact:

1. **"<30min = noise" — FALSE.** Quick retests perform AT base (45.8 vs 46.1), and for fvg_cb
   <30m is its *best* same-day bucket (46.9%, netR −0.144, its best netR anywhere same-day).
2. **"≥1hr same-day = genuine" — BACKWARDS.** 1–4h is below base (44.9, −1.2pp) and >4h same-day
   is the worst cell in the whole study (34.8%, netR −0.26). A zone that sits untouched all day
   and gets hit late is being run over, not respected. The ≥1h-same-day variant is **−1.8pp**.
3. **"Near extreme swing" — VACUOUS at 5m.** 94.5% of zones pass the 2 ATR/1 ATR test; the
   strict 3 ATR/0.5 ATR version still passes 85% and adds **+0.0pp** alone. On 5m data, 2-ATR
   swings are everywhere; the filter does not discriminate. (Cross-tab: near_ext=yes improves
   next-day+ by ~3pp over near_ext=no next-day+, but the "no" cell is only n=878 — noise-sized.)
4. **"Later-day retest = genuine" — the one survivor.** +2.3pp hit, +0.030R, MFE 3.17 vs 2.67,
   holdout-stable 4/4.

## Composite cell (the full recipe: delayed ≥1h-or-next-day AND near extreme swing)

| cell | n | hit% | netR | lift vs base |
|---|---|---|---|---|
| composite pooled | 37,253 | 46.9 | −0.180 | **+0.7pp** / +0.006R |
| composite fvg_cb | 3,800 | 46.2 | −0.183 | −0.2pp (holdout-UNSTABLE: T2/C0/C1 negative) |
| composite ob_lux | 13,204 | 47.2 | −0.181 | +0.6pp |
| composite mitigation | 20,249 | 46.8 | −0.179 | +1.0pp |
| best variant: next-day+ only | 22,738 | 48.4 | −0.156 | +2.3pp / +0.030R |
| next-day+ & strict-ext | 20,093 | 48.5 | −0.153 | +2.4pp / +0.033R |

The ≥1h-same-day leg drags the composite down to +0.7pp; dropping it (next-day+ only) is
strictly better, and the extreme-swing leg adds +0.1pp on top — i.e. the entire live content of
the recipe is "zone retested on a later day".

## Holdouts (pooled, first retest per zone; lift = cell hit% − cell base hit%)

| condition | T1 | T2 | C0 | C1 | same-sign 4/4? |
|---|---|---|---|---|---|
| composite (delayed & near_ext) | +1.1pp | +0.4pp | +0.8pp | +0.6pp | yes (hit & netR) |
| next-day+ only | +2.8pp | +1.9pp | +2.5pp | +2.1pp | yes (hit & netR) |
| next-day+ & strict-ext | +3.0pp | +1.9pp | +2.5pp | +2.2pp | yes (hit & netR) |
| composite, fvg_cb only | +0.3pp | −0.8pp | −0.1pp | −0.4pp | **no** |

Time-of-day confound checked: next-day+ first-retests are NOT clustered at the open (hour
distribution nearly flat vs same-day), and the within-hour lift is ~+3.2pp / +0.04R — the effect
is not a session-time proxy.

## Verdict

**The cascade as stated is dead.** Its core mechanism — early retest = invalid, late-same-day
retest = valid — is empirically backwards (<30m performs at base; ≥1h same-day is *negative*;
>4h same-day is the worst cell measured), and the extreme-swing gate passes ~95% of zones, so
it filters nothing. The full composite is +0.7pp against a **+6pp breakeven bar**, netR −0.18R,
and it is holdout-unstable on fvg_cb.

**What survives**: one clean, 4/4-holdout-stable, deconfounded fact — a zone whose first retest
comes on a **later day** hits at +2.3pp over base (+3.2pp within-hour), netR −0.156 vs −0.186,
with fatter MFE (3.17 ATR). That is a real overnight-carry effect, consistent with the program's
existing carried-zone prior — but at ~40% of the breakeven bar and still ~−0.15R after costs, it
is a **context feature, not a trade**. Same conclusion as RESULTS.md: direction information
exists; the cost/excursion geometry eats it.

*Artifacts: `casc_main.py` / `casc_report.py` / `casc_confound.py` + `casc_signals.parquet` in
the session scratchpad; signals from `runs/artifacts-data/signals60.parquet`, prices
`data/long5m/`. bpr dropped (birth not recoverable); compression_fade/inducement/turtle_soup out
of scope (not zone-retest detectors).*
