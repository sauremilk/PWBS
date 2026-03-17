# ADR-009: Envelope Encryption with per-User Keys

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

The PWBS stores highly sensitive personal data: OAuth tokens, calendar entries, notes, meeting transcripts, LLM-generated briefings. The encryption strategy must be GDPR-compliant (Art. 32: appropriate technical measures), enable account deletion without full re-encryption, and at the same time not prevent server-side search and briefing generation. The balance between security and functionality is the central trade-off.

---

## Decision

We use **Envelope Encryption with per-user Data Encryption Keys (DEKs)**, with AWS KMS serving as the Key Encryption Key (KEK), because this scheme enables account deletion by simply deleting the DEK and delegates key management complexity to AWS KMS.

---

## Options Evaluated

| Option                                     | Advantages                                                                                                                                                                             | Disadvantages                                                                                                                                                                                    | Exclusion Reasons                              |
| ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------- |
| **Envelope Encryption (KEK/DEK)** (chosen) | Per-user keys enable account deletion without full re-encryption (delete DEK = data cryptographically unreadable). AWS KMS as KEK avoids key management complexity. Industry standard. | Weaviate vectors are stored unencrypted in the index (required for search). Requires careful key lifecycle management.                                                                           | –                                              |
| Application-level encryption only          | Simpler setup, no KMS required.                                                                                                                                                        | Key management entirely in the application – higher risk from key loss. No HSM-backed key storage. No key rotation without re-encryption.                                                        | Insufficient key management                    |
| DB-level encryption only                   | Simplest implementation (AWS RDS Encryption), transparent to application.                                                                                                              | No per-user isolation – all data encrypted with the same key. Account deletion does not require cryptographic isolation. Protection only against physical storage access, not against DB access. | No per-user isolation                          |
| Zero-knowledge architecture                | Maximum security – server cannot decrypt data.                                                                                                                                         | Prevents server-side search and briefing generation. Users must manage key material themselves. Key loss = data loss. Incompatible with the core functionality of the PWBS.                      | Incompatible with server-side search/briefings |

---

## Consequences

### Positive Consequences

- Account deletion: delete DEK → all user data cryptographically unreadable, without expensive re-encryption
- AWS KMS: HSM-backed key storage, automatic key rotation, audit trail via CloudTrail
- Per-user DEK: compromise of one DEK affects only one user, not all
- Industry standard: proven scheme recommended by AWS, Google Cloud, and Azure
- Compatible with server-side search and briefing generation (server decrypts temporarily for processing)

### Negative Consequences / Trade-offs

- Weaviate vectors and BM25 index are stored unencrypted in plaintext (required for search). Mitigated by volume encryption (AWS EBS), network isolation, and physical tenant separation in Weaviate.
- Neo4j graph data is stored in plaintext for query performance. Mitigated by volume encryption and network isolation.
- Key rotation of the KEK requires re-wrapping all DEKs (not re-encryption of the data – significantly cheaper)
- In case of AWS KMS outage, no new data can be encrypted (mitigated: KMS multi-region keys, DEK caching in application memory)

### Open Questions

- DEK caching strategy: How long does a decrypted DEK remain in application memory? (Trade-off: performance vs. attack surface)
- Backup encryption: Separate backup keys vs. user DEKs for backups
- Define key rotation frequency for KEK

---

## GDPR Implications

- **Art. 32 (Security):** Envelope encryption fulfills the requirement for "appropriate technical measures" to protect personal data.
- **Art. 17 (Erasure):** DEK deletion makes user data cryptographically unreadable – effective erasure without physically overwriting all database entries.
- **Art. 25 (Privacy by Design):** Per-user encryption as a fundamental structure, not as an optional feature.
- **Encryption Matrix:**
  - PostgreSQL: AWS RDS TDE + column-level AES-256-GCM for OAuth tokens with user DEK
  - Weaviate: Volume encryption (AWS EBS) – plaintext in index (documented trade-off)
  - Neo4j: Volume encryption (AWS EBS) – plaintext in graph (documented trade-off)
  - Redis: AWS ElastiCache Encryption at Rest
  - Backups: AES-256-GCM with separate backup keys

---

## Security Implications

- AWS KMS as HSM-backed key storage avoids hand-rolled key management
- CloudTrail logging for all KEK operations (Encrypt, Decrypt, GenerateDataKey)
- DEKs are stored encrypted in the users table (`encryption_key_enc` column)
- Decrypted DEKs only temporarily in application memory – no logging, no disk swap
- Risk: side-channel attacks on application memory (mitigated: evaluate Nitro Enclaves for Phase 5)

---

## Revision Date

2027-03-13 – Assessment of key rotation experience, DEK caching strategy, and evaluation of AWS Nitro Enclaves for additional isolation.
