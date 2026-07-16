"""Trader CLI: scaffold a working directory (`init`), inspect it (`list`),
run the engine against mock/file data (`watch`), and read back the journal
(`journal`, `status`).

Single source of truth for the default `config.json` content: the template
shipped alongside this package at ``<repo>/app/config/config.json`` (a sibling
of the ``trader`` package, resolved relative to this file so it works from an
editable install without hand-duplicating the defaults).

All engine logic (scoring, orchestration, journaling) lives in ``trader.engine``
/ ``trader.store``; this module only wires CLI options to those calls and
formats the result as rich tables.
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from trader.config import load_settings, load_stocks
from trader.engine.pipeline import Orchestrator
from trader.engine.scanner import fit, has_data
from trader.feed.file import FileFeed
from trader.feed.mock import ScenarioFeed, judas_reversal
from trader.store.candles import CandleStore
from trader.store.journal import Journal

app = typer.Typer(no_args_is_help=True)
console = Console()

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "config"
_DEFAULT_STOCKS: dict = {"stocks": []}


@app.command()
def init(
    dir: Path = typer.Option(Path("."), "--dir", help="Directory to scaffold."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files."),
) -> None:
    """Write default config.json and stocks.json into --dir."""
    dir.mkdir(parents=True, exist_ok=True)
    config_path = dir / "config.json"
    stocks_path = dir / "stocks.json"

    if not force:
        existing = [p for p in (config_path, stocks_path) if p.exists()]
        if existing:
            names = ", ".join(p.name for p in existing)
            typer.echo(f"Refusing to overwrite existing file(s): {names} (use --force)", err=True)
            raise typer.Exit(code=1)

    template = _TEMPLATE_DIR / "config.json"
    shutil.copyfile(template, config_path)
    stocks_path.write_text(json.dumps(_DEFAULT_STOCKS, indent=2) + "\n")

    typer.echo(f"Initialized trader workspace in {dir}")


@app.command(name="list")
def list_stocks(
    dir: Path = typer.Option(Path("."), "--dir", help="Directory containing stocks.json."),
) -> None:
    """Print a numbered table of configured stocks."""
    stocks = load_stocks(dir / "stocks.json")

    table = Table()
    table.add_column("#")
    table.add_column("symbol")
    table.add_column("fit")
    for i, symbol in enumerate(stocks, start=1):
        table.add_row(str(i), symbol, "-")

    console.print(table)


def _resolve_symbols(dir: Path, stocks: list[str], numbers: list[int],
                     auto: int | None) -> list[str]:
    """Numbers index into stocks.json (1-based); --auto K picks the top K by
    fit() using any cached candle data under dir/journal/candles, falling
    back to the first K configured stocks when none has data."""
    if auto is None:
        bad = [n for n in numbers if not 1 <= n <= len(stocks)]
        if bad:
            typer.echo(f"stock number(s) out of range: {bad} "
                       f"(stocks.json has {len(stocks)} entries)", err=True)
            raise typer.Exit(code=1)
        return [stocks[n - 1] for n in numbers]
    settings = load_settings(dir / "config.json")
    spec = settings.market_spec()
    store = CandleStore(dir / "journal" / "candles", spec)
    scored = []
    for sym in stocks:
        store.load(sym)
        if has_data(sym, store, spec):
            scored.append((fit(sym, store, spec)["score"], sym))
    if scored:
        scored.sort(key=lambda t: -t[0])
        return [sym for _, sym in scored[:auto]]
    return stocks[:auto]


def _latest_day(journal_dir: Path) -> date | None:
    files = sorted(journal_dir.glob("*.jsonl"))
    return date.fromisoformat(files[-1].stem) if files else None


def _print_summary(title: str, summary: dict) -> None:
    table = Table(title=title)
    table.add_column("metric")
    table.add_column("value")
    for k, v in summary.items():
        table.add_row(str(k), str(v))
    console.print(table)


def _symbol_row(symbol: str, entries: list[dict]) -> tuple:
    rows = [e for e in entries if e.get("symbol") == symbol]
    verdicts = [e for e in rows if e["kind"] == "verdict"]
    opens = [e for e in rows if e["kind"] == "trade_open"]
    closes = [e for e in rows if e["kind"] == "trade_close"]
    template = verdicts[-1]["template"] if verdicts else "-"
    score = f"{verdicts[-1]['final']:.1f}" if verdicts else "-"
    verdict = "traded" if opens else ("skip" if any(e["kind"] == "skip" for e in rows) else "-")
    position = "open" if len(opens) > len(closes) else ("closed" if opens else "-")
    pnl = sum((Decimal(e["pnl"]) for e in closes), Decimal(0))
    return symbol, template, score, verdict, position, str(pnl)


@app.command()
def watch(
    numbers: Optional[list[int]] = typer.Argument(
        None, help="Stock numbers (1-based, from stocks.json)."),
    dir: Path = typer.Option(Path("."), "--dir", help="Config directory."),
    capital: Optional[float] = typer.Option(None, "--capital"),
    max_qty: int = typer.Option(1, "--max-qty"),
    feed: str = typer.Option("mock", "--feed", help="mock|file"),
    data: Optional[Path] = typer.Option(None, "--data", help="CSV root for --feed file."),
    auto: Optional[int] = typer.Option(None, "--auto", help="Auto-pick top K by fit score."),
) -> None:
    """Run the Orchestrator against mock or file data to exhaustion, then
    print a summary + per-symbol table once (live streaming is a later phase)."""
    stocks = load_stocks(dir / "stocks.json")
    symbols = _resolve_symbols(dir, stocks, numbers or [], auto)
    if not symbols:
        typer.echo("no symbols selected (pass numbers or --auto K)", err=True)
        raise typer.Exit(code=1)

    settings = load_settings(dir / "config.json")
    if feed == "mock":
        today = date.today()
        data_feed = ScenarioFeed([judas_reversal(sym, today, 100.0) for sym in symbols])
    elif feed == "file":
        if data is None:
            typer.echo("--feed file requires --data DIR", err=True)
            raise typer.Exit(code=1)
        data_feed = FileFeed(data)
    else:
        typer.echo(f"unknown --feed {feed!r} (expected mock|file)", err=True)
        raise typer.Exit(code=1)

    journal_dir = dir / "journal"
    orch = Orchestrator(settings, data_feed, symbols, capital=capital,
                        max_qty=max_qty, journal_dir=journal_dir)
    summary = orch.run()
    _print_summary("Session Summary", summary)

    day = _latest_day(journal_dir)
    entries = Journal(journal_dir).read(day) if day else []
    table = Table(title="Symbols")
    for col in ("symbol", "template", "top score", "verdict", "position", "pnl"):
        table.add_column(col)
    for sym in symbols:
        table.add_row(*_symbol_row(sym, entries))
    console.print(table)


@app.command()
def journal(
    day: str = typer.Option(..., "--day", help="Session date YYYY-MM-DD."),
    dir: Path = typer.Option(Path("."), "--dir", help="Config directory."),
) -> None:
    """Pretty-print journal entries (kind, ts, symbol, key fields) for a day."""
    entries = Journal(dir / "journal").read(date.fromisoformat(day))
    table = Table(title=f"Journal {day}")
    for col in ("kind", "ts", "symbol", "detail"):
        table.add_column(col)
    for e in entries:
        detail = ", ".join(f"{k}={v}" for k, v in e.items()
                           if k not in ("kind", "ts", "symbol"))
        table.add_row(e.get("kind", ""), e.get("ts", ""), e.get("symbol", ""), detail)
    console.print(table)


@app.command()
def status(
    dir: Path = typer.Option(Path("."), "--dir", help="Config directory."),
) -> None:
    """Print trades/wins/losses/pnl/skips for the latest journal day."""
    journal_dir = dir / "journal"
    day = _latest_day(journal_dir)
    if day is None:
        typer.echo("no journal entries found")
        return
    entries = Journal(journal_dir).read(day)
    closes = [e for e in entries if e["kind"] == "trade_close"]
    _print_summary(f"Status {day.isoformat()}", {
        "trades": sum(1 for e in entries if e["kind"] == "trade_open"),
        "wins": sum(1 for e in closes if Decimal(e["pnl"]) > 0),
        "losses": sum(1 for e in closes if Decimal(e["pnl"]) < 0),
        "pnl": str(sum((Decimal(e["pnl"]) for e in closes), Decimal(0))),
        "skips": sum(1 for e in entries if e["kind"] == "skip"),
    })


if __name__ == "__main__":
    app()
