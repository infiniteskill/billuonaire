# 47-40STOCK — EDGE-PRESERVATION RETHINK: regime & instrument (2026-07-24)

**Mandate:** do NOT lose the achieved graded edge (+6.13R/2026 mixed · +8.20R/2024-Q4 bear holdout, grade
ladder monotone out-of-sample). Be adversarial + quantitative. Every claim carries its number + n.
**Hard rule honored:** no `derive_tradebook.py` re-run, no pipeline. All numbers below are from the
`study40_2026` parquet (frame A), the `derive_work/*.jsonl` grading journals (which happen to persist the
**2024-Q4 verdict stream with direction + taught_grade** — a lucky, decisive artifact), and `tb_2024q4_40.txt`.

---

## THE CROWN JEWEL (restated, with the exact numbers we must not lose)

`tb_2024q4_40.txt`, frozen config, unseen 2024-Q4 bear tape (31/41 down), hi-tier = config `grade>=4`:

| stop-mode | hi n | win% | NET/t | ladder (g4/g5/g6/g7) | quadrants (all +) |
|---|---|---|---|---|---|
| intrabar | 3001 | 62 | **+8.200R** | +5.43 / +8.34 / +9.54 / +8.62 | 12.14 / 11.07 / 5.11 / 6.60 |
| m5_close | 3016 | 65 | **+8.352R** | +5.28 / +8.41 / +9.89 / +8.97 | 12.52 / 11.21 / 5.08 / 6.74 |
| eod-prod | 3049 | 72 | **+8.068R** | +5.27 / +8.57 / +8.86 / +8.73 | 10.60 / 9.77 / 5.83 / 7.33 |

Ladder monotone g3→g6 every mode (g1/g2 negative, g3 breakeven). This is real and it is the asset.

---

## (a) STRESS THE CROSS-REGIME PASS — is +8.2R bear-favorability (regime-ALIGNED shorts) or genuine?

### The hypothesis to kill
"The taught method is short-biased/fade; 2024-Q4 is 31/41 down; therefore the +8.2R is shorts riding the
bear → the pass is regime-ALIGNED, not regime-agnostic, and a bull tape breaks it."

### What the data says — the hypothesis is FALSE (the pass is NOT all-shorts)
The `derive_work/2024-*.jsonl` journals persist every config-`grade>=4` grading **verdict on the 2024-Q4
tape, with `direction`** (the orchestrator journals at config `min_grade=4`, so the journal population **IS
the hi-tier**). Measured direction mix of the crown-jewel tier on the bear tape:

| slice | SHORT | LONG | %SHORT | n |
|---|---|---|---|---|
| 2024-Q4 hi-tier, raw verdicts | 4409 | 6940 | **39%** | 11,349 |
| 2024-Q4 hi-tier, dedup to distinct (sym,day,zone,dir) | 2984 | 5033 | **37%** | 8,017 |
| 2024-Q4 **grade-8** (strongest) | 112 | 499 | **18%** | 611 |
| 2026 mixed hi-tier (contrast) | 1548 | 1428 | 52% | 2,976 |

**On the bear tape the +8.2R tier is 63% LONG.** The strongest cell (grade-8) is 82% long. The crown jewel
is **majority counter-trend LONG on a down tape** — the opposite of the "all-shorts" hypothesis.

### So what fraction of +8.2R plausibly came from shorts? ~40%, NOT ~all.
Shorts are 37% of the tier by count. Even granting shorts the frame-A directional advantage (below), a bound:
solve for graded win by direction holding the 62% tier mean and the ~+10pp short gap → SHORT win ~0.68 /
LONG ~0.58; net-R contribution (share × (win·~13R − (1−win)·1R)) ⇒ **SHORT ≈ 41% of net-R, LONG ≈ 59%.**
Shorts cannot exceed ~half; the majority of the +8.2R came from **counter-trend reversal longs.**

### The frame-A directional signal (2026 parquet, symmetric 1ATR:1ATR, decided n) — the proxy for "bear conditions"
| regime | dir | n | win% | edge(win−b_hit) | mfe/atr | mae/atr |
|---|---|---|---|---|---|---|
| DOWN | LONG | 5256 | **44.3** | +0.057 | 5.44 | 6.59 |
| DOWN | SHORT | 5381 | **54.9** | +0.083 | 6.19 | 5.12 |
| RANGE | LONG/SHORT | 10466/10126 | 47.5/52.7 | +0.076/+0.082 | ~1.2 | ~1.2 |

SHORT beats LONG in **10/11 DOWN stocks** (ASHOKLEY the lone ~tie 47/46) — broad, not 1–2 names. So in a
symmetric frame the bear tape *does* favor shorts by ~+10.6pp. **Yet the grader picks 63% long.** Why:
config `grade` is a **sweep+BOS-reversal + OTE + phase** conjunction — on a down tape, sweep-of-lows→BOS-up
(reversal-long) setups are the most frequent A-grade objects (every bounce), so the grade systematically
selects the *counter*-symmetric-favored direction and still wins because **2024-Q4 was a correction rich in
sharp V-bounces**, and the large-R targets harvest them.

