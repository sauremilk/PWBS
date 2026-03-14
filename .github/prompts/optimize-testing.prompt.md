---
agent: agent
description: "Tiefenoptimierung der Test-Strategie und -Qualität im PWBS-Workspace. Analysiert Coverage-Lücken, Test-Patterns, Edge-Cases, Fixture-Qualität und Test-Architektur – zustandsunabhängig bei jeder Ausführung."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Test-Optimierung

> **Fundamentalprinzip: Zustandslose Frische**
>
> Tests veralten genauso wie Code. Bei jeder Ausführung die gesamte Test-Suite gegen den aktuellen Produktions-Code evaluieren. Keine Annahmen über vorherige Test-Verbesserungen.

> **Robustheitsregeln:**
>
> - Prüfe, welche Test-Dateien und Test-Frameworks tatsächlich existieren.
> - Bei Modulen ohne Tests: Identifiziere als Coverage-Gap mit konkretem Testplan.
> - Teste nicht das, was nicht existiert – aber identifiziere, was getestet werden muss, sobald es existiert.
> - Verwende plattformgerechte Befehle (pytest auf Backend, npm-Scripts auf Frontend).

---

## Phase 0: Test-Inventar erstellen (Extended Thinking)

### 0.1 Test-Dateien kartieren

```
tests/
├── conftest.py          → Globale Fixtures
├── unit/                → Unit-Tests (schnell, isoliert)
├── integration/         → Integrationstests (benötigen DBs)
├── e2e/                 → End-to-End-Tests
├── test_api/            → API-Endpunkt-Tests
├── test_connectors/     → Konnektor-Tests
├── test_processing/     → Processing-Pipeline-Tests
└── test_services/       → Service-Layer-Tests
```

Für jedes Verzeichnis:

- Welche Dateien existieren?
- Wie viele Tests pro Datei?
- Welche Fixtures werden verwendet?

### 0.2 Coverage-Map erstellen

| Source-Modul     | Test-Dateien     | Geschätzte Coverage | Lücken |
| ---------------- | ---------------- | ------------------- | ------ |
| pwbs/api/        | test_api/        | ...%                | ...    |
| pwbs/connectors/ | test_connectors/ | ...%                | ...    |
| pwbs/processing/ | test_processing/ | ...%                | ...    |
| pwbs/core/       | ...              | ...%                | ...    |
| pwbs/storage/    | ...              | ...%                | ...    |
| pwbs/briefing/   | ...              | ...%                | ...    |
| pwbs/search/     | ...              | ...%                | ...    |
| pwbs/graph/      | ...              | ...%                | ...    |
| pwbs/scheduler/  | ...              | ...%                | ...    |
| pwbs/services/   | test_services/   | ...%                | ...    |

---

## Phase 1: Test-Qualitäts-Analyse

### 1.1 Test-Anatomy

Für jeden existierenden Test prüfen:

- [ ] **Benennung:** Folgt `test_<was_wird_getestet>_<szenario>_<erwartetes_ergebnis>` Pattern
- [ ] **Arrange-Act-Assert:** Klare Struktur mit erkennbaren Phasen
- [ ] **Single Assertion:** Pro Test idealerweise ein logisches Assert
- [ ] **Isolation:** Test hängt nicht von Ausführungsreihenfolge oder anderen Tests ab
- [ ] **Determinismus:** Test liefert immer das gleiche Ergebnis (kein Zeitabhängigkeit, kein Random)

### 1.2 Was wird getestet?

- [ ] **Verhalten**, nicht Implementierung (Black-Box-Testing bevorzugt)
- [ ] **Geschäftslogik** hat höchste Test-Priorität
- [ ] **Grenzwerte**: Leere Listen, `None`, maximale/minimale Werte
- [ ] **Fehlerpfade**: Was passiert bei Exceptions, Timeouts, ungültigen Inputs?
- [ ] **Keine Tautologien**: Tests, die nur die Mock-Konfiguration zurückgeben

### 1.3 Async-Test-Patterns

- [ ] `pytest-asyncio` korrekt konfiguriert (`asyncio_mode = "auto"` in `pyproject.toml`)
- [ ] Async-Fixtures mit `@pytest_asyncio.fixture` statt `@pytest.fixture`
- [ ] Keine `asyncio.run()` innerhalb von Tests
- [ ] Timeout für async-Tests, um Hangs zu verhindern
- [ ] Event-Loop-Isolation zwischen Tests

---

## Phase 2: Fixture-Analyse

### 2.1 conftest.py Qualität

Lies `tests/conftest.py` und alle modul-spezifischen `conftest.py`:

- [ ] Fixtures für alle externen Abhängigkeiten (DBs, API-Clients, LLM)
- [ ] Keine echten Netzwerkzugriffe in Unit-Tests
- [ ] Fixture-Scope korrekt: `session` für teure Setup, `function` für isolierte Tests
- [ ] Kein Fixture-Overengineering – einfache Tests brauchen keine komplexen Fixtures
- [ ] Factory-Fixtures für flexible Test-Daten-Erstellung

### 2.2 Mock-Qualität

- [ ] Mocks spiegeln das tatsächliche Interface wider (kein Over-Mocking)
- [ ] `AsyncMock` für async-Funktionen verwendet
- [ ] Mocks werden nach dem Test zurückgesetzt
- [ ] Keine Mocks, die das zu testende Verhalten verbergen
- [ ] Integration-Tests als Ergänzung zu gemockten Unit-Tests

### 2.3 Test-Daten

- [ ] Fabrik-Funktionen oder Fixtures für wiederverwendbare Test-Daten
- [ ] Test-Daten sind minimal – nur die nötigen Felder
- [ ] Keine hardcodierten UUIDs/Timestamps, die brechen könnten
- [ ] DSGVO-relevante Test-Daten: `owner_id` immer gesetzt

