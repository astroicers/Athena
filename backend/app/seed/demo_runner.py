"""
Automated 6-step OODA cycle demo script for Athena C5ISR platform.

Sequentially calls the API to walk through two full OODA cycles,
printing each step's expected and actual results.

Usage (from backend/ directory):
    python -m app.seed.demo_runner

Environment variables:
    DEMO_STEP_DELAY  — seconds between steps (default: 3)
    DEMO_BASE_URL    — API base URL (default: http://localhost:8000/api)

Works with MOCK_LLM=true and no real Caldera (all mock).
"""

import asyncio
import json
import os
import sys
import textwrap
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL: str = os.environ.get("DEMO_BASE_URL", "http://localhost:8000/api")
STEP_DELAY: float = float(os.environ.get("DEMO_STEP_DELAY", "3"))
HTTP_TIMEOUT: float = 30.0

# ANSI colour helpers (disabled when not a TTY)
_COLOUR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOUR else text


def cyan(t: str) -> str:
    return _c("36", t)


def green(t: str) -> str:
    return _c("32", t)


def yellow(t: str) -> str:
    return _c("33", t)


def red(t: str) -> str:
    return _c("31", t)


def bold(t: str) -> str:
    return _c("1", t)


def dim(t: str) -> str:
    return _c("2", t)


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

BANNER = r"""
  █████╗ ████████╗██╗  ██╗███████╗███╗   ██╗ █████╗
 ██╔══██╗╚══██╔══╝██║  ██║██╔════╝████╗  ██║██╔══██╗
 ███████║   ██║   ███████║█████╗  ██╔██╗ ██║███████║
 ██╔══██║   ██║   ██╔══██║██╔══╝  ██║╚██╗██║██╔══██║
 ██║  ██║   ██║   ██║  ██║███████╗██║ ╚████║██║  ██║
 ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝
         C5ISR — OODA Cycle Demo  (PHANTOM-EYE)
"""


# ---------------------------------------------------------------------------
# Low-level HTTP helpers
# ---------------------------------------------------------------------------

async def _request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    **kwargs: Any,
) -> httpx.Response:
    """Issue an HTTP request, retrying once on non-200 responses."""
    url = f"{BASE_URL}{path}"
    for attempt in range(1, 3):  # up to 2 attempts
        try:
            resp = await client.request(method, url, timeout=HTTP_TIMEOUT, **kwargs)
            if resp.status_code < 400:
                return resp
            if attempt == 1:
                print(
                    yellow(
                        f"  [retry] {method} {path} → HTTP {resp.status_code} "
                        f"(attempt {attempt}/2)"
                    )
                )
                await asyncio.sleep(1)
            else:
                print(
                    red(
                        f"  [skip]  {method} {path} → HTTP {resp.status_code} "
                        f"after retry — skipping step"
                    )
                )
                return resp
        except httpx.RequestError as exc:
            if attempt == 1:
                print(
                    yellow(
                        f"  [retry] {method} {path} — connection error: {exc} "
                        f"(attempt {attempt}/2)"
                    )
                )
                await asyncio.sleep(1)
            else:
                print(
                    red(
                        f"  [skip]  {method} {path} — connection error after retry: {exc}"
                    )
                )
                # Return a synthetic 503 response so callers can inspect .is_error
                return httpx.Response(503, text=str(exc))
    # Should not reach here, but satisfy type checker
    return httpx.Response(503, text="Exhausted retries")


async def get(client: httpx.AsyncClient, path: str, **kwargs: Any) -> httpx.Response:
    return await _request(client, "GET", path, **kwargs)


async def post(client: httpx.AsyncClient, path: str, **kwargs: Any) -> httpx.Response:
    return await _request(client, "POST", path, **kwargs)


# ---------------------------------------------------------------------------
# Pretty-printing helpers
# ---------------------------------------------------------------------------

def _print_step_header(step: int, title: str, phase: str) -> None:
    sep = "─" * 60
    print()
    print(bold(cyan(sep)))
    print(bold(cyan(f"  STEP {step}/6 — {phase.upper()} — {title}")))
    print(bold(cyan(sep)))


def _print_expected(text: str) -> None:
    print(dim(f"  Expected : {text}"))


def _print_result(resp: httpx.Response, extract_fn=None) -> None:
    """Print the HTTP status and optionally a parsed excerpt of the body."""
    status_str = f"HTTP {resp.status_code}"
    if resp.is_error:
        print(red(f"  Result   : {status_str} — {resp.text[:200]}"))
        return

    print(green(f"  Result   : {status_str} OK"))

    if extract_fn is None:
        return

    try:
        body = resp.json()
        summary = extract_fn(body)
        if summary:
            # Indent multi-line summaries
            for line in textwrap.wrap(str(summary), width=70):
                print(f"             {line}")
    except Exception as exc:
        print(yellow(f"  (could not parse response body: {exc})"))


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------

