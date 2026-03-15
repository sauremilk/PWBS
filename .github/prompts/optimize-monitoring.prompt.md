---
agent: agent
description: "Tiefenoptimierung der Monitoring-, Logging- und Observability-Strategie im PWBS-Workspace. Analysiert strukturiertes Logging, Health-Checks, Metriken, Alerting und Tracing – zustandsunabhängig bei jeder Ausführung."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Monitoring- und Observability-Optimierung

> **Fundamentalprinzip: Zustandslose Frische**
>
> Observability-Konfigurationen und Logging-Patterns veralten mit jedem neuen Feature. Bei jeder Ausführung alle Monitoring-bezogenen Aspekte von Grund auf analysieren. Keine Annahmen über vorherige Audits.

> **Robustheitsregeln:**
>
> - Prüfe, welche Logging- und Monitoring-Infrastruktur tatsächlich existiert.
> - Bei fehlendem Monitoring: Identifiziere als Aufbaupotenzial mit konkretem Vorschlag, nicht als Fehler.
> - Berücksichtige den MVP-Kontext (Phase 2) – strukturiertes Logging und Health-Checks sind Pflicht, APM-Tooling ist Nice-to-have.
> - Plattformgerechte Befehle verwenden.

---

## Phase 0: Monitoring-Inventar (Extended Thinking)

### 0.1 Logging-Infrastruktur kartieren

| Aspekt | Aktueller Stand | Bewertung |
|--------|----------------|-----------|
| Logging-Framework | `logging` / `structlog` / `loguru` / keins | ... |
| Log-Format | JSON / Text / Gemischt | ... |
| Log-Level-Konfiguration | Zentral / Pro-Modul / Hardcodiert | ... |
| Correlation-ID / Request-ID | Implementiert / Fehlt | ... |
| PII-Filter im Logging | Aktiv / Fehlt | ... |

### 0.2 Health- und Readiness-Checks

| Endpunkt | Existiert? | Prüft was? |
|----------|-----------|------------|
| `/health` oder `/healthz` | ... | Prozess lebt |
| `/ready` oder `/readyz` | ... | DB, Weaviate, Neo4j erreichbar |
| `/metrics` | ... | Prometheus-kompatible Metriken |

### 0.3 Metriken und Alerting

- [ ] Metriken-Export (Prometheus, StatsD, CloudWatch)
- [ ] Alerting-Regeln definiert
- [ ] Dashboard-Konfiguration (Grafana, CloudWatch)

---

## Phase 1: Strukturiertes Logging

### 1.1 Log-Format-Analyse

Durchsuche alle `logger.*`-, `logging.*`- und `print()`-Aufrufe:

- [ ] **Einheitliches Format:** Alle Log-Ausgaben als strukturiertes JSON (nicht Freitext)
- [ ] **Kontextfelder:** `request_id`, `owner_id` (anonymisiert), `module`, `operation` in jedem Log-Eintrag
- [ ] **Log-Level-Konsistenz:** DEBUG für Details, INFO für Geschäftsereignisse, WARNING für Degradation, ERROR für Fehler, CRITICAL für Systemausfälle
- [ ] **Keine PII in Logs:** Suche nach `logger.*` mit E-Mail, Namen, Token-Werten, Content-Feldern

```python
# SCHLECHT – PII und unstrukturiert:
logger.info(f"User {email} searched for '{query}'")

# GUT – strukturiert und PII-frei:
logger.info("search_executed", extra={"owner_id": owner_id, "result_count": len(results), "latency_ms": elapsed})
```

### 1.2 Logging-Konfiguration

- [ ] **Zentralisierte Konfiguration:** Ein `logging_config.py` oder `structlog`-Setup statt verteilte Konfiguration
- [ ] **Umgebungsabhängig:** JSON-Logs in Production, Human-Readable in Development
- [ ] **Log-Rotation:** Konfiguriert für File-basiertes Logging (falls relevant)
- [ ] **Externe Log-Aggregation-Readiness:** Logs an stdout/stderr für Container-Logging

### 1.3 PII-Scrubbing

Prüfe systematisch:

```python
# SUCHE NACH:
logger.info(f"User {email}")              # ← PII!
logger.debug(f"Content: {content}")        # ← Potenziell PII!
logger.error(f"Token: {token}")            # ← Secret!
logger.warning(f"Query: {user_query}")     # ← Nutzerinhalt!
print(user_data)                           # ← PII in stdout!
```

---

## Phase 2: Health-Checks und Readiness

### 2.1 Liveness-Probe

- [ ] `/health`-Endpunkt existiert und antwortet mit `200 OK` + JSON-Body
- [ ] Keine schweren Operationen im Health-Check (kein DB-Query)
- [ ] Timeout < 1s

### 2.2 Readiness-Probe

- [ ] `/ready`-Endpunkt prüft alle kritischen Abhängigkeiten:
  - PostgreSQL-Verbindung
  - Weaviate-Verbindung (falls konfiguriert)
  - Neo4j-Verbindung (falls konfiguriert)
  - Redis-Verbindung (falls konfiguriert)
- [ ] Antwort enthält Status pro Abhängigkeit:

```json
{
  "status": "healthy",
  "dependencies": {
    "postgresql": {"status": "up", "latency_ms": 2},
    "weaviate": {"status": "up", "latency_ms": 15},
    "neo4j": {"status": "degraded", "error": "connection timeout"}
  }
}
```

