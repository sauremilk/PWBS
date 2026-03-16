# ADR-016: MVP-Fokussierung – 5-Schritte-Refactoring

**Status:** Akzeptiert
**Datum:** 2026-03-15
**Autoren:** Copilot-gestütztes Refactoring

## Kontext

Das PWBS-Backend enthielt 36+ Module, von denen viele für das MVP (Phase 2, 10–20 Early Adopters) nicht benötigt werden. Die Komplexitätskosten durch Teams/RBAC/Billing/Marketplace/SSO/Developer-Module sowie 8 Konnektoren übersteigen den Nutzen für die Phase-2-Zielgruppe deutlich.

**Ziel:** Maximale Reduktion der aktiven Codebasis ohne Datenverlust oder Breaking Changes.

## Entscheidung

5-Schritte-Strategie mit konservativer Herangehensweise (kommentieren statt löschen):

### Schritt 1: Out-of-Scope Module deaktivieren

**Betroffene Module:** billing, teams, rbac, marketplace, developer, sso

**Maßnahmen:**
- Modul-Dateien nach `_deferred/` kopiert (Origale bleiben für Alembic-Import-Integrität)
- 9 Router-Imports + `include_router`-Aufrufe in `main.py` auskommentiert mit `# DEFERRED: Phase 3`
- Webhooks-Router deaktiviert (Gmail Pub/Sub + Slack Events)
- `_deferred/README.md` mit vollständiger Reaktivierungsanleitung erstellt

**Bewusste Entscheidung:** `models/__init__.py` behält ALLE 32 ORM-Imports (Alembic Discovery). `schemas/enums.py` bleibt komplett (keine Breaking Changes in Serialisierung).

### Schritt 2: Phase-3 Konnektoren deaktivieren

**Aktive Kern-4:** Google Calendar, Notion, Zoom, Obsidian
**Deaktiviert:** Gmail, Slack, Outlook, Google Docs

**Maßnahmen:**
- Konnektor-Dateien nach `_deferred/connectors/` verschoben
- `integrations/slack/` nach `_deferred/integrations/slack/` verschoben
- Test-Dateien nach `_deferred/tests/` verschoben
- In `connectors.py` Route: Phase-3-Einträge in 6+ Dictionaries auskommentiert (`_CONNECTOR_META`, `_AUTH_URLS`, `_SCOPES`, `redirect_uri_map`, `client_id_map`, `client_secret_map`, `token_endpoints`)

### Schritt 3: Feature Flags – Beibehalten

**Analyse-Ergebnis:** Feature-Flags-Service ist bereits MVP-tauglich:
- ENV-Override (`FEATURE_FLAGS_OVERRIDE`) als höchste Priorität implementiert
- Kein Business-Logik-Code nutzt Feature Flags
- Service ist opt-in, kein Overhead

**Entscheidung:** Keine Änderung nötig.

### Schritt 4: Vertikale Profile – Beibehalten

**Analyse-Ergebnis:** Default-Profil "general" ist aktiv:
- Kein Supplement, keine Speziallogik
- `entity_priorities`/`ner_focus` definiert aber nirgends implementiert
- Dormante Konfiguration kostet nichts

**Entscheidung:** Keine Änderung nötig.

### Schritt 5: Datenbank-Architektur – Neo4j optional

**Problem:** App crashte wenn Neo4j nicht erreichbar (SinglePointOfFailure).
**Analyse:** GraphBuilder wird NIE in der Pipeline aufgerufen – kein User-Daten-Write nach Neo4j.

**Maßnahmen:**
- `neo4j_client.py`: `get_neo4j_driver()` gibt `AsyncDriver | None` zurück; `_init_failed`-Flag für Short-Circuit
- `main.py` lifespan: Neo4j-Init mit None-Check + Warning-Log
- `docker-compose.yml`: Neo4j hinter `profiles: ["graph"]` (aktivierbar mit `--profile graph`)
- Bestehende Fallbacks bestätigt: `NullGraphService` in Briefing, try/except in Knowledge-API

## Geänderte Dateien

| Datei | Änderung |
| --- | --- |
| `pwbs/api/main.py` | 9 Router deaktiviert, Neo4j-Startup optional |
| `pwbs/api/v1/routes/connectors.py` | Phase-3-Einträge in 6+ Dictionaries kommentiert |
| `pwbs/db/neo4j_client.py` | Gibt None zurück bei Fehler, _init_failed-Flag |
| `docker-compose.yml` | Neo4j hinter `profiles: ["graph"]` |
| `_deferred/README.md` | Dokumentation mit Reaktivierungsanleitung |
| `CHANGELOG.md` | Alle 5 Schritte dokumentiert |

## Nicht-Geänderte Dateien (bewusst)

| Datei | Grund |
| --- | --- |
| `models/__init__.py` | Alle 32 ORM-Imports bleiben für Alembic |
| `schemas/enums.py` | SourceType/EntityType komplett für Serialisierungskompatibilität |
| `api_key_auth.py` | Imports aus developer-Modul (existiert noch am Original-Ort) |

## Konsequenzen

**Positiv:**
- Reduzierte aktive Codebasis: ~6 Module + 4 Konnektoren weniger aktiv
- App startet ohne Neo4j (kein SPOF mehr)
- Docker-Setup leichtgewichtiger (nur PG + Weaviate + Redis benötigt)
- Alle Tests bestehen weiterhin

**Negativ:**
- Module existieren doppelt (`pwbs/` + `_deferred/`) für Alembic-Kompatibilität
- Kommentierte Code-Blöcke in `connectors.py` und `main.py`

**Risiken:**
- Bei Schema-Änderungen in deferred Models: Alembic sieht weiterhin die originalen Model-Dateien
- `api_key_auth.py` hängt vom developer-Modul ab (muss bei Löschung inlined werden)

## Reaktivierung

Vollständige Anleitung in `_deferred/README.md`. Zusammenfassung:
1. Dateien zurückverschieben
2. Router-Imports in `main.py` entkommentieren
3. Connector-Einträge in `connectors.py` entkommentieren
4. Tests zurückverschieben und ausführen
