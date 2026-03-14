# ADR-003: Weaviate als Vektor-Datenbank

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

Das PWBS benötigt eine Vektor-Datenbank für semantische Suche über alle ingestierten Dokumente. Die Datenbank muss hochdimensionale Embeddings (1536 Dimensionen, OpenAI text-embedding-3-small) speichern, Nearest-Neighbor-Suche mit niedriger Latenz durchführen und native Hybrid-Suche (Vektor + BM25) unterstützen. Multi-Tenancy für Mandantenisolation ist DSGVO-kritisch. Self-Hosting muss möglich sein für die On-Premise-Option in Phase 4.

---

## Entscheidung

Wir verwenden **Weaviate** als Vektor-Datenbank, weil es als einzige Open-Source-Option native Hybrid-Suche (Vektor + BM25), physische Multi-Tenancy und Self-Hosting-Fähigkeit kombiniert.

---

## Optionen bewertet

| Option                 | Vorteile                                                                                                                                                     | Nachteile                                                                                                 | Ausschlussgründe                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| **Weaviate** (gewählt) | Open-Source, Self-Hosting möglich, native Hybrid-Suche (Vektor + BM25), physische Multi-Tenancy (Tenant-Isolation), aktive Community, GraphQL- und REST-API. | Höherer Betriebsaufwand als Pinecone (managed). HNSW-Index verbraucht viel RAM.                           | –                                             |
| Pinecone               | Fully managed, exzellente Skalierung, niedrige Betriebskomplexität.                                                                                          | Kein Self-Hosting (SaaS only), kein nativer BM25, US-basierter Provider (DSGVO-Bedenken), Vendor Lock-in. | Kein Self-Hosting, DSGVO-Risiko               |
| Qdrant                 | Open-Source, gute Performance, Rust-basiert.                                                                                                                 | Keine native Hybrid-Suche (BM25 fehlt), Multi-Tenancy weniger ausgereift.                                 | Fehlende native Hybrid-Suche                  |
| Milvus                 | Open-Source, horizontal skalierbar, bewährt bei großen Datenmengen.                                                                                          | Komplexes Deployment (mehrere Komponenten), keine native BM25-Suche, höhere Betriebskomplexität.          | Overkill für MVP-Skala                        |
| pgvector               | Kein separater Service nötig, PostgreSQL-Integration.                                                                                                        | Deutlich langsamer bei großen Datenmengen, keine native Hybrid-Suche, kein Multi-Tenancy-Konzept.         | Als Fallback behalten, nicht als Primärlösung |

---

## Konsequenzen

### Positive Konsequenzen

- Native Hybrid-Suche mit konfigurierbarem Alpha-Parameter (Gewichtung Vektor vs. BM25)
- Physische Multi-Tenancy: Jeder Nutzer hat einen isolierten Tenant – keine Cross-User-Ergebnisse möglich
- Self-Hosting ermöglicht On-Premise-Deployment in Phase 4
- Weaviate Cloud als managed Option für Cloud-Deployment, reduziert Betriebsaufwand
- Batch-Import-API für effiziente initiale Daten-Ingestion

### Negative Konsequenzen / Trade-offs

- Höherer Betriebsaufwand als fully-managed Lösungen (mitigiert: Weaviate Cloud als Option)
- HNSW-Index lädt vollständig in RAM – Memory-Anforderungen steigen linear mit Dokumentanzahl (mitigiert: vertikale Skalierung, Sharding in Phase 4)
- Chunk-Inhalte liegen im Klartext im Index (notwendig für BM25-Suche) – keine Spalten-Level-Verschlüsselung möglich

### Offene Fragen

- Memory-Budgetierung pro Nutzer evaluieren, sobald reale Nutzungsdaten vorliegen
- Weaviate-Version-Pinning-Strategie für Upgrade-Pfad definieren

---

## DSGVO-Implikationen

- **Mandantenisolation:** Physische Multi-Tenancy – jeder Nutzer hat einen eigenen isolierten Tenant. Kein shared Embedding-Space über Nutzergrenzen.
- **Löschbarkeit:** Tenant-Löschung entfernt alle Vektoren und BM25-Indizes eines Nutzers. Wird bei Account-Deletion (Art. 17) als Teil der Kaskade aufgerufen.
- **Verschlüsselung:** Chunk-Inhalte und Vektoren liegen unverschlüsselt im Index (Trade-off: Vektorsuche und BM25 erfordern Klartext-Zugriff). Mitigiert durch Volume Encryption (AWS EBS), Netzwerkisolation und Tenant-Separation.
- **Datenresidenz:** Self-Hosting auf EU-Infrastruktur (AWS eu-central-1) gewährleistet.

---

## Sicherheitsimplikationen

- Weaviate in privatem Subnet, kein direkter Internet-Zugang
- API-Key-Authentifizierung für Weaviate-Zugriff
- Netzwerkisolation: Nur der API-Service darf auf Weaviate zugreifen (Security Groups)
- Volume Encryption (AWS EBS) für at-rest-Schutz
- Regelmäßige Updates des Weaviate-Containers für Security-Patches

---

## Revisionsdatum

2027-03-13 – Bewertung der Memory-Anforderungen und Skalierungsstrategie nach 12 Monaten, Evaluation von Weaviate Cloud vs. Self-Hosting.
