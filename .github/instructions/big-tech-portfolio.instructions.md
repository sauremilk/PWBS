<!-- MOVED: Vollständiger Inhalt → .github/skills/portfolio-standards/SKILL.md
     Aktivierung: Skill `portfolio-standards` im Chat verwenden.
     applyTo entfernt um Token-Last bei jeder Interaktion zu vermeiden. -->

---

## I. Design Before Code (Google Design Doc / Amazon 6-Pager)

**Pflicht vor jeder nicht-trivialen Änderung (> 50 LOC oder neue Abstraktion):**

### Design-Checkliste (mental vor dem ersten Keystroke)

1. **Problem Statement** – Was ist das exakte Problem? Warum jetzt?
2. **Non-Goals** – Was lösen wir explizit NICHT? (Scope-Creep verhindern)
3. **Alternatives Considered** – Mindestens 2 Alternativen skizziert und verworfen (mit Begründung)
4. **API Contract** – Wie sieht das Interface aus? (Signatur zuerst, Implementierung danach)
5. **Data Model Impact** – Welche Schema-Änderungen entstehen? Ist eine Alembic-Migration nötig?
6. **Failure Modes** – Was passiert wenn X ausfällt? Graceful Degradation definiert?
7. **Security & Privacy** – Threat-Modell skizziert? `owner_id`-Filter gesetzt? PII-Handling klar?
8. **Observability** – Welche Metriken/Logs belegen, dass das Feature funktioniert?
9. **Rollback Plan** – Wie reverten wir das Feature ohne Datenverlust?

> **Google Rule**: "A design doc that took 1 day to write saves 1 week of debugging."
> Für ADRs: Template in `docs/adr/000-template.md` verwenden.

---

## II. Testing Pyramid & Quality Gates (Google Testing Philosophy)

```
         /\
        /E2E\          ← Wenige, langsam, teuer – nur kritische User-Journeys
       /------\
      /Integrat\       ← Moderate Anzahl – Service-Grenzen testen
     /----------\
    / Unit Tests  \    ← Viele, schnell, eigenständig – Geschäftslogik isoliert
   /--------------\
```

### Pflichtregeln

- **70/20/10-Ratio** anstreben: 70% Unit, 20% Integration, 10% E2E
- **Keine Tests überspringen** für gelieferte Features – jede neue Funktion hat mindestens einen Test
- **Hermetic Tests only**: Kein echter Netzwerkzugriff (Redis/Weaviate/Neo4j/DB alle gemockt in Unit-Tests)
- **Eigenschaft statt Beispiel**: Neben Happy-Path immer `None`-Input, leere Listen, Overflow-Cases testen
- **Test-Names als Dokumentation**: `test_search_returns_empty_list_when_no_documents_indexed` – nie `test_search()`
- **Assertions are specifications**: Ein Test = eine Kernaussage. Mehrere Assertions = mehrere Tests.

### Mutation Testing Mindset (Google's "Effectiveness over Coverage")

Coverage-Zahlen lügen. Frag stattdessen: _Würde ein Test rot werden, wenn ich diese Zeile lösche?_
Wenn nein → Test ist schwach, unabhängig vom Coverage-Score.

### Performance-Tests als Bürger erster Klasse

```python
# Jede neue Query / Algorithmus bekommt einen Benchmark
# Regression-Guard: max. 20% langsamer als Baseline
@pytest.mark.benchmark
def test_hybrid_search_p99_latency(benchmark):
    result = benchmark(search_service.search, query="quarterly review", top_k=10)
    assert benchmark.stats["mean"] < 0.200  # 200ms Ziel-P99
```

---

## III. Observability-First (Google SRE / Apple Telemetry)

### Das "Three Pillars"-Prinzip (Google SRE Book)

Jedes Feature ist erst "shipped" wenn es in allen drei Dimensionen observable ist:

