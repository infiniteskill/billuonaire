"""CandleStore: multi-timeframe candle storage with no-lookahead views.

Only M1 candles may be added; M5/M15/H1/D1 series are derived by
re-aggregating the affected bucket from its constituent M1 candles on every
add (correct over fast).

Session model (NSE): 09:15-15:30 local wall clock, 375 minutes. All bucket
math is done on the candle's own wall clock, so timestamps are expected to
be session-local (IST) and timezone-aware.

Bucket rule: bucket start = 09:15 + floor((ts - 09:15) / tf.minutes) *
tf.minutes on ts's session day. Because Timeframe.D1.minutes == 375, the D1
bucket is exactly the whole session (start 09:15, closes 15:30) and needs no
special case.

Ordering guarantees:
- Out-of-order adds are inserted at their sorted position (lists are always
  sorted ascending by ts).
- A duplicate add (same symbol + ts) REPLACES the earlier candle
  (last write wins), and every derived bucket containing it is recomputed.

Visibility rule (no lookahead): a candle is visible through a view iff
``candle.ts + timedelta(minutes=candle.tf.minutes) <= now`` -- i.e. only
fully closed candles. For D1 this means the session's 15:30 close.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from datetime import datetime, timedelta
from operator import attrgetter
from pathlib import Path

import pandas as pd

from trader.models.candle import Candle, Timeframe, tick

_TS = attrgetter("ts")
_DERIVED = (Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.D1)
_PRICE_COLS = ("open", "high", "low", "close")


def _bucket_start(ts: datetime, tf: Timeframe) -> datetime:
    """Start of the tf bucket containing ts, anchored at 09:15 of ts's day."""
    session_open = ts.replace(hour=9, minute=15, second=0, microsecond=0)
    offset_min = int((ts - session_open).total_seconds() // 60)
    return session_open + timedelta(minutes=(offset_min // tf.minutes) * tf.minutes)


def _insert_sorted(candles: list[Candle], candle: Candle) -> None:
    """Insert keeping ascending ts order; same-ts duplicate is replaced."""
    i = bisect_left(candles, candle.ts, key=_TS)
    if i < len(candles) and candles[i].ts == candle.ts:
        candles[i] = candle  # duplicate: last write wins
    else:
        candles.insert(i, candle)


class CandleView:
    """Read-only, point-in-time view. NEVER exposes a candle that has not
    fully closed as of ``now`` (see module docstring for the closed rule)."""

    def __init__(self, store: "CandleStore", symbol: str, now: datetime):
        if now.tzinfo is None:
            raise ValueError("view 'now' must be timezone-aware")
        self._store = store
        self._symbol = symbol
        self._now = now

    def _closed(self, tf: Timeframe) -> list[Candle]:
        """All candles of tf closed as of now (ts + tf.minutes <= now)."""
        candles = self._store._data.get(self._symbol, {}).get(tf, [])
        cutoff = self._now - timedelta(minutes=tf.minutes)
        return candles[: bisect_right(candles, cutoff, key=_TS)]

    def _today(self) -> "datetime.date":
        """Session date of 'now', in the tz the candles are stored in."""
        candles = self._store._data.get(self._symbol, {}).get(Timeframe.M1, [])
        tz = candles[-1].ts.tzinfo if candles else self._now.tzinfo
        return self._now.astimezone(tz).date()

    def last(self, n: int, tf: Timeframe) -> list[Candle]:
        """Most recent n fully closed tf candles (oldest first)."""
        return self._closed(tf)[-n:] if n > 0 else []

    def today(self, tf: Timeframe) -> list[Candle]:
        """Fully closed tf candles of the current session day."""
        d = self._today()
        return [c for c in self._closed(tf) if c.ts.date() == d]

    def prev_day(self, tf: Timeframe) -> list[Candle]:
        """Fully closed tf candles of the latest session day before today."""
        d = self._today()
        earlier = [c for c in self._closed(tf) if c.ts.date() < d]
        if not earlier:
            return []
        prev = earlier[-1].ts.date()  # list is sorted, so last date is max
        return [c for c in earlier if c.ts.date() == prev]


class CandleStore:
    """Per-symbol candle store. Add M1 only; derived TFs stay consistent.

    Persistence: ``save``/``load`` write one parquet per timeframe under
    ``root/<symbol>/<tf>.parquet``. Prices are stored as strings and
    rehydrated through ``tick()`` so Decimals roundtrip exactly; timestamps
    keep their timezone.
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self._data: dict[str, dict[Timeframe, list[Candle]]] = {}

    def _series(self, symbol: str) -> dict[Timeframe, list[Candle]]:
        return self._data.setdefault(symbol, {tf: [] for tf in Timeframe})

    def add(self, candle: Candle) -> None:
        """Add an M1 candle (raise ValueError otherwise) and recompute the
        M5/M15/H1/D1 buckets that contain it. The timestamp must lie within
        the NSE session of its day: 09:15 <= ts < 15:30 (else ValueError).
        Duplicates replace; see module docstring."""
        if candle.tf is not Timeframe.M1:
            raise ValueError(f"CandleStore.add accepts M1 only, got {candle.tf}")
        session_open = candle.ts.replace(hour=9, minute=15, second=0, microsecond=0)
        session_close = session_open + timedelta(minutes=Timeframe.D1.minutes)
        if not (session_open <= candle.ts < session_close):
            raise ValueError(
                f"M1 ts {candle.ts} outside session 09:15-15:30 of its day"
            )
        series = self._series(candle.symbol)
        _insert_sorted(series[Timeframe.M1], candle)
        for tf in _DERIVED:
            self._recompute_bucket(candle.symbol, tf, candle.ts)

    def _recompute_bucket(self, symbol: str, tf: Timeframe, ts: datetime) -> None:
        """Rebuild the tf bucket containing ts from its constituent M1s."""
        start = _bucket_start(ts, tf)
        end = start + timedelta(minutes=tf.minutes)
        m1 = self._data[symbol][Timeframe.M1]
        members = m1[bisect_left(m1, start, key=_TS): bisect_left(m1, end, key=_TS)]
        agg = Candle(
            symbol=symbol,
            tf=tf,
            ts=start,
            open=members[0].open,
            high=max(c.high for c in members),
            low=min(c.low for c in members),
            close=members[-1].close,
            volume=sum(c.volume for c in members),
        )
        _insert_sorted(self._data[symbol][tf], agg)

    def view(self, symbol: str, now: datetime) -> CandleView:
        """Point-in-time view exposing only candles fully closed by ``now``."""
        return CandleView(self, symbol, now)

    def save(self, symbol: str) -> None:
        """Write each non-empty timeframe to root/<symbol>/<tf>.parquet."""
        sym_dir = self.root / symbol
        sym_dir.mkdir(parents=True, exist_ok=True)
        for tf, candles in self._data.get(symbol, {}).items():
            if not candles:
                continue
            df = pd.DataFrame(
                {
                    "symbol": [c.symbol for c in candles],
                    "ts": [c.ts for c in candles],
                    **{col: [str(getattr(c, col)) for c in candles] for col in _PRICE_COLS},
                    "volume": [c.volume for c in candles],
                }
            )
            df.to_parquet(sym_dir / f"{tf.value}.parquet", index=False)

    def load(self, symbol: str) -> None:
        """Load all timeframes for symbol from parquet, replacing any
        in-memory series for that symbol.

        A derived timeframe (M5/M15/H1/D1) may be absent from disk (e.g. an
        M1-only parquet set). When that happens and M1 data was loaded, the
        missing timeframe's buckets are re-derived from the loaded M1
        candles by reusing ``_recompute_bucket`` (the same logic ``add()``
        uses) -- never left empty, which would make detectors silently see
        empty views.
        """
        sym_dir = self.root / symbol
        series = {tf: [] for tf in Timeframe}
        missing: set[Timeframe] = set()
        for tf in Timeframe:
            path = sym_dir / f"{tf.value}.parquet"
            if not path.exists():
                missing.add(tf)
                continue
            df = pd.read_parquet(path)
            series[tf] = sorted(
                (
                    Candle(
                        symbol=row.symbol,
                        tf=tf,
                        ts=row.ts.to_pydatetime(),
                        open=tick(row.open),
                        high=tick(row.high),
                        low=tick(row.low),
                        close=tick(row.close),
                        volume=int(row.volume),
                    )
                    for row in df.itertuples(index=False)
                ),
                key=_TS,
            )
        self._data[symbol] = series
        m1 = series[Timeframe.M1]
        if m1:
            for tf in _DERIVED:
                if tf in missing:
                    for candle in m1:
                        self._recompute_bucket(symbol, tf, candle.ts)
