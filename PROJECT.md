# TRADER — Project Orientation (for any AI / new session)

Read this first. It tells you what this is, where it stands, and the rules of engagement.
Deep detail lives in `dev/plan/`; this is the map.

## What it is
A CLI, data-only (no charts) **intraday trade engine for NSE cash equity**. It detects
operator manipulation via SMC/ICT + Wyckoff concepts, waits with discipline, takes 0–3
high-confluence paper trades/day, manages them, squares off before close. Dry-run first;
Kite Connect (live/paper broker + options) is a future adapter, not built yet.

Philosophy (binding, `dev/plan/00-DESIGN-SPEC.md`): single pipeline (live=replay, same
code — a backtest that runs different code lies); detachable detectors emitting `Evidence`,
confluence renormalizes over enabled ones; default answer is NO (patience); assume stops
are visible and hunted (stealth software stops, close-confirmed); costs modeled always;
Decimal money, NSE tick 0.05; data-only conclusions (no eyeballing).

Core model: **CAGE → TRAP → RELEASE**. Cage = today's boundaries (levels/OI walls). Trap
= morning manipulation (observe only, 09:15–11:00). Release = trade the reversal 11:00–14:30,
SL beyond the trap extreme, targets at opposing liquidity, squareoff 15:10.

## Where it stands (2026-07-17)
- **~111 commits, 592 tests green.** Pushed to `github.com/infiniteskill/billuonaire` (branch main).
- **Phases 1–5 complete**: data models, candle store (multi-TF, no-lookahead proven),
  12 detectors + Level state machine + confluence + gates + entry-FSM + paper broker +
  position manager + orchestrator + CLI, replay/report/calibrate, learning loop, memory
  bounds. Market-agnostic (`MarketSpec` — crypto/any works by config).
- **Real-data study done**: 20 liquid NIFTY stocks × 19 sessions (free yfinance M1),
  143k bars. First honest result: signals form but execution+cost killed them. Execution
  bug-fixes applied & validated (limit-fill, cost-viable stops, effective-R, STT sell-only):
  0→9 trades, cost drag 7R→0.23R/trade. Detector accuracy audited (64k evidences vs random
  baseline) — see findings below.
- **Phase 6 (Kite live/options) NOT started** — blocked on the user buying the API;
  also needs a Broker-ABC refactor first.

## The current research frontier (what we're actually doing now)
The 64k-evidence study measured every detector's real edge vs time-matched random baselines,
walk-forward. Key measured facts (ONE month, must re-validate):
- **The whole edge is fading extension after 11:00**: sweep/OB/FVG against-the-30-60min-move
  entries = +9–14% edge; with-momentum entries = poison. (User's "market traps then reverses"
  thesis, measured.)
- **Structure BOS/CHoCH are ANTI-signals at the break bar** (−22%) — a break is context, not
  an entry. The LuxAlgo reference fires identically → inherent to SMC, not our bug.
- **OB quality formula is inverted** (small subtle OBs win; hunt-born bonus falsified).
- **Pool-strength (touch-count) predicts nothing**; **wyckoff spring/upthrust retuned = the
  strongest edges (+23%/+32%)**; **VSA booster degrades everything but FVG**; **PO3 is
  structurally late** (parked).
- Reference Pine scripts (LuxAlgo SMC / Liquidity Swings) independently point to the same
  fixes: premium/discount fade-gate, volatility-adjusted OB anchor, volume-based liquidity,
  FVG close-beyond. (`dev/plan/13-PINE-VS-CODE-BRAINSTORM.md`.)

**CRITICAL DISCIPLINE (user directive): none of the detector retunes or Pine ideas are
applied. They are HYPOTHESES.** One correlated month tuned in-sample = overfitting = "shit."
Nothing reaches production until it clears `dev/plan/15-VALIDATION-METHODOLOGY.md`
(cross-sectional stock-holdout + block-bootstrap significance + multiple-comparison
discipline + economic significance + forward-accrued fresh data). All ideas tracked in
`dev/plan/14-IDEA-LEDGER.md` with status. **Do NOT "just apply" the retunes.**

## Layout
- `app/trader/` — the package. `detectors/` (12 plugins), `engine/` (levels, context,
  confluence, gates, entry, template, pipeline, po3, scanner), `execution/` (paper broker,
  position manager), `store/` (candles, journal), `feed/` (mock scenarios, file CSV, kite=TODO),
  `replay/`, `learn/`, `tools/` (fetch=yfinance, study=accuracy harness), `cli.py`.
- `app/config/config.json` — all tunables (weights, thresholds, risk, times, costs).
- `data/real/*.csv` — fetched M1 (20 stocks + NIFTY). `runs/` — replay journals (full20d = current baseline).
- `dev/plan/` — 00 spec, 01 contracts, 02 detector-specs, 03 roadmap, 05 axioms, 06 confluence,
  09/11 phase plans, 10 gap-audit, 12 real-month conclusions, 13 pine brainstorm,
  **14 idea-ledger, 15 validation-methodology** (the current-frontier docs).
- `.superpowers/sdd/` — agent run reports (gitignored). `dev/idea/`, `dev/design/` — original
  problem catalog + concept reference (NOT current solution; superseded by dev/plan).

## How to run
```
cd app && uv pip install -e '.[dev,data]'          # deps
.venv/bin/pytest -q                                 # 592 tests
.venv/bin/trader fetch RELIANCE INFY ... --days 28 --data ../data/real   # free M1 (~30d)
.venv/bin/trader replay --data ../data/real --all --from D1 --to D2 --dir ../runs/X --index NIFTY --capital 100000 --max-qty 1000
.venv/bin/trader report --journal ../runs/X/journal
.venv/bin/trader study --data ../data/real --all --out ../runs/study   # detector accuracy
.venv/bin/trader calibrate --journal ../runs/X/journal                 # weight suggestions (print-only)
```
Free-data limits: yfinance M1 = trailing ~30 days only; 15m ≈ 60d, daily = years. True new
history accrues only by fetching forward (set up a daily pull).

## Working rules
- COMPACT code (user mandate): shortest clear form, no bloat, small files, config-driven knobs.
- Commit trailer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Push when asked.
- Parallel agents on disjoint files are welcomed; NEVER `git add -A` in a shared tree (races) —
  use explicit pathspecs. Keep tool outputs small (agents died dumping >64k tokens).
- The pipeline is deterministic and no-lookahead — preserve both; any change re-runs the suite.

## Immediate next work
Build the validation harness (cross-sectional splits + block-bootstrap + hypothesis registry)
and set up forward data accrual, THEN validate the ledger ideas in batches. No production
detector change until validated. Also pending: re-run the detector-retune integrator wave —
but only AFTER its ideas clear the bar, not blindly.
