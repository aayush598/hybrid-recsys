from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class DatabasePool:
    """Optimized async database connection pool.

    Production configuration:
    - QueuePool for connection reuse (avoids connection overhead)
    - Pool sizing based on CPU cores and workload
    - Pre-ping for connection health
    - Connection recycling to prevent stale connections
    - Read replica support for scaling reads

    For SQLite: uses NullPool (no pooling needed, file-based)
    For PostgreSQL: uses QueuePool with configurable size
    """

    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker | None = None
        self._read_engine: AsyncEngine | None = None
        self._read_session_factory: async_sessionmaker | None = None

    def initialize(
        self,
        database_url: str | None = None,
        pool_size: int = 20,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        read_replica_url: str | None = None,
    ) -> None:
        """Initialize the database engine with optimized pool settings."""
        url = database_url or settings.DATABASE_URL

        if "sqlite" in url:
            pool_class = NullPool
            pool_kwargs = {}
        else:
            pool_class = QueuePool
            pool_kwargs = {
                "pool_size": pool_size,
                "max_overflow": max_overflow,
                "pool_timeout": pool_timeout,
                "pool_recycle": pool_recycle,
                "pool_pre_ping": True,
            }

        self._engine = create_async_engine(
            url,
            poolclass=pool_class,
            echo=settings.DATABASE_ECHO,
            **pool_kwargs,
        )

        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        if read_replica_url:
            self._read_engine = create_async_engine(
                read_replica_url,
                poolclass=pool_class,
                pool_size=pool_size * 2,
                max_overflow=max_overflow * 2,
                pool_pre_ping=True,
            )
            self._read_session_factory = async_sessionmaker(
                self._read_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

        logger.info(
            "Database pool initialized",
            url=url.split("@")[-1] if "@" in url else url,
            pool_size=pool_size,
            has_read_replica=read_replica_url is not None,
        )

    @asynccontextmanager
    async def get_session(self, read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session from the pool."""
        factory = (
            self._read_session_factory
            if read_only and self._read_session_factory
            else self._session_factory
        )

        if factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    async def execute_batch(
        self,
        operations: list,
        batch_size: int = 1000,
    ) -> int:
        """Execute a batch of operations efficiently."""
        total = 0
        async with self.get_session() as session:
            for i, op in enumerate(operations):
                session.add(op)
                total += 1

                if (i + 1) % batch_size == 0:
                    await session.flush()
                    logger.info(f"Batch progress: {i + 1}/{len(operations)}")

            await session.commit()
        return total

    async def close(self) -> None:
        """Dispose of all connections."""
        if self._engine:
            await self._engine.dispose()
        if self._read_engine:
            await self._read_engine.dispose()
        logger.info("Database pool closed")

    @property
    def pool_status(self) -> dict:
        """Get pool health status."""
        if not self._engine:
            return {"status": "not_initialized"}

        pool = self._engine.pool
        status = {
            "status": "healthy",
            "pool_size": getattr(pool, "size", lambda: "N/A")(),
            "checked_out": getattr(pool, "checkedout", lambda: "N/A")(),
            "checked_in": getattr(pool, "checkedin", lambda: "N/A")(),
            "overflow": getattr(pool, "overflow", lambda: "N/A")(),
        }
        return status


db_pool = DatabasePool()
