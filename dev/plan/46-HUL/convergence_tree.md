# 46 — HUL CONVERGENCE TREE: HTF→LTF nesting, re-verifying the HAVELLS F1/F2 findings (2026-07-24)

Firings-based re-verification (HUL has **no hand-marks**). Resampled raw 1m (2026 + 2024Q4) to
D1/H1/M15/M5 with `pandas.resample`; traced strong setups top-down (D1 extreme ⊃ H1 zone ⊃ M5 entry);
read the fired `htf_nest` rows out of `runs/validate/hul_study_{2026,2024}/evidence.parquet` and put
**HUL numbers beside the HAVELLS numbers**, verdict REPLICATES / WEAKER / ABSENT per finding. No
pipeline run (derive_work untouched). RECOGNITION, honest — several HAVELLS findings do NOT survive.

## 0. Data + the two dealing ranges (resampled, verified)
| period | 1m rows | span | D1 low (disc extreme) | D1 high (prem extreme) | EQ | htf_nest rows |
|--------|---------|------|-----------------------|------------------------|----|---------------|
| 2026   | 7 125   | Jun19–Jul16 (19 D1 bars) | **2091.0** (Jul15) | **2238.8** (Jul03) | 2164.9 | 38 (11 L / 27 S) |
| 2024Q4 | 22 875  | Sep02–Nov29 (61 D1 bars) | **2375.75** (Nov18) | **3035.0** (Sep23) | 2705.4 | 84 (47 L / 37 S) |

Note the **geometry differs from HAVELLS**: HAVELLS 2026 oscillated inside a drawn box with a *later,
higher* spike (1234) as the fresh extreme. HUL 2026 is a **down-trend** — the high (2238.8) is *early*
(Jul 3) and the discount extreme (2091) is *late* (Jul 15, one session before data ends). So on HUL the
"fresh, un-re-anchored extreme" is the **LOW**, not the high — which flips which side F2 bites.

---

## 1. SETUP A — 2026 PREMIUM SHORT, Jul 8 (CAPTURED by htf_nest, hit)
D1 raids 2238.8 (Jul 3 13:00 H1 high), distributes Jul3→Jul7 in a 2190–2220 supply, Jul 8 opens 2189.5
straight into the leftover supply and rejects.

```
CONVERGENCE TREE — SHORT                                     entry pct in D1 range ≈ 70% (PREMIUM)
D1  range 2091 ─────────────────────────────── 2238.8       true supply extreme = 2238.8 (Jul3)
      │ premium half (>2165); Jul3 tags 2238.8 = buy-side raid
      ▼
H1  supply Jul3/Jul7 ............ zone ~2190 ── 2220        (Jul8 09:00 H1 opens 2189.5, closes 2178.5 = down)
      ▼
M5  reject Jul8 09:15→09:25 ..... zone 2189.5 ─ 2198.5      (poke 2198.5, close-away 2179.4)
      ▼  ENTRY ~2194  ·  fired htf_nest zones 2189.5–2208.8
════════════════════════════════════════════════════════════════════════════
CONVERGE @ 2189–2199   nest_depth = 2 (strength 0.667)
htf_nest: Jul8 09:15/09:20/09:25 SHORT → **hit 1.00**, mfe 5.09 ATR ≈ +27pt
OUTCOME: 2194 → Jul8 D1 low 2130 (+64pt) → Jul15 2091 (+103pt).  CAPTURED ✓
```
But the **true extreme (2238.8) short is only partly seen**: the highest supply nest is **2225.7–2231.5**
(the *body* of the Jul3 high H1 bar) — **zone_hi caps at 2231.5, gap 7.3pt to the 2238.8 wick**, and that
near-extreme zone went 1/3 (see §3). The nest that actually hit is the *interior* 2190 supply, not the top.

## 2. SETUP B — 2026 DISCOUNT LONG, Jun 30 (MISSED — wrong anchor, loss)
Price falls into Jun 30; the M5 open sweeps down to a **2114.5** low (close 2118.2), Jul 1 rallies from
~2120 to 2190. The **real demand is 2114–2120**.

```
D1  range 2091 ──────── 2238.8      Jun30 actual low = 2114.5 (→ Jul1 rally origin 2120)
      ▼
htf_nest fired LONG @ **2142.2–2145.8**  (Jun30 09:15)  →  **27pt ABOVE the real low**
      ▼  price runs straight through it → **LOSS** (mae 4.44 ATR, price to 2114.5)
════════════════════════════════════════════════════════════════════════════
The demand nest is anchored to the *earlier* ~2140 swing (Jun24/Jun29 lows), never re-anchored to the
2114.5 sweep. Detector "convergence" @ 2142–2146 is FURNITURE; the true convergence 2114–2120 is INVISIBLE.
```

