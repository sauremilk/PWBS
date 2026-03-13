---
agent: agent
description: Führt einen umfassenden Architektur-Review für ein PWBS-Modul oder Feature durch. Prüft auf Verstöße gegen die Designprinzipien, Sicherheitslücken und Verbesserungspotenzial.
tools:
  - codebase
  - problems
---

# Architektur-Review

**Zu überprüfendes Modul/Feature:** ${input:module:Modulpfad oder Feature-Name, z.B. "pwbs/connectors/" oder "Briefing-Pipeline"}

## Phase 0: Vorbereitende Tiefenanalyse (Extended Thinking)

Bevor du mit dem Review beginnst, analysiere stil intern:

1. **Transitive Abhängigkeiten:** Welche Module hängen direkt oder transitiv von `${input:module:module}` ab? Gibt es zirkuläre Imports?
2. **Verborgene DSGVO-Risiken:** Welche Daten fließen durch das Modul, die nicht unmittelbar als PII erkennbar sind (z.B. Kalender-IDs, IP-Adressen in Logs)?
3. **Lastszenario-Schwachstellen:** Was passiert, wenn 1000 Dokumente gleichzeitig ingested werden? Gibt es Bottlenecks, N+1-Queries oder Memory-Leaks?
4. **Angriffsflächen:** Welche Inputs können von externen Quellen kontrolliert werden? Sind diese vollständig validiert?
5. **State-Konsistenz-Szenarien:** Was passiert, wenn der Prozess während Phase 2 von 3 einer Pipeline abstürzt?

## Review-Checkliste

### 1. Architekturprinzipien

**DSGVO by Design**

- [ ] Jedes Datum hat `owner_id`, `expires_at` und kann gelöscht werden
- [ ] Keine PII in Logs
- [ ] Nutzerdaten-Trennung auf DB-Ebene (`WHERE owner_id = ...` in jeder Query)
- [ ] Kein LLM-Training mit Nutzerdaten

**Erklärbarkeit**

- [ ] LLM-Outputs enthalten `sources: list[SourceRef]`
- [ ] Fakten und Interpretationen sind trennbar
- [ ] Keine stillen Halluzinationen möglich

**Idempotenz**

- [ ] Upsert-Patterns in DB-Writes (kein blindes INSERT)
- [ ] Cursor/Watermark persistent gespeichert
- [ ] Pipeline kann ohne Datenverlust neu gestartet werden

**Modularität**

- [ ] Keine zirkulären Imports zwischen Modulen
- [ ] Nur über definierte Python-Interfaces kommuniziert (kein HTTP im MVP)
- [ ] Externe Abhängigkeiten via Dependency Injection injiziert

### 2. Code-Qualität

**Python**

- [ ] Vollständige Type Annotations (kein implizites `Any`)
- [ ] Pydantic v2 Patterns (kein veraltetes `class Config`)
- [ ] `async def` für alle I/O-Operationen
- [ ] Eigene Exception-Klassen (`PWBSError`-Hierarchie)

**Sicherheit (OWASP)**

- [ ] Keine SQL-Injection-Risiken (parametrisierte Queries)
- [ ] Kein SSRF-Risiko (URL-Validierung für Webhooks)
- [ ] Keine Secrets im Code
- [ ] Input-Validierung mit Pydantic

### 3. Testabdeckung

- [ ] Unit-Tests für Business-Logik vorhanden
- [ ] Keine echten Netzwerkzugriffe in Unit-Tests
- [ ] Happy-Path + Fehlerfall getestet
- [ ] Idempotenz explizit getestet

### 4. Performance

- [ ] N+1-Query-Probleme identifiziert
- [ ] Embedding-Batching implementiert (nicht einzeln pro Dokument)
- [ ] Keine synchronen Blocking-Operationen in async Kontext

## Output-Format

Erstelle einen strukturierten Review-Report:

```markdown
## Architektur-Review: [Modulname]

### Kritische Probleme (Must-Fix, blockiert Deployment)

| # | Problem | Betroffene Datei | Empfehlung |
|---|---------|-----------------|------------|
| 1 | ... | ... | ... |

### Wichtige Probleme (Should-Fix, nächster Sprint)

...

### Verbesserungsvorschläge (Nice-to-Have)

...

### DSGVO-Bewertung

- Mandanten-Isolation: [OK / RISIKO: ...]
- Löschbarkeit: [OK / OFFEN: ...]
- Logging-Hygiene: [OK / BEFUND: ...]

### Idempotenz-Bewertung

- Cursor-Persistenz: [OK / FEHLT: ...]
- Upsert-Patterns: [OK / FEHLT IN: ...]

### Sicherheitsbewertung (OWASP)

- Injection-Risiken: [Keine / BEFUND: ...]
- SSRF-Risiken: [Keine / BEFUND: ...]
- Auth/Autorisierung: [OK / Lücke: ...]
```

### Verbesserungsvorschläge (Should-Fix)

...

### Positive Aspekte

...

### Empfohlene nächste Schritte

...
```

Für jedes gefundene Problem: Zeige den problematischen Code, erkläre das Problem und schlage einen konkreten Fix vor.
