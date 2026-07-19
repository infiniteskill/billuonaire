"""CandleStore: multi-timeframe candle storage with no-lookahead views.

Only M1 candles may be added; M5/M15/H1/D1 series are derived by
re-aggregating the affected bucket from its constituent M1 candles on every
add (correct over fast).

Session model comes from a MarketSpec (default NSE: 09:15-15:30, 375 min).
Bucket math is on the candle's own wall clock, so timestamps must be
session-local and timezone-aware. Bucket start = session_open +
floor((ts - session_open) / tf_minutes) * tf_minutes on ts's session day;
D1's duration is spec.session_minutes, so its bucket is the whole session.

Ordering guarantees:
- Out-of-order adds are inserted at their sorted position (lists are always
  sorted ascending by ts).
- A duplicate add (same symbol + ts) REPLACES the earlier candle
  (last write wins), and every derived bucket containing it is recomputed.

Visibility rule (no lookahead): a candle is visible through a view iff
``candle.ts + its tf duration <= now`` -- i.e. only fully closed candles.
For D1 this means the session close.

Completeness rule (audit 5, fail-closed): a derived bucket holding fewer M1
members than its span expects (session-close truncation respected: the last
bucket of a session expects fewer) is INCOMPLETE -- kept in the store, but a
``complete_only`` view excludes it, so detectors never read a feed-gap
candle as a real one. The pipeline builds every detector-facing view with
``complete_only=True``; plain views (tools, tests, last-price reads) keep
raw access. Complete data marks nothing, leaving views bit-identical.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from datetime import datetime, timedelta
from operator import attrgetter
from pathlib import Path

import pandas as pd

from trader.models.candle import Candle, Timeframe
from trader.models.market import NSE, MarketSpec

_TS = attrgetter("ts")
_DERIVED = (Timeframe.M5, Timeframe.M15, Timeframe.H1, Timeframe.D1)
_PRICE_COLS = ("open", "high", "low", "close")


def _tf_minutes(tf: Timeframe, spec: MarketSpec) -> int:
    """Duration of one tf candle; D1 is the market's whole session."""
    return spec.session_minutes if tf is Timeframe.D1 else tf.minutes


def _bucket_start(ts: datetime, tf: Timeframe, spec: MarketSpec) -> datetime:
    """Start of the tf bucket containing ts, anchored at session open."""
    open_, n = spec.session_open_dt(ts), _tf_minutes(tf, spec)
    offset_min = int((ts - open_).total_seconds() // 60)
    return open_ + timedelta(minutes=(offset_min // n) * n)


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

    def __init__(self, store: "CandleStore", symbol: str, now: datetime,
                 complete_only: bool = False):
        if now.tzinfo is None:
            raise ValueError("view 'now' must be timezone-aware")
        self._store = store
        self._symbol = symbol
        self._now = now
        self._complete_only = complete_only

    def _closed(self, tf: Timeframe) -> list[Candle]:
        """All candles of tf closed as of now (ts + tf duration <= now).
        complete_only views additionally drop incomplete buckets (missing M1
        members, audit 5 fail-closed)."""
        candles = self._store._data.get(self._symbol, {}).get(tf, [])
        cutoff = self._now - timedelta(minutes=_tf_minutes(tf, self._store.spec))
        out = candles[: bisect_right(candles, cutoff, key=_TS)]
        bad = self._store._incomplete
        return [c for c in out if (self._symbol, tf, c.ts) not in bad] \
            if bad and self._complete_only else out

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
    ``root/<symbol>/<tf>.parquet``. Prices are stored as strings, rehydrated
    via ``spec.quantize`` (exact Decimal roundtrip); timestamps keep their tz.
    """

    def __init__(self, root: Path, spec: MarketSpec = NSE):
        self.root = Path(root)
        self.spec = spec
        self._data: dict[str, dict[Timeframe, list[Candle]]] = {}
        # derived buckets missing M1 members: kept in _data, hidden from views
        self._incomplete: set[tuple[str, Timeframe, datetime]] = set()

    def _series(self, symbol: str) -> dict[Timeframe, list[Candle]]:
        return self._data.setdefault(symbol, {tf: [] for tf in Timeframe})

    def add(self, candle: Candle) -> None:
        """Add an M1 candle (raise ValueError otherwise) and recompute the
        M5/M15/H1/D1 buckets that contain it. The timestamp must lie within
        the market session of its day: open <= ts < close (else ValueError).
        Duplicates replace; see module docstring."""
        if candle.tf is not Timeframe.M1:
            raise ValueError(f"CandleStore.add accepts M1 only, got {candle.tf}")
        session_open = self.spec.session_open_dt(candle.ts)
        session_close = session_open + timedelta(minutes=self.spec.session_minutes)
        if not (session_open <= candle.ts < session_close):
            raise ValueError(f"M1 ts {candle.ts} outside session "
                             f"{self.spec.session_open}-{self.spec.session_close} of its day")
        series = self._series(candle.symbol)
        _insert_sorted(series[Timeframe.M1], candle)
        for tf in _DERIVED:
            self._recompute_bucket(candle.symbol, tf, candle.ts)

    def _recompute_bucket(self, symbol: str, tf: Timeframe, ts: datetime) -> None:
        """Rebuild the tf bucket containing ts from its constituent M1s."""
        start = _bucket_start(ts, tf, self.spec)
        end = start + timedelta(minutes=_tf_minutes(tf, self.spec))
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
        self._audit_bucket(symbol, tf, start)

    def _audit_bucket(self, symbol: str, tf: Timeframe, start: datetime) -> None:
        """Mark the bucket incomplete iff it holds fewer M1 members than its
        span expects (span truncated at session close: the session's last
        bucket legitimately expects fewer)."""
        end = start + timedelta(minutes=_tf_minutes(tf, self.spec))
        close = (self.spec.session_open_dt(start)
                 + timedelta(minutes=self.spec.session_minutes))
        expected = int((min(end, close) - start).total_seconds() // 60)
        m1 = self._data[symbol][Timeframe.M1]
        n = (bisect_left(m1, end, key=_TS) - bisect_left(m1, start, key=_TS))
        key = (symbol, tf, start)
        if n < expected:
            self._incomplete.add(key)
        else:
            self._incomplete.discard(key)

    def view(self, symbol: str, now: datetime,
             complete_only: bool = False) -> CandleView:
        """Point-in-time view exposing only candles fully closed by ``now``;
        ``complete_only`` (detector-facing) also hides incomplete buckets."""
        return CandleView(self, symbol, now, complete_only)

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
                        open=self.spec.quantize(row.open),
                        high=self.spec.quantize(row.high),
                        low=self.spec.quantize(row.low),
                        close=self.spec.quantize(row.close),
                        volume=int(row.volume),
                    )
                    for row in df.itertuples(index=False)
                ),
                key=_TS,
            )
        self._data[symbol] = series
        self._incomplete = {k for k in self._incomplete if k[0] != symbol}
        m1 = series[Timeframe.M1]
        if m1:
            for tf in _DERIVED:
                if tf in missing:
                    for candle in m1:
                        self._recompute_bucket(symbol, tf, candle.ts)
                else:       # trust loaded buckets, re-derive completeness only
                    for c in series[tf]:
                        self._audit_bucket(symbol, tf, c.ts)
