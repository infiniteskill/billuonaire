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
import logging
import shutil
from datetime import date
from decimal import Decimal
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from trader.config import load_settings, load_stocks
from trader.engine.pipeline import Orchestrator
from trader.engine.scanner import fit, has_data
from trader.feed.file import FileFeed
from trader.feed.mock import ScenarioFeed, judas_reversal
from trader.learn.calibrate import analyze
from trader.replay.engine import run_replay
from trader.replay.metrics import Report, compute
from trader.store.candles import CandleStore
from trader.store.journal import Journal

app = typer.Typer(no_args_is_help=True)
console = Console()

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "config"
_DEFAULT_STOCKS: dict = {"stocks": []}


def _setup_logging(dir: Path, verbose: bool) -> None:
    """C7: one root-logger setup per run — rich console at INFO (DEBUG with
    --verbose) + rotating DEBUG file at --dir/logs/trader.log, so detector
    exceptions (logged by DetectorRegistry.run_all) are actually visible.
    Handlers are REPLACED, keeping repeat CLI invocations idempotent."""
    logs = dir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    file = RotatingFileHandler(logs / "trader.log",
                               maxBytes=5_000_000, backupCount=3)
    file.setLevel(logging.DEBUG)
    file.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"))
    rich = RichHandler(console=console, show_path=False, rich_tracebacks=True)
    rich.setLevel(logging.DEBUG if verbose else logging.INFO)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers[:] = [rich, file]


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


def _candle_store(dir: Path, spec) -> CandleStore:
    """Shared store dir convention (watch/list/scanner alike)."""
    return CandleStore(dir / "journal" / "candles", spec)


@app.command(name="list")
def list_stocks(
    dir: Path = typer.Option(Path("."), "--dir", help="Directory containing stocks.json."),
) -> None:
    """Print a numbered table of configured stocks (stocks.json order) with
    a real fit() score wherever its candle cache under dir/journal/candles
    is non-empty, else '-'."""
    stocks = load_stocks(dir / "stocks.json")
    settings = load_settings(dir / "config.json")
    spec = settings.market_spec()
    store = _candle_store(dir, spec)

    table = Table()
    table.add_column("#")
    table.add_column("symbol")
    table.add_column("fit")
    for i, symbol in enumerate(stocks, start=1):
        store.load(symbol)
        score = f"{fit(symbol, store, spec)['score']:.1f}" if has_data(symbol, store, spec) else "-"
        table.add_row(str(i), symbol, score)

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
    store = _candle_store(dir, spec)
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
    index: Optional[str] = typer.Option(None, "--index",
                                        help="Index symbol (overrides config index_symbol)."),
    verbose: bool = typer.Option(False, "--verbose", "-v",
                                 help="Console logging at DEBUG."),
) -> None:
    """Run the Orchestrator against mock or file data to exhaustion, then
    print a summary + per-symbol table once (live streaming is a later phase).
    Candle cache (dir/journal/candles) loads before the run and saves after,
    so fit scores and prior-day context accumulate across invocations."""
    _setup_logging(dir, verbose)
    stocks = load_stocks(dir / "stocks.json")
    symbols = _resolve_symbols(dir, stocks, numbers or [], auto)
    if not symbols:
        typer.echo("no symbols selected (pass numbers or --auto K)", err=True)
        raise typer.Exit(code=1)

    settings = load_settings(dir / "config.json")
    index = index or settings.index_symbol
    if feed == "mock":
        today = date.today()
        data_feed = ScenarioFeed([judas_reversal(sym, today, 100.0)
                                  for sym in symbols + ([index] if index else [])])
    elif feed == "file":
        if data is None:
            typer.echo("--feed file requires --data DIR", err=True)
            raise typer.Exit(code=1)
        if index and not (data / f"{index}.csv").exists():
            typer.echo(f"index {index}: no data in feed, running without index context",
                       err=True)
            index = None
        data_feed = FileFeed(data)
    else:
        typer.echo(f"unknown --feed {feed!r} (expected mock|file)", err=True)
        raise typer.Exit(code=1)

    journal_dir = dir / "journal"
    all_symbols = symbols + ([index] if index else [])
    store = _candle_store(dir, settings.market_spec())
    for sym in all_symbols:
        store.load(sym)
    orch = Orchestrator(settings, data_feed, symbols, index_symbol=index,
                        capital=capital, max_qty=max_qty, journal_dir=journal_dir,
                        store=store, level_dir=journal_dir / "levels",
                        timestats_dir=journal_dir / "timestats")
    summary = orch.run()
    for sym in all_symbols:
        store.save(sym)
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


