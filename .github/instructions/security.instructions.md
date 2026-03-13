---
applyTo: "**/*.{py,ts,tsx}"
---

# Sicherheits- & DSGVO-Instruktionen

## DSGVO – Datenschutzgrundverordnung

### Grundprinzipien (nicht verhandelbar)

1. **Datensparsamkeit:** Nur Daten erheben, die für den definierten Zweck zwingend nötig sind.
2. **Zweckbindung:** Daten dürfen nur für den ursprünglich definierten Zweck verarbeitet werden.
3. **Speicherbegrenzung:** Jedes Datum hat ein `expires_at`. Ablaufprüfung in der Cleanup-Pipeline.
4. **Löschbarkeit:** `DELETE CASCADE` auf alle `user_id`-gebundenen Daten. GDPR-Delete-Funktion testen.
5. **Keine LLM-Training-Nutzung:** Nutzerdaten dürfen NIEMALS für externes LLM-Training verwendet werden.

### Mandanten-Isolation

```python
# PFLICHT: Jede Query gegen Nutzerdaten mit user_id filtern
# FALSCH
docs = await db.query("SELECT * FROM documents")
# KORREKT
docs = await db.query("SELECT * FROM documents WHERE owner_id = $1", user_id)
```

### Verschlüsselung

- **At Rest:** PostgreSQL-Verschlüsselung auf Spaltenebene für PII-Felder (`cryptography`-Bibliothek).
- **In Transit:** TLS 1.3 zwingend. Keine HTTP-Verbindungen für API-Calls in Produktion.
- **OAuth-Tokens:** Refresh-Tokens mit `Fernet`-Verschlüsselung vor DB-Speicherung verschlüsseln.

### Logging-Regeln

```python
# FALSCH – PII in Logs
logger.info(f"Processing document: {doc.content[:100]}")
# KORREKT – nur IDs und Metadaten
logger.info(f"Processing document: id={doc.id} source={doc.source}")
```

---

## OWASP Top 10 – Pflichtprüfung

### A01 – Broken Access Control

- Jeder API-Endpunkt muss authentifizierten Nutzer prüfen.
- Ressource-Ownership vor jeder Lese-/Schreib-Operation verifizieren.
- `user_id` immer aus JWT-Token extrahieren, nie aus Request-Body lesen.

### A02 – Cryptographic Failures

- Passwörter: `argon2` (primär) oder `bcrypt` – niemals MD5/SHA1.
- Zufallswerte: `secrets.token_urlsafe()` – niemals `random`.
- API-Keys: Mindestlänge 32 Bytes, urlsafe base64-encodiert.

### A03 – Injection

```python
# SQL-Injection: Immer parametrisierte Queries (asyncpg/SQLAlchemy)
# FALSCH
await db.execute(f"SELECT * FROM docs WHERE source_id = '{source_id}'")
# KORREKT
await db.execute("SELECT * FROM docs WHERE source_id = $1", source_id)

# Cypher-Injection (Neo4j): Immer Parameter übergeben
session.run("MATCH (n:Entity {id: $id}) RETURN n", id=entity_id)
```

### A04 – Insecure Design

- Threat-Modelling für neue Features: Im ADR-Dokument Sicherheitsimplikationen dokumentieren.
- Keine Konstruktoren mit privilegiertem Zustand als öffentliche API exponieren.

### A05 – Security Misconfiguration

- Alle Secrets über Umgebungsvariablen. `.env.example` mit Platzhaltern committen, `.env` niemals.
- Debug-Endpoints (`/docs`, `/redoc`) in Produktion deaktivieren (`PWBS_ENV=production`).
- CORS auf explizite Allowlist beschränken – kein `*` in Produktion.
- Security-Headers: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`.

### A07 – Identification & Authentication Failures

- JWT: `RS256` statt `HS256`. Kurze Access-Token-Laufzeit (15 Min). Lange Refresh-Tokens (30 Tage) mit Rotation.
- Rate Limiting: Login-Endpunkte max. 5 Versuche pro Minute pro IP.
- Keine nutzbaren Fehlermeldungen bei Login-Fehlern ("E-Mail oder Passwort falsch", nicht "E-Mail existiert nicht").

### A09 – Security Logging & Monitoring

- Erfolgreiche und fehlgeschlagene Authentifizierungsversuche loggen.
- Zugriffe auf andere Nutzerdaten (403-Fehler) als Security-Event loggen.
- PII niemals in Logs schreiben (siehe oben).

### A10 – SSRF (Server-Side Request Forgery)

- Webhook-URLs und externe URLs validieren: Kein Zugriff auf `169.254.0.0/16` (AWS Metadata), `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`.
- HTTP-Timeout für externe Calls: max. 30 Sekunden.
- Erlaubte Domains für Connector-Oauth-Callbacks in Allowlist verwalten.

---

## OAuth-Konnektoren – Sicherheits-Checkliste

- [ ] PKCE (Proof Key for Code Exchange) für alle OAuth-2.0-Flows implementieren.
- [ ] State-Parameter mit `secrets.token_urlsafe(32)` generieren und validieren.
- [ ] Refresh-Token verschlüsselt in DB speichern (nicht im Klartext).
- [ ] Token-Rotation: Bei jedem Refresh alten Token invalidieren.
- [ ] Scope-Minimierung: Nur die minimalen Berechtigungen anfordern.
- [ ] Connector deaktivieren bei mehreren aufeinanderfolgenden 401-Fehlern.
