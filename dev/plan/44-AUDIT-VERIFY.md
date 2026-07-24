# 44 — AUDIT VERIFICATION (12 findings)

Verification of the 12 code-audit findings against the measured **+6.13R** research
edge (`runs/validate/tradebook_40_t8.txt:14` — `hi ALL n=706 win%=49 gross/t=+7.55R
NET/t=+6.130R`, the exact print format of `derive_tradebook.stat()`).

**Central question:** the +6.13R was measured by `tools/derive_tradebook.py` (an offline
research sim), **not** by the production pipeline (`ConfluenceEngine` → ladder → `EntryFSM`
→ `PositionManager`). So the only findings that can *invalidate the number* are those that
touch the **research path**; findings on the **production path** are live-readiness gaps.

## The two paths (why scope matters)

- **PATH 2 — RESEARCH (produces +6.13R):** `tools/derive_tradebook.py` loads a separate
  config `runs/validate/taught_profile/config.json`, hard-overrides
  `s.detectors.enabled = list(TAUGHT)` (derive:91) so ALL taught detectors are ON, builds
  `Orchestrator(... journal_dir=..., NO level_dir)` (derive:93-94), taps `registry.run_all`
  and routes evidence through `decide()` (derive:55, `decision.py`). `decision.py` is an
  independent AND-chain: it imports only context/evidence/level and has **zero** references
  to `ConfluenceEngine`, `EntryFSM`, `_traded_zone`, or `scanner`. Fills are simulated by
  `_sim` on the finest 1m candles with gap-aware intrabar touch and honest per-trade costs.
- **PATH 1 — PRODUCTION (never produced +6.13R):** the template `config.json` →
  `pipeline.py` → `ConfluenceEngine.score` → ladder → `entry.py`/`EntryFSM` →
  `manager.py`. Different entry selection, arm/trigger gating, stop-widening, M5-close
  stops, laddered exits. The +6.13R has **never** been reproduced through this path.

## (a) Per-finding verdict / scope / edge-impact

| # | Finding | Verdict | Scope | Path touched | Invalidates +6.13R? |
|---|---------|---------|-------|--------------|---------------------|
| F1 | decision tree has no production caller | CONFIRMED | production-only | PATH 1 | No — derive calls `decide()` directly (derive:55) |
| F2 | taught detectors disabled in template | PARTIAL | production-only | PATH 1 | No — derive overrides `enabled=TAUGHT` (derive:91) |
| F3 | restart/watermark state loss | PARTIAL | production-only | PATH 1 | No — derive has no `level_dir`; restart branch is dead code |
| F4 | `min_zone_detectors:1` (single-signal entry) | CONFIRMED | production-only | PATH 1 | No — `decision.py` never reads confluence block |
| F5 | transitive/lineage-blind overlap merge | CONFIRMED | production-only | PATH 1 | No — `_cluster` lives only on PATH 1 |
| F6 | traded-zone entry substitution | CONFIRMED | production-only | PATH 1 | No — `decide()` derives its own entry (`_mid(z.zone)`) |
| F7 | no 2m/3m confirmation timeframe | CONFIRMED | both | PATH 1+2 | No — edge measured *on* M5-confirm/1m-fill; self-consistent |
| F8 | **scanner lookahead (far-future read)** | PARTIAL | production-only | PATH 1 (CLI only) | **No — derive does NOT import the scanner** |
| F9 | M5-close-confirmed market stop | CONFIRMED | production-only | PATH 1 | No — sim caps loss at −1.0R intrabar touch (derive:76) |
| F10 | **research-vs-production parity** | CONFIRMED | research-parity | PATH 1≠2 | **No — but the number is unproven through PATH 1** |
| F11 | feed/bucket boundary handling | CONFIRMED | both | PATH 1+2 | No — only drops 1 final M5 bar/symbol; no look-ahead |
| F12 | no live/Kite feed | CONFIRMED | both | PATH 1+2 | No — backtest needs no live stream |

Scope tally: production-only = 8 (F1,F2,F3,F4,F5,F6,F8,F9) · both = 3 (F7,F11,F12) ·
research-parity = 1 (F10).

## (b) Counts

- **CONFIRMED: 9** — F1, F4, F5, F6, F7, F9, F10, F11, F12
- **PARTIAL: 3** — F2, F3, F8
- **FALSE_POSITIVE: 0**
- Total: 12

## (c) KEY conclusion — invalidate vs live-only

**Findings that INVALIDATE the measured +6.13R research edge: NONE (0 of 12).**

Every finding lands in one of two buckets, neither of which falsifies the number:

**Bucket A — production/live-readiness only (11):** F1, F2, F3, F4, F5, F6, F7, F8, F9,
F11, F12. These are defects in the PATH 1 production engine (or missing infra like the
live feed) that the research sim never invokes. `decide()`/`derive_tradebook.py` bypass
`ConfluenceEngine` (F1,F4,F5,F6), enable the taught detectors regardless of the template
(F2), run one continuous pass with no restart state (F3), cap losses at −1R by intrabar
touch instead of a market stop (F9), and never touch the scanner (F8). They block going
live; they do not change the measured R.

**Bucket B — research↔production parity gap (1):** F10. This is the load-bearing one. It
does not say the +6.13R is *wrong* — it says the +6.13R describes a **different strategy**
than what would execute live. The production path uses different entry selection, arm/
trigger gating that would drop many `decide()` takes, `min_stop_atr` stop-widening (which
`entry.py:154` itself warns "would kill the RR edge"), M5-close-confirmed stops instead of
1m intrabar touch, and laddered partial/trailing exits instead of one fixed-R runway
target. So the number is an honest measurement of the research strategy that has **never
been reproduced through production**.

