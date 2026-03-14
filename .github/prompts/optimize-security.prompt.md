---
agent: agent
description: "Tiefenoptimierung der Sicherheit und DSGVO-Compliance im PWBS-Workspace. Führt einen vollständigen Sicherheitsaudit durch – OWASP Top 10, Datenschutz, Verschlüsselung, Zugriffskontrolle – zustandsunabhängig bei jeder Ausführung."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Sicherheits- und DSGVO-Optimierung

> **Fundamentalprinzip: Zustandslose Frische**
>
> Sicherheit ist nie „fertig". Bei jeder Ausführung den gesamten Security-Posture von Null analysieren. Keine Annahmen über vorherige Audits. Jede Zeile Code ist ein potenzieller Angriffsvektor, bis das Gegenteil bewiesen ist.

> **Robustheitsregeln:**
>
> - Analysiere nur vorhandenen Code – melde fehlende Sicherheitsmechanismen als Gap, nicht als Bug.
> - Unterscheide zwischen „nicht implementiert" (Aufbaupotenzial) und „falsch implementiert" (Sicherheitslücke).
> - Berücksichtige den MVP-Kontext: Nicht jedes Enterprise-Feature ist jetzt nötig, aber die Grundlagen müssen stimmen.

---

## Phase 0: Threat Model (Extended Thinking)

Bevor du Code analysierst, erstelle ein aktuelles Bedrohungsmodell:

### 0.1 Angriffsflächen inventarisieren

```
Externe Angriffsflächen:
  ├── API-Endpunkte (FastAPI) → Authentifizierung, Autorisierung, Input-Validierung
  ├── OAuth-Callbacks → Token-Diebstahl, CSRF, Open Redirect
  ├── Webhook-Empfänger → Payload-Manipulation, Replay-Attacks
  ├── Frontend → XSS, CSRF, ClickJacking
  └── LLM-Integration → Prompt Injection, Data Exfiltration

Interne Angriffsflächen:
  ├── Datenbank-Zugriff → SQL Injection, Privilege Escalation
  ├── Dateisystem → Path Traversal (Obsidian Connector)
  ├── Inter-Service-Kommunikation → im MVP: Python-intern (niedrig)
  └── Secrets-Management → Umgebungsvariablen, .env-Dateien
```

### 0.2 Akteure und Motivationen

| Akteur                   | Motivation           | Fähigkeiten                  | Hauptziele                   |
| ------------------------ | -------------------- | ---------------------------- | ---------------------------- |
| Externer Angreifer       | Datendiebstahl       | Web-Angriffe, API-Missbrauch | Nutzerdaten, OAuth-Tokens    |
| Authentifizierter Nutzer | Cross-Tenant-Zugriff | API-Manipulation             | Fremde Daten einsehen        |
| Malicious OAuth App      | Token-Ernte          | OAuth-Flow-Manipulation      | Zugangs-Tokens               |
| LLM Prompt Injection     | Datenexfiltration    | Manipulierte Inhalte         | System-Prompts, fremde Daten |

---

## Phase 1: DSGVO-Compliance Deep Scan

### 1.1 owner_id-Audit (KRITISCH)

Durchsuche **jede** Datenbankabfrage und Datenzugriffe:

- [ ] Jede PostgreSQL-Query mit User-Bezug: `WHERE owner_id = :user_id` vorhanden
- [ ] Jede Weaviate-Abfrage: Filter auf `owner_id` gesetzt
- [ ] Jede Neo4j-Cypher-Query: `WHERE n.owner_id = $owner_id` vorhanden
- [ ] Kein Endpunkt kann Daten ohne Authentifizierung zurückgeben
- [ ] Keine API-Antwort enthält `owner_id` eines anderen Nutzers

**Suche explizit nach:**

```python
# GEFÄHRLICH – fehlender owner_id-Filter:
session.query(Document).filter_by(id=doc_id)  # ← owner_id fehlt!
# KORREKT:
session.query(Document).filter_by(id=doc_id, owner_id=user_id)
```