async def step1_observe(client: httpx.AsyncClient, op_id: str) -> None:
    """OBSERVE — Trigger first OODA cycle via POST /ooda/trigger."""
    _print_step_header(1, "Trigger first OODA cycle", "OBSERVE")
    _print_expected(
        "API triggers Observe → Orient → Decide → Act; "
        "returns new ooda_iteration record with iteration_number ≥ 2"
    )
    resp = await post(client, f"/operations/{op_id}/ooda/trigger")

    def extract(body: Any) -> str | None:
        if isinstance(body, dict):
            phase = body.get("phase", body.get("current_phase", "?"))
            iter_num = body.get("iteration_number", body.get("ooda_iteration_count", "?"))
            summary = body.get("observe_summary") or body.get("summary") or ""
            return (
                f"phase={phase}  iteration={iter_num}  "
                f"observe_summary={summary[:80]!r}"
            )
        return None

    _print_result(resp, extract)


async def step2_orient(client: httpx.AsyncClient, op_id: str) -> None:
    """ORIENT — Retrieve latest PentestGPT recommendation."""
    _print_step_header(2, "Check PentestGPT recommendation", "ORIENT")
    _print_expected(
        "Returns latest recommendation with confidence > 0, "
        "recommended technique, and situation_assessment text"
    )
    resp = await get(client, f"/operations/{op_id}/recommendations/latest")

    def extract(body: Any) -> str | None:
        if isinstance(body, dict):
            tech_id = body.get("recommended_technique_id", "?")
            confidence = body.get("confidence", "?")
            assessment = (body.get("situation_assessment") or "")[:80]
            return (
                f"technique={tech_id}  confidence={confidence}  "
                f"assessment={assessment!r}"
            )
        return None

    _print_result(resp, extract)


async def step3_decide(client: httpx.AsyncClient, op_id: str) -> None:
    """DECIDE — Review C5ISR domain status to inform decision."""
    _print_step_header(3, "Review C5ISR domain status", "DECIDE")
    _print_expected(
        "Returns 6 C5ISR domains (command, control, comms, computers, "
        "cyber, isr) with health_pct values"
    )
    resp = await get(client, f"/operations/{op_id}/c5isr")

    def extract(body: Any) -> str | None:
        if not isinstance(body, list):
            return None
        parts = [f"{d.get('domain','?')}={d.get('health_pct','?')}%" for d in body]
        return "  |  ".join(parts)

    _print_result(resp, extract)


async def step4_act(client: httpx.AsyncClient, op_id: str) -> None:
    """ACT — Check technique execution history (matrix view)."""
    _print_step_header(4, "Check execution history (techniques)", "ACT")
    _print_expected(
        "Returns technique list with latest_status per technique; "
        "at least one entry should show status='success'"
    )
    # The spec references /techniques/matrix; fall back to /techniques
    resp = await get(client, f"/operations/{op_id}/techniques/matrix")
    if resp.status_code == 404:
        print(yellow("  [info]   /techniques/matrix not found — using /techniques"))
        resp = await get(client, f"/operations/{op_id}/techniques")

    def extract(body: Any) -> str | None:
        if not isinstance(body, list):
            return None
        statuses = [
            f"{t.get('mitre_id','?')}={t.get('latest_status') or 'none'}"
            for t in body
        ]
        return "  |  ".join(statuses)

    _print_result(resp, extract)


async def step5_observe2(client: httpx.AsyncClient, op_id: str) -> None:
    """OBSERVE round 2 — Trigger second OODA cycle."""
    _print_step_header(5, "Trigger second OODA cycle", "OBSERVE (round 2)")
    _print_expected(
        "API runs another Observe → Orient → Decide → Act cycle; "
        "iteration_number should increment from previous cycle"
    )
    resp = await post(client, f"/operations/{op_id}/ooda/trigger")

    def extract(body: Any) -> str | None:
        if isinstance(body, dict):
            phase = body.get("phase", body.get("current_phase", "?"))
            iter_num = body.get("iteration_number", body.get("ooda_iteration_count", "?"))
            act_summary = body.get("act_summary") or body.get("summary") or ""
            return (
                f"phase={phase}  iteration={iter_num}  "
                f"act_summary={act_summary[:80]!r}"
            )
        return None

    _print_result(resp, extract)


