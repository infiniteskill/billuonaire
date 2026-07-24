# 45 — HAVELLS CONVERGENCE TREE: HTF→LTF nesting, where the timeframes converge (2026-07-24)

Deep study: resample raw 1m (2026 + 2024Q4) to D1/H1/M15/M5, trace 3 concrete strong setups
top-down (D1 dealing-range extreme ⊃ H1 zone ⊃ M15 ⊃ M5 entry ⊃ tiny stop), show nest_depth +
the CONVERGENCE PRICE (where all TFs agree), diff vs the user's hand-drawing (6 multi-TF images),
state the rule, and pin where the wired `htf_nest` (EXT-band parents, min_depth=2) does vs does NOT
capture it. RECOGNITION, not edge-hype. All prices are from `pandas.resample` of the raw 1m; no
pipeline run (derive_work left untouched).

## 0. Data + the two dealing ranges (resampled, verified)
| period | 1m rows | span | D1 low (swept) | D1 high (raid) | window |
|--------|---------|------|----------------|----------------|--------|
| 2026   | 6 000   | Jun25–Jul17 (16 D1 bars) | 1140.5 (Jun30) | 1234.0 (Jul08) | intraday leg |
| 2024Q4 | 22 874  | Sep02–Nov29 (61 D1 bars) | 1586.8 (Nov)   | 2106.0 (Sep23) | multi-month |

The user hand-draws the D1 range as two **"LIQUIDITY EXTREME RED LINES"** (img 08-13-01, 30m):
upper **1234.34**, lower **1125.51** → EQ = **1179.9**. The resampled D1 confirms it exactly: the
2026 leg tops at 1234.0 (tags the upper line to the tick on Jul 8) and bottoms at 1140.5, oscillating
inside the drawn box. So the D1 "dealing range" is not a metaphor — it is a measured 1125.5–1234.3
channel with EQ 1180; everything above 1180 = **premium (sell)**, below = **discount (buy)**.
(img HAVELLS_T1_fib_ote adds the HTF **fib/OTE** overlay on the same range — 0%/100% + a shaded
61.8–70.2% OTE band = the "sensitive" retrace zone.)

---

## 1. SETUP A — PREMIUM SHORT, 2026-07-09, entry 1221 (T1 `fib_ote`, the 3-pt stop)
D1 raids the 1234.34 buy-side line (Jul 8 11:30 M15 high = **1234.0**), distributes, breaks down;
Jul 9 retraces UP into the supply left behind → short the mitigation at 1221, stop 3 pt above.

```
CONVERGENCE TREE — SHORT (bearish nest)                         entry pct in D1 range = 87.7% (PREMIUM)
D1  dealing range 1125.5 ─────────────────────────── 1234.3     OTE-premium band 1193.0–1211.5
      │  premium half (>1180); Jul8 tags 1234 = buy-side raid → EXT_H supply
      ▼
H1  supply origin Jul8 11:00–13:00 ..... zone 1226 ── 1234   (high 1234.0, closes 1222→1210 = distribution)
      │  Jul9 09:00 H1 retrace high 1223.0 mitigates lower edge
      ▼
M15 mitigation block Jul8 12:00–12:30 .. zone 1220 ── 1228   (1227→1221 down-bodies under the high)
      │
      ▼
M5  rejection Jul9 09:15→09:20 ......... zone 1220.8 ─ 1223.0 (poke 1223, open-away 1220.8, close 1215)
      │
      ▼  ENTRY 1221  ·  SL 1224 (1 pt above the 1223 wick)  ·  RISK = 3 pt / 0.25%
════════════════════════════════════════════════════════════════════════════════
CONVERGE @ 1220.8–1224  (D1-premium ∩ H1-supply-low-edge ∩ M15-mitig ∩ M5-reject)  nest_depth = 3
OUTCOME: Jul9 1221→1183 (target 1197 hit same day = +24pt = 8R) → Jul17 low 1142 (+79pt = 26R)
```

---

## 2. SETUP B — DISCOUNT LONG, 2026-06-30, entry ~1141 (T2a mitigation, run to the opposite line)
Price falls Jun25 1196 → Jun30 sweeps 1140.5, closes back up (rejection), rallies to the 1234 line.

