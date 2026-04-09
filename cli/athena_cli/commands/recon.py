"""athena recon — Reconnaissance scanning commands."""

from __future__ import annotations

import asyncio

import typer

from athena_cli import api
from athena_cli.config import get_config
from athena_cli.display import (
    console,
    print_json,
    render_recon_result,
    render_recon_status,
    render_ws_event,
)

app = typer.Typer(no_args_is_help=True)


@app.command("scan")
def recon_scan(
    op_id: str = typer.Argument(..., help="Operation ID"),
    target_id: str = typer.Argument(..., help="Target ID"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow scan progress in real-time"),
) -> None:
    """Start a recon scan on a target. SPEC-052: Initial access handled by OODA."""
    async def _run() -> None:
        try:
            result = await api.recon_scan(op_id, target_id)
            scan_id = result.get("scan_id", "?")
            console.print(f"[green]Scan queued[/]: {scan_id}")

            if follow:
                await _follow_recon(op_id, scan_id)
            else:
                await _poll_recon(op_id, scan_id)
        finally:
            await api.close_client()

    asyncio.run(_run())


async def _follow_recon(op_id: str, scan_id: str) -> None:
    """Follow recon scan via WebSocket until completion."""
    from athena_cli.ws import stream_events

    console.print("[dim]Following scan via WebSocket...[/]")
    event_filter = {"recon.started", "recon.progress", "recon.completed", "recon.failed", "fact.new"}

    try:
        async for evt, data, ts in stream_events(op_id, event_filter):
            render_ws_event(evt, data, ts)
            if evt in ("recon.completed", "recon.failed"):
                console.print()
                # Fetch full result
                try:
                    full = await api.recon_result(op_id, scan_id)
                    render_recon_result(full)
                except Exception:
                    render_recon_status(data)
                return
    except KeyboardInterrupt:
        console.print("[dim]Interrupted.[/]")


async def _poll_recon(op_id: str, scan_id: str, timeout: float = 120, interval: float = 2) -> None:
    """Poll recon status until scan completes."""
    from rich.live import Live
    from rich.spinner import Spinner

    with Live(Spinner("dots", text="Scanning..."), console=console, refresh_per_second=4):
        elapsed = 0.0
        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval
            data = await api.recon_status(op_id)
            status = data.get("status", "")
            if status in ("completed", "failed"):
                break

    # Fetch and display full result
    try:
        full = await api.recon_result(op_id, scan_id)
        if get_config().json_output:
            print_json(full)
        else:
            render_recon_result(full)
    except Exception:
        data = await api.recon_status(op_id)
        render_recon_status(data)


@app.command("status")
def recon_status_cmd(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """Show most recent recon scan status."""
    async def _run() -> None:
        try:
            data = await api.recon_status(op_id)
            if get_config().json_output:
                print_json(data)
            else:
                render_recon_status(data)
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("result")
def recon_result_cmd(
    op_id: str = typer.Argument(..., help="Operation ID"),
    scan_id: str = typer.Argument(..., help="Scan ID"),
) -> None:
    """Show full recon scan result."""
    async def _run() -> None:
        try:
            data = await api.recon_result(op_id, scan_id)
            if get_config().json_output:
                print_json(data)
            else:
                render_recon_result(data)
        finally:
            await api.close_client()

    asyncio.run(_run())