### 1.2 expires_at-Audit

- [ ] Jedes nutzerbezogene Datenmodell hat `expires_at: datetime | None`
- [ ] Default-Wert für `expires_at` ist gesetzt (z.B. + 2 Jahre)
- [ ] Cleanup-Job existiert, der abgelaufene Daten löscht
- [ ] Löschung kaskadiert über alle Storage-Layer (PostgreSQL → Weaviate → Neo4j)

### 1.3 Recht auf Löschung (Art. 17 DSGVO)

- [ ] DELETE-Endpunkt existiert für Nutzer-Account
- [ ] Löschung entfernt ALLE nutzerbezogenen Daten aus ALLEN Speichern
- [ ] Löschung ist verifizierbar (Audit-Log ohne PII)
- [ ] OAuth-Tokens werden bei Nutzer-Löschung revoked

### 1.4 Datenminimierung

- [ ] Keine unnötigen Felder in Datenmodellen
- [ ] Externe Daten werden auf das Minimum normalisiert
- [ ] Rohdaten werden nach Processing nicht unbegrenzt gespeichert
- [ ] Logs enthalten keine PII (nur IDs, Metadaten, Fehlertypen)

### 1.5 PII-Scanning

Durchsuche Code nach potenzieller PII in Logs:

```python
# SUCHE NACH:
logger.info(f"User {email}")           # ← PII!
logger.debug(f"Content: {content}")     # ← Potenziell PII!
logger.error(f"Token: {token}")         # ← Secret!
print(user_data)                        # ← PII in stdout!
```

---

## Phase 2: OWASP Top 10 Audit

### A01 – Broken Access Control

- [ ] Authentifizierung auf allen geschützten Endpunkten
- [ ] Autorisierung: Nutzer kann nur eigene Ressourcen zugreifen
- [ ] `user_id` wird aus JWT extrahiert, NIEMALS aus Request-Body/Query
- [ ] Admin-Endpunkte mit separater Rolle geschützt
- [ ] Rate Limiting auf allen öffentlichen Endpunkten

### A02 – Cryptographic Failures

- [ ] Passwörter: `argon2` oder `bcrypt` (NICHT md5, sha256)
- [ ] API-Keys: `secrets.token_urlsafe(32)` (mindestens 32 Bytes Entropie)
- [ ] OAuth-Tokens: Verschlüsselt in DB (`Fernet` oder AES-256-GCM)
- [ ] TLS 1.3 für alle externen Verbindungen konfiguriert
- [ ] Keine Secrets in Quellcode oder Logs
- [ ] Envelope Encryption laut `docs/encryption-strategy.md`

### A03 – Injection

- [ ] SQL: Parametrisierte Queries (SQLAlchemy ORM oder asyncpg $params)
- [ ] Neo4j: Parameter-Übergabe (`$param`), kein String-Formatting in Cypher
- [ ] XSS: Alle User-Inputs im Frontend sanitized
- [ ] Command Injection: Kein `os.system()`, `subprocess.run(shell=True)`
- [ ] LLM Prompt Injection: User-Content in separatem Block, System-Prompt geschützt

### A05 – Security Misconfiguration

- [ ] Debug-Modus deaktiviert in Production
- [ ] CORS: Explizite Allowlist, kein `*`
- [ ] Security Headers: `X-Content-Type-Options`, `X-Frame-Options`, CSP
- [ ] Keine Default-Credentials in config
- [ ] `.env` in `.gitignore`
- [ ] Docker: Non-Root-User, Security Updates

### A07 – Identification & Authentication

- [ ] JWT: RS256 oder EdDSA (NICHT HS256 mit schwachem Secret)
- [ ] Access Token: Kurze Gültigkeit (≤ 15 Min)
- [ ] Refresh Token: Längere Gültigkeit (≤ 30 Tage), verschlüsselt gespeichert
- [ ] Token-Rotation: Refresh Token bei Nutzung erneuert
- [ ] Rate Limiting: ≤ 5 Login-Versuche/Minute
- [ ] Keine nutzbaren Fehlermeldungen („User not found" vs. „Invalid credentials")

