# PRO ENTRY-REFINEMENT — HTF zone -> M1 nest -> CE entry, compared by WHERE THE STOP LIVES

Data: `data/wide` native M1, 138 symbols x 20 sessions (2026-06-19..07-17; NIFTY + 2 empty files excluded;
splice guard `trader.tools.doctor.splices` @ >25%: **0 sessions dropped**). Build (leak-free): M5 = 5xM1
session-anchored; ATR14 = SMA of TR over the 14 bars BEFORE each bar (carried across sessions, no overnight TR).
Parent zones on M5, validated rules — OB: last opposite-color candle <=5 bars before a body>=1.5xATR14(M5)
displacement that closes beyond it, candle range = zone, dies on M5 close past far edge; FVG: 3-bar gap
>=0.3xATR14(M5), dies on full wick fill. Setup = first M1 return-touch of a live zone; direction = zone's.
Same touches feed all modes, Rs10k risk budget, qty = 10k/stop-dist, notional cap Rs50L (5x on Rs10L),
tick 0.05. Fills: limit fills AT price on >=1-tick trade-through; stop = market at next M1 open ±5bp slip;
stop-before-target intrabar; no entry-bar target fills; no fills >=15:00; squareoff 15:10 open. Costs:
Rs20x2 + 0.025% sell STT + 1-tick spread. Targets 2R/3R from each mode's OWN stop distance, + EOD.
M1 nest (B/C): same rules at M1 scale (ATR14(M1)), same direction, completing at/after the touch while the
parent lives, midpoint (CE) inside the parent zone; limit at that CE. D = diagnostic control: market at next
open after the M1 zone completes, structural stop (isolates the retrace-limit's selection effect).

## Funnel

touches **16,387** -> A fills 13,658 (83.3%) | M1 zone forms 3,895 (23.8%; OB5 parents 40.2%, FVG5 19.4%)
-> B/C limit fills 3,148 (80.8% of refined; 19.2% of touches). Mode B books only 2,835 — **313 refined fills
(10%) have a stop smaller than one tick** and are unquotable. D books 3,837.

## Mode table (per-unit-risk R = actual Rs risked; per10k = net Rs per Rs10k risked)

| mode | tgt | n | win% | P(stop) | P(eod) | netR | per Rs10k | med stop (ATR5) | overshoot (R) | capbind | med risk Rs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A parent CE, structural SL | 2R | 13,658 | 21.8% | .579 | .203 | **-0.358** | -3,579 | 1.50 | 0.24 | 12.4% | 9,998 |
| A | 3R | 13,658 | 11.5% | .596 | .288 | -0.367 | -3,671 | 1.50 | 0.24 | 12.4% | 9,998 |
| B M1 CE, M1 SL (tiny) | 2R | 2,835 | 17.0% | **.830** | .001 | **-4.198** | **-41,984** | **0.119** (=2.6bp of price) | **2.78** | **99.8%** | 1,311 |
| B | 3R | 2,835 | 13.3% | .866 | .002 | -4.237 | -42,372 | 0.119 | 2.74 | 99.8% | 1,311 |
| C M1 CE, structural SL | 2R | 3,148 | 17.1% | .496 | .333 | **-0.303** | -3,031 | 1.72 | 0.22 | 7.1% | 9,998 |
| C | 3R | 3,148 | 8.1% | .507 | .412 | -0.309 | -3,087 | 1.72 | 0.22 | 7.1% | 9,998 |
| D ctrl: market after M1 zone | 2R | 3,837 | 10.1% | .419 | .480 | -0.293 | -2,928 | 2.40 | 0.15 | 0.4% | 9,997 |
| D | 3R | 3,837 | 3.9% | .422 | .540 | -0.290 | -2,900 | 2.40 | 0.15 | 0.4% | 9,997 |

Cost decomposition (tgt 2R, mean R): A gross -0.236 / cost 0.122; **B gross -2.789 / cost 1.409** (STT on the
cap-bound ~Rs50L notional alone ~0.95R when risk is Rs1.3k); C gross -0.199 / cost 0.104. B's stopped trades
lose 3.78R gross each: the stop is 2.6bp of price, the exit is next-M1-open + 5bp — **the slippage is ~2x the
entire stop distance** (mean overshoot 2.78R).

## Entry improvement — is the refined fill a better price? NO

B/C entry vs A's parent-CE entry, in ATR(M5): **median -0.220** (mean -0.244, q25 -0.405, q75 -0.053);
better-priced than A in only **17.8%** of fills. The M1 zone forms on the reaction bounce inside the parent,
so its CE sits SHALLOWER than the parent midpoint. "Refine into M1" buys a worse price on 4 of 5 fills.
C's apparent survival gain (P(stop) .496 vs A .579) is just the wider effective stop (1.72 vs 1.50 ATR5) that
the shallower entry creates — geometry, not information.

## Adverse selection — the retrace limit selects the losers (stable in all 4 holdout cells)

D outcomes split by whether the B/C limit ever filled (tgt 2R): **D | limit filled: n=3,148, win 7.8%,
netR -0.479. D | limit NEVER filled: n=689, win 20.6%, netR +0.556.** Delta ~1.0R. Per cell (missed/filled):
T0S0 +0.599/-0.495, T0S1 +0.544/-0.433, T1S0 +0.591/-0.522, T1S1 +0.490/-0.445. The only positive bucket in
the entire study is the one you structurally cannot be in: refined contexts where price never came back.
(Post-hoc split — "never filled" is future information, not a tradable rule.)

## Paired A vs C — same zones, same context, only the entry differs

| tgt | A on B-filled zones | C | C - A |
|---|---|---|---|
| 2R | -0.218 (n=2,944) | -0.303 (n=3,148) | **-0.086** |
| 3R | -0.280 | -0.309 | -0.029 |

Per holdout cell (2R): C-A = -0.050 / -0.160 / -0.061 / -0.089 — **C loses to A in all four cells.**
C's pooled headline "edge" over A (-0.303 vs -0.358) is pure composition (C only trades zones where an M1
nest formed and refilled); on identical contexts the pro split is strictly worse than resting at the parent CE.

