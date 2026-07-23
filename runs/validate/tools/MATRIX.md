# COVERAGE MATRIX — taught-feature catalog (registry.jsonl)

Generated from 10 `cat_*.jsonl` batches → merged, exact-deduped → `467` distinct marks across `139` charts, `16` feature types, `16` symbols.

> **GUARDRAIL (RETHINK.md):** every count below is a *RECOGNITION* tally — the mark was drawn and the structure is present on the chart. It is **NOT** an edge or profitability claim ("fires on the right candle" != profitable). Native 5m tape exists only <60d (Yahoo since 2026-05-04 + `data/long5m`); older trades are daily/1h only, so their tiny structural OUTER-WICK stop is **unverifiable** on the available tape. Only **SBILIFE t31 (2024)** has a truly firm year. Every other NSE-trade year is either a **price-era guess** via results.json (`era-approx`; RETHINK warns this resolution can be circular / selection-on-outcome) or taken from the **mark's own written label** with the exact date left approximate (`label-year`, HTF/multi-month context). Dev (HDFCBANK/HEROMOTOCO), forex, crypto and reference graphics have **no ytrades/results source** and are left unresolved by design. No mark was dropped — all 467 are retained and tagged.

- rows merged (raw): **467**  |  exact duplicates removed: **0**  |  distinct marks kept: **467**
- distinct chart paths: **139**
- resolution status: **era-approx** 211, **reference** 108, **label-year** 61, **dev-unvalidated** 47, **foreign** 29, **firm** 11
  - `firm` = year certain (only SBILIFE t31 = 2024). `era-approx` = year is a **price-era guess** via results.json (RETHINK flags this as possibly circular/selection-on-outcome). `label-year` = year taken from the mark's OWN written label, exact date approximate (HTF/multi-month context, no single ytrades leg). `dev-unvalidated` = HDFCBANK/HEROMOTOCO dev charts (year is the mark's label, not in ytrades). `foreign` = FX/crypto/US reference. `reference` = educational graphic, no symbol/tf/axis.

## 1. Stock × feature instance-counts

| stock | breaker | compression | extreme_swing | fvg | htf_ltf_nesting | ifvg | liquidity_pool | mitigation | order_block | premium_discount | propulsion | spring_utad | structure_bos_choch | sweep | volume_time | wyckoff_phase | **TOTAL** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **HAVELLS** | 6 | · | 18 | 4 | · | · | 25 | 10 | 55 | 1 | · | · | 28 | 10 | 2 | · | **159** |
| **SBICARD** | · | · | · | 8 | 8 | 2 | · | · | 23 | · | 6 | · | 3 | · | · | · | **50** |
| **SBILIFE** | 1 | · | 1 | · | · | · | 4 | · | 4 | 3 | 2 | · | 4 | 1 | · | 2 | **22** |
| **DABUR** | · | · | 2 | 2 | · | · | 1 | · | 5 | · | 1 | · | 3 | 3 | · | · | **17** |
| **DLF** | · | · | · | 1 | · | · | 3 | 2 | 10 | · | · | · | 1 | · | · | · | **17** |
| **VOLTAS** | · | · | · | · | · | · | 2 | · | 5 | · | · | · | · | 3 | · | · | **10** |
| **TITAN** | · | · | · | · | · | · | · | 1 | 3 | · | · | · | 2 | 2 | · | · | **8** |
| **HEROMOTOCO** | · | · | 16 | 3 | · | 1 | · | · | 10 | · | · | · | · | · | · | · | **30** |
| **HDFCBANK** | 2 | 2 | · | 4 | · | · | · | · | 8 | · | 1 | · | · | · | · | · | **17** |
| **EURUSD** | · | · | 3 | · | · | · | 2 | · | 2 | · | 1 | · | 2 | · | · | · | **10** |
| **GBPUSD** | · | · | · | · | · | · | 2 | · | 2 | · | · | · | · | · | · | · | **4** |
| **BTC** | · | · | · | 2 | · | · | 4 | · | · | · | · | · | · | · | · | · | **6** |
| **BTCUSD** | · | · | · | 1 | · | · | 2 | · | · | · | 1 | · | · | · | · | · | **4** |
| **XAUUSD** | · | · | 2 | · | · | · | 2 | · | · | · | · | · | · | · | · | · | **4** |
| **TSLA** | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 1 | **1** |
| **(none/reference)** | 5 | · | 26 | 7 | 1 | · | 11 | 3 | 18 | 4 | 3 | 1 | 18 | 1 | 1 | 9 | **108** |
| **TOTAL** | **14** | **2** | **68** | **32** | **9** | **3** | **58** | **16** | **145** | **8** | **15** | **1** | **61** | **20** | **3** | **12** | **467** |

