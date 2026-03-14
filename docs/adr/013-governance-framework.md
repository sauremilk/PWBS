# ADR-013: Governance-Framework und Entwicklungsstandards

**Status:** Akzeptiert
**Datum:** 13. März 2026
**Entscheider:** Projektgründer

---

## Kontext

Das PWBS wächst von Phase 1 (PoC) in Phase 2 (MVP) mit bis zu 12 parallelen KI-Orchestratoren. Ohne formalisierte Prozesse für Branching, Commit-Konventionen, Code-Reviews, Task-Lifecycle und Entscheidungsdokumentation drohen Inkonsistenzen, schwer nachvollziehbare Änderungen und Koordinationsfehler zwischen Mensch und KI. Ein verbindliches Entwicklungs-Regelwerk ist Voraussetzung für skalierbare, nachvollziehbare Zusammenarbeit.

---

## Entscheidung

Wir werden ein zentrales Governance-Dokument (`GOVERNANCE.md`) als verbindliches Regelwerk für alle Entwicklungsprozesse etablieren, weil es die einzige Quelle der Wahrheit für Prozessfragen sein soll — sowohl für menschliche Entwickler als auch für KI-Agenten.

---

## Optionen bewertet

| Option                                            | Vorteile                                                                | Nachteile                                                          | Ausschlussgründe                     |
| ------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------ |
| Verstreute Regeln in README, CONTRIBUTING, ADRs   | Dezentral, flexibel                                                     | Inkonsistent, schwer auffindbar, Widersprüche möglich              | Skaliert nicht mit 12 Orchestratoren |
| Wiki-basierte Dokumentation (GitHub Wiki)         | Suchbar, versioniert                                                    | Außerhalb des Repos, nicht in Git-History, nicht im Editor-Kontext | KI-Agenten haben keinen Wiki-Zugriff |
| **Zentrales GOVERNANCE.md + Enforcement-Dateien** | Versioniert im Repo, maschinenlesbar, Pre-Commit-Hooks erzwingen Regeln | Ein großes Dokument, muss gepflegt werden                          | –                                    |

---

## Konsequenzen

### Positive Konsequenzen

- Einheitliche Prozesse für Mensch und KI — gleiche Regeln, gleiche Werkzeuge
- Commits sind durch Conventional Commits maschinenlesbar und automatisch auswertbar
- Code-Reviews haben durch das PR-Template eine standardisierte Checkliste (inkl. DSGVO)
- Trunk-Based Development mit kurzlebigen Branches verhindert divergierende Code-Stänge
- Pre-Commit-Hooks fangen Fehler **vor** dem Commit ab, nicht erst in CI
- ADR-Framework mit Pflichtfeldern (DSGVO, Sicherheit, Revision) verhindert unvollständige Dokumentation
- CHANGELOG.md liefert eine menschenlesbare Änderungshistorie mit TASK-ID-Traceability

### Negative Konsequenzen / Trade-offs

- Overhead: Jeder Commit muss dem Conventional-Commits-Format entsprechen
- Orchetrator-Sonderregeln (direkter Push auf master) weichen vom Standard ab — Risiko bei Konflikten
- Governance-Dokument muss aktiv gepflegt werden, sonst veraltet es

### Offene Fragen

- Wann auf GitHub Actions CI/CD umstellen (TASK-012)?
- Soll der `no-commit-to-branch`-Hook für Orchestratoren deaktiviert oder per `--no-verify` umgangen werden?

---

## DSGVO-Implikationen

Keine direkten DSGVO-Implikationen. Das Governance-Framework **stärkt** die DSGVO-Compliance durch verpflichtende Checklisten in PRs und ADRs (owner_id-Filter, expires_at, Lösch-Kaskaden, PII-Prüfung).

---

## Sicherheitsimplikationen

- Pre-Commit-Hook `detect-private-key` verhindert Commit von Private Keys
- PR-Template enthält OWASP-Checkliste
- Security-Gate bei sicherheitsrelevanten Änderungen (2 Reviewer)
- Risiko: Orchestratoren nutzen `--no-verify` für den `no-commit-to-branch`-Hook — andere Hooks (Linting, Keys) bleiben aktiv

---

## Revisionsdatum

September 2026 — nach Abschluss der Phase-2-MVP-Entwicklung evaluieren, ob die Prozesse skalieren.
