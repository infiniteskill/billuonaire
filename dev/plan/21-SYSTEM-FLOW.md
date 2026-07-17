# The System Flow — how it finds, decides, acts, earns (2026-07-17)

The end-to-end autonomous flow. The intelligence is in the RANKING at each stage: the
system never trades "a signal" — it continuously scores the whole universe and acts only on
the few setups with the highest profit potential. Built on the operator model (`20-...`) +
the measured toolkit (`18-...`) + the control contract (`19-...`).

## STAGE 0 — INPUTS (you set once)
Stock list (or pool + "auto top-K"), capital, risk-per-trade %, max trades/day, re-entry
rule, selectivity (confluence threshold + min-RR), entry TF (2m/5m) + direction TF (auto ~6×),
day-guards (loss cap, profit lock), mode (dry/paper/live). → the system obeys these as hard limits.

## STAGE 1 — PRE-MARKET HOMEWORK (before 09:15): finalize which stocks
For EVERY stock the system does deep homework so it arrives ready:
1. Pull HTF (Week/Day/H1). **Macro bias**: where in the weekly/monthly range (break-&-return),
   the 1D PO3 phase (accumulation/markup/distribution/markdown), premium vs discount of the swing.
2. **Map the fat SL-cluster field**: fresh OB/FVG/SD zones + unswept liquidity (PDH/PDL/PWH/PWL,
   equal highs/lows, round numbers), each RANKED BY FATNESS (obviousness × touches × roundness × recency).
3. **Draw-on-liquidity**: the nearest untapped FAT cluster in the HTF direction = where price is
   magnetized next = the predicted hunt.
4. **Setup-potential score per stock** = cleanliness × energy(ATR%) × zone-proximity ×
   HTF-alignment × confluence-density-of-mapped-aspects.
5. **RANK the universe** → top-K by potential = today's FOCUS list (watched closely); rest = backburner.
   *This is "finalize which stocks to trade": the ones already lining up everything.*

## STAGE 2 — OPEN / OBSERVE (09:15–~11:00): no trades, read the trap
Morning = manipulation window (validated: entries here lose). OBSERVE only:
- How does each focus stock open vs its HTF bias? Gap (trap direction), opening range.
- Is the morning move a Judas hunt or genuine? Lock the day template (trend/trap-reversal/range/double-trap).
- Add today's intraday zones (OR edges, the morning sweep levels = fresh clusters).
- **Re-rank**: which focus stocks just printed a fresh high-quality zone + reversal signature?

## STAGE 3 — WAIT & ARM (~11:00–14:30): price comes to the zone
For each focus stock, continuously:
- Is price APPROACHING a fat cluster / high-confluence zone in the HTF direction (within N×ATR)?
  → **ARM** it (high alert). *This is "we wait, see price come into the zone."*
- Compute the **CONFLUENCE SCORE** at that exact zone: how many aspects stack there —
  OB + FVG + fresh-cluster + compression-coil + PO3-phase + sweep-setup + HTF-dir + premium/discount.
- **RANK all armed setups across all stocks** by (confluence-density × RR-potential × cleanliness).
  Capital & attention flow to the BEST — the system is always pointed at its single best opportunity.

## STAGE 4 — THE GRAB (entry): take max-profit potential
When an armed zone is HIT and the destroy fires:
- **The grab** = fat cluster swept / failed-break + RECLAIM (wick beyond + close back) + volume burst.
- **Confirm gates**: HTF direction agrees, confluence ≥ threshold, RR ≥ min, within trade/re-entry/heat limits, in the entry window.
- **Decide everything**:
  - ENTRY PRICE = the reclaim / zone CE (a resting limit — NEVER chase the breakout candle).
  - ENTRY TIME = the grab-confirm bar.
  - RISK = SL just beyond the destroyed extreme (tiny by construction) → QTY = risk% ÷ SL-distance (capped).
  - TARGETS = the next opposite fat cluster(s); partial 33% at 3R (expectancy peak), runner to 5–10R.
- **Max-profit selection**: among simultaneous grabs, take the one(s) maximizing
  **confluence-density × RR (far target ÷ tiny SL) × cleanliness × HTF tailwind.** That is
  "take which has potential and max profit chance" — highest reward per unit of tiny risk.

## STAGE 5 — MANAGE (in-trade): protect + let it run
Breakeven at 1R; partial at 3R; **structure-ratchet trail** (never widen); promote to slower-TF
swings as it runs (let the winner breathe toward 10R). Exit early only on a **counter-grab**
(opposing high-confluence setup = our winner became their trap) or a **stall** (no progress →
free the capital for a better setup elsewhere).

## STAGE 6 — EXIT & DAY-END: bank it
Exit at target / stealth-stop (close-confirmed, wick-tolerant) / counter / stall / EOD 15:10.
Enforce **daily profit-lock** (hit the goal → stop, go home with the win) and **loss-cap**
(protect capital). Squareoff all before close. No overnight.

## STAGE 7 — LEARN (nightly): get smarter tomorrow
Journal every decision + outcome. Calibrate which aspects/confluences actually paid, nudge
weights within guardrails. Update per-stock cleanliness/behaviour stats. Accrue the day's data
→ tomorrow's homework (Stage 1) is smarter. Forward data compounds; the system improves while you watch.

## THE INTELLIGENCE (the through-line)
At EVERY stage the system RANKS and focuses only on the best: pre-market ranks stocks by
potential; intraday ranks armed setups by confluence×RR×cleanliness; entry picks the max-profit
grab; management protects and lets winners run. **Max profit = tiny SL (grab entry) × far target
(next cluster) × high confluence (everything lines up) × clean stock × HTF tailwind.** It never
takes "a trade" — it takes the *best available* expression of the operator's own play, against
the trapped crowd.

## Honest gate (before this ships)
The ranking intelligence rests on one unproven claim: **confluence density lifts edge/RR**
(your "perfect stock = everything aligns"). That's the next measurement. If it validates on
holdout with real sample, this flow is sound and we build it. If not, the ranking logic is
re-derived from what actually stacks. Then: build v2 (plug-n-play core), economic replay vs
baseline, forward month — ship only when it earns.