## 2. Per-feature totals (feature vocabulary)

| feature | instances | charts w/ feature | doc35 note |
|---|---|---|---|
| `breaker` | 14 | 14 | flipped OB after break — supply/demand inversion |
| `compression` | 2 | 2 | BOX_ON_LEVEL measured NEGATIVE (-2.3pp) |
| `extreme_swing` | 68 | 30 | the taught liquidity anchor (EXT), source of the sweep |
| `fvg` | 32 | 25 | FVG-as-target / CE entry is not the edge |
| `htf_ltf_nesting` | 9 | 9 | HTF-align DEPTH×maturity = the one still-open joint gate (doc36) |
| `ifvg` | 3 | 3 | inverse FVG — flip of an unmitigated gap |
| `liquidity_pool` | 58 | 41 | must come from EXT extremes, not fractal furniture |
| `mitigation` | 16 | 16 | return-to-zone; CE entry not edge |
| `order_block` | 145 | 97 | OUTER-WICK box vs INNER-BODY block — shipped detector emits body-edge only |
| `premium_discount` | 8 | 7 | fragile 40-bar window; 5 trades violate own rule |
| `propulsion` | 15 | 14 | parent-linked continuation block |
| `spring_utad` | 1 | 1 | SPRING n=8 (+38pp thin); UPTHRUST mirror NEGATIVE -9.2pp |
| `structure_bos_choch` | 61 | 43 | BOS/CHOCH measured fwd-negative (recognition only) |
| `sweep` | 20 | 20 | born only AFTER sweep+BOS, not mid-air |
| `volume_time` | 3 | 3 | VSA +5.3pp but sub-toll; time-of-day clusters collide w/ no-session rule |
| `wyckoff_phase` | 12 | 10 | PHASE +4.6pp sub-toll; schematic references, not tape |
| **TOTAL** | **467** | **139** | |

## 3. Per-stock resolution & data availability

| stock | marks | charts | resolve_status (counts) | data_avail | notes |
|---|---|---|---|---|---|
| **HAVELLS** | 159 | 39 | era-approx:144, label-year:15 | daily-only (pre intraday cache) | 17 trades; 2026 legs 5m, 2022-25 1h, pre-2023-08 daily-only |
| **SBICARD** | 50 | 19 | label-year:36, era-approx:14 | 1h (Yahoo intraday back ~2024-07) | yahoo 5m only (NOT in long5m); recent legs 5m, older daily/1h |
| **SBILIFE** | 22 | 4 | firm:11, label-year:10, era-approx:1 | daily-only (pre intraday cache) | ONLY firm year (t31=2024); daily-only, no cached intraday |
| **DABUR** | 17 | 4 | era-approx:17 | 5m-native (<60d: Yahoo since 2026-05-04 + long5m) | 2026 legs 5m; Feb/Nov 1h; some daily-only |
| **DLF** | 17 | 7 | era-approx:17 | 1h (Yahoo intraday, back ~2024-07) | 2025 legs 1h; 2022 daily-only |
| **VOLTAS** | 10 | 5 | era-approx:10 | 5m-native (<60d: Yahoo since 2026-05-04 + long5m) | 2026 legs 5m native |
| **TITAN** | 8 | 3 | era-approx:8 | 1h (Yahoo intraday, back ~2024-07) | 2026 long 5m; 2025 short 1h |
| **HEROMOTOCO** | 30 | 9 | dev-unvalidated:30 | 5m (long5m symbol present; only <60d covered, older dates daily/1h via Yahoo) | DEV chart — not a user trade; long5m symbol present |
| **HDFCBANK** | 17 | 11 | dev-unvalidated:17 | 5m (long5m symbol present; only <60d covered, older dates daily/1h via Yahoo) | DEV chart — not a user trade; long5m symbol present |
| **EURUSD** | 10 | 2 | foreign:10 | n/a (foreign/reference — no NSE tape) | foreign FX reference |
| **GBPUSD** | 4 | 1 | foreign:4 | n/a (foreign/reference — no NSE tape) | foreign FX reference |
| **BTC** | 6 | 1 | foreign:6 | n/a (foreign/reference — no NSE tape) | crypto reference |
| **BTCUSD** | 4 | 1 | foreign:4 | n/a (foreign/reference — no NSE tape) | crypto reference |
| **XAUUSD** | 4 | 1 | foreign:4 | n/a (foreign/reference — no NSE tape) | gold FX reference |
| **TSLA** | 1 | 1 | foreign:1 | n/a (foreign/reference — no NSE tape) | US equity reference (Wyckoff) |
| **(none/reference)** | 108 | 31 | reference:108 | n/a (foreign/reference — no NSE tape) | educational graphics — no symbol/tf/axis |

