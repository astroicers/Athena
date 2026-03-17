"""athena ooda — OODA loop control commands."""

from __future__ import annotations

import asyncio

import typer

from athena_cli import api
from athena_cli.config import get_config
from athena_cli.display import (
    console,
    print_json,
    render_c5isr_overview,
    render_ooda_dashboard,
    render_ooda_history,
    render_ooda_timeline,
    render_ws_event,
)

app = typer.Typer(no_args_is_help=True)


@app.command("status")
def ooda_status(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """Show OODA dashboard — current phase, latest iteration."""
    async def _run() -> None:
        try:
            data = await api.ooda_dashboard(op_id)
            if get_config().json_output:
                print_json(data)
            else:
                render_ooda_dashboard(data)
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("trigger")
def ooda_trigger(
    op_id: str = typer.Argument(..., help="Operation ID"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow cycle in real-time"),
) -> None:
    """Trigger one OODA cycle."""
    async def _run() -> None:
        try:
            result = await api.ooda_trigger(op_id)
            console.print("[green]OODA cycle queued.[/]")

            if follow:
                await _follow_ooda_cycle(op_id)
            else:
                await _poll_ooda_cycle(op_id)
        finally:
            await api.close_client()

    asyncio.run(_run())


async def _follow_ooda_cycle(op_id: str) -> None:
    """Follow OODA cycle via WebSocket until completion."""
    from athena_cli.ws import stream_events

    console.print("[dim]Following OODA cycle via WebSocket...[/]")
    event_filter = {"ooda.phase", "ooda.completed", "c5isr.update", "fact.new", "opsec.alert", "decision.result"}

    try:
        async for evt, data, ts in stream_events(op_id, event_filter):
            render_ws_event(evt, data, ts)
            if evt == "ooda.completed":
                # Fetch and display final state
                console.print()
                dashboard = await api.ooda_dashboard(op_id)
                render_ooda_dashboard(dashboard)
                # Also show C5ISR
                c5isr_data = await api.c5isr_status(op_id)
                if c5isr_data:
                    render_c5isr_overview(c5isr_data)
                return
    except KeyboardInterrupt:
        console.print("[dim]Interrupted.[/]")


async def _poll_ooda_cycle(op_id: str, timeout: float = 120, interval: float = 2) -> None:
    """Poll OODA dashboard until iteration count changes."""
    from rich.live import Live
    from rich.spinner import Spinner

    initial = await api.ooda_dashboard(op_id)
    initial_count = initial.get("iteration_count", 0)

    with Live(Spinner("dots", text="Waiting for OODA cycle to complete..."), console=console, refresh_per_second=4):
        elapsed = 0.0
        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval
            data = await api.ooda_dashboard(op_id)
            current_count = data.get("iteration_count", 0)
            if current_count > initial_count:
                break

    # Show final result
    dashboard = await api.ooda_dashboard(op_id)
    render_ooda_dashboard(dashboard)
    c5isr_data = await api.c5isr_status(op_id)
    if c5isr_data:
        render_c5isr_overview(c5isr_data)


@app.command("history")
def ooda_history(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """Show all OODA iteration history."""
    async def _run() -> None:
        try:
            data = await api.ooda_history(op_id)
            if get_config().json_output:
                print_json(data)
            else:
                render_ooda_history(data)
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("timeline")
def ooda_timeline(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """Show per-phase OODA timeline."""
    async def _run() -> None:
        try:
            data = await api.ooda_timeline(op_id)
            if get_config().json_output:
                print_json(data)
            else:
                render_ooda_timeline(data)
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("directive")
def ooda_directive(
    op_id: str = typer.Argument(..., help="Operation ID"),
    text: str = typer.Argument(..., help="Directive text"),
) -> None:
    """Issue a commander directive for the next OODA cycle."""
    async def _run() -> None:
        try:
            result = await api.ooda_directive(op_id, text)
            console.print(f"[green]Directive stored[/] (id: {result.get('id', '?')})")
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("auto-start")
def ooda_auto_start(
    op_id: str = typer.Argument(..., help="Operation ID"),
    interval: int = typer.Option(30, "--interval", "-i", help="Seconds between cycles"),
    max_iterations: int = typer.Option(0, "--max", "-m", help="Max iterations (0=unlimited)"),
) -> None:
    """Start automatic OODA loop."""
    async def _run() -> None:
        try:
            result = await api.ooda_auto_start(op_id, interval, max_iterations)
            console.print(f"[green]Auto loop started[/]: interval={interval}s, max={max_iterations or 'unlimited'}")
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("auto-stop")
def ooda_auto_stop(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """Stop automatic OODA loop."""
    async def _run() -> None:
        try:
            result = await api.ooda_auto_stop(op_id)
            console.print(f"[yellow]Auto loop stopped[/]: {result.get('iterations_completed', '?')} iterations completed")
        finally:
            await api.close_client()

    asyncio.run(_run())


@app.command("auto-status")
def ooda_auto_status(
    op_id: str = typer.Argument(..., help="Operation ID"),
) -> None:
    """Check automatic OODA loop status."""
    async def _run() -> None:
        try:
            result = await api.ooda_auto_status(op_id)
            if get_config().json_output:
                print_json(result)
            else:
                status = result.get("status", "unknown")
                color = "green" if status == "running" else "dim"
                console.print(f"Auto loop: [{color}]{status}[/{color}]")
                if status == "running":
                    console.print(f"  Interval: {result.get('interval_sec', '?')}s")
                    console.print(f"  Iterations: {result.get('iterations_completed', '?')}")
        finally:
            await api.close_client()

    asyncio.run(_run())
