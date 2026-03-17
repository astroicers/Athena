"""Rich renderers for all Athena CLI display views."""

from __future__ import annotations

import json as _json
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# ── Color Palette ─────────────────────────────────────────────────

PHASE_COLORS: dict[str, str] = {
    "observe": "cyan",
    "orient": "yellow",
    "decide": "magenta",
    "act": "green",
}

STATUS_COLORS: dict[str, str] = {
    "operational": "green",
    "active": "cyan",
    "nominal": "green",
    "engaged": "cyan",
    "scanning": "cyan",
    "degraded": "yellow",
    "offline": "red",
    "critical": "red",
}

OP_STATUS_COLORS: dict[str, str] = {
    "planning": "blue",
    "active": "green",
    "paused": "yellow",
    "completed": "dim",
    "aborted": "red",
}


def _trunc(text: str | None, max_len: int = 80) -> str:
    if not text:
        return "-"
    return text[:max_len] + ("..." if len(text) > max_len else "")


def _health_bar(pct: float, width: int = 14) -> Text:
    filled = int(pct / 100 * width)
    empty = width - filled
    color = "green" if pct >= 75 else "yellow" if pct >= 50 else "red"
    bar = Text()
    bar.append("\u2588" * filled, style=color)
    bar.append("\u2591" * empty, style="dim")
    return bar


def _fmt_time(ts: str | None) -> str:
    if not ts:
        return "-"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S")
    except (ValueError, AttributeError):
        return str(ts)[:8]


# ── JSON output ───────────────────────────────────────────────────

def print_json(data: Any) -> None:
    console.print_json(_json.dumps(data, default=str))


# ── Operations ────────────────────────────────────────────────────

def render_operations_list(ops: list[dict]) -> None:
    if not ops:
        console.print("[dim]No operations found.[/]")
        return
    table = Table(title="Operations", show_lines=False, padding=(0, 1))
    table.add_column("CODE", style="bold")
    table.add_column("CODENAME", style="cyan")
    table.add_column("STATUS")
    table.add_column("PHASE")
    table.add_column("ITER", justify="right")
    table.add_column("THREAT", justify="right")
    table.add_column("SUCCESS", justify="right")
    for op in ops:
        status = op.get("status", "")
        sc = OP_STATUS_COLORS.get(status, "white")
        phase = op.get("current_ooda_phase", "")
        pc = PHASE_COLORS.get(phase, "white")
        table.add_row(
            op.get("code", ""),
            op.get("codename", ""),
            f"[{sc}]{status}[/{sc}]",
            f"[{pc}]{phase}[/{pc}]",
            str(op.get("ooda_iteration_count", 0)),
            f"{op.get('threat_level', 0):.1f}",
            f"{op.get('success_rate', 0):.0f}%",
        )
    console.print(table)


def render_operation_detail(op: dict) -> None:
    status = op.get("status", "")
    sc = OP_STATUS_COLORS.get(status, "white")
    phase = op.get("current_ooda_phase", "")
    pc = PHASE_COLORS.get(phase, "white")

    lines = [
        f"[bold]Code:[/]     {op.get('code', '')}",
        f"[bold]Name:[/]     {op.get('name', '')}",
        f"[bold]Status:[/]   [{sc}]{status}[/{sc}]",
        f"[bold]Phase:[/]    [{pc}]{phase}[/{pc}]",
        f"[bold]Profile:[/]  {op.get('mission_profile', '')}",
        f"[bold]Auto:[/]     {op.get('automation_mode', '')}",
        "",
        f"[bold]Iterations:[/]  {op.get('ooda_iteration_count', 0)}",
        f"[bold]Threat:[/]      {op.get('threat_level', 0):.1f} / 10",
        f"[bold]Success:[/]     {op.get('success_rate', 0):.0f}%",
        f"[bold]Agents:[/]      {op.get('active_agents', 0)}",
        f"[bold]Techniques:[/]  {op.get('techniques_executed', 0)} / {op.get('techniques_total', 0)}",
        "",
        f"[bold]Intent:[/] {_trunc(op.get('strategic_intent', ''), 120)}",
    ]
    panel = Panel(
        "\n".join(lines),
        title=f"[bold]{op.get('codename', 'UNKNOWN')}[/]",
        border_style="blue",
    )
    console.print(panel)


