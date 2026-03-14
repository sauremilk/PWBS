"""ConnectorRegistry - central registry for all PWBS data-source connectors (TASK-042).

Provides:
- Registration of connector classes by ``SourceType``
- Lookup and instantiation of connectors
- Bulk health-check across all registered connector types

Thread-safety: The registry is a module-level singleton populated at import
time via ``register_connector``.  Mutation after startup is not expected.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pwbs.core.exceptions import ConnectorError, NotFoundError
from pwbs.schemas.enums import SourceType  # noqa: TC001 - runtime dict key

if TYPE_CHECKING:
    from uuid import UUID

    from pwbs.connectors.base import BaseConnector, ConnectorConfig

logger = logging.getLogger(__name__)

# Internal registry: SourceType -> connector class
_registry: dict[SourceType, type[BaseConnector]] = {}


def register_connector(
    source_type: SourceType,
    connector_class: type[BaseConnector],
) -> None:
    """Register a connector class for a given source type.

    Raises ``ConnectorError`` if a connector for the same source type is
    already registered (prevents accidental double-registration).
    """
    if source_type in _registry:
        raise ConnectorError(
            f"Connector for {source_type.value} already registered: "
            f"{_registry[source_type].__name__}",
            code="CONNECTOR_ALREADY_REGISTERED",
        )
    _registry[source_type] = connector_class
    logger.info(
        "Registered connector: source_type=%s class=%s",
        source_type.value,
        connector_class.__name__,
    )


def get_connector_class(source_type: SourceType) -> type[BaseConnector]:
    """Return the connector class registered for *source_type*.

    Raises ``NotFoundError`` if no connector is registered.
    """
    cls = _registry.get(source_type)
    if cls is None:
        raise NotFoundError(
            f"No connector registered for source type: {source_type.value}",
            code="CONNECTOR_NOT_FOUND",
        )
    return cls


def create_connector(
    source_type: SourceType,
    *,
    owner_id: UUID,
    connection_id: UUID,
    config: ConnectorConfig,
) -> BaseConnector:
    """Instantiate a connector for the given source type with the provided context.

    Convenience function combining lookup + instantiation.
    """
    cls = get_connector_class(source_type)
    return cls(owner_id=owner_id, connection_id=connection_id, config=config)


def list_registered_types() -> list[SourceType]:
    """Return all source types that have a registered connector."""
    return list(_registry.keys())


async def health_check_all(
    *,
    owner_id: UUID,
    connection_id: UUID,
    config: ConnectorConfig,
) -> dict[SourceType, bool]:
    """Run health checks for all registered connectors.

    Returns a mapping of source type to health status.
    Connector-level exceptions are caught and mapped to ``False``.
    """
    results: dict[SourceType, bool] = {}
    for source_type, cls in _registry.items():
        try:
            connector = cls(
                owner_id=owner_id,
                connection_id=connection_id,
                config=config,
            )
            results[source_type] = await connector.health_check()
        except Exception:
            logger.warning(
                "Health check failed: source_type=%s",
                source_type.value,
                exc_info=True,
            )
            results[source_type] = False
    return results


def clear_registry() -> None:
    """Remove all registered connectors. Only for use in tests."""
    _registry.clear()