**On F8 specifically (the scanner lookahead):** the derived tradebook does **NOT** use the
scanner. Verified: `scanner` is imported only by `app/trader/cli.py`, `test_cli.py`, and
`test_scanner.py` — `tools/derive_tradebook.py` and `decision.py` contain no scanner
reference. The far-future read is confined to the CLI `list` display and `watch --auto`
symbol pre-selection. It can bias *which symbols the CLI chooses to run*, never a trade
signal in the tradebook. **The +6.13R is not contaminated by lookahead.**

## (d) Honest bottom line

**The +6.13R research edge is REAL-BUT-UNWIRED — not contaminated.**

- **Real:** it is an internally self-consistent measurement — taught AND-chain entries/
  stops/runway target, gap-aware 1m intrabar fill (conservative: stop-before-target on
  ambiguous bars), honest per-trade rupee costs. No confirmed finding puts look-ahead or a
  data leak into the research path. F8 (the one lookahead finding) does not reach it; F11's
  only research-path effect is dropping a single final complete M5 bar per symbol — a
  deterministic ~1-bar boundary artifact with no directional bias.
- **Unwired:** the edge was measured on PATH 2 and has never been reproduced on PATH 1.
  Production is not merely "not enabled" (F1,F2,F4) — via F10 it is a *structurally
  different strategy* whose stop-widening + close-confirmed fills + partial ladder would
  materially reshape the R distribution, and via F9 would realize losses > 1R that the sim
  caps at −1R.
- **Verdict:** the number stands as a research result. It is **not proven as a live edge.**
  Closing the gap requires wiring `decide()` into production (F1,F2), removing single-signal
  entries (F4), and — decisively — reproducing the tradebook through the actual
  `EntryFSM`/`PositionManager` execution model (F9,F10) before any capital is risked.

---
*Verified 2026-07-24. Load-bearing facts checked against source: scanner import sites;
`decision.py` independence; `derive_tradebook.py` decide()-wiring, TAUGHT override, and
absent level_dir; +6.13R location.*

## F9 PRODUCTION-PARITY TEST (2026-07-24) — the edge SURVIVES the M5-close stop rule
Added stop_mode to tools/derive_tradebook.py (research harness only; intrabar default =
the +6.13R baseline). 'm5_close' replicates production PositionManager (manager.py:78):
stop only on an M5 CLOSE beyond sl, filled at that close (loss CAN exceed 1R); target =
limit touch. BOTH modes run on the SAME decide() signals, 40 stocks, one pass.
| tier>=4 | intrabar (research) | m5_close (production F9) |
|---|---|---|
| net/trade | +6.13R | **+5.80R (-5.4%)** |
| win% | 49% | 50% |
| holdout all-4 | + (4.3..9.1) | + (3.7..9.3) |
| outcomes | stop993/gap557/tgt605 | stop877/gap604/tgt660 |
READ: the production stop rule gives FEWER stops (survives intrabar wicks) + MORE targets,
roughly offsetting the bigger close-through losses -> net -5% on the high tier, win% holds,
all 4 holdout quadrants stay positive. **F9 (the audit's biggest execution R-reshaper) is
REAL but NOT the killer — the edge survives it.** grade-4 marginal tier is sensitive (flips
-0.42 under m5_close), so the tradeable boundary is >=5. REMAINING production-parity to test:
F6 (entry substitution) + F10 (laddered exits / arm-trigger gating) + F1 (wire decide() into
pipeline for a true end-to-end production reproduction). Still one 17d regime.

## F1 WIRING (2026-07-24) — decide() into production: part-1 done, 2 real gaps found
Part-1 (COMMITTED, 915 green, default-preserving): decision.py Decision gains zone/members;
pipeline reads detectors.params.decision.{engine,min_grade}; engine=taught routes _on_m5_close
to _taught_zones() (fresh-zone-gated decide() -> forced-arm ScoredZone) instead of confluence.
Smoke replay (engine=taught, 2 stocks): runs end-to-end, NO crash in the wiring -> taught zones
reach the FSM. But 0 trades, revealing TWO production-parity gaps the derived sim never had:
1. **Production GateChain rejects all taught signals**: skips = template 43, time_window 71,
   ladder 16, chase 12. time/ladder/chase are config-relaxable; the TEMPLATE gate (gates.py:106,
   rejects ctx.day.template=='UNCLASSIFIED') needs a taught bypass. These are confluence-era
   SELECTION gates irrelevant to the taught decision (which already decided).
2. **Meta-schema bug**: EntryFSM.arm (entry.py:155) does sig.meta['sl_floor'], but htf_nest (and
   some taught signals) emit 'sl' WITHOUT 'sl_floor' -> KeyError. The FSM's tiny-stop logic assumes
   ob_taught's exact meta schema.
=> F1 is MULTI-PART. The +6.13R (raw decide() signals) is untouched; production wraps them in gates
+ a meta assumption that don't yet fit the taught chain. NEXT (verified): entry.py
sig.meta.get('sl_floor','0'); bypass template/ladder for engine=taught; re-run replay -> net-R
through production execution vs +6.13R. NO production-engine code changed this session (edge-safe).
NOTE: taught_profile config.json has experiment values (gates relaxed, engine=taught) — a research
artifact, not production defaults.
