# Sicherheitsaudit – PWBS

**Audit-Typ:** Internes Sicherheitsaudit (Vorbereitung für externes Audit)
**Scope:** Backend-API, Authentifizierung, Datenhaltung, LLM-Integration, Infrastruktur
**Framework:** OWASP Top 10 (2021) + DSGVO Art. 25/32
**Datum:** 14. März 2026
**Version:** 1.0
**Status:** Erstbewertung abgeschlossen

---

## Management Summary

Das PWBS verfügt über eine solide Sicherheitsbasis. Kritische Schutzmechanismen (Verschlüsselung, Authentifizierung, Mandantenisolation, Rate Limiting) sind implementiert. Die identifizierten Findings sind überwiegend im Bereich Härtung und operativer Sicherheit angesiedelt. Keine kritischen Schwachstellen offen.

| Schweregrad | Anzahl Findings | Status |
|:-----------:|:---------------:|:------:|
| Kritisch    | 0               | —      |
| Hoch        | 2               | Mitigiert / In Arbeit |
| Mittel      | 4               | Teilweise adressiert |
| Niedrig     | 3               | Akzeptiert / Geplant |

---

## OWASP Top 10 Assessment

### A01 – Broken Access Control

**Status:** ✅ Implementiert

| Kontrolle | Umsetzung | Bewertung |
|-----------|-----------|:---------:|
| JWT-basierte Authentifizierung | RS256-signierte Access Tokens, 15 Min. Laufzeit | ✅ |
| `owner_id`-Filter auf allen Daten-Queries | SQLAlchemy-Queries filtern nach `owner_id` aus JWT | ✅ |
| Ressource-Ownership-Prüfung | `get_current_user` Dependency auf allen geschützten Routen | ✅ |
| user_id aus JWT, nicht aus Request Body | `auth.py` Dependency extrahiert aus Bearer Token | ✅ |
| Neo4j-Queries mit `owner_id`-Filter | Cypher-Queries verwenden `WHERE n.owner_id = $owner_id` | ✅ |
| Weaviate-Queries mit Mandantenisolation | Filterung nach `owner_id` bei allen Suchanfragen | ✅ |

**Finding A01-F01 (Niedrig):** Health-Endpoint (`/api/v1/health`) ist öffentlich zugänglich. Dies ist beabsichtigt für Load-Balancer-Checks, sollte aber keine internen Details exponieren.
**Status:** Akzeptiertes Risiko.

---

### A02 – Cryptographic Failures

**Status:** ✅ Implementiert

| Kontrolle | Umsetzung | Bewertung |
|-----------|-----------|:---------:|
| Passwort-Hashing | Argon2id (`argon2-cffi`) | ✅ |
| JWT-Signierung | RS256 (asymmetrisch), Fallback auf HS256 für Dev | ✅ |
| OAuth-Token-Verschlüsselung | AES-256-GCM (Fernet) vor DB-Speicherung | ✅ |
| Refresh-Token-Speicherung | SHA-256 Hash in DB, Klartext nie persistiert | ✅ |
| Zufallswerte | `secrets.token_urlsafe()` | ✅ |
| Envelope Encryption | Per-User DEK mit AWS KMS als KEK (ADR-009) | ✅ Konzept |
| TLS in Transit | TLS 1.2+ erzwungen, HSTS-Header in Produktion | ✅ |

**Finding A02-F01 (Mittel):** Dev-Fallback auf HS256, wenn keine RSA-Keys konfiguriert sind. In Produktion MÜSSEN RSA-Keys vorhanden sein.
**Maßnahme:** Startup-Check hinzufügen, der bei `PWBS_ENV=production` ohne RSA-Keys den Start verweigert.

---

### A03 – Injection

**Status:** ✅ Implementiert

| Kontrolle | Umsetzung | Bewertung |
|-----------|-----------|:---------:|
| SQL-Injection | SQLAlchemy ORM mit parametrisierten Queries | ✅ |
| Cypher-Injection (Neo4j) | Parametrisierte Queries (`$parameter`) | ✅ |
| XSS | Frontend: React (default escaping), CSP-Header geplant | ⚠️ |
| Command Injection | Keine Shell-Aufrufe mit User-Input | ✅ |
| Input-Validierung | Pydantic v2 auf allen API-Endpunkten | ✅ |

**Finding A03-F01 (Mittel):** Content-Security-Policy (CSP) Header fehlt noch. Aktuell werden `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` gesetzt.
**Maßnahme:** CSP-Header in `SecurityHeadersMiddleware` ergänzen.

---

### A04 – Insecure Design

**Status:** ✅ Implementiert

| Kontrolle | Umsetzung | Bewertung |
|-----------|-----------|:---------:|
| Threat Modeling | ADR-Prozess mit Sicherheitsimplikationen | ✅ |
| DSGVO by Design | `owner_id`, `expires_at` auf allen Datenstrukturen | ✅ |
| Idempotenz | Upsert-Pattern, Cursor-basierte Sync | ✅ |
| Erklärbarkeit | Quellenreferenzen auf allen LLM-Outputs | ✅ |

Keine Findings.

---

