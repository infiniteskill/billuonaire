# RLADDER — target-R ladder (2R…10R) for the assembled taught system

2026-07-19. **0 new configs examined.** The recognizer is the frozen `tune_frozen.json`
(pct 0.06 / body-OB / FVG mmax6 q0 / death 0.5 second-life / dedup stack≥4 / parent-linked PRP /
edge entry / zone-height stop with 1.5×ATR fallback). **The target multiple is an EXIT parameter,
not a detection knob** — so this is a pure exit sweep over the SAME episodes: I reused
`asm_h1.run_symbol` / `asm_daily.run_symbol` detection verbatim (reproduces `tune_full`: 207,763 H1
& 307,991 daily episodes, `lad2_net≡t2_net` and `nul2_net≡null_t2_net` to 0.00e+00) and only walked
each episode's frozen fill `fp` and stop `sd` to a fixed target `fp + d·tgtR·sd` for tgtR∈{2…10},
plus the standing slow-trail runner. Costs/sizing = `dgrid_lib` (STT 0.1%×2, exch 0.004%, DP ₹15/sell,
slip 2bp/leg, R0=₹500 risk, ₹5L cap). Top grade tier only: **g≥2 = 1{stack≥4}+1{parent_ok}+1{dist≤2} ≥ 2**.

Scripts: `scratchpad/rl_lib.py` (patched `econ`/`_null_net` ladder), `rl_h1.py`, `rl_daily.py`, `rl_report.py`.

**Breakeven hit% = (1+costR)/(tgtR+1)** — the win rate a *clean* +tgtR-win / −1R-loss book needs to net 0.
Caveat: real books also exit at the **horizon** at an intermediate mark; those non-hits are NOT −1R (on
daily they bank partial upside), so `net_R` can be positive even when actual hit% < breakeven. **Trust the
measured `net_R` / `EXCESS`, not the breakeven flag.** `costR = gross − net` (≈constant per frame).

---

## A. H1 / intraday-hourly (l4_h1, 138 syms, 2023-08→2026-07, horizon 70 H1 bars). Top tier g≥2, n=184,744, 85% zone-height stop.

| tgtR | trades | wins | hit% | gross_R | net_R (±95% clust) | costR | breakeven hit% | actual≥BE? | 4-way net sign |
|---|---|---|---|---|---|---|---|---|---|
| 2R | 184,744 | 57,371 | 31.1% | +0.0594 | **−0.2677 ±0.0147** | 0.327 | 44.2% | no | all − |
| 3R | 184,744 | 38,416 | 20.8% | +0.0392 | −0.2879 ±0.0157 | 0.327 | 33.2% | no | all − |
| 4R | 184,744 | 27,518 | 14.9% | +0.0307 | −0.2964 ±0.0168 | 0.327 | 26.5% | no | all − |
| 5R | 184,744 | 20,439 | 11.1% | +0.0252 | −0.3019 ±0.0181 | 0.327 | 22.1% | no | all − |
| 6R | 184,744 | 15,498 | 8.4% | +0.0191 | −0.3081 ±0.0187 | 0.327 | 19.0% | no | all − |
| 7R | 184,744 | 12,101 | 6.6% | +0.0187 | −0.3084 ±0.0189 | 0.327 | 16.6% | no | all − |
| 8R | 184,744 | 9,508 | 5.1% | +0.0132 | −0.3139 ±0.0196 | 0.327 | 14.7% | no | all − |
| 9R | 184,744 | 7,653 | 4.1% | +0.0119 | −0.3153 ±0.0203 | 0.327 | 13.3% | no | all − |
| 10R | 184,744 | 6,282 | 3.4% | +0.0108 | −0.3163 ±0.0206 | 0.327 | 12.1% | no | all − |
| **TRAIL** | 184,744 | — | 34.3%¹ | — | **−0.2774 ±0.0259** | — | — | — | all − |

¹ trail hit% = win rate (net>0); no fixed target. Trail peakR: mean 1.14, median 0.51, **%≥5R = 3.1%, %≥10R = 0.3%**.
Every holdout cell (early/late × crc-half) has >1,400 winners even at 10R → reliable.

**H1 verdict: NO R is profitable.** `net_R` is **maximized at the LOWEST rung (2R, −0.268R)** and decays
**monotonically** to −0.316R at 10R; negative in all 4 holdout cells at every rung. Actual hit% never
reaches breakeven (31.1% vs 44.2% at 2R; 3.4% vs 12.1% at 10R). costR ≈ **0.33R** (tight stop → huge
notional → STT dominates gross of only +0.01…+0.06R). Raising the target only adds cost drag and horizon
timeouts. Trail = −0.277R, no better.

---

## B. Daily positional (dailymax, 139 syms, ~25y, horizon 40d ≈ 8 wk). Top tier g≥2, n=285,766. **Survivorship: trust EXCESS, not absolute net.**

Matched-drift null = 5 random same-symbol same-direction entries per trade, **same %-of-price stop**, same
target/horizon/costs, swept at every tgtR. EXCESS = real net − null net.

