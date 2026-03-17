# ADR-003: Weaviate as Vector Database

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

PWBS requires a vector database for semantic search across all ingested documents. The database must store high-dimensional embeddings (1536 dimensions, OpenAI text-embedding-3-small), perform nearest-neighbor search with low latency, and support native hybrid search (vector + BM25). Multi-tenancy for tenant isolation is GDPR-critical. Self-hosting must be possible for the on-premise option in Phase 4.

---

## Decision

We use **Weaviate** as the vector database because it is the only open-source option that combines native hybrid search (vector + BM25), physical multi-tenancy, and self-hosting capability.

---

## Options Evaluated

| Option                | Advantages                                                                                                                                                   | Disadvantages                                                                                   | Exclusion Reasons                         |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- | ----------------------------------------- |
| **Weaviate** (chosen) | Open-source, self-hosting possible, native hybrid search (vector + BM25), physical multi-tenancy (tenant isolation), active community, GraphQL and REST API. | Higher operational overhead than Pinecone (managed). HNSW index consumes significant RAM.       | –                                         |
| Pinecone              | Fully managed, excellent scaling, low operational complexity.                                                                                                | No self-hosting (SaaS only), no native BM25, US-based provider (GDPR concerns), vendor lock-in. | No self-hosting, GDPR risk                |
| Qdrant                | Open-source, good performance, Rust-based.                                                                                                                   | No native hybrid search (BM25 missing), multi-tenancy less mature.                              | Missing native hybrid search              |
| Milvus                | Open-source, horizontally scalable, proven with large datasets.                                                                                              | Complex deployment (multiple components), no native BM25 search, higher operational complexity. | Overkill for MVP scale                    |
| pgvector              | No separate service needed, PostgreSQL integration.                                                                                                          | Significantly slower with large datasets, no native hybrid search, no multi-tenancy concept.    | Kept as fallback, not as primary solution |

---

## Consequences

### Positive Consequences

- Native hybrid search with configurable alpha parameter (weighting vector vs. BM25)
- Physical multi-tenancy: Each user has an isolated tenant – no cross-user results possible
- Self-hosting enables on-premise deployment in Phase 4
- Weaviate Cloud as managed option for cloud deployment, reduces operational overhead
- Batch import API for efficient initial data ingestion

### Negative Consequences / Trade-offs

- Higher operational overhead than fully-managed solutions (mitigated: Weaviate Cloud as option)
- HNSW index loads entirely into RAM – memory requirements scale linearly with document count (mitigated: vertical scaling, sharding in Phase 4)
- Chunk contents stored in plaintext in the index (necessary for BM25 search) – no column-level encryption possible

### Open Questions

- Evaluate memory budgeting per user once real usage data is available
- Define Weaviate version pinning strategy for upgrade path

---

## GDPR Implications

- **Tenant Isolation:** Physical multi-tenancy – each user has their own isolated tenant. No shared embedding space across user boundaries.
- **Deletability:** Tenant deletion removes all vectors and BM25 indices for a user. Called during account deletion (Art. 17) as part of the cascade.
- **Encryption:** Chunk contents and vectors are stored unencrypted in the index (trade-off: vector search and BM25 require plaintext access). Mitigated by volume encryption (AWS EBS), network isolation, and tenant separation.
- **Data Residency:** Self-hosting on EU infrastructure (AWS eu-central-1) guaranteed.

---

## Security Implications

- Weaviate in private subnet, no direct internet access
- API key authentication for Weaviate access
- Network isolation: Only the API service may access Weaviate (Security Groups)
- Volume encryption (AWS EBS) for at-rest protection
- Regular updates of the Weaviate container for security patches

---

## Revision Date

2027-03-13 – Evaluation of memory requirements and scaling strategy after 12 months, evaluation of Weaviate Cloud vs. self-hosting.