### A05 – Security Misconfiguration

**Status:** ⚠️ Teilweise implementiert

| Kontrolle | Umsetzung | Bewertung |
|-----------|-----------|:---------:|
| Secrets über Env-Vars | `.env` nicht committet, `.env.example` vorhanden | ✅ |
| Debug-Endpoints in Prod | `PWBS_ENV`-basierte Steuerung vorhanden | ✅ |
| CORS-Konfiguration | `cors_origins` aus Settings, nicht `*` | ✅ |
| Security-Headers | `SecurityHeadersMiddleware` mit 5 Headern | ✅ |
| TrustedHost-Middleware | Konfiguriert mit `trusted_hosts` | ✅ |
| Dependency-Audit | Kein automatischer CVE-Scan konfiguriert | ⚠️ |

**Finding A05-F01 (Hoch):** Keine automatische Dependency-Vulnerability-Prüfung in CI/CD.
**Maßnahme:** `pip-audit` oder `safety` in CI-Pipeline integrieren. Für Frontend: `npm audit`.

**Finding A05-F02 (Niedrig):** `allow_methods=["*"]` und `allow_headers=["*"]` in CORS — sollte auf tatsächlich genutzte Methoden/Header eingeschränkt werden.
**Maßnahme:** Auf `["GET", "POST", "PUT", "DELETE", "PATCH"]` und `["Authorization", "Content-Type"]` beschränken.

---

### A06 – Vulnerable & Outdated Components

**Status:** ⚠️ Manuell geprüft

**Finding A06-F01 (Mittel):** Kein automatisierter CVE-Scanner. Dependencies werden manuell aktualisiert.
**Maßnahme:** GitHub Dependabot aktivieren oder Renovate konfigurieren.

---

### A07 – Identification & Authentication Failures

**Status:** ✅ Implementiert

| Kontrolle | Umsetzung | Bewertung |
|-----------|-----------|:---------:|
| JWT RS256 | Asymmetrische Signierung, kurze Laufzeit (15 Min.) | ✅ |
| Refresh Token Rotation | Opaque Tokens, SHA-256-Hashes, Rotation bei Nutzung | ✅ |
| Rate Limiting Login | 5 Anfragen/60s pro IP (Redis-backed) | ✅ |
| Passwort-Komplexität | Min. 12 Zeichen, Großbuchstabe, Zahl | ✅ |
| Generische Fehlermeldungen | Login-Fehler ohne User-Existenz-Hinweis | ✅ |
| Password Hashing Argon2id | Industriestandard, kein MD5/SHA1 | ✅ |

Keine Findings.

---

### A08 – Software & Data Integrity Failures

**Status:** ⚠️ Teilweise implementiert

| Kontrolle | Umsetzung | Bewertung |
|-----------|-----------|:---------:|
| Webhook-Signatur-Validierung | Slack: HMAC-SHA256, Gmail: Pub/Sub-Validierung | ✅ |
| LLM-Output-Grounding | Grounding-Service validiert Quellenreferenzen | ✅ |
| Alembic-Migrationen | Versionierte Schema-Änderungen | ✅ |

**Finding A08-F01 (Mittel):** Kein sigiertes Docker-Image-Verification in Deployment-Pipeline.
**Maßnahme:** Docker Content Trust oder Cosign für Image-Signierung evaluieren.

---

### A09 – Security Logging & Monitoring

**Status:** ⚠️ Teilweise implementiert

| Kontrolle | Umsetzung | Bewertung |
|-----------|-----------|:---------:|
| Access-Logging | `AccessLogMiddleware` loggt alle Requests | ✅ |
| Request-ID-Tracking | `RequestIDMiddleware` für Request-Korrelation | ✅ |
| PII nicht in Logs | Logging-Konventionen definiert (`nur IDs, keine Inhalte`) | ✅ |
| Auth-Failure-Logging | Fehlgeschlagene Logins geloggt | ✅ |
| Audit-Trail | Konzept definiert, Implementierung in Arbeit | ⚠️ |

**Finding A09-F01 (Hoch):** Dedizierter Audit-Trail (append-only `audit_log`-Tabelle) ist konzipiert aber noch nicht vollständig implementiert. Datenschutzrelevante Aktionen (Datenlöschung, Connector-Anbindung, Export) sollten unveränderlich protokolliert werden.
**Maßnahme:** Audit-Log-Tabelle und Service implementieren (Phase 3 Backlog).

---

### A10 – SSRF (Server-Side Request Forgery)

**Status:** ✅ Konzept definiert

| Kontrolle | Umsetzung | Bewertung |
|-----------|-----------|:---------:|
| Private-IP-Blocking | In security.instructions.md spezifiziert | ✅ Richtlinie |
| HTTP-Timeout 30s | Konfiguriert für externe Calls | ✅ |
| OAuth-Callback-Allowlist | Connector-spezifische Redirect-URIs | ✅ |

**Finding A10-F01 (Niedrig):** SSRF-Schutz (Private-IP-Blocking) ist als Richtlinie definiert, sollte als Middleware/Utility zentral implementiert werden.
**Maßnahme:** URL-Validierungsfunktion für alle externen HTTP-Clients bereitstellen.

