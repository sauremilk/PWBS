---
agent: agent
description: Implementiert einen neuen Datenquellen-Konnektor für das PWBS. Erstellt alle notwendigen Dateien, Migrations und Tests.
tools:
  - codebase
  - editFiles
  - runCommands
---

# Neuen Konnektor erstellen

> **Robustheitsregeln:**
>
> - Prüfe vor jedem Dateizugriff, ob die Datei/das Verzeichnis existiert. Erstelle fehlende Verzeichnisse nach Bedarf.
> - Verwende plattformgerechte Shell-Befehle. Alle Shell-Beispiele sind Pseudo-Code.
> - Falls `BaseConnector`, `registry.py` oder `types.py` noch nicht existieren: erstelle die benötigte Basisstruktur oder dokumentiere die fehlende Abhängigkeit.
> - Leite den Konnektor-Verzeichnisnamen aus dem Datenquellen-Namen ab (Kleinbuchstaben, Sonderzeichen durch Unterstriche ersetzen, z.B. "Google Calendar" → `google_calendar`).

Erstelle einen vollständigen, produktionsreifen Konnektor für die folgende Datenquelle:

**Datenquelle:** ${input:source_name:Name der Datenquelle, z.B. "Notion", "Gmail", "Slack"}
**Source-ID-Format:** ${input:source_id_format:Format der Quell-IDs, z.B. "uuid", "email_id", "page_id"}
**Auth-Typ:** ${input:auth_type:Authentifizierungstyp: "oauth2", "api_key", "webhook"}

## Phase 0: Voranalyse (Extended Thinking)

Vor der Implementierung:

1. **API-Charakteristik analysieren:** Pagination-Modell (cursor/offset/token), Rate-Limit-Verhalten, Webhook vs. Poll.
2. **Normalisierungskomplexität:** Welche Felder der API lassen sich sauber auf UDF-Felder mappen? Welche sind mehrdeutig?
3. **Idempotenz-Strategie festlegen:** Was ist der stabile, eindeutige Identifier für Dokumente dieser Quelle?
4. **DSGVO-Check:** Welche API-Felder enthalten PII? Gibt es Felder, die _nicht_ gespeichert werden sollen?

### 1. Konnektor-Klasse erstellen

Erstelle `pwbs/connectors/<source_lower>/<source_lower>_connector.py` (wobei `<source_lower>` der Datenquellen-Name in Kleinbuchstaben ist, z.B. `notion`, `gmail`, `google_calendar`):

- Erbt von `BaseConnector`
- Implementiert `fetch_since(cursor: str | None) -> SyncResult`
- Implementiert `normalize(raw: dict) -> UnifiedDocument`
- Cursor-basierte Pagination implementieren
- OAuth-Token-Refresh aus `TokenManager` nutzen
- Exponential Backoff für Rate-Limits (429, 503)
- Vollständige Type Annotations

### 2. Pydantic-Datenmodelle

Erstelle `pwbs/connectors/<source_lower>/models.py`:

- `<SourceName>RawDocument` für API-Rohformat (z.B. `NotionRawDocument`)
- `<SourceName>ConnectorConfig` mit Pydantic v2 (z.B. `NotionConnectorConfig`)
- Alle Felder mit Types und Validators

### 3. Connector registrieren

1. **Prüfe ob `pwbs/connectors/registry.py` existiert.** Falls ja: Konnektor in `CONNECTOR_MAP` eintragen. Falls nein: erstelle die Registry-Datei mit dem neuen Konnektor als erstem Eintrag.
2. **Prüfe ob `pwbs/core/types.py` existiert.** Falls ja: `SourceType`-Enum erweitern. Falls nein: erstelle die Datei mit dem `SourceType`-Enum.

### 4. Alembic-Migration

1. **Prüfe ob Alembic konfiguriert ist:** Suche nach `alembic.ini` oder `alembic/` im `backend/`-Verzeichnis. Falls nicht vorhanden: überspringe diesen Schritt und dokumentiere, dass die Migration manuell erstellt werden muss.
2. Falls vorhanden, erstelle die Migration:
   ```
   cd backend
   alembic revision --autogenerate -m "add_<source_lower>_connector_state"
   ```

### 5. Tests schreiben

Erstelle `tests/unit/connectors/test_<source_lower>_connector.py` (z.B. `test_notion_connector.py`):

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
