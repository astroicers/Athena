"""Async HTTP client wrapping all Athena backend REST endpoints."""

from __future__ import annotations

import json as _json
from typing import Any

import httpx
import typer
from rich.console import Console

from athena_cli.config import get_config

console = Console(stderr=True)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        cfg = get_config()
        base = cfg.base_url.rstrip("/")
        _client = httpx.AsyncClient(base_url=f"{base}/api", timeout=30.0)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
        _client = None


async def _request(method: str, path: str, **kwargs: Any) -> Any:
    client = _get_client()
    try:
        resp = await client.request(method, path, **kwargs)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:200]
        console.print(f"[red]HTTP {exc.response.status_code}[/] {path}: {body}")
        raise typer.Exit(1) from exc
    except httpx.ConnectError as exc:
        console.print(f"[red]Connection failed[/]: {exc}")
        raise typer.Exit(1) from exc
    if resp.status_code == 204 or not resp.content:
        return None
    content_type = resp.headers.get("content-type", "")
    if "application/json" not in content_type:
        console.print(
            f"[red]Unexpected response[/] from {path}: "
            f"content-type={content_type}. Is --base-url pointing to the backend?"
        )
        raise typer.Exit(1)
    return resp.json()


# ── Operations ────────────────────────────────────────────────────

async def list_operations() -> list[dict]:
    return await _request("GET", "/operations")


async def get_operation(op_id: str) -> dict:
    return await _request("GET", f"/operations/{op_id}")


# ── OODA ──────────────────────────────────────────────────────────

async def ooda_trigger(op_id: str) -> dict:
    return await _request("POST", f"/operations/{op_id}/ooda/trigger")


async def ooda_dashboard(op_id: str) -> dict:
    return await _request("GET", f"/operations/{op_id}/ooda/dashboard")


async def ooda_current(op_id: str) -> dict | None:
    return await _request("GET", f"/operations/{op_id}/ooda/current")


async def ooda_history(op_id: str) -> list[dict]:
    return await _request("GET", f"/operations/{op_id}/ooda/history")


async def ooda_timeline(op_id: str) -> list[dict]:
    return await _request("GET", f"/operations/{op_id}/ooda/timeline")


async def ooda_directive(op_id: str, text: str, scope: str = "next_cycle") -> dict:
    return await _request(
        "POST",
        f"/operations/{op_id}/ooda/directive",
        json={"directive": text, "scope": scope},
    )


async def ooda_auto_start(
    op_id: str, interval_sec: int = 30, max_iterations: int = 0
) -> dict:
    return await _request(
        "POST",
        f"/operations/{op_id}/ooda/auto-start",
        json={"interval_sec": interval_sec, "max_iterations": max_iterations},
    )


async def ooda_auto_stop(op_id: str) -> dict:
    return await _request("DELETE", f"/operations/{op_id}/ooda/auto-stop")


async def ooda_auto_status(op_id: str) -> dict:
    return await _request("GET", f"/operations/{op_id}/ooda/auto-status")


# ── C5ISR ─────────────────────────────────────────────────────────

async def c5isr_status(op_id: str) -> list[dict]:
    return await _request("GET", f"/operations/{op_id}/c5isr")


async def c5isr_report(op_id: str, domain: str) -> dict:
    return await _request("GET", f"/operations/{op_id}/c5isr/{domain}/report")


# ── Recon ─────────────────────────────────────────────────────────

async def recon_scan(
    op_id: str, target_id: str, enable_initial_access: bool = True
) -> dict:
    return await _request(
        "POST",
        f"/operations/{op_id}/recon/scan",
        json={
            "target_id": target_id,
            "enable_initial_access": enable_initial_access,
        },
    )


async def recon_status(op_id: str) -> dict:
    return await _request("GET", f"/operations/{op_id}/recon/status")


async def recon_result(op_id: str, scan_id: str) -> dict:
    return await _request("GET", f"/operations/{op_id}/recon/scans/{scan_id}")


# ── Targets / Facts ──────────────────────────────────────────────

async def list_targets(op_id: str) -> list[dict]:
    return await _request("GET", f"/operations/{op_id}/targets")


async def list_facts(op_id: str) -> list[dict]:
    return await _request("GET", f"/operations/{op_id}/facts")


async def recommendation_latest(op_id: str) -> dict | None:
    return await _request("GET", f"/operations/{op_id}/recommendations/latest")
