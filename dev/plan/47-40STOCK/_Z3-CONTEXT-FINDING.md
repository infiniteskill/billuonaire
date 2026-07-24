# 47-40STOCK — Z3 deeper: faithfulness is CONTEXT-DEPENDENT (the premium/discount window finding) (2026-07-24)

The red-team called faithfulness UNDECIDABLE (undated marks). The user corrected: the marks HAVE dates —
`ytrades.json` has month+day, year is mostly 2026 (month≤7), price disambiguates outliers (H_570@570≈2020,
H_old@1910≈2024). This unlocked TEMPORAL co-location — and it surfaced a bigger finding than a pass/fail.

## THE DISCOVERY — direction is lookback-window-sensitive
Same HAVELLS price data, 2026-07-09 (both feeds identical, 1199-1234):
- **17-day context** (data/wide, range 1140-1234): system fires **SHORTS** — entry 1221 → **+27.6R**,
  1216→+17R, 1214→+11.6R.
- **full-2026 context** (data/marks_2026, range 1141-1910): system fires **LONGS** — entry 1187-1212, tiny targets.

`premium_discount` computes the dealing range over available history. 17-day window: 1221 sits at the
range TOP = **premium → SHORT**. Full-2026 window: the 1910 high makes 1200 = **discount → LONG**. Same
price, opposite direction. **The system's direction depends on how much history the extremes/p-d detector
has seen.**

## Consequence for faithfulness
- Co-locating the user's trades against a FULL-2026 (6-month lookback) tradebook is the WRONG context —
  the window flips direction, so the user's shorts appear "not fired" (4/20). Artifact, not a real miss.
- In the LOCAL context (17-day tape ≈ the user's ~1-month chart view), the user's marked SHORTS fire as
  WINNERS: H_jul_short@1221 → **g4 +27.6R**, Da_jul_short@448 → **g5 +16.4R**. Faithful for shorts.
- The two in-window LONGS (H_jun_long@1141 06-29, Da_jun_long@421 06-27) did NOT fire even locally — a
  real LONG recall gap.
- Caveat: the system fires a CLUSTER per setup (DABUR n16, R range −23.7..+16.4); "best match" is the
  winner of a mixed cluster — the user's discretion selected the winner. So recall is real; per-fire
  outcome is mixed (consistent with the dedup/clustering finding).

## HONEST verdict (refined)
Faithfulness is NOT simply pass/fail or undecidable — it is **CONTEXT-DEPENDENT**. When the system's
extremes/premium-discount window matches the user's local trading horizon, it faithfully fires the marked
SHORTS as winners (the +27.6R 1221 short is the user's textbook trade, reproduced). The apparent low
full-2026 faithfulness is a WINDOW artifact, not evidence of a lookalike.

## DESIGN FINDING (edge-relevant, → the build list)
The extremes / premium_discount lookback must MATCH the trading horizon (a LOCAL swing range, not
all-history). This is a real lever: a mis-set window mis-calls direction. Connects to B1 (both are the
EXT anchor being context-dependent). Next: (a) parameterize the p-d/extremes lookback to a local window
and A/B whether it improves the graded tier + the mark recall; (b) test the LONG recall gap (why 1141/421
longs don't fire); (c) fetch prior-year (2024/2025) data for the 12 Aug-Dec marks to extend the test.

## STATUS of the earlier "undecidable"
Superseded in part: the marks ARE dated (mostly 2026), temporal co-location IS possible, and it shows
context-dependent faithfulness for shorts. Still open: LONG recall, the 12 prior-year marks, and whether
a local-window p-d improves both faithfulness AND the edge.
