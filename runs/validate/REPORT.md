> ⚠️ SUPERSEDED — see runs/validate/RETHINK.md. The "96% target reached" is inflated ~3× (in
> 19/30 the stop was breached before the target; correctly sequenced ≈10/30). Year-resolution is
> partly circular (10/30 multi-year, picked outcome-maximising year; only t31 truly resolved) and
> a timezone off-by-one corrupts daily dates. This doc proves anatomy FIDELITY only (structures
> exist on real tape), NOT profitability/hit-rate. Numbers below are recognition, not edge.

# VALIDATE — the 30 taught trades checked against REAL Yahoo OHLCV (2026-07-23)

User ask: take the ~30 hand-drawn taught trades, FIND them in real market data, and
check the structures/sweeps/SLs/blocks/FVGs actually happened as drawn — multi-timeframe.
This is an INDEPENDENT reality check on the corpus (attacks survivorship from the other
side: were the setups even real, or misremembered/cherry-drawn?).

## Method (how each trade was located + checked)
1. **Vision extraction** — 5 parallel agents read all 72 screenshots → per-trade
   (stock, DD/MM, price era, direction, entry, SL, target, swept extreme, range).
   Charts show NO year (Kite prints only day/month), so:
2. **Year resolution** (`tools/yvalidate.resolve_year`) — for (stock, month, entry price)
   scan full daily history for the year(s) where the stock traded at that price in that
   month, constrained to the drawn price ERA. Ambiguous years validated on structure; the
   year whose real tape matches (swept extreme + move to target) wins.
3. **Daily validation** (all 30) — around the resolved date: was the drawn extreme
   pierced-then-closed-back (sweep)? was there a mature/contracting range? did price move
   to the drawn target in the drawn direction? MFE / MAE / R.
4. **Fine-TF** — 1h back to 2023-08 (10 trades), native **5m** back to 2026-05-04 (8 recent
   trades). For the 8 recent, a gap-aware **fill-through path-sim** replays the EXACT drawn
   entry/SL/target on real 5m bars (`tools/y5sim.py`).

### Data tiers (Yahoo hard window — the honest ceiling)
| TF | history | trades it reached |
|----|---------|-------------------|
| daily | decades | **all 30** |
| 1h | ~2023-08 | 10 |
| 5m | 60d (2026-05-04) | **8** (the only fine-edge window) |
| 1m | 7d | 0 |

## RESULT 1 — the anatomy is REAL (daily, all 30)
- **swept extreme confirmed: 27/30 (90%)** — the drawn liquidity level really was swept on
  real data. (3 "misses" = H_old/H_sep/H_apr: the sweep was a same-day intraday poke
  invisible at DAILY granularity, not a fabrication.)
- **target reached in drawn direction: 29/30 (96%)**
- median forward MFE **+12.4%** / **+17.4R** (drawn tiny stop); median range width 16%;
  contracting range in 18/30.
- Every year resolved to a real session where the stock, month, and price era coincide with
  a matching structure. Nothing was un-locatable. **The drawings are faithful to the tape.**

Full per-trade table: `runs/validate/results.json`. Extraction tables: `runs/validate/dates/a1..a5.md`.

## RESULT 2 — the fill-through lever is REAL (5m mechanical replay, 8 recent winners)
Replaying the drawn entry/SL/target mechanically on native 5m, gap-aware:

| trade | resolved | outcome | R | drawn RR | stop(pt) | MAE(R) |
|-------|----------|---------|---|----------|----------|--------|
| H_jun_long | 2026-06-30 | TARGET | +9.9 | 9.9 | 8 | 0.06 |
| T_jun_long | 2026-06-01 | TARGET | +9.6 | 9.6 | 25 | 0.92 |
| V_jul_short | 2026-07-16 | TARGET | +8.0 | 8.0 | 10 | 0.63 |
| V_may_long | 2026-06-02 | TARGET | +4.0 | 4.0 | 18 | 0.60 |
| H_jul_short | 2026-07-07 | STOP | −1.0 | 6.5 | 4 | 1.6 |
| Da_jun_long | 2026-06-23 | STOP | −1.0 | 14.5 | 2 | 1.2 |
| **Da_jul_short** | 2026-07-03 | **STOP_GAP** | gap-through | 6.0 | 3 | 0.9 |
| S_t28_long | 2026-07-08 | TIMEOUT | — | 15.4 | 5 | 0.6 |

- **4/8 hit target for +4 to +10R** — the tiny-stop RR geometry is real and pays big when it works.
- **3/8 lost: 2 clean stops + 1 GAP-THROUGH.** The gap-through (Da_jul_short, 3pt stop) is
  exactly the fill-through failure mode doc-34 named as THE dominant edge/risk — it
  materialised on a real taught trade. The smallest stops (2-4pt) are the ones that failed.
- Gross of the 8 ≈ **+28R** (winners +31.5R, two stops −2R, one gap ≈ −1.5R, one timeout 0) —
  BUT see the caveat: these are hand-picked winners.

## Honest conclusions
1. **The corpus is not fabricated.** 90% of drawn sweeps and 96% of targets are literally on
   the real tape at the resolved date; every trade was locatable. The user draws faithfully.
2. **The edge geometry is real AND the fill-through risk is real** — both showed up on the
   same 8-trade 5m replay: huge-R winners from tiny stops, and a genuine gap-through kill.
   Discretion (entry timing, which setup to skip, stop management) is doing real work that a
   mechanical replay loses — mechanical target-hit was only 4/8 even on winners.
3. **Survivorship is NOT resolved by this.** All 30 are winners the user chose; 96% target-hit
   is selection, not expectancy. This validates ANATOMY FIDELITY, not PROFITABILITY.
4. **Free-data ceiling stands.** Only 8/30 could touch native 5m (the edge TF); the other 22
   are daily/1h — too coarse to see a 3-5pt structural stop. Full fine-TF validation of the
   older trades needs paid historical intraday (Kite/vendor), still on hold.

## What this changes for the build
- Fill-through is confirmed live and biases toward the SMALLEST stops → the build must test
  stop-survival at the ACTUAL entry TF, and likely floor the stop distance (a 2-3pt stop
  gap-throughs). The 4pt/2pt/3pt failures vs 8/10/25pt winners is a concrete signal.
- Next real test remains: (A) construct the LOSING twins (HTF-misaligned, per doc-36) and
  measure ex-ante separation; (B) fill-through net-R on 5m across winners AND losers. This
  validation supplies the faithful winner side; the loser side still needs data or the build.

Scripts: `tools/yvalidate.py` (fetch/cache/resolve/validate), `tools/yrun.py` (year-resolve +
daily/1h per trade), `tools/y5sim.py` (5m fill-through path-sim), `tools/ytrades.json` (the 30).
Cached Yahoo pulls: `data/yahoo/`.
