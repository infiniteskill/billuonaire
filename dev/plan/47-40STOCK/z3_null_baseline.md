# Z3 NULL BASELINE — is 20/32 co-location real, or tape-density chance? (2026-07-24)

**Claim under test** (from `_Z3-FAITHFULNESS.md` §2): the system "FIRES 20/32" of the user's hand-marks
(same stock+dir, entry within 2%, year-ambiguous) → cited as instance-level faithfulness.
**Red-team question:** would a RANDOM / non-taught grader co-locate 20/32 anyway, just because each stock's
tape is dense with trades? Faithfulness is real only if **real >> placebo**.

Method: 32 marks `tools/ytrades.json` vs 3 tapes deduped by (sym,entry,sl,target) → 27,196 unique trades.
Match rule reproduced exactly: same sym + same dir + |trade.entry − mark.entry| ≤ 2%·mark.entry, any tape.
Reproduced **20/32 fire** (20/27 coverable; 5 marks are SBICARD/SBILIFE, not in the 40 → can never fire). ✓

## 1) The tape is DENSE — "a trade near any price" is the norm
Per-mark base rate = fraction of that stock+dir's trades within 2% of the mark: **mean 6.5%, median 4.5%,
max 25.6%** (n=27). Individually small — BUT each stock fires 40–133 same-dir trades, so the **union** of
±2% bands covers most of the traded range. Band-coverage = P(a random in-range same-dir price fires ≥1 trade):

| stock+dir | coverage | | stock+dir | coverage |
|---|---|---|---|---|
| HAVELLS long | 66% | | DLF short | **96%** |
| HAVELLS short | 60% | | TITAN long | **98%** |
| VOLTAS long | 33% | | TITAN short | 70% |
| VOLTAS short | 40% | | DABUR long | 36% |
| DLF long | 65% | | DABUR short | 46% |

For most stock+dirs a **random** price co-locates 60–98% of the time. Co-location is cheap.

## 2) PLACEBO — shuffle mark entries to random in-range prices (dir kept), 5000 iters
| band | REAL | placebo mean | median | p5 | p95 | max | **P(placebo ≥ real)** |
|---|---|---|---|---|---|---|---|
| **2.0%** (the cited claim) | 20 | **16.5** | 17 | 13 | 20 | 24 | **0.099** |
| 1.0% | 17 | 13.5 | 13 | 9 | 18 | 22 | 0.110 |
| 0.5% | 16 | 10.6 | 11 | 7 | 15 | 19 | **0.027** |
| 0.2% | 13 | 7.4 | 7 | 4 | 11 | 17 | **0.017** |
| 0.1% | 5 | 5.3 | 5 | 2 | 9 | 13 | 0.638 |

Dir-shuffled placebo (randomize dir too): mean 16.5, p95 21 — no change; direction carries no extra info.

## 3) READ
- **At the cited 2% band, 20/32 is NOT above chance.** A coin-flip grader placing same-dir orders at random
  prices co-locates **16.5/32 on average (52%)** and reaches ≥20 in **~10% of runs (p=0.099)**. Real 20 sits
  right at the placebo **p95 edge** — inside the null, not beyond it. The 63% headline is mostly tape density.
- **A weaker, genuine fingerprint survives only at TIGHT tolerance.** At 0.2–0.5% (20–50 bps) real exceeds the
  placebo 95th percentile with **p≈0.02**: the user's marked prices sit closer to *actual fills* than random
  placement — a real (but modest) signal that the system trades the user's specific levels, not just somewhere
  in the range. It collapses at 0.1% (10 bps) because marks are round numbers vs raw fill prices.

## VERDICT
**The 20/32 (63%) co-location is largely a density artifact — real is NOT >> placebo at 2% (p≈0.10).**
It should be **downgraded**: as stated it is not evidence of faithfulness above a random grader. The only
defensible instance-level signal is the tight-band residual (0.2–0.5%, p≈0.02), which is real but weak.
Structural faithfulness (sweep 67% / far-RR 76–95%, `_Z3` §1) remains the stronger case; **instance
co-location at 2% does not corroborate it and should not be cited as strong evidence.**
