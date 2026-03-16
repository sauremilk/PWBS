# Test-Optimierungsbericht – PWBS Backend

**Datum:** 2026-03-15
**Scope:** Phase 0–6 gemäß `optimize-testing.prompt.md`

---

## 1. Zusammenfassung

| Metrik                       | Vorher     | Nachher | Delta |
| ---------------------------- | ---------- | ------- | ----- |
| Gesammelte Tests             | 2.541      | 2.478\* | –63†  |
| Fehlgeschlagene Tests        | 33 + 1 Err | 0       | –34   |
| Übersprungene Tests          | ~57        | ~58     | +1†   |
| Neue Testdateien             | 0          | 4       | +4    |
| Neue Testfunktionen          | 0          | 62      | +62   |
| Behobene Quelldateien (Prod) | 0          | 2       | +2    |
| Behobene Testdateien         | 0          | 10      | +10   |

_\*Netto-Rückgang durch Deaktivierung der Slack-Bot-Tests (125 Tests → übersprungen), +62 neue Tests_
_†Slack-Bot-Tests werden via `pytest.importorskip` korrekt übersprungen statt mit ImportError abzubrechen_

---

## 2. Behobene Test-Fehler (34 Failures → 0)

### 2.1 Produktionsfehler entdeckt

| #   | Datei                      | Problem                                                                                                          | Fix                                                     |
| --- | -------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| 1   | `pwbs/api/main.py`         | `health_router` importiert aber nie registriert – `/health`-Endpunkt war in Produktion nicht erreichbar          | `application.include_router(health_router)` hinzugefügt |
| 2   | `pwbs/schemas/enums.py`    | `SourceType` fehlte `OCR` und `AUDIO_TRANSCRIPT` – Multimodal-Pipeline nutzte String-Literale ohne Enum-Einträge | Enum-Mitglieder hinzugefügt                             |
| 3   | `pwbs/queue/celery_app.py` | Multimodal-Tasks hatten keine Queue-Route → würden in Default-Queue landen                                       | `"pwbs.queue.tasks.multimodal.*"` Route hinzugefügt     |

### 2.2 Test-Synchronisierungsfehler

| #   | Bereich                                                                 | Anzahl | Ursache                                                                                                           | Fix                                                                                              |
| --- | ----------------------------------------------------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 1   | `test_auth/test_briefings_api.py`                                       | 4F     | `BriefingType` von 2→4 Werte erweitert; `submit_feedback` refactored (trigger_context → BriefingFeedback-Tabelle) | Side-Effects auf 4 erweitert; Assertions aktualisiert                                            |
| 2   | `test_auth/test_user_api.py`                                            | 5F     | Mock-User fehlte `timezone`, `language`, `briefing_auto_generate`, `reminder_frequency`                           | Fehlende Attribute zum Mock hinzugefügt                                                          |
| 3   | `test_vertical_profiles/`                                               | 10F    | Gleiche Mock-User-Felder fehlend                                                                                  | Gleicher Fix wie test_user_api                                                                   |
| 4   | `test_email/test_briefing_email.py`                                     | 1F     | `UserSettingsResponse` erfordert `vertical_profile`                                                               | Feld hinzugefügt                                                                                 |
| 5   | `unit/test_schemas_document.py`                                         | 1F     | `SourceType` von 5→11 Werte (inkl. OCR, AUDIO_TRANSCRIPT)                                                         | Expected-Set aktualisiert                                                                        |
| 6   | `unit/test_schemas_knowledge.py`                                        | 1F     | `EntityType` von 4→8 Werte                                                                                        | Expected-Set aktualisiert                                                                        |
| 7   | `test_dsgvo/test_export_service.py`                                     | 3F     | `_build_zip()` erwartet `llm_usage` Parameter; `run_export` hat zusätzlichen DB-Collector                         | Parameter + Mock-Side-Effect hinzugefügt; fehlende `with zipfile.ZipFile(...)` Zeile restauriert |
| 8   | `unit/test_app_factory.py` + `test_app_skeleton.py` + `test_openapi.py` | 4F     | Health-Route nicht registriert                                                                                    | Durch Produktionsfix in main.py behoben                                                          |
| 9   | `test_integrations/test_slack_bot.py`                                   | 1E     | Import von `pwbs.integrations.slack.bot` (in `_deferred/` verschoben)                                             | `pytest.importorskip` statt direktem Import                                                      |

