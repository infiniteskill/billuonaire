# Recognizer audit: parity is not lineage

JUnit: `{"errors": 0, "failures": 0, "path": "dev/CODEX/researcher_a/output/recognizer_tests.xml", "present": true, "skipped": 0, "tests": 193}`

| recognizer | test/reference parity | causal timing | strict lineage |
|---|---|---|---|
| HTF/M5 swings | unit-contract | PASS | CONDITIONAL |
| external liquidity | unit-contract | PASS | PASS_TO_LEVEL |
| sweep/reclaim | unit-contract + LevelEngine tests | PASS | PASS_TO_LEVEL |
| BOS/CHOCH | unit-contract | PASS | FAIL_STRICT |
| FVG/IFVG | unit-contract | PASS | PASS_TO_FVG_LEVEL |
| close-beyond FVG | real-data reference parity | PASS | CONDITIONAL |
| generic order block | unit-contract | PASS_WITH_MOVING_WINDOW | FAIL_STRICT |
| Lux order block | real-data reference parity | PASS | CONDITIONAL |
| generic breaker | unit-contract | PASS | CONDITIONAL |
| MSB breaker block | real-data reference parity | PASS | INTERNAL_PASS_EXTERNAL_FAIL |
| propulsion block | unit-contract | PASS | FAIL_STRICT |
| mitigation block | real-data reference parity | PASS | FAIL_STRICT |
| shared level state/freshness | state-machine unit-contract | PASS_WITH_RESTART_CONDITIONS | SCHEMA_FAIL |

## HTF/M5 swings

Source: `app/trader/detectors/swings.py` (`01f97dde340a`)

- Strict symmetric window over fully closed candles; confirmation occurs only after N right bars.
- Level.born is pivot time, not confirmation time; Level has no confirmed_at or parent/origin metadata.
- Downstream code must reconstruct confirmation lag to avoid treating the pivot as known early.

## external liquidity

Source: `app/trader/detectors/liquidity.py` (`855e22a1ee91`)

- PDH/PDL, prior-week, opening-range and EQ levels have stable level_id values.
- EQ grouping consumes only already-confirmed swing Levels.
- The detector does not distinguish external/important H1 swings; that importance gate is a research-layer definition.

## sweep/reclaim

Source: `app/trader/detectors/sweep.py` (`65064ccbf836`)

- Sweep and upgrade are keyed to exact level_id and SWEPT state timestamp.
- Reclaim upgrade requires the LevelEngine transition inside the configured closed-bar window.
- Episode base memory is instance-only and is cleared at session end/restart, so replay/live restart parity is conditional.

## BOS/CHOCH

Source: `app/trader/detectors/structure.py` (`b4312e763449`)

- Break evidence records the exact swing_id and uses closed-candle close breaks.
- CHOCH strength boost scans every Level.state_history, without filtering the level timeframe, kind, direction or same root episode.
- BOS/CHOCH does not require a displacement body, close location, or an FVG/OB born from the same break.
- All historical swing Levels are considered regardless of terminal state.

## FVG/IFVG

Source: `app/trader/detectors/fvg.py` (`73049e90788e`)

- Three-closed-candle creation and IFVG inversion are keyed to exact FVG level_id and inversion timestamp.
- Generic FVG evidence episodes clear each session, allowing a carried zone to fire again; this is not first-lifetime-touch freshness.
- The shared Level stores origin bar as born but no explicit c3 confirmation time or parent structure-break id.

## close-beyond FVG

Source: `app/trader/detectors/fvg_cb.py` (`6c8287e0a748`)

- Actual c3 timestamp is separately retained and same-c3 entries are excluded.
- Real-data gap/event parity is tested against the durable reference.
- Session-end deliberately clears retest/CE dedupe so carried levels re-fire; reference-continuum parity test documents this as the sole divergence.

## generic order block

Source: `app/trader/detectors/orderblock.py` (`d5d3db765d20`)

- An opposite candle plus close displacement can form an OB without a causal swing break/BOS/CHOCH.
- Evidence carries level_id but no source swing_id, break timestamp, displacement event id or parent FVG id.
- Historical candidates in the small rolling window are thresholded with current ATR, not their own-bar ATR.

## Lux order block

Source: `app/trader/detectors/ob_lux.py` (`7b1e0ece11cb`)

- Incremental pivot-break-anchor state and real-data birth parity are strongly tested.
- The internal pivot/confirm/anchor relationship is not serialized into Level or Evidence; downstream sees only level_id.
- It is parity to one LuxAlgo OB definition, not proof that it belongs to a separate liquidity-sweep event.

## generic breaker

Source: `app/trader/detectors/breaker.py` (`c735b2e18103`)

- Retest is tied to exact level_id and latest INVERTED episode.
- Eligible parents include OB, swing and opening-range Levels, so the label does not guarantee a swept-OB-to-MSS breaker lineage.
- No root sweep id or structure-break id is carried downstream.

## MSB breaker block

Source: `app/trader/detectors/breaker_msb.py` (`f6a54666c1ab`)

- The stateful zigzag -> swept older swing -> MSB -> breaker box -> later retest chain is internally ordered and parity-tested.
- Evidence metadata omits box id, source swing ids and MSB id, so it cannot be joined strictly to an external HTF root downstream.

## propulsion block

Source: `app/trader/detectors/propulsion_block.py` (`e20061d7a0da`)

- Tap is checked only against live parent OBs and confirmation occurs on a later bar.
- Pending and confirmed blocks are keyed only by (tap timestamp, direction), not parent level_id; same-side parents can overwrite one another.
- Confirmed blocks retain no parent reference and are not invalidated when the parent OB later becomes terminal.

## mitigation block

Source: `app/trader/detectors/mitigation.py` (`f30d4f07cb76`)

- Candidate formation uses the block candle's causal ATR and real-data parity is tested.
- It is a standalone displacement block with no root sweep, structure break, FVG or parent level id.
- Touch metadata exposes no block timestamp/id, so downstream cannot prove same-event ancestry.

## shared level state/freshness

Source: `app/trader/models/level.py` (`efb05a235b24`)

- State history timestamps transitions, but Level schema has no confirmed_at, parent_id, root_event_id, origin_break_id, first_touch_at or invalidation reason.
- A strict ordered strategy therefore cannot be proven from shared Level objects alone; it needs a lineage ledger such as the isolated study emits.

## Audit conclusion

The current tests can all pass while a combined strategy still lacks same-event ancestry. Generic structure, OB, propulsion and mitigation outputs must not be joined merely because timestamps/directions/zones are nearby. The isolated study therefore reconstructs one explicit root_id -> H1 break -> parent -> first revisit -> M5 MSS -> child -> fill ledger.
