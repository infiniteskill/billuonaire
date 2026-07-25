# 49-APP-ARCH — pluggable app architecture (user spec, 2026-07-25)

## USER REQUIREMENTS (verbatim intent)
- Core PLUGGABLE to anything (django/fastapi/any shell) WITHOUT design change → modular tool.
- UI: watchlist → stock → on-click scan OR autoscan toggle (fetch+autoscan on start) → per-stock
  TRADE LIST → click trade → deep view w/ MULTI-TF switching.
- Execution engine (order/SL sending) LATER; risk manager LATER (to design). Executed trades shown
  in Kite = NOT our scope. Essentials only.
- Analysis must be RECORDED, not re-run on already-analyzed data: persist unvisited liquidity/OB/
  FVG/BB, price ranges/limits per feature; re-run only when needed (new bars).
- Analysis-charting is OURS (broker chart can't draw our objects): plot OB/FVG/liq/BB with a PANEL
  of what's drawn + TF tags (nested multi-TF: which OB is which TF), TF switcher, planned-entry
  marks ("we enter here") BEFORE execution, live price entering zones.
- Separation: UI / fetching / list management / analysis-charting = separate modules.

## MODULE MAP
CORE (pure python, zero framework deps)
  feed port (kite-live | file | any) · analysis engine (incremental, zone-registry persisted)
  scanner service (scan(stock) -> planned trades) · trade store (planned/upcoming/invalidated)
  execution port (LATER) · risk manager (LATER)
SHELLS (thin, replaceable)
  UI (watchlist/trades/deep-view) · fetcher daemon · analysis-chart renderer (our objects + panel)

## MEASURED LATENCY (stage2, full 14-detector deep scan, 2026-07-25)
- 6.68 ms per M1 bar incremental · ~2.5 s one-session catchup/stock · full 33-session deep scan
  82.7 s/stock · 40-stock live universe ≈ 0.27 s per M1 tick sequential (parallelizable).
- => live autoscan across 40 stocks is comfortably real-time on current hardware.

## EXISTING PIECES (map to modules)
- pipeline/Orchestrator = analysis engine (already incremental: detector cursors, LevelStore
  persists levels, journal records verdicts/skips). CLI = existing shell (proves pluggability).
- decide() already emits planned trades (entry/SL/target/grade) pre-execution.
- MISSING: zone-registry snapshot API (query unvisited zones per TF), scanner facade, trade store,
  UI, live kite feed adapter, execution+risk (later).

## RECALL-VS-PRECISION (user's 66% question — the honest frame)
66% = precision (wins of TAKEN trades; 34% = real taken losses, not missed detections).
RECALL vs the 32 marks ≈ 60-80% — missed classes: multi-day sweeps (S3 fixed), min_disp-killed
post-sweep OBs (I1 open), pending-extreme mitigations (B1 open), p/d warm-up early entries.
Real performance = recall x edge → recall fixes add MORE killshots at same quality.