def _parse_day(s: Optional[str]) -> Optional[date]:
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        typer.echo(f"invalid date {s!r} (want YYYY-MM-DD)", err=True)
        raise typer.Exit(code=1)


def _fmt(v) -> str:
    return "-" if v is None else f"{v:.2f}" if isinstance(v, float) else str(v)


def _render_report(rep: Report) -> None:
    _print_summary("Totals", {k: _fmt(v) for k, v in rep.totals.items()})
    for title, rows in (("By template", rep.per_template),
                        ("By symbol", rep.per_symbol),
                        ("By exit reason", rep.per_exit)):
        if not rows:
            continue
        table = Table(title=title)
        for col in ("", "n", "wr", "gross R", "net R", "net pnl"):
            table.add_column(col)
        for key, r in rows.items():
            table.add_row(key, str(r["n"]), f"{r['wr']:.0%}", _fmt(r["gross_r"]),
                          _fmt(r["net_r"]), str(r["net_pnl"]))
        console.print(table)
    if rep.per_gate:
        table = Table(title="Skips by gate")
        table.add_column("gate")
        table.add_column("n")
        for gate, n in sorted(rep.per_gate.items()):
            table.add_row(gate, str(n))
        console.print(table)
    if rep.per_day:
        table = Table(title="Per day")
        for col in ("day", "trades", "net R"):
            table.add_column(col)
        for day_iso, n, r in rep.per_day:
            table.add_row(day_iso, str(n), _fmt(r))
        console.print(table)
        s = rep.day_stats
        console.print(f"daily net R: mean {s['mean']:.2f}, std {s['std']:.2f}, "
                      f"n_days {s['n_days']}")
    for note in rep.notes:
        console.print(f"[yellow]note: {note}[/yellow]")


@app.command()
def replay(
    data: Path = typer.Option(..., "--data", help="CSV root (FileFeed schema)."),
    from_: str = typer.Option(..., "--from", help="Start date YYYY-MM-DD."),
    to: str = typer.Option(..., "--to", help="End date YYYY-MM-DD."),
    stocks: Optional[str] = typer.Option(None, "--stocks",
                                         help="Comma-separated stock numbers (stocks.json)."),
    all_: bool = typer.Option(False, "--all", help="Replay every CSV in --data."),
    index: Optional[str] = typer.Option(None, "--index",
                                        help="Index symbol (overrides config index_symbol)."),
    dir: Path = typer.Option(Path("."), "--dir", help="Config directory."),
    capital: Optional[float] = typer.Option(None, "--capital"),
    max_qty: int = typer.Option(1, "--max-qty"),
    fresh: bool = typer.Option(True, "--fresh/--no-fresh",
                               help="Wipe dir/journal (journals + candle/level/"
                               "timestats caches) before replaying, so reruns "
                               "never append duplicate day entries. --no-fresh "
                               "accumulates state across runs (watch-style)."),
    verbose: bool = typer.Option(False, "--verbose", "-v",
                                 help="Console logging at DEBUG."),
) -> None:
    """Replay a date range of CSV data through the live pipeline (journals
    under dir/journal, wiped first unless --no-fresh), then print the
    metrics report for the range."""
    _setup_logging(dir, verbose)
    settings = load_settings(dir / "config.json")
    index = index or settings.index_symbol
    start, end = _parse_day(from_), _parse_day(to)
    if start > end:
        typer.echo(f"--from {start} is after --to {end}", err=True)
        raise typer.Exit(code=1)
    if all_:
        symbols = sorted(p.stem for p in data.glob("*.csv") if p.stem != index)
    elif stocks:
        try:
            numbers = [int(n) for n in stocks.split(",")]
        except ValueError:
            typer.echo(f"invalid --stocks {stocks!r} (want e.g. 1,4)", err=True)
            raise typer.Exit(code=1)
        symbols = _resolve_symbols(dir, load_stocks(dir / "stocks.json"), numbers, None)
    else:
        typer.echo("pass --stocks 1,4 or --all", err=True)
        raise typer.Exit(code=1)
    if not symbols:
        typer.echo("no symbols to replay", err=True)
        raise typer.Exit(code=1)
    if index and not (data / f"{index}.csv").exists():
        typer.echo(f"index {index}: no data in feed, running without index context",
                   err=True)
        index = None
    if fresh and (dir / "journal").exists():   # after validation: errors never wipe
        shutil.rmtree(dir / "journal")
    summary = run_replay(settings, data, symbols, start, end, dir / "journal",
                         index=index, capital=capital, max_qty=max_qty)
    _print_summary("Replay Summary", summary)
    _render_report(compute(dir / "journal", start, end))


