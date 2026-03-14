# ADR-009: Envelope Encryption mit per-User-Keys

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

Das PWBS speichert hochsensible personenbezogene Daten: OAuth-Tokens, Kalendereinträge, Notizen, Meeting-Transkripte, LLM-generierte Briefings. Die Verschlüsselungsstrategie muss DSGVO-konform sein (Art. 32: angemessene technische Maßnahmen), Account-Löschung ohne Gesamt-Re-Encryption ermöglichen und gleichzeitig serverseitige Suche und Briefing-Generierung nicht verhindern. Die Balance zwischen Sicherheit und Funktionalität ist der zentrale Trade-off.

---

## Entscheidung

Wir verwenden **Envelope Encryption mit per-User Data Encryption Keys (DEKs)**, wobei AWS KMS als Key Encryption Key (KEK) dient, weil dieses Schema Account-Löschung durch einfaches DEK-Löschen ermöglicht und Key-Management-Komplexität an AWS KMS delegiert.

---

## Optionen bewertet

| Option                                      | Vorteile                                                                                                                                                                                     | Nachteile                                                                                                                                                                                                | Ausschlussgründe                                |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| **Envelope Encryption (KEK/DEK)** (gewählt) | Per-User-Keys ermöglichen Account-Löschung ohne Gesamt-Re-Encryption (DEK löschen = Daten kryptografisch unlesbar). AWS KMS als KEK vermeidet Key-Management-Komplexität. Industriestandard. | Weaviate-Vektoren liegen unverschlüsselt im Index (notwendig für Suche). Erfordert sorgfältiges Key-Lifecycle-Management.                                                                                | –                                               |
| Applikations-Level Encryption nur           | Einfacherer Aufbau, kein KMS erforderlich.                                                                                                                                                   | Key-Management komplett in der Anwendung – höheres Risiko durch Key-Verlust. Kein HSM-backed Key-Storage. Keine Key-Rotation ohne Re-Encryption.                                                         | Unzureichendes Key-Management                   |
| DB-Level Encryption only                    | Einfachste Implementierung (AWS RDS Encryption), transparent für Anwendung.                                                                                                                  | Kein per-User-Isolation – alle Daten mit gleichem Key verschlüsselt. Account-Löschung erfordert keine kryptografische Isolation. Schutz nur gegen physischen Datenträgerzugriff, nicht gegen DB-Zugriff. | Keine per-User-Isolation                        |
| Zero-Knowledge-Architektur                  | Maximale Sicherheit – Server kann Daten nicht entschlüsseln.                                                                                                                                 | Verhindert serverseitige Suche und Briefing-Generierung. Nutzer müssen Key-Material selbst verwalten. Key-Verlust = Datenverlust. Inkompatibel mit der Kernfunktionalität des PWBS.                      | Inkompatibel mit serverseitiger Suche/Briefings |

---

## Konsequenzen

### Positive Konsequenzen

- Account-Löschung: DEK löschen → alle Nutzerdaten kryptografisch unlesbar, ohne teure Re-Encryption
- AWS KMS: HSM-backed Key-Storage, automatische Key-Rotation, Audit-Trail über CloudTrail
- Per-User-DEK: Kompromittierung eines DEKs betrifft nur einen Nutzer, nicht alle
- Industriestandard: Bewährtes Schema, das von AWS, Google Cloud und Azure empfohlen wird
- Kompatibel mit serverseitiger Suche und Briefing-Generierung (Server entschlüsselt temporär für Verarbeitung)

### Negative Konsequenzen / Trade-offs

- Weaviate-Vektoren und BM25-Index liegen unverschlüsselt im Klartext (notwendig für Suche). Mitigiert durch Volume Encryption (AWS EBS), Netzwerkisolation und physische Tenant-Separation in Weaviate.
- Neo4j-Graph-Daten liegen im Klartext für Query-Performance. Mitigiert durch Volume Encryption und Netzwerkisolation.
- Key-Rotation des KEK erfordert Re-Wrapping aller DEKs (nicht Re-Encryption der Daten – deutlich günstiger)
- Bei AWS-KMS-Ausfall können keine neuen Daten verschlüsselt werden (mitigiert: KMS Multi-Region-Keys, DEK-Caching im Application Memory)

### Offene Fragen

- DEK-Caching-Strategie: Wie lange bleibt ein entschlüsselter DEK im Application Memory? (Trade-off: Performance vs. Angriffsfläche)
- Backup-Encryption: Separate Backup-Keys vs. User-DEKs für Backups
- Key-Rotation-Frequenz für KEK definieren

---

## DSGVO-Implikationen

- **Art. 32 (Sicherheit):** Envelope Encryption erfüllt die Anforderung an „angemessene technische Maßnahmen" zum Schutz personenbezogener Daten.
- **Art. 17 (Löschung):** DEK-Löschung macht Nutzerdaten kryptografisch unlesbar – effektive Löschung ohne physisches Überschreiben aller Datenbankeinträge.
- **Art. 25 (Privacy by Design):** Per-User-Verschlüsselung als Grundstruktur, nicht als optionales Feature.
- **Verschlüsselungsmatrix:**
  - PostgreSQL: AWS RDS TDE + Spalten-Level AES-256-GCM für OAuth-Tokens mit User-DEK
  - Weaviate: Volume Encryption (AWS EBS) – Klartext im Index (dokumentierter Trade-off)
  - Neo4j: Volume Encryption (AWS EBS) – Klartext im Graph (dokumentierter Trade-off)
  - Redis: AWS ElastiCache Encryption at Rest
  - Backups: AES-256-GCM mit separaten Backup-Keys

---

## Sicherheitsimplikationen

- AWS KMS als HSM-backed Key-Storage vermeidet handgemachtes Key-Management
- CloudTrail-Logging für alle KEK-Operationen (Encrypt, Decrypt, GenerateDataKey)
- DEKs werden verschlüsselt in der users-Tabelle gespeichert (`encryption_key_enc` Spalte)
- Entschlüsselte DEKs nur temporär im Application Memory – kein Logging, kein Disk-Swap
- Risiko: Side-Channel-Angriffe auf Application Memory (mitigiert: Nitro-Enclaves für Phase 5 evaluieren)

---

## Revisionsdatum

2027-03-13 – Bewertung der Key-Rotation-Erfahrungen, DEK-Caching-Strategie und Evaluation von AWS Nitro Enclaves für zusätzliche Isolation.
