"""Market data fetcher: pull NSE M1 candles (yfinance) into FileFeed CSV
schema (``ts,open,high,low,close,volume``; see ``trader.feed.file``).

Only ``fetch_symbol`` touches the network (and imports ``yfinance`` lazily,
so it stays an optional dependency -- extra ``data``). Every other function
here is a pure transform over DataFrames, testable with fixtures.

yfinance's 1m interval is limited to short trailing windows and rejects
requests spanning more than ~7 days, so a ``--days N`` pull is chunked into
<=7-day windows and concatenated.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import timedelta
from pathlib import Path

import pandas as pd

from trader.models.market import NSE, MarketSpec

CSV_COLUMNS = ["ts", "open", "high", "low", "close", "volume"]
CHUNK_DAYS = 7
GAP_THRESHOLD = 300  # M1 rows/session; a full NSE session is 375


def chunks(days: int, today: date_type | None = None) -> list[tuple[date_type, date_type]]:
    """[start, end) day windows covering the trailing ``days`` days ending
    ``today`` (default: real today), each <= CHUNK_DAYS wide."""
    end = today or date_type.today()
    start = end - timedelta(days=days)
    out, cur = [], start
    while cur < end:
        nxt = min(cur + timedelta(days=CHUNK_DAYS), end)
        out.append((cur, nxt))
        cur = nxt
    return out


def to_filefeed(raw: pd.DataFrame, spec: MarketSpec = NSE) -> pd.DataFrame:
    """Convert a yfinance-shaped OHLCV frame (tz-aware DatetimeIndex or a
    ``Datetime``/``ts`` column; columns Open/High/Low/Close/Volume, any
    case) into the FileFeed CSV schema: ``ts`` ISO in spec's tz, prices
    tick-quantized, volume int. Rows outside the session
    ``[open_t, close_t)`` are dropped; duplicate ``ts`` keep the last row;
    result is sorted by ``ts``."""
    if raw.empty:
        return pd.DataFrame(columns=CSV_COLUMNS)
    df = raw.reset_index() if "ts" not in raw.columns else raw.copy()
    df.columns = [str(c).lower() for c in df.columns]
    ts_col = "ts" if "ts" in df.columns else df.columns[0]
    ts = pd.to_datetime(df[ts_col], utc=True).dt.tz_convert(spec.tzinfo)
    in_session = ts.map(lambda t: spec.open_t <= t.time() < spec.close_t)
    out = pd.DataFrame({
        "ts": ts[in_session].map(lambda t: t.isoformat()),
        "open": [str(spec.quantize(v)) for v in df.loc[in_session, "open"]],
        "high": [str(spec.quantize(v)) for v in df.loc[in_session, "high"]],
        "low": [str(spec.quantize(v)) for v in df.loc[in_session, "low"]],
        "close": [str(spec.quantize(v)) for v in df.loc[in_session, "close"]],
        "volume": df.loc[in_session, "volume"].astype(int).to_numpy(),
    })
    return (out.drop_duplicates(subset="ts", keep="last")
               .sort_values("ts").reset_index(drop=True))


def merge(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    """Union two FileFeed-schema frames by ``ts`` (``new`` wins on
    conflict), sorted ascending."""
    if existing.empty:
        return new.copy().reset_index(drop=True)
    if new.empty:
        return existing.copy().reset_index(drop=True)
    combined = pd.concat([existing, new], ignore_index=True)
    return (combined.drop_duplicates(subset="ts", keep="last")
                    .sort_values("ts").reset_index(drop=True))


def gap_report(df: pd.DataFrame, threshold: int = GAP_THRESHOLD) -> list[tuple[str, int]]:
    """Sessions (calendar date of ``ts``) with fewer than ``threshold`` M1
    rows, as ``(date_iso, row_count)`` pairs sorted by date."""
    if df.empty:
        return []
    counts = pd.to_datetime(df["ts"]).dt.date.value_counts()
    return sorted((d.isoformat(), int(n)) for d, n in counts.items() if n < threshold)


def read_csv(path: Path) -> pd.DataFrame:
    """Existing FileFeed CSV at ``path``, or an empty frame if absent."""
    if not path.exists():
        return pd.DataFrame(columns=CSV_COLUMNS)
    return pd.read_csv(path, dtype={"ts": str})


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def fetch_symbol(symbol: str, days: int, data_dir: Path,
                 spec: MarketSpec = NSE) -> dict:
    """Download ``days`` trailing days of NSE M1 data for ``symbol`` via
    yfinance, merge into ``data_dir/<symbol>.csv`` (union by ts with any
    existing file), and return a summary dict (symbol, days, rows, gaps).
    Raises RuntimeError with an install hint if yfinance is not installed."""
    try:
        import yfinance as yf
    except ImportError as e:
        raise RuntimeError(
            "yfinance is required for `trader fetch` (install with "
            "`uv pip install 'trader[data]'`)") from e

    ticker = yf.Ticker(f"{symbol}.NS")
    frames = [h for start, end in chunks(days)
             if not (h := ticker.history(interval="1m", start=start, end=end)).empty]
    raw = pd.concat(frames) if frames else pd.DataFrame()
    fetched = to_filefeed(raw, spec)

    path = data_dir / f"{symbol}.csv"
    merged = merge(read_csv(path), fetched)
    write_csv(path, merged)

    return {"symbol": symbol, "days": days, "rows": len(merged), "gaps": gap_report(merged)}
