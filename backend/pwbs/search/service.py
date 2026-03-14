"""Semantic Search Service (TASK-072).

Implements Weaviate Nearest-Neighbor search over the ``DocumentChunk``
collection, isolated per user tenant.  Query embeddings are generated
through the :class:`EmbeddingService` (TASK-058).

D1 §3.3.2: ``alpha=0.75`` for standard semantic-weighted search.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

import weaviate
from weaviate.classes.query import MetadataQuery

from pwbs.processing.embedding import EmbeddingService
from pwbs.storage.weaviate import COLLECTION_NAME

logger = logging.getLogger(__name__)

__all__ = [
    "SearchConfig",
    "SemanticSearchResult",
    "SemanticSearchService",
]


@dataclass(frozen=True, slots=True)
class SearchConfig:
    """Configuration for the semantic search service."""

    default_top_k: int = 10
    max_top_k: int = 50
    default_alpha: float = 0.75


@dataclass(frozen=True, slots=True)
class SemanticSearchResult:
    """A single Weaviate search result."""

    chunk_id: uuid.UUID
    content: str
    title: str
    source_type: str
    created_at: str
    score: float
    chunk_index: int


class SemanticSearchService:
    """Performs semantic nearest-neighbor search over document chunks.

    Queries are embedded using the :class:`EmbeddingService`, then matched
    against the user's Weaviate tenant in the ``DocumentChunk`` collection.
    Results are isolated to the requesting user (multi-tenancy).
    """

    def __init__(
        self,
        weaviate_client: weaviate.WeaviateClient,
        embedding_service: EmbeddingService,
        config: SearchConfig | None = None,
    ) -> None:
        self._client = weaviate_client
        self._embedding = embedding_service
        self._config = config or SearchConfig()

    @property
    def config(self) -> SearchConfig:
        return self._config

    async def search(
        self,
        query: str,
        user_id: uuid.UUID,
        top_k: int | None = None,
        alpha: float | None = None,
    ) -> list[SemanticSearchResult]:
        """Search for chunks semantically similar to *query*.

        Args:
            query: The search query text.
            user_id: Owner ID — search is scoped to this user's tenant.
            top_k: Number of results (default: 10, max: 50).
            alpha: Semantic weight (0.0 = keyword, 1.0 = pure semantic).

        Returns:
            List of :class:`SemanticSearchResult` sorted by score descending.
            Empty list if query is empty or no results found.
        """
        if not query or not query.strip():
            return []

        effective_top_k = min(
            top_k or self._config.default_top_k,
            self._config.max_top_k,
        )
        effective_alpha = alpha if alpha is not None else self._config.default_alpha

        # Generate query embedding
        query_embedding = await self._embedding.embed_text(query)

        # Execute Weaviate nearVector search
        return self._query_weaviate(
            user_id=user_id,
            query_vector=query_embedding,
            top_k=effective_top_k,
            alpha=effective_alpha,
        )

    def _query_weaviate(
        self,
        user_id: uuid.UUID,
        query_vector: list[float],
        top_k: int,
        alpha: float,
    ) -> list[SemanticSearchResult]:
        """Execute the Weaviate nearVector query."""
        collection = self._client.collections.get(COLLECTION_NAME)
        tenant_collection = collection.with_tenant(str(user_id))

        response = tenant_collection.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_metadata=MetadataQuery(distance=True, certainty=True),
            return_properties=[
                "chunkId",
                "content",
                "title",
                "sourceType",
                "createdAt",
                "chunkIndex",
            ],
        )

        results: list[SemanticSearchResult] = []
        for obj in response.objects:
            props = obj.properties
            # Weaviate returns certainty in [0, 1] where 1 = identical
            score = obj.metadata.certainty if obj.metadata and obj.metadata.certainty is not None else 0.0

            results.append(
                SemanticSearchResult(
                    chunk_id=uuid.UUID(str(props.get("chunkId", ""))),
                    content=str(props.get("content", "")),
                    title=str(props.get("title", "")),
                    source_type=str(props.get("sourceType", "")),
                    created_at=str(props.get("createdAt", "")),
                    score=float(score),
                    chunk_index=int(props.get("chunkIndex", 0)),  # type: ignore[arg-type]
                )
            )

        return results