## 4. Chart × feature present(●)/absent(·) list

One row per distinct chart (139). ● = ≥1 mark of that feature on the chart. Short feature codes: `brea`=breaker, `comp`=compression, `extr`=extreme_swing, `fvg`=fvg, `htf_`=htf_ltf_nesting, `ifvg`=ifvg, `liqu`=liquidity_pool, `miti`=mitigation, `orde`=order_block, `prem`=premium_discount, `prop`=propulsion, `spri`=spring_utad, `stru`=structure_bos_choch, `swee`=sweep, `volu`=volume_time, `wyck`=wyckoff_phase

| chart (basename) | stock | brea | comp | extr | fvg | htf_ | ifvg | liqu | miti | orde | prem | prop | spri | stru | swee | volu | wyck | n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Screenshot from 2026-07-22 09-39-34.png | HAVELLS | · | · | · | · | · | · | · | · | ● | · | · | · | ● | ● | · | · | 3 |
| Screenshot from 2026-07-22 09-42-03.png | HAVELLS | · | · | · | · | · | · | · | · | ● | · | · | · | ● | · | · | · | 3 |
| Screenshot from 2026-07-22 09-42-12.png | HAVELLS | · | · | · | · | · | · | · | · | ● | · | · | · | ● | ● | · | · | 4 |
| Screenshot from 2026-07-22 09-53-27.png | HAVELLS | · | · | · | · | · | · | ● | · | ● | · | · | · | ● | ● | · | · | 5 |
| Screenshot from 2026-07-22 09-53-33.png | HAVELLS | · | · | · | · | · | · | ● | · | ● | · | · | · | ● | ● | · | · | 6 |
| Screenshot from 2026-07-22 09-57-51.png | HAVELLS | · | · | · | · | · | · | ● | · | ● | · | · | · | ● | ● | · | · | 4 |
| Screenshot from 2026-07-22 09-58-10.png | HAVELLS | · | · | · | · | · | · | ● | · | ● | · | · | · | ● | ● | · | · | 4 |
| Screenshot from 2026-07-22 10-08-01.png | HAVELLS | · | · | ● | · | · | · | ● | · | ● | · | · | · | ● | ● | · | · | 8 |
| Screenshot from 2026-07-22 10-08-08.png | HAVELLS | · | · | ● | · | · | · | ● | · | ● | · | · | · | ● | ● | · | · | 7 |
| Screenshot from 2026-07-22 10-08-13.png | HAVELLS | · | · | ● | · | · | · | ● | · | ● | · | · | · | ● | ● | · | · | 7 |
| Screenshot from 2026-07-22 10-11-12.png | HAVELLS | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | · | · | 3 |
| Screenshot from 2026-07-22 10-17-32.png | HAVELLS | · | · | ● | · | · | · | ● | ● | · | · | · | · | · | · | · | · | 3 |
| Screenshot from 2026-07-22 10-17-42.png | HAVELLS | · | · | ● | · | · | · | ● | ● | · | · | · | · | · | · | · | · | 3 |
| Screenshot from 2026-07-22 10-20-21.png | HAVELLS | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-22 10-21-03.png | HAVELLS | · | · | · | · | · | · | ● | · | ● | · | · | · | ● | · | · | · | 4 |
| Screenshot from 2026-07-22 10-24-08.png | HAVELLS | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-22 10-24-15.png | HAVELLS | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-22 08-42-37.png | HAVELLS | · | · | ● | ● | · | · | · | ● | ● | · | · | · | · | · | · | · | 4 |
| Screenshot from 2026-07-22 08-54-55.png | HAVELLS | · | · | ● | · | · | · | · | · | ● | ● | · | · | ● | · | · | · | 6 |
| Screenshot from 2026-07-22 08-55-11.png | HAVELLS | · | · | ● | · | · | · | ● | · | ● | · | · | · | ● | · | · | · | 6 |
| Screenshot from 2026-07-22 09-01-28.png | HAVELLS | · | · | · | ● | · | · | · | ● | · | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-22 09-02-27.png | HAVELLS | · | · | ● | ● | · | · | · | ● | · | · | · | · | · | · | · | · | 3 |
| Screenshot from 2026-07-22 09-08-23.png | HAVELLS | · | · | · | · | · | · | · | · | ● | · | · | · | ● | ● | · | · | 3 |
| Screenshot from 2026-07-22 09-12-34.png | HAVELLS | · | · | · | · | · | · | · | · | ● | · | · | · | ● | · | · | · | 5 |
| Screenshot from 2026-07-22 09-12-39.png | HAVELLS | · | · | · | · | · | · | · | · | ● | · | · | · | ● | · | · | · | 5 |
| Screenshot from 2026-07-22 09-20-11.png | HAVELLS | · | · | ● | · | · | · | · | · | ● | · | · | · | · | · | · | · | 3 |
| Screenshot from 2026-07-22 09-23-31.png | HAVELLS | · | · | ● | · | · | · | · | · | ● | · | · | · | · | · | · | · | 3 |
| Screenshot from 2026-07-22 09-23-54.png | HAVELLS | · | · | ● | · | · | · | · | · | ● | · | · | · | · | · | · | · | 4 |
| Screenshot from 2026-07-22 09-34-29.png | HAVELLS | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-22 09-34-32.png | HAVELLS | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | ● | · | 3 |
| Screenshot from 2026-07-22 09-34-36.png | HAVELLS | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | ● | · | 3 |
| Screenshot from 2026-07-22 08-13-01.png | HAVELLS | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-22 08-15-53.png | HAVELLS | · | · | · | ● | · | · | · | · | · | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-22 08-16-48.png | HAVELLS | ● | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-22 08-23-15.png | HAVELLS | ● | · | ● | · | · | · | ● | ● | ● | · | · | · | ● | · | · | · | 7 |
| Screenshot from 2026-07-22 08-24-08.png | HAVELLS | ● | · | · | · | · | · | ● | ● | ● | · | · | · | ● | · | · | · | 6 |
| Screenshot from 2026-07-22 08-24-47.png | HAVELLS | ● | · | ● | · | · | · | ● | ● | ● | · | · | · | ● | · | · | · | 7 |
| Screenshot from 2026-07-22 08-24-55.png | HAVELLS | ● | · | ● | · | · | · | ● | ● | ● | · | · | · | ● | · | · | · | 7 |
| Screenshot from 2026-07-22 08-29-34.png | HAVELLS | ● | · | ● | · | · | · | ● | ● | ● | · | · | · | ● | · | · | · | 7 |
| Screenshot from 2026-07-23 17-25-13.png | SBICARD | · | · | · | · | ● | · | · | · | · | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-23 17-27-21.png | SBICARD | · | · | · | ● | ● | · | · | · | ● | · | · | · | · | · | · | · | 3 |
| Screenshot from 2026-07-23 17-28-05.png | SBICARD | · | · | · | ● | · | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-23 17-32-06.png | SBICARD | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-23 17-32-11.png | SBICARD | · | · | · | · | ● | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-23 17-32-14.png | SBICARD | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-23 17-32-18.png | SBICARD | · | · | · | · | ● | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-23 17-32-31.png | SBICARD | · | · | · | · | ● | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-23 17-32-40.png | SBICARD | · | · | · | · | ● | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-23 17-32-45.png | SBICARD | · | · | · | ● | ● | · | · | · | ● | · | · | · | · | · | · | · | 4 |
| Screenshot from 2026-07-23 17-35-56.png | SBICARD | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-23 17-36-50.png | SBICARD | · | · | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | 3 |
| Screenshot from 2026-07-23 17-37-00.png | SBICARD | · | · | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | 3 |
| Screenshot from 2026-07-23 17-37-17.png | SBICARD | · | · | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | 3 |
| Screenshot from 2026-07-23 17-38-01.png | SBICARD | · | · | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | 4 |
| Screenshot from 2026-07-23 17-39-05.png | SBICARD | · | · | · | · | ● | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-23 17-44-28.png | SBICARD | · | · | · | ● | · | · | · | · | · | · | · | · | ● | · | · | · | 2 |
| Screenshot from 2026-07-23 17-46-42.png | SBICARD | · | · | · | ● | · | ● | · | · | ● | · | ● | · | ● | · | · | · | 7 |
| Screenshot from 2026-07-23 17-47-09.png | SBICARD | · | · | · | ● | · | ● | · | · | ● | · | ● | · | · | · | · | · | 5 |
| Screenshot from 2026-07-23 20-29-11.png | SBILIFE | · | · | ● | · | · | · | ● | · | ● | ● | · | · | ● | · | · | · | 7 |
| Screenshot from 2026-07-23 20-32-21.png | SBILIFE | · | · | · | · | · | · | · | · | · | ● | · | · | ● | · | · | ● | 5 |
| Screenshot from 2026-07-23 20-10-01.png | SBILIFE | · | · | · | · | · | · | ● | · | ● | · | · | · | ● | · | · | · | 3 |
| Screenshot from 2026-07-23 20-12-23.png | SBILIFE | ● | · | · | · | · | · | ● | · | ● | · | ● | · | ● | ● | · | · | 7 |
| Screenshot from 2026-07-22 11-16-15.png | DABUR | · | · | · | · | · | · | · | · | ● | · | · | · | ● | ● | · | · | 4 |
| Screenshot from 2026-07-22 11-21-57.png | DABUR | · | · | · | · | · | · | ● | · | ● | · | ● | · | ● | ● | · | · | 5 |
| Screenshot from 2026-07-22 11-33-07.png | DABUR | · | · | ● | ● | · | · | · | · | · | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-22 12-18-31.png | DABUR | · | · | ● | ● | · | · | · | · | ● | · | · | · | · | ● | · | · | 6 |
| Screenshot from 2026-07-22 10-40-23.png | DLF | · | · | · | ● | · | · | ● | · | ● | · | · | · | ● | · | · | · | 4 |
| Screenshot from 2026-07-22 10-43-16.png | DLF | · | · | · | · | · | · | ● | ● | ● | · | · | · | · | · | · | · | 4 |
| Screenshot from 2026-07-22 10-43-28.png | DLF | · | · | · | · | · | · | ● | ● | ● | · | · | · | · | · | · | · | 4 |
| Screenshot from 2026-07-22 10-59-41.png | DLF | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-22 11-00-03.png | DLF | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-22 11-00-31.png | DLF | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-22 11-00-34.png | DLF | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-22 10-29-29.png | VOLTAS | · | · | · | · | · | · | · | · | ● | · | · | · | · | ● | · | · | 2 |
| Screenshot from 2026-07-22 10-29-39.png | VOLTAS | · | · | · | · | · | · | · | · | ● | · | · | · | · | ● | · | · | 2 |
| Screenshot from 2026-07-22 10-29-48.png | VOLTAS | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-22 10-30-05.png | VOLTAS | · | · | · | · | · | · | · | · | ● | · | · | · | · | ● | · | · | 2 |
| Screenshot from 2026-07-22 10-31-55.png | VOLTAS | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | · | · | 3 |
| Screenshot from 2026-07-22 11-04-57.png | TITAN | · | · | · | · | · | · | · | ● | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-22 11-09-13.png | TITAN | · | · | · | · | · | · | · | · | ● | · | · | · | ● | ● | · | · | 3 |
| Screenshot from 2026-07-22 11-10-04.png | TITAN | · | · | · | · | · | · | · | · | ● | · | · | · | ● | ● | · | · | 3 |
| Screenshot from 2026-07-19 20-14-04.png | HEROMOTOCO | · | · | ● | · | · | · | · | · | · | · | · | · | · | · | · | · | 8 |
| Screenshot from 2026-07-19 20-15-07.png | HEROMOTOCO | · | · | ● | · | · | · | · | · | · | · | · | · | · | · | · | · | 8 |
| Screenshot from 2026-07-19 20-19-25.png | HEROMOTOCO | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-19 20-22-12.png | HEROMOTOCO | · | · | · | · | · | ● | · | · | ● | · | · | · | · | · | · | · | 4 |
| Screenshot from 2026-07-19 20-24-50.png | HEROMOTOCO | · | · | · | ● | · | · | · | · | ● | · | · | · | · | · | · | · | 3 |
| Screenshot from 2026-07-19 20-28-57.png | HEROMOTOCO | · | · | · | ● | · | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-19 20-29-43.png | HEROMOTOCO | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-19 20-30-01.png | HEROMOTOCO | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-19 20-30-16.png | HEROMOTOCO | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-19 21-41-43.png | HDFCBANK | · | · | · | ● | · | · | · | · | · | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-19 21-41-47.png | HDFCBANK | · | · | · | ● | · | · | · | · | · | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-19 21-42-42.png | HDFCBANK | · | ● | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-19 21-42-56.png | HDFCBANK | · | ● | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-19 21-43-15.png | HDFCBANK | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-19 21-44-25.png | HDFCBANK | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-19 21-44-40.png | HDFCBANK | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-19 21-45-37.png | HDFCBANK | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-19 21-46-21.png | HDFCBANK | · | · | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | 3 |
| Screenshot from 2026-07-19 21-46-48.png | HDFCBANK | ● | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-19 21-47-58.png | HDFCBANK | ● | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-19 20-40-14.png | EURUSD | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | · | · | 4 |
| Screenshot from 2026-07-19 20-49-40.png | EURUSD | · | · | ● | · | · | · | · | · | · | · | ● | · | ● | · | · | · | 6 |
| Screenshot from 2026-07-19 20-42-09.png | GBPUSD | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | · | · | 4 |
| Screenshot from 2026-07-19 20-44-30.png | BTC | · | · | · | ● | · | · | ● | · | · | · | · | · | · | · | · | · | 6 |
| Screenshot from 2026-07-19 20-44-08.png | BTCUSD | · | · | · | ● | · | · | ● | · | · | · | ● | · | · | · | · | · | 4 |
| Screenshot from 2026-07-19 20-48-31.png | XAUUSD | · | · | ● | · | · | · | ● | · | · | · | · | · | · | · | · | · | 4 |
| Screenshot from 2026-07-23 20-34-21.png | TSLA | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ● | 1 |
| Screenshot from 2026-07-23 20-33-24.png | (none/reference) | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ● | 1 |
| Screenshot from 2026-07-23 20-33-41.png | (none/reference) | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ● | 1 |
| Screenshot from 2026-07-23 20-33-58.png | (none/reference) | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ● | 1 |
| Screenshot from 2026-07-23 20-34-26.png | (none/reference) | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ● | 1 |
| Screenshot from 2026-07-23 20-35-06.png | (none/reference) | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ● | 1 |
| Screenshot from 2026-07-19 20-40-37.png | (none/reference) | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-19 20-40-51.png | (none/reference) | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-19 20-41-51.png | (none/reference) | ● | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | · | 6 |
| Screenshot from 2026-07-19 20-44-56.png | (none/reference) | · | · | · | ● | · | · | · | ● | · | · | ● | · | · | · | · | · | 3 |
| Screenshot from 2026-07-19 20-45-22.png | (none/reference) | · | · | ● | ● | · | · | · | · | · | · | · | · | · | · | · | · | 3 |
| Screenshot from 2026-07-19 20-45-37.png | (none/reference) | · | · | · | ● | · | · | · | · | · | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-19 20-46-26.png | (none/reference) | ● | · | ● | · | · | · | · | · | ● | · | · | · | ● | · | · | · | 8 |
| Screenshot from 2026-07-19 20-46-59.png | (none/reference) | ● | · | ● | · | · | · | · | · | ● | · | · | · | ● | · | · | · | 8 |
| Screenshot from 2026-07-19 20-47-41.png | (none/reference) | ● | · | · | · | · | · | ● | · | ● | · | · | · | · | · | · | · | 4 |
| Screenshot from 2026-07-19 20-49-01.png | (none/reference) | · | · | · | ● | ● | · | ● | · | ● | · | · | · | ● | · | · | · | 10 |
| Screenshot from 2026-07-19 20-49-22.png | (none/reference) | · | · | ● | · | · | · | · | · | · | · | · | · | ● | · | · | · | 8 |
| Screenshot from 2026-07-19 20-52-39.png | (none/reference) | · | · | · | · | · | · | · | · | · | ● | · | · | · | · | · | · | 1 |
| Screenshot from 2026-07-19 20-52-55.png | (none/reference) | · | · | ● | · | · | · | ● | · | ● | ● | · | · | · | · | ● | · | 8 |
| Screenshot from 2026-07-19 20-53-07.png | (none/reference) | · | · | · | · | · | · | · | · | · | ● | · | ● | ● | · | · | · | 6 |
| Screenshot from 2026-07-19 20-54-21.png | (none/reference) | · | · | ● | · | · | · | · | · | · | ● | · | · | ● | · | · | · | 4 |
| Screenshot from 2026-07-19 21-04-03.png | (none/reference) | ● | · | · | · | · | · | · | ● | · | · | · | · | ● | · | · | · | 4 |
| Screenshot from 2026-07-19 21-04-31.png | (none/reference) | · | · | ● | · | · | · | · | ● | · | · | · | · | ● | · | · | · | 6 |
| Screenshot from 2026-07-19 21-06-15.png | (none/reference) | · | · | · | · | · | · | ● | · | ● | · | · | · | ● | ● | · | · | 4 |
| Screenshot from 2026-07-19 21-06-26.png | (none/reference) | · | · | · | · | · | · | ● | · | ● | · | · | · | ● | · | · | · | 3 |
| Screenshot from 2026-07-19 21-07-57.png | (none/reference) | · | · | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | 2 |
| Screenshot from 2026-07-19 21-08-06.png | (none/reference) | · | · | · | · | · | · | · | · | ● | · | ● | · | · | · | · | · | 2 |
| Screenshot from 2026-07-19 21-11-32.png | (none/reference) | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ● | 1 |
| Screenshot from 2026-07-19 21-11-42.png | (none/reference) | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ● | 1 |
| Screenshot from 2026-07-19 21-11-51.png | (none/reference) | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | ● | 2 |
| Screenshot from 2026-07-19 21-13-01.png | (none/reference) | · | · | · | ● | · | · | ● | · | · | · | · | · | · | · | · | · | 2 |
| Screenshot from 2026-07-19 21-13-16.png | (none/reference) | · | · | · | ● | · | · | ● | · | · | · | · | · | · | · | · | · | 2 |

