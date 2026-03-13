# Verschluesselungsstrategie: PWBS

**Version:** 1.0
**Datum:** 13. Maerz 2026
**Status:** Genehmigt (Architekturentscheidung)
**Basis:** DSGVO-Erstkonzept (docs/dsgvo-erstkonzept.md), ARCHITECTURE.md Abschnitt 5.1
**Blockiert:** TASK-022 (EncryptionService implementieren)

---

## 1. Uebersicht

Das PWBS verwendet eine **Envelope-Encryption-Architektur** mit einer dreistufigen Key-Hierarchie. Ziel ist der Schutz aller personenbezogenen Daten at rest und in transit bei gleichzeitiger Erhaltung der Suchfunktionalitaet.

```
+------------------------------------------------------------+
|  AWS KMS                                                    |
|  +------------------------------------------------------+  |
|  | Master Key (CMK)                                     |  |
|  | - Region: eu-central-1                                |  |
|  | - Rotation: automatisch, jaehrlich                    |  |
|  +------------------------------------------------------+  |
+-----------------------------+------------------------------+
                              |
                   verschluesselt/entschluesselt
                              |
                              v
+------------------------------------------------------------+
|  Key Encryption Key (KEK)                                   |
|  - Gespeichert als Env-Variable (ENCRYPTION_KEK)            |
|  - Verwendet fuer: Wrapping aller DEKs                      |
|  - Rotation: alle 90 Tage                                   |
+-----------------------------+------------------------------+
                              |
                   verschluesselt/entschluesselt
                              |
                              v
+------------------------------------------------------------+
|  Data Encryption Keys (DEKs)         pro Nutzer             |
|  - Generiert bei User-Erstellung                            |
|  - Gespeichert in users-Tabelle (wrapped mit KEK)           |
|  - Algorithmus: AES-256-GCM                                 |
|  - Verwendet fuer: OAuth-Tokens, sensible Metadaten         |
+------------------------------------------------------------+
```

---

## 2. At-Rest-Verschluesselung pro Speicherschicht

### 2.1 PostgreSQL

| Aspekt | Loesung |
|--------|---------|
| **Datenbankebene** | AWS RDS Encryption (AES-256, KMS-managed) fuer gesamtes Volume |
| **Spaltenebene** | Sensible Felder mit User-DEK verschluesselt: `oauth_access_token`, `oauth_refresh_token`, `content` (sofern PII) |
| **Algorithmus** | AES-256-GCM via User-DEK |
| **Key-Speicherung** | `users.encrypted_dek` (wrapped mit KEK) |
| **Backup** | RDS-Snapshots sind automatisch verschluesselt (KMS) |
| **Performance-Impact** | Minimal (RDS TDE transparent, Spalten-Decrypt nur bei Zugriff) |

```python
# Implementierungsbeispiel (EncryptionService)
class EncryptionService:
    def encrypt_field(self, plaintext: str, user_dek: bytes) -> str:
        """Verschluesselt ein Datenbankfeld mit dem User-DEK."""
        # AES-256-GCM mit zufaelligem Nonce
        # Output: base64(nonce + ciphertext + tag)

    def decrypt_field(self, ciphertext: str, user_dek: bytes) -> str:
        """Entschluesselt ein Datenbankfeld."""

    def unwrap_dek(self, wrapped_dek: bytes, kek: bytes) -> bytes:
        """Entpackt einen User-DEK mit dem KEK."""
```

### 2.2 Weaviate (Vektor-Store)

| Aspekt | Loesung |
|--------|---------|
| **Verschluesselung** | Volume-Encryption auf Infrastrukturebene (EBS Encryption, AES-256) |
| **Vektordaten** | **NICHT** auf Anwendungsebene verschluesselt |
| **Properties** | Metadaten (`source_id`, `title`, `created_at`) im Klartext fuer Filter-Queries |
| **Content-Property** | Unverschluesselt gespeichert (benoetigt fuer BM25-Suche und Anzeige) |

