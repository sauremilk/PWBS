# ADR-010: Hybrid Search (Vector + BM25) Instead of Pure Vector Search

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

The PWBS must be able to search across heterogeneous documents (calendar entries, notes, transcripts, briefings) both semantically and keyword-based. Pure vector search has weaknesses with exact proper names, project names, and technical terms. Pure keyword search does not understand semantic relationships. Search is a core feature – quality and relevance of results significantly determine the user experience.

---

## Decision

We use **Hybrid Search (Vector + BM25)** with Reciprocal Rank Fusion (RRF) for result combination, because the combination of both approaches compensates for the respective weaknesses of the other, and Weaviate natively supports both.

---

## Options Evaluated

| Option                                     | Advantages                                                                                                                                                       | Disadvantages                                                                                                                                    | Exclusion Reasons                                    |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------- |
| **Hybrid Search (Vector + BM25)** (chosen) | Vector search for semantic similarity + BM25 for exact matches. Weaviate offers both natively with configurable alpha (weighting). RRF as proven ranking fusion. | Increased indexing costs (two indices per collection). More complex relevance tuning.                                                            | –                                                    |
| Pure Vector Search                         | Simpler setup, strong semantic search, works cross-language.                                                                                                     | Fails with exact proper names (e.g., "Project Meridian"), technical terms, and acronyms. Hallucinates similarities with short, specific queries. | Proper name and technical term weakness unacceptable |
| Pure Keyword Search                        | Fast, deterministic, excellent for exact matches and filtering.                                                                                                  | Does not understand synonyms, no semantic relationships. "Besprechung" does not find "Meeting". Poor for natural language.                       | No semantic understanding capability                 |
| Elasticsearch                              | Mature BM25, many analyzers, good faceting. Semantic search possible via plugin.                                                                                 | Separate service with high resource requirements. No native vector embedding (plugin dependency). Redundant to Weaviate.                         | Redundant – Weaviate offers BM25 natively            |

---

## Consequences

### Positive Consequences

- Best search results through combination: semantic similarity (vector) + exact matches (BM25)
- Configurable alpha parameter: weighting between vector and BM25 can be adjusted per use case (e.g., alpha=0.7 for semantic-dominant search, alpha=0.3 for keyword-dominant search)
- No additional service required – Weaviate offers both natively
- RRF as fusion algorithm is robust and requires no query-specific training
- PostgreSQL tsvector as additional keyword fallback for scenarios without Weaviate

### Negative Consequences / Trade-offs

- Double indexing costs: each document is stored as both a vector and a BM25 index (mitigated: marginal at expected MVP data volume)
- Relevance tuning is more complex than with pure vector search (alpha parameter, RRF k parameter)
- BM25 requires plaintext storage of chunk contents in Weaviate (GDPR trade-off, documented in ADR-009)

### Open Questions

- Evaluate optimal alpha value for different query types (short questions vs. natural language vs. proper names)
- Implement relevance feedback loop for alpha tuning (Phase 3)
- Integrate graph search (Neo4j traversal) as a fourth search mode

---

## GDPR Implications

- **BM25 Index:** Requires plaintext storage of chunk contents in Weaviate. This trade-off is documented in ADR-009 and mitigated by volume encryption, network isolation, and tenant separation.
- **Tenant Isolation:** Every search query contains `owner_id` as a filter – no cross-user results possible. Weaviate multi-tenancy guarantees physical isolation.
- **Audit Logging:** Every search query is logged in the audit log (`search.executed` event with query hash, not plaintext query).

---

## Security Implications

- owner_id as mandatory filter in every search query prevents information disclosure between users
- Query validation: maximum query length, top_k limit (max. 50) against resource-intensive search queries
- No storage of search queries in plaintext in logs (only query hash for audit)
- Rate limiting on search endpoint against brute-force enumeration

---

## Revision Date

2027-03-13 – Assessment of search quality and alpha tuning results after 12 months of MVP operation.