### The real driver is VOLATILITY (large two-sided excursion), not direction
ATR is **not** understated for DOWN (atr/price median RANGE 0.196% · UP 0.214% · **DOWN 0.215%** — equal),
but realized excursion is ~5× larger: median mfe/price RANGE **0.101%** vs DOWN **0.487%**; median mfe/atr
RANGE 0.49 vs DOWN **2.17** (mean 5.44 — fat right tail). The +8.2R is a **large-excursion harvest gated by
grade**: tiny 1-ATR stop vs multi-ATR runs = double-digit R multiples. Both tapes that PASSED (2026
mixed-with-range, 2024-Q4 correction) are **high-two-sided-excursion, reversal-rich** tapes.

### Verdict on (a) — RE-FRAMED, and it sharpens the bull test
The pass is **not** regime-aligned *shorts* (it's 63% long). But it **is** regime-aligned *volatility*:
the edge is a mean-reversion / large-excursion harvest, and every tape it has seen is bouncy. The
falsification risk is therefore **not** "shorts vs longs" — it is a **low-volatility grinding melt-up**,
which is simultaneously (i) low-excursion (large-R targets rarely fill) and (ii) directionally hostile to
the 37% short leg. **Bull test remains make-or-break — for a deeper reason than the brief hypothesized.**

**Caveat (n-honesty):** the direction mix is from grading *verdicts* (hi-tier n=11,349 / dedup 8,017), a
~3.8× superset of the ~3,001 tb takes; the 63%-long conclusion survives dedup (63%) and is robust, but R
*by direction on 2024* is NOT directly measurable without a re-derive — hence the ~40% short-contribution is
a reasoned bound, not a measured split. This is exactly the gap (c) closes.

---

## (b) THE DECISIVE BULL ADVERSARIAL TEST

### Tape / window — a *grinding* melt-up (low-vol, few pullbacks), not a bouncy uptrend
Pick a sustained low-volatility advance where drift is persistent and excursions are *small* — the exact
opposite of the correction/range tapes already passed. Indian large-caps: **2023-Q4 (Oct–Dec 2023)** or the
**2024-Q1 (Jan–Mar 2024)** grind are the cleanest melt-ups (persistent up-drift, shallow dips). Fetch 1m for
the same universe family, same session spec, **frozen config** (`taught_profile/config.json`, untouched).

### How to pick bull stocks — per-stock D1 drift filter (reuse `_REGIME.md` machinery) + a melt-up gate
Select symbols that are `UPTREND` by the existing rule — `drift% > +3 AND close_pos > 65` — **AND** add a
*grind* gate so we test low-excursion, not V-bounce: `down_day_fraction < 0.40` **AND** `median(mfe/atr) <
1.0` (i.e. exclude names whose "uptrend" was actually big two-sided swings). Target ~20–30 qualifying names;
this deliberately starves the harvest of the volatility it fed on.

### PASS / FAIL thresholds (on the hi-tier = config `grade>=4`, the crown jewel)
| outcome | hi-tier net-R | ladder | direction split | reading |
|---|---|---|---|---|
| **CONFIRM (regime-agnostic)** | **≥ +3.0R** | monotone g4<g5<g6, win ≥50% | book + even with 37% shorts | edge does NOT need two-sided vol → genuinely regime-agnostic; green-light paper pilot |
| **CONDITIONAL (mode-switch mandatory)** | 0 .. +3R, OR ≥+3R only after removing shorts | ladder holds | longs +, **shorts deeply −** | edge real but regime-attenuated; the 37% counter-trend shorts bleed → mode-switch (#8) becomes a *requirement*, not an option |
| **FALSIFY (edge was volatility-specific)** | **≤ 0R**, or worse than g3 breakeven | ladder collapses / inverts | longs ALSO ≤0 | the +8.2R was a large-excursion/mean-reversion harvest; two prior passes were volatility-aligned, not regime-agnostic → thesis downgraded to "regime-conditional, needs a vol/regime gate to trade" |

+3R bar rationale: half the *weakest* prior pass (+6.13R) with the ladder intact is a conservative "still
clearly an edge" line; anything under +3R is attenuation worth flagging.

### The load-bearing diagnostic — split the FAIL into "wrong direction" vs "no volatility"
Because (a) proved the driver is excursion, the bull run must **report the excursion distribution
(median/mean mfe·atr) and the per-direction hi-tier net-R**. This disambiguates the two failure modes:
- **Shorts ≤0 but longs stay ≥+3R, excursions normal** → *directional* failure → mode-switch fixes it (edge SURVIVES gated). This is the survivable outcome.
- **Longs ALSO collapse, median mfe/atr < ~1** → *excursion* failure → the harvest has no fuel in a grind → the deeper falsification; no direction gate recovers it.

### What each result MEANS for the thesis
- CONFIRM → three regimes (bull grind + bear correction + mixed range), edge robust → the historical-edge question is closed; remaining risk is execution/live-frictions only.
- CONDITIONAL → edge is real but the frozen regime-blind config is NOT shippable as-is; the mode-switch moves from "BUILD later" to "BUILD before any pilot."
- FALSIFY → the crown jewel is a volatility harvest, not a universal grade edge; must gate trading to
high-excursion regimes (a realized-vol filter) or abandon the "regime-agnostic" claim. Either way we learn
it **before** risking capital, which is the entire point.

---

## (c) THE CHEAP ENABLER — persist the per-trade tradebook so every future tune is A/B'd offline in seconds

**Why this is THE key to touching anything without risking the edge.** The central danger (brief + `_SYNTHESIS`)
is that the deep-study tunes were measured in **frame A** (symmetric coin-flip), never in **frame B** (the
graded +8R). A symmetric-frame win can be a graded-frame loss. Today the only way to test a tune on frame B
is a **~3hr re-derive**. If `derive_tradebook.py` *persists the per-trade graded tradebook once*, every
candidate tune (drop `b_hit==0`, T3 buffer, no-blind, a mode-switch gate, a direction veto) becomes an
**offline pandas filter over a saved frame — seconds, zero re-derive, zero risk to the frozen config.**

### Minimal diff (additive only — no path/logic change, cannot perturb the edge)
`derive_tradebook.py`, `report(mode)` already builds `rows = [(t, o, r, net), ...]`. The `t` dict carries
`sym, ts, dir, entry, sl, target, grade`; `o`=outcome, `r`=gross-R, `net`=net-R. Add a regime label from
the `_REGIME.md` map and dump one parquet per mode. `b_hit` is **not** on the `Decision` today (it's a
study-frame null-model, not a decide() field) — persist the `reasons`/grade-decomposition instead (it
encodes bos/sweep/ote/phase/nest:N/maturity:M, which is *more* useful for term-level A/B), and add `b_hit`
later only if we expose it from decide().

```python
# top of file
import pandas as pd
_UP={"AARTIIND","ABB","APOLLOHOSP","BAJAJ-AUTO","BAJFINANCE","BIOCON","DLF","TITAN"}
_DN={"ABFRL","ADANIPOWER","ASHOKLEY","AXISBANK","BALKRISIND","BANKBARODA",
     "BERGEPAINT","CANBK","CGPOWER","COALINDIA","CROMPTON"}
_reg=lambda s:"UP" if s in _UP else ("DOWN" if s in _DN else "RANGE")

# in _tap(...).run_all, when appending the trade, also capture the grade decomposition:
#   trades.append({... , "grade": d.grade, "reasons": list(getattr(d, "reasons", []))})
#   (decide() already builds `reasons`; add `reasons` to the Decision dataclass + return it — 1 line each)

# inside report(mode), AFTER the `rows` loop, before/after printing:
    pd.DataFrame([{
        "mode": mode, "sym": t["sym"], "ts": t["ts"], "reg": _reg(t["sym"]),
        "dir": t["dir"], "grade": t["grade"],
        "entry": float(t["entry"]), "sl": float(t["sl"]), "target": float(t["target"]),
        "outcome": o, "R": r, "netR": net,
        "reasons": ";".join(t.get("reasons", [])),
    } for (t, o, r, net) in rows]).to_parquet(
        ROOT / f"runs/validate/tradebook_{mode}.parquet", index=False)
```

Three files (`tradebook_intrabar/m5_close/eod.parquet`), written for free at the end of a run we already do.
From then on: **every tune is `df.query(...)`** — e.g. `df[df.b_hit>0]` (once exposed), or
`df[~df.reasons.str.contains('nest:0')]`, grouped by `reg`×`grade` — and we read the Δ net-R on the REAL
graded frame in seconds. **This is the safety mechanism that lets us change things without re-deriving and
without risking the crown jewel.** Do it **before** applying a single deep-study tune to the config.

---

## EDGE-RISK VERDICT

| item | risk to +8R edge | why |
|---|---|---|
| (c) persist tradebook | **SAFE** — additive logging, no path/logic touch | writes a file at end of an existing run; cannot alter decide()/sim |
| (b) bull adversarial test | **SAFE** — read-only, new tape, frozen config | can only *inform*; a FAIL is information, not damage |
| Apply deep-study frame-A tunes to config **now** | **RISKY — DO NOT** | measured in frame A, never in frame B; a symmetric-frame win can be a graded-frame loss. Gate every tune through (c) first |
| Touch the frozen `taught_profile/config.json` before (c) exists | **RISKY** | no offline A/B harness yet ⇒ any change is an untested 3hr gamble against the crown jewel |

**Bottom line:** the cross-regime pass is genuine but is **volatility/excursion-aligned, not shorts-aligned**
(63% long on the bear tape; shorts ~40% of net-R). That re-frames — does not remove — the bull risk: the
true out-of-domain test is a **low-vol grinding melt-up**, run frozen, PASS ≥+3R hi-tier with monotone
ladder. Build **(c) the persisted tradebook first** — it is the cheap, zero-risk enabler that converts every
future tune from a 3hr edge-gamble into a seconds-long offline A/B. **Protect the edge: instrument, then
test on a bull tape, before changing one config line.**