@app.command()
def report(
    journal: Path = typer.Option(..., "--journal", help="Journal directory (JSONL days)."),
    from_: Optional[str] = typer.Option(None, "--from", help="Start date YYYY-MM-DD."),
    to: Optional[str] = typer.Option(None, "--to", help="End date YYYY-MM-DD."),
) -> None:
    """Re-render the metrics report from journal JSONL files."""
    _render_report(compute(journal, _parse_day(from_), _parse_day(to)))


@app.command()
def calibrate(
    journal: Path = typer.Option(..., "--journal", help="Journal directory (JSONL days)."),
    from_: Optional[str] = typer.Option(None, "--from", help="Start date YYYY-MM-DD."),
    to: Optional[str] = typer.Option(None, "--to", help="End date YYYY-MM-DD."),
    dir: Path = typer.Option(Path("."), "--dir", help="Config directory (current weights)."),
) -> None:
    """Per-detector precision from journaled verdict members + trade
    outcomes, with capped weight suggestions (see learn/calibrate.py for the
    proxy). PRINT ONLY -- config.json is never touched."""
    weights = {}
    cfg_path = dir / "config.json"
    if cfg_path.exists():
        settings = load_settings(cfg_path)
        weights = {k: v for k, v in settings.confluence.weights.items()
                   if k in settings.detectors.enabled}
    else:
        console.print(f"[yellow]no {cfg_path}: precision only, "
                      "no weight suggestions[/yellow]")
    rep = analyze(journal, _parse_day(from_), _parse_day(to), weights)
    console.print(f"verdicts {rep.n_verdicts}, linked trades {rep.n_trades}, "
                  f"wins {rep.n_wins}")
    table = Table(title="Detector precision (win-zone share of member appearances)")
    for col in ("detector", "weight", "members", "in wins", "precision", "suggested"):
        table.add_column(col)
    for det in sorted(set(rep.weights) | set(rep.rows)):
        r = rep.rows.get(det, {"appearances": 0, "wins": 0, "precision": 0.0})
        sug = (f"{rep.suggestions[det]:g}" if det in rep.suggestions
               else "-" if det not in rep.weights
               else f"insufficient data (<{rep.min_samples})")
        table.add_row(det, _fmt(rep.weights.get(det)), str(r["appearances"]),
                      str(r["wins"]), f"{r['precision']:.1%}", sug)
    console.print(table)
    if rep.weights:
        merged = {d: rep.suggestions.get(d, w) for d, w in rep.weights.items()}
        console.print('copy-paste "weights" for config.json confluence '
                      "(suggestions applied; NOT auto-applied):")
        console.print(json.dumps(merged, indent=2))


@app.command()
def fetch(
    symbols: list[str] = typer.Argument(..., help="Symbols to fetch (e.g. RELIANCE TCS)."),
    days: int = typer.Option(25, "--days", help="Trailing days of M1 data to pull."),
    data: Path = typer.Option(..., "--data", help="CSV root; writes/merges <SYMBOL>.csv."),
    source: str = typer.Option("yfinance", "--source", help="Data source (yfinance)."),
) -> None:
    """Pull trailing M1 candles for SYMBOLS into --data as FileFeed CSVs
    (merged with any existing file), printing a per-symbol summary with a
    gap report (sessions with <300 M1 rows)."""
    if source != "yfinance":
        typer.echo(f"unknown --source {source!r} (expected yfinance)", err=True)
        raise typer.Exit(code=1)
    from trader.tools.fetch import fetch_symbol

    data.mkdir(parents=True, exist_ok=True)
    for symbol in symbols:
        try:
            summary = fetch_symbol(symbol, days, data)
        except RuntimeError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1)
        table = Table(title=f"fetch {symbol}")
        table.add_column("metric")
        table.add_column("value")
        table.add_row("days requested", str(summary["days"]))
        table.add_row("rows", str(summary["rows"]))
        gaps = summary["gaps"]
        table.add_row("gap sessions", str(len(gaps)))
        for day_iso, n in gaps:
            table.add_row(f"  {day_iso}", f"{n} rows")
        console.print(table)


if __name__ == "__main__":
    app()