#### Trade-off: Weaviate-Vektoren unverschluesselt

**Begruendung:** Weaviate benoetigt Zugriff auf die rohen Vektoren fuer Nearest-Neighbor-Suche (HNSW-Index). Anwendungsebene-Verschluesselung wuerde die Suchfunktionalitaet zerstoeren, da verschluesselte Vektoren keine semantische Aehnlichkeit mehr transportieren.

**Risikominimierung:**
1. Volume-Encryption schuetzt gegen physischen Zugriff auf Disk
2. **Tenant-Isolation:** Jede Query filtert nach `owner_id` - kein Cross-User-Zugriff moeglich
3. **Netzwerk-Isolation:** Weaviate ist nicht oeffentlich erreichbar (nur internes Netzwerk)
4. **Access Control:** Nur der API-Service hat Zugriff auf Weaviate (Security Group)

**Akzeptiertes Risiko:** Ein Angreifer mit Root-Zugriff auf den Weaviate-Host koennte Vektordaten lesen. Dieses Risiko wird durch Infrastruktur-Security (AWS Security Groups, keine oeffentliche IP, SSH-Key-only) mitigiert.

### 2.3 Neo4j (Knowledge Graph)

| Aspekt | Loesung |
|--------|---------|
| **Verschluesselung** | Volume-Encryption auf Infrastrukturebene (EBS Encryption, AES-256) |
| **Graphdaten** | **NICHT** auf Anwendungsebene verschluesselt |
| **Properties** | Node-Properties (`name`, `description`) im Klartext fuer Cypher-Queries |

#### Trade-off: Neo4j-Graphdaten unverschluesselt

**Begruendung:** Neo4j benoetigt Klartext-Zugriff auf Node- und Relationship-Properties fuer:
- Graph-Traversal-Queries (WHERE-Clauses)
- Volltextsuche innerhalb des Graphen
- Pattern-Matching (MATCH-Queries)

Anwendungsebene-Verschluesselung wuerde erfordern, dass jeder Node vor jeder Query entschluesselt wird - bei Graph-Traversals mit Tiefe 2+ waere das ein massiver Performance-Einbruch.

**Risikominimierung:** Identisch zu Weaviate (Volume-Encryption, Tenant-Isolation, Netzwerk-Isolation, Access Control).

**Akzeptiertes Risiko:** Identisch zu Weaviate. Dokumentiert und bewusst akzeptiert.

### 2.4 Redis (Cache / Session Store)

| Aspekt | Loesung |
|--------|---------|
| **Verschluesselung** | Redis-TLS + ElastiCache Encryption at Rest |
| **Session-Daten** | Kurzlebig (TTL), kein sensitiver Content |
| **Caching** | Keine PII in Redis-Keys. Cache-Values sind transient. |
| **Auth-Tokens** | JWT-Blacklist (Token-IDs, keine Payloads) |

---

## 3. In-Transit-Verschluesselung

| Verbindung | Protokoll | Minimum-Version | Erzwungen |
|------------|-----------|----------------|-----------|
| Client <-> API (extern) | TLS | 1.3 | Ja (HTTPS only, HSTS) |
| API <-> PostgreSQL | TLS | 1.2 | Ja (`sslmode=require`) |
| API <-> Weaviate | TLS | 1.2 | Ja (internes Netzwerk, Phase 3: mTLS) |
| API <-> Neo4j | TLS (bolt+s) | 1.2 | Ja |
| API <-> Redis | TLS | 1.2 | Ja (ElastiCache in-transit) |
| API <-> OpenAI/Anthropic | TLS | 1.3 | Ja (HTTPS, von Provider erzwungen) |
| API <-> Google/Notion/Zoom | TLS | 1.3 | Ja (OAuth2 erfordert HTTPS) |
| Frontend <-> API | TLS | 1.3 | Ja (Vercel erzwingt HTTPS) |

### Phase-3-Erweiterung: mTLS