| tgtR | trades | wins | hit% | net_R abs (±95%) | null net | **EXCESS (±95%)** | costR | BE hit% | ≥BE? | holdout EXCESS sign² |
|---|---|---|---|---|---|---|---|---|---|---|
| 2R | 285,766 | 96,714 | 33.8% | +0.0398 ±0.0108 | −0.1329 | **+0.1727 ±0.0204** | 0.123 | 37.4% | no | all + |
| 3R | 285,766 | 62,796 | 22.0% | +0.0193 ±0.0120 | −0.1174 | +0.1367 ±0.0232 | 0.123 | 28.1% | no | all + |
| 4R | 285,766 | 42,718 | 14.9% | +0.0048 ±0.0134 | −0.1059 | +0.1108 ±0.0210 | 0.123 | 22.5% | no | all + |
| 5R | 285,766 | 30,543 | 10.7% | −0.0005 ±0.0145 | −0.1005 | +0.0999 ±0.0197 | 0.123 | 18.7% | no | all + |
| 6R | 285,766 | 22,675 | 7.9% | −0.0036 ±0.0156 | −0.1063 | +0.1028 ±0.0263 | 0.123 | 16.0% | no | all + |
| 7R | 285,766 | 17,496 | 6.1% | −0.0032 ±0.0160 | −0.1000 | +0.0968 ±0.0225 | 0.123 | 14.0% | no | all + |
| 8R | 285,766 | 13,841 | 4.8% | −0.0011 ±0.0166 | −0.0961 | +0.0950 ±0.0229 | 0.123 | 12.5% | no | all + |
| 9R | 285,766 | 11,179 | 3.9% | −0.0007 ±0.0173 | −0.0893 | +0.0887 ±0.0277 | 0.123 | 11.2% | no | **mixed** |
| 10R | 285,766 | 9,173 | 3.2% | −0.0004 ±0.0179 | −0.0891 | +0.0887 ±0.0281 | 0.123 | 10.2% | no | **mixed** |
| **TRAIL** | 285,766 | — | 40.3%¹ | +0.0078 ±0.0340 | −0.1875 | **+0.1954 ±0.0478** | — | — | — | all + |

² holdout = 3 temporal thirds + 2 crc-halves (5 cells, all trade-n ≈ 95k–158k → reliable). Trail peakR:
mean 1.23, median 0.62, **%≥5R = 2.9%, %≥10R = 0.4%**.

**Daily verdict: profitability is maximized at the LOWEST rung and erodes as R rises.**
- **Absolute net** (survivorship-inflated): +0.040R at 2R → crosses ~0 by 5R → flat ≈0 out to 10R.
- **EXCESS over drift** (the trustworthy number): **argmax = 2R at +0.173R ±0.020**, monotonically down to
  +0.089R at 10R. Sign-consistent across all 5 holdout cells through **8R**; at **9R/10R it goes "mixed"**
  (one holdout cell flips negative) → high-R excess also loses out-of-sample robustness.
- The **TRAIL** (bank partial run + 1R ratchet) is the *only* "let it run" variant that beats fixed 2R:
  EXCESS **+0.195R**, holdout all +. A fixed 5R/10R **target** does not — it is strictly worse than 2R.

---

## KEY MATH — why higher R hurts here (the intuition is falsified)

The user's thesis: *tight risk, big target — hit% falls but each win pays more, so net rises.* **It doesn't.**
The win-rate decay is roughly `hit(tgtR) ≈ hit(2R)·(3/(tgtR+1))` (near a −1 power law: hit halves ~every +3R),
so **`hit%·tgtR` (gross reach) is flat-to-declining** while the **−1R legs and per-trade cost pile up on the
growing majority of non-hits**. Concretely, expected gross ≈ `hit·tgtR − (1−hit)` barely moves (H1 gross
+0.06→+0.01; daily net +0.04→~0), but each rung adds horizon-timeouts that would have banked at 2R. Result:
**both `net_R` (H1 & daily) and `EXCESS` (daily) are argmax at tgtR = 2R and monotonically worse above it.**
The "let it run to 1:5+" dream is empirically rare: only **~3% of trades ever reach +5R favorable excursion,
~0.3–0.4% reach +10R** (trail peakR). Managing the runner with a **trail** (not a fixed far target) is the
version that helps, and only on daily (+0.195R excess).

## VERDICT

- **argmax over the ladder:** **tgtR = 2R on both frames** — H1 net −0.268R (least-negative, still a loss);
  daily net +0.040R and daily EXCESS +0.173R (both peak at 2R). Higher R is strictly worse everywhere.
- **Holdout-robust & positive:** only **Daily 2R** (EXCESS +0.173 ±0.020, all 5 cells +) and the **Daily
  trail** (EXCESS +0.195, all +). H1 is negative at every rung and cell. Daily excess stays all-+ through
  8R but goes mixed at 9R/10R.

### Does going to higher R make it profitable — yes/no, at what R?
**NO. Higher R makes it *less* profitable, not more.** On both frames net (and daily EXCESS) are **maximized at
the lowest rung, 2R, and decay monotonically through 10R.** H1/intraday is a loss at every target (−0.27R at
2R → −0.32R at 10R; costs, not misses). Daily positional's edge is real but banks earliest: **best at 2R
(+0.17R excess over a matched-drift null, positive in all holdout cells); it is roughly halved by 10R and
loses holdout-sign robustness beyond 8R.** The only "let it run" that helps is a **trailing** stop on daily
(+0.195R excess), never a fixed high-R target.