# ── OODA ──────────────────────────────────────────────────────────

def render_ooda_dashboard(data: dict) -> None:
    phase = data.get("current_phase", "")
    pc = PHASE_COLORS.get(phase, "white")
    iter_count = data.get("iteration_count", 0)

    latest = data.get("latest_iteration")
    if latest:
        _render_ooda_iteration_panel(latest, title_extra=f"Iteration #{iter_count}")
    else:
        console.print(
            Panel(
                f"[{pc}]Phase: {phase}[/{pc}]  |  Iterations: {iter_count}\n\n"
                "[dim]No iterations completed yet.[/]",
                title="OODA",
                border_style=pc,
            )
        )


def _render_ooda_iteration_panel(it: dict, *, title_extra: str = "") -> None:
    phase = it.get("phase", "")
    pc = PHASE_COLORS.get(phase, "white")
    num = it.get("iteration_number", "?")
    title = f"OODA  #{num}"
    if title_extra:
        title = f"OODA  {title_extra}"

    sections = []
    for p in ("observe", "orient", "decide", "act"):
        color = PHASE_COLORS[p]
        summary = it.get(f"{p}_summary") or "[dim]pending[/]"
        sections.append(
            Panel(
                summary,
                title=f"[bold]{p.upper()}[/]",
                border_style=color,
                padding=(0, 1),
            )
        )

    from rich.columns import Columns  # noqa: PLC0415

    # Stack vertically
    inner = "\n".join(str(s) for s in sections)
    panel = Panel(
        inner if not sections else sections,  # type: ignore[arg-type]
        title=f"[bold]{title}[/]  Phase: [{pc}]{phase}[/{pc}]",
        border_style=pc,
    )
    # Rich can render a list of renderables in a Panel via Group
    from rich.console import Group  # noqa: PLC0415

    console.print(
        Panel(
            Group(*sections),
            title=f"[bold]{title}[/]  Phase: [{pc}]{phase}[/{pc}]",
            border_style=pc,
        )
    )


def render_ooda_history(iterations: list[dict]) -> None:
    if not iterations:
        console.print("[dim]No OODA iterations found.[/]")
        return
    table = Table(title="OODA History", show_lines=True, padding=(0, 1))
    table.add_column("#", justify="right", style="bold")
    table.add_column("PHASE")
    table.add_column("OBSERVE", max_width=30)
    table.add_column("ORIENT", max_width=30)
    table.add_column("DECIDE", max_width=30)
    table.add_column("ACT", max_width=30)
    table.add_column("TIME")

    for it in iterations:
        phase = it.get("phase", "")
        pc = PHASE_COLORS.get(phase, "white")
        table.add_row(
            str(it.get("iteration_number", "")),
            f"[{pc}]{phase}[/{pc}]",
            _trunc(it.get("observe_summary"), 30),
            _trunc(it.get("orient_summary"), 30),
            _trunc(it.get("decide_summary"), 30),
            _trunc(it.get("act_summary"), 30),
            _fmt_time(it.get("completed_at") or it.get("started_at")),
        )
    console.print(table)


def render_ooda_timeline(entries: list[dict]) -> None:
    if not entries:
        console.print("[dim]No timeline entries.[/]")
        return
    for entry in entries:
        phase = entry.get("phase", "")
        color = PHASE_COLORS.get(phase, "white")
        ts = _fmt_time(entry.get("timestamp") or entry.get("started_at"))
        summary = entry.get("summary", entry.get("detail", ""))
        console.print(f"  [{color}]{ts}[/{color}]  [{color}]{phase:>7}[/{color}]  {summary}")


