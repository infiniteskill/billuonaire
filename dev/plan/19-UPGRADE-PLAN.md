# System Upgrade — Brainstorm + Plan (v2, "see & earn")

Goal: the best AUTO system — it does everything (scan → decide → enter → manage → exit →
learn), user just watches and earns. Built on the measured evidence (`18-MASTER-SYNTHESIS.md`)
+ error/robustness removal (`10-GAP-AUDIT.md`). Nothing ships unproven (`15-VALIDATION-METHODOLOGY.md`).

## The vision, decomposed into 3 pillars
1. **BRAIN v2** — the signal engine rebuilt to the evidence (grab-not-breakout, M10,
   fresh>obvious, HTF-direction + LTF-grab sniper). Must PROVE it earns before it ships.
2. **ARMOR** — error removal + robustness so it can run unattended without breaking or
   losing state (persistence, crash-recovery, holiday calendar, Broker-ABC, logging).
3. **AUTOPILOT** — autonomy + interface: scheduled full-day automation, live feed (Kite),
   a "just watch" live view + push alerts, safety kill-switches, self-tuning within guardrails.

---

## PILLAR 1 — BRAIN v2 (the measured redesign)

### What changes (from 18-MASTER-SYNTHESIS, all validated 2-axis on 1 month)
- **Decision TF → M10** (edge peaks, stops cost-viable). Keep M5 for tightest-SL variant, M15 for zones.
- **Direction layer**: HTF structure bias at ~6× TF (M10→H1), + premium/discount extreme, + wyckoff-HTF veto. No trade against it.
- **Entry = confluence of GRAB signals** at a zone in HTF direction: inducement-sweep,
  SD/OB retest (LuxAlgo vol-adj anchor), FVG close-beyond, compression-FADE, wyckoff-spring.
  Enter ON the grab; SL just beyond the grabbed extreme (tiny by construction).
- **Freshness scoring**: fresh/thin levels weighted UP, heavy/obvious/high-volume DOWN (inverted from now).
- **REMOVE from scoring** (measured losers): structure-break-as-entry, breaker (current impl),
  PO3-distribution, heavy-level strength bonus, compression-FOLLOW, VSA booster (except FVG-confirm).
- **KEEP as context** (not entry): structure→direction, HTF phase→veto, timestats (flattened priors).
- Targets at opposing liquidity but AVOID heavy/obvious levels (they get run, not respected).

### Key fork — how to build it without wrecking the validated baseline
**Recommend: build v2 detectors ALONGSIDE (new `detectors/` + a v2 config profile), keep the
current pipeline, and A/B via replay.** Reasons: the current system is a green, proven-honest
baseline; v2 is a big change (removes half the detectors, new TF); we must be able to compare
`replay(baseline)` vs `replay(v2)` on the same month + holdout stocks. Only promote v2 if it
wins the economic replay. (Alt: refactor-in-place — rejected, loses the comparison + big risky diff.)

### The gate v2 must clear before it becomes "production"
Portfolio replay on the cross-sectional HOLDOUT stocks: v2 net-R > baseline net-R with the
change's own block-bootstrap CI on daily net-R excluding zero, AND positive on a fresh
forward month once accrued. Economic significance, not just per-signal edge.

---

## PILLAR 2 — ARMOR (error removal + unattended robustness)

From the gap audits, ranked by what blocks unattended running:
- **Position + RiskState persistence** — a crash mid-day currently loses open positions/risk
  ledger. MUST fix before any unattended run. (LevelStore + CandleStore persistence already wired.)
- **Broker ABC** — never built; `PaperBroker` is concrete. Blocks Kite drop-in. Extract the
  interface now (small refactor) so live is a pure adapter later.
- **NSE holiday/session calendar** — MarketSpec has no trading-day notion; a holiday misread
  corrupts stats and would arm on a closed day. Add.
- **Config packaging** (`trader init` breaks on non-editable install) — fix for deployment.
- **Remaining correctness** — re-audit v2 detectors the same way (adversarial + no-lookahead),
  and clear any deferred minors (wyckoff zero-guard done, etc.).
- **Logging + structured audit** — done (P5T5); extend with a daily run-report log.

## PILLAR 3 — AUTOPILOT (auto-everything + "just watch")

- **Scheduler** — one command/daemon runs the full day automatically: 08:45 pre-market
  fetch + scan + rank → 09:15 observe → 11:00 arm → intraday loop → 15:10 squareoff →
  15:45 report + nightly calibrate. Cron or an in-app async scheduler + NSE-calendar aware.
- **Live feed = Kite** (the real blocker — needs the API purchased). Until then, AUTOPILOT
  runs in "paper-live" on scheduled fetch+replay of the day's accrued data (near-real-time).
  KiteFeed slots into the DataFeed ABC; KiteBroker into the Broker ABC — zero brain changes.
- **"We just see"** — data-only mandate ⇒ interface = (a) a live `rich` terminal dashboard
  (per-symbol state, armed zones, positions, PnL, verdicts) + (b) **push alerts** (Telegram
  bot) on arm/entry/exit/EOD so the user earns without watching a screen.
- **Safety** — hard kill-switch; daily-loss auto-lock (exists); portfolio heat cap (exists);
  crash-recovery reload of positions/levels; "dry-run vs live" flag with a deliberate arming step.
- **Self-tuning** — nightly calibration exists (print-only). AUTOPILOT can auto-apply weight
  nudges WITHIN tight guardrails (±10%/week cap, min-sample gate, walk-forward, all journaled)
  — but only after v2 is proven and forward data exists. Auto-tuning on thin data = the #1 way
  to "make shit"; gate it hard.

---

## Phased plan (sequenced by dependency + risk)

**Phase U1 — Prove BRAIN v2 (validation-gated, no production change).**
Build v2 grab-signal detectors + M10 profile alongside; economic replay A/B vs baseline on
holdout stocks + bootstrap CI. If it doesn't beat baseline → iterate signals, don't ship.

**Phase U2 — ARMOR.** Position/RiskState persistence, Broker ABC extraction, holiday calendar,
config packaging, v2 correctness re-audit. Makes it unattended-safe.

**Phase U3 — AUTOPILOT (paper).** Scheduler (calendar-aware full-day automation) + live
terminal dashboard + Telegram alerts + kill-switch + crash-recovery. Runs the whole day on
accrued data automatically. This is "see & earn" minus real-time ticks.

**Phase U4 — LIVE (Kite).** KiteFeed + KiteBroker adapters (blocked on API purchase). Paper-live
on real ticks → then real orders behind a deliberate kill-switch + tiny size. Options/OI (cage)
detector becomes possible here.

**Phase U5 — CONTINUOUS SELF-IMPROVEMENT.** Forward-data accrual compounds; nightly
auto-calibration within guardrails; monthly re-validation; weak signals auto-benched (human
confirms kills). The system that keeps getting better while the user watches.

## Open forks for you (decide before U1)
1. **v2 build style**: alongside + A/B (recommended) vs refactor-in-place?
2. **Interface**: terminal dashboard + Telegram alerts — is Telegram the alert channel you want?
3. **Self-tuning autonomy**: auto-apply calibration within guardrails, or always human-confirm?
4. **First**: do U1 (prove the brain earns) before any ARMOR/AUTOPILOT work — agree? (Building
   autopilot around an unproven brain = automating losses.)