## Holdout (temporal halves x crc32(symbol)%2, mean netR, 2R)

| mode | T0S0 | T0S1 | T1S0 | T1S1 |
|---|---|---|---|---|
| A | -0.279 | -0.313 | -0.400 | -0.402 |
| B | -3.439 | -4.321 | -4.362 | -4.457 |
| C | -0.299 | -0.213 | -0.370 | -0.283 |
| D | -0.263 | -0.256 | -0.343 | -0.279 |

All 16 cells negative at both targets. Nothing is close to zero.

## VERDICT

1. **Does M1 refinement improve the fill? No — it worsens it twice over.** Price: median -0.22 ATR(M5) vs the
   parent CE (better only 17.8% of the time). Selection: conditional on the refined limit filling, the same
   context with the same structural stop makes -0.48R; when the limit never fills it makes +0.56R. The
   improvement isn't merely eaten by adverse selection — there is no improvement, and adverse selection is
   an additional ~1R of conditioning against you.
2. **B vs A — refinement paradox at M1: holds, x12.** netR -4.20 vs -0.36 per unit risked. Mechanism fully
   quantified: median M1 stop = 0.119 ATR(M5) = 2.6bp of price -> 83% stop rate, mean stop overshoot 2.78R
   (next-open + 5bp exit dwarfs the stop), costs 1.41R/trade (leverage cap binds on 99.8% of fills, so STT on
   Rs50L notional lands on Rs1.3k of deployable risk), and 10% of fills have stops below one tick. A "minimum
   SL" at M1 scale is smaller than the exit friction itself; it cannot be risk-managed into existence.
3. **C vs A — the pro split does NOT lift expectancy.** Pooled it flatters (-0.303 vs -0.358) but paired on
   identical zones A beats C by 0.086R at 2R and in every holdout cell. The refined entry contributes a worse
   price plus adverse selection; the structural stop merely stops the bleeding relative to B.
4. **Net-positive? No mode, no target, no cell.** Best tradable number is D 2R at -0.29R. The one positive
   bucket (+0.556R, refined-but-never-filled) is the adverse-selection residue, visible only ex-post.

Entry-refinement placement is now measured end-to-end: the stop can live at the M1 zone (B, catastrophic),
at the structure (C, no lift vs A), and the entry itself is the liability. This closes the pro
entry-refinement variant: at M5->M1 scale on this universe, refinement is negative-sum mechanics, not edge.

Artifacts: `m1r_run.py`, `m1r_analyze.py`, `m1r_trades.csv` (63,343 rows) in session scratchpad.
