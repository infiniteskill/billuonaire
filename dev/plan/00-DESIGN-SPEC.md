# TRADER — Design Spec (v1)

> Approved design, 2026-07-15. Supersedes `dev/idea/` + `dev/design/` SOLUTIONS.
> Those docs remain the PROBLEM catalog (manipulation tactics) and concept reference.
> `dilemma` (Django, browser-data) is dead — nothing reused.

## Mission

CLI-based, data-only (no visuals), intraday trade planner + executor for NSE cash equity.
Watches a user-picked subset of a stock list, detects operator manipulation
(SMC/ICT + Wyckoff + options-cage), waits with discipline, takes 0–3 high-confluence
trades/day, trails structure-based, squares off before close. Dry-run first
(paper fills, simulated), Kite Connect added later behind an adapter.

## Non-Negotiable Principles

1. **Single pipeline** — live, paper, and replay run the *same* analysis/decision code.
   Only the feed and the broker adapters differ. A backtest that runs different code lies.
2. **Detachable detectors** — every concept (OB, breaker, FVG, sweep, Wyckoff, cage…)
   is a plugin emitting `Evidence`. Config can disable any detector; confluence
   renormalizes weights over enabled detectors. Absence never breaks anything.
   Detectors NEVER veto; only cross-cutting Gates veto.
3. **Data-only conclusions** — Wyckoff "boxes", patterns, curvature: all reduced to
   arithmetic on OHLCV + OI. No chart, no image, no human eyeballing in the loop.
4. **Default answer is NO** — patience engine. Entry must pass every gate.
   Skips are logged with reasons and scored later (skipped-setup outcome tracking).
5. **Blind-build first** — no API today. MockFeed (scripted scenario days with known
   ground truth) + FileFeed (CSV/bhavcopy). KiteFeed is a thin adapter added last.
6. **Assume stops are visible and hunted** — stealth stops (software-held),
   never placed at obvious levels, close-confirmed breaches, wick tolerance.
7. **Costs modeled always** — brokerage/STT/slippage in every paper fill.
   Results without costs are fiction.
8. Decimal for all prices, quantized to NSE tick 0.05. Never float for money.

## Core Model: CAGE → TRAP → RELEASE

- **CAGE** (pre-market + rolling): today's allowed battlefield.
  Edges = OI walls (max CE OI = ceiling, max PE OI = floor), max pain,
  ATM straddle width, PDH/PDL, PWH/PWL, round numbers. Without options data
  the cage degrades gracefully to price-levels only.
- **TRAP** (observation, roughly 09:15–10:45): morning move treated as suspect.
  Trap confirmed by chain: cage-edge/liquidity **sweep** → LTF **CHoCH** →
  **breaker / inversion-FVG** forms → consequent encroachment holds,
  with Wyckoff volume confirmation (climax + absorption = spring/upthrust).
- **RELEASE** (trade window, ~10:45–14:30): direction = opposite of trap,
  aligned with HTF phase veto (no longs inside HTF markdown — the
  "3-months-underwater" defense). Entry at breaker/iFVG/OB retrace in OTE.
  SL beyond trap extreme + ATR buffer, off round numbers. Targets: internal
  liquidity → opposite cage edge; partials 1R/2R, trail structure, squareoff 15:10.

## Day Templates (classified by ~11:30, all from data)

| Template | Signature | Play |
|---|---|---|
| TRAP_REVERSAL | one cage edge swept + reclaimed + CHoCH | trade release direction |
| TREND | opens near edge, drives, no reclaim, shallow pullbacks | join pullbacks only, no fades |
| RANGE_PIN | no edge swept, narrow straddle, tight OI walls | fade edges half-size or skip |
| DOUBLE_TRAP | both edges swept | only 2nd sweep, half size |
| UNCLASSIFIED | none confirmed | no trades |

Template stats learned per stock over time; feed confluence weights.

## Decision Pipeline (per stock, per closed candle)

```
feed event → candle store merge → level state machine update
 → run enabled detectors → Evidence list
 → confluence score (renormalized weights, direction consensus)
 → template classifier state
 → gates: [risk budget, time window, regime/HTF veto, psychology caps, template known]
 → verdict: WAIT | ARMED | ENTER | VETO(reason)
 → if ENTER: TradePlan → paper broker → position manager (trail/partials/squareoff)
 → journal (trades AND skips, full evidence snapshot)
```

## Anti-Stop-Hunt Rules

1. SL held in software only; exit = market order on **close beyond** stop, not wick touch.
2. Wick tolerance: configurable 1-candle penetration allowed if reclaim.
3. Placement: beyond swept trap extreme + `atr_buffer × ATR`, offset from round numbers.
4. Live phase later: catastrophic exchange SL-M at 2× stop distance (crash insurance only).
5. Backtest measures hunt-survival benefit vs slippage cost — data decides the rule.

## Risk Engine

- Per trade risk = min(0.5% capital, user max-qty × stop distance). Qty derived; user qty = ceiling.
- Max 3 trades/day, 1 per stock/day, 2 consecutive losses = day over, daily loss cap 1.5%.
- No entry after 14:30. Hard squareoff 15:10. Expiry Thursday: size × 0.5.
- All values in `config.json` — everything tunable, nothing hard-coded.

## CLI (typer + rich)

```
trader init                          # scaffold config.json + stocks.json
trader list                          # numbered watchlist + today-fit score
trader watch 1 4 7 --capital 100000 --max-qty 50    # live/paper loop
trader status                        # per-stock state machine verdicts
trader journal --today               # trades, skips, PnL
trader replay --from D1 --to D2 [--stocks 1,4,7]    # backtest, same pipeline
trader report --month                # metrics: WR, PF, DD, per-template, per-gate
```

`stocks.json` = list of symbols. `watch` args pick by number. Fit score
(pre-market): spread, ATR%, avg volume, gap vs cage.

## Validation Strategy

- Breadth over duration: ~30 stocks simultaneously. Caveat encoded: same-day
  stocks share regime → metrics clustered per day; need ≥10 sessions for confidence.
- MockFeed scenario days with ground truth = detector unit tests (precision/recall
  per detector against scripted traps).
- Expected honest numbers: WR 45–55%, avg RR 1.8–2.5, PF 1.3–1.8, DD 10–15%.
  ~70% of concepts may fail statistically → learning loop kills weak detectors' weights.

## Explicitly Out of v1

Options/futures as tradeable instruments (context only), web dashboard,
real order placement, L2 order-flow, news calendar, Markov/Monte Carlo
prediction (rejected — reactive precision, not forecasting).

## Layout

Code: `app/`. Plans: `dev/plan/`. See `01-ARCHITECTURE-CONTRACTS.md`.
