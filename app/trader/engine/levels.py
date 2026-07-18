"""Level state machine (LevelEngine) + JSON persistence (LevelStore).

Every sweep/breaker/reversal signal in the trap-detection model derives from
the transitions produced here, so the semantics are spelled out exactly.

Side mapping
============
The "origin side" of a level is the side price normally sits on relative to
the zone. It is derived from the kind (explicit table below); ROUND is
side-less, so its side is taken from where price was on first evaluation
(previous candle close, falling back to the candle's open) and then cached
for the level's lifetime.

    side == "below" (price below zone; resistance-ish):
        PDH, PWH, EQH, SWING_H, OPEN_RANGE_H, OI_WALL_CE, OB_BEAR, FVG_BEAR
    side == "above" (price above zone; support-ish):
        PDL, PWL, EQL, SWING_L, OPEN_RANGE_L, OI_WALL_PE, OB_BULL, FVG_BULL
    ROUND: from reference close (inside the zone -> nearest half by midpoint)

Edges: for a side=="below" level, near edge = zone_lo and far edge = zone_hi
(the edge away from price). Mirrored for side=="above".

Transition rules (one closed candle; AT MOST ONE transition per level per
candle; precedence DEAD-confirm > SWEPT > RECLAIMED > INVERTED > TESTED)
=======================================================================
ACTIVE -> TESTED
    Candle range intersects the zone expanded by ``touch_atr * atr`` on both
    sides AND close is fully back on the origin side of the near edge.
    ``touches += 1`` on every qualifying touch (also while already TESTED).
    A close *inside* the zone triggers nothing -- the candle is undecided.

ACTIVE/TESTED -> SWEPT
    Wick trades beyond the far edge AND close is fully back on the origin
    side (wick-through-close-back). Starts the reclaim window.

ACTIVE/TESTED -> DEAD (2-candle confirm)
    Close fully beyond the far edge marks engine-internal PENDING_BREAK
    (a dict, NOT a LevelState) and emits nothing. The next closed candle
    resolves it:
        close beyond far edge again      -> DEAD
        close back on origin side        -> SWEPT (break-then-reclaim path;
                                            reclaim window starts here)
        close inside the zone            -> pending cancelled, no transition

SWEPT -> RECLAIMED
    Within ``reclaim_candles`` (default 3) closed candles after the sweep, a
    close fully back on the origin side reclaims the level. If the window
    expires without a reclaim, SWEPT is terminal (documented decision: no
    late reclaims; an engine restart also treats a persisted SWEPT level as
    expired because the window counter is engine memory, not persisted).

RECLAIMED -> INVERTED (breaker seed)
    Close beyond the far edge (through the zone to the other side) held for
    one candle: the next close must also be beyond the far edge. A failed
    hold cancels silently and stays RECLAIMED; later attempts are allowed.

OB_BULL/OB_BEAR: second qualifying test -> MITIGATED instead of staying
    TESTED (order block consumed; dead for entries).

DEAD, MITIGATED and INVERTED are terminal for this engine.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from trader.models.candle import Candle, Timeframe
from trader.models.level import TERMINAL, Level, LevelKind, LevelState

logger = logging.getLogger("trader.engine.levels")

# Explicit side table -- keep in sync with LevelKind. ROUND is intentionally
# absent (side-less, resolved per level from the reference close).
_SIDE_BY_KIND: dict[LevelKind, str] = {
    LevelKind.PDH: "below", LevelKind.PWH: "below", LevelKind.EQH: "below",
    LevelKind.SWING_H: "below", LevelKind.OPEN_RANGE_H: "below",
    LevelKind.OI_WALL_CE: "below", LevelKind.OB_BEAR: "below",
    LevelKind.FVG_BEAR: "below",
    LevelKind.PDL: "above", LevelKind.PWL: "above", LevelKind.EQL: "above",
    LevelKind.SWING_L: "above", LevelKind.OPEN_RANGE_L: "above",
    LevelKind.OI_WALL_PE: "above", LevelKind.OB_BULL: "above",
    LevelKind.FVG_BULL: "above",
}

_OB_KINDS = frozenset({LevelKind.OB_BULL, LevelKind.OB_BEAR})


def level_side(level: Level, prev_close: Decimal | None) -> str:
    """Return which side of the zone price normally sits on: "above"|"below".

    ``prev_close`` is only consulted for ROUND levels (side-less kind); for
    a reference close inside the zone the nearest half by midpoint decides.
    """
    side = _SIDE_BY_KIND.get(level.kind)
    if side is not None:
        return side
    if prev_close is None:
        raise ValueError(f"{level.kind.name} level needs a reference close to derive side")
    lo, hi = level.zone
    if prev_close < lo:
        return "below"
    if prev_close > hi:
        return "above"
    return "below" if prev_close <= (lo + hi) / 2 else "above"


@dataclass(frozen=True)
class LevelTransition:
    level_id: str
    old: LevelState
    new: LevelState
    ts: datetime


class LevelEngine:
    """Applies the transition rules above to live Level objects, one closed
    candle at a time. Mutates levels in place (record_state / touches) and
    returns the transitions it made."""

    def __init__(self, params: dict):
        self.touch_atr = Decimal(str(params.get("touch_atr", "0.1")))
        self.reclaim_candles = int(params.get("reclaim_candles", 3))
        # Engine-internal memories (never LevelStates, never persisted):
        self._pending_break: dict[str, int] = {}   # level_id -> candles since close beyond
        self._since_swept: dict[str, int] = {}     # level_id -> closed candles since sweep
        self._pending_invert: dict[str, int] = {}  # level_id -> candles since close through
        self._round_side: dict[str, str] = {}      # level_id -> cached ROUND side
        self._prev_close: dict[tuple[str, Timeframe], Decimal] = {}

    def update(self, levels: list[Level], candle: Candle,
               atr: Decimal | None) -> list[LevelTransition]:
        tol = self.touch_atr * atr if atr is not None else Decimal("0")
        prev_close = self._prev_close.get((candle.symbol, candle.tf))
        transitions = []
        for level in levels:
            if level.symbol != candle.symbol or level.state in TERMINAL:
                continue
            t = self._step(level, candle, tol, prev_close)
            if t is not None:
                transitions.append(t)
        self._prev_close[(candle.symbol, candle.tf)] = candle.close
        return transitions

    def on_session_end(self) -> None:
        """Drop ALL per-run memory at a session boundary. Otherwise a carried
        level (PDH/PDL/PW*/EQ*/ROUND survive _carry_over) swept on day 1's
        last bars keeps a small window/pending counter, so day 2's FIRST bar
        would wrongly resolve it -- reclaim the sweep, confirm a break, hold
        an inversion -- treating the overnight gap as "one candle". Clearing
        also makes a continuous multi-day run match per-day restarts."""
        self._pending_break.clear()
        self._since_swept.clear()
        self._pending_invert.clear()
        self._round_side.clear()
        self._prev_close.clear()

    # ------------------------------------------------------------- internals

    def _side(self, level: Level, candle: Candle, prev_close: Decimal | None) -> str:
        if level.kind is not LevelKind.ROUND:
            return level_side(level, None)
        side = self._round_side.get(level.id)
        if side is None:
            ref = prev_close if prev_close is not None else candle.open
            side = level_side(level, ref)
            self._round_side[level.id] = side
        return side

    def _step(self, level: Level, candle: Candle, tol: Decimal,
              prev_close: Decimal | None) -> LevelTransition | None:
        side = self._side(level, candle, prev_close)
        lo, hi = level.zone
        if side == "below":  # price origin below zone: near=lo, far=hi
            beyond_far = lambda p: p > hi
            on_origin = lambda p: p < lo
            wick_beyond = candle.high > hi
        else:                # price origin above zone: near=hi, far=lo
            beyond_far = lambda p: p < lo
            on_origin = lambda p: p > hi
            wick_beyond = candle.low < lo
        touched = candle.low <= hi + tol and candle.high >= lo - tol
        close = candle.close

        # 1. PENDING_BREAK resolution -- DEAD-confirm has top precedence.
        if level.id in self._pending_break:
            del self._pending_break[level.id]
            if beyond_far(close):
                return self._apply(level, LevelState.DEAD, candle.ts)
            if on_origin(close):
                self._since_swept[level.id] = 0
                return self._apply(level, LevelState.SWEPT, candle.ts)
            return None  # closed inside the zone: break fizzled, level lives

        state = level.state
        if state in (LevelState.ACTIVE, LevelState.TESTED):
            if wick_beyond and on_origin(close):           # SWEPT beats TESTED
                self._since_swept[level.id] = 0
                return self._apply(level, LevelState.SWEPT, candle.ts)
            if beyond_far(close):                          # arm 2-candle confirm
                self._pending_break[level.id] = 0
                return None
            if touched and on_origin(close):               # TESTED (lowest)
                level.touches += 1
                if state is LevelState.ACTIVE:
                    return self._apply(level, LevelState.TESTED, candle.ts)
                if level.kind in _OB_KINDS and level.touches >= 2:
                    return self._apply(level, LevelState.MITIGATED, candle.ts)
            return None

        if state is LevelState.SWEPT:
            n = self._since_swept.get(level.id)
            if n is None:
                return None  # reclaim window already expired: SWEPT terminal
            n += 1
            if n <= self.reclaim_candles and on_origin(close):
                del self._since_swept[level.id]
                return self._apply(level, LevelState.RECLAIMED, candle.ts)
            if n >= self.reclaim_candles:
                del self._since_swept[level.id]  # window expired
            else:
                self._since_swept[level.id] = n
            return None

        if state is LevelState.RECLAIMED:
            if level.id in self._pending_invert:
                del self._pending_invert[level.id]
                if beyond_far(close):                      # held one candle
                    return self._apply(level, LevelState.INVERTED, candle.ts)
                return None                                # failed hold
            if beyond_far(close):
                self._pending_invert[level.id] = 0
            return None

        return None

    @staticmethod
    def _apply(level: Level, new: LevelState, ts: datetime) -> LevelTransition:
        old = level.state
        level.record_state(ts, new)
        return LevelTransition(level_id=level.id, old=old, new=new, ts=ts)


class LevelStore:
    """JSON persistence for levels: ``root/<symbol>/levels.json``.

    Encoding: Decimal -> str, Enum -> name, datetime -> isoformat.
    ``load`` reconstructs Level objects exactly (dataclass equality holds)."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str) -> Path:
        return self.root / symbol / "levels.json"

    def save(self, symbol: str, levels: list[Level]) -> None:
        path = self._path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps([self._encode(l) for l in levels], indent=2))
        os.replace(tmp, path)  # atomic: survive crashes mid-write

    def load(self, symbol: str) -> list[Level]:
        path = self._path(symbol)
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text())
        except json.JSONDecodeError:
            logger.warning(
                "corrupt or empty levels.json for %s at %s; treating as no levels",
                symbol, path,
            )
            return []
        return [self._decode(d) for d in raw]

    def save_watermark(self, symbol: str, ts: datetime) -> None:
        """Persist the last-processed candle ts (watch-resume watermark:
        SymbolPipeline replays rows at/before it into the store only)."""
        path = self.root / symbol / "watermark.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(ts.isoformat()))
        os.replace(tmp, path)  # atomic, like save()

    def load_watermark(self, symbol: str) -> datetime | None:
        path = self.root / symbol / "watermark.json"
        if not path.exists():
            return None
        try:
            return datetime.fromisoformat(json.loads(path.read_text()))
        except (ValueError, TypeError, json.JSONDecodeError):
            logger.warning("corrupt watermark.json for %s at %s; ignoring",
                           symbol, path)
            return None

    @staticmethod
    def _encode(level: Level) -> dict:
        return {
            "id": level.id,
            "symbol": level.symbol,
            "kind": level.kind.name,
            "zone": [str(level.zone[0]), str(level.zone[1])],
            "born": level.born.isoformat(),
            "tf": level.tf.name if level.tf is not None else None,
            "state": level.state.name,
            "touches": level.touches,
            "state_history": [[ts.isoformat(), st.name]
                              for ts, st in level.state_history],
        }

    @staticmethod
    def _decode(d: dict) -> Level:
        return Level(
            id=d["id"],
            symbol=d["symbol"],
            kind=LevelKind[d["kind"]],
            zone=(Decimal(d["zone"][0]), Decimal(d["zone"][1])),
            born=datetime.fromisoformat(d["born"]),
            tf=Timeframe[d["tf"]] if d["tf"] is not None else None,
            state=LevelState[d["state"]],
            touches=d["touches"],
            state_history=[(datetime.fromisoformat(ts), LevelState[st])
                           for ts, st in d["state_history"]],
        )
