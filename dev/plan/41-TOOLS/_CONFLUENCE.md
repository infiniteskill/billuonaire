# _CONFLUENCE — the taught co-fire map (2026-07-23)

Synthesis of all 14 tool validations (`41-TOOLS/*.md`) against the reasoning
engine (`33-DECISION-TREE.md`). The taught method is **not** any single detector
firing — it is a **stack of tools that must CO-FIRE at one price, in one order**,
each either the *anchor* (draws the price object) or the *confirmer* (says the
object is tradeable now). This doc names that stack, its firing order, the
anchor/confirmer at each node, and the **weakest links** that gate the whole thing.

Guardrail carried from every source doc: this is a **RECOGNITION/wiring** map, not
an edge claim. `pct_match` = how faithfully a tool reproduces the user's hand-mark.

---

## 0. The one insight

Every node's anchor is the **same object**: the `extremes.py` percent-leg pivot
(`EXT_H`/`EXT_L`, wick-band, master ranks — the taught anchor since commit 8dc7cc8).
Every node's confirmer is an **event/gate** on that anchor (sweep, BOS, phase,
premium/discount, maturity). The taught setup is a **confluence STACK**: N tools
resolving to the *same price* = stack depth = the grade. A trade is only as strong
as the **weakest confirmer in its stack** — and two whole layers of the stack (the
HTF context top, the runway bottom) currently score ~0%, so **no complete taught
stack can co-fire end-to-end today.** The middle fires; the gates that give the
method its selectivity do not.

---

## 1. What must CO-FIRE for ONE valid taught setup

A valid taught LONG (mirror for SHORT) requires **all** of these to resolve at the
same level, top-down:

1. **HTF regime = accumulation / discount** — `wyckoff.htf_phase` (D1) says
   accumulation **AND** `premium_discount` says price ≤ EQ of the master dealing
   range. [directional permission]
2. **A mature marked range** — `extremes` has printed the master `EXT_L`/`EXT_H`
   pair **AND** `compression`/`volume_time` say the range is contracted/mature.
   [the drawable context box]
3. **A liquidity sweep of the low EXT** — `liquidity` has a pool ON that `EXT_L`
   **AND** `sweep` fires wick-through-close-back on it. [the trigger + bias]
4. **BOS up** — `structure` closes through the last EXT-anchored shelf. [sweep→BOS
   = the birth gate]
5. **A decisional zone born in that displacement leg** — one of
   `ob_taught`/`fvg`/`breaker`/`mitigation`/`propulsion`, **fresh**, located in
   **discount** (demand) / **premium** (supply), not deep-broken. [the entry object]
6. **Refined on a finer TF** — `htf_ltf_nesting`/internal-OB/`fvg_n` nests the entry
   inside the parent; entry = **CE (mid)** of the innermost tier, SL = beyond the
   **outer wick** of the base / the swept extreme. [the tight entry + stop]
7. **Clean runway ≥ target R** — a far `liquidity` pool / opposite master EXT /
   unfilled `fvg` (FVG-as-target) gives magnitude. [the magnitude gate]

Steps 3+4 together are the **sweep→BOS birth gate**; step 5's zone is only valid if
it is born *inside* that gated leg. Steps 1+2+7 are the context/magnitude gates that
convert a mid-tape pattern into a *taught* setup — they are exactly the missing 0%
layers.

---

## 2. Firing ORDER — node by node (anchor · confirmer · gating pct)

