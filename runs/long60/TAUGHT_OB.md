# TAUGHT_OB — user-taught order-block spec: detection parity + entry-depth facts

Scripts: session scratchpad `tob_lib.py` / `tob_verify.py` / `tob_run.py` / `tob_report.py`.
Reuses `dev/research/ext_zigzag.py` (ATR-zigzag pivots, causal confirmation) and `dev/research/dgrid_lib.py` (fvg_cb wick rule, delivery cost model). Data: `runs/artifacts-data/l4_h1.parquet`, 138 symbols, H1, 2023-08..2026-07.

## Spec as implemented (taught rules)

- Pivot = ATR-zigzag extreme; per-symbol `K = 0.047 / median(ATR/close)` (the ~4.7% TF-invariant leg floor). Median K 5.7, range 3.7–8.8, none clipped. ~82 pivots/sym over 3y.
- **OB** = opposite-direction candle or consolidation cluster (consecutive overlapping-range bars) pausing a leg; box = FULL hi–lo of cluster; cluster ends at the first close beyond the box in leg direction (continuation proof). Pivot-anchored variant sweeps back through the final flush candles at the pivot itself.
- **Power** = distance from the leg-origin pivot in ATR (0 = at pivot).
- **FVG** = fvg_cb 3-candle wick gap (displacement close + adaptive size threshold).
- **Flips**: close beyond distal edge → IOB (breaker) / IFVG, opposite side, born at the flip bar. **Overlap** = same-direction box intersection across types (`n_ov`).
- **Causal gate enforced**: zone tradeable only from `max(cluster-break bar, pivot confirm bar)` — the ext_zigzag confirmation lag (H1 median ~16–22 bars) applies before any revisit counts.
- **Revisit**: price must first fully LEAVE the box (low above hi / high below lo), then first touch = visit. Zone dies if closed through before arming.

Zone counts (138 syms): OB 54,471 · FVG 27,352 · IOB 47,807 · IFVG 24,567. First-revisit episodes measured: 127,869.

## Verification vs hand-drawn HEROMOTOCO chart (Jan–Apr 2026, tol ±1.5% / ±4d)

| zone | user drew | we found | verdict |
|---|---|---|---|
| (a) OB 5300–5350, born ~12 Jan at the January low, visit ~16 Feb → rally ~5800 | OB **[5298.5, 5353.0]** born **27 Jan 12:15** at the Jan-low pivot, dist **0.00 ATR**, tradeable 03 Feb; sibling shelf [5330.5, 5447.5] born 28 Jan touched **19–20 Feb** (low 5375) → rally to **5840** on 25 Feb. Tight box's first strict touch 09 Mar (low 5340) → rally to 5763. | **PARTIAL** — box exact (edge diff ≤0.06%), pivot-anchored (rank 0), revisit + rally within tolerance; birth date off vs recollection: tape prints no 5300–5350 before 23 Jan (12 Jan low = 5628), the January low IS 27 Jan. |
| (b) OB + iFVG band 5720–5800, formed early Feb, ENTRY on retest 12–16 Mar → collapse ~4900 | OB **[5668, 5888]** born **05 Feb** at pivot (dist 0) + OB **[5667.5, 5805]** born 11 Feb + breaker **[5676.5, 5790]** flipped 11 Feb + FVG [5662, 5720] — stacked confluence, n_ov up to 25. First strict touch **25–27 Feb** (high 5840, faded to 5340 = 2R+); **second** visit **10–11 Mar** (high 5763.5, inside band) → collapse to 5125 → **4906 (02 Apr)**. | **FOUND** box+birth (edges ≤0.9%, "early Feb" exact, OB⊗breaker⊗FVG overlap = highest grade as taught); **PARTIAL** on visit ordering — the drawn mid-March entry is the tape's *second* visit; our first-revisit rule fires 25 Feb (that fade also worked). |
| (c) OB 5430–5480 ~09 Mar | OB **[5429.5, 5474.5]** born **09 Mar 12:15** (edge diff 0.01%/0.11%), dist 1.55 ATR; plus pivot-anchored [5340, 5442.5] dist 0. Touched 12 Mar, closed through in the crash → flipped to breaker. | **FOUND** — exact on both axes; its break feeding the collapse is consistent with the drawing. |

Zigzag context pivots match the taught swings: 27 Jan L 5298.5 → 05 Feb H 5888 → 20 Feb L 5375 → 25 Feb H 5840 → 09 Mar L 5340 → 11 Mar H 5763.5 → 16 Mar L 5125 → 02 Apr L 4906.5.

## Entry-depth measurement (all 138 syms, first revisit, fade, 2R tgt / 1.5×ATR stop, gap-aware, 10-session time stop, delivery costs)

Per policy — EDGE = limit at proximal edge, CE = box midpoint, OTE = 0.705 retrace of the leg (causal running extreme). Fill% of episodes; hit% / netR on fills.

