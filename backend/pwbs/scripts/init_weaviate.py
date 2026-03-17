"""Idempotent Weaviate DocumentChunk collection setup (TASK-025).

Creates the DocumentChunk collection with HNSW vector index,
multi-tenancy, and hybrid search support. Safe to run multiple times.
"""

from __future__ import annotations

import weaviate
import weaviate.classes.config as wvc

COLLECTION_NAME = "DocumentChunk"


def ensure_document_chunk_collection(client: weaviate.WeaviateClient) -> None:
    if client.collections.exists(COLLECTION_NAME):
        return

    client.collections.create(
        name=COLLECTION_NAME,
        vectorizer_config=wvc.Configure.Vectorizer.none(),
        vector_index_config=wvc.Configure.VectorIndex.hnsw(
            ef_construction=128,
            max_connections=16,
            ef=64,
        ),
        multi_tenancy_config=wvc.Configure.multi_tenancy(enabled=True),
        properties=[
            wvc.Property(name="chunkId", data_type=wvc.DataType.UUID),
            wvc.Property(name="userId", data_type=wvc.DataType.UUID),
            wvc.Property(name="sourceType", data_type=wvc.DataType.TEXT),
            wvc.Property(
                name="content",
                data_type=wvc.DataType.TEXT,
                tokenization=wvc.Tokenization.WORD,
            ),
            wvc.Property(name="title", data_type=wvc.DataType.TEXT),
            wvc.Property(name="createdAt", data_type=wvc.DataType.DATE),
            wvc.Property(name="language", data_type=wvc.DataType.TEXT),
        ],
    )


def main() -> None:
    from pwbs.core.config import get_settings

    settings = get_settings()
    host = settings.weaviate_url.replace("http://", "").replace("https://", "")
    parts = host.split(":")
    hostname = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 8080

    client = weaviate.connect_to_local(host=hostname, port=port)
    try:
        ensure_document_chunk_collection(client)
        print(f"DocumentChunk collection ready (exists={client.collections.exists(COLLECTION_NAME)})")
    finally:
        client.close()


if __name__ == "__main__":
    main()