| # | Node (tree) | ANCHOR (draws the object) | CONFIRMER (gates it now) | gating pct_match | status |
|---|---|---|---|---|---|
| 0 | **HTF phase / macro context** | `wyckoff` htf_phase / macro range box | `compression` maturity · `volume_time` (bars×height) | **wyckoff 0% · compression 0% · volume_time 0%** | UNBUILT — no HTF box, no range-box, no maturity meter |
| 1 | **Premium / discount gate** | `extremes` **master EXT pair** → range+EQ | `premium_discount` (side classifier) | **p/d 100% (n=2, spec only)**, ← `extremes 58.6%` | detector does NOT exist; robust only on deep HTF extremes |
| 2 | **Liquidity + sweep (trigger)** | `extremes` `EXT_H/EXT_L` → `liquidity` pool | `sweep` (wick-through-close-back) | **liquidity 5.9%** · sweep 83.3% | wire BROKEN both joints — see §4 |
| 3 | **Structure (BOS/CHoCH) = birth gate** | `extremes` (broken shelf) | `structure` (close-through event) | **structure 50%** (over-fires 8:1 on fractal) | anchored on wrong swings |
| 4 | **Decisional zone (entry)** | `ob_taught` box / `fvg` gap | `breaker` (flip) · `mitigation` (No-Break) · `propulsion` (launch) | **breaker 85.7% ▸ fvg 50% ▸ ob 35.5% ▸ mit 11.1% ▸ prop 0%** | births mid-structure, carries NO sweep/BOS gate |
| 5 | **Refine (finer-TF nest)** | innermost LTF origin (`htf_nest`/internal-OB/`fvg_n`) | `nest_depth` | **htf_ltf_nesting 0%** | no nesting detector; 2H/30m/10m TFs don't exist |
| 6 | **Runway / target (magnitude)** | opposite master EXT / far `liquidity` pool / unfilled `fvg` | ≥ target R | **liquidity 5.9%** (no target-role) · fvg (no FVG-as-target) | magnitude gate essentially unbuilt |
| 7 | **Grade + manage** | stack depth (dedup) | maturity · parent-link · runway-R | compression/volume_time 0% | grade inputs missing |

**Reading the order:** context (0-1) → trigger (2-3) → entry (4-5) → magnitude (6) →
grade (7). The tree recurses: node 5 is the *same tree* re-run at a finer TF for the
entry. Direction is set once, at node 2 (high-sweep→short, low-sweep→long), and every
later node must agree with it (a zone whose local direction inverts the sweep bias —
`mitigation` LONG inside a SHORT supply — is the mid-air failure signature).

---

## 3. Anchor vs confirmer — the invariant

- **ANCHOR is always extremes-derived.** The pool (node 2), the range+EQ (node 1),
  the broken shelf (node 3), the zone's grade (node 4), the target (node 6) are all
  meant to hang off `EXT_H/EXT_L`. `extremes` emits the correct object (wick-band =
  outer-wick SL reference for free; `master`/`rank_atr` meta).
- **CONFIRMER is always an event/gate.** `sweep` (SWEPT transition), `structure`
  (close-through), `wyckoff`/`premium_discount` (regime/side), `compression`/
  `volume_time` (maturity). Confirmers never draw the price object — they license it.
- **The entry family (node 4) is interchangeable** — OB ≈ FVG ≈ breaker ≈ mitigation
  ≈ propulsion are one slot (t26: "FVG-as-zone = OB-as-zone"). They differ only in
  *how the zone was born*: plain origin (OB), imbalance (FVG), flip-after-Break
  (breaker), retest-No-Break (mitigation), parent-launch (propulsion). Pick the box
  from the tightest (`ob_taught` bodies) and the birth-gate from the strictest
  (`breaker_msb` sweep gate).

---

## 4. The systemic root cause — the EXT wire is half-built

One defect explains the four worst WIRED links at once. `extremes.py` produces the
taught anchor, but its consumers still read **fractal SWING** furniture:

- `sweep._SIDE_BY_KIND` (`levels.py:80-89`) has **no `EXT_H/EXT_L`** → `sweep.py:50`
  skips them → **the taught anchor is not sweepable** (sweep only reaches marks via
  the SWING fallback). *(sweep P1, extremes P3)*
- `liquidity` has **no EXT pool family** (`_create_eq` sources `SWING_H/SWING_L`) →
  every lone-extreme pool is unreachable → **5.9%**. *(liquidity P1/P2)*
- `structure.detect()` (`L48`) grades BOS/CHoCH against **fractal SWING**, not EXT →
  **8:1 over-fire**, latches minor pivots. *(structure P1)*