```
CONVERGENCE TREE — LONG (bullish nest)                          entry pct in D1 range = 14.2% (DISCOUNT)
D1  dealing range 1125.5 ─────────────────────────── 1234.3     OTE-discount band 1148.4–1166.9
      │  discount half (<1180); sweep toward 1125.5 = EXT_L demand
      ▼
H1  demand Jun30 09:00–10:00 ........... zone 1140.5 ─ 1148   (down-leg base; 10:00 low 1140.5, closes up)
      │
      ▼
M15 sweep-OB Jun30 10:00–10:15 ......... zone 1140.5 ─ 1142   (10:15 low 1140.5, close 1146.5 = rejection)
      │
      ▼
M5  demand Jun30 10:10→10:25 ........... zone 1140.5 ─ 1142.8 (10:20 low 1140.5, 10:25 closes 1146.5 = BOS↑)
      │
      ▼  ENTRY ~1141.6 (CE)  ·  SL 1139 tick / 1133 user (below the 1140.5 wick)  ·  RISK = 2.6–8.6 pt / 0.2–0.7%
════════════════════════════════════════════════════════════════════════════════
CONVERGE @ 1140.5–1143.3  (D1-discount ∩ H1-demand ∩ M15-OB ∩ M5-OB — a 3-pt band)   nest_depth = 3
OUTCOME: 1141→Jul1 1200→Jul7 1228→Jul8 1234 (tags the upper line) = +93pt; R = +11 to +36 by stop
NOTE: entry 1141 is BELOW OTE-discount (1148) = a sweep of the OTE low into the extreme, then reverse.
```

---

## 3. SETUP C — PREMIUM SHORT, 2024-09-25, entry 2050 (T4 mitigation, multi-month leg)
Sep rally tops Sep23 at **2106** (buy-side raid off the ~1859 Sep base), distributes Sep24, Sep25
retraces into supply → short 2050, stop above the 2073–2075 rejection.

```
CONVERGENCE TREE — SHORT (bearish nest)                         entry pct in D1 range = 77.3% (PREMIUM, OTE-top)
D1  swing 1859 ──────────────────────────────────── 2106       OTE-premium band 2012–2054  (EQ 1982)
      │  Sep23 tags 2106 = EXT_H supply; entry 2050 sits at the OTE-premium ceiling
      ▼
H1  supply Sep23 12:00–Sep24 09:00 ..... zone 2075 ── 2106   (2106 high, closes down; Sep24 2087→2054)
      │  Sep25 09:00 H1 retrace high 2073 mitigates lower edge
      ▼
M15 supply Sep25 09:15 ................. zone 2065 ── 2075   (poke 2073.0, close 2065.5 = rejection)
      │
      ▼
M5  rejection Sep25 09:15→09:20 ........ zone 2062 ── 2073   (high 2072.95, open-away 2068.45)
      │
      ▼  ENTRY 2050  ·  SL 2075 (above the 2073 wick / H1 supply edge)  ·  RISK = 25 pt / 1.2%  (H1-level stop)
════════════════════════════════════════════════════════════════════════════════
CONVERGE @ 2050–2075  (D1-premium-OTE ∩ H1-supply ∩ M15-supply ∩ M5-reject)          nest_depth = 3
OUTCOME: Sep26 1991 → Oct3 1919 (target 1920 hit = +130pt = 5.2R) → Oct17 1785 (+265pt = 10.6R)
```

---

## 4. How the user HAND-DRAWS the nesting (6 multi-TF images) vs the detectors
| element | user's drawing (imgs 08-13-01, T1, 09-42-03, 10-08-01, T22, T23) | detector reality |
|---------|------------------------------------------------------------------|------------------|
| D1 context | 2 red "LIQUIDITY EXTREME" lines (1234.34 / 1125.51) + fib/OTE band | `premium_discount` (fires 709×) + `extremes` EXT_H/EXT_L |
| HTF zone | green OB **box** at the swept extreme, born only after **liq-sweep + BOS** | `ob_taught` bodies-box; sweep-gated |
| nesting | tighter box drawn INSIDE the wider zone (T22: 4000–30 inside 4000–50) | `htf_nest` counts higher-TF parents that contain the base |
| entry | **inner-body mid-line** ("ENTRY" label mid-box) | `htf_nest` ce = base mid ✓ (matches) |
| SL | **beyond the OUTER WICK** of the sweep spike (1 tick past) | `htf_nest` sl = base far edge (close, sometimes too tight) |
| target | opposite red line / EQ / prior liquidity | — |

The images teach an explicit **top-down recursion**: draw the D1 range → mark the HTF OB at the
swept extreme → drop a TF, find the nested OB → repeat to M5 → enter mid, stop past the outer wick.
Every one of Setups A/B/C is this exact object: **D1-extreme ⊃ H1 ⊃ M15 ⊃ M5, all same direction,
converging on a 3-pt (2026) / 25-pt (2024) band.**

---

## 5. THE RULE (measured, not asserted)
> **A valid HAVELLS entry = an LTF (M5) decisional zone nested ≥2 higher TFs deep AND sitting at a
> D1 extreme (premium for shorts / discount for longs, at-or-beyond the OTE band), same direction
> throughout. The stop is 1 tick past the OUTER WICK of the M5 zone; the target is the opposite D1
> line.** nest_depth alone is necessary but NOT sufficient — the D1-EXTREME condition is the other half.

Evidence for the "AND at a D1 extreme" clause, straight from the fired `htf_nest` rows (HAVELLS):
- Nests anchored **at the two D1 extremes** → **80% hit** each: the 1141.0–1143.3 discount-demand
  LONG (n=5, 80%) and the 1197.3–1201.2 supply SHORT (n=5, 80%).
