---
agent: agent
description: "Tiefenoptimierung der Dependencies und Technical Debt im PWBS-Workspace. Analysiert Abhängigkeitsversionen, bekannte Schwachstellen, veraltete Patterns, Tech-Debt-Hotspots und Upgrade-Pfade – zustandsunabhängig bei jeder Ausführung."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
  - fetch
---

# Dependency- und Tech-Debt-Optimierung

> **Fundamentalprinzip: Zustandslose Frische**
>
> Dependencies und Tech Debt akkumulieren kontinuierlich. Bei jeder Ausführung den gesamten Abhängigkeitsbaum und alle Code-Patterns von Grund auf bewerten. Keine Annahmen über vorherige Audits.

> **Robustheitsregeln:**
>
> - Prüfe, welche Dependency-Management-Dateien existieren (`pyproject.toml`, `package.json`, `requirements.txt`).
> - Wenn `pip audit` oder `npm audit` nicht ausführbar ist, analysiere Versionen manuell.
> - Unterscheide: „veraltete Version" (funktioniert, aber nicht aktuell) vs. „vulnerable Version" (Sicherheitsrisiko).
> - Plattformgerechte Befehle verwenden.

---

## Phase 0: Dependency-Inventar (Extended Thinking)

### 0.1 Python Backend

Lies `backend/pyproject.toml` und erstelle ein vollständiges Inventar:

| Package     | Aktuelle Version | Kategorie        | Kritisch?     |
| ----------- | ---------------- | ---------------- | ------------- |
| fastapi     | ≥0.115.0         | Web Framework    | Ja            |
| pydantic    | ≥2.10.0          | Datenvalidierung | Ja            |
| sqlalchemy  | ≥2.0.36          | ORM              | Ja            |
| asyncpg     | ≥0.30.0          | DB-Driver        | Ja            |
| python-jose | ≥3.3.0           | JWT              | Ja (Security) |
| passlib     | ≥1.7.4           | Password Hashing | Ja (Security) |
| ...         | ...              | ...              | ...           |

Optionale Dependencies:

- `[llm]`: anthropic, openai
- `[vector]`: weaviate-client, sentence-transformers
- `[graph]`: neo4j
- `[dev]`: pytest, ruff, mypy, pre-commit

### 0.2 Frontend

Lies `frontend/package.json`:

| Package     | Aktuelle Version | Kategorie   | Kritisch? |
| ----------- | ---------------- | ----------- | --------- |
| next        | ^14.2.0          | Framework   | Ja        |
| react       | ^18.3.0          | UI Library  | Ja        |
| typescript  | ^5.7.0           | Type System | Ja        |
| tailwindcss | ^3.4.0           | Styling     | Nein      |
| ...         | ...              | ...         | ...       |

### 0.3 Docker/Infrastructure

| Image/Tool  | Version | Quelle             |
| ----------- | ------- | ------------------ |
| PostgreSQL  | ...     | docker-compose.yml |
| Weaviate    | ...     | docker-compose.yml |
| Neo4j       | ...     | docker-compose.yml |
| Redis       | ...     | docker-compose.yml |
| Python Base | ...     | Dockerfile         |
| Node Base   | ...     | Dockerfile         |

---

## Phase 1: Sicherheits-Audit

### 1.1 Bekannte Schwachstellen (CVEs)

Falls möglich, führe aus:

```bash
# Python
cd backend && pip audit

# Node
cd frontend && npm audit
```

Falls nicht ausführbar, prüfe manuell:

**Python – Bekannte Risiko-Packages:**

- [ ] `python-jose`: Bevorzugt `PyJWT` oder `python-jose[cryptography]`
- [ ] `passlib`: Aktiv maintained? Alternative: `argon2-cffi` direkt
- [ ] `jinja2`: Auto-Escaping aktiviert?
- [ ] `httpx`: Kein SSRF durch unbeschränkte URLs

**JavaScript:**

- [ ] Keine Packages mit bekannten Prototype Pollution Vulnerabilities
- [ ] Keine veralteten React/Next.js Versionen mit bekannten XSS-Vectors

### 1.2 Supply Chain Risiken

- [ ] Lock-Files existieren und werden committet (`package-lock.json`, `requirements.lock`)
- [ ] Kein `pip install` aus unbekannten Quellen
- [ ] Keine Typosquatting-Risiken in Package-Namen
- [ ] Dependencies minimiert – keine unbenutzten Packages

---

## Phase 2: Versions-Aktualität

### 2.1 Major-Version-Gaps

| Package | Pinned | Latest Stable | Gap | Breaking Changes? |
| ------- | ------ | ------------- | --- | ----------------- |
| ...     | ...    | ...           | ... | ...               |

Prüfe für jedes Package mit signifikantem Gap:

- Gibt es Security-Fixes in neueren Versionen?
- Gibt es Performance-Verbesserungen?
- Welche Breaking Changes existieren?
- Lohnt sich das Upgrade für den aktuellen Stand?

### 2.2 Deprecated Packages

- [ ] Keine Packages, die offiziell deprecated sind
- [ ] Keine Packages, die seit > 12 Monaten kein Release hatten
- [ ] Alternatives für unmaintained Packages vorschlagen

### 2.3 Version-Pinning-Strategie