## 3. SETUP C — 2026 the DESCENDING LOW (Jul13–16): the F2 demand failure in full
Lower lows: Jul13 **2120**, Jul14 **2116**, Jul15 **2091**, Jul16 2096. The LONG demand nest stays pinned
at **2138–2145** and fires there on Jul6/7/8/10/13 **as price falls through it** (losses). The deepest
LONG zone ever emitted is **2113.3–2115.5 on Jul16 — AFTER the 2091 low was already made**. The true
discount extreme 2091 (Jul15, based 13:00–15:00 then bounced +15pt to 2106) **never gets a nest**.
→ **min zone_lo 2113.3 vs true low 2091.0 = gap 22.3pt. The best discount setup is invisible.**

## 4. SETUP D — 2024 PREMIUM SHORT, Sep 25 (extreme CAPTURED but trade FAILS)
D1 tops 3035 (Sep23 13:00 H1); Sep24 distributes 3020→2946; Sep25 opens 2950.6, pokes 2953.6 (09:20),
rejects. Here the nest **does** anchor supply at the extreme: zones **3026–3034 / 3021–3028 / 3019–3021**
(zone_hi 3033.95 vs true 3035, **gap 1.1pt**). Yet these top shorts **won only 17.6%** — 3035 was tagged
and price stayed elevated (2905–3030) for a full week before the real fall came in Oct–Nov. **The extreme
was correctly seen and the extreme short still lost** — the inverse of the HAVELLS "at-extreme = 80%" claim.

---

## 5. RE-VERIFICATION — each HAVELLS finding, HUL numbers beside HAVELLS

### F1 — htf_nest counts furniture as depth → the nest term is an ANTI-signal
| metric | HAVELLS | HUL 2026 | HUL 2024Q4 | verdict |
|--------|---------|----------|------------|---------|
| SHORT: highest baseline yet lowest win | b_hit **0.59**, win **41.7%** | b_hit **0.600**, win **40.7%** | b_hit 0.534, win **16.2%** | **REPLICATES** (2026 near-identical) |
| LONG win | 48% | 54.5% (b_hit 0.36) | 40.4% (b_hit **0.597**) | REPLICATES |
| corr(b_hit, actual win) | ≈0 (anti) | **+0.018** | **−0.014** | **REPLICATES** — b_hit has zero predictive power |
| depth gradient (more align = better?) | depth 0→3 win **43→58%** | (all depth 2) | depth 2 → 3 win **36.4% → 16.7%** | **INVERTS** — more depth = worse |
| EQ-mid furniture graded as depth | yes (1158–1188 ~40%) | **absent** (all firings correct-side) | **present** (11 EQ-mid LONG nests, **18.2%** win) | mechanism REPLICATES 2024, absent 2026 |

**F1 REPLICATES.** The nest term is an anti-signal on HUL just as on HAVELLS: the side with the *highest*
baseline expectation (SHORT, b_hit 0.60) delivers the *lowest* win (40.7% / 16.2%), corr≈0, and the
*deepest* nests (depth 3) are the *worst* (16.7%). The EQ-mid-furniture mechanism is visible directly in
2024 (11 mid-range longs at 18%); in 2026 the firings happen to all land on the correct OTE side, so the
anti-signal there comes from **premium shorts firing on every retest before the drop**, not from mid-range.

### F2 — EXT anchored to the latest swing, never re-anchors the later extreme → zone capped short
| period | true HIGH | max zone_hi | gap | true LOW | min zone_lo | gap | verdict |
|--------|-----------|-------------|-----|----------|-------------|-----|---------|
| HAVELLS 2026 | 1234.34 | 1201.2 | **33** (never reaches) | — | — | — | baseline |
| **HUL 2026** | 2238.8 | 2231.5 | 7.3 (body only) | **2091.0** (fresh, Jul15) | **2113.3** | **22.3** | **REPLICATES on the LOW** |
| **HUL 2024Q4** | 3035.0 | 3033.9 | **1.1** | 2375.75 | 2381.0 | 5.2 | **WEAKER / near-ABSENT** |

**F2 REPLICATES but is condition-dependent.** It bites exactly when the extreme is **fresh and unretested**:
HUL 2026's discount low 2091 was made one session before data end and is never re-anchored (gap 22.3, best
setup invisible — §3), mirroring HAVELLS's un-re-anchored 1234 (gap 33). It **dissolves** when the extreme
is old and retested: over the 3-month 2024Q4 window both extremes anchor to 1–5pt. Same mechanism
(single-latest-swing EXT anchor), surfaces on whichever extreme is the *recent* one (the LOW on HUL 2026
because it down-trends, vs the HIGH on HAVELLS).

### nest_depth-at-a-D1-extreme discriminator (HAVELLS: at-extreme 80% vs EQ-mid 40%)
| bucket | HAVELLS | HUL pooled (2026+2024, n=122) | verdict |
|--------|---------|-------------------------------|---------|
| nests AT the extreme (short pos≥.90 / long ≤.10) | **80%** | **16.7%** (n=18) | **INVERTS** |
| interior / mid | ~40% | 37.5% (n=104) | — |
| SHORT at supply extreme (pos≥.90) | — | 17.6% (n=17) | at-top shorts worst |

