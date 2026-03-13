---
agent: agent
description: Debugging-Workflow für PWBS-Agenten. Analysiert Logs, Traces und Datenbankzustände um Fehler in der Ingestion-, Processing- oder Briefing-Pipeline zu diagnostizieren.
tools:
  - codebase
  - runCommands
  - problems
---

# Agenten-Debugging

**Betroffener Agent/Bereich:** ${input:agent:Welcher Agent oder Bereich ist betroffen? z.B. "IngestionAgent/Notion", "BriefingAgent/morning", "ProcessingAgent/embedding"}

**Fehlerbeschreibung:** ${input:error:Kurze Beschreibung des Problems oder Fehlermeldung}

## Phase 0: Hypothesen-Analyse (Extended Thinking)

Vor den Diagnose-Schritten: Alle pläusiblen Ursachen ranken und priorisieren.

| Rang | Hypothese | Wahrscheinlichkeit | Falsifizierbar durch |
|------|-----------|-------------------|---------------------|
| 1 | ... | Hoch/Mittel/Niedrig | ... |
| 2 | ... | ... | ... |

Typische Ursachen-Kategorien:
- **Zustandsproblem:** Cursor korrupt, abgelaufener OAuth-Token, inkonsistente DB-Daten
- **Netzwerk/API:** Rate-Limit, Timeout, API-Schema-Änderung beim Quell-System
- **Normalisierungsfehler:** Unerwartetes Datenformat in Rohdaten vom Connector
- **Idempotenz-Verletzung:** Duplikat-Insert, fehlender Upsert
- **Typ-Fehler:** Pydantic-Validierungsfehler durch neues Feld in API-Response
- **Concurrency:** Doppelter Job-Start, Race Condition beim Cursor-Update

### 1. Logs analysieren

Suche nach relevanten Fehlern in den Logs:

```bash
# Strukturierte Logs nach Agent und Fehlertyp filtern
grep -r "${input:agent:agent}" logs/ | grep -i "error\|exception\|failed"
```

Achte auf:

- Stack-Traces mit konkreten Fehlermeldungen
- `source_id` und `owner_id` der fehlgeschlagenen Operationen
- Zeitstempel und Häufigkeit der Fehler

### 2. Datenbankzustand prüfen

Prüfe den Connector-/Job-Zustand:

```sql
-- Letzter bekannter guter Cursor
SELECT connector_type, cursor, last_sync_at, status, error_message
FROM connector_states
WHERE owner_id = '[user_id]'
ORDER BY last_sync_at DESC;

-- Fehlgeschlagene Jobs
SELECT job_id, status, started_at, finished_at, error
FROM scheduler_job_runs
WHERE status = 'failed'
ORDER BY started_at DESC LIMIT 20;
```

### 3. Idempotenz-Prüfung

Bei Duplikat-Fehlern:

```sql
-- Duplikate in documents prüfen
SELECT source_id, owner_id, COUNT(*)
FROM documents
GROUP BY source_id, owner_id
HAVING COUNT(*) > 1;
```

### 4. Quellcode analysieren

Lies relevante Implementierungsdateien:

- Agent-Klasse in `pwbs/{connector_name}/`
- Fehlerbehandlung in `pwbs/core/exceptions.py`
- Retry-Logik in `pwbs/core/retry.py`

### 5. Fix-Strategie

Basierend auf der Diagnose:

- **Cursor-Korruption:** Cursor zurücksetzen auf letzten validen Stand, nicht auf Null
- **Rate-Limit-Fehler:** Backoff-Konfiguration prüfen, ggf. Batch-Größe reduzieren
- **Normalisierungsfehler:** Beispiel-Rohdaten des Fehlerfalles extrahieren und Test schreiben
- **Duplikate:** Upsert-Logik prüfen, Hash-Funktion für Dedup-Schlüssel kontrollieren

### 6. Präventive Maßnahmen

Nach dem Fix:

- [ ] Reproduzierenden Unit-Test schreiben
- [ ] Cursor-Validierung stärken falls nötig
- [ ] Alerting-Threshold anpassen falls zu sensitiv/insensitiv

### 7. Abschluss-Report

Strukturierten Abschluss-Report erstellen:

```markdown
## Debug-Report: [Agent] – [Datum]

**Root Cause:** ...
**Betroffene Dokumente/Nutzer:** ...
**Fix angewendet:** ...
**Präventionsmaßnahme:** ...
**Neuer Test:** tests/.../test_...py
```