| type | pol | n_ep | fill% | hit% | grossR | netR |
|---|---|---|---|---|---|---|
| OB | EDGE | 46,392 | 100.0 | 34.6 | +0.037 | **−0.187** |
| OB | CE | 46,392 | 85.4 | 34.3 | +0.026 | −0.195 |
| OB | OTE | 46,392 | 43.1 | 29.3 | −0.114 | −0.325 |
| FVG | EDGE | 22,696 | 100.0 | 32.3 | −0.033 | −0.245 |
| FVG | CE | 22,696 | 88.8 | 32.4 | −0.029 | −0.240 |
| FVG | OTE | 22,696 | 35.8 | 27.1 | −0.185 | −0.388 |
| IOB | EDGE | 38,790 | 100.0 | 33.9 | +0.013 | −0.204 |
| IOB | CE | 38,790 | 86.0 | 33.8 | +0.008 | −0.208 |
| IFVG | EDGE | 19,991 | 100.0 | 34.7 | +0.043 | −0.170 |
| IFVG | CE | 19,991 | 88.7 | 35.1 | +0.055 | −0.157 |

(IOB/IFVG OTE: 37%/35% fill, netR −0.35/−0.39.) Mean cost ≈ **0.224R**/trade; outcome mix OB EDGE: 34.6% target / 64.7% stop / 0.7% timeout. Median trade −1.17R (stopped + costs).

**Every cell is negative after delivery costs.** Gross is ~breakeven (+0.04R best) — the taught zones are real structure but the 2R-fade edge is **sub-cost**, same verdict as the falsified SMC-fade study.

**Edge vs mid vs fib, answered**: EDGE ≥ CE > OTE, and OTE is the *worst* by a wide margin — the 0.705 leg-retrace usually lies **beyond the box** (median position 1.47 box-depths; 58% beyond the distal edge, only 25% inside), so waiting for OTE selects into zones that are already breaking. Deeper entry does not rescue the trade; it filters into worse ones.

**Penetration depth** (OB first revisits): median max-penetration **0.82×** box height; **42% blow straight through** (>1.0); only 16% reverse in the first quarter of the box. There is no shallow "typical reversal depth" — the box edge is the only entry that keeps positive gross, and only barely.

## Swing-nearness (the power claim)

OB EDGE by distance from origin pivot:

| bucket | n | hit% | netR |
|---|---|---|---|
| 0 (at pivot) | 10,242 | 35.0 | −0.154 |
| 0–2 ATR | 5,480 | 35.2 | −0.167 |
| 2–5 ATR | 12,232 | 34.9 | −0.185 |
| >5 ATR mid-leg | 18,438 | 34.0 | −0.212 |

Directionally **confirms the taught ranking** (monotone in netR; at-pivot vs mid-leg: hit z=1.65, netR t=2.86) but the effect is ~1pp hit / 0.06R — real, small, nowhere near cost-clearing. It inverts under CE/OTE (deep entries at pivot zones are the worst).

## Wait-to-revisit (the "visit comes days–weeks later" lesson)

Median wait is only 9 bars (~1.3 sessions) because every pause candle spawns a zone; the taught prototype is the late-visit subset, and it IS the best conditioner found:

| OB EDGE wait | n | hit% | grossR | netR |
|---|---|---|---|---|
| <1 session | 18,315 | 34.1 | +0.024 | −0.201 |
| 1s–1wk | 14,885 | 33.8 | +0.006 | −0.221 |
| 1wk–1mo | 8,176 | 35.0 | +0.044 | −0.181 |
| >1mo | 5,016 | 37.9 | +0.163 | **−0.046** |

hit z=5.3, netR t=6.9 (>1mo vs <1wk) — a genuine, strong effect. The full taught prototype — **at-pivot OB, visit ≥1 month later**: n=1,805, hit 36.7%, gross +0.133, **netR −0.077** (t=−2.12 vs 0; +overlap≥3: n=1,465, netR −0.061). The user's exact lesson selects the best cell in the whole grid — and it is still ~cost-sized negative. Overlap confluence: monotone but weak (0 ov −0.220 → 3+ ov −0.183, t=1.4).

## Holdout (temporal thirds × crc32%2 halves)

OB EDGE netR: T1 −0.181/−0.184, T2 −0.170/−0.187, T3 −0.204/−0.198 (n 7.1–8.4k/cell). All 6 cells negative for every type × policy; OTE worst everywhere. The negative result is stable across time and symbol halves — not regime luck.

## Verdict

Detection parity: the taught spec is implemented and reproduces the hand-drawn zones — (c) exact, (b) exact box/confluence with visit-ordering caveat, (a) exact box at the pivot with a birth-date recollection mismatch the tape itself contradicts. The taught *rankings* (pivot-nearness, overlap, late visit) all point the measured direction — the lessons encode real structure. But as a 2R/1.5ATR fade on H1 delivery, the best taught cell is gross +0.13R and net **−0.05 to −0.08R**: sub-cost, no tradeable edge in this form. If this zone logic is to earn money it must be as *context* for the momentum work (entry trigger, not fade target), or on a cost structure ~4× cheaper.
