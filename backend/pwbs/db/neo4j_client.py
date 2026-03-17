"""Neo4j async driver singleton and health check (TASK-029).

Neo4j is optional in MVP – the driver returns None if the connection
cannot be established.  All consumers must guard against ``None``.
"""

from __future__ import annotations

import logging

from neo4j import AsyncDriver, AsyncGraphDatabase

from pwbs.core.config import get_settings

logger = logging.getLogger(__name__)

_driver: AsyncDriver | None = None
_init_failed: bool = False


def get_neo4j_driver() -> AsyncDriver | None:
    """Return the Neo4j driver singleton, or ``None`` if unavailable.

    After one failed initialisation attempt the function short-circuits
    and returns ``None`` immediately (no repeated timeouts).
    """
    global _driver, _init_failed
    if _driver is not None:
        return _driver
    if _init_failed:
        return None
    try:
        settings = get_settings()
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        )
        return _driver
    except Exception:
        _init_failed = True
        logger.warning("Neo4j driver initialisation failed – running without graph DB")
        return None


async def check_neo4j_health() -> bool:
    try:
        driver = get_neo4j_driver()
        if driver is None:
            return False
        await driver.verify_connectivity()
        return True
    except Exception:
        return False


async def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
