"""Weaviate storage layer for document chunk embeddings (TASK-059).

Provides idempotent upsert of embeddings into the Weaviate
``DocumentChunk`` collection with multi-tenancy isolation (one tenant
per ``user_id``).  Vectors are externally generated — the collection
uses ``vectorizer: none`` with an HNSW index.

Schema reference: D1 §3.3.2.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import weaviate
from weaviate.classes.config import (
    Configure,
    DataType,
    Property,
)
from weaviate.classes.data import DataObject
from weaviate.classes.tenants import Tenant, TenantActivityStatus

from pwbs.processing.chunking import TextChunk
from pwbs.processing.embedding import EmbeddingResult

logger = logging.getLogger(__name__)

__all__ = [
    "WeaviateChunkStore",
]

COLLECTION_NAME = "DocumentChunk"


@dataclass(frozen=True, slots=True)
class ChunkUpsertRequest:
    """Data needed to upsert a single chunk into Weaviate."""

    chunk_id: uuid.UUID
    user_id: uuid.UUID
    document_id: uuid.UUID
    embedding: list[float]
    content: str
    title: str
    source_type: str
    language: str
    created_at: datetime
    chunk_index: int


@dataclass(frozen=True, slots=True)
class ChunkUpsertResult:
    """Result of a single chunk upsert operation."""

    chunk_id: uuid.UUID
    weaviate_id: uuid.UUID
    success: bool


class WeaviateChunkStore:
    """Manages the ``DocumentChunk`` Weaviate collection.

    Multi-tenancy: Each user gets their own Weaviate tenant, ensuring
    strict data isolation.  Upserts are idempotent — a chunk with the
    same deterministic UUID is overwritten on re-ingestion.

    HNSW index: ``efConstruction=128``, ``maxConnections=16`` per D1 §3.3.2.
    """

    def __init__(self, client: weaviate.WeaviateClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def ensure_collection(self) -> None:
        """Create the ``DocumentChunk`` collection if it does not exist.

        Idempotent — safe to call on every startup.
        """
        if self._client.collections.exists(COLLECTION_NAME):
            logger.debug("Collection %s already exists", COLLECTION_NAME)
            return

        self._client.collections.create(
            name=COLLECTION_NAME,
            multi_tenancy_config=Configure.multi_tenancy(
                enabled=True,
                auto_tenant_creation=True,
                auto_tenant_activation=True,
            ),
            vectorizer_config=Configure.Vectorizer.none(),
            vector_index_config=Configure.VectorIndex.hnsw(
                ef_construction=128,
                max_connections=16,
            ),
            properties=[
                Property(name="chunkId", data_type=DataType.UUID),
                Property(name="documentId", data_type=DataType.UUID),
                Property(name="userId", data_type=DataType.UUID),
                Property(name="sourceType", data_type=DataType.TEXT),
                Property(name="content", data_type=DataType.TEXT),
                Property(name="title", data_type=DataType.TEXT),
                Property(name="createdAt", data_type=DataType.DATE),
                Property(name="language", data_type=DataType.TEXT),
                Property(name="chunkIndex", data_type=DataType.INT),
            ],
        )
        logger.info("Created Weaviate collection %s", COLLECTION_NAME)

    def ensure_tenant(self, user_id: uuid.UUID) -> None:
        """Ensure a tenant exists for the given user.  Idempotent."""
        collection = self._client.collections.get(COLLECTION_NAME)
        tenant_name = str(user_id)

        existing = collection.tenants.get()
        if tenant_name in existing:
            # Reactivate if inactive
            tenant = existing[tenant_name]
            if tenant.activity_status != TenantActivityStatus.ACTIVE:
                collection.tenants.update([
                    Tenant(name=tenant_name, activity_status=TenantActivityStatus.ACTIVE)
                ])
            return

        collection.tenants.create([Tenant(name=tenant_name)])
        logger.info("Created Weaviate tenant for user %s", user_id)

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    def upsert_chunks(
        self,
        requests: list[ChunkUpsertRequest],
    ) -> list[ChunkUpsertResult]:
        """Upsert chunk embeddings into Weaviate.

        Uses deterministic UUIDs derived from ``chunk_id`` so that
        re-ingesting the same chunk overwrites the previous vector
        (idempotency).

        Args:
            requests: List of chunks with their embeddings and metadata.

        Returns:
            List of :class:`ChunkUpsertResult` indicating success per chunk.
        """
        if not requests:
            return []

        # Group by user_id (tenant)
        by_tenant: dict[uuid.UUID, list[ChunkUpsertRequest]] = {}
        for req in requests:
            by_tenant.setdefault(req.user_id, []).append(req)

        results: list[ChunkUpsertResult] = []

        for user_id, tenant_requests in by_tenant.items():
            self.ensure_tenant(user_id)
            tenant_results = self._upsert_tenant_batch(user_id, tenant_requests)
            results.extend(tenant_results)

        return results

    def _upsert_tenant_batch(
        self,
        user_id: uuid.UUID,
        requests: list[ChunkUpsertRequest],
    ) -> list[ChunkUpsertResult]:
        """Upsert a batch of chunks for a single tenant."""
        collection = self._client.collections.get(COLLECTION_NAME)
        tenant_collection = collection.with_tenant(str(user_id))
        results: list[ChunkUpsertResult] = []

        with tenant_collection.batch.dynamic() as batch:
            for req in requests:
                weaviate_id = self._deterministic_uuid(req.chunk_id)
                properties = {
                    "chunkId": str(req.chunk_id),
                    "documentId": str(req.document_id),
                    "userId": str(req.user_id),
                    "sourceType": req.source_type,
                    "content": req.content,
                    "title": req.title,
                    "createdAt": req.created_at.isoformat(),
                    "language": req.language,
                    "chunkIndex": req.chunk_index,
                }
                batch.add_object(
                    properties=properties,
                    vector=req.embedding,
                    uuid=weaviate_id,
                )
                results.append(
                    ChunkUpsertResult(
                        chunk_id=req.chunk_id,
                        weaviate_id=weaviate_id,
                        success=True,
                    )
                )

        # Check for batch errors
        if tenant_collection.batch.failed_objects:
            failed_ids = {
                str(obj.original_uuid)
                for obj in tenant_collection.batch.failed_objects
            }
            for result in results:
                if str(result.weaviate_id) in failed_ids:
                    results = [
                        ChunkUpsertResult(
                            chunk_id=r.chunk_id,
                            weaviate_id=r.weaviate_id,
                            success=str(r.weaviate_id) not in failed_ids,
                        )
                        for r in results
                    ]
                    break

            for obj in tenant_collection.batch.failed_objects:
                logger.error(
                    "Weaviate upsert failed for %s: %s",
                    obj.original_uuid,
                    obj.message,
                )

        return results

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_chunks(
        self,
        user_id: uuid.UUID,
        chunk_ids: list[uuid.UUID],
    ) -> None:
        """Delete specific chunks from Weaviate for a user (DSGVO compliance)."""
        if not chunk_ids:
            return

        collection = self._client.collections.get(COLLECTION_NAME)
        tenant_collection = collection.with_tenant(str(user_id))

        for chunk_id in chunk_ids:
            weaviate_id = self._deterministic_uuid(chunk_id)
            try:
                tenant_collection.data.delete_by_id(weaviate_id)
            except Exception:
                logger.warning(
                    "Failed to delete chunk %s from Weaviate (may not exist)",
                    chunk_id,
                )

    def delete_user_data(self, user_id: uuid.UUID) -> None:
        """Delete all data for a user by removing their tenant (DSGVO)."""
        collection = self._client.collections.get(COLLECTION_NAME)
        try:
            collection.tenants.remove([str(user_id)])
            logger.info("Removed Weaviate tenant for user %s", user_id)
        except Exception:
            logger.warning("Failed to remove tenant for user %s", user_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _deterministic_uuid(chunk_id: uuid.UUID) -> uuid.UUID:
        """Generate a deterministic Weaviate UUID from the chunk's PG UUID.

        Uses UUID5 with a fixed namespace so the same chunk_id always
        produces the same Weaviate UUID — enabling idempotent upserts.
        """
        namespace = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        return uuid.uuid5(namespace, str(chunk_id))