### 2.3 Startup-Probe

- [ ] Migrations-Status prüfbar
- [ ] Konfiguration validiert beim Start (fail-fast bei fehlenden Env-Vars)

---

## Phase 3: Metriken

### 3.1 Business-Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|-------------|
| `pwbs_ingestion_documents_total` | Counter | `source`, `status` | Ingested Dokumente |
| `pwbs_search_queries_total` | Counter | `mode`, `owner_id_hash` | Suchanfragen |
| `pwbs_briefing_generations_total` | Counter | `type`, `status` | Generierte Briefings |
| `pwbs_search_latency_seconds` | Histogram | `mode` | Such-Latenz |
| `pwbs_llm_calls_total` | Counter | `provider`, `status` | LLM-API-Aufrufe |
| `pwbs_llm_latency_seconds` | Histogram | `provider` | LLM-Latenz |
| `pwbs_llm_tokens_total` | Counter | `provider`, `direction` | Verbrauchte Tokens |

### 3.2 Infrastruktur-Metriken

- [ ] DB Connection Pool: Aktive/Wartende/Maximale Verbindungen
- [ ] Request-Latenz (P50, P95, P99) pro Endpunkt
- [ ] Error-Rate pro Endpunkt
- [ ] Queue-Tiefe (Celery, falls aktiv)

### 3.3 DSGVO-Metriken

- [ ] `pwbs_data_expired_total` – Abgelaufene Datensätze (für Cleanup-Monitoring)
- [ ] `pwbs_data_deletion_requests_total` – DSGVO-Löschanfragen
- [ ] `pwbs_data_deletion_latency_seconds` – Dauer einer vollständigen Löschung

---

## Phase 4: Request-Tracing

### 4.1 Correlation-ID

- [ ] Jeder eingehende Request erhält eine unique `X-Request-ID`
- [ ] ID wird durch alle Agenten-Aufrufe durchgereicht
- [ ] ID erscheint in jedem Log-Eintrag des Request-Pfads
- [ ] FastAPI-Middleware generiert/propagiert die ID

### 4.2 Distributed Tracing (Phase 3 Readiness)

- [ ] OpenTelemetry-Integration vorbereitet (Instrumentierung-Hooks vorhanden)
- [ ] Span-Annotationen an kritischen Operationen (DB-Queries, LLM-Calls, externe APIs)
- [ ] Trace-Context-Propagation zwischen Modulen

---

## Phase 5: Alerting-Strategie

### 5.1 Kritische Alerts (sofortige Benachrichtigung)

| Alert | Bedingung | Konsequenz |
|-------|-----------|------------|
| API Down | Health-Check fehlgeschlagen > 3x | System nicht erreichbar |
| DB Connection Exhausted | Pool > 90% ausgelastet > 5min | Requests scheitern |
| LLM-API-Fehler | Error-Rate > 50% über 5min | Briefings/Suche degradiert |
| Ingestion gestoppt | 0 Dokumente in > 2h (Werktag) | Daten veralten |

### 5.2 Warn-Alerts (nächster Arbeitstag)

| Alert | Bedingung | Konsequenz |
|-------|-----------|------------|
| Hohe Latenz | P95 > 2s über 15min | UX-Degradation |
| DSGVO-Cleanup verzögert | Abgelaufene Daten > 24h nicht gelöscht | Compliance-Risiko |
| Token-Budget | LLM-Kosten > Tageslimit | Budgetüberschreitung |

---

## Phase 6: Optimierungen implementieren

Für jedes Finding:

1. **Bewerte:** Sicherheit/Compliance > Betreibbarkeit > Beobachtbarkeit > Nice-to-have
2. **Priorisiere:** PII-in-Logs und fehlende Health-Checks zuerst
3. **Implementiere:** Vollständige Fixes, keine Platzhalter
4. **Validiere:** Logging-Format prüfen, Health-Check testen

---

## Phase 7: Monitoring-Bericht

```markdown
# Monitoring-Bericht – [Datum]

## Observability-Reifegrad

| Aspekt | Score (1-5) | Nächster Schritt |
|--------|-------------|-----------------|
| Strukturiertes Logging | ... | ... |
| Health-Checks | ... | ... |
| Metriken | ... | ... |
| Tracing | ... | ... |
| Alerting | ... | ... |
| PII-Scrubbing | ... | ... |

## Durchgeführte Verbesserungen

1. ...

## Empfehlungen

1. ...
```

---

## Opus 4.6 – Kognitive Verstärker

- **Perspektiven-Wechsel:** Bewerte Observability aus Sicht des Entwicklers (Debugging), des Ops-Teams (Alerting), des Datenschutzbeauftragten (PII in Logs) und des Endnutzers (Latenz-Erkennung).
- **Kausalketten:** Verfolge jeden Incident-Pfad: Wie würde ein Ausfall erkannt? Wie lange dauert es von Symptom zu Root Cause? Wo sind blinde Flecken?
- **Muster-Erkennung:** Identifiziere systematische Lücken – fehlt Logging konsistent in bestimmten Modulen? Werden bestimmte Fehlerklassen nie geloggt?
- **Zukunftsprojektion:** Welche Monitoring-Lücken werden beim Übergang zu Phase 3 (Multi-Service) kritisch?
