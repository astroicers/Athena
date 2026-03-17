"""athena ops — Operation management commands."""

from __future__ import annotations

import asyncio

import typer

from athena_cli import api
from athena_cli.config import get_config
from athena_cli.display import (
    console,
    print_json,
    render_operation_detail,
    render_operations_list,
    render_ws_event,
)

app = typer.Typer(no_args_is_help=True)


@app.command("list")
def ops_list() -> None:
    """List all operations."""
    async def _run() -> None:
        try:
            data = await api.list_operations()
            if get_config().json_output:
                print_json(data)
            else:
                render_operations_list(data)
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("show")
def ops_show(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """Show operation details."""
    async def _run() -> None:
        try:
            data = await api.get_operation(op_id)
            if get_config().json_output:
                print_json(data)
            else:
                render_operation_detail(data)
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("follow")
def ops_follow(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """Follow operation events in real-time via WebSocket."""
    from athena_cli.ws import stream_events

    async def _run() -> None:
        console.print(f"[dim]Connecting to WebSocket for {op_id}... (Ctrl+C to stop)[/]")
        try:
            async for evt, data, ts in stream_events(op_id):
                render_ws_event(evt, data, ts)
        except KeyboardInterrupt:
            pass
        finally:
            await api.close_client()
            console.print("[dim]Disconnected.[/]")

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass
