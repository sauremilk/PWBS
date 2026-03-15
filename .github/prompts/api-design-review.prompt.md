---
agent: agent
description: "Tiefenaudit der API-Design-Qualität im PWBS-Workspace. Prüft REST-Konventionen, Fehlerformate, Versionierung, Paginierung, Rate-Limiting, OpenAPI-Spec und Schema-Konsistenz zwischen Backend und Frontend – zustandsunabhängig bei jeder Ausführung."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# API-Design-Review

> **Fundamentalprinzip: Zustandslose Frische**
>
> API-Oberflächen verändern sich mit jedem Feature. Bei jeder Ausführung alle API-Endpunkte, Schemas und Konventionen von Grund auf analysieren. Keine Annahmen über vorherige Reviews.

> **Robustheitsregeln:**
>
> - Prüfe, welche API-Endpunkte tatsächlich existiert. Nicht nach Idealzustand bewerten, sondern nach aktuellem MVP-Stand.
> - Fehlende aber nicht geplante Features sind Empfehlungen, keine Fehler.
> - Berücksichtige DSGVO-Anforderungen an API-Antworten (keine PII in Fehler-Details, owner_id-Filterung).
> - Plattformgerechte Befehle verwenden.

---

## Phase 0: API-Inventar (Extended Thinking)

### 0.1 Endpunkt-Katalog

Durchsuche alle FastAPI-Router und erstelle eine vollständige Endpunkt-Liste:

| Methode | Pfad | Router-Datei | Auth? | Response-Model | Beschreibung |
|---------|------|-------------|-------|----------------|-------------|
| GET | `/api/...` | ... | ... | ... | ... |
| POST | `/api/...` | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... |

### 0.2 Pydantic-Schema-Inventar

| Schema | Datei | Verwendet in | Felder | Validatoren |
|--------|-------|-------------|--------|-------------|
| ... | ... | ... | ... | ... |

### 0.3 OpenAPI-Spec-Status

- [ ] OpenAPI-Spec generiert und zugänglich (`/docs`, `/openapi.json`)
- [ ] Spec-Version und Beschreibungsqualität
- [ ] Beispielwerte in Schemas vorhanden

---

## Phase 1: REST-Konventionen

### 1.1 URL-Design

- [ ] **Konsistente Namensgebung:** Plural-Substantive für Collections (`/connectors`, nicht `/connector`)
- [ ] **Hierarchische Ressourcen:** Korrekte Verschachtelung (`/connectors/{id}/sync`, nicht `/sync-connector/{id}`)
- [ ] **Keine Verben in URLs:** Aktionen über HTTP-Methoden, nicht URL-Verben (Ausnahme: Custom Actions wie `/sync`)
- [ ] **Kebab-Case:** URL-Segmente in kebab-case, nicht snake_case oder camelCase
- [ ] **Konsistente Trailing Slashes:** Einheitlich mit oder ohne `/` am Ende

### 1.2 HTTP-Methoden

| Operation | Methode | Idempotent? | Erwarteter Status |
|-----------|---------|------------|-------------------|
| Liste abrufen | GET | Ja | 200 |
| Einzelressource | GET | Ja | 200 / 404 |
| Erstellen | POST | Nein* | 201 |
| Vollständig aktualisieren | PUT | Ja | 200 |
| Teilweise aktualisieren | PATCH | Nein | 200 |
| Löschen | DELETE | Ja | 204 / 404 |

\* POST-Endpunkte mit idempotency_key sind Ausnahme.

- [ ] Korrekte Methoden-Zuordnung für alle Endpunkte
- [ ] Status-Codes entsprechen der Operation
- [ ] OPTIONS/HEAD wo nötig implementiert

### 1.3 Query-Parameter

- [ ] **Filterung:** Konsistentes Muster (`?source=notion&status=active`)
- [ ] **Sortierung:** `?sort=created_at&order=desc`
- [ ] **Feld-Selektion (optional):** `?fields=id,title,created_at`

---

## Phase 2: Fehlerbehandlung

