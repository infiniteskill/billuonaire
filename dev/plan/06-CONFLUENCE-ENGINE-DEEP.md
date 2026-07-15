# Confluence Engine — Deep Design (problem → solution)

The decision core. Everything else feeds this. Ten problems, each solved concretely.

---

## §1 Problem: fuse heterogeneous evidence into ONE accurate decision

Flat weighted sums lie: 10 weak signals scattered across prices can outscore 3 strong
signals stacked at one price. Confluence is **spatial** — it happens AT a price, in A
direction, at A time.

**Solution: 4-layer scoring.**

```
Layer 0  DETECT    per-TF detector runs → Evidence(tf, direction, zone, strength, ttl)
Layer 1  CLUSTER   overlapping zones → ConfluenceZone objects (spatial stacking)
Layer 2  ALIGN     cross-TF narrative fit (multiplicative, not additive)
Layer 3  CONTEXT   time × template × obviousness multipliers → final 0–100
```

**Layer 1 — zone clustering.** Sweep-line over price: Evidence zones overlapping (or
within `merge_atr: 0.25` × ATR) merge into `ConfluenceZone`:

```python
@dataclass
class ConfluenceZone:
    zone: tuple[Decimal, Decimal]        # merged extent
    direction: Direction                  # net (conflicts subtract, see below)
    members: list[Evidence]               # who stacked here
    raw: float                            # Σ weight_i × strength_i (enabled-renormalized)
    distinct: int                         # distinct detector count
```

Rules: same-detector duplicates in one zone count once (best strength). Opposing-direction
evidence in the same zone **subtracts** at 0.8× (a contested zone is worth less than an
uncontested one, but the stronger side still owns it). Arming requires
`distinct >= min_zone_detectors (3)` — axiom 22: nothing trusted standalone.

**Layer 2 — alignment (see §2).** **Layer 3 — context:**

```
final = zone.raw × align_mult × time_mult × template_mult × obviousness_mult
time_mult        = 1 - danger(bucket)                    # timestats, learned
template_mult    = 1.0 matched play / 0.5 off-template / 0.0 UNCLASSIFIED
obviousness_mult = see §8
```

Enter when `final ≥ threshold (65)` AND all gates pass. Every component logged to journal —
each trade's score fully decomposable post-mortem, else learning (§10) is impossible.

---

## §2 Problem: multi-timeframe fitting — TFs contradict each other

M5 says long, H1 says markdown. Who wins? Docs' answer ("weight by TF") is mush.

**Solution: TFs get ROLES, not weights.**

| TF | Role | Power |
|---|---|---|
| D1 | REGIME | veto only — HTF Wyckoff markdown blocks all longs (the 3-month-underwater defense). Never generates entries |
| H1 | BIAS | direction filter — release direction must match or H1 must be neutral-ranging |
| M15 | SETUP | where ConfluenceZones live; the tradeable structure |
| M5 | TRIGGER | confirmation inside zone (§4) |
| M1 | FILL | execution timing only |

