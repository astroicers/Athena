# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Mission report export endpoint."""

import asyncpg
from fastapi import APIRouter, Depends

from app.database import get_db
from app.models.report import PentestReport
from app.routers._deps import ensure_operation

router = APIRouter()


def _rows_to_dicts(rows: list) -> list[dict]:
    return [dict(r) for r in rows]


@router.get("/operations/{operation_id}/report")


async def get_operation_report(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Export a complete mission report as JSON."""
    await ensure_operation(db, operation_id)

    # Operation summary
    row = await db.fetchrow(
        "SELECT * FROM operations WHERE id = $1", operation_id
    )
    operation = dict(row)

    # OODA timeline
    ooda_rows = await db.fetch(
        "SELECT * FROM ooda_iterations WHERE operation_id = $1 "
        "ORDER BY iteration_number",
        operation_id,
    )
    ooda_timeline = _rows_to_dicts(ooda_rows)

    # Technique executions
    exec_rows = await db.fetch(
        "SELECT * FROM technique_executions WHERE operation_id = $1 "
        "ORDER BY started_at",
        operation_id,
    )
    executions = _rows_to_dicts(exec_rows)

    # Facts
    fact_rows = await db.fetch(
        "SELECT * FROM facts WHERE operation_id = $1 ORDER BY collected_at",
        operation_id,
    )
    facts = _rows_to_dicts(fact_rows)

    # Recommendations
    rec_rows = await db.fetch(
        "SELECT * FROM recommendations WHERE operation_id = $1 "
        "ORDER BY created_at",
        operation_id,
    )
    recommendations = _rows_to_dicts(rec_rows)

    # C5ISR statuses
    c5_rows = await db.fetch(
        "SELECT * FROM c5isr_statuses WHERE operation_id = $1",
        operation_id,
    )
    c5isr = _rows_to_dicts(c5_rows)

    # Log entries
    log_rows = await db.fetch(
        "SELECT * FROM log_entries WHERE operation_id = $1 ORDER BY timestamp",
        operation_id,
    )
    logs = _rows_to_dicts(log_rows)

    # Mission steps
    step_rows = await db.fetch(
        "SELECT * FROM mission_steps WHERE operation_id = $1 ORDER BY step_number",
        operation_id,
    )
    mission_steps = _rows_to_dicts(step_rows)

    # Targets
    target_rows = await db.fetch(
        "SELECT * FROM targets WHERE operation_id = $1",
        operation_id,
    )
    targets = _rows_to_dicts(target_rows)

    # Agents
    agent_rows = await db.fetch(
        "SELECT * FROM agents WHERE operation_id = $1",
        operation_id,
    )
    agents = _rows_to_dicts(agent_rows)

    return {
        "operation": operation,
        "ooda_timeline": ooda_timeline,
        "executions": executions,
        "facts": facts,
        "recommendations": recommendations,
        "c5isr": c5isr,
        "logs": logs,
        "mission_steps": mission_steps,
        "targets": targets,
        "agents": agents,
    }


@router.get(
    "/operations/{operation_id}/report/structured",
    response_model=PentestReport,
)


async def get_structured_report(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
) -> PentestReport:
    """Generate a structured client-deliverable pentest report (JSON)."""
    await ensure_operation(db, operation_id)

    from app.services.report_generator import ReportGenerator
    return await ReportGenerator().generate(db, operation_id)


@router.get(
    "/operations/{operation_id}/report/markdown",
)


async def get_markdown_report(
    operation_id: str,
    db: asyncpg.Connection = Depends(get_db),
):
    """Generate a structured pentest report as downloadable Markdown."""
    from fastapi.responses import PlainTextResponse
    await ensure_operation(db, operation_id)

    from app.services.report_generator import ReportGenerator
    generator = ReportGenerator()
    report = await generator.generate(db, operation_id)
    md_content = generator.to_markdown(report)

    return PlainTextResponse(
        content=md_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="report-{operation_id}.md"'},
    )