### 2.1 Error-Response-Format

Prüfe, ob alle Fehler einem einheitlichen Format folgen:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Connector with ID '...' not found",
    "details": {},
    "request_id": "req_abc123"
  }
}
```

- [ ] **Einheitliches Format:** Alle Endpunkte verwenden dasselbe Error-Schema
- [ ] **Maschinenlesbare Codes:** `error.code` ist ein stabiler String-Enum, kein Freitext
- [ ] **Keine PII in Fehlern:** Fehlermeldungen enthalten keine Nutzerdaten, Tokens oder interne Pfade
- [ ] **Keine Stack-Traces in Production:** `detail` enthält in Produktion keine Python-Tracebacks
- [ ] **Request-ID in Fehlern:** Jeder Fehler enthält eine korrelierbare Request-ID

### 2.2 Fehler-Klassifikation

| HTTP-Status | Verwendung | PWBSError-Subklasse |
|-------------|-----------|---------------------|
| 400 | Validierungsfehler (Pydantic) | `ValidationError` |
| 401 | Fehlende/ungültige Authentifizierung | `AuthenticationError` |
| 403 | Fehlende Berechtigung (owner_id Mismatch) | `AuthorizationError` |
| 404 | Ressource nicht gefunden | `NotFoundError` |
| 409 | Konflikt (Duplikat, veralteter State) | `ConflictError` |
| 422 | Semantischer Fehler (valide Syntax, ungültige Logik) | `UnprocessableError` |
| 429 | Rate Limit erreicht | `RateLimitError` |
| 500 | Interner Fehler | `InternalError` |
| 503 | Abhängigkeit nicht verfügbar | `ServiceUnavailableError` |

- [ ] Alle Fehler verwenden korrekte HTTP-Status-Codes
- [ ] Eigene Exception-Klassen von `PWBSError` abgeleitet
- [ ] Exception-Handler in FastAPI registriert

### 2.3 Validierungsfehler

- [ ] Pydantic-Validierungsfehler werden als 422 mit Feld-Details zurückgegeben
- [ ] Fehlermeldungen sind für Frontend-Anzeige geeignet (lokalisierbar, verständlich)
- [ ] Batch-Validierung: Alle Fehler auf einmal zurückgeben, nicht beim ersten abbrechen

---

## Phase 3: Paginierung

### 3.1 Paginierungs-Strategie

- [ ] **Konsistentes Paginierungs-Pattern** über alle Listen-Endpunkte:

```json
{
  "items": [...],
  "pagination": {
    "total": 142,
    "page": 1,
    "page_size": 20,
    "has_next": true,
    "next_cursor": "eyJpZCI6..."
  }
}
```

- [ ] **Default-Limits:** Sinnvolle Defaults (z.B. 20) und Maximum (z.B. 100)
- [ ] **Cursor-basiert:** Für große Collections Cursor-basierte Paginierung statt Offset
- [ ] **Stabile Sortierung:** Paginierung funktioniert auch bei gleichzeitigen Inserts

### 3.2 Response-Envelope

- [ ] Konsistente Envelope-Struktur für Listen vs. Einzelressourcen
- [ ] Metadaten (total, page, limits) in allen Listen-Antworten

---

## Phase 4: Authentifizierung und Autorisierung

### 4.1 Auth-Konsistenz

- [ ] **Alle Endpunkte geschützt:** Kein Endpunkt ohne Auth-Dependency (außer `/health`, `/docs`)
- [ ] **JWT-Validierung:** Token-Signatur, Expiry und Claims geprüft
- [ ] **owner_id-Extraktion:** Aus JWT konsistent in allen Routen → DB-Filter
- [ ] **Keine Cross-Tenant-Zugriffe:** Kein Endpunkt gibt Daten ohne owner_id-Filter zurück

### 4.2 Rate-Limiting

- [ ] Rate-Limiting auf allen öffentlichen Endpunkten
- [ ] Differenzierte Limits (z.B. Search: 30/min, LLM-basiert: 10/min)
- [ ] Standard-Header: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- [ ] 429-Response mit Retry-After-Header

---

## Phase 5: Schema-Konsistenz (Backend ↔ Frontend)

### 5.1 Pydantic ↔ TypeScript Alignment

Für jedes Pydantic-Response-Model prüfen:

- [ ] **Feld-Namen:** snake_case (Backend) korrekt zu camelCase (Frontend) konvertiert oder einheitlich
- [ ] **Typen:** `datetime` → ISO-8601-String, `UUID` → String, `Decimal` → Number/String
- [ ] **Optionale Felder:** `| None` im Backend → `?` oder `| null` im Frontend
- [ ] **Enums:** Backend-StringEnum und Frontend-TypeScript-Enum synchron

### 5.2 Breaking-Change-Erkennung

- [ ] Versionierung geplant oder implementiert (URL-Prefix `/api/v1/` oder Header)
- [ ] Abwärtskompatible Änderungen bevorzugt (neue Felder optional hinzufügen)
- [ ] Deprecation-Strategie für alte Felder/Endpunkte

---

## Phase 6: OpenAPI-Qualität

### 6.1 Spec-Vollständigkeit

- [ ] Alle Endpunkte in OpenAPI-Spec enthalten
- [ ] Response-Schemas für alle Status-Codes (200, 400, 401, 404, 422, 500)
- [ ] Beschreibungen für alle Endpunkte und Parameter
- [ ] Beispielwerte (`example`) in Schemas

### 6.2 Generierung und Nutzbarkeit

- [ ] Frontend-Client aus OpenAPI-Spec generierbar (`openapi-typescript`, `orval`)
- [ ] Spec ist valide (OpenAPI 3.0/3.1 konform)
- [ ] Tags und Gruppierung sinnvoll für Dokumentation

---

## Phase 7: Optimierungen implementieren

Für jedes Finding:

1. **Bewerte:** Sicherheit > Korrektheit > Konsistenz > DX (Developer Experience)
2. **Priorisiere:** Auth-Lücken und PII-Leaks zuerst, dann Konventionsverletzungen
3. **Implementiere:** Vollständige Fixes, keine Platzhalter
4. **Validiere:** `problems`-Tool verwenden, Server starten, OpenAPI-Spec prüfen

---

## Phase 8: API-Design-Bericht

```markdown
# API-Design-Review – [Datum]

