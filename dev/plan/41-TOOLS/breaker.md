# breaker

Validation of the `breaker` feature against **EVERY** hand-marked instance in
`runs/validate/tools/registry.jsonl` (feature == "breaker") — **14 instances**,
no sample. Three detectors emit this object, graded as one family:
`app/trader/detectors/breaker_msb.py` (EmreKb MSB-OB Pine port — the sweep-gated
breaker box, the +19.6pp 5m-hit ingredient), `ob_taught.py` (taught OB with a
`BRK` flip on deep-break-after-sweep), and `breaker.py` (LevelEngine INVERTED
level retest — the shipped `breaker`, a weaker −7% rule). Numeric checks run on
`data/long5m/HAVELLS.csv` (covers 2026-04-27..07-17 → the 6-9 Jul 2026 window is
fully in-window) and `data/yahoo/SBILIFE_1d.csv` (daily, 2017-2026).

Guardrail (RETHINK.md): **RECOGNITION (fires on the right candle) != EDGE.** The
already-measured record is NEGATIVE/flat for the LTF breaker retest
(`breaker_retest −8pp`), and that null tested a MIS-BUILT proxy (body-edge SL,
ATR stop). Nothing below claims profitability — this is a geometry/recognition
audit of the USER's drawn breaker only.

## Feature notes (structure & validity)

