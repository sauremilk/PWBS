---
agent: agent
description: Implementiert einen neuen Datenquellen-Konnektor für das PWBS. Erstellt alle notwendigen Dateien, Migrations und Tests.
tools:
  - codebase
  - editFiles
  - runCommands
---

# Neuen Konnektor erstellen

Erstelle einen vollständigen, produktionsreifen Konnektor für die folgende Datenquelle:

**Datenquelle:** ${input:source_name:Name der Datenquelle, z.B. "Notion", "Gmail", "Slack"}
**Source-ID-Format:** ${input:source_id_format:Format der Quell-IDs, z.B. "uuid", "email_id", "page_id"}
**Auth-Typ:** ${input:auth_type:Authentifizierungstyp: "oauth2", "api_key", "webhook"}

## Aufgaben

### 1. Konnektor-Klasse erstellen

Erstelle `pwbs/connectors/${input:source_name:source_name|lower}/${input:source_name:source_name|lower}_connector.py`:

- Erbt von `BaseConnector`
- Implementiert `fetch_since(cursor: str | None) -> SyncResult`
- Implementiert `normalize(raw: dict) -> UnifiedDocument`
- Cursor-basierte Pagination implementieren
- OAuth-Token-Refresh aus `TokenManager` nutzen
- Exponential Backoff für Rate-Limits (429, 503)
- Vollständige Type Annotations

### 2. Pydantic-Datenmodelle

Erstelle `pwbs/connectors/${input:source_name:source_name|lower}/models.py`:

- `${input:source_name:source_name}RawDocument` für API-Rohformat
- `${input:source_name:source_name}ConnectorConfig` mit Pydantic v2
- Alle Felder mit Types und Validators

### 3. Connector registrieren

Aktualisiere `pwbs/connectors/registry.py`:

- Konnektor in `CONNECTOR_MAP` eintragen
- `SourceType`-Enum in `pwbs/core/types.py` erweitern

### 4. Alembic-Migration

Erstelle Migration für Connector-Zustandstabelle:

```
alembic revision --autogenerate -m "add_${input:source_name:source_name|lower}_connector_state"
```

### 5. Tests schreiben

Erstelle `tests/unit/connectors/test_${input:source_name:source_name|lower}_connector.py`:

- Test für `fetch_since()` mit gemockten API-Responses
- Test für `normalize()` mit Beispiel-Rohdaten
- Test für Idempotenz: Zweifaches Ingestieren erzeugt keine Duplikate
- Test für Cursor-Persistierung
- Test für Rate-Limit-Handling

### Checkliste

- [ ] Keine Secrets im Code (API-Keys über Env-Vars)
- [ ] `owner_id` in jedem normalisierten Dokument gesetzt
- [ ] `expires_at` gesetzt (DSGVO)
- [ ] Idempotenz: Hash aus `source_id` + `owner_id` als Dedup-Schlüssel
- [ ] Fehlerbehandlung mit `ConnectorError`
- [ ] Logging ohne PII
