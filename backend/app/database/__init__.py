# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""Athena database package — PostgreSQL via asyncpg with connection pooling.

Public API:
    db_manager  — singleton DatabaseManager instance
    get_db      — FastAPI dependency that yields a connection from the pool
    init_db     — startup hook: create pool + run migrations + seed
"""

from app.database.manager import DatabaseManager, db_manager, get_db, init_db

__all__ = ["DatabaseManager", "db_manager", "get_db", "init_db"]