`align_mult`: full agreement (D1 allows + H1 agrees + M15 zone directional) = 1.0;
H1 neutral = 0.8; H1 disagrees = 0.0 (**multiplicative zero — no trade**, not a discount).
This is why alignment is a product: one broken link kills the chain, exactly how nested
traps work (axiom 3: countermoves co-exist per TF — the higher TF's move IS the lower
TF's context).

---

## §3 Problem: Power of Three — detect ACC→MANIP→DIST live, per TF

PO3 is a narrative; narratives aren't computable. Make it a state machine with
measurable transitions.

**Solution: PO3 FSM, one instance per (symbol, scale).**

Two scales: DAY (opening range = accumulation box) and LEG (any compression box, §5).

```
ACCUMULATION: box forms — range < range_atr×ATR for ≥ min_box_candles,
              volume contracting (vol-slope < 0)
    → MANIPULATION: box edge swept (wick beyond + close back inside/reclaim)
              direction_of_manipulation = sweep side
    → DISTRIBUTION: displacement > 1.5×ATR AWAY from sweep side + BOS on M15
              true_direction = opposite of manipulation      ← tradeable state
    → (new box forms → back to ACCUMULATION at next scale/leg)
FAILURE PATHS: box breaks WITH volume expansion and no reclaim → not manipulation,
              it's TREND continuation → hand to template classifier as TREND evidence
```

Evidence: DISTRIBUTION confirm = strength 0.85 in true_direction (one of the two
strongest signals with breaker). MANIPULATION state = Evidence NEUTRAL "arm-soon" marker
feeding the entry FSM (§4). PO3-DAY state also drives template classification —
judas_reversal IS PO3-DAY where the box = opening range.

---

## §4 Problem: entry precision — small SL needs exact entry, not "zone entered, buy"

Market-buying when price touches a zone = wide effective stop + hunted.

**Solution: 3-stage entry FSM per armed zone.**

```
ARMED    zone scored ≥ threshold, gates pass, price approaching (within 1×ATR)
         → posts limit intent at zone CE (50% of zone)
TRIGGER  price INSIDE zone AND M5 confirmation fires:
           rejection wick ≥ 60% of candle range off zone, OR
           M5 CHoCH inside zone, OR
           VSA stopping-volume/absorption bar inside zone
         no trigger + zone violated (close beyond far edge + wick_tolerance) → DISARM
         armed > arm_ttl_candles (12 M5) without touch → EXPIRE
FILL     market order on trigger-candle close
         SL = beyond zone far edge + trap extreme + atr_buffer, off round numbers
         effective risk ≈ zone height + buffer  → small BY CONSTRUCTION
```

Chase protection (axiom 10/25): if trigger candle closes beyond zone + `chase_tolerance_atr`,
entry SKIPPED — journaled `skip: chased_away`. Missing a runner is a zero-cost event;
entering late is a paid one. DISARM also fires if the zone's OB Level breaks (axiom 28) —
then breaker detector inherits the zone.

---

## §5 Problem: compression candles — coiled energy, where and when it releases

**Solution: compression detector (new, Phase 3).**

Detection over last `window: 12` candles per TF:
```
contraction = mean(range[last 4]) / mean(range[first 4])      # < 0.6 ⇒ compressing
overlap     = intersection of last 6 bodies > 0                # bodies stacking
vol_slope   = linreg slope of volume                           # < 0 ⇒ quiet
NR-cluster  = ≥2 of last 4 candles are narrowest-of-7 (NR7) or inside bars
compression_score = weighted mix, ≥ 0.7 ⇒ compression box confirmed
```

Outputs:
1. **Box** = high/low of compressed cluster → registered as PO3 ACCUMULATION box (§3):
   first break is suspected manipulation, not signal. Never trade compression breakout
   directly — trade its FAILURE (sweep-reclaim) or post-BOS retrace.
2. **Energy metric**: `expected_expansion = box_height × expansion_factor (2.5, learned)`
   → feeds target selection (§6): targets beyond expected expansion get probability haircut.
3. **Location quality**: compression sitting ON a hunt-born OB / HTF FVG = loaded spring —
   Evidence strength 0.75 in the zone's direction once §3 reaches DISTRIBUTION; compression
   in the middle of nowhere = 0.3 context marker only.

---

## §6 Problem: exits & targets — where does the move actually die

Fixed 1.5R/2.5R/4R is blind: sometimes 4R sits beyond an OI wall (never reached),
sometimes liquidity sits at 6R (money left).

**Solution: targets = OPPOSING confluence map.** Same Layer-1 clustering, opposite
direction: unswept liquidity pools, opposing OI wall, opposing HTF FVG midpoints, PDH/PDL.

```
T1 = nearest opposing cluster ≥ 1.5R   (if nearest < 1.5R → trade SKIPPED — no room)
T2 = next cluster / cage edge
T3 = external liquidity (PDH/PDL/PWH/PWL), capped at compression energy bound (§5)
partials: 33% at T1 + SL→breakeven, 33% at T2, run T3
```

**Early-exit triggers** (before stop): opposing ConfluenceZone forms ≥ threshold against
position (new counter-trap detected — axiom 2: our winner becomes their trap) → exit at
market. Time-stop: < 0.5R progress after `stall_candles: 18` (M5) → scratch — capital and
attention freed; dead trades are where hunts find you.

---

## §7 Problem: trailing — trail tight = wicked out, trail loose = give back

**Solution: TF-promotion ratchet + hunt awareness.**

```
phase 1 (< 1R):    initial SL, untouched. No trailing — noise zone
phase 2 (≥ 1R):    SL → breakeven + costs. partial 1 off
phase 3 (≥ 2R):    trail behind M5 swing (last confirmed swing ± 0.1×ATR)
phase 4 (≥ 3R):    trail behind M15 swing — as trade matures, protection widens to
                   match the TF now moving it (winners graduate to slower structure)
always:            stealth (software), close-confirmed breach, wick_tolerance 1 candle,
                   ratchet only (never widen — hard invariant, tested)
EOD:               squareoff 15:10 regardless
```

Ratchet levels also snap off round numbers and away from freshly obvious swing points
(same anti-hunt placement rules as entry SL).

---

## §8 Problem: obvious setups are bait (axioms 22–24)

The prettier the pattern, the more retail is in it, the more profitable it is to hunt.

**Solution: obviousness score → multiplier.**

```
obviousness = mean of:
  level_visibility   pool touches ≥3, round number, PDH/PDL      (everyone sees it)
  pattern_textbook   compression→breakout, triangle-clean EQH    (everyone learned it)
  direction_crowded  breakout direction == retail momentum direction
obviousness_mult = 1.0 (< 0.5) | 0.85 (0.5–0.7) | 0.6 (> 0.7) applied to BREAKOUT-style
                   evidence only
INVERSION: obvious level SWEPT then RECLAIMED → obviousness flips to bonus ×1.15 —
           the trap fired and failed; trapped crowd is now fuel for our direction.
```

Post-hunt entries at obvious levels are the best entries. Pre-hunt entries at obvious
levels are donations. Same level, opposite value — state decides, not the level.

---

## §9 Problem: stock finding — system picks the battlefield itself

**Solution: pre-market scanner (auto-fit), runs before 09:15 over the WHOLE stocks.json.**

```
fit = weighted:
  cleanliness  0.25   spread bps, gap frequency (20d), swing-size stddev, ATR stability
  energy       0.20   ATR% in tradeable band 1–4%, compression present on D1/H1
  liquidity    0.20   avg volume, value traded (slippage feasibility for qty)
  setup_ready  0.20   unswept pools near price, hunt-worthy equal H/L, HTF zone proximity
  context      0.15   index alignment, not day-after-TREND giveback risk, no earnings today
```

`trader list` shows ranked fit scores; `trader watch --auto 8` takes top 8 itself.
Intraday re-rank every 30 min: stock that gapped through its structure or went dirty
(spread blowout) gets benched — WATCHING → BENCHED state, no new arms, existing position
still managed. Scanner learns: fit-score components regressed against realized per-stock
expectancy monthly.

---

## §10 Problem: "self-doing everything" — autonomy without self-destruction

**Solution: session state machine + nightly self-audit.**

```
08:45 PREP       load caches, compute levels/cage, scan+rank, arm nothing
09:15 OBSERVE    ingest, detect, classify — entries locked (axiom 9)
11:00 HUNT_DONE  templates locked in, entry FSMs may arm (axiom 8/27)
      TRADE      full pipeline: arm → trigger → fill → manage
14:30 NO_NEW     manage-only
15:10 SQUAREOFF  flatten all, session journal sealed
15:45 AUDIT      nightly self-audit:
        - per-detector health: precision (evidence in winning zones / total), decay-weighted
        - weight nudge: ±10% max/week toward performance (Laplace-smoothed, min 30 samples)
        - detector auto-bench: precision < 0.35 over 100 samples → weight floor 25%,
          flag in report — HUMAN decides kill (self-tuning yes, self-mutilation no)
        - skipped-setup scoring: would skips have won? gate cost/benefit table
        - timestats bucket update, template priors update, scanner regression data
        - report emit: expectancy, PF, DD, hunt-survival rate, per-template PnL
```

Guardrails on the learning itself (from docs' meta-learning, kept minimal): walk-forward
only (never fit on the week being evaluated), weight changes capped, any auto-change
journaled with before/after — the system explains every opinion it forms.

---

## Pipeline assembled (one closed M5 candle, one stock)

```
candle → store → levels update → PO3 FSMs update → detectors (all TFs due)
  → Layer 1 cluster → Layer 2 align → Layer 3 context → zones scored
  → template/gates check → entry FSM (arm/trigger/disarm)
  → position manager (partials/trail/early-exit/time-stop)
  → journal verdict + full decomposition
```

Everything above is detachable-safe: every named detector contributes Evidence only;
removing one shrinks `members`/`distinct` and renormalizes weights — thresholds like
`min_zone_detectors` and the multiplicative layers (alignment, time, template) work
unchanged over whatever remains.