### 2.3 Zusammenfassung der geänderten Dateien

**Produktionscode (3 Dateien):**

- `pwbs/api/main.py` – health_router-Registrierung
- `pwbs/schemas/enums.py` – OCR + AUDIO_TRANSCRIPT Enum-Werte
- `pwbs/queue/celery_app.py` – Multimodal Queue-Route

**Testcode (10 Dateien):**

- `tests/test_auth/test_briefings_api.py`
- `tests/test_auth/test_user_api.py`
- `tests/test_vertical_profiles/test_user_vertical_api.py`
- `tests/test_email/test_briefing_email.py`
- `tests/unit/test_schemas_document.py`
- `tests/unit/test_schemas_knowledge.py`
- `tests/test_dsgvo/test_export_service.py`
- `tests/unit/test_app_factory.py` (indirekt behoben)
- `tests/unit/test_app_skeleton.py` (indirekt behoben)
- `tests/test_integrations/test_slack_bot.py`

---

## 3. Neue Tests (62 Funktionen in 4 Dateien)

### 3.1 `tests/unit/test_auth_service.py` (20 Tests)

| Klasse                     | Tests | Abdeckung                                                           |
| -------------------------- | ----- | ------------------------------------------------------------------- |
| `TestHashToken`            | 3     | SHA-256 Determinismus, Unterschiedlichkeit, Hex-Format              |
| `TestCreateAccessToken`    | 3     | Rückgabewert, Roundtrip-Validierung, Eindeutigkeit                  |
| `TestValidateAccessToken`  | 3     | Ungültiger Token, abgelaufener Token, fehlendes `sub`               |
| `TestCreateRefreshToken`   | 3     | Plaintext-Rückgabe, Hash-Speicherung in DB, Custom Family-ID        |
| `TestValidateRefreshToken` | 4     | Gültiger Token, ungültig, widerrufen (Replay-Detection), abgelaufen |
| `TestRevokeRefreshToken`   | 1     | DB-Update-Ausführung                                                |
| `TestRevokeAllUserTokens`  | 1     | Rückgabe der widerrufenen Anzahl                                    |
| `TestCreateTokenPair`      | 1     | TokenPair-Struktur und Werte                                        |
| `TestRotateRefreshToken`   | 1     | Rotation: Alten widerrufen → Neues Paar erzeugen                    |

**Sicherheitsrelevanz:** Hoch – JWT-Erstellung, Token-Validierung, Replay-Detection, Hash-Speicherung

### 3.2 `tests/unit/test_middleware.py` (9 Tests)

| Klasse                | Tests | Abdeckung                                                       |
| --------------------- | ----- | --------------------------------------------------------------- |
| `TestSecurityHeaders` | 1     | Standard-Sicherheitsheader                                      |
| `TestGetClientIp`     | 3     | X-Forwarded-For, Client-IP, Fallback "unknown"                  |
| `TestClassifyRequest` | 5     | Auth-Login, Auth-Register, Sync-Endpoint, General mit/ohne User |

**Sicherheitsrelevanz:** Hoch – Rate-Limiting-Klassifizierung, IP-Extraktion aus Proxy-Headern

### 3.3 `tests/unit/test_db_clients.py` (18 Tests)

| Klasse               | Tests | Abdeckung                                                   |
| -------------------- | ----- | ----------------------------------------------------------- |
| `TestNeo4jClient`    | 6     | Init-Fehler → None, Short-Circuit, verfügbar, Health, Close |
| `TestRedisClient`    | 5     | Erstaufruf, Cache, Health True/False, Close                 |
| `TestWeaviateClient` | 4     | Erstaufruf, Health True/False, Close                        |
| `TestPostgresClient` | 3     | Engine-Erstellung, Cache, Dispose                           |

**Sicherheitsrelevanz:** Mittel – Singleton-Verhalten, Graceful Degradation bei Neo4j-Ausfall

### 3.4 `tests/unit/test_briefing_validation.py` (15 Tests)

