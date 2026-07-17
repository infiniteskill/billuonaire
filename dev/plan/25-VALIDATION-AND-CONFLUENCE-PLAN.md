# 25 — Validation & Confluence Master Plan (2026-07-17)

The deep plan from here to a validated, confluence-driven v2. Sequence is the user's:
**finish building → list every tool → validate+improve each's accuracy in-framework → check on 50
stocks → plan improvement + confluence.** One law governs all of it:

> **The scratchpad edges do NOT count. They were measured on multi-day concatenated series with
> per-bar ATR; the framework runs per-session with drifting state. Every tool is re-validated
> IN-FRAMEWORK on real data before it earns a place. The 50-stock in-framework number is truth.**

(Wave-1 reviews already proved this matters: `inducement` reproduced only 35% of its scratchpad
grabs in-framework; `ob_lux` reset per session vs multi-day; `fvg_cb`/`compression_fade` emit
multiplicity the batch had. The gap between scratchpad and framework is exactly what Phase C/D measure.)

---

## PHASE A — Finish the toolkit (build what's left)
| Wave | Item | Status |
|---|---|---|
| 1 | ob_lux, fvg_cb, compression_fade | ✅ built + reviewed + fixed + pushed |
| 1 | inducement (stateful rewrite) | 🔧 in flight (parity-gated) |
| 2 | bpr, mitigation, turtle_soup | briefs staged → build next |
| 2 | sl_cluster_map (fresh>obvious level fatness map) | design below |
| 3 | H60 direction (leak-free), SMT divergence, premium/discount filter | build |
| 3 | decision-TF = M10 (MarketSpec config, thread through pipeline) | build |
| 3 | structure → direction-only (weight 0 as entry) | reweight |
| 3 | **planner honors `meta["sl"]`** (destroyed-extreme tiny SL, not ATR-buffer) | integration |
| 3 | level-consumer OWNER filter (kind≠owner bug) + evidence dedupe-by-price-event | integration |

**sl_cluster_map** — not a signal detector; a per-symbol map of fat SL clusters (OB/FVG/SD zones,
PDH/PDL/PWH/PWL, EQH/EQL, round numbers) each scored by fatness = obviousness × touches × roundness
× recency, with the strength **sign-INVERTED** (measured: fresh/light > obvious/heavy). Feeds
(a) zone-freshness weighting in confluence, (b) draw-on-liquidity target selection.

## PHASE B — Tool inventory ("list of each tool")
Deliverable: `dev/plan/26-TOOL-REGISTRY.md` — one row per tool:
`name | emits (Evidence/Level) | direction rule | SL semantics | scratchpad edge | in-framework edge (TBD) | role (trigger/zone/filter/direction/map) | enabled-in-v2?`
This is the single source of truth for what exists and its measured standing. Built after Phase A,
filled in by Phase C/D.

## PHASE C — Per-tool in-framework validation + improvement
For EACH tool, one leak-free measurement **through the real pipeline** (not the scratchpad):
1. Replay the tool alone on real data; collect its emitted Evidence (ts, dir, zone, sl).
2. **Accuracy / hit-rate:** hit = MFE ≥ 1×ATR before MAE ≥ 1×ATR (session-safe, EOD-truncated).
   edge% = hit% − same-time-bucket random baseline. RR = mean max-R at the tool's own tiny SL,
   expectancy@{2,3,5,10}R. Sample n.
3. **Holdout:** temporal (derive-days / validate-days) AND cross-sectional (stock-set A / B). A tool
   passes only if the sign holds on BOTH holdouts.
4. **Improve:** if in-framework edge < scratchpad, diagnose (session-reset loss? SL wiring? threshold?
   multiplicity?) → tune params → re-measure. Freeze tuned params in config. No peeking at holdout
   while tuning (tune on derive-set only).
5. **Gate:** tool → confluence ONLY if in-framework holdout edge clears its bar (hit-edge >0 stable,
   or RR-expectancy >0 stable). Else: drop or demote to filter.

