---
agent: agent
description: Nutzt Claude Opus 4.6 Extended Thinking für komplexe Multi-Schritt-Analysen, Architekturentscheidungen und tiefes systematisches Durchdenken von PWBS-Problemen.
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Extended Thinking: Tiefenanalyse

**Analysegegenstand:** ${input:subject:Was soll tiefgehend analysiert werden? z.B. "Skalierbarkeit der Ingestion-Pipeline", "Sicherheitsaudit OAuth-Flow", "Datenbankschema-Konsistenz"}

**Analyseziel:** ${input:goal:Was ist das konkrete Ziel der Analyse? z.B. "Engpässe identifizieren", "Sicherheitslücken aufdecken", "Optimierungsempfehlungen ableiten"}

---

## Struktur der Tiefenanalyse

### Schritt 1: Problem-Dekomposition

Zerlege `${input:subject:subject}` in atomare Teilprobleme:

1. Welche Subsysteme und Module sind direkt beteiligt?
2. Welche Datenflüsse laufen durch diese Subsysteme?
3. Welche externen Abhängigkeiten (APIs, DBs, LLMs) spielen eine Rolle?
4. Welche zeitlichen oder ressourcentechnischen Constraints gelten?

### Schritt 2: Lösungsraum kartieren

Formuliere **mindestens drei** konzeptionell unterschiedliche Lösungsansätze:

| Ansatz | Kernidee | Vorteile | Nachteile | Risiken |
|--------|----------|----------|-----------|---------|
| A | ... | ... | ... | ... |
| B | ... | ... | ... | ... |
| C | ... | ... | ... | ... |

Bewerte jeden Ansatz gegen:
- DSGVO-Compliance (owner_id, expires_at, Löschbarkeit)
- Idempotenz-Garantie
- Modularer Monolith – kein HTTP zwischen Modulen im MVP
- Testbarkeit (mockbare Abhängigkeiten)
- Erklärbarkeit aller LLM-Ausgaben

### Schritt 3: Interaktionsanalyse

Modelliere die Auswirkungen des gewählten Ansatzes auf andere Systemkomponenten:

```
Betroffene Agenten:
  IngestionAgent: [keine / Änderung: ...]
  ProcessingAgent: [keine / Änderung: ...]
  BriefingAgent: [keine / Änderung: ...]
  SearchAgent: [keine / Änderung: ...]
  GraphAgent: [keine / Änderung: ...]
  SchedulerAgent: [keine / Änderung: ...]

Breaking Changes:
  API-Kontrakte: [keine / ...]
  Datenbankschema: [keine / Migration notwendig: ...]
  Connector-Interface: [keine / ...]
```

### Schritt 4: Risiko- und Sicherheitsanalyse

Für den gewählten Ansatz:

**DSGVO-Risiken:**
- [ ] Neue PII-Felder ohne `expires_at`?
- [ ] Cross-User-Datenlecks möglich?
- [ ] LLM-Calls mit Nutzerdaten: Training-Opt-Out konfiguriert?

**Sicherheitsrisiken (OWASP):**
- [ ] Neue Injection-Vektoren (SQL, Cypher, Command)?
- [ ] SSRF durch neue externe HTTP-Calls?
- [ ] Auth-Bypass bei neuen Endpunkten möglich?
- [ ] Secrets versehentlich in Logs oder Responses?

**Architekturrisiken:**
- [ ] Zirkuläre Abhängigkeiten eingeführt?
- [ ] Synchroner Blocking-Code in async Kontext?
- [ ] Ungetestete Fehlerszenarien (DB-Down, LLM-Timeout)?

### Schritt 5: Implementierungsplan

Strukturierter Plan für den empfohlenen Ansatz:

```markdown
## Implementierungsplan

### Phase 1: Fundament (keine Breaking Changes)
1. [ ] ...
2. [ ] ...

### Phase 2: Kernimplementierung
1. [ ] ...
2. [ ] ...

### Phase 3: Integration & Tests
1. [ ] Unit-Tests für neue Logik
2. [ ] Idempotenz-Test: Zweifacher Aufruf = identisches Ergebnis
3. [ ] DSGVO-Test: Delete-Cascade funktioniert korrekt

### Rollback-Strategie
Falls Phase 2 fehlschlägt: [konkreter Rollback-Plan]
```

### Schritt 6: Entscheidung und Begründung

**Empfohlener Ansatz:** [A / B / C]

**Begründung in drei Sätzen:**
1. [Fachliche Begründung]
2. [Technische Begründung]
3. [Risiko-Begründung]

**Nicht gewählte Ansätze – warum verworfen:**
- Ansatz X: [Ablehnungsgrund]
- Ansatz Y: [Ablehnungsgrund]

---

## ADR erstellen?

Falls die Entscheidung architektonisch bedeutsam ist (betrifft > 1 Modul oder setzt einen Präzedenzfall), erstelle ein ADR unter `docs/adr/`:

```bash
# ADR-Nummer prüfen
ls docs/adr/ | tail -1

# ADR erstellen
cp docs/adr/000-template.md docs/adr/NNN-${input:subject:subject|slugify}.md
```