- Nests in the **EQ mid-range** (1158–1188, 1165–1180, 1173–1179 …) → **~40–48% hit**; these drag
  LONG hit% to 48% and SHORT to 31%. Same nest_depth, no extreme → coin-flip.
=> depth × D1-extreme is the discriminator; depth × mid-range is noise. This is the doc-36
HTF-alignment thesis sharpened: *alignment must terminate at a D1 EXTREME, not just any HTF overlap.*

---

## 6. Where the wired `htf_nest` (EXT-band parents, min_depth=2) CAPTURES vs MISSES
`htf_nest.py`: base = M5 OB/FVG (ACTIVE/TESTED); parents = OB/FVG **or EXT bands** (EXT_L=demand,
EXT_H=supply) on higher TFs; nest_depth = # distinct higher TFs whose same-dir parent overlaps the
base; emits when depth ≥ min_depth (=2, iter-7 tune); ce = base mid, sl = base far edge.

**CAPTURES (✓):**
- **Setup B (discount 1141).** Fired the 1141.0–1143.3 LONG nest on Jul 1/2/3/6/7 — depth 2 (0.667
  strength) — and it **hit 80%**. The EXT_L parent at the discount extreme was anchored correctly, so
  the discount-demand nest is fully in the net. The entry-mid + far-edge-SL match the user's drawing.
- **Setup A's fallback (EQ supply).** Fired 1197.3–1201.2 SHORT, hit 80%. This is the *intermediate*
  H1 supply, one rung below the true premium extreme.

**MISSES (✗) — the concrete gap:**
- **Setup A's actual entry (1221 mitigation at the 1234 extreme) is INVISIBLE.** Across all 37 HAVELLS
  `htf_nest` rows, **zone_hi never exceeds 1201.2** — it never reaches the 1234.34 premium line. The
  M5 supply at 1221 had NO higher-TF EXT_H parent overlapping it (the EXT_H was anchored at ~1201, the
  earlier Jul1–2 swing, not the later 1234 spike), so nest_depth = 0 → not emitted. **The user's single
  best short — 3-pt stop, target hit +8R, ran +26R — is exactly the setup the detector cannot see.**
- **min_depth=2 with EXT-only parents fires the EQ mid-range nests** (1158–1188 etc., ~40% hit) because
  an EXT band clips them "somewhere," inflating depth without a real extreme. Depth is satisfied by
  furniture, not by a terminal D1 extreme.

Root causes: (a) `htf_nest` has **no true multi-TF OB/FVG parent emitter** — it leans on EXT bands only
(the "STARVED / needs infra" note, 42-REFINE §iter-4); (b) the EXT_H/EXT_L anchor is a single latest
swing, so a **later, higher extreme (1234) is not re-anchored**; (c) there is **no premium/discount
gate** on the base zone, so mid-range nests pass.

---

## 7. THE CONCRETE TUNE THIS IMPLIES (additive, default-preserving)
1. **Gate the base on the D1 OTE/extreme, not just EXT overlap.** Require the base M5 zone to sit in
   the `premium_discount` OTE band on the correct side (short→premium ≥0.62, long→discount ≤0.38).
   This kills the ~40%-hit EQ-mid nests and keeps the 80%-hit extreme nests. Predicted effect: LONG
   hit 48→~70%+, SHORT 31→~70%+ by dropping mid-range firings (mirrors the iter-8 "furniture cut").
2. **Re-anchor EXT_H/EXT_L to the CURRENT range extreme (highest high / lowest low still unmitigated),
   not the latest swing.** Then the 1234 line becomes a live EXT_H parent and Setup A's 1221 nest
   gains depth ≥1 → is emitted. Without this, the best premium-extreme mitigations stay invisible.
3. **SL = 1 tick past the OUTER WICK of the base, not the body far edge** (matches the drawing;
   35-FEATURE-ANATOMY §OB). On these setups the outer-wick stop is 2.6 pt (B) / 3 pt (A) — the tiny
   stop that makes the +8..+36R geometry; the body edge would be even tighter and gap-through prone.
4. **Keep min_depth=2 but redefine a "tier" as an OB/FVG **or** re-anchored EXT at a range extreme** so
   depth measures true D1⊃H1⊃M15 alignment (all 3 user setups are depth-3) rather than incidental EXT
   clipping. Pairs with the multi-TF OB emitter still owed (G2 infra).

Net: the wired `htf_nest` already proves the doc-36 edge (nest_depth grades the winners, +6.13R
high-tier, holdout-stable — 42-REFINE §iter-8) — but it currently grades the *discount* side and the
*EQ* supply, while **missing the premium-EXTREME mitigation that is the user's textbook short**. Adding
the OTE gate (1) + extreme re-anchor (2) closes exactly that gap; both are additive and testable on the
existing parquet without a pipeline run.