### A10 – SSRF (Server-Side Request Forgery)

- [ ] Webhook-URLs: Validierung gegen private IP-Bereiche
- [ ] Blockierte Ranges: `169.254.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`
- [ ] Timeout: 30s für alle externen Requests
- [ ] Kein offener Redirect in OAuth-Flow

---

## Phase 3: OAuth-Sicherheit

### 3.1 OAuth Flow

- [ ] Authorization Code Flow mit PKCE (NICHT Implicit Flow)
- [ ] State-Parameter: Kryptographisch zufällig, einmalig, validiert
- [ ] Redirect-URI: Exakt registriert, keine Wildcards
- [ ] Scope-Minimierung: Nur benötigte Permissions anfragen

### 3.2 Token-Management

- [ ] Refresh-Tokens: Verschlüsselt gespeichert (Fernet)
- [ ] Token-Rotation: Neuer Refresh-Token bei jedem Einsatz
- [ ] Token-Revocation: Implementiert für Logout und Account-Deletion
- [ ] Fehlerbehandlung: `401` bei abgelaufenem Token → automatischer Refresh

---

## Phase 4: LLM-Sicherheit

### 4.1 Prompt Injection

- [ ] User-Content NICHT direkt in System-Prompts eingebettet
- [ ] Strukturierte Trennung: System-Prompt → Context → User-Query
- [ ] Output-Validierung: LLM-Antworten gegen Schema validiert
- [ ] Kein Zugriff auf System-Interna in LLM-Responses

### 4.2 Daten-Exfiltration

- [ ] Keine Cross-User-Daten im LLM-Kontext
- [ ] LLM-Input enthält nur Daten des anfragenden Users
- [ ] Keine Nutzerdaten für LLM-Training (API-Parameter prüfen)

---

## Phase 5: Abhängigkeits-Sicherheit

- [ ] Keine bekannten CVEs in Dependencies (`pip audit`, `npm audit`)
- [ ] `python-jose` mit `cryptography`-Backend (nicht `pycryptodome`)
- [ ] Alle Dependencies gepinnt auf sichere Mindestversionen
- [ ] Docker Base Images: aktuelle Versionen, keine `latest`-Tags

---

## Phase 6: Sicherheitsbericht und Fixes

### 6.1 Findings-Klassifizierung

| #   | Kategorie | Finding | Schwere                                        | CVSS-ähnlich | Fix |
| --- | --------- | ------- | ---------------------------------------------- | ------------ | --- |
| 1   | ...       | ...     | 🔴 Kritisch / 🟡 Hoch / 🟠 Mittel / 🟢 Niedrig | ...          | ... |

### 6.2 Sofort-Fixes

Für jedes 🔴-Finding: Implementiere den Fix sofort und vollständig.

### 6.3 Sicherheits-Empfehlungen

```markdown
# Sicherheitsbericht – [Datum]

## Kritische Findings (sofort beheben)

...

## Hohe Findings (nächster Sprint)

...

## Mittlere Findings (Backlog)

...

## Aufbaupotenzial (noch zu implementieren)

...

## Security-KPIs

- owner_id-Coverage: ...%
- expires_at-Coverage: ...%
- Parametrisierte Queries: ...%
- Verschlüsselte Secrets: ...%
```

---

## Opus 4.6 – Kognitive Verstärker

- **Adversarisches Denken:** Spiele bei jedem Feature den Angreifer – wie würdest du es ausnutzen?
- **Kausale Kettenanalyse:** Verfolge jeden Datenfluss von Input bis Storage – wo könnten Lecks entstehen?
- **Blinde-Flecken-Suche:** Welche Sicherheitsaspekte werden in den Instructions/Prompts NICHT erwähnt? Genau dort suchen.
- **Regulatorische Vorausschau:** Welche DSGVO-Anforderungen werden in Phase 3/4 relevant, für die jetzt Grundlagen fehlen?
