# ADR-002: PostgreSQL als primäre Datenbank

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

Das PWBS benötigt eine relationale Datenbank für Nutzerverwaltung, Konnektoren-Konfiguration, Dokument-Metadaten, Briefings, Audit-Logs und OAuth-Token-Speicherung. Die Datenbank muss JSONB für flexible Metadaten unterstützen, starke Transaktionsgarantien bieten und als Fallback für Vektorsuche dienen können (pgvector). Mandantenisolation auf Row-Level ist zwingend für DSGVO-Compliance.

---

## Entscheidung

Wir verwenden **PostgreSQL 16+** als primäre relationale Datenbank, weil es die beste Kombination aus JSONB-Flexibilität, Transaktionssicherheit, Ökosystem-Reife und Erweiterbarkeit (pgvector als Fallback) bietet.

---

## Optionen bewertet

| Option                   | Vorteile                                                                                                                                                                                           | Nachteile                                                                                                                                                              | Ausschlussgründe                        |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| **PostgreSQL** (gewählt) | JSONB für flexible Metadaten, starke ACID-Transaktionen, bewährtes Ökosystem, pgvector als Backup, hervorragendes Tooling (Alembic, pgAdmin, psql). Full-Text-Search (tsvector) für BM25-Fallback. | Kein natives horizontales Sharding.                                                                                                                                    | –                                       |
| MySQL                    | Weit verbreitet, gute Performance bei einfachen Queries.                                                                                                                                           | Schwächerer JSONB-Support, kein pgvector-Äquivalent, schwächere CHECK-Constraints.                                                                                     | JSONB- und Erweiterbarkeits-Nachteile   |
| MongoDB                  | Schemaflexibel, horizontale Skalierung eingebaut.                                                                                                                                                  | Schwächere Transaktionsgarantien, kein nativer Join, schwierigere Migrations-Verwaltung. Nicht geeignet für stark relationale Daten (Users ↔ Connections ↔ Documents). | Relationale Daten dominieren das Schema |
| CockroachDB              | PostgreSQL-kompatibel, natives horizontales Sharding, geographische Verteilung.                                                                                                                    | Höhere Latenz bei Single-Node, komplexeres Betriebsmodell, höhere Kosten. Overkill für MVP-Skala.                                                                      | Overkill für MVP-Anforderungen          |

---

## Konsequenzen

### Positive Konsequenzen

- JSONB-Spalten ermöglichen flexible Metadaten pro Dokumenttyp ohne Schema-Änderungen
- pgvector als Fallback, falls Weaviate ausfällt oder für einfache Vektorsuche ohne separaten Service
- Alembic für versionierte Schema-Migrationen mit Rollback-Fähigkeit
- Bewährtes Backup/Restore mit pg_dump, Point-in-Time-Recovery via WAL
- AWS RDS als managed Service mit automatischem Failover

### Negative Konsequenzen / Trade-offs

- Kein natives horizontales Sharding (mitigiert durch Read-Replicas und ggf. Citus-Extension in Phase 5)
- documents-Tabelle kann bei hohem Volumen langsam werden (mitigiert durch Partitioning nach created_at oder owner_id)
- Connection-Pool-Management erforderlich (PgBouncer in Phase 3+)

### Offene Fragen

- Partitioning-Strategie für documents-Tabelle evaluieren, sobald >100K Dokumente pro Nutzer erreicht werden
- pgvector-Performance vs. Weaviate benchmarken für Fallback-Szenarien

---

## DSGVO-Implikationen

- **Mandantenisolation:** Jede Query enthält `WHERE owner_id = $user_id` als Filter. Row-Level Security (RLS) als zusätzliche Absicherungsschicht möglich.
- **Löschbarkeit:** `DELETE CASCADE` auf allen Foreign Keys stellt sicher, dass Account-Löschung alle zugehörigen Daten entfernt.
- **Verschlüsselung:** AWS RDS Encryption (AES-256) für at-rest. Zusätzliche Spalten-Level-Verschlüsselung für OAuth-Tokens mit User-DEK.
- **Datenexport:** SQL-Queries können alle Nutzerdaten für Art.-15-Export zusammenstellen.
- **Ablaufdaten:** `expires_at`-Spalte auf documents-Tabelle ermöglicht automatische Löschung abgelaufener Daten.

---

## Sicherheitsimplikationen

- Erzwungenes TLS für alle Verbindungen (API → PostgreSQL)
- PostgreSQL in privatem Subnet, kein direkter Internet-Zugang
- Zugangsdaten über Environment-Variablen, nicht im Code
- Prepared Statements via SQLAlchemy verhindern SQL-Injection
- Regelmäßige Security-Updates über AWS RDS Maintenance Windows

---

## Revisionsdatum

2027-03-13 – Bewertung der Skalierungsanforderungen nach 12 Monaten, insbesondere Sharding-Bedarf und pgvector-Nutzung.