```
1. LOGS    → Strukturiertes JSON (structlog). Nur IDs, keine PII.
              log.info("briefing.generated", briefing_id=str(id), duration_ms=elapsed)

2. METRICS → Prometheus Counter/Histogram für jede kritische Operation.
              BRIEFING_LATENCY.observe(elapsed)   # Histogram, nicht nur Counter

3. TRACES  → Correlation-ID durch alle Schichten (bereits in Middleware aktiv).
              Jeden externen API-Call (LLM, Weaviate, Neo4j) als Span tracen.
```

### SLO-Mentalität vor jeder neuen Route

Bevor ein neuer API-Endpunkt gereviewed wird:

- **Availability-SLO**: Ziel (z.B. 99,9%) und Error Budget berechnet?
- **Latency-SLO**: P50 / P99 definiert? (z.B. P99 < 500 ms für Search-Endpunkte)
- **Alerting**: Prometheus-Alert-Rule vorhanden wenn SLO verletzt wird?

---

## IV. API Contract-First Design (OpenAI / Google API Design Guidelines)

### Prinzipien (aus Google API Design Guide + OpenAI API-Philosophie)

1. **Stabilität über Cleverness** – Ein langweiliges, vorhersehbares Interface schlägt jedes clevere API.
2. **Minimal surface area** (Apple-Philosophie) – Öffentliche API-Felder sind Schulden. Jeden Field hinterfragen.
3. **Idempotenz by default** – Jedes POST/PUT muss bei Wiederholung dasselbe Ergebnis liefern.
4. **Versionierung vor Breaking Changes** – Niemals `/v1/` brechen. Neues Feature → `/v2/` oder additive Felder.
5. **Error responses als API** – HTTP-Fehler sind Teil des Contracts. `detail`-Dict immer strukturiert:
   ```python
   {"code": "CONNECTOR_AUTH_EXPIRED", "message": "...", "connector_id": "..."}
   ```

### OpenAPI-Spec als Single Source of Truth

- FastAPI generiert `/docs` automatisch – aber: Descriptions, Examples, Deprecation-Hinweise **manuell** pflegen.
- Alle Response-Schemas vollständig typisiert (kein `dict` als Return-Type in Routes).
- Breaking Changes dokumentiert in `CHANGELOG.md` unter `### Breaking Changes`.

---

## V. Code Review Standards (Google's Code Review Developer Guide)

### Als Autor

- **CL (Changelist) so klein wie möglich** – Ein PR löst ein Problem. Split bei > 400 LOC.
- **Description ist Pflicht**: Was ändert sich? Warum? Wie testen? Link zum ADR/Issue.
- **Selbst-Review vor Push**: Diff nochmals lesen als wäre man der Reviewer.
- **Tests sind Teil des PR** – nie "Tests folgen in separatem PR".

### Als Reviewer (wenn Copilot Code generiert)

Validiere jeden generierten Code gegen diese Checkliste:

```
□ owner_id-Filter bei allen DB-Queries?
□ Kein PII in Logs?
□ Idempotent (Upsert statt blindes INSERT)?
□ Fehlerfall behandelt (nicht nur Happy-Path)?
□ Type Annotations vollständig?
□ Test existiert für neue Logik?
□ Kein Hard-Coded Value (URL, Secret, ID)?
□ Keine Abstraktion die nur einmal genutzt wird?
```

### Google's "No LGTM without understanding"

Jede Zeile die unklar ist muss erklärt werden, bevor sie gemergt wird. Bei KI-generiertem Code:
_Kann ich diese Zeile verteidigen wenn ein Staff Engineer fragt?_ Wenn nein → umschreiben.

---

## VI. Operational Excellence (Google SRE / Apple Reliability)

### Runbook-Pflicht für jede Celery-Task und geplante Job

Jeder Job in `pwbs/scheduler/` braucht einen Runbook-Eintrag in `docs/runbooks/`:

