# audit_regime — wyckoff + compression + premium_discount vs the taught visual language (2026-07-25)

Method: code read vs _SPEC/obs_a..d; standalone bit-faithful replications of `wyckoff._event`,
`compression._score/_maturity`, `premium_discount` (real `extremes` functions imported) on
data/marks_2026 1m; real-pipeline cross-check via `trader.cli study --only`. Branch stage2.
Scripts: scratchpad `wy_audit.py`, `pd_sweep.py`. NO config/code changed.

## 1. CODE-VS-SPEC

**wyckoff** — schematics (obs_d, 5 imgs) mark Spring = LOWEST point undercutting range low (phase C),
UTAD = highest above range, "no volume notes" on EVERY schematic; the traded structure is multi-week.
Code: 40×5m window (≈3.3h) band < 3×ATR(5m), single-bar poke + close-in-own-bar-half + vol>1.5×SMA20.
Three deltas: (a) **scale** — band_max ≈ 7.4 pts (median ATR5m 2.47) vs taught HAVELLS range 94 pts
(1140-1234, ~18 sessions): a 12× mismatch; the 40×5m band was in-range only **2% of bars** Jun24-Jul17.
(b) **vol gate not taught** (G8) — no schematic mentions volume, and at taught scale it VETOES both
taught events (measured ratios 1.06×, 1.48× vs 1.5 threshold). (c) no phase sequencing (any poke = event,
no SC/AR/ST precedence, no Test) — acceptable simplification, but "close in own-bar half" ≠ the taught
"close back inside range"; at 1h scale both taught bars pass it anyway (keep).

**compression** — 12×5m (=1h) coil, box = last-6 extremes. This is the LEG-scale PO3 armer, NOT the
Wyckoff "cause": measured 109 boxes/18 sessions, median box 5.0 pts vs the taught multi-day 90+ pt cause.
Role-correct — do not stretch it. One degeneracy: `_maturity` duration term `min(len(w)/12,1)` is a
**constant 0.25** (len(w)==window always when it fires) — the "duration" input to the maturity grade is
dead code; maturity spread (0.45..0.93, med 0.78) comes entirely from contraction+touches.

**premium_discount** — taught dealing range = the LOCAL traded structure (t1: 1125.5-1234.34 ≈ 6 weeks;
_SPEC row: "LOCAL dealing range … also FRACTAL within a zone"). Code range = the singleton GLOBAL master
EXT pair (all-history max-H/min-L per tf — `extremes._sync` flags exactly one of each). stage2's
`range_lookback_days`/`PD_LOOKBACK_DAYS` **filters that singleton pair by born-date** — it can only
switch the gate OFF (masters older than the window ⇒ empty side ⇒ no emission), it can NEVER re-anchor
locally. This is why the 47/Z3 local-window A/B was inconclusive (n16): arm B was "gate absent", not
"gate local". Fractal within-zone p/d = G5, separate, still open.

## 2. DETECTION ACCURACY (measured)

