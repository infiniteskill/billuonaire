# THE HONEST RESET (2026-07-26) — the fill-truth that reframes everything

## What the user's trace-demand found
Phantom fills: the research sim assumed a position at the entry price without racing the fill.
57% of "trades" had entries price NEVER touched (91% of recorded profit, 88% fake "win" rate —
price ran without ever pulling back to the limit). Independent trace re-race matched sim math
99.9% — the arithmetic was right; the FILL ASSUMPTION was fiction.

## The honest table (entry-fill raced, blind CE-limit, SL-first fill-bar, eod hi>=5+minRR, wide2026)
| config | n | win% | mean | TOTAL | phantom claim |
|---|---|---|---|---|---|
| frozen main | 559 | 14.3 | -1.50 | -837 | +7314 |
| stage2 | 744 | 14.5 | -1.57 | -1167 | +8359 |
| b1s | 786 | 14.6 | -1.49 | -1168 | +9520 |
ALL config deltas were phantom noise. Under real fills every variant is the same negative.

## What this means (and does NOT mean)
- DEAD: the BLIND RESTING LIMIT AT ZONE-CE entry mechanic. To fill it, price must already be
  moving through the tiny zone against you; 86% continue to the stop. The passive limit
  self-selects losers (adverse selection, now measured end-to-end).
- NOT dead: detection (direction was right in most phantom runs), the zone/level analysis, the
  grading. The METHOD's real entry (taught: sweep -> REJECTION/RECLAIM confirmation -> enter) was
  NEVER simulated. The user will now teach the actual entry mechanics; sim variants follow
  (DERIVE_ENTRY_STYLE: ce_limit | edge_limit | reclaim_confirm | marketable).
- BOUNDS: SL-first on the fill bar at 1m granularity = maximally PESSIMISTIC bound (intra-minute
  sequence unknowable). Truth for any style lies between the phantom (+) and this (-) bound;
  tick data or live pilot narrows it.
## Process lesson (permanent): EVERY sim claim must survive an independent per-trade trace to
raw data (tools/trace_audit.py) before it is believed. The user's "verify those 1584 trades from
origin" instinct caught what 12 gate batteries + 3 regimes + walk-forward could not, because all
of them shared the same fill assumption. Correlated assumptions invalidate independent-looking tests.