**The taught breaker (from the marks + the reference schematics).** An order
block that **fails**: price closes THROUGH a prior demand/supply OB (a Break of
Structure), invalidating it, and on the **retest from the new side** the old
demand flips to supply (bear breaker → short) or old supply flips to demand
(bull breaker → long). The distinguishing gate vs a plain mitigation block
(explicit in `c31_breaker_1`): a breaker requires an **opposing structure break**
("Break"); a mitigation block is retested WITHOUT taking the prior swing ("No
Break"). Reference `b8d2_c07/08/09` add: born at a former HL/LH OB, entry on the
breaker retest, **SL beyond the far/outer edge** (the schematic draws the SL box
*below* a bull breaker), target at the opposite liquidity.

**What `breaker_msb.py` targets** — the closest port of that geometry:
- Zigzag(`zz=9`) alternating swings over the full 5m continuum; a bar that is the
  min/max of the last `zz` bars flips the trend and confirms a swing.
- A **bearish MSB** fires when `market==1` and `l0 < l1 − |h0−l1|·fib`
  (`fib=0.33`); bullish mirrored. Gated to bar index ≥ `max(warm=25, 14)` and to
  BOTH extremes having changed since the last MSB.
- The **BREAKER box exists ONLY when the older swing was SWEPT** — bear: `h0>h1`
  (prior swing high taken = buy-side liquidity grab); bull: `l0<l1`. Otherwise
  the Pine draws a *mitigation* block, which this detector **deliberately does
  not emit** (`_msb`, lines 145-158). This IS the `c31` sweep-vs-no-break gate.
- Box = full range (`hi/lo`) of the last same-direction candle near the
  swing-high (bear) origin (`_origin`, strict candle color).
- **Entry** = first LATER close back inside the box (`_sweep_boxes`, once per
  box). **SL = the box far edge** (`b.top` for a short, `b.bot` for a long — the
  level whose close-through kills the box), plus `sl_floor = 0.15·ATR`.
- Defaults `{tf:5m, zz:9, fib:0.33, warm:25, sl_atr_floor:0.15}`; strength 0.8,
  ttl 4.

**What `ob_taught.py` targets** — the OB→BRK flip:
- A bodies-box OB (cluster of closes) is born at a continuation break with ≥1
  counter-candle. On a **deep break** (`≥0.5·ATR` close-through, `step_zone`)
  the box is KILLED and **FLIPS**: if the birth leg's running extreme took the
  prior same-side extreme (`meta["pex"]`, `swept` test in `step`) → `BRK`, else
  `MIT`. The flipped `BRK` zone (opposite dir, SAME box, parent grade) emits on
  the first armed retest from the other side. Entry = **edge**; **SL = far edge
  raw** (`z.lo`/`z.hi`), `sl_floor=0.15·ATR`; strength 0.7, ttl 6.

**What `breaker.py` targets** — the shipped level-inversion rule:
- Watches `OB_BULL/OB_BEAR/SWING_H/SWING_L/OPEN_RANGE_*` levels the LevelEngine
  has flagged `INVERTED`. Fires when the latest closed candle overlaps the zone
  AND its close is fully back on the new side. Direction = flip of
  `_SIDE_BY_KIND` (an `OB_BULL`/demand OB, side "above", inverted → close < lo →
  **SHORT** — matches a bear breaker). Strength 0.85, ttl 12. **Emits NO `sl`**
  and has **no explicit sweep/BOS gate** — birth is just the close-through
  inversion (the −7% weaker rule).

**Confluence.** The breaker rides on: a prior **liquidity sweep** (buy-/sell-side
grab, `b8d2_c09` dashed line above the zone), a **BOS/CHoCH** through the OB
(`b8d2_c07/08` "Break"/"OB Failed"), the parent **order_block**
(`t1d_order_block_2`, `T3a/b` invalidated-OB-to-breaker), and the **retest
mitigation** band (`t1d_mitigation_1` RETEST FOR ENTRY at 1221). All four sit in
the same registry cluster as these breaker marks.

## How the user draws it

A small horizontal box at the failed-OB level, then price is expected to retest
it and reject:
- **HAVELLS (t1c–t1h, 6 redraws of one mark).** Bear breaker box ~**1217–1224**
  at the 8 Jul 2026 top; "prior bull/demand OB broken then flips to supply on
  rejection." Companion marks give the mechanics: `t1d_order_block_2` = the entry
  supply OB (1219–1222.5), `t1d_mitigation_1` = "RETEST FOR ENTRY" band, **entry
  1221**, short.
- **SBILIFE (t31b).** Bull/**demand** breaker, box **HI 1845 – LO 1825**, inner
  line 1830, labeled "BB", long — "the breaker block = origin of the 18/09→24/09
  rally into the supply."
- **HDFCBANK (h4648/h4758).** Bear breaker, box **972.2–968.7** (user tooltip:
  **3.56pt / −0.37% / 34 bars**); "broken swing-high zone retested from below,"
  short to ~948. `h4758` explicitly labeled "BREAKER BLOCK."
- **References (c13, b8d2_c07/08/09, c31).** Textbook schematics defining the
  object (failed OB + opposing break + retest; breaker vs mitigation).

The user never annotates entry/SL numerically on the breaker box itself except
via the sibling OB/retest marks — entry ≈ box CE/edge (1221 on HAVELLS), SL
beyond the **outer wick**, target at far liquidity.

## Accuracy verdict

**pct_match = hit / (hit + partial + miss) = 6 / 7 = 85.7%.**
Counts over ALL 14 instances: **hit 6, partial 1, miss 0, uncheckable 7.**

| stock | instances | verdict | note |
|---|---|---|---|
| HAVELLS | t1c,t1d,t1e,t1f,t1g,t1h | **6 hit** | 5m tape; box within 0.5 ATR, birth confirmed |
| SBILIFE | t31b | **1 partial** | daily-only; structure confirmed, 30m geom uncheckable |
| HDFCBANK | h4648,h4758 | **2 uncheckable** | 2025-09 intraday tape absent |
| (reference) | c13,c07,c08,c09,c31 | **5 uncheckable** | schematics, no NSE tape |

**HAVELLS — full numeric reproduction (the 6 hits).** ATR(5m,14)@09-Jul 09:15 =
**4.88 pt**. The marks bracket the real 8-Jul 12:05–12:55 OB body
(**1219.4–1222.0**) within **0.02–0.49 ATR** (hi offsets 0.0–2.0pt, lo offsets
−2.4..+0.1pt). Birth is textbook and confirmed on tape:
- **Sweep**: prior swing high 1228.8 (7 Jul) → 8 Jul high **1234.0** = buy-side
  grab **+5.2pt** (satisfies breaker_msb `h0>h1`).
- **BOS-down**: the 1219.4 base broke — 13:55 close 1210.1, 14:00 close 1206.5 =
  **12.9pt** close-through (> 0.5·ATR = 2.44).
- **Retest**: 9 Jul 09:15 high **1223.0** back into the 1217–1224 box (close
  1220.8 inside), then rejected **−37.7pt to 1183.1** (13:05). Entry ~1221
  achievable.

So a breaker signal fires on the right candle, right zone (±0.5 ATR), right
direction (short), born after **sweep + BOS** (not mid-air) — recognition HIT.

**Structural + NUMERIC gaps (the doc35 residue, quantified on this trade):**
1. **SL object (gap#3).** `ob_taught` SL = body far edge **1222.0**, which sits
   **4.8pt (0.98 ATR)** inside the local top wick 1226.8 and **12.0pt (2.5 ATR)**
   inside the swing-high outer wick **1234.0**. The user's SL lives beyond the
   outer wick → the shipped body-edge SL would be **taken by the very retest
   wick** the user survives. `breaker_msb` far edge ≈ **1231** is only **3.0pt
   (0.6 ATR)** short of 1234 — much closer to the taught geometry.
2. **Box anchor.** `breaker_msb`'s box is a single swing-high-origin candle
   (~1226–1231), **higher** than the user's OB-body box (1219–1222); `ob_taught`
   and `breaker.py` anchor at the OB body (tight match). No one detector gives
   both the low box AND the outer-wick SL.
3. **Entry.** All three enter at box **edge / first-close-inside**, not an
   explicit **CE (50%)** — numerically ~1221 is reachable, but the rule is
   edge-not-CE.
4. **Birth gate coverage.** Only `breaker_msb` enforces the sweep gate
   (`h0>h1`); `breaker.py` fires on bare inversion (no sweep/BOS) → would also
   fire on the weaker mitigation case the user distinguishes (`c31`).

**SBILIFE t31b — partial.** Daily data confirms the mark's **birth, direction,
and price band**: 17/09/2024 low **1808.4** sweeps the 16/09 low 1816.1
(sell-side grab), 18/09 bullish reversal (O1818.2 H1848.9 C1842.4) = rally
origin, rally into 23–24/09 supply (H1925 / 1927.9) rejected. The box
**1825–1845** sits INSIDE the 18/09 origin candle 1815.1–1848.9. But it is a
**30m** mark on **daily-only** tape — the fine box hi/lo tolerance, CE entry, and
outer-wick SL cannot be verified and the breaker detectors cannot be run
sub-daily → partial.

**Data limits (why 7 are uncheckable).**
- **HDFCBANK h4648/h4758** — 2025-09 window: `long5m/HDFCBANK.csv` only covers
  2026-04-27+, and there is **no HDFCBANK Yahoo daily/1h** cached → zero candles
  for the mark. Only t31 SBILIFE has a firm year; HDFCBANK's is a mark-label
  guess (2025).
- **c13, b8d2_c07/08/09, c31** — foreign educational schematics (TradingFinder,
  ForexBee, blanet) with no symbol/tf/axis → no tape. They still validate the
  *definition* (esp. `c31`: breaker = OB flipped **after** an opposing break;
  `b8d2_c08`: SL box **below** the breaker = outer-edge stop).

No silent drops: every uncheckable is logged with its reason in
`runs/validate/tools/val_breaker.jsonl`.

## Enhancement plan

Prioritized; references exact params/functions. Goal = make ONE detector
reproduce the user's full breaker geometry (low OB-body box **AND** outer-wick
SL **AND** sweep+BOS gate). All changes gated behind A/B — the measured
`breaker_retest −8pp` was on the mis-built proxy, so re-measure with the
outer-wick SL before trusting any number.

**P1 — Structural: outer-wick SL on the breaker box (doc35 gap#3).** The single
largest gap: on the HAVELLS trade the shipped body-edge SL (1222) is hit by the
retest wick the user survives (1234). Change `ob_taught._evidence` and the
`BRK` flip so the emitted `sl` is the **outer wick** of the box's origin
candle(s), not `z.lo/z.hi` (body). Concretely: track the box's min-low / max-high
(wick) alongside the bodies box in `ObZones._cluster` and emit
`sl = wick_far_edge`. TARGET on this trade: SL ≈ **1234** (swing-high wick),
i.e. `≥ 1226.8` (local wick), not 1222 — a **4.8–12pt** correction. `breaker_msb`
already ships the far-edge SL (`b.top`); keep it, but widen from the origin
candle to the **swing-high wick** so it reaches 1234, not 1231.

**P2 — Structural: unify the box anchor to the OB body, keep the msb sweep
gate.** Neither detector alone is right. Best path: extend **`ob_taught`'s BRK**
(which already anchors the low OB-body box 1219–1222, the ±0.5-ATR match) with
`breaker_msb`'s **explicit sweep gate**. Today the BRK flip fires on `swept =
z.meta["ext"] > pex` — verify this fired BRK (not MIT) on the HAVELLS OB by
confirming the birth-leg extreme (~1227–1234) exceeded `pex`; if `pex` resolves
to the 1234 swing high the leg fails to exceed it → MIT mislabel. Fix: seed
`pex` from the **pre-sweep** swing (1228.8), so the 1234 sweep registers as
`swept=True → BRK`. This makes the OB-body box carry the breaker label instead of
falling back to `breaker_msb`'s higher single-candle box.

**P3 — Numeric threshold: CE (50%) entry option.** Add `entry_mode ∈
{edge, ce}` to `ob_taught`/`breaker_msb`. For `ce`, arm the retest at box
mid `(lo+hi)/2` (HAVELLS: (1219.4+1222.0)/2 = **1220.7 ≈ user 1221**) rather than
the edge. Keep edge as default for A/B; the user's marks (entry 1221 at mid) favor
CE. TARGET: entry within **0.2 ATR** of box mid.

**P4 — Birth-gate/confluence: require sweep+BOS on the shipped `breaker.py`.**
`breaker.py` currently fires on bare `INVERTED` with no sweep/BOS gate → it will
also fire the weak mitigation case (`c31` "No Break"). Add a precondition: the
inversion must be preceded by a liquidity sweep (a level whose extreme was taken
within N bars) — reuse the `inducement`/EXT sweep signal. This closes the
breaker-vs-mitigation gap the user explicitly draws and should recover part of
the `breaker.py` −7% vs `breaker_msb` +19.6pp spread.

**P5 — Confluence stack (measurement, not a filter yet).** Log alongside each
breaker: (a) sweep magnitude in ATR (HAVELLS +5.2pt = 1.07 ATR), (b) BOS depth in
ATR (12.9pt = 2.6 ATR), (c) parent-OB grade `pivot_dist_atr`, (d) resting
liquidity above/below (`b8d2_c09`). Then re-run the joint ex-ante test
(RETHINK §D) — the breaker's edge, if any, is expected only in the **sweep-gated
+ deep-BOS + outer-wick-SL** conjunction, never in the bare retest that measured
−8pp.

**Data to unblock the 7 uncheckables.** Cache HDFCBANK 2025-09 intraday (30m or
5m) to grade h4648/h4758 numerically; without it their box-tol/birth/SL stay
analytical-only. SBILIFE t31b needs 30m 2024-09 tape to lift partial→hit.
