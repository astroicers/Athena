# Copyright 2026 Athena Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Target and topology endpoints."""

import aiosqlite
from fastapi import APIRouter, Depends

from app.database import get_db
from app.models import Target
from app.models.api_schemas import TopologyData, TopologyEdge, TopologyNode
from app.routers._deps import ensure_operation

router = APIRouter()


def _row_to_target(row: aiosqlite.Row) -> Target:
    return Target(
        id=row["id"],
        hostname=row["hostname"],
        ip_address=row["ip_address"],
        os=row["os"],
        role=row["role"],
        network_segment=row["network_segment"],
        is_compromised=bool(row["is_compromised"]),
        privilege_level=row["privilege_level"],
        operation_id=row["operation_id"],
    )


@router.get("/operations/{operation_id}/targets", response_model=list[Target])
async def list_targets(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    cursor = await db.execute(
        "SELECT * FROM targets WHERE operation_id = ? ORDER BY hostname",
        (operation_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_target(r) for r in rows]


@router.get("/operations/{operation_id}/topology", response_model=TopologyData)
async def get_topology(
    operation_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Build topology graph from targets and agents."""
    db.row_factory = aiosqlite.Row
    await ensure_operation(db, operation_id)

    # Targets → host nodes
    cursor = await db.execute(
        "SELECT * FROM targets WHERE operation_id = ?", (operation_id,)
    )
    target_rows = await cursor.fetchall()

    nodes: list[TopologyNode] = []
    for t in target_rows:
        nodes.append(
            TopologyNode(
                id=t["id"],
                label=f"{t['hostname']} ({t['ip_address']})",
                type="host",
                data={
                    "hostname": t["hostname"],
                    "ip_address": t["ip_address"],
                    "os": t["os"],
                    "role": t["role"],
                    "is_compromised": bool(t["is_compromised"]),
                    "privilege_level": t["privilege_level"],
                },
            )
        )

    # Agents → agent nodes + edges to their host
    cursor = await db.execute(
        "SELECT * FROM agents WHERE operation_id = ?", (operation_id,)
    )
    agent_rows = await cursor.fetchall()

    edges: list[TopologyEdge] = []
    for a in agent_rows:
        nodes.append(
            TopologyNode(
                id=a["id"],
                label=a["paw"],
                type="agent",
                data={
                    "paw": a["paw"],
                    "status": a["status"],
                    "privilege": a["privilege"],
                    "platform": a["platform"],
                },
            )
        )
        edges.append(
            TopologyEdge(
                source=a["id"],
                target=a["host_id"],
                label=f"beacon ({a['status']})",
            )
        )

    return TopologyData(nodes=nodes, edges=edges)
