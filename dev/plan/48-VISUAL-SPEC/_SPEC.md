# 48-VISUAL-SPEC — the trader's visual language vs detector code (2026-07-25)

Source: 85 hand-annotated screenshots (32 trades + WYCKOFF refs), 4 observer passes (obs_a..d.md),
diffed against all 11 detectors + decision.py. Goal: human-eye detection fidelity.

## A. THE UNIFIED VISUAL LANGUAGE (how the human draws — cross-image invariants)

| object | anchor | edges | TF drawn on | birth | death |
|---|---|---|---|---|---|
| **Liquidity line** | 2+ equal wick-pivots (EQH/EQL) or range extreme | WICK price, single line | any (5m-30m) | 2nd equal touch | segment ENDS at sweep candle |
| **Extreme line** | absolute wick hi/lo of the traded range | WICK, full-width red | 30m/4H ctx | range identified | swept+reversed |
| **Sweep** | THE poke candle (wick through line, close back) | — | entry TF | marked AT poke, not reclaim | — |
| **BOS** | swing-pivot level broken by close | thin line or thin BAND (t24 rects) | entry TF | the break candle; segment ends there | — |
| **OB** | (a) last opposite bodies before impulse OR (b) basing cluster right AFTER sweep candle | **BODIES; sweep wick deliberately OUTSIDE** (poking below/above box) | 5m-2H | after impulse leaves | deep break → INVALIDATED (kept on chart, relabeled) |
| **Internal/refined OB** | tighter body cluster inside parent, at lower TF | BODIES | 1m-5m | drilldown | with parent |
| **FVG** | 3-candle gap of the impulse | **wick-to-wick gap bounds** (c1 wick ↔ c3 wick) | **2H/30m/15m/5m — native TF of the impulse** | impulse | filled / inverted → iFVG |
| **CE line** | FVG/zone midline | 50% | same | drawn explicitly | — |
| **Breaker (BB)** | consolidation bodies under swept high / old demand that broke | BODIES | entry TF | after flip | continuation waypoint |
| **Mitigation** | failed lower-high origin after extreme | BODIES | 30m | LH forms | — |
| **Propulsion** | OB-retest candle closing away | its BODY | 5m | on retest | with parent |
| **Entry** | INTERIOR of zone: mid/CE ("ENTRY IN MID OF BLOCK"), nested band, or discount-half of the zone | — | finest TF | retest | — |
| **SL** | 1-2 pts beyond zone BODY edge — NOT beyond the wick extreme (1224 vs 1223.5; 1133 vs 1134.7-body/1125.5-wick; 1870 vs 1859-wick) | — | — | — | — |
| **Target** | opposing liquidity line / opposing OB-FVG / origin swing / fib 100-161.8 (once) | — | — | — | — |
| **Premium/discount** | LOCAL dealing range of the traded structure (multi-month box on 4H; also FRACTAL: discount-half *within* a zone) | — | 4H ctx → zone | — | — |

