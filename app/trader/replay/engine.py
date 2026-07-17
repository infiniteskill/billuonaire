"""Replay: the SAME Orchestrator driven over FileFeed for a date range.

No forked logic -- multi-day handling is the pipeline's own session resets.
Candle cache, levels and timestats persist under journal_dir (load before,
save after).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from trader.config import Settings
from trader.engine.pipeline import Orchestrator
from trader.feed.file import FileFeed
from trader.store.candles import CandleStore


class _RangeFeed:
    """FileFeed events filtered to session dates within [start, end]."""

    def __init__(self, feed: FileFeed, start: date, end: date):
        self.feed, self.start, self.end = feed, start, end

    def subscribe(self, symbols: list[str]) -> None:
        self.feed.subscribe(symbols)

    def events(self):
        return (e for e in self.feed.events()
                if self.start <= e.candle.ts.date() <= self.end)


def run_replay(settings: Settings, data_dir: Path, symbols: list[str],
               start: date, end: date, journal_dir: Path,
               index: str | None = None, capital: float | None = None,
               max_qty: int = 1) -> dict:
    """Replay [start, end] of CSV data through one Orchestrator; return its
    summary. Journals/candles/levels land under journal_dir."""
    journal_dir = Path(journal_dir)
    store = CandleStore(journal_dir / "candles", settings.market_spec())
    all_syms = symbols + ([index] if index else [])
    for sym in all_syms:
        store.load(sym)
    feed = _RangeFeed(FileFeed(Path(data_dir), settings.market_spec()), start, end)
    orch = Orchestrator(settings, feed, symbols, index_symbol=index,
                        capital=capital, max_qty=max_qty, journal_dir=journal_dir,
                        store=store, level_dir=journal_dir / "levels",
                        timestats_dir=journal_dir / "timestats")
    summary = orch.run()
    for sym in all_syms:
        store.save(sym)
    return summary
