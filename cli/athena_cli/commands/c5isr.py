"""athena c5isr — C5ISR domain health commands."""

from __future__ import annotations

import asyncio

import typer

from athena_cli import api
from athena_cli.config import get_config
from athena_cli.display import (
    console,
    print_json,
    render_c5isr_overview,
    render_c5isr_report,
)

app = typer.Typer(no_args_is_help=True)

VALID_DOMAINS = ["command", "control", "comms", "computers", "cyber", "isr"]


@app.command("status")
def c5isr_status(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """Show 6-domain C5ISR health overview."""
    async def _run() -> None:
        try:
            data = await api.c5isr_status(op_id)
            if get_config().json_output:
                print_json(data)
            else:
                render_c5isr_overview(data)
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("report")
def c5isr_report(
    op_id: str = typer.Argument(..., help="Operation ID"),
    domain: str = typer.Argument(..., help=f"Domain: {', '.join(VALID_DOMAINS)}"),
) -> None:
    """Show full domain report with metrics, risks, recommendations."""
    domain = domain.lower()
    if domain not in VALID_DOMAINS:
        console.print(f"[red]Invalid domain:[/] {domain}. Choose from: {', '.join(VALID_DOMAINS)}")
        raise typer.Exit(1)

    async def _run() -> None:
        try:
            data = await api.c5isr_report(op_id, domain)
            if get_config().json_output:
                print_json(data)
            else:
                render_c5isr_report(data)
        finally:
            await api.close_client()

    asyncio.run(_run())
