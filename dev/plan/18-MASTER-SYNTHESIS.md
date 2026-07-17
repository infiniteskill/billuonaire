# Master Synthesis — the evidence-based system (2026-07-17)

Every head-to-head below measured identically on 20 NIFTY stocks × 19 sessions (free
yfinance M1), study `outcome`/`baseline` scoring (hit = MFE≥1×ATR before MAE≥1×ATR vs
time-bucket random), **temporal + cross-sectional (unseen-stock) holdout**, multi-TF.
Scripts in scratchpad; per-concept reports in `.superpowers/sdd/h2h-*.md`.

## ENTRY SIGNALS — validated, ranked by edge (ALL "enter at the grab" types)

| Signal | best edge (TF) | holdout (val / unseen-stocks) | n | note |
|---|---|---|---|---|
| **Inducement sniper** (HTF CHoCH dir + LTF inducement sweep, len20) | **+14% (M10)** | +16.3 / +20.1 | 221 | strongest; enter AT the IDM grab. BOS-after LOSES |
| **Supply/Demand retest** (Forex_Steward) | **+13.7% (M10)** | +14.1 / +16.6 | ~2k | beats OB at M5/M10, 4× signals; dies at M15 |
| **LuxAlgo OB retest** (vol-adj leg extreme, spike-excluded) | +10.4 (M5) → **+13.8 (M15)** | +16.6 / +17.8 | 1038 | most ROBUST across TF; the M15 pick |
| **FVG close-beyond** (dedicated LuxAlgo, displacement closes past gap) | **+12.4% (M10)** | +12.0 / +14.1 | 361 | close-beyond filter = the ingredient |
| **Compression-FADE** (fade the coil breakout) | +8–10% (all TF) | +9.9 / +10.9 | **6144** | huge sample; FADE not follow |
| **Wyckoff spring/upthrust** (retuned 30/4.0/1.25) | +23/+32% | (temporal only) | ~169/mo | strong but modest n |
| **TFlab sweep** | +8–11% (M10) | +11.3 / +11.8 | 207 | 3rd independent inducement-family confirm |
| EmreKb OB | +13.2 (M5) | — | 219 | higher edge, rarer; use as confluence filter |

## DIRECTION LAYER
- **HTF structure direction lifts edge — at the ~6× ratio.** M5 entry + **M30** direction:
  agree +10.7 / val +12.7 vs unfiltered +8.6. M5+M15 INVERTS (too-fast HTF = noise);
  M5+H60 dilutes. Rule: direction TF ≈ 6× entry TF.
- Premium/Discount position (+3.3%): weak standalone, use as a secondary filter (fade in
  premium/discount extremes).

## LOSERS — never enter here (these ARE the traps retail takes)
| Anti-signal | edge | note |
|---|---|---|
| Structure break BOS/CHoCH (entry) | **−18%** | UNIVERSAL: ours/LuxAlgo-fractal/TFlab/EmreKb — 4 defs, all negative |
| Confirmed breakout (BOS-after-IDM) | negative | waiting for confirmation = worse than the grab |
| Compression-FOLLOW (join the coil break) | −8 to −11% | the breakout is the trap |
| Liquidity pool sweep, HEAVY levels | −6 to −12% | volume-graded WORSE (−11.6 hi-vol vs −2.2 lo-vol); touches inverted too |
| Breaker (our current impl) | −8% | 0.85 strength on a negative signal |
| PO3 distribution | −15 to −27% | structurally late |

## THE FIVE LAWS (all measured, holdout-stable)
1. **Enter AT the grab, never at the breakout.** Every confirmed-breakout entry loses;
   every fade-the-trap / retest-the-zone entry wins.
2. **Fresh > obvious.** The heavier/more-touched/higher-volume a level, the WORSE — the
   crowded level is where a sweep becomes a real break (retail piled in, gets run, keeps going).
3. **Slower TF = more edge + cost-viable stops.** Sweet spot M10 (edge peaks, stops clear
   the ₹40 floor, good sample). M15 for the most robust zones, M5 for tightest SL.
4. **Structure break = DIRECTION compass, not an entry trigger.**
5. **Sniper = HTF direction (~6× TF) + LTF liquidity-grab entry + tiny SL beyond the grab.**

## PROPOSED V2 ARCHITECTURE (design — NOT yet built; needs portfolio-replay economic test)
- **Decision TF: M10** (primary). Direction from **M30/H1** structure. Tightest-SL variant M5.
- **Direction gate**: HTF (M30) CHoCH bias + premium/discount + wyckoff-HTF veto. No trade against it.
- **Entry = confluence of GRAB signals** at a zone in the HTF direction: inducement-sweep,
  SD/OB retest, FVG-CE (close-beyond), compression-fade, wyckoff-spring. Enter on the grab.
- **SL**: just beyond the grabbed extreme (the swept low / OB far edge) — tiny by construction.
- **Targets**: opposing liquidity; but avoid heavy/obvious levels as targets (they get run).
- **REMOVE from scoring**: structure-break-as-entry, breaker (current), PO3, heavy-level
  strength bonus, compression-follow, VSA booster (except FVG).
- **KEEP as context**: structure (direction), HTF phase (veto), timestats (flattened priors).

## Status
All rows above = `validated(OOS, 2-axis)` on ONE month. Remaining gates (per
`15-VALIDATION-METHODOLOGY.md`): block-bootstrap CI, portfolio-replay economic test, and a
FRESH forward month. This synthesis is the north-star design; building it is the next phase,
gated by the economic replay proving it beats the frozen baseline.
