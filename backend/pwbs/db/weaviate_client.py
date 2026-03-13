"""Weaviate client singleton and health check (TASK-028)."""

from __future__ import annotations

import weaviate
from weaviate.classes.init import Auth

from pwbs.core.config import get_settings

_client: weaviate.WeaviateClient | None = None


def get_weaviate_client() -> weaviate.WeaviateClient:
    global _client
    if _client is None or not _client.is_connected():
        settings = get_settings()
        host = settings.weaviate_url.replace("http://", "").replace("https://", "")
        parts = host.split(":")
        hostname = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 8080
        _client = weaviate.connect_to_local(host=hostname, port=port)
    return _client


async def check_weaviate_health() -> bool:
    try:
        client = get_weaviate_client()
        return client.is_ready()
    except Exception:
        return False


async def close_weaviate_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None