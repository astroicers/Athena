"""athena intel — Intelligence queries: targets, facts, recommendations."""

from __future__ import annotations

import asyncio

import typer

from athena_cli import api
from athena_cli.config import get_config
from athena_cli.display import (
    console,
    print_json,
    render_facts_list,
    render_recommendation,
    render_targets_list,
)

app = typer.Typer(no_args_is_help=True)


@app.command("targets")
def intel_targets(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """List all targets in an operation."""
    async def _run() -> None:
        try:
            data = await api.list_targets(op_id)
            if get_config().json_output:
                print_json(data)
            else:
                render_targets_list(data)
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("facts")
def intel_facts(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """List all collected intelligence facts."""
    async def _run() -> None:
        try:
            data = await api.list_facts(op_id)
            if get_config().json_output:
                print_json(data)
            else:
                render_facts_list(data)
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("recommend")
def intel_recommend(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """Show the latest Orient recommendation."""
    async def _run() -> None:
        try:
            data = await api.recommendation_latest(op_id)
            if get_config().json_output:
                print_json(data)
            else:
                render_recommendation(data)
        finally:
            await api.close_client()

    asyncio.run(_run())
