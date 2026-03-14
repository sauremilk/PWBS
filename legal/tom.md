# Technische und Organisatorische Maßnahmen (TOM)

**Verantwortlicher:** PWBS – Persönliches Wissens-Betriebssystem
**Version:** 1.0
**Datum:** 14. März 2026
**Status:** Aktiv
**Nächste Überprüfung:** 14. September 2026

---

## 1. Zutrittskontrolle (physisch)

| Maßnahme           | Umsetzung                                                              | Status    |
| ------------------ | ---------------------------------------------------------------------- | --------- |
| Serverstandort     | AWS eu-central-1 (Frankfurt), ISO 27001 zertifiziert                   | ✅ Aktiv  |
| Physischer Zugang  | Durch AWS verwaltet (SOC 2 Type II, ISO 27001)                         | ✅ Aktiv  |
| Entwickler-Rechner | Festplattenverschlüsselung (BitLocker/FileVault) bei allen Entwicklern | ✅ Policy |

---

## 2. Zugangskontrolle (logisch)

| Maßnahme          | Umsetzung                                                      | Status     |
| ----------------- | -------------------------------------------------------------- | ---------- |
| Authentifizierung | JWT-basiert, RS256-Signatur, 15min Access-Token                | ✅ Aktiv   |
| Token-Rotation    | Refresh-Token 30 Tage, automatische Rotation bei Nutzung       | ✅ Aktiv   |
| Passwort-Hashing  | Argon2id mit individuellen Salts                               | ✅ Aktiv   |
| OAuth2-Tokens     | Fernet-verschlüsselt in Datenbank gespeichert                  | ✅ Aktiv   |
| Rate Limiting     | Login: 5 Versuche/min pro IP; API: konfigurierbar pro Endpunkt | ✅ Aktiv   |
| Multi-Faktor      | Geplant für Phase 4                                            | 📋 Geplant |

---

## 3. Zugriffskontrolle (Autorisierung)

| Maßnahme                  | Umsetzung                                                      | Status   |
| ------------------------- | -------------------------------------------------------------- | -------- |
| Mandanten-Isolation       | Jede DB-Query enthält `WHERE owner_id = :user_id`              | ✅ Aktiv |
| Ressource-Ownership       | Vor jeder Lese-/Schreiboperation wird Ownership geprüft        | ✅ Aktiv |
| user_id aus JWT           | `user_id` wird ausschließlich aus verifiziertem JWT extrahiert | ✅ Aktiv |
| Keine globalen Indizes    | Kein übergreifender Zugriff auf Nutzerdaten möglich            | ✅ Aktiv |
| Weaviate Tenant-Isolation | Separate Tenant-Namespaces pro Nutzer                          | ✅ Aktiv |
| Neo4j owner_id-Filter     | Alle Cypher-Queries mit `WHERE n.owner_id = $owner_id`         | ✅ Aktiv |

---

## 4. Weitergabekontrolle (Transport)