async def step6_orient2(client: httpx.AsyncClient, op_id: str) -> None:
    """ORIENT round 2 — Final operation state + OODA timeline."""
    _print_step_header(6, "Final state + OODA timeline", "ORIENT (round 2)")
    _print_expected(
        "Operation shows updated ooda_iteration_count ≥ 2; "
        "timeline lists per-phase entries for all completed iterations"
    )

    # 6a — operation state
    resp_op = await get(client, f"/operations/{op_id}")
    print(bold("  [6a] Operation state:"))

    def extract_op(body: Any) -> str | None:
        if isinstance(body, dict):
            code = body.get("code", "?")
            phase = body.get("current_ooda_phase", "?")
            iters = body.get("ooda_iteration_count", "?")
            status = body.get("status", "?")
            return (
                f"code={code}  status={status}  "
                f"ooda_phase={phase}  iteration_count={iters}"
            )
        return None

    _print_result(resp_op, extract_op)

    # 6b — OODA timeline
    print(bold("  [6b] OODA timeline:"))
    _print_expected("List of per-phase timeline entries across all iterations")
    resp_tl = await get(client, f"/operations/{op_id}/ooda/timeline")

    def extract_timeline(body: Any) -> str | None:
        if not isinstance(body, list):
            return None
        entries = [
            f"iter{e.get('iteration_number','?')}:{e.get('phase','?')}"
            for e in body
        ]
        return "  ".join(entries)

    _print_result(resp_tl, extract_timeline)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

async def _check_health(client: httpx.AsyncClient) -> bool:
    """Return True if the API is healthy."""
    print(dim("Checking API health …"))
    try:
        resp = await client.get(f"{BASE_URL}/health", timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            print(green(f"  API is healthy: status={data.get('status','?')}"))
            services = data.get("services", {})
            for svc, state in services.items():
                colour = green if state in ("ok", "connected", "mock", "active", "claude") else yellow
                print(colour(f"  {svc:12s}: {state}"))
            return True
        print(red(f"  Health check failed: HTTP {resp.status_code}"))
        return False
    except httpx.RequestError as exc:
        print(red(f"  Cannot reach API at {BASE_URL}: {exc}"))
        return False


# ---------------------------------------------------------------------------
# Operation discovery
# ---------------------------------------------------------------------------

async def _get_operation_id(client: httpx.AsyncClient) -> str | None:
    """Return the first operation ID from GET /operations."""
    print(dim("Discovering first operation …"))
    try:
        resp = await client.get(f"{BASE_URL}/operations", timeout=10.0)
        if resp.status_code == 200:
            ops = resp.json()
            if ops:
                op = ops[0]
                op_id = op.get("id", "?")
                name = op.get("name", "?")
                code = op.get("code", "?")
                print(green(f"  Using operation: id={op_id}  code={code}  name={name}"))
                return op_id
            print(yellow("  No operations found in the database."))
        else:
            print(red(f"  GET /operations returned HTTP {resp.status_code}"))
    except httpx.RequestError as exc:
        print(red(f"  Could not fetch operations: {exc}"))
    return None


# ---------------------------------------------------------------------------
# Main demo runner
# ---------------------------------------------------------------------------

STEPS = [
    step1_observe,
    step2_orient,
    step3_decide,
    step4_act,
    step5_observe2,
    step6_orient2,
]


async def run_demo() -> None:
    """Execute the full 6-step OODA cycle demo."""
    print(bold(cyan(BANNER)))
    print(f"  Base URL   : {bold(BASE_URL)}")
    print(f"  Step delay : {bold(str(STEP_DELAY))} s")
    print(f"  Timeout    : {bold(str(HTTP_TIMEOUT))} s")
    print()

    async with httpx.AsyncClient() as client:
        # Pre-flight: health + operation ID
        if not await _check_health(client):
            print(
                red(
                    "\n[ABORT] API is not reachable. "
                    "Start the backend first: uvicorn app.main:app --reload\n"
                )
            )
            return

        op_id = await _get_operation_id(client)
        if not op_id:
            print(
                red(
                    "\n[ABORT] No operation found. "
                    "Run 'python -m app.seed.demo_scenario' first.\n"
                )
            )
            return

        print()
        print(bold("Starting 6-step OODA demo …"))

        for i, step_fn in enumerate(STEPS, start=1):
            await step_fn(client, op_id)
            if i < len(STEPS):
                print(dim(f"\n  Waiting {STEP_DELAY}s before next step …"))
                await asyncio.sleep(STEP_DELAY)

    print()
    print(bold(green("=" * 60)))
    print(bold(green("  DEMO COMPLETE — All 6 OODA steps executed.")))
    print(bold(green("=" * 60)))
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(run_demo())