# ── C5ISR ─────────────────────────────────────────────────────────

def render_c5isr_overview(domains: list[dict]) -> None:
    if not domains:
        console.print("[dim]No C5ISR data.[/]")
        return
    table = Table(show_header=True, padding=(0, 1), show_lines=False)
    table.add_column("DOMAIN", style="bold", min_width=10)
    table.add_column("STATUS", min_width=12)
    table.add_column("HEALTH", justify="right", min_width=6)
    table.add_column("", min_width=14)  # bar
    table.add_column("METRIC")

    # Sort by canonical domain order
    order = ["command", "control", "comms", "computers", "cyber", "isr"]
    sorted_domains = sorted(domains, key=lambda d: (
        order.index(d.get("domain", "")) if d.get("domain", "") in order else 99
    ))

    for d in sorted_domains:
        status = d.get("status", "")
        sc = STATUS_COLORS.get(status, "white")
        health = d.get("health_pct", 0.0)
        num = d.get("numerator")
        den = d.get("denominator")
        label = d.get("metric_label", "")
        metric = f"{num}/{den} {label}" if num is not None and den is not None else label

        table.add_row(
            d.get("domain", "").upper(),
            f"[{sc}]{status.upper()}[/{sc}]",
            f"{health:.0f}%",
            _health_bar(health),
            metric,
        )

    console.print(Panel(table, title="[bold]C5ISR Domain Health[/]", border_style="blue"))


def render_c5isr_report(report: dict) -> None:
    domain = report.get("domain", "")
    health = report.get("health_pct", 0.0)
    status = report.get("status", "")
    sc = STATUS_COLORS.get(status, "white")

    lines = [f"[bold]Status:[/] [{sc}]{status.upper()}[/{sc}]  Health: {health:.1f}%\n"]

    # Metrics
    metrics = report.get("metrics", [])
    if metrics:
        lines.append("[bold]Metrics:[/]")
        for m in metrics:
            name = m.get("name", "")
            val = m.get("value", 0)
            weight = m.get("weight", 0)
            num = m.get("numerator", "")
            den = m.get("denominator", "")
            lines.append(f"  {name}: {val:.1f}  (weight: {weight:.2f}, {num}/{den})")
        lines.append("")

    # Risks
    risks = report.get("risks", [])
    if risks:
        lines.append("[bold]Risks:[/]")
        for r in risks:
            sev = r.get("severity", "INFO")
            rc = "red" if sev == "CRIT" else "yellow" if sev == "WARN" else "dim"
            lines.append(f"  [{rc}][{sev}][/{rc}] {r.get('message', '')}")
        lines.append("")

    # Recommendations
    recs = report.get("recommendations", [])
    if recs:
        lines.append("[bold]Recommendations:[/]")
        for rec in recs:
            lines.append(f"  - {rec}")

    console.print(
        Panel("\n".join(lines), title=f"[bold]{domain.upper()} Report[/]", border_style="blue")
    )


# ── Recon ─────────────────────────────────────────────────────────

