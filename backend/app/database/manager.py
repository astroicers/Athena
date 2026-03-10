# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.

"""DatabaseManager — asyncpg connection pool + Alembic migrations.

Replaces the old monolithic database.py (aiosqlite).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages an asyncpg connection pool with lifecycle hooks."""

    def __init__(self, dsn: str | None = None, min_size: int = 5, max_size: int = 20):
        self._dsn = dsn or settings.DATABASE_URL
        self._min_size = min_size
        self._max_size = max_size
        self._pool: asyncpg.Pool | None = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("DatabaseManager not started — call startup() first")
        return self._pool

    async def startup(self) -> None:
        """Create the connection pool."""
        logger.info("Creating asyncpg pool: %s (min=%d, max=%d)", self._dsn, self._min_size, self._max_size)
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=self._min_size,
            max_size=self._max_size,
            command_timeout=60,
        )
        logger.info("asyncpg pool ready")

    async def shutdown(self) -> None:
        """Close all connections in the pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("asyncpg pool closed")

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Acquire a connection from the pool."""
        async with self.pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Acquire a connection and wrap it in a transaction (auto commit/rollback)."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn

    async def execute(self, query: str, *args: Any) -> str:
        """Execute a query and return the status string."""
        async with self.connection() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        """Execute a query and return all rows."""
        async with self.connection() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        """Execute a query and return a single row (or None)."""
        async with self.connection() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        """Execute a query and return the first column of the first row."""
        async with self.connection() as conn:
            return await conn.fetchval(query, *args)


# ---------------------------------------------------------------------------
# Singleton instance used throughout the application
# ---------------------------------------------------------------------------
db_manager = DatabaseManager()


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI dependency — yields a pooled connection.

    Usage in routers:
        async def endpoint(db: asyncpg.Connection = Depends(get_db)):
    """
    async with db_manager.connection() as conn:
        yield conn


async def init_db() -> None:
    """Start the pool and run Alembic migrations, then seed if needed."""
    await db_manager.startup()

    # Run Alembic migrations programmatically
    from alembic import command
    from alembic.config import Config

    import importlib.resources
    from pathlib import Path

    alembic_dir = Path(__file__).resolve().parent.parent.parent / "alembic"
    alembic_cfg = Config(str(alembic_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    # Run upgrade in a thread to avoid blocking the event loop
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: command.upgrade(alembic_cfg, "head"))
    logger.info("Alembic migrations applied")

    # Seed data if operations table is empty
    from app.database.seed import seed_if_empty
    await seed_if_empty(db_manager)
