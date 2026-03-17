---
applyTo: ".github/prompts/audit-*.prompt.md"
---

# Audit-Instruktionen: Gemeinsame Prinzipien für alle Audit-Prompts

## Fundamentalprinzip: Zustandslose Frische

Jeder Audit-Prompt operiert bei **jeder Ausführung** so, als würde er den Workspace zum ersten Mal sehen:

- Keine Annahmen über vorherige Audit-Läufe
- Kein „gut genug"-Zustand akzeptieren
- Jede Schicht von Grund auf neu analysieren
- Die Analysekraft ist unabhängig davon, wie oft der Prompt bereits ausgeführt wurde

## Robustheitsregeln (vor jeder Aktion anwenden)

1. **Existenzprüfung:** Prüfe vor jedem Dateizugriff, ob Datei/Verzeichnis existiert. Passe dein Vorgehen dynamisch an den tatsächlichen Workspace-Zustand an.

2. **Plattform-Awareness:** Verwende plattformgerechte Shell-Befehle (PowerShell auf Windows, Bash auf Linux/macOS). Shell-Beispiele in Prompts sind Pseudo-Code.

3. **Adaptive Tiefe:** Überspringe Audit-Bereiche, für die noch keine Artefakte existieren – dokumentiere diese als „Aufbaupotenzial". Falls ein Bereich bereits auf hohem Niveau ist, suche nach Verfeinerungen auf der nächsten Qualitätsstufe.

4. **MVP-Scope (ADR-016):** Berücksichtige den aktuellen Projektstand. Deaktivierte Module in `backend/_deferred/` NICHT analysieren oder bemängeln. Kern-4-Konnektoren (Google Calendar, Notion, Zoom, Obsidian) sind aktiv. Neo4j ist optional.

5. **Keine Halluzinationen:** Analysiere nur Code, der existiert. Vermutete Probleme sind keine Findings – nur nachweisbare.

## Phase-0-Inventar-Pattern

Jeder Audit beginnt mit einer Zustandserfassung:

```markdown
### Phase 0: Inventar (Extended Thinking)

Bevor du analysierst, erfasse den **exakten aktuellen Zustand**:

1. **Was existiert tatsächlich?** Lies Verzeichnisstruktur und Dateien.
2. **Was ist implementiert vs. Stub?** Unterscheide echten Code von `__init__.py`-only.
3. **Welche Konfigurationen gelten?** Lies pyproject.toml, package.json, etc.
4. **Welcher Reifegrad?** Foundation → Aufbau → Reifung → Optimierung

Erstelle ein internes Zustandsbild, bevor du Findings generierst.
```

## Priorisierungs-Schema

Alle Findings werden nach diesem Schema klassifiziert:

| Prio | Label           | Kriterium                         | Aktion          |
| ---- | --------------- | --------------------------------- | --------------- |
| 🔴   | Kritisch        | Sicherheit, DSGVO, Breaking Bugs  | Sofort beheben  |
| 🟡   | Wichtig         | Qualität, Performance, Robustheit | Nächster Sprint |
| 🟢   | Nice-to-have    | Verfeinerungen, Optimierungen     | Backlog         |
| 🔵   | Aufbaupotenzial | Noch nicht existierende Bereiche  | Dokumentieren   |

**Sortierung:** Kritische Sicherheits- und DSGVO-Probleme immer zuerst, dann nach Impact/Aufwand-Verhältnis.

## Output-Format

Jeder Audit endet mit einem strukturierten Bericht:

```markdown
# [Audit-Typ]-Bericht – [Datum]

## Zustandsbild

[Reifegrad-Tabelle oder Inventar-Zusammenfassung]

## Findings

### 🔴 Kritisch

| #   | Finding | Betroffene Datei | Empfehlung |
| --- | ------- | ---------------- | ---------- |

### 🟡 Wichtig

...

### 🟢 Nice-to-have

...

### 🔵 Aufbaupotenzial

...

## Durchgeführte Fixes

[Liste der in diesem Audit behobenen Probleme]

## Nächste Schritte

[Priorisierte Empfehlungen für Follow-up]
```

## Opus 4.6 – Kognitive Verstärker

Audits nutzen Extended Thinking für:

- **Multi-Schritt-Reasoning:** Komplexe Probleme in Teilschritte zerlegen
- **Perspektiven-Wechsel:** Problem aus Entwickler-, Nutzer-, Security-Sicht betrachten
- **Kontra-Analyse:** Gegenargumente für eigene Empfehlungen formulieren
- **Kausalketten:** Jedes Problem bis zur Root Cause verfolgen
- **Zukunftsprojektion:** Auswirkungen auf spätere Phasen antizipieren

## PWBS-spezifische Prüfpunkte (immer anwendbar)

### DSGVO-Grundprüfung

- [ ] `owner_id` in allen nutzerbezogenen Datenstrukturen
- [ ] `expires_at` für PII-Daten
- [ ] Keine PII in Logs
- [ ] Löschkaskade implementiert

### Idempotenz-Grundprüfung

- [ ] DB-Writes als UPSERT/MERGE
- [ ] Cursor/Watermark-Persistierung
- [ ] Pipeline bei Neustart ohne Datenverlust

### Erklärbarkeits-Grundprüfung

- [ ] `sources: list[SourceRef]` bei allen LLM-Outputs
- [ ] Fakten vs. Interpretationen trennbar

### Code-Qualitäts-Grundprüfung

- [ ] Vollständige Type Annotations
- [ ] Keine `# TODO: implement` Platzhalter
- [ ] `async def` für I/O-Operationen
