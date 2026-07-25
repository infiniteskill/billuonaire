# SHAKEN-WINNER AUTOPSY (user's insight, 2026-07-25) — runs/validate/shaken_autopsy.csv

Question: of the 34-35% killshot losers, how many were RIGHT-direction trades lost to bad entry/SL?
Data: tb_s3_w26 eod hi>=5+minRR losers (463), raced 3 days post-stop on wide2026 1m.

RESULT: **185/463 (40%) = SHAKEN WINNERS** — original target printed after the stop; median missed
move +28.6R (75th pct +45R). 278 (60%) true losers.

WIDER SL IS NOT THE FIX: median adverse beyond SL = 9.7R (25th pct 4.2R). Buffer economics all
net-negative (+0.5R: −51R net; +1R: −206; +2R: −440) — only 10-29/185 shakeouts are shallow.

REAL DIAGNOSIS: shallow-tier entries taken BEFORE the deep sweep — the user's own "ALL SL TAKEN BY
BANK AS LIQUIDITY SWEEP" lesson at scale. The +28R move starts from the DEEPER zone.

FIX CANDIDATES (both taught-native, both need sim extension + gate):
1. DEEPEST-REFINEMENT ENTRY: when nested tiers exist, entry = innermost/deepest zone not first touch
   (t28 discipline). Sim: re-derive with entry at deepest available nest tier.
2. RE-ENTRY RULE: REJECTED by user reasoning (2026-07-25): the 60% true losers would re-trigger on
   reclaim wiggles -> doubled losses; reclaim signal unproven to separate shaken-from-doomed;
   revenge-trade shaped. BETTER ENTRY IS THE FIX.
DEEPEST-TIER ENTRY design: decide() takes the FIRST qualifying zone evidence; change = among
same-direction candidates in window prefer the DEEPEST zone (long->lowest / short->highest;
generalizes the htf_nest-CE preference). Distinct from G5 (same-zone depth, neutral) — this changes
WHICH zone we wait for. Param-gated -> wide2026 gate.
