"""Neo4j async driver singleton and health check (TASK-029)."""

from __future__ import annotations

from neo4j import AsyncGraphDatabase, AsyncDriver

from pwbs.core.config import get_settings

_driver: AsyncDriver | None = None


def get_neo4j_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        settings = get_settings()
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        )
    return _driver


async def check_neo4j_health() -> bool:
    try:
        driver = get_neo4j_driver()
        await driver.verify_connectivity()
        return True
    except Exception:
        return False


async def close_neo4j_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None