## 5. Resolution ledger (NO silent drops)

All **467** marks are retained in `registry.jsonl` — none dropped. Each carries `resolved_date`, `resolved_year`, `matched_trade`, `data_avail`, `resolve_status`, `resolve_note`. Three tiers of certainty:

1. **Date-resolved — 222** (`firm` 11 + `era-approx` 211): pinned to a specific session via ytrades+results. Year is a price-era guess except SBILIFE t31 (firm 2024).
2. **Year-only — 61** (`label-year`): NSE trade-stock marks whose year comes from the mark's own label, but the exact date is an HTF/multi-month span with no single ytrades leg → date left null.
3. **No resolution source — 184**: not in ytrades/results at all — logged, never checked.

Breakdown of tiers 2+3 (everything NOT pinned to a session), by reason:

| reason | tier | count |
|---|---|---|
| reference graphic — uncheckable | 3 no-source | 108 |
| NSE mark: year from label, no ytrades leg that year (HTF context) | 2 year-only | 61 |
| dev stock HEROMOTOCO, not in ytrades — year unvalidated | 3 no-source | 30 |
| dev stock HDFCBANK, not in ytrades — year unvalidated | 3 no-source | 17 |
| EURUSD foreign — uncheckable | 3 no-source | 10 |
| BTC foreign — uncheckable | 3 no-source | 6 |
| GBPUSD foreign — uncheckable | 3 no-source | 4 |
| BTCUSD foreign — uncheckable | 3 no-source | 4 |
| XAUUSD foreign — uncheckable | 3 no-source | 4 |
| TSLA foreign — uncheckable | 3 no-source | 1 |
| **total not-pinned** | | **245** |

Cross-check: 222 date-resolved + 245 not-pinned = **467 = 467**. NSE trade-stock marks (checkable in principle against real tape): **283** (HAVELLS, SBICARD, SBILIFE, DABUR, DLF, VOLTAS, TITAN); non-NSE (dev/forex/crypto/reference, no NSE tape): **184**.

---
_registry: `/home/doom/Public/PROJECT/2026/trader/runs/validate/tools/registry.jsonl` · sources: 10 cat batches · resolution: ytrades.json + results.json + data/yahoo (yvalidate) · RECOGNITION only, never edge._
