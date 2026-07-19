# NATIVE30 — the final spec, run natively on 30-minute charts

**Question**: the full SMC stack (swings + liquidity + FVG/OB/iFVG/breaker) with the elimination ladder, built and traded ON 30m charts (not 5m zones held longer), positional 1–2 week holds, 50 liquid stocks, no MA/VWAP — does it make money after delivery costs?

**Script**: scratchpad `native30_run.py` → `native30_trades.parquet`. Data: `data/long5m/` resampled to 30m (09:15-anchored) + D1 (one bar/session), 57 sessions 2026-04-27…2026-07-17 (52 distinct entry sessions after warmup/censoring). Universe: **top 50 of 139 by total traded value** (Σ close×volume; HDFCBANK ₹1500B … TRENT ₹178B).

## Method (conventions, stated once)

- **Zones on 30m** (verified chartpar/hulinv ports): `fvg_cb` (wick gap + c2-close displacement + running range% threshold), `ob_lux`, EmreKb breaker (zz=9, fib=0.33), **iFVG** = FVG closed beyond its far edge → flipped zone born at the invalidation bar. Death = close beyond far edge. Inventory: 1320 FVG + 2915 OB + 174 breaker + 1024 iFVG = **5433 zones**; 4380 (81%) got a first retest, 536 died unretested, 517 never touched.
- **Trade**: first wick-retest after confirmation (breaker: EmreKb close-inside-box; a bar that kills the zone doesn't count as retest) → enter **next 30m open**, fade direction, one trade per zone. Stop k×ATR(14,30m at retest), k∈{1.5, 2.5}; target 2R; time-stop at close of Hth session (entry session = 1), H∈{5, 10}. **EOD not closed** — every bar's open beyond stop/target fills AT OPEN (overnight gaps go through stops); intrabar stop-before-target. Windows running off the data edge dropped (2290 cell-rows censored).
- **Ladder** (cumulative): **r1** = zone origin-candle session strictly before retest session. **r2** = 30m zone overlaps a live, trade-direction-aligned **D1** fvg/ob zone (confirmed on an earlier session, not yet dead). **r3** = zone origin within [0,3] 30m bars after an aligned EQ-pool sweep (pools = ≥2 same-side 5/5-fractal 30m swings within 0.25×ATR(14,30m); sweep = wick through + close back; EQH→shorts, EQL→longs).
- **Costs (delivery)**: STT 0.1% + exch 0.004% + slip 2bp per leg, DP ₹15/sell. ₹1L capital, 0.5% risk (₹500), 5× notional cap (never bound; qty0 skips = 0). R on actual rupee risk qty×stop.
- **Holdout**: 4 quadrants = (entry session </≥ 2026-06-08) × crc32(symbol)%2.
- ATR(14,30m) median **0.56% of price** (p25–p75 0.46–0.69%) → k1.5 stop ≈ 0.84% of price, ~2.6× the 5m-scale stops of SWING.md.

**D1 zone thinness (honest)**: only **317 daily zones across 50 symbols** (mean 6.3/sym, min 2, max 12 — 57 daily bars minus ~15-session ATR warmup leaves little room). A live aligned D1 zone existed for **49.6%** of trade candidates; requiring actual overlap cuts r1's 2285 trades to **502** (r1+2). The r2 rung is real but operates on a thin HTF list — flagged, not hidden.

## Cells

win% = net R > 0. netR_long = long-only (the side cash delivery can actually hold overnight). MFE/MAE in ATR over the full H window (exit-agnostic). Quadrant columns = mean net R.

| cell | n | win% | grossR | netR | netR_long | MFE/MAE | T1C0 | T1C1 | T2C0 | T2C1 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| k1.5 H5 all | 4032 | 34.1 | −0.001 | −0.314 | −0.365 | 0.965 | −0.334 | −0.322 | −0.244 | −0.369 | dead |
| k1.5 H5 r1 | 2285 | 32.9 | −0.048 | −0.362 | −0.378 | 0.956 | −0.334 | −0.436 | −0.312 | −0.386 | dead |
| k1.5 H5 r1+2 | 502 | 36.7 | +0.052 | −0.257 | −0.359 | 1.027 | −0.278 | −0.409 | −0.154 | −0.316 | dead |
| k1.5 H5 r1+2+3 | 37 | 32.4 | −0.035 | −0.355 | −0.660 | 0.878 | +0.021 | −1.413 | +0.047 | −0.869 | dead |
| k1.5 H10 all | 3551 | 33.7 | −0.010 | −0.321 | −0.351 | 0.961 | −0.341 | −0.326 | −0.250 | −0.370 | dead |
| k1.5 H10 r1 | 2007 | 32.3 | −0.064 | −0.377 | −0.373 | 0.948 | −0.333 | −0.438 | −0.347 | −0.406 | dead |
| k1.5 H10 r1+2 | 401 | 36.2 | +0.026 | −0.278 | −0.376 | 0.991 | −0.278 | −0.409 | −0.201 | −0.301 | dead |
| k1.5 H10 r1+2+3 | 25 | 24.0 | −0.291 | −0.617 | −0.803 | 1.000 | +0.021 | −1.413 | −0.102 | −1.056 | dead |
| k2.5 H5 all | 4032 | 34.9 | −0.027 | −0.227 | −0.256 | 0.965 | −0.220 | −0.256 | −0.209 | −0.230 | dead |
| k2.5 H5 r1 | 2285 | 34.1 | −0.054 | −0.256 | −0.273 | 0.956 | −0.267 | −0.306 | −0.195 | −0.267 | dead |
| k2.5 H5 r1+2 | 502 | 36.3 | +0.029 | −0.169 | −0.251 | 1.027 | −0.333 | −0.393 | −0.018 | −0.187 | dead |
| k2.5 H5 r1+2+3 | 37 | 43.2 | +0.189 | −0.016 | −0.426 | 0.878 | +1.144 | −1.197 | +0.742 | −1.179 | dead |
| k2.5 H10 all | 3551 | 33.4 | −0.029 | −0.229 | −0.239 | 0.961 | −0.207 | −0.274 | −0.209 | −0.228 | dead |
| k2.5 H10 r1 | 2007 | 31.9 | −0.076 | −0.277 | −0.277 | 0.948 | −0.252 | −0.321 | −0.250 | −0.295 | dead |
| k2.5 H10 r1+2 | 401 | 34.4 | +0.000 | −0.196 | −0.280 | 0.991 | −0.348 | −0.388 | −0.075 | −0.135 | dead |
| k2.5 H10 r1+2+3 | 25 | 36.0 | +0.044 | −0.163 | −0.424 | 1.000 | +1.796 | −1.197 | +0.677 | −1.096 | dead |

Trade mix (k1.5 H5 all): OB 2006, FVG 1103, iFVG 843, breaker 80; longs 2030 / shorts 2002. Exit mix: 2637 stops / 1335 targets / 60 time-stops (H10: 2354/1192/5).

## Overnight gaps

| cell (all-zone) | stop exits | gap-through-stop | mean excess | max excess | cost drag |
|---|---|---|---|---|---|
| k1.5 H5 | 65.4% | 341 = **8.5% of trades** (12.9% of stops) | **0.64R** | 6.37R | 0.313R |
| k1.5 H10 | 66.3% | 8.7% of trades | 0.65R | 6.37R | 0.311R |
| k2.5 H5 | 60.1% | 7.9% of trades | 0.49R | 4.04R | 0.201R |
| k2.5 H10 | 66.3% | 8.9% of trades | 0.51R | 4.04R | 0.200R |

~1 in 12 trades gaps THROUGH the stop overnight, losing an extra ~0.5–0.65R beyond the intended 1R (worst 6.4R). Wider k=2.5 stops absorb gaps somewhat (excess 0.65→0.5R) but can't remove them.

## Sanity anchors (both agree — the measurement is trustworthy)

1. **Pooled all-zone MFE/MAE = 0.961–0.965** vs SWING.md's 0.985–0.99 at multi-day holds. Same answer: excursions are symmetric; zones carry no multi-day directional information. (r1+2 nudges to 0.99–1.03 — still nowhere near a tradeable ≥1.15.)
2. **Cost drag 0.20R (k2.5) / 0.31R (k1.5)** vs SWING's 0.48–0.91R at 5m stops. Stops here are ~2.6× wider (0.84% vs 0.32% of price) → expected 0.48–0.91/2.6 ≈ 0.18–0.35R. Measured lands exactly in that band. No flags.

## Verdict — DEAD

The bar was: net R > 0 pooled AND in all 4 holdout quadrants. **0 of 16 cells pass. Every cell is net-negative pooled.** Plainly:

- **Gross ≈ 0 before costs, everywhere** (−0.03…+0.05R in every cell with n>100). Moving the whole stack from 5m to native 30m did not create edge — the zones fade a random walk at this scale too, exactly as the MFE/MAE ratio (~0.96) predicts.
- The ladder monotonically *improves* gross (all → r1+2: −0.001 → +0.052 at k1.5 H5) but the improvement is ~0.05R against a 0.2–0.3R cost floor and it is **not holdout-stable** (r1+2 negative in all 4 quadrants).
- The near-breakeven cell (k2.5 H5 r1+2+3, net −0.016) is a symbol-half artifact: crc-half C0 +0.7…+1.8, C1 **−1.2** in both time halves, on n=37. That is noise, not signal.
- Long-only — the only side cash delivery can hold overnight — is *worse* in 15/16 cells (−0.24…−0.80R).
- **Rung-3 cadence**: 37 trades / 52 sessions across the whole 50-stock book ≈ **45 trades/quarter** (~0.9/stock/quarter, H10: ~30/qtr). The user wanted few; the ladder delivers few — but few losers are still losers.

This closes the loop started in SWING.md: the failure was never the timeframe. 5m zones held a week: dead. 30m-native zones held 1–2 weeks: dead, same shape (symmetric excursions, ~0 gross, costs + gap tail on top). The SMC-fade family is measured out at both scales on this data; anything next has to be a different hypothesis (momentum track), not another knob on this one.
