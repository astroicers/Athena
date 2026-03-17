"""Athena CLI — entry point."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from athena_cli.config import load_config, set_global_config

app = typer.Typer(
    name="athena",
    help="Athena C5ISR Pentest Platform CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


@app.callback()
def main(
    base_url: Optional[str] = typer.Option(  # noqa: UP007
        None, "--base-url", "-u", envvar="ATHENA_BASE_URL",
        help="Backend API base URL",
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Raw JSON output",
    ),
    no_color: bool = typer.Option(
        False, "--no-color", help="Disable color output",
    ),
) -> None:
    """Athena C5ISR Pentest Platform CLI."""
    cfg = load_config(base_url=base_url, json_output=json_output, no_color=no_color)
    set_global_config(cfg)
    if no_color:
        console.no_color = True


# Import and register subcommands
from athena_cli.commands import ops, ooda, c5isr, recon, intel  # noqa: E402

app.add_typer(ops.app, name="ops", help="Operation management")
app.add_typer(ooda.app, name="ooda", help="OODA loop control")
app.add_typer(c5isr.app, name="c5isr", help="C5ISR domain health")
app.add_typer(recon.app, name="recon", help="Reconnaissance scanning")
app.add_typer(intel.app, name="intel", help="Intelligence: targets, facts, recommendations")

if __name__ == "__main__":
    app()
