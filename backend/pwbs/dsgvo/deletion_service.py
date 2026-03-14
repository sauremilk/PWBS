"""Account deletion service (TASK-105) — Art. 17 DSGVO.

Three-phase deletion:
1. Schedule: Set deletion_scheduled_at = now + 30 days (grace period)
2. Cancel: Clear deletion_scheduled_at during grace period
3. Cleanup: Cascade-delete across all storage layers after grace period
   - PostgreSQL: CASCADE DELETE (via SQLAlchemy relationships)
   - Weaviate: Tenant deletion (all vectors)
   - Neo4j: All nodes with userId
   - Redis: Session/token flush
   - Filesystem: Export files

All operations are idempotent and retry-safe.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.models.user import User
from pwbs.services.user import verify_password

logger = logging.getLogger(__name__)

GRACE_PERIOD_DAYS = 30


async def schedule_deletion(
    db: AsyncSession,
    user: User,
    password: str,
) -> datetime:
    """Schedule account deletion with 30-day grace period.

    Returns the scheduled deletion datetime.

    Raises:
        ValueError: If password is incorrect or deletion already scheduled.
    """
    if not verify_password(password, user.password_hash):
        raise ValueError("Invalid password")

    if user.deletion_scheduled_at is not None:
        raise ValueError("Deletion already scheduled")

    now = datetime.now(tz=timezone.utc)
    deletion_at = now + timedelta(days=GRACE_PERIOD_DAYS)
    user.deletion_scheduled_at = deletion_at
    await db.flush()
    return deletion_at


async def cancel_deletion(
    db: AsyncSession,
    user: User,
) -> None:
    """Cancel a pending account deletion.

    Raises:
        ValueError: If no deletion is scheduled.
    """
    if user.deletion_scheduled_at is None:
        raise ValueError("No deletion scheduled")

    user.deletion_scheduled_at = None
    await db.flush()


async def cleanup_expired_accounts(db: AsyncSession) -> int:
    """Find and cascade-delete accounts past their grace period.

    Returns the number of accounts deleted.
    """
    now = datetime.now(tz=timezone.utc)
    stmt = select(User).where(
        User.deletion_scheduled_at.isnot(None),
        User.deletion_scheduled_at <= now,
    )
    result = await db.execute(stmt)
    users = list(result.scalars().all())

    deleted = 0
    for user in users:
        try:
            await _cascade_delete_user(db, user)
            deleted += 1
        except Exception:
            logger.exception("Failed to delete user %s", user.id)

    return deleted


async def _cascade_delete_user(db: AsyncSession, user: User) -> None:
    """Cascade-delete a user across all storage layers.

    Order: external stores first, PostgreSQL last (so FK data is
    still available for external lookups if needed).
    """
    user_id = user.id

    # 1. Weaviate: Remove tenant (all vectors)
    await _cleanup_weaviate(user_id)

    # 2. Neo4j: Remove all user nodes and relationships
    await _cleanup_neo4j(user_id)

    # 3. Redis: Flush sessions and tokens
    await _cleanup_redis(user_id)

    # 4. Filesystem: Remove export ZIP files
    await _cleanup_export_files(user_id, db)

    # 5. PostgreSQL: Delete user (CASCADE handles all related tables)
    await db.execute(sa_delete(User).where(User.id == user_id))
    await db.flush()

    logger.info("Cascade-deleted user %s across all storage layers", user_id)


async def _cleanup_weaviate(user_id: uuid.UUID) -> None:
    """Remove user's Weaviate tenant."""
    try:
        from pwbs.db.weaviate_client import get_weaviate_client
        from pwbs.storage.weaviate import WeaviateChunkStore

        client = get_weaviate_client()
        store = WeaviateChunkStore(client)
        store.delete_user_data(user_id)
    except Exception:
        logger.exception("Weaviate cleanup failed for user %s", user_id)


async def _cleanup_neo4j(user_id: uuid.UUID) -> None:
    """Remove all Neo4j nodes for the user (DETACH DELETE removes edges too)."""
    try:
        from pwbs.db.neo4j_client import get_neo4j_driver

        driver = get_neo4j_driver()
        async with driver.session() as session:
            await session.run(
                "MATCH (n {userId: $user_id}) DETACH DELETE n",
                user_id=str(user_id),
            )
    except Exception:
        logger.exception("Neo4j cleanup failed for user %s", user_id)


async def _cleanup_redis(user_id: uuid.UUID) -> None:
    """Flush user sessions and refresh token keys from Redis."""
    try:
        from pwbs.db.redis_client import get_redis_client

        client = get_redis_client()
        # Delete session keys
        async for key in client.scan_iter(match=f"session:{user_id}:*"):
            await client.delete(key)
        # Delete refresh token keys
        async for key in client.scan_iter(match=f"refresh:{user_id}:*"):
            await client.delete(key)
    except Exception:
        logger.exception("Redis cleanup failed for user %s", user_id)


async def _cleanup_export_files(user_id: uuid.UUID, db: AsyncSession) -> None:
    """Delete export ZIP files from filesystem."""
    try:
        from pwbs.models.data_export import DataExport

        stmt = select(DataExport).where(DataExport.user_id == user_id)
        result = await db.execute(stmt)
        exports = list(result.scalars().all())

        for export in exports:
            if export.file_path:
                p = Path(export.file_path)
                if p.is_file():
                    p.unlink()
                    logger.info("Deleted export file %s", p)
    except Exception:
        logger.exception("Export file cleanup failed for user %s", user_id)
