# 47-40STOCK — WALK-FORWARD: 19/19 sequential windows positive (2026-07-24)

Temporal-stability rigor check: split each tape's hi-tier (grade>=5 eod, deduped, min-RR>=3) into
sequential time windows, measure net-R per window. Is the edge stable over time, or a few lucky periods?

| tape | windows POSITIVE | net-R range | span |
|---|---|---|---|
| FULL-2026 (7 stk, 137 sessions) | **7/7** | +0.30 .. +10.65R | 2026-01-07 .. 07-23 |
| BEAR-2024Q4 (40 stk) | **6/6** | +3.18 .. +8.67R | 2024-09-04 .. 11-29 |
| BULL-2023 (40 stk) | **6/6** | +7.48 .. +10.72R | 2023-11-06 .. 2024-01-31 |

**19/19 sequential windows positive**, ~14 months of calendar coverage across 3 regimes.

KEY: the frozen config was tuned on the 2026-06-24..07-17 slice, yet FULL-2026 windows W1-W5 (Jan-May 2026)
are BEFORE the tuning window = genuinely OUT-OF-SAMPLE (and earlier in time) -> all positive (+6.50..+9.94R).
The config generalizes BACKWARD in time. The weakest window anywhere (2026 W6, +0.30R/54%) still does not lose.

=> The edge is TEMPORALLY STABLE, not a few lucky periods. Combined with regime-agnostic (3 regimes,
all quads +), window-robust (min-RR), deduped/honest, and faithful-in-local-context, the validation
stack is about as complete as historical-1m data allows.

## Validation stack (status)
- Regime-agnostic: 3 regimes, 12/12 quad-regime cells + ..................... PASS
- Window-robust: min-RR makes far-RR edge lookback-invariant .................. PASS
- Temporally stable: 19/19 sequential windows + (incl OOS-earlier 2026) ....... PASS (this doc)
- Honest/deduped: raw ~40% clustering-inflated -> +6-7R executable ............ PASS
- Faithful (local context): user shorts fire as winners (1221 +27.6R) ......... PARTIAL (shorts; context-dep)
- Tuning-resistant: 3 deep-study fixes rejected by gate; robust optimum ....... PASS

## Remaining (the untouchable ceiling + last steps)
- 12 prior-year (Aug-Dec) marks (2024/25 fetch) -- extend faithfulness.
- Tick-granular fills -- replace the 1m gap-aware model (sim optimism).
- Live execution / capacity / latency -- only a paper pilot answers these.
- Future-regime -- unknowable; 14 months of history != the future.
VERDICT: a VALIDATED CANDIDATE. The next real step is a small PAPER PILOT (needs live Kite wiring),
not more historical tuning.