**THE NESTING GRAMMAR (the method's spine, t28 = canonical):**
`1D context (accumulation ellipse) ⊃ 2H OB ⊃ 2H FVG ⊃ 5m OB ⊃ 5m entry band` — up to 5 deep.
Each level: SAME zone re-anchored at lower TF on tighter bodies. Entry only at innermost. Parent zones
are **OB/FVG boxes on HIGHER TFs** — not just range extremes.

**THE SEQUENCE GRAMMAR (~20 trades explicit):**
`liquidity line → sweep (wick-through-close-back) → BOS (sometimes double cascade) → zone at origin
(OB/FVG/breaker/mitigation) → retest entry (interior) → target = opposing liquidity`.

## B. GAPS — visual truth vs detector code (ranked by fidelity impact)

| # | gap | visual truth | code truth | sev | surgical fix |
|---|---|---|---|---|---|
| **G1** | **HTF zone parents missing** | nesting parents = OB/FVG on 2H/30m/15m (t28/t29/t30) | ob_taught/fvg_n/fvg run tf=5m ONLY; htf_nest parents = EXT bands only (the "STARVED" note) | **CRIT** | multi-TF param: ob_taught+fvg_n accept `timeframes:[...]`, internal tracker per TF; htf_nest counts same-dir HTF OB/FVG zones containing base → real nest_depth |
| **G2** | **FVG native TF** | drawn on the impulse's own TF: 2H/30m/15m/5m | fvg tf=5m, fvg_n tf=5m | **HIGH** | same multi-TF param as G1 |
| **G3** | **sweep localization** | marked AT the poke candle | sweep Evidence fires on level-state transition at close/reclaim (B9: 13% on-poke) | HIGH | emit meta poke_ts/poke_price = the wick bar; SL anchoring + grading read poke not fire-bar |
| **G4** | **runway/target menu** | targets = opposing liquidity LINES (EQH/EQL), opposing OB/FVG, origin swing | decision._runway = nearest far opposite EXT mid only | MED | _runway candidates += EQH/EQL pools + far opposing live zones; keep nearest-far selection |
| **G5** | **zone-internal p/d entry** | entry in discount-half of a bullish zone ("fvg entry" box, lower half) | entry = _mid(zone) (50%) | MED | optional entry_depth param 0.25-0.5; GATE before ship |
| **G6** | OB far-edge wick variants | parent/outer boxes sometimes take wick on the protected side (t21/t29 bottoms) | bodies-only frozen (TUNE +3.46..+3.83) | LOW | leave frozen; parent-TF boxes may use wick far-edge later |
| **G7** | extreme line pre-confirmation | 1234.34 line drawn while high still pending | extremes emits only confirmed pivots (B1; broad fix REJECTED) | MED | only surgical re-attempt later; NOT now |
| **G8** | wyckoff spring volume gate | schematics mark Spring/UTAD by structure, no volume note | code requires vol>1.5×SMA | LOW | measure recognition delta with vol gate off before touching |
| **G9** | BOS as band | drawn as line AND thin rect | structure emits swing-mid ±tick zone | OK | no change |
| **G10** | invalidated-zone lesson | broken OB kept, relabeled | step_zone flip BRK/MIT | OK | concept matches |

**MATCHES (no gap):** entry=mid ✓ · bodies-box OB ✓ · wick-to-wick FVG bounds ✓ · break-depth
invalidation ✓ · breaker/mitigation flip logic ✓ · propulsion parent-link ✓ · EQ clustering ✓ ·
sequence gate (sweep→BOS→retest) ✓ present as ob_taught gates.

## C. TEST LADDER (per fix — fidelity first, edge gate second)
1. RECOGNITION: does the detector now draw what the human drew on the SAME chart? (co-locate vs obs
   notes: t28 nest stack, t30 fvg, T13 OB, t24 sweep — exact price/candle match)
2. FIRING SANITY: counts per TF, warm-up, dedup (study --only, evidence.parquet)
3. EDGE GATE: ab_tradebook — hi≥5 net-R holds/improves + all 4 quads + walk-forward windows +. Else revert.

## D. QUESTIONS FOR USER (screenshots don't disambiguate)
1. **OB far edge**: entry boxes = bodies (clear). But parent/outer OB bottom sometimes at WICK
   (t21, t29 yellow). Rule: outer zone far-edge = wick, inner refined = bodies?
2. **SL rule for the bot**: screenshots show SL 1-2pt beyond zone BODY edge (inside the sweep wick) —
   but your live note says "ALL SL TAKEN BY BANK". Bot rule: body-edge+buffer, or beyond sweep wick?
3. **Target priority order** when several exist: opposing liquidity line vs opposing OB/FVG vs fib ext?
4. **Entry depth**: mid/CE (50%) vs discount-half (25%) vs nested-band edge — rule per zone type, or
   "deepest available refinement wins"?
5. **Which TFs are canonical parents**? seen: 1D context, 2H/30m/15m parents, 5m entry, 1m refinement.
   Fixed ladder or instrument-dependent?