## PHASE D — 50-stock accuracy + hit-rate sweep (the headline check)
1. **Data:** fetch NIFTY-50 (50 liquid NSE names) M1 over a uniform trailing ~30-day window via
   `trader fetch <sym> --days 30 --source yfinance` (background; yfinance M1 is trailing-only). Store
   under `data/real50/`. Log any symbol that fails/gaps.
2. **Splits:** cross-sectional 25/25 (derive / holdout stocks) + temporal mid-split within each.
   Multiple-comparison aware (many tools × many R-targets → discount marginal winners).
3. **Sweep:** run Phase-C measurement for every tool across all 50 stocks. Output
   `runs/val50/accuracy.md` — table `tool × [n, hit%, edge%, exp@3R, exp@5R, RR-median, holdout-sign]`.
4. **This table is the ground truth** that ranks the toolkit and sets confluence weights. It replaces
   every scratchpad number in docs 16/18/23.

## PHASE E — Improvement loop
- Rank tools by in-framework holdout edge. Drop < bar; keep+weight the rest by measured marginal edge.
- Per-stock behaviour profile: which stocks respect which tools (cleanliness/respect stat) → feeds selection.
- Tune the marginal-but-promising tools (thresholds, TF) on derive-set; re-measure on holdout.
- Iterate until the kept set is stable across holdouts (no new overfit).

## PHASE F — Confluence engine (deep)
The decision is a **weighted-quality vote**, NOT a count (density-doesn't-lift is validated).
1. **Spatial confluence:** tools whose Evidence agrees on direction AND co-locates at a zone within
   N×ATR stack. Score = Σ (tool_weight × tool_strength), weights = Phase-D marginal edge.
2. **Gates (measured, not assumed):** H60 direction agree, premium/discount OK, fresh>obvious (cluster
   map), min-RR (far target ÷ tiny SL) ≥ threshold, in entry window, within heat/trade limits.
3. **Validate the LIFT (the unproven core claim):** does a weighted-confluence entry beat the single
   best tool alone, on holdout? Measure: expectancy(confluence≥T) vs expectancy(best-tool-alone). Also
   find WHICH pairs/triples actually stack (measured), since count alone doesn't. If confluence shows
   no lift → the engine reduces to "best tool + direction filter"; that's still a system, honestly derived.
4. **Selection layer:** rank the 50-stock universe each day by setup-potential (cleanliness × energy ×
   zone-proximity × HTF-align × the stacks that measured-lift); trade only the top max-profit setups.

## PHASE G — Economic replay gate (ship/no-ship)
Assemble the full v2 config (enabled tools + Phase-D weights + M10 + H60 + SL-wiring) and replay the
50-stock month on the HOLDOUT stocks, **with realistic costs** (brokerage + STT + slippage at the
tiny-SL rupee risk). Ship v2 ONLY if net-R beats the baseline replay AND survives costs AND the win/RR
profile matches the honest expectation (~30–45% win, +0.2–0.4R/trade). Then forward-accrue a month.

## Build/measure discipline (non-negotiable)
- Leak-free (fully-closed bars, no look-ahead), EOD-truncated RR, session-safe hit.
- Holdout BEFORE belief (temporal + cross-sectional); multiple-comparison discount.
- Frozen hypotheses; the in-framework 50-stock number supersedes scratchpad.
- Every tool: subagent-built → adversarially reviewed → parity/accuracy-gated → then confluence.

## Immediate next actions
1. Land inducement fix (parity-gated) → merge → push.
2. Build Wave 2 (bpr, mitigation, turtle_soup) → review → merge.
3. Build sl_cluster_map + Wave-3 infra (H60/SMT/M10/SL-wiring/owner-filter).
4. Build the Phase-C in-framework measurement harness (reuses replay + study.outcome/baseline).
5. Fetch NIFTY-50 data → run the Phase-D sweep → publish `runs/val50/accuracy.md`.
6. Build + validate the confluence engine → economic replay gate.