**Does NOT replicate — it inverts.** On HUL the nests sitting *at* the D1 extreme are the **worst** (16.7%),
because HUL's extremes (2238.8, 3035) were tagged and *held* rather than swept-and-reversed. The HAVELLS
"depth × D1-extreme = 80%" edge required the sweep+BOS reversal to actually fire promptly; it did not on HUL.

### T1 — OTE-gate the base zone (short≥.62 premium / long≤.38 discount)
| split | HUL pooled win | verdict |
|-------|----------------|---------|
| OTE-ok = True | **0.333** (n=81) | no lift |
| OTE-ok = False | 0.366 (n=41) | — |
| SHORT premium (ok) vs SHORT discount | 0.294 vs 0.154 | gate helps shorts |
| LONG discount (ok) vs LONG premium | 0.400 vs **0.464** | gate **hurts** longs (2024 Sep up-trend rewarded premium longs) |

**WEAKER / ABSENT as a universal lift.** The OTE gate helps the short side (0.154→0.294) but *hurts* the
long side (0.464→0.400) because HUL's Sep-2024 up-trend rewarded premium longs — so pooled it nets to no
lift. T1's benefit is **regime-dependent** on HUL, not the clean HAVELLS win it was predicted to be.

### F5 — enter-before-sweep, AM shorts worst
HAVELLS: AM shorts worst. **HUL: AM (≤10:00) shorts win 31.4% (n=51) vs later shorts 7.7% (n=13)** →
**INVERTS / ABSENT** (small n; also a firing-timing artifact — most nests re-emit at the 09:15 session open).

### F6 — strength / zone-width blind (AUC≈0.48)
`htf_nest.strength` is effectively constant (0.667 for 110/122 rows; 1.0 for 12). It carries **no**
discrimination on HUL (depth-3/strength-1.0 rows are actually *worse*, 16.7%). **REPLICATES — blind.**

### F3 — tiny outer-wick stop shaken out
Not simulated here (needs 1m SL replay; out of scope for a firings/resample study). Left OPEN for HUL.

---

## 6. SUMMARY TABLE — replication verdicts
| finding | claim | HUL verdict |
|---------|-------|-------------|
| **F1** | nest term is an anti-signal (highest b_hit, lowest win; furniture as depth) | **REPLICATES** (2026 SHORT 0.600/40.7% ≈ HAVELLS 0.59/41.7%; corr≈0; depth3 worst) |
| **F2** | EXT never re-anchors the later extreme → zone capped below true extreme | **REPLICATES on the fresh extreme** (2026 low: gap 22.3, invisible) / **WEAKER 2024** (gaps 1–5) |
| depth×extreme | nests at D1 extreme hit 80% vs mid 40% | **INVERTS** (HUL at-extreme 16.7% < interior 37.5%) |
| **T1** | OTE-gate lifts win | **WEAKER/ABSENT** (helps shorts, hurts longs; pooled no lift — regime-dependent) |
| **F5** | AM shorts worst | **INVERTS/ABSENT** (AM 31.4% > later 7.7%, small n) |
| **F6** | strength/width blind | **REPLICATES** (strength constant, no AUC) |

## 7. What HUL adds to the thesis
1. **F1 (anti-signal) is the robust, symbol-independent finding** — it reproduces to two decimal places on
   HUL 2026 and stronger on 2024. The `htf_nest` term as wired grades the *loser* side highest. This is the
   core doc-45 result and it holds.
2. **F2 is real but only on FRESH extremes.** The single-latest-swing EXT anchor loses the *recent*
   unretested extreme (HUL 2026 low 2091, gap 22.3, best setup invisible) and captures old retested ones
   (2024, gap ≤5). The fix (re-anchor EXT to the current range extreme) is still warranted, but its payoff
   concentrates on the newest extreme — exactly the one you're about to trade.
3. **The HAVELLS "at-extreme = 80%" edge does NOT transfer.** It needed the sweep-and-*prompt*-reversal
   that HAVELLS's spike extremes had; HUL's extremes were tagged-and-held (3035 held a week), so extreme
   shorts were the *worst* bucket. → **OTE/extreme gating alone is insufficient; it must be conjoined with
   a confirmed sweep+BOS reversal**, or it will grade held-tops as A-setups. This sharpens T1: gate on
   *extreme AND reversal-confirmed*, not extreme alone.

zone_hi vs true D1 extreme (the headline ask): **2026 zone_hi 2231.5 vs true high 2238.8 (−7.3), and the
worse miss zone_lo 2113.3 vs true low 2091.0 (+22.3, the fresh discount extreme never re-anchored);
2024Q4 3033.9 vs 3035.0 (−1.1) and 2381.0 vs 2375.75 (+5.2).**