---

## Phase 3: Coverage-Gap-Analyse (Extended Thinking)

### 3.1 Kritische Pfade ohne Tests

Identifiziere die geschäftskritischsten Code-Pfade und prüfe ihre Test-Coverage:

**Höchste Priorität (Sicherheit & Datenintegrität):**

1. Authentifizierung und Autorisierung
2. owner_id-Filterung in allen Queries
3. Datenlöschung (DSGVO Right to Erasure)
4. Token-Verschlüsselung und -Rotation
5. Input-Validierung an API-Grenzen

**Hohe Priorität (Kernfunktionalität):**

1. Ingestion-Pipeline (Fetch → Normalize → Store)
2. Processing-Pipeline (Chunk → Embed → NER → Graph)
3. Such-Pipeline (Query → Search → Rank → Return)
4. Briefing-Generierung

**Mittlere Priorität (Robustheit):**

1. Fehlerbehandlung und Retry-Logik
2. Idempotenz (doppeltes Ausführen produziert keinen Duplikat)
3. Cursor/Watermark-Persistierung
4. Graceful Degradation bei Teil-Ausfällen

### 3.2 Edge Cases identifizieren

Für jedes Modul systematisch:

| Edge Case                              | Modul      | Test existiert? | Priorität |
| -------------------------------------- | ---------- | --------------- | --------- |
| Leere Eingabeliste                     | Processing | ...             | Hoch      |
| None-Werte in optionalen Feldern       | Alle       | ...             | Hoch      |
| Abgelaufener OAuth-Token               | Connectors | ...             | Kritisch  |
| DB-Connection-Fehler                   | Storage    | ...             | Hoch      |
| LLM-Timeout oder Fehler                | Briefing   | ...             | Hoch      |
| Duplikat-Dokument-Ingestion            | Ingestion  | ...             | Kritisch  |
| Sehr langes Dokument (> 100k Token)    | Processing | ...             | Mittel    |
| Unicode/Sonderzeichen in Content       | Alle       | ...             | Mittel    |
| Concurrent Writes auf gleiche Resource | Storage    | ...             | Hoch      |
| Rate-Limit von externer API            | Connectors | ...             | Hoch      |

---

## Phase 4: Test-Strategie-Optimierung

### 4.1 Test-Pyramide bewerten

```
          /  E2E  \        ← Wenig, teuer, langsam
         / Integration \    ← Moderat, DBs nötig
        /    Unit Tests  \  ← Viele, schnell, isoliert
```

- [ ] Unit-Tests bilden die breite Basis (> 70% der Tests)
- [ ] Integration-Tests decken kritische Schnittstellen ab
- [ ] E2E-Tests decken die wichtigsten User-Journeys ab
- [ ] Kein invertiertes Pyramiden-Anti-Pattern (mehr E2E als Unit-Tests)

### 4.2 Test-Performance

- [ ] Unit-Test-Suite läuft in < 30 Sekunden
- [ ] Keine unnötigen DB-Zugriffe in Unit-Tests
- [ ] Fixture-Scope optimiert (teure Setups einmal pro Session)
- [ ] Parallele Testausführung möglich (keine Shared State-Konflikte)

### 4.3 CI-Readiness

- [ ] Tests sind in CI ausführbar (keine lokalen Pfad-Abhängigkeiten)
- [ ] Integration-Tests haben Docker-Compose-Setup
- [ ] Test-Marker (`@pytest.mark.integration`, `@pytest.mark.e2e`) korrekt gesetzt
- [ ] Flaky-Test-Detection (Tests, die nur manchmal fehlschlagen)

---

## Phase 5: Tests implementieren

### 5.1 Priorisierte Test-Erstellung

Für jede identifizierte Coverage-Lücke:

1. **Sicherheits-Tests zuerst** (owner_id, Auth, Injection)
2. **Idempotenz-Tests** (Duplikate, Wiederholung)
3. **Edge-Case-Tests** (None, leere Listen, Fehler)
4. **Happy-Path-Tests** (Standardabläufe)

### 5.2 Test-Implementierungs-Standards

Jeder neue Test MUSS:

- Vollständig und lauffähig sein (keine Platzhalter)
- Fixtures für externe Abhängigkeiten verwenden
- Kein echter Netzwerkzugriff in Unit-Tests
- Aussagekräftige Assertion-Messages haben
- DSGVO: `owner_id` in allen Test-Daten setzen

---

## Phase 6: Test-Bericht

```markdown
# Test-Optimierungsbericht – [Datum]

## Metriken

| Metrik            | Vorher | Nachher | Ziel                  |
| ----------------- | ------ | ------- | --------------------- |
| Anzahl Tests      | ...    | ...     | ...                   |
| Est. Coverage     | ...%   | ...%    | > 80%                 |
| Test-Laufzeit     | ...s   | ...s    | < 30s                 |
| Sicherheits-Tests | ...    | ...     | 100% kritischer Pfade |

## Coverage-Lücken geschlossen

1. ...

## Neue Tests erstellt

1. ...

## Verbleibende Lücken

1. ...

## Empfehlungen

1. ...
```

---

## Opus 4.6 – Kognitive Verstärker

- **Inverses Denken:** Für jeden Code-Pfad: „Wie kann ich diesen Code zum Absturz bringen?" → Das ist der Test.
- **Kombinatorische Analyse:** Welche Input-Kombinationen erzeugen unerwartetes Verhalten?
- **Regressionspotenzial:** Welche Stellen brechen am wahrscheinlichsten bei zukünftigen Änderungen?
- **Test-Entkopplung:** Vermeide Tests, die bei Refactoring brechen – teste Verhalten, nicht Implementierung.
