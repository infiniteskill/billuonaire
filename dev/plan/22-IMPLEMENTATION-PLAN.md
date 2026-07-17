# Implementation Plan — per aspect: source, code status, build (2026-07-17)

For each aspect: the BEST implementation (measured), whether reference code is PROVIDED
(adapt) or MISSING (I build own / you source), and the build approach. Final keep/drop per
aspect is gated by the comprehensive dry-run (5 agents running) + the economic replay.

## Legend
Source: **LUX**=adapt LuxAlgo, **REF**=other provided ref, **OURS**=our code, **BUILD**=I build own, **DATA**=needs Kite/options.
Code: ✅ provided in dev/h2h · ⚙️ I build (SMC logic, not proprietary) · ⛔ needs external data · ❓ better ref would help (you could source).

## Per-aspect table
| Aspect | Best (measured) | Source | Code | Build approach |
|---|---|---|---|---|
| **Order Block** | LuxAlgo vol-adj leg-extreme +10–14% | LUX | ✅ pinescripts.txt | Adapt: parsed H/L swap on ≥2×ATR spike bars; OB = extreme candle of impulse leg; SD-zone (3.txt) as M5/M10 alt |
| **FVG** | LuxAlgo dedicated close-beyond +12% | LUX | ✅ (you pasted it) | 3-bar gap + displacement CLOSE-beyond + auto mean-range% threshold |
| **iFVG (inversion)** | pending (our code dead-path) | BUILD | ⚙️ | Correct inversion: gap filled→trades back→rejects other side |
| **Consequent Encroachment** | = FVG mid (our CE-hold +8.8%) | OURS | ✅ | CE-hold entry event on the FVG |
| **CHoCH / BOS** | DIRECTION ONLY (−18% as entry) | OURS+LUX | ✅ | Keep for bias; LuxAlgo/inducement CHoCH for HTF direction |
| **Breaker block** | seek-destroy harvest (ours −8% is wrong) | BUILD | ⚙️ | Failed-break + reclaim + volume burst = harvest entry |
| **Compression + PO3** | compression-FADE +0.33R; combo pending | BUILD | ⚙️ (no ref) | Our concept: coil→sweep→expansion; fade the break |
| **Liquidity sweep / IDM** | LuxAlgo Inducements&Sweeps +14–20% | LUX | ✅ 2.txt | Adapt: HTF CHoCH (len~20) dir + LTF inducement grab entry |
| **Wyckoff accu/dist** | ours retuned +23% | OURS | ❓ better Wyckoff ref welcome | Retuned 30/4.0/1.25 + bar guards; no clean Pine ref exists |
| **Liquidity pools** | INVERTED (fresh>obvious) | BUILD | ⚙️ (ref concept inverted) | SL-cluster fatness map, strength SIGN-FLIPPED |
| **Premium / Discount** | LuxAlgo SMC +3.3% (filter) | LUX | ✅ pinescripts.txt | Range top-5%/bottom-5% as a position filter |
| **Multi-TF** | M10 primary, 2m entry, HTF dir | BUILD | ⚙️ | Config-driven decision/direction TFs |
| **HTF check** | leak-free (re-measuring) | BUILD | ⚙️ | Last fully-closed HTF bar bias (no look-ahead) |
| **Mitigation block** | pending | BUILD | ⚙️ | ICT def; test then decide |
| **Rejection/vacuum block** | pending | BUILD | ⚙️ | Large-wick rejection at level |
| **Confluence decision tree** | our engine, re-weighted | OURS | ⚙️ | Spatial confluence, weights = measured edge; density-validated |
| **Relative strength / SMT** | pending (selection agent) | BUILD | ❓ RS/SMT Pine welcome | Stock vs NIFTY; divergence |
| **Weekly/monthly range** | pending | BUILD | ⚙️ | Break-&-return of HTF range as macro bias |
| **Cleanliness / fit** | ours (scanner) | OURS | ✅ | Stock-selection gate |
| **Option expiry / OI / cage** | needs data | DATA | ⛔ Kite | Thursday sizing now; OI-cage in Phase 6 |
| **Kill zones / time** | ours (timestats, flatten) | OURS | ✅ | Time filter, corrected priors |

## What's MISSING — you provide OR I build own
- **⛔ Needs data you'd buy (Kite):** option-chain/OI (cage, max-pain, expiry-decay). Nothing to code until the API is purchased.
- **❓ A good reference Pine would help (you could source, else I build own):** Wyckoff accumulation/distribution schematic; Relative-Strength (RS rating) vs index; SMT-divergence indicator. I can build all three myself (not proprietary) — a reference just speeds/validates them.
- **⚙️ I build own (standard SMC logic, no ref needed):** iFVG, seek-destroy harvest/breaker, compression+PO3, SL-cluster fatness map, weekly-range, mitigation/rejection blocks, HTF-bias, confluence engine, multi-TF config.
- **✅ Adapt from provided LuxAlgo/refs:** OB, FVG, premium/discount, inducement/sweep, MSS, SD-zone, liquidity-pool concept.

So: **most of it I build myself from the measured winners; only options/OI truly needs your Kite purchase, and Wyckoff/RS/SMT are the three where a good Pine from you would help but aren't blockers.**

## Build sequence (deep work)
1. **Plug-n-play core** (per your portability ask): a pure engine library — models, feed ABC, detector plugin ABC, confluence engine, decision, risk, broker ABC, journal — no I/O in the core. Adapters (feed/broker/UI/alerts) plug around it. This is the foundation everything else slots into.
2. **v2 aspects** (only the ones that clear the dry-run): adapt LUX (OB/FVG/premium-discount/inducement) + build (harvest/compression-PO3/iFVG/SL-cluster/HTF-bias). Each a detachable plugin emitting Evidence.
3. **Confluence decision engine** — re-weight by measured edge, validated by the density test.
4. **Selection/scanner layer** — the aspects that survive (RS/SMT/cleanliness/weekly-range) rank the universe (Stage-1 homework).
5. **Autopilot** — scheduler, dashboard, alerts, control contract (`19`), kill-switch, persistence.
6. **Economic replay gate** — v2 vs baseline on holdout stocks; ship only if it earns; forward month.
7. **Phase 6 (Kite)** — live feed/broker adapters + options/OI cage.

## Gate
Nothing ships until: (a) the aspect cleared the dry-run (edge/RR + holdout), (b) it's in the
confluence engine with a measured weight, (c) the whole v2 beats the baseline economically.