def render_recon_result(result: dict) -> None:
    scan_id = result.get("scan_id", "?")[:8]
    ip = result.get("ip_address", "?")
    os_guess = result.get("os_guess") or "unknown"
    duration = result.get("scan_duration_sec", 0)
    status = result.get("status", "")

    header = f"Target: {ip}    OS: {os_guess}    Duration: {duration:.1f}s    Status: {status}"

    # Services table
    services = result.get("services", [])
    svc_table = Table(show_header=True, padding=(0, 1), show_lines=False)
    svc_table.add_column("PORT", justify="right")
    svc_table.add_column("PROTO")
    svc_table.add_column("SERVICE")
    svc_table.add_column("VERSION")
    for svc in services:
        svc_table.add_row(
            str(svc.get("port", "")),
            svc.get("protocol", ""),
            svc.get("service", ""),
            svc.get("version", ""),
        )

    # Initial access
    ia = result.get("initial_access", {})
    ia_lines = []
    if ia:
        method = ia.get("method", "none")
        cred = ia.get("credential") or "-"
        agent = "YES" if ia.get("agent_deployed") else "NO"
        ia_lines = [
            f"Method: {method}   Cred: {cred}",
            f"Agent: {agent}     Facts: {result.get('facts_written', 0)}",
        ]

    from rich.console import Group  # noqa: PLC0415

    parts: list = [header, "", svc_table]
    if ia_lines:
        parts.append("")
        parts.append(Panel("\n".join(ia_lines), title="Initial Access", border_style="dim"))

    console.print(
        Panel(
            Group(*parts),
            title=f"[bold]RECON[/]  scan {scan_id}",
            border_style="green" if status == "completed" else "red",
        )
    )


def render_recon_status(data: dict) -> None:
    status = data.get("status", "unknown")
    scan_id = data.get("scan_id", data.get("id", "?"))[:8]
    color = "green" if status == "completed" else "yellow" if status in ("queued", "running") else "red"
    console.print(f"[{color}]Scan {scan_id}: {status}[/{color}]")
    if status == "completed":
        console.print(f"  Services: {data.get('services_found', '?')}  Facts: {data.get('facts_written', '?')}")


# ── Intel (Targets / Facts / Recommendations) ────────────────────

FACT_CATEGORY_COLORS: dict[str, str] = {
    "credential": "red",
    "service": "cyan",
    "network": "blue",
    "host": "green",
    "vulnerability": "yellow",
    "web": "magenta",
    "osint": "dim",
    "file": "dim",
    "poc": "green",
}


def render_targets_list(targets: list[dict]) -> None:
    if not targets:
        console.print("[dim]No targets found.[/]")
        return
    table = Table(title="Targets", show_lines=False, padding=(0, 1))
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("HOSTNAME")
    table.add_column("IP")
    table.add_column("OS")
    table.add_column("ROLE")
    table.add_column("COMPROMISED")
    table.add_column("PRIVILEGE")
    table.add_column("ACTIVE")

    for t in targets:
        comp = t.get("is_compromised", False)
        comp_str = "[green]YES[/]" if comp else "[dim]NO[/]"
        active = t.get("is_active", False)
        active_str = "[green]YES[/]" if active else "[dim]NO[/]"
        table.add_row(
            str(t.get("id", ""))[:8],
            t.get("hostname", "-"),
            t.get("ip_address", "-"),
            t.get("os") or "-",
            t.get("role", "-"),
            comp_str,
            t.get("privilege_level") or "-",
            active_str,
        )
    console.print(table)


def render_facts_list(facts: list[dict]) -> None:
    if not facts:
        console.print("[dim]No facts collected.[/]")
        return
    # Sort by category
    sorted_facts = sorted(facts, key=lambda f: f.get("category", ""))

    table = Table(title=f"Facts ({len(facts)})", show_lines=False, padding=(0, 1))
    table.add_column("CATEGORY", min_width=10)
    table.add_column("TRAIT")
    table.add_column("VALUE", max_width=50)
    table.add_column("TARGET", style="dim", max_width=8)
    table.add_column("TIME", style="dim")

    for f in sorted_facts:
        cat = f.get("category", "")
        cc = FACT_CATEGORY_COLORS.get(cat, "white")
        table.add_row(
            f"[{cc}]{cat}[/{cc}]",
            f.get("trait", ""),
            _trunc(f.get("value", ""), 50),
            str(f.get("source_target_id") or "")[:8],
            _fmt_time(f.get("collected_at")),
        )
    console.print(table)