- `premium_discount` needs the **master EXT pair** to even define the range —
  it does not exist yet.
- `ob_taught` reads EXT (`_PIV`) but **only as a grade** (`maxd=any`), never a gate.

**Highest-leverage single fix:** add `EXT_H:"below", EXT_L:"above"` to
`_SIDE_BY_KIND` + an EXT pool family in `liquidity` + EXT-anchoring in `structure`.
That one wire simultaneously lifts liquidity (node 2), makes the taught anchor
sweepable (node 2), de-noises structure (node 3), and unblocks premium_discount
(node 1) — four nodes from one change. Because `extremes._band` is already the outer
wick, it also hands every downstream node the **outer-wick SL** the whole method
rests on (the object the measured null never tested, RETHINK §D2).

Second systemic defect: **the entry family births with no sweep/BOS gate** (node 4).
`ob_taught` (138-159 births/window), `mitigation` (60/11d), `propulsion` (504→50→23
vs 1 mark), `fvg` (4/session vs 1) all over-fire because they collapse the chain into
a local rule and never consume the node-2/3 confluence. Recall is ~100%; **precision
is the gap.** Gate node-4 birth on an upstream `sweep`+`structure` event within N bars
+ `pivot_dist_atr ≤ gate` of an EXT, and the family's births collapse toward O(1).

---

## 5. Weakest links — what gates overall accuracy (ranked)

Because a valid stack needs **every** node to fire, overall accuracy is capped by the
weakest confirmer in each co-firing chain (a serial AND, not a max).

**Tier 0 — structurally ABSENT (0%), and they are the TOP and BOTTOM of the tree:**
- `wyckoff` 0%, `compression` 0%, `volume_time` 0% — **node 0** (HTF phase / range
  maturity). No macro box, no range-box, no maturity meter exist.
- `htf_ltf_nesting` 0% — **node 5** (refine). No nesting detector; 2H/30m/10m TFs
  aren't even in the enum.
- `propulsion` 0% — **node 4** confirmer. 11/15 marks are projection *lines* the box
  detector can't draw; the block path over-fires and inverts direction.
- **Consequence:** the context gate (node 0), the refine (node 5) and the runway
  (node 6, via liquidity) are near-zero, so **the selectivity the taught method lives
  in cannot be expressed** — only the middle (sweep→BOS→zone) is functional.

**Tier 1 — WIRED but crippled, and they sit on the critical path:**
- `liquidity` **5.9%** — the single most damaging wired link: it is leg-0 (the pool)
  AND the target (node 6), and it can place neither (no EXT family; `eq_tolerance`
  0.1% splits the user's 0.15-0.2% rails; no target/SL role).
- `mitigation` **11.1%** — body-only sliver zones never retested; mid-air direction
  inversion.
- `ob_taught` **35.5%** — the primary entry object; recall ~100%, **precision is the
  gap** (no birth gate, bodies-only box, no CE entry, body-edge SL).

**Tier 2 — functional, high pct, the load-bearing middle:**
- `structure` 50% (fixable to much higher via EXT anchor), `fvg` 50%,
  `extremes` 58.6% (the anchor everything needs — its K-clip floor of ~6-8% drops the
  1-3% intraday swings, so even the anchor under-fires at LTF), `sweep` 83.3%,
  `breaker` 85.7% (the strongest real detector — sweep-gated by construction).
- `premium_discount` 100% is on n=2 and is spec-only; treat as unbuilt.

**The binding constraint:** overall = min over the stack. With node 0 ≈ 0 and
node 6 ≈ 6%, the *end-to-end taught pct is ~0 regardless of the strong middle.* The
fastest path to a firing stack: (a) the EXT wire (§4) lifts liquidity/sweep/structure/
premium_discount together; (b) build the two missing context detectors (HTF wyckoff
box @ `range_atr≈6`, `range_box` aggregator) so node 0 exists; (c) add the sweep+BOS
birth gate to the node-4 family so precision replaces over-fire. Those three moves
convert the tree from "strong middle, no gates" to a stack that can actually co-fire.
