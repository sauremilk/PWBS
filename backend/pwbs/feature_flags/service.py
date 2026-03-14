"""Feature-flag resolution service (TASK-174).

Resolution order:
1. Environment override (FEATURE_FLAGS_OVERRIDE) — highest priority
2. DB: enabled_globally
3. DB: user in enabled_for_users array
"""

from __future__ import annotations

import logging
import uuid
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.models.feature_flag import FeatureFlag

logger = logging.getLogger(__name__)


def _parse_env_overrides(raw: str) -> dict[str, bool]:
    """Parse 'flag1:true,flag2:false' into a dict."""
    if not raw.strip():
        return {}
    overrides: dict[str, bool] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        name, val = pair.split(":", 1)
        name = name.strip()
        val = val.strip().lower()
        if name and val in ("true", "false"):
            overrides[name] = val == "true"
    return overrides


@lru_cache(maxsize=1)
def _get_env_overrides() -> dict[str, bool]:
    """Load and cache env overrides from settings (singleton)."""
    from pwbs.core.config import get_settings

    return _parse_env_overrides(get_settings().feature_flags_override)


class FeatureFlagService:
    """Stateless service for feature-flag resolution."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def is_enabled(self, flag_name: str, user_id: uuid.UUID) -> bool:
        """Check if a feature flag is enabled for the given user.

        Resolution: env override > global toggle > per-user list.
        """
        # 1. Environment override (highest priority)
        env = _get_env_overrides()
        if flag_name in env:
            return env[flag_name]

        # 2. DB lookup
        stmt = select(FeatureFlag).where(FeatureFlag.flag_name == flag_name)
        result = await self._db.execute(stmt)
        flag = result.scalar_one_or_none()

        if flag is None:
            return False

        # 3. Global toggle
        if flag.enabled_globally:
            return True

        # 4. Per-user whitelist
        return user_id in (flag.enabled_for_users or [])

    async def get_all(self) -> list[FeatureFlag]:
        """Return all feature flags."""
        stmt = select(FeatureFlag).order_by(FeatureFlag.flag_name)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def upsert(
        self,
        flag_name: str,
        enabled_globally: bool | None = None,
        enabled_for_users: list[uuid.UUID] | None = None,
    ) -> FeatureFlag:
        """Create or update a feature flag."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        values: dict = {"flag_name": flag_name}
        update_set: dict = {}

        if enabled_globally is not None:
            values["enabled_globally"] = enabled_globally
            update_set["enabled_globally"] = enabled_globally
        if enabled_for_users is not None:
            values["enabled_for_users"] = enabled_for_users
            update_set["enabled_for_users"] = enabled_for_users

        insert_stmt = pg_insert(FeatureFlag).values(**values)
        if update_set:
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=["flag_name"],
                set_=update_set,
            )
        else:
            insert_stmt = insert_stmt.on_conflict_do_nothing(
                index_elements=["flag_name"],
            )

        await self._db.execute(insert_stmt)
        await self._db.flush()

        # Re-fetch to return current state
        stmt = select(FeatureFlag).where(FeatureFlag.flag_name == flag_name)
        result = await self._db.execute(stmt)
        return result.scalar_one()


async def is_feature_enabled(
    flag_name: str,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> bool:
    """Convenience function for quick flag checks."""
    svc = FeatureFlagService(db)
    return await svc.is_enabled(flag_name, user_id)
