"""Trader CLI: scaffold a working directory (`init`) and inspect it (`list`).

Single source of truth for the default `config.json` content: the template
shipped alongside this package at ``<repo>/app/config/config.json`` (a sibling
of the ``trader`` package, resolved relative to this file so it works from an
editable install without hand-duplicating the defaults).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from trader.config import load_stocks

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


if __name__ == "__main__":
    app()