**wyckoff on HAVELLS, frozen 5m config, Jun-24..Jul-17** — 6 events, ALL micro-chop (07-02 15:10/15:25,
07-06 14:55, 07-07 09:15, 07-13 09:15, 07-17 14:15); **0 at the taught spots**. The 06-30 spring day
(low 1140.3, user entry 1141) and 07-08 top (1234.0, user's 1221 short) never even reach the range gate —
those days' travel alone exceeds the 7.4-pt band. Gate ablation (vol off / half off / both off) adds only
more chop, never the taught spots: the RANGE DEFINITION is the binding miss, not the gates.

**wyckoff re-scaled to the taught frame (1h, W=70, range_atr=12, vol gate OFF)** — 8 events/6 weeks incl.
**SPRING 06-30 10:15 @1140** (the user's long, same bar as the 1141 fill) and **UPTHRUST 07-08 11:15
@1234** (the 11:30 extreme in obs_a t1 = the 1221 short thesis). W=100 loses the spring (window swallows
the Jun-01/02 1124 lows); W=40 adds 3 noise events; vol gate ON kills both taught events (1.06×/1.48×).

**premium_discount lookback sweep** (side called at the mark's entry bar; leg_pct 2.0, tf 1h,
min_range_atr 4.0 — height gate passed in every non-silent cell):

| mark (want) | lb=0 (prod) | lb=10 asImpl | lb=10 local | lb=20 local | lb=40 local |
|---|---|---|---|---|---|
| H_jul_short 07-09 @1221 (SHORT) | [1124-1515] 0.25 disc→LONG ✗ | SILENT | [1140-1234] 0.87 prem→SHORT ✓ | 0.87 ✓ | 0.89 ✓ |
| H_jun_long 06-30 @1141 (LONG) | 0.05 disc→LONG ✓ | SILENT | ✓ | [1126-1209] 0.19 ✓ | ✓ |
| Da_jul_short 07-08 @448 (SHORT) | [403-534] 0.34 disc→LONG ✗ | SILENT | [422-451] 0.90 prem→SHORT ✓ | 0.91 ✓ | 0.83 ✓ |
| Da_jun sweep 06-24 @421 (LONG) | 0.13 ✓ | SILENT | SILENT (no pair yet) | [418-439] 0.13 ✓ | ✓ |
| Da_jun_long 07-01 @423 (LONG) | 0.16 ✓ | SILENT | [417-431] 0.44 ✓ | 0.31 ✓ | 0.22 ✓ |

asImpl (stage2 code) is SILENT for every lb>0 on every mark. **Local-recompute masters: lb=20d = 5/5
correct direction and reproduces the taught boxes exactly** (HAVELLS 1140-1234 = the t1 range; DABUR
417-451 = the t25 swept-low/liquidity-line pair). lb=0 miscalls BOTH taught shorts LONG (the Z3 flip).
Real-engine confirmation (study, HAVELLS May-01..Jul-17, --only extremes,premium_discount, taught
profile): lb=0 → 124 p/d evidences spread over the whole span; lb=10 → **11 evidences, all ≤ May-15**
(while the in-feed masters were freshly born), then permanently silent — zero on any mark day.
H_old_short(1910)/H_570 are prior-year marks — not in 2026 data, excluded.

## 3. ISSUES → SURGICAL TWEAKS (exact A/B, no config change, no commits)

**P1 (CRIT) p/d lookback filters instead of recomputing** — `premium_discount.py:54-60`: move the `lb`
read above the comprehension and make lb>0 drop the master-flag requirement (non-EXT kinds already fall
out at the highs/lows step):
```python
lb = float(self.params.get("range_lookback_days") or os.environ.get("PD_LOOKBACK_DAYS") or 0)
masters = [lv for lv in ctx.levels
           if lv.state in _ACTIVE and (lv.meta.get("master") or lb > 0)
           and (lv.tf is tf or lv.tf is None)]
```
A/B: `cd app && PD_LOOKBACK_DAYS=20 python -m trader.cli study --data ../data/marks_2026 --symbols HAVELLS,DABUR --from 2026-05-01 --to 2026-07-17 --only extremes,premium_discount --dir ../runs/validate/taught_profile --out /tmp/pd20`
— pre-fix expectation (measured at lb=10): emissions die by mid-May; post-fix: alive through July.
Direction check: `python scratchpad/pd_sweep.py` → expect the 5/5 lb=20 column. Then edge gate:
`python3 tools/ab_tradebook.py runs/validate/tradebook_2026.csv none` must hold hi≥5 net-R + quads.
Recommend sweeping lb ∈ {15,20,30} (lb=10 too tight for freshly-formed structures — DABUR 06-24 silent).

**W1 (HIGH) wyckoff scale + vol gate** — parameterize the hardcoded 1.5 (`wyckoff.py:104-105`):
`_DEFAULTS += {"vol_mult": 1.5}`; `m=float(self.params["vol_mult"])`; skip the check when `m == 0`.
Then A/B via a SCRATCH config (repo untouched):
```bash
CFG=/tmp/audit_ab; mkdir -p $CFG; cp runs/validate/taught_profile/config.json $CFG/
python3 -c "import json;p='$CFG/config.json';c=json.load(open(p));c['detectors']['params']['wyckoff']={'tf':'1h','window':70,'range_atr':12.0,'vol_mult':0};json.dump(c,open(p,'w'),indent=1)"
cd app && python -m trader.cli study --data ../data/marks_2026 --symbols HAVELLS --from 2026-06-01 --to 2026-07-17 --only wyckoff --dir /tmp/audit_ab --out /tmp/wy1h
```
Recognition pass = evidence.parquet contains SPRING 06-30 10:15 + UPTHRUST 07-08 11:15 (frozen 5m
config: neither). Keep the 5m instance too if the intraday springs earn their keep — decide via
ab_tradebook, not by recognition alone. Note `phase()` inherits the same scale fix for free (1h
ACCUMULATION/DISTRIBUTION instead of 3.3h flicker).

**C1 (LOW) compression maturity dead term** — duration input constant 0.25; TUNE frozen, grade-input
only → leave frozen; if ever touched, replace `len(w)/12` with box AGE in bars since `fsm.box_ts`.
No other compression change: it is the leg-scale armer, not the taught cause.

Caveats: standalone p/d table assumes EXT levels ACTIVE/TESTED (states not simulated) — the real-engine
study reproduced the silence mechanism, so the mechanism claim is engine-verified; direction cells are
replication-verified only. 1h bars are session-anchored (09:15..15:15, last bucket 15-min). n=5 marks,
one regime — recognition evidence, not an edge claim; both tweaks still owe the ab_tradebook gate.