| Klasse                  | Tests | Abdeckung                                                 |
| ----------------------- | ----- | --------------------------------------------------------- |
| `TestExtractReferences` | 4     | Single/Multiple, keine Refs, Whitespace                   |
| `TestFindBestMatch`     | 5     | Exact, Substring, Fuzzy, unter Threshold, leerer Titel    |
| `TestCleanText`         | 3     | Entfernung, Warnung, gültige Refs unberührt               |
| `TestValidate`          | 3     | Keine Refs, gültige Ref aufgelöst, ungültige Ref entfernt |

**Sicherheitsrelevanz:** Mittel – Verhindert Halluzinationen durch Quellenvalidierung (DSGVO-Erklärbarkeit)

---

## 4. Qualitätsanalyse (Phase 1 – Ergebnisse)

### Top-5 identifizierte Qualitätsprobleme

1. **Mock-Synchronisierung:** Tests verwenden MagicMock statt Factories → brechen bei Schemaänderungen (20+ Dateien betroffen)
2. **Assertion-Granularität:** Einige Tests prüfen nur Statuscode, nicht Response-Body-Struktur
3. **Fixture-Redundanz:** `_make_user()` wird in 3+ Dateien separat definiert statt in conftest.py
4. **Determinismus:** Zeitabhängige Tests nutzen `datetime.now()` statt eingefrorene Zeitstempel
5. **Missing Negative Tests:** Fehler-Pfade (DB-Fehler, LLM-Timeout) sind unterdurchschnittlich getestet

### Top-5 vorbildliche Patterns

1. **Conftest-Isolation:** Globale Fixtures mocken alle externen Dienste zuverlässig
2. **AAA-Pattern:** ~85% der Tests folgen Arrange-Act-Assert sauber
3. **Pytest-Marker:** Konsistente Nutzung von `@pytest.mark.asyncio`
4. **Parametrisierte Tests:** Gute Nutzung von `@pytest.mark.parametrize` für Enum-Validierungen
5. **Keine Netzwerkzugriffe:** Unit-Tests sind vollständig isoliert (kein echter I/O)

---

## 5. Verbleibende Coverage-Lücken (priorisiert)

| Priorität | Modul                                                   | Geschätzte fehlende Tests | Risiko                           |
| --------- | ------------------------------------------------------- | ------------------------- | -------------------------------- |
| P1        | `pwbs/queue/tasks/*.py` (5 Dateien)                     | ~30                       | Celery-Tasks ohne Tests          |
| P1        | `pwbs/api/middleware/rate_limit.py` (Redis-Integration) | ~10                       | Rate-Limit-Bypass möglich        |
| P2        | `pwbs/connectors/zoom/*.py`                             | ~15                       | Zoom-Konnektor nur 1 Testdatei   |
| P2        | `pwbs/processing/chunking.py`                           | ~10                       | Semantisches Chunking ungetestet |
| P2        | `pwbs/dsgvo/anonymization.py`                           | ~10                       | DSGVO-Anonymisierung             |
| P3        | `pwbs/search/hybrid.py`                                 | ~8                        | Hybrid-Suche (RRF-Fusion)        |
| P3        | `pwbs/scheduler/jobs/*.py`                              | ~12                       | Scheduler-Jobs                   |

---

## 6. Empfehlungen

### Kurzfristig (Sprint)

1. **User-Factory-Fixture:** `_make_user()` in `conftest.py` zentralisieren mit allen relevanten Feldern
2. **Celery-Task-Tests:** Mindestens Smoke-Tests für alle 5 Queue-Tasks
3. **Rate-Limit-Integrationstest:** Redis-Mock-basierter Test für den vollen Middleware-Stack

### Mittelfristig (Quartal)

4. **Property-Based Testing (Hypothesis):** Für Chunking, Fuzzy-Matching und Enum-Serialisierung
5. **Snapshot-Tests:** Für Briefing-Output-Struktur (Regression-Schutz)
6. **Test-Timing-Budget:** 30s-Timeout aus pyproject.toml mit spezifischen Markern für langsame Tests

### Langfristig (Phase 3)

7. **Coverage-CI-Gate:** `pytest-cov` mit Mindest-Coverage (z.B. 80%) als CI-Check
8. **Contract-Tests:** Für Service-Split-Vorbereitung (API-Grenzen)