| Maßnahme            | Umsetzung                                                      | Status   |
| ------------------- | -------------------------------------------------------------- | -------- |
| TLS 1.3             | Alle externen API-Verbindungen über HTTPS                      | ✅ Aktiv |
| HSTS                | `Strict-Transport-Security: max-age=31536000` in Produktion    | ✅ Aktiv |
| Security Headers    | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` | ✅ Aktiv |
| Webhook-Validierung | HMAC-SHA256 Signaturvalidierung (Gmail, Slack)                 | ✅ Aktiv |
| CORS                | Explizite Allowlist, kein Wildcard in Produktion               | ✅ Aktiv |

---

## 5. Eingabekontrolle

| Maßnahme                | Umsetzung                                                         | Status   |
| ----------------------- | ----------------------------------------------------------------- | -------- |
| Input-Validierung       | Alle API-Inputs über Pydantic v2 validiert                        | ✅ Aktiv |
| Parametrisierte Queries | SQLAlchemy ORM + parametrisierte SQL-Statements                   | ✅ Aktiv |
| Neo4j-Parameter         | Cypher-Queries mit `$parameter`-Syntax statt String-Interpolation | ✅ Aktiv |
| Webhook-Payloads        | Pydantic-Validierung und Signaturprüfung vor Verarbeitung         | ✅ Aktiv |
| Audit-Log               | Unveränderlicher `audit_log` für datenschutzrelevante Aktionen    | ✅ Aktiv |

---

## 6. Auftragskontrolle

| Maßnahme                  | Umsetzung                                                   | Status           |
| ------------------------- | ----------------------------------------------------------- | ---------------- |
| AVV mit AWS               | Data Processing Agreement (EU-Standard)                     | ✅ Abgeschlossen |
| AVV mit Anthropic         | DPA, Zero Data Retention, EU-Datenverarbeitung bestätigt    | ✅ Abgeschlossen |
| AVV mit OpenAI            | DPA, Zero Data Retention API, kein Training mit Nutzerdaten | ✅ Abgeschlossen |
| AVV mit Vercel            | DPA für Frontend-Hosting, keine Backend-Daten               | ✅ Abgeschlossen |
| Sub-Processor-Überwachung | Vierteljährliche Überprüfung aller Dienstleister-Policies   | ✅ Prozess       |

---

## 7. Verfügbarkeitskontrolle

| Maßnahme          | Umsetzung                                              | Status          |
| ----------------- | ------------------------------------------------------ | --------------- |
| Backups           | Verschlüsselte PostgreSQL-Backups (RPO < 1h, RTO < 4h) | ✅ Aktiv        |
| Redundanz         | AWS ECS Fargate mit Multi-AZ-Deployment                | ✅ Aktiv        |
| Health Checks     | Liveness und Readiness Probes auf allen Services       | ✅ Aktiv        |
| Monitoring        | Prometheus/Grafana für Metriken und Alerting           | ✅ Aktiv        |
| Incident Response | Eskalationsprozess mit definierten Antwortzeiten       | ✅ Dokumentiert |

---

## 8. Trennungskontrolle

| Maßnahme                  | Umsetzung                                                     | Status    |
| ------------------------- | ------------------------------------------------------------- | --------- |
| Logische Datentrennung    | `owner_id` als Pflichtfeld auf allen nutzerbezogenen Tabellen | ✅ Aktiv  |
| Getrennte DB pro Umgebung | Separate PostgreSQL-Instanzen für Dev/Staging/Prod            | ✅ Aktiv  |
| Kein Cross-User-Lernen    | Keine gemeinsamen Embedding-Spaces oder ML-Modelle            | ✅ Aktiv  |
| Test-/Prod-Trennung       | Keine Produktionsdaten in Test-Umgebungen                     | ✅ Policy |

---

## 9. Verschlüsselung

| Maßnahme                     | Umsetzung                                                  | Status         |
| ---------------------------- | ---------------------------------------------------------- | -------------- |
| At Rest: Envelope Encryption | KEK (AWS KMS) wraps DEK (pro Nutzer, AES-256-GCM)          | ✅ Aktiv       |
| At Rest: Volume Encryption   | AWS EBS und RDS Storage-Verschlüsselung                    | ✅ Aktiv       |
| In Transit: TLS 1.3          | Alle externen Verbindungen verschlüsselt                   | ✅ Aktiv       |
| OAuth-Tokens                 | Fernet-Verschlüsselung vor DB-Speicherung                  | ✅ Aktiv       |
| PII-Spalten                  | Spaltenebene-Verschlüsselung via `cryptography`-Bibliothek | ✅ Aktiv       |
| Account-Löschung             | DEK löschen → alle Daten kryptografisch unlesbar           | ✅ Architektur |

---

## 10. Organisatorische Maßnahmen

| Maßnahme                      | Umsetzung                                            | Status          |
| ----------------------------- | ---------------------------------------------------- | --------------- |
| Logging ohne PII              | Nur IDs und Metadaten in Logs, keine Inhalte         | ✅ Policy       |
| Secrets-Management            | Umgebungsvariablen, nie im Code. `.env` nicht in Git | ✅ Policy       |
| Code-Review                   | PR-basierter Workflow mit DSGVO-Checkliste           | ✅ Prozess      |
| ADR-Dokumentation             | Sicherheitsimplikationen in jedem ADR                | ✅ Prozess      |
| Schulungen                    | Jährliche DSGVO-Schulung für alle Entwickler         | 📋 Geplant      |
| Datenschutz-Folgenabschätzung | DSFA für LLM-Verarbeitung erstellt                   | ✅ Dokumentiert |

---

## Änderungshistorie

| Version | Datum      | Änderung                                             |
| ------- | ---------- | ---------------------------------------------------- |
| 1.0     | 14.03.2026 | Erstversion als Teil von TASK-147 (Sicherheitsaudit) |