- [ ] Production Dependencies: Mindestversion gepinnt (`>=X.Y.Z`)
- [ ] Dev Dependencies: Range gepinnt
- [ ] Docker Images: Exakte Version, kein `latest`
- [ ] Konsistentes Pinning-Schema über alle Konfigurationsdateien

---

## Phase 3: Tech Debt Identifikation (Extended Thinking)

### 3.1 Code-Smells systematisch suchen

Durchsuche den gesamten Code nach:

**Architekturelle Tech Debt:**

- [ ] Module, die ihre Verantwortlichkeit überschreiten
- [ ] Abstractions, die nicht genutzt werden (Over-Engineering)
- [ ] Fehlende Abstractions (Copy-Paste statt DRY)
- [ ] Hardcodierte Werte, die konfigurierbar sein sollten

**Code-Level Tech Debt:**

- [ ] `# TODO:`, `# FIXME:`, `# HACK:`, `# WORKAROUND:` – Inventar erstellen
- [ ] `type: ignore` oder `noqa` Kommentare – jeder braucht eine Begründung
- [ ] Auskommentierter Code
- [ ] Leere except-Blöcke
- [ ] Veraltete API-Patterns (Pydantic v1, alte SQLAlchemy Syntax)

**Test-Debt:**

- [ ] Skipped Tests (`@pytest.mark.skip`)
- [ ] Tests, die nur in bestimmten Umgebungen laufen
- [ ] Fehlende Edge-Case-Tests für kritische Pfade

### 3.2 Tech Debt Scoring

| Tech Debt Item | Kategorie                   | Impact              | Wachstumsrate           | Fix-Aufwand |
| -------------- | --------------------------- | ------------------- | ----------------------- | ----------- |
| ...            | Architektur/Code/Test/Infra | Hoch/Mittel/Niedrig | Steigend/Stabil/Sinkend | S/M/L       |

**Priorisierung:** Fokus auf Tech Debt mit hoher Wachstumsrate (wird schlimmer mit der Zeit).

### 3.3 Veraltete Patterns

Suche nach:

```python
# Pydantic v1 (veraltet):
class Config:
    orm_mode = True
# Korrekt (Pydantic v2):
model_config = ConfigDict(from_attributes=True)

# Altes Optional (veraltet in 3.12+):
from typing import Optional, List
# Korrekt:
list[str] | None

# Altes dict/list (veraltet):
Dict[str, Any], List[int]
# Korrekt:
dict[str, Any], list[int]
```

---

## Phase 4: Upgrade-Planung

### 4.1 Kritische Upgrades (Sicherheit)

Für jedes Package mit bekannter Schwachstelle:

| Package | Von | Nach | CVE | Aufwand | Breaking? |
| ------- | --- | ---- | --- | ------- | --------- |
| ...     | ... | ...  | ... | S/M/L   | Ja/Nein   |

### 4.2 Strategische Upgrades (Features/Performance)

| Package | Von | Nach | Benefit | Aufwand | Empfehlung       |
| ------- | --- | ---- | ------- | ------- | ---------------- |
| ...     | ... | ...  | ...     | S/M/L   | Upgrade/Abwarten |

### 4.3 Migrations-Pfade

Für jedes empfohlenes Major-Upgrade:

1. Breaking Changes dokumentieren
2. Betroffene Code-Stellen identifizieren
3. Test-Strategie für Upgrade
4. Rollback-Plan

---

## Phase 5: Optimierungen implementieren

### 5.1 Sofort (Sicherheit)

- Packages mit bekannten CVEs upgraden
- Pin-Ranges verschärfen wo nötig

### 5.2 Quick Wins (Tech Debt)

- TODO-Kommentare mit Task-IDs verknüpfen
- Veraltete Patterns modernisieren
- Auskommentierten Code entfernen
- Ungenutzte Dependencies entfernen

### 5.3 Empfehlungen (Strategic)

Für größere Upgrades: Konkreten Plan mit Schritten erstellen.

---

## Phase 6: Dependency- und Tech-Debt-Bericht

```markdown
# Dependency & Tech Debt Bericht – [Datum]

## Security Status

- Kritische CVEs: ...
- Unpatched Packages: ...
- Supply Chain Risiko: Niedrig/Mittel/Hoch

## Tech Debt Score

| Kategorie    | Items | Trend |
| ------------ | ----- | ----- |
| Architektur  | ...   | ↑/→/↓ |
| Code         | ...   | ...   |
| Tests        | ...   | ...   |
| Dependencies | ...   | ...   |

## Durchgeführte Fixes

1. ...

## Upgrade-Roadmap

| Q               | Upgrade | Benefit | Aufwand |
| --------------- | ------- | ------- | ------- |
| Jetzt           | ...     | ...     | ...     |
| Nächster Sprint | ...     | ...     | ...     |
| Backlog         | ...     | ...     | ...     |
```

---

## Opus 4.6 – Kognitive Verstärker

- **Transitive Abhängigkeitsanalyse:** Ein Package-Update kann kaskadierend andere Packages betreffen – modelliere die volle Abhängigkeitskette.
- **Historische Muster:** Welche Packages in diesem Stack haben häufig Breaking Changes? Vorausschauend pinnen.
- **Opportunity Cost:** Welche Zeit wird für Workarounds alter Versionen verschwendet, die ein Upgrade einsparen würde?
- **Debt-Akkumulation:** Welcher Tech Debt wächst am schnellsten und wird bald zur Architektur-Blockade?