---

## DSGVO-Compliance Assessment

### Art. 5 – Grundsätze

| Grundsatz | Umsetzung | Status |
|-----------|-----------|:------:|
| Datensparsamkeit | Nur notwendige Daten, definierte Zwecke | ✅ |
| Zweckbindung | Datentypen mit definierten Verarbeitungszwecken | ✅ |
| Speicherbegrenzung | `expires_at` auf allen Dokumenten, Cleanup-Job | ✅ |
| Integrität/Vertraulichkeit | Envelope Encryption, TLS, Argon2id | ✅ |

### Art. 15–22 – Betroffenenrechte

| Recht | Umsetzung | Status |
|-------|-----------|:------:|
| Auskunft (Art. 15) | API-Endpunkte für Datenabruf vorhanden | ✅ |
| Löschung (Art. 17) | DEK-Löschung = kryptografische Löschung + DB-Cascade | ✅ Konzept |
| Datenportabilität (Art. 20) | Export-Funktion im Backlog | ⚠️ Ausstehend |
| Widerspruch gegen Verarbeitung | Connector-Deaktivierung, Account-Löschung | ✅ |

### Art. 25 – Privacy by Design & Default

| Maßnahme | Umsetzung | Status |
|----------|-----------|:------:|
| `owner_id` auf allen Datenstrukturen | Durchgängig implementiert | ✅ |
| `expires_at` Standard-Werte | Per Datentyp konfiguriert | ✅ |
| Mandantenisolation | DB-Level auf allen drei Datenbanken | ✅ |
| Kein LLM-Training mit Nutzerdaten | Zero Data Retention bei API-Providern | ✅ |

### Art. 30 – Verarbeitungsverzeichnis

**Status:** ✅ Erstellt (`legal/verarbeitungsverzeichnis.md`)
10 Verarbeitungstätigkeiten dokumentiert.

### Art. 32 – Technische und organisatorische Maßnahmen

**Status:** ✅ Dokumentiert (`legal/tom.md`)
10 Kontrollbereiche mit konkreten Maßnahmen.

### Art. 28 – Auftragsverarbeitung

**Status:** ✅ Templates erstellt
AVV-Templates für AWS, OpenAI, Anthropic, Vercel unter `legal/avv/`.

---

## Zusammenfassung der Findings

| ID | Schweregrad | Beschreibung | Status | Maßnahme |
|----|:-----------:|-------------|:------:|----------|
| A02-F01 | Mittel | HS256-Fallback in Dev ohne RSA-Keys | Offen | Startup-Check für Production |
| A03-F01 | Mittel | CSP-Header fehlt | Offen | SecurityHeadersMiddleware erweitern |
| A05-F01 | Hoch | Kein automatischer CVE-Scan | Offen | pip-audit + npm audit in CI |
| A05-F02 | Niedrig | CORS allow_methods/headers zu permissiv | Offen | Auf genutzte Werte einschränken |
| A06-F01 | Mittel | Kein Dependabot/Renovate | Offen | GitHub Dependabot aktivieren |
| A08-F01 | Mittel | Keine Docker-Image-Signierung | Offen | Cosign evaluieren |
| A09-F01 | Hoch | Audit-Trail nicht vollständig implementiert | In Arbeit | Phase 3 Backlog |
| A10-F01 | Niedrig | SSRF-Schutz nur als Richtlinie | Offen | Zentrale URL-Validierung |
| A01-F01 | Niedrig | Health-Endpoint öffentlich | Akzeptiert | — |

---

## Empfehlungen für externes Audit

1. **Vor dem Audit schließen:** A05-F01 (CVE-Scanner), A02-F01 (Production-Check), A03-F01 (CSP)
2. **Dokumentation bereithalten:** TOM, Verarbeitungsverzeichnis, AVV-Templates, ADR-009
3. **Penetrationstest:** Fokus auf API-Endpunkte, JWT-Handling, Mandantenisolation
4. **LLM-spezifische Risiken:** Prompt Injection, Datenexfiltration über LLM-Outputs — Grounding-Service als Mitigation dokumentieren

---

## Nächste Schritte

- [ ] A05-F01: `pip-audit` in GitHub Actions CI integrieren
- [ ] A02-F01: Production-Startup-Guard für RSA-Keys
- [ ] A03-F01: CSP-Header implementieren
- [ ] A06-F01: Dependabot `.github/dependabot.yml` erstellen
- [ ] A09-F01: Audit-Log-Service spezifizieren
- [ ] Externes Audit beauftragen nach Schließung der Hoch-Findings

---

## Anhänge

- TOM: `legal/tom.md`
- Verarbeitungsverzeichnis: `legal/verarbeitungsverzeichnis.md`
- AVV-Templates: `legal/avv/avv-aws.md`, `legal/avv/avv-openai.md`, `legal/avv/avv-anthropic.md`, `legal/avv/avv-vercel.md`
- Verschlüsselungsstrategie: `docs/adr/009-envelope-encryption.md`
- DSGVO-Erstkonzept: `docs/dsgvo-erstkonzept.md`
