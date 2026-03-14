---
agent: agent
description: "Tiefenoptimierung der Code-Qualität im gesamten PWBS-Workspace. Analysiert Python-Backend und TypeScript-Frontend auf Typing, Patterns, Konsistenz, Komplexität und Idiomatik – zustandsunabhängig bei jeder Ausführung."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Code-Qualitäts-Optimierung

> **Fundamentalprinzip: Zustandslose Frische**
>
> Bei jeder Ausführung den gesamten Code neu analysieren. Keine Annahmen über vorherige Optimierungen. Jede Datei verdient eine frische, kritische Betrachtung.

> **Robustheitsregeln:**
>
> - Prüfe, welche Source-Dateien tatsächlich existieren – analysiere nur vorhandenen Code.
> - Bei leeren Modulen (nur `__init__.py`): Notiere als „noch zu implementieren", nicht als Fehler.
> - Plattformgerechte Shell-Befehle verwenden.
> - Prüfungen an den tatsächlichen Tech-Stack anpassen (Python 3.12+, Pydantic v2, FastAPI, Next.js 14+).

**Fokus-Bereich:** ${input:scope:Welcher Bereich soll optimiert werden? z.B. "backend", "frontend", "all", "pwbs/connectors/", "frontend/src/components/"}

---

## Phase 0: Code-Inventar erstellen (Extended Thinking)

Bevor du optimierst, erstelle ein vollständiges Inventar:

1. **Dateibaum** – Liste alle Source-Dateien im Zielbereich (`.py`, `.ts`, `.tsx`)
2. **LOC-Schätzung** – Wie viel Code existiert pro Modul?
3. **Implementierungsgrad** – Welche Module sind vollständig, partial, stub?
4. **Abhängigkeitsgraph** – Welches Modul importiert was?

---

## Phase 1: Python Backend-Analyse

Für jede `.py`-Datei in `pwbs/` und `tests/`:

### 1.1 Type Annotations

- [ ] Alle Funktionsargumente und Rückgabewerte vollständig annotiert
- [ ] `list[X]`, `dict[K,V]`, `tuple[X,...]` statt `List`, `Dict`, `Tuple` (Python 3.12+)
- [ ] `X | None` statt `Optional[X]`
- [ ] Kein `Any` – wenn unvermeidbar, begründeter Kommentar
- [ ] `TypeVar`, `Generic`, `Protocol` korrekt eingesetzt wo nötig
- [ ] Pydantic-Modelle mit vollständigen Field-Annotationen

### 1.2 Pydantic v2 Compliance

- [ ] `model_config = ConfigDict(...)` statt `class Config:`
- [ ] `@model_validator(mode="after")` statt veraltetem `@validator`
- [ ] `@field_validator` mit korrekter Signatur
- [ ] `model_dump()` statt `dict()`
- [ ] `model_validate()` statt `parse_obj()`
- [ ] Keine Verwendung veralteter Pydantic v1 Patterns

### 1.3 FastAPI Patterns

- [ ] Response-Objekte in Route-Signaturen als `Response` annotiert (nicht `Response | None`)
- [ ] `Response` vor Default-Parameter-Dependencies platziert
- [ ] Dependency Injection konsequent genutzt
- [ ] Status-Codes in Dekoratoren explizit angegeben
- [ ] `HTTPException` mit strukturiertem `detail`-Dict

### 1.4 Async-Konsistenz

- [ ] `async def` für alle I/O-gebundenen Operationen
- [ ] Kein synchroner blocking Code im Event-Loop
- [ ] `asyncio.to_thread()` für unvermeidbare Blocking-Operationen
- [ ] `async with` für Context-Manager mit I/O
- [ ] Keine `asyncio.run()` innerhalb von async-Kontexten

### 1.5 Fehlerbehandlung

- [ ] Eigene Exception-Klassen abgeleitet von `PWBSError`
- [ ] Granulare Exceptions (nicht bare `except:` oder `except Exception:`)
- [ ] Strukturierte Error-Responses in API-Endpunkten
- [ ] Retry-Logik mit Exponential Backoff für transiente Fehler
- [ ] Ressourcen-Cleanup in `finally`-Blöcken oder Context-Managern

### 1.6 Import-Qualität

- [ ] Absolute Imports bevorzugt (`from pwbs.core.config import Settings`)
- [ ] Keine zirkulären Imports (prüfe mit `TYPE_CHECKING`-Guard wo nötig)
- [ ] Import-Sortierung konsistent (isort/ruff-kompatibel)
- [ ] Keine ungenutzten Imports
- [ ] Keine Wildcard-Imports (`from x import *`)

### 1.7 Code-Gesundheit

- [ ] Keine Funktionen > 50 LOC ohne Aufteilung
- [ ] Keine duplizierte Logik zwischen Modulen
- [ ] Keine magischen Strings/Zahlen – Konstanten oder Enums verwenden
- [ ] Keine auskommentierten Code-Blöcke
- [ ] Keine `# TODO: implement` ohne zugehörigen Task
- [ ] Single Responsibility pro Klasse/Funktion

---

