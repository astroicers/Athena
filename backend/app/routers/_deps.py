# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Shared dependencies for router modules."""

import asyncpg
from fastapi import HTTPException


async def ensure_operation(db: asyncpg.Connection, operation_id: str) -> None:
    """Raise 404 if *operation_id* does not exist."""
    row = await db.fetchrow("SELECT id FROM operations WHERE id = $1", operation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Operation not found")