## Endpunkt-Übersicht

- Gesamtzahl Endpunkte: N
- Davon auth-geschützt: N
- Davon mit Rate-Limiting: N

## Design-Reifegrad

| Aspekt | Score (1-5) | Nächster Schritt |
|--------|-------------|-----------------|
| REST-Konventionen | ... | ... |
| Fehlerbehandlung | ... | ... |
| Paginierung | ... | ... |
| Auth/Rate-Limiting | ... | ... |
| Schema-Konsistenz | ... | ... |
| OpenAPI-Qualität | ... | ... |

## Durchgeführte Verbesserungen

1. ...

## Empfehlungen

1. ...
```

---

## Opus 4.6 – Kognitive Verstärker

- **Perspektiven-Wechsel:** Bewerte die API aus Sicht des Frontend-Entwicklers (DX), des Sicherheits-Auditors (Auth, PII), des API-Consumers (Konsistenz, Dokumentation) und des Ops-Teams (Debugging, Monitoring).
- **Kausalketten:** Verfolge den Pfad einer Anfrage von Frontend-Komponente durch API-Route, Auth-Middleware, Business-Logik, DB-Query bis zur Response – wo gehen Informationen verloren oder werden inkonsistent?
- **Muster-Erkennung:** Identifiziere systematische Inkonsistenzen – werden bestimmte Patterns (Error-Handling, Paginierung, Auth) in einigen Routen anders gehandhabt als in anderen?
- **Zukunftsprojektion:** Welche API-Design-Entscheidungen werden beim Übergang zu Phase 3 (Service-Split, öffentliche API) problematisch?