## Phase 2: TypeScript Frontend-Analyse

Für jede `.ts`/`.tsx`-Datei in `frontend/src/`:

### 2.1 TypeScript Strictness

- [ ] Kein `any` – stattdessen `unknown` und Type Guards
- [ ] Explizite Props-Interfaces für alle Komponenten
- [ ] `as const` statt `enum` wo möglich
- [ ] Keine Type Assertions (`as X`) ohne klare Begründung
- [ ] Discriminated Unions für komplexe State-Typen

### 2.2 React/Next.js Patterns

- [ ] Server Components als Default, `"use client"` nur bei tatsächlichem Bedarf
- [ ] Kein State/Effects in Server Components
- [ ] `Suspense`-Boundaries für asynchrone Operationen
- [ ] Error Boundaries für robuste Fehlerbehandlung
- [ ] Kein Prop Drilling – Composition Patterns bevorzugen

### 2.3 API-Integration

- [ ] Alle API-Aufrufe über `lib/api/` abstrahiert
- [ ] Kein direktes `fetch()` in Komponenten
- [ ] Fehlerbehandlung mit strukturierten `ApiError`-Typen
- [ ] Loading- und Error-States für jede asynchrone Operation

### 2.4 Frontend-Code-Gesundheit

- [ ] Keine übermäßig große Komponenten (> 200 LOC aufteilen)
- [ ] Konsistente Benennung (PascalCase Komponenten, camelCase Funktionen)
- [ ] Tailwind-Klassen konsistent, `cn()` für bedingte Klassen
- [ ] Keine inline-Styles
- [ ] Keine ungenutzten Imports oder Variablen

---

## Phase 3: Cross-Cutting Concerns

### 3.1 Konsistenz zwischen Backend und Frontend

- [ ] API-Typen im Frontend spiegeln Pydantic-Schemas des Backends
- [ ] Fehlerformate sind konsistent (Backend `detail`-Dict → Frontend `ApiError`)
- [ ] Enum-Werte stimmen zwischen Backend und Frontend überein

### 3.2 Idempotenz-Patterns

- [ ] Alle DB-Writes als Upsert (`ON CONFLICT DO UPDATE` in PostgreSQL)
- [ ] Weaviate: Prüfung vor Insert anhand `source_id`
- [ ] Neo4j: `MERGE` statt `CREATE`
- [ ] Cursor/Watermark nach erfolgreichem Batch persistiert
- [ ] Pipeline kann ohne Datenverlust neu gestartet werden

### 3.3 DSGVO-Compliance im Code

- [ ] Jede DB-Query mit User-Bezug enthält `WHERE owner_id = ...`
- [ ] Alle nutzerbezogenen Datenstrukturen haben `owner_id` und `expires_at`
- [ ] Keine PII in Log-Statements
- [ ] Löschkaskade implementiert für User-Deletion

---

## Phase 4: Automatisierte Qualitätsprüfung

Führe folgende Checks aus (sofern die Tools installiert sind):

```
# Python
ruff check pwbs/ tests/ --select ALL
mypy pwbs/ --strict
pytest tests/unit/ -v --tb=short

# Frontend
cd frontend && npm run type-check
cd frontend && npm run lint
```

Analysiere die Ausgabe und korreliere mit den manuellen Findings.

---

## Phase 5: Optimierungen implementieren

Für jedes Finding:

1. **Bewerte:** Ist es ein echter Qualitätsmangel oder eine Stilfrage?
2. **Priorisiere:** Sicherheit > Korrektheit > Konsistenz > Stil
3. **Implementiere:** Vollständige Fixes, keine Platzhalter
4. **Validiere:** Prüfe, dass der Fix keine Regression einführt

---

## Phase 6: Qualitätsbericht

```markdown
# Code-Qualitätsbericht – [Datum]

## Analysierter Bereich

[Scope und Dateianzahl]

## Metriken

| Metrik                    | Wert    | Ziel | Status |
| ------------------------- | ------- | ---- | ------ |
| Type Coverage (Python)    | ...%    | 100% | ...    |
| Ruff Violations           | ...     | 0    | ...    |
| MyPy Errors               | ...     | 0    | ...    |
| TS Strict Errors          | ...     | 0    | ...    |
| Durchschn. Funktionslänge | ... LOC | < 30 | ...    |

## Top-Findings

1. ...
2. ...

## Durchgeführte Fixes

1. ...

## Empfehlungen für nächsten Lauf

1. ...
```

---

## Opus 4.6 – Kognitive Verstärker

- **Muster-Erkennung:** Identifiziere systematische Code-Probleme, die über Copy-Paste oder fehlende Konventionen entstanden sind.
- **Refactoring-Planung:** Bei strukturellen Problemen erst die Gesamtauswirkung modellieren, dann schrittweise refactorn.
- **Idiomatik-Transfer:** Erkenne Patterns aus anderen Sprachen/Frameworks, die in Python/TypeScript nicht idiomatisch sind.
- **Vorausschauende Analyse:** Welcher Code wird bei Wachstum zum Bottleneck oder Wartungsproblem?
