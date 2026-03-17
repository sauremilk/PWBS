---
agent: agent
description: "Tiefenanalyse für komplexe Multi-Schritt-Probleme. Aktiviert systematisches Reasoning mit Extended Thinking für Architekturentscheidungen, Debugging und Trade-off-Analysen."
tools:
  - codebase
  - editFiles
  - problems
  - runCommands
---

# Tiefenanalyse

Du führst eine systematische Tiefenanalyse für ein komplexes Problem durch.

**Gegenstand:** ${input:subject:Was soll analysiert werden? z.B. "Skalierbarkeit der Ingestion-Pipeline", "OAuth-Token-Rotation-Bug"}
**Ziel:** ${input:goal:Konkretes Analyseziel: z.B. "Engpässe identifizieren", "Root Cause finden", "Architekturentscheidung treffen"}
**Typ:** ${input:type:architecture / debugging / trade-off / security / performance}

---

## Reasoning-Protokoll

### Schritt 1: Problem-Dekomposition

Zerlege **${input:subject}** in atomare Teilfragen (max. 7):

| #   | Teilfrage | Warum relevant? | Wie beantwortbar? |
| --- | --------- | --------------- | ----------------- |
| 1   |           |                 |                   |
| 2   |           |                 |                   |
| 3   |           |                 |                   |
| ... |           |                 |                   |

Jede Teilfrage muss:

- Konkret und falsifizierbar sein
- Unabhängig von anderen Teilfragen beantwortbar sein
- Zum Gesamtziel **${input:goal}** beitragen

---

### Schritt 2: Kontext sammeln

Für jede Teilfrage relevanten Kontext laden:

**Code:**

- Betroffene Module/Dateien identifizieren
- Relevante Implementierungen lesen
- Abhängigkeiten und Datenflüsse verstehen

**Dokumentation:**

- ARCHITECTURE.md, AGENTS.md, ADRs prüfen
- Bestehende Entscheidungen verstehen
- Constraints und Prinzipien identifizieren

**Zustand:**

- Aktueller Implementierungsgrad
- Bekannte Probleme (`problems`-Tool)
- Letzte relevante Änderungen (`git log`)

---

### Schritt 3: Lösungsraum kartieren

Formuliere **mindestens 3** konzeptionell unterschiedliche Ansätze:

| Ansatz | Kernidee | Vorteile | Nachteile | Risiken | Aufwand |
| ------ | -------- | -------- | --------- | ------- | ------- |
| A      |          |          |           |         |         |
| B      |          |          |           |         |         |
| C      |          |          |           |         |         |

**Wichtig:** Kein Ansatz sollte offensichtlich unterlegen sein. Falls doch, ist die Analyse nicht tiefgründig genug.

---

### Schritt 4: Bewertungsmatrix

Bewerte jeden Ansatz gegen PWBS-Prinzipien:

| Kriterium               | Ansatz A | Ansatz B | Ansatz C |
| ----------------------- | -------- | -------- | -------- |
| DSGVO-Compliance        | ✅/⚠️/❌ |          |          |
| Idempotenz-Garantie     |          |          |          |
| Erklärbarkeit           |          |          |          |
| Testbarkeit             |          |          |          |
| Wartbarkeit             |          |          |          |
| Phase-3-Readiness       |          |          |          |
| Performance             |          |          |          |
| Implementierungsaufwand |          |          |          |

---

### Schritt 5: Kontra-Analyse

Für den bevorzugten Ansatz:

**Was könnte schiefgehen?**

1. ...
2. ...
3. ...

**Welche Annahmen sind implizit?**

1. ...
2. ...

**Was würde ein kritischer Reviewer einwenden?**

1. ...

**Unter welchen Umständen wäre ein anderer Ansatz besser?**

- ...

---

### Schritt 6: Empfehlung

**Gewählter Ansatz:** [A/B/C]

**Begründung:**
[2-3 Sätze, die die Entscheidung nachvollziehbar machen]

**Explizite Trade-offs:**
| Akzeptiert | Zugunsten von |
|------------|---------------|
| ... | ... |

**Offene Risiken:**
| Risiko | Mitigationsstrategie |
|--------|---------------------|
| ... | ... |

---

### Schritt 7: Implementierungsplan

| Phase | Aktion | Abhängig von | Aufwand | Validierung |
| ----- | ------ | ------------ | ------- | ----------- |
| 1     |        |              |         |             |
| 2     |        |              |         |             |
| 3     |        |              |         |             |

**Rollback-Strategie:**
Falls die Implementierung scheitert, wie wird zurückgerollt?

**Messpunkte:**
Woran erkennt man, dass die Lösung funktioniert?

---

## Typ-spezifische Erweiterungen

### Bei `type=debugging`:

**Hypothesen-Ranking:**
| Rang | Hypothese | Wahrscheinlichkeit | Falsifizierbar durch |
|------|-----------|-------------------|---------------------|
| 1 | | Hoch/Mittel/Niedrig | |
| 2 | | | |

**Diagnose-Schritte:**

1. Log-Analyse: ...
2. DB-Zustand: ...
3. Code-Inspektion: ...
4. Reproduktion: ...

### Bei `type=security`:

**Threat Model:**
| Akteur | Motivation | Angriffspfad | Impact |
|--------|------------|--------------|--------|

**STRIDE-Analyse:**

- Spoofing: ...
- Tampering: ...
- Repudiation: ...
- Information Disclosure: ...
- Denial of Service: ...
- Elevation of Privilege: ...

### Bei `type=performance`:

**Bottleneck-Hypothesen:**
| # | Komponente | Vermuteter Engpass | Messmethode | Baseline |
|---|------------|-------------------|-------------|----------|

**Optimierungs-Kandidaten:**
| Optimierung | Erwarteter Gewinn | Risiko | Komplexität |
|-------------|-------------------|--------|-------------|

---

## Output

```markdown
# Tiefenanalyse: ${input:subject}

## Zusammenfassung

[1-2 Sätze: Problem, Empfehlung, wichtigster Trade-off]

## Analyse

[Ergebnisse aus Schritten 1-5]

## Empfehlung

[Aus Schritt 6]

## Implementierungsplan

[Aus Schritt 7]

## Offene Fragen

[Falls vorhanden]
```

---

## Opus 4.6 – Kognitive Verstärker

Diese Analyse erfordert Extended Thinking für:

1. **Perspektiven-Wechsel:** Problem aus Dev, User, Ops, Security betrachten
2. **Kontrafaktisches Denken:** Was wäre wenn X nicht gegeben wäre?
3. **Analogie-Suche:** Ähnliche Probleme in anderen Systemen?
4. **Kausalketten:** Symptom → Ursache → Root Cause → Design-Fehler?
5. **Zukunftsprojektion:** Wie skaliert die Lösung über 1/10/100 Nutzer?