def render_recommendation(rec: dict | None) -> None:
    if not rec:
        console.print("[dim]No recommendation available.[/]")
        return

    tech_id = rec.get("recommended_technique_id", "?")
    conf = rec.get("confidence", 0)
    assessment = rec.get("situation_assessment", "")

    # Header
    lines = [
        f"[bold]Recommended:[/] {tech_id}  Confidence: [bold]{conf:.0%}[/]",
        "",
        f"[bold]Assessment:[/]",
        _trunc(assessment, 300),
        "",
    ]

    # Options table
    options = rec.get("options", [])
    if options:
        opt_table = Table(show_header=True, padding=(0, 1), show_lines=False)
        opt_table.add_column("#", justify="right", style="bold")
        opt_table.add_column("TECHNIQUE")
        opt_table.add_column("NAME", max_width=35)
        opt_table.add_column("CONF", justify="right")
        opt_table.add_column("RISK")
        opt_table.add_column("ENGINE")

        for i, opt in enumerate(options, 1):
            risk = opt.get("risk_level", "")
            rc = "red" if risk == "high" else "yellow" if risk == "medium" else "green"
            opt_table.add_row(
                str(i),
                opt.get("technique_id", ""),
                _trunc(opt.get("technique_name", ""), 35),
                f"{opt.get('confidence', 0):.0%}",
                f"[{rc}]{risk}[/{rc}]",
                opt.get("recommended_engine", ""),
            )

        from rich.console import Group  # noqa: PLC0415
        console.print(
            Panel(
                Group("\n".join(lines), opt_table),
                title="[bold]Orient Recommendation[/]",
                border_style="magenta",
            )
        )
    else:
        console.print(
            Panel("\n".join(lines), title="[bold]Orient Recommendation[/]", border_style="magenta")
        )


# ── Live Events ───────────────────────────────────────────────────

EVENT_COLORS: dict[str, str] = {
    "ooda.phase": "cyan",
    "ooda.completed": "magenta",
    "c5isr.update": "yellow",
    "fact.new": "green",
    "recon.started": "blue",
    "recon.progress": "blue",
    "recon.completed": "green",
    "recon.failed": "red",
    "opsec.alert": "red",
    "decision.result": "magenta",
    "log.new": "dim",
}


def render_ws_event(event_type: str, data: dict, timestamp: str) -> None:
    ts = _fmt_time(timestamp)
    color = EVENT_COLORS.get(event_type, "white")
    # Build summary from data
    summary = _event_summary(event_type, data)
    console.print(f"[dim]{ts}[/] [{color}]{event_type:<20}[/{color}] {summary}")


def _event_summary(event_type: str, data: dict) -> str:
    if event_type == "ooda.phase":
        return f"Phase -> {data.get('phase', '?')} (iteration #{data.get('iteration_number', '?')})"
    if event_type == "ooda.completed":
        return f"Iteration #{data.get('iteration_number', '?')} complete"
    if event_type == "c5isr.update":
        parts = []
        for d in data.get("domains", [data]) if isinstance(data, dict) else []:
            domain = d.get("domain", "?")
            health = d.get("health_pct", "?")
            parts.append(f"{domain}={health}%")
        return "  ".join(parts) if parts else str(data)[:80]
    if event_type == "fact.new":
        return f"{data.get('category', '')}: {data.get('trait', '')} = {_trunc(data.get('value', ''), 50)}"
    if event_type == "recon.progress":
        return f"Phase {data.get('phase', '?')} ({data.get('step', '?')}/{data.get('total_steps', '?')})"
    if event_type == "recon.completed":
        return f"Scan complete: {data.get('services_found', '?')} services, {data.get('facts_written', '?')} facts"
    if event_type == "opsec.alert":
        return f"[red]{data.get('message', data.get('detail', str(data)[:80]))}[/]"
    if event_type == "decision.result":
        return f"confidence={data.get('confidence', '?')} auto={data.get('auto_approved', '?')}"
    if event_type == "log.new":
        return _trunc(data.get("message", ""), 60)
    return str(data)[:80]