- **Symptom**: Wie erkennt man einen Fehler?
- **Diagnosis**: Welche Logs/Metriken prüfen?
- **Mitigation**: Wie sofort stabilisieren (Feature-Flag, Job pausieren)?
- **Resolution**: Rootcause-Fix und Verifizierung.

### Post-Mortem-Kultur (blameless)

Nach jedem Produktionsvorfall (oder kritischem Bug):

- `docs/internal/postmortems/YYYY-MM-DD-<title>.md` erstellen
- Format: Timeline → Root Cause → Impact → Action Items (mit Owner + Deadline)
- Keine Schuldzuweisung – nur: Was hat das System ermöglicht?

### Feature Flags sind Deployment-Safety

Neues Feature immer hinter Feature-Flag deployen:

```python
if feature_flag_service.is_enabled("new_briefing_format", user_id=owner_id):
    return new_generator.generate(context)
return legacy_generator.generate(context)
```

Erst nach 7 Tagen stabilen Betriebs: Flag entfernen, Legacy-Pfad löschen.

---

## VII. Privacy-First Engineering (Apple's Privacy Approach)

### Apple's "Privacy Nutrition Label" Denkmuster

Für jede neue Datenerfassung fragen:

- **Daten-Typ**: Ist das ein Identifier? Kontaktdaten? Gesundheit? Finanz?
- **Verwendungszweck**: Exakt einer. Kein "für zukünftige Features"-Vorbehalt.
- **Verknüpfung mit Identität**: Kann das mit einer Person in Verbindung gebracht werden?
- **Tracking über Apps hinweg**: Nein. Immer Nein.

### Differential Privacy Mindset

Aggregierte Stats (Dashboard, Analytics) dürfen keine Rückschlüsse auf Einzelpersonen erlauben.
Mindest-k = 5: Kein Aggregat ausgeben wenn weniger als 5 Nutzer im Sample.

---

## VIII. AI Safety & Evaluation (OpenAI Engineering Culture)

### Evals als First-Class Citizens

Jedes LLM-Feature hat eine Eval-Suite bevor es in Produktion geht:

```python
# Eval-Struktur: docs/evals/<feature>/
# - test_cases.json    → Input/Expected-Output-Paare
# - eval_runner.py     → Automatisiertes Scoring
# - results/           → Versionierte Ergebnisse (Git-getrackt)
```

**Eval-Metriken für Briefings:**

- Factual consistency (Quellenreferenzen validierbar?)
- Hallucination rate (Behauptungen ohne Quelle?)
- Relevance score (Briefing zum richtigen Kontext?)
- User satisfaction (thumbs up/down aus BriefingFeedback)

### Red-Teaming Documentation

Für jede neue LLM-Interaktion:

- Was ist der worst-case Prompt-Injection Angriff?
- Kann ein Nutzer Information eines anderen Nutzers extrahieren?
- Kann das Modell zu unerwünschten Aktionen gebracht werden?
- Dokumentiert in `docs/adr/` unter Sicherheitsimplikationen.

### "No vibes-based deploys" (OpenAI-Prinzip)

LLM-Qualitätsänderungen nur deployen wenn Eval-Ergebnisse das belegen.
Kein "scheint besser" – nur "Eval-Score verbessert sich von X auf Y auf Testset Z."

---

## IX. Data-Driven Development (Google's Culture of Metrics)

### Jede Feature-Entscheidung braucht eine Metrik-Hypothese

```
Hypothesis: "Wenn wir das Meeting-Briefing 30 Min früher generieren,
             steigt die open_rate von 45% auf 60%."

Measurement: briefings.delivery_offset_minutes vs. briefings_viewed / briefings_sent

Decision gate: A/B-Test über 2 Wochen, min. 100 Nutzer per Arm
```

### Feature Flags als A/B-Testing-Infrastruktur

Der Feature-Flag-Service (bereits aktiv) kann für kontrollierte Experimente genutzt werden.
Kein Feature ship ohne:

- Baseline-Metrik vor dem Deploy
- Expected Impact (quantifiziert)
- Success-Metrik nach dem Deploy

