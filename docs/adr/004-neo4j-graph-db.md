# ADR-004: Neo4j as Graph Database

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

The PWBS requires a graph database for the Knowledge Graph, which stores relationships between people, projects, decisions, documents, topics, and entities. The graph serves as an audit layer for LLM explainability and enables context queries (e.g., \x22All decisions related to Project X\x22), pattern recognition, and relationship analysis. Self-hosting must be possible for the on-premise option.

---

## Decision

We use **Neo4j** as the graph database because Cypher as an expressive query language, the largest community, and the most mature tooling (Browser, Bloom) provide the best foundation for the Knowledge Graph.

---

## Options Evaluated

| Option              | Advantages                                                                                                                                                                                              | Disadvantages                                                                                        | Exclusion Reasons                          |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| **Neo4j** (chosen)  | Cypher as an expressive, well-documented query language. Largest graph DB community. Mature tools (Neo4j Browser, Bloom for visualization). Stable Python driver. Self-hosting possible.                 | High RAM requirements for large graphs. Community Edition without cluster capability.                 | \u2013                                          |
| TigerGraph          | Very high performance for graph analytics, native parallel traversals.                                                                                                                                  | Proprietary query language (GSQL), smaller community, higher learning curve. Self-hosting is complex. | Proprietary query language                 |
| Amazon Neptune      | Fully managed, supports Gremlin and SPARQL.                                                                                                                                                             | No self-hosting (AWS only), no Cypher support, higher costs, vendor lock-in.                         | No self-hosting possible                   |
| TerminusDB          | Open-source, Git-like versioning of graph data.                                                                                                                                                         | Smaller community, less mature tooling, performance with complex traversals unclear.                  | Maturity and community size not sufficient |

---

## Consequences

### Positive Consequences

- Cypher enables intuitive graph queries (MATCH, MERGE, WHERE) for context queries and pattern recognition
- Neo4j Browser and Bloom enable visual exploration of the Knowledge Graph (useful for debugging and feature demos)
- MERGE command guarantees idempotency during graph population (no duplicate creation of nodes/edges)
- Python driver (neo4j-python-driver) is stable and well-documented
- Neo4j Aura available as a managed cloud option

### Negative Consequences / Trade-offs

- High RAM requirements for large graphs \u2013 Community Edition has no memory tiering (mitigated: expected graph size in MVP is manageable, Neo4j Aura as alternative)
- Community Edition has no cluster capability (mitigated: Enterprise Edition or Neo4j Aura for Phase 5)
- Graph traversals with depth >3 can become slow (mitigated: query timeouts, result limits, caching of frequent patterns)

### Open Questions

- Validate RAM sizing for expected graph size in MVP
- Verify Neo4j 5.x vs. 4.x compatibility of the Python driver

---

## GDPR Implications

- **Tenant Isolation:** All nodes and edges carry owner_id as a property. Every Cypher query contains WHERE n.owner_id = .
- **Deletability:** Account deletion removes all nodes and edges with the user\x27s owner_id. MATCH (n {owner_id: }) DETACH DELETE n removes them cascadingly.
- **Encryption:** Graph data is stored in plaintext for query performance. Mitigated by volume encryption (AWS EBS), network isolation, no external access.
- **Explainability:** The graph serves as the source reference layer \u2013 every LLM-generated briefing references graph nodes as source evidence.

---

## Security Implications

- Neo4j in a private subnet, no direct internet access
- Bolt protocol with TLS for encrypted connection (API \u2192 Neo4j)
- Authentication via username/password (environment variables)
- Volume encryption (AWS EBS) for at-rest protection
- Query timeouts prevent resource-intensive infinite traversals (DoS protection)

---

## Revision Date

2027-03-13 \u2013 Assessment of RAM requirements and cluster needs after 12 months of MVP operation. Evaluation of Neo4j Aura vs. self-hosting.