Ab Phase 3 (Service-Split) wird mTLS zwischen internen Services implementiert:
- Jeder Service erhaelt ein Client-Zertifikat
- Gegenseitige Authentifizierung
- Automatische Zertifikats-Rotation via AWS Certificate Manager

---

## 4. Key-Management

### 4.1 Key-Lebenszyklus

| Key-Typ | Erstellung | Rotation | Revocation |
|---------|-----------|----------|------------|
| **CMK (AWS KMS)** | Einmalig bei Projekt-Setup | Automatisch jaehrlich (AWS managed) | Nur bei Kompromittierung |
| **KEK** | Bei Deployment | Alle 90 Tage | Bei Verdacht auf Leak |
| **User-DEK** | Bei User-Registrierung | Bei KEK-Rotation (Re-Wrap) | Bei Account-Loeschung |

### 4.2 KEK-Rotation

```
1. Neuen KEK generieren (AES-256)
2. Alten KEK beibehalten (Dual-Read)
3. Alle User-DEKs mit neuem KEK re-wrappen (Batch-Job)
4. Alten KEK nach erfolgreicher Migration loeschen
5. Gesamtdauer: <5min fuer 10.000 User
```

### 4.3 User-DEK-Erstellung

```python
# Bei User-Registrierung:
raw_dek = os.urandom(32)  # 256 Bit
wrapped_dek = aes_gcm_encrypt(raw_dek, kek)
# Speichern: users.encrypted_dek = wrapped_dek
```

### 4.4 Key-Escrow und Recovery

- KEK-Backup in AWS KMS (verschluesselt mit CMK)
- Recovery-Prozess dokumentiert (nur mit 2-Person-Regel)
- Kein Single Point of Failure fuer Key-Zugriff

---

## 5. Verschluesselungs-Matrix (Zusammenfassung)

| Datentyp | PostgreSQL | Weaviate | Neo4j | Redis |
|----------|-----------|----------|-------|-------|
| OAuth-Tokens | AES-256-GCM (User-DEK) | - | - | - |
| Dokumentinhalt | RDS TDE | Volume-Enc | - | - |
| Embeddings | - | Volume-Enc | - | - |
| Graph-Nodes | - | - | Volume-Enc | - |
| Graph-Relations | - | - | Volume-Enc | - |
| Briefings | RDS TDE | - | - | - |
| Audit-Log | RDS TDE | - | - | - |
| Sessions | - | - | - | ElastiCache Enc |
| User-DEKs | KEK-wrapped | - | - | - |

**Legende:**
- AES-256-GCM (User-DEK): Anwendungsebene-Verschluesselung mit nutzer-spezifischem Key
- RDS TDE: Transparente Datenverschluesselung auf Datenbankebene
- Volume-Enc: EBS Volume Encryption (Infrastrukturebene)
- KEK-wrapped: Key ist mit dem Key Encryption Key verschluesselt

---

## 6. Implementierungs-Reihenfolge

| Phase | Massnahme | Task |
|-------|-----------|------|
| MVP (Phase 2) | EncryptionService: encrypt_field, decrypt_field, wrap/unwrap DEK | TASK-022 |
| MVP (Phase 2) | OAuth-Token-Verschluesselung in Connection-Tabelle | TASK-043 |
| MVP (Phase 2) | RDS TDE aktivieren | TASK-010 (Infra) |
| MVP (Phase 2) | Volume-Encryption fuer Weaviate/Neo4j (Docker: dev, EBS: prod) | TASK-010 (Infra) |
| Phase 3 | mTLS zwischen Services | STREAM-PHASE3 |
| Phase 3 | Redis TLS | STREAM-PHASE3 |
| Phase 4 | Key-Rotation-Automatisierung | STREAM-PHASE4 |

---

## Referenzen

- ARCHITECTURE.md, Abschnitt 5.1 (Verschluesselungsstrategie)
- docs/dsgvo-erstkonzept.md (DSGVO-Anforderungen)
- NIST SP 800-57 (Key Management Recommendations)
- AWS KMS Best Practices