---

## X. Documentation as Code (Google's Engineering Docs Standards)

### Versionierte Dokumentation (nicht nur ADRs)

| Dokument-Typ                 | Speicherort                     | Wann erstellen?                   |
| ---------------------------- | ------------------------------- | --------------------------------- |
| Architecture Decision Record | `docs/adr/NNN-<slug>.md`        | Bei jeder Architekturentscheidung |
| Runbook                      | `docs/runbooks/<service>.md`    | Bei jedem neuen Job/Endpunkt      |
| Post-Mortem                  | `docs/internal/postmortems/`    | Nach jedem Vorfall                |
| API Changelog                | `CHANGELOG.md`                  | Bei jeder Route-Änderung          |
| OpenAPI Examples             | FastAPI route `openapi_extra`   | Bei jeder neuen Route             |
| Eval Results                 | `docs/evals/<feature>/results/` | Nach jedem LLM-Eval-Lauf          |

### "Docs rot" vermeiden (Apple's internal documentation discipline)

- Veraltete Docs sind schlechter als keine Docs.
- Wenn Code geändert wird → zugehörige Docs im selben PR aktualisieren.
- TODO-Kommentare im Code: immer mit `TASK-NNN` oder `# TODO(owner): ...` referenziert.

---

## XI. Portfolio-Signale für Big-Tech-Recruiter

**Was Google Staff Engineers im Code suchen:**

- Skalierbarkeits-Denken in Kommentaren (z.B. `# O(n*k) – bei >10K docs auf Batch-Cursor umstellen`)
- Defensive Programming ohne Paranoia (Fehler an Systemgrenzen fangen, nicht überall)
- Clean Abstractions (Klassen tun eine Sache, Interfaces sind schmal)
- Verständnis von Konsistenz-Trade-offs (eventual vs. strong, dokumentiert)

**Was Apple Engineers im Code suchen:**

- Privacy-impact in Kommentaren bei Daten-Erhebung
- API-Minimalism (jeder public Parameter ist notwendig oder existiert nicht)
- "It just works" ohne Konfiguration (sane defaults, progressive disclosure)

**Was OpenAI Engineers im Code suchen:**

- Safety-Awareness bei LLM-Calls (Grounding, kein freies Prompt-Format)
- Eval-First statt Ship-First bei ML-Features
- Strukturiertes Experiment-Logging (was wurde getestet, was hat nicht funktioniert)
- Transparenz über Modell-Grenzen in Kommentaren und Docs

---

## XII. Code-Qualitäts-Metriken (automatisch validiertent)

### Pflicht-Gates vor jedem Commit

```bash
# Python
ruff check .                    # Linting (Google Style + PEP 8)
mypy pwbs/ --strict             # Type Checking (keine impliziten Any)
pytest tests/unit/ --cov=pwbs   # Unit Tests mit Coverage (Ziel: ≥85%)

# TypeScript
tsc --noEmit                    # Type Checking
eslint src/ --max-warnings 0    # Linting (0 Warnings erlaubt)
vitest run                      # Unit Tests
```

### Complexity-Budget (Google's readability standards)

- **Cyclomatic Complexity** pro Funktion: max. 10
- **Function length**: max. 50 LOC (Ausnahmen dokumentieren)
- **Class cohesion**: Eine Klasse = ein Concern. God Classes vermeiden.
- **Nesting depth**: max. 3 Ebenen (dann Extraktion oder Early-Return)

```python
# Anti-Pattern (nesting depth 4):
if user:
    if user.is_active:
        if connector:
            if connector.is_authorized:
                return fetch_data()

# Big Tech Pattern (early return, flat):
if not user or not user.is_active:
    raise HTTPException(status_code=403, detail={"code": "USER_INACTIVE"})
if not connector or not connector.is_authorized:
    raise HTTPException(status_code=401, detail={"code": "CONNECTOR_UNAUTHORIZED"})
return fetch_data()
```
