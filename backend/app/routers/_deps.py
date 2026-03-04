# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: [TODO: contact email]

"""Shared dependencies for router modules."""

import aiosqlite
from fastapi import HTTPException


async def ensure_operation(db: aiosqlite.Connection, operation_id: str) -> None:
    """Raise 404 if *operation_id* does not exist."""
    cursor = await db.execute("SELECT id FROM operations WHERE id = ?", (operation_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Operation not found")
