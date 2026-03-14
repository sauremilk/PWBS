## Beschreibung

<!-- Was wurde geändert und warum? Referenziere die TASK-ID. -->

**TASK-ID:** TASK-XXX
**Typ:** feat / fix / refactor / perf / docs / security
**Stream:** STREAM-XXX (falls zutreffend)

### Änderungen

- ...

### Motivation

<!-- Warum ist diese Änderung notwendig? Welches Problem wird gelöst? -->

---

## Verknüpfte Dokumente

- **ADR:** docs/adr/XXX-...md (falls relevant)
- **Architektur:** ARCHITECTURE.md §X.X (falls relevant)
- **PRD:** PRD-SPEC.md §FR-XXX (falls relevant)

---

## Checkliste

### Code-Qualität

- [ ] Vollständige Type Annotations (Python: kein `Any`, TypeScript: kein implizites `any`)
- [ ] Conventional Commit Message(s) mit TASK-ID
- [ ] Ein Commit = eine logische Änderung

### Tests

- [ ] Neue Funktionalität hat Unit-Tests
- [ ] Bestehende Tests nicht gebrochen
- [ ] Integration-Tests für DB-Operationen (falls zutreffend)

### DSGVO (falls Nutzer-Daten betroffen)

- [ ] `owner_id`-Filter in allen DB-Queries
- [ ] `expires_at` bei neuen Datenstrukturen
- [ ] Lösch-Kaskade implementiert (Art. 17)
- [ ] Keine PII in Logs oder Fehlermeldungen
- [ ] LLM-Prompts enthalten keine unnötigen personenbezogenen Daten

### Sicherheit (falls Auth/Crypto/API betroffen)

- [ ] Input-Validierung mit Pydantic
- [ ] Keine SQL-Injection (parameterisierte Queries)
- [ ] Keine Secrets im Code
- [ ] OWASP Top 10 geprüft

### Idempotenz (falls Schreiboperationen)

- [ ] Writes als Upsert (nicht blindes INSERT)
- [ ] Konnektoren mit Cursor/Watermark

### Erklärbarkeit (falls LLM-Ausgaben)

- [ ] `sources: list[SourceRef]` in LLM-Responses
- [ ] Keine Halluzinationen ohne Kennzeichnung

---

## Screenshots / Logs

<!-- Falls relevant: Screenshots der UI-Änderung oder relevante Log-Ausgaben -->

---

## Breaking Changes

<!-- Falls zutreffend: Was bricht? Wie migrieren bestehende Clients? -->

- [ ] **Kein Breaking Change**
- [ ] Breaking Change — Migrationsanleitung:
