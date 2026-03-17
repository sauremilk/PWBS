# ADR-002: PostgreSQL as Primary Database

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

PWBS requires a relational database for user management, connector configuration, document metadata, briefings, audit logs, and OAuth token storage. The database must support JSONB for flexible metadata, provide strong transaction guarantees, and serve as a fallback for vector search (pgvector). Row-level tenant isolation is mandatory for GDPR compliance.

---

## Decision

We use **PostgreSQL 16+** as the primary relational database because it offers the best combination of JSONB flexibility, transactional reliability, ecosystem maturity, and extensibility (pgvector as fallback).

---

## Options Evaluated

| Option                  | Advantages                                                                                                                                                                              | Disadvantages                                                                                                                                           | Exclusion Reasons                     |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| **PostgreSQL** (chosen) | JSONB for flexible metadata, strong ACID transactions, proven ecosystem, pgvector as backup, excellent tooling (Alembic, pgAdmin, psql). Full-text search (tsvector) for BM25 fallback. | No native horizontal sharding.                                                                                                                          | –                                     |
| MySQL                   | Widely adopted, good performance for simple queries.                                                                                                                                    | Weaker JSONB support, no pgvector equivalent, weaker CHECK constraints.                                                                                 | JSONB and extensibility disadvantages |
| MongoDB                 | Schema-flexible, built-in horizontal scaling.                                                                                                                                           | Weaker transaction guarantees, no native joins, harder migration management. Not suitable for highly relational data (Users ↔ Connections ↔ Documents). | Relational data dominates the schema  |
| CockroachDB             | PostgreSQL-compatible, native horizontal sharding, geographic distribution.                                                                                                             | Higher latency on single-node, more complex operational model, higher costs. Overkill for MVP scale.                                                    | Overkill for MVP requirements         |

---

## Consequences

### Positive Consequences

- JSONB columns enable flexible metadata per document type without schema changes
- pgvector as fallback in case Weaviate fails or for simple vector search without a separate service
- Alembic for versioned schema migrations with rollback capability
- Proven backup/restore with pg_dump, point-in-time recovery via WAL
- AWS RDS as managed service with automatic failover

### Negative Consequences / Trade-offs

- No native horizontal sharding (mitigated by read replicas and potentially Citus extension in Phase 5)
- Documents table can become slow at high volume (mitigated by partitioning on created_at or owner_id)
- Connection pool management required (PgBouncer in Phase 3+)

### Open Questions

- Evaluate partitioning strategy for documents table once >100K documents per user is reached
- Benchmark pgvector performance vs. Weaviate for fallback scenarios

---

## GDPR Implications

- **Tenant Isolation:** Every query includes `WHERE owner_id = $user_id` as a filter. Row-Level Security (RLS) as an additional safeguard layer is possible.
- **Deletability:** `DELETE CASCADE` on all foreign keys ensures account deletion removes all associated data.
- **Encryption:** AWS RDS Encryption (AES-256) for at-rest. Additional column-level encryption for OAuth tokens with user DEK.
- **Data Export:** SQL queries can compile all user data for Art. 15 export.
- **Expiration Dates:** `expires_at` column on documents table enables automatic deletion of expired data.

---

## Security Implications

- Enforced TLS for all connections (API → PostgreSQL)
- PostgreSQL in private subnet, no direct internet access
- Credentials via environment variables, not in code
- Prepared statements via SQLAlchemy prevent SQL injection
- Regular security updates via AWS RDS Maintenance Windows

---

## Revision Date

2027-03-13 – Evaluation of scaling requirements after 12 months, particularly sharding needs and pgvector usage.
