"""Weaviate client singleton and health check (TASK-028).

Weaviate is optional in MVP – the client returns None if the connection
cannot be established.  All consumers must guard against ``None``.
"""

from __future__ import annotations

import logging

import weaviate

from pwbs.core.config import get_settings

logger = logging.getLogger(__name__)

_client: weaviate.WeaviateClient | None = None
_init_failed: bool = False


def get_weaviate_client() -> weaviate.WeaviateClient | None:
    """Return the Weaviate client singleton, or ``None`` if unavailable.

    After one failed initialisation attempt the function short-circuits
    and returns ``None`` immediately (no repeated timeouts).
    """
    global _client, _init_failed
    if _client is not None and _client.is_connected():
        return _client
    if _init_failed:
        return None
    try:
        settings = get_settings()
        host = settings.weaviate_url.replace("http://", "").replace("https://", "")
        parts = host.split(":")
        hostname = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 8080
        _client = weaviate.connect_to_local(host=hostname, port=port)
        return _client
    except Exception:
        _init_failed = True
        logger.warning("Weaviate connection failed \u2013 running without vector search")
        return None


async def check_weaviate_health() -> bool:
    try:
        client = get_weaviate_client()
        if client is None:
            return False
        return client.is_ready()
    except Exception:
        return False


async def close_weaviate_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
