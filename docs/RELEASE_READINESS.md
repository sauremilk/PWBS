# Release-Readiness-Kriterienkatalog: PWBS

**Version:** 1.0
**Datum:** 17. März 2026
**Status:** Aktiv
**Verantwortlich:** Projektleitung
**Basisdokumente:** [LEGAL_COMPLIANCE.md](LEGAL_COMPLIANCE.md), [GTM_PLAN.md](GTM_PLAN.md), [UX_ONBOARDING_SPEC.md](UX_ONBOARDING_SPEC.md), [TRACKING_PLAN.md](TRACKING_PLAN.md), [SUPPORT_OPERATIONS_PLAN.md](SUPPORT_OPERATIONS_PLAN.md), [security-audit.md](../legal/security-audit.md), [audit-reports/2026-03-16-workspace-audit.md](audit-reports/2026-03-16-workspace-audit.md)

---

## Inhaltsverzeichnis

1. [Übersicht & Gate-Definitionen](#1-übersicht--gate-definitionen)
2. [Readiness-Checkliste: Closed Beta](#2-readiness-checkliste-closed-beta)
3. [Readiness-Checkliste: Open Beta](#3-readiness-checkliste-open-beta)
4. [Readiness-Checkliste: General Availability](#4-readiness-checkliste-general-availability)
5. [Rollback-Plan](#5-rollback-plan)
6. [Sign-off-Log](#6-sign-off-log)
7. [Known Issues & Accepted Risks](#7-known-issues--accepted-risks)

---

## 1. Übersicht & Gate-Definitionen

Das PWBS durchläuft drei Release-Gates. Jedes Gate hat spezifische Mindestanforderungen, die vor dem Übergang erfüllt sein müssen. Kriterien sind kumulativ – ein späteres Gate beinhaltet alle Anforderungen der vorherigen Gates.

| Gate                     | Zielgruppe                 | Erwartete Nutzer | Zweck                                     | Risikoakzeptanz                                          |
| ------------------------ | -------------------------- | :--------------: | ----------------------------------------- | -------------------------------------------------------- |
| **Closed Beta**          | Eingeladene Early Adopters |      10–20       | Validierung, Bug-Finding, Feedback        | Hoch (Known Issues akzeptabel, 1-on-1-Support)           |
| **Open Beta**            | Self-Serve via Waitlist    |     bis 200      | Skalierung, Retention-Messung, Self-Serve | Mittel (Self-Serve muss funktionieren, SLOs eingehalten) |
| **General Availability** | Öffentlich                 |      1.000+      | Produktivbetrieb, Monetarisierung         | Niedrig (SLA-Garantien, formaler Support, Pricing aktiv) |

### Übergangslogik

```
Closed Beta → Open Beta:
  Alle "Must"-Kriterien der Closed Beta ✅
  + Alle Exit-Kriterien aus GTM_PLAN Abschnitt 6 erfüllt
  + Load-Test bestanden

Open Beta → General Availability:
  Alle "Must"-Kriterien der Open Beta ✅
  + D30-Retention > 50 % über ≥ 3 Kohorten
  + ≥ 30 % der aktiven Nutzer signalisieren Zahlungsbereitschaft
  + Uptime > 99,5 % über letzten Monat
```

### Status-Legende

| Symbol | Bedeutung     |
| :----: | ------------- |
|   ✅   | Erfüllt       |
|   ⏳   | In Arbeit     |
|   ❌   | Nicht erfüllt |

---

## 2. Readiness-Checkliste: Closed Beta

### Security (SEC)

| ID     | Kriterium                                                                     | Must/Should | Status | Quelle                                                       | Verantwortlich |
| ------ | ----------------------------------------------------------------------------- | :---------: | :----: | ------------------------------------------------------------ | -------------- |
| SEC-01 | Keine kritischen OWASP-Findings offen                                         |    Must     |   ✅   | security-audit.md: 0 kritische Findings                      | Entwicklung    |
| SEC-02 | Keine hohen OWASP-Findings offen                                              |    Must     |   ❌   | security-audit.md: A05-F01 (CVE-Scan), A09-F01 (Audit-Trail) | Entwicklung    |
| SEC-03 | Dependency-Audit durchgeführt (`pip-audit`, `npm audit`)                      |    Must     |   ❌   | security-audit.md: Finding A05-F01, SUPPORT_OPS #5           | Entwicklung    |
| SEC-04 | Secrets nicht im Repository (kein `.env` committed)                           |    Must     |   ✅   | security-audit.md: A05, workspace-audit: Positiv             | Entwicklung    |
| SEC-05 | CORS auf spezifische Origins eingeschränkt (nicht `*`)                        |    Must     |   ✅   | security-audit.md: A05 – `cors_origins` aus Settings         | Entwicklung    |
| SEC-06 | Rate Limiting auf allen öffentlichen Endpoints aktiv                          |    Must     |   ✅   | security-audit.md: A07 – 5 Req/60s Login                     | Entwicklung    |
| SEC-07 | JWT-Token-Rotation funktional (RS256, 15 Min. Access, 30 Tage Refresh)        |    Must     |   ✅   | security-audit.md: A07 – RS256, Rotation bei Nutzung         | Entwicklung    |
| SEC-08 | Produktions-Startup-Check: kein Start ohne RSA-Keys bei `PWBS_ENV=production` |    Must     |   ❌   | security-audit.md: Finding A02-F01, SUPPORT_OPS #7           | Entwicklung    |
| SEC-09 | CSP-Header in SecurityHeadersMiddleware implementiert                         |   Should    |   ❌   | security-audit.md: Finding A03-F01, SUPPORT_OPS #6           | Entwicklung    |
| SEC-10 | CORS `allow_methods` und `allow_headers` auf genutzte Werte eingeschränkt     |   Should    |   ❌   | security-audit.md: Finding A05-F02                           | Entwicklung    |

**Begründung Must/Should:**

- SEC-01 bis SEC-08 sind Must, weil sie direkte Angriffsvektoren absichern oder DSGVO Art. 32 (technische Maßnahmen) erfüllen.
- SEC-09 und SEC-10 sind Should, weil React-Default-Escaping und Backend-Auth bereits Grundschutz bieten.

---

### Legal (LEG)

| ID     | Kriterium                                                                            | Must/Should | Status | Quelle                                                          | Verantwortlich |
| ------ | ------------------------------------------------------------------------------------ | :---------: | :----: | --------------------------------------------------------------- | -------------- |
| LEG-01 | Impressum online und erreichbar unter `/impressum` (DDG § 5)                         |    Must     |   ❌   | LEGAL_COMPLIANCE: Abschnitt 5, Blocker B-2                      | Projektleitung |
| LEG-02 | Datenschutzerklärung online und erreichbar (DSGVO Art. 13/14)                        |    Must     |   ❌   | LEGAL_COMPLIANCE: Abschnitt 5, Blocker B-1                      | Projektleitung |
| LEG-03 | AGB veröffentlicht (mindestens Beta-AGB mit Haftungsausschluss)                      |    Must     |   ❌   | LEGAL_COMPLIANCE: Abschnitt 5, Blocker B-3                      | Projektleitung |
| LEG-04 | AVVs mit allen Auftragsverarbeitern abgeschlossen (AWS, Anthropic, OpenAI, Vercel)   |    Must     |   ⏳   | LEGAL_COMPLIANCE: Abschnitt 5, Blocker B-4 – Entwürfe vorhanden | Projektleitung |
| LEG-05 | Konto-Löschung funktional (DSGVO Art. 17, 30 Tage Soft-Delete, kaskadierte Löschung) |    Must     |   ✅   | LEGAL_COMPLIANCE: Abschnitt 3.7 – CASCADE DELETE + DEK-Löschung | Entwicklung    |
| LEG-06 | Cookie-/Tracking-Consent-Banner funktional (falls nicht-essentielles Tracking aktiv) |   Should    |   ❌   | LEGAL_COMPLIANCE: Abschnitt 5, TRACKING_PLAN: Consent-Banner    | Entwicklung    |
| LEG-07 | `owner_id`-Filter auf allen Daten-Queries (Mandantenisolation)                       |    Must     |   ✅   | security-audit.md: A01 – durchgängig implementiert              | Entwicklung    |
| LEG-08 | OAuth-Token-Verschlüsselung vor DB-Speicherung (AES-256-GCM)                         |    Must     |   ✅   | security-audit.md: A02 – Fernet-Verschlüsselung                 | Entwicklung    |

**Begründung Must/Should:**

- LEG-01 bis LEG-05, LEG-07, LEG-08 sind Must, weil sie gesetzliche Pflichten erfüllen. Ohne Impressum, DSE und AGB ist ein Launch in der EU rechtswidrig (LEGAL_COMPLIANCE: „Launch-Blocker").
- LEG-06 ist Should, weil Vercel Analytics standardmäßig deaktiviert ist. Erst bei Aktivierung von Tracking wird der Banner zum Must.

---

### Quality (QA)

| ID    | Kriterium                                                                      | Must/Should | Status | Quelle                                                      | Verantwortlich |
| ----- | ------------------------------------------------------------------------------ | :---------: | :----: | ----------------------------------------------------------- | -------------- |
| QA-01 | Kein offener P0-Bug                                                            |    Must     |   ✅   | GTM_PLAN: Exit-Kriterium 4, workspace-audit: keine P0-Bugs  | Entwicklung    |
| QA-02 | Unit-Test-Suite besteht (≥ 80 % der Tests grün)                                |    Must     |   ✅   | workspace-audit: ~470 Unit-Tests                            | Entwicklung    |
| QA-03 | E2E-Happy-Path getestet: Register → Connect → Briefing                         |    Must     |   ❌   | UX_ONBOARDING_SPEC: Abschnitt 4, GTM_PLAN: Exit-Kriterium 6 | Entwicklung    |
| QA-04 | API-Health-Check gibt 200 zurück (`GET /api/v1/admin/health`)                  |    Must     |   ✅   | SUPPORT_OPS: Abschnitt 3.2                                  | Entwicklung    |
| QA-05 | Alembic-Migrationen angewendet und konsistent (`alembic current` zeigt `head`) |    Must     |   ⏳   | workspace-audit: Alembic-Verzeichnis Status unklar          | Entwicklung    |
| QA-06 | Kein offener P1-Bug                                                            |   Should    |   ✅   | GTM_PLAN: Exit-Kriterium 4                                  | Entwicklung    |

**Begründung Must/Should:**

- QA-01 bis QA-05 sind Must, weil sie die Grundfunktionalität für Beta-Nutzer sicherstellen.
- QA-06 ist Should, weil einzelne P1-Bugs in der Closed Beta akzeptabel sind, solange Workarounds existieren.

---

### UX (UX)

| ID    | Kriterium                                                                                         | Must/Should | Status | Quelle                                                                | Verantwortlich |
| ----- | ------------------------------------------------------------------------------------------------- | :---------: | :----: | --------------------------------------------------------------------- | -------------- |
| UX-01 | Onboarding-Wizard implementiert (Welcome → Connect → Sync → Briefing)                             |   Should    |   ⏳   | UX_ONBOARDING_SPEC: Abschnitt 5 – Wizard existiert, Integration offen | Entwicklung    |
| UX-02 | Empty States für alle Haupt-Dashboard-Seiten definiert (Briefings, Konnektoren, Suche, Knowledge) |   Should    |   ⏳   | UX_ONBOARDING_SPEC: Abschnitt 6 – Komponente vorhanden, generisch     | Entwicklung    |
| UX-03 | Error States nutzerfreundlich (keine technischen Stacktraces an Endnutzer)                        |    Must     |   ❌   | UX_ONBOARDING_SPEC: Heuristik 9 – ❌ Kritisch, generische Fehler      | Entwicklung    |
| UX-04 | Mobile-Responsive (Mindestanforderung: lesbar auf Tablet)                                         |   Should    |   ⏳   | UX_ONBOARDING_SPEC: Abschnitt 8 – responsive ab `md:` Breakpoint      | Entwicklung    |
| UX-05 | Time-to-First-Briefing ≤ 20 Minuten für 80 % der Nutzer (mit 1-on-1-Onboarding)                   |    Must     |   ❌   | GTM_PLAN: Exit-Kriterium 6, KPI #2                                    | Entwicklung    |

**Begründung Must/Should:**

- UX-03 ist Must, weil technische Fehlermeldungen Vertrauen zerstören und Support-Last erzeugen.
- UX-05 ist Must, weil Time-to-First-Briefing das zentrale Exit-Kriterium der Closed Beta ist (GTM_PLAN).
- UX-01, UX-02, UX-04 sind Should, weil in der Closed Beta 1-on-1-Onboarding den Wizard kompensiert und generische Empty States funktional ausreichen.

---

### Analytics (ANA)

| ID     | Kriterium                                                                                      | Must/Should | Status | Quelle                                          | Verantwortlich |
| ------ | ---------------------------------------------------------------------------------------------- | :---------: | :----: | ----------------------------------------------- | -------------- |
| ANA-01 | Core-Events implementiert: `auth_user_registered`, `connector_connected`, `briefing_generated` |    Must     |   ❌   | TRACKING_PLAN: Phase 1, Tasks 3–5               | Entwicklung    |
| ANA-02 | Activation-Funnel messbar (Register → Connect → Briefing)                                      |   Should    |   ❌   | TRACKING_PLAN: Abschnitt 6.1                    | Entwicklung    |
| ANA-03 | Analytics-Dashboard zugänglich (PostHog Self-Hosted oder äquivalent)                           |   Should    |   ❌   | TRACKING_PLAN: Abschnitt 8, Phase 3 Tasks 16–20 | Entwicklung    |

**Begründung Must/Should:**

- ANA-01 ist Must, weil ohne Server-Side-Events die Exit-Kriterien der Closed Beta (Retention, Connector Completion Rate) nicht messbar sind.
- ANA-02 und ANA-03 sind Should, weil die KPIs in der Closed Beta auch manuell über DB-Queries gemessen werden können.

---

### Operations (OPS)

| ID     | Kriterium                                                                         | Must/Should | Status | Quelle                                                            | Verantwortlich |
| ------ | --------------------------------------------------------------------------------- | :---------: | :----: | ----------------------------------------------------------------- | -------------- |
| OPS-01 | Health-Check-Endpoint funktional (`GET /api/v1/admin/health` → 200)               |    Must     |   ✅   | SUPPORT_OPS: Abschnitt 3.2                                        | Entwicklung    |
| OPS-02 | Strukturierte Logs aktiv (JSON-Format mit Structlog, Correlation-IDs)             |    Must     |   ✅   | SUPPORT_OPS: Abschnitt 3.1, workspace-audit: TASK-196             | Entwicklung    |
| OPS-03 | Error-Tracking aktiv (Sentry oder äquivalent konfiguriert)                        |    Must     |   ❌   | SUPPORT_OPS: Abschnitt 10 #1 – Sentry geplant, nicht konfiguriert | Entwicklung    |
| OPS-04 | Backup-Strategie dokumentiert (RPO < 1h, RTO < 4h)                                |    Must     |   ✅   | SUPPORT_OPS: Abschnitt 7.4 – RPO/RTO definiert                    | Entwicklung    |
| OPS-05 | Backup-Restore getestet (DR-Runbook praktisch validiert)                          |   Should    |   ❌   | SUPPORT_OPS: Abschnitt 10 #15                                     | Entwicklung    |
| OPS-06 | Rollback-Verfahren dokumentiert (ECS Task Definition Revision, Alembic Downgrade) |    Must     |   ✅   | SUPPORT_OPS: Abschnitt 7 – Verfahren dokumentiert                 | Entwicklung    |
| OPS-07 | Grafana-Alerting konfiguriert (P0/P1: API Down, Error Rate, DB-Fehler)            |   Should    |   ❌   | SUPPORT_OPS: Abschnitt 10 #2                                      | Entwicklung    |
| OPS-08 | Deployment-Runbook vorhanden                                                      |   Should    |   ❌   | SUPPORT_OPS: Runbook-Index – „Zu erstellen"                       | Entwicklung    |

**Begründung Must/Should:**

- OPS-01 bis OPS-04 und OPS-06 sind Must, weil sie die Mindest-Betriebsfähigkeit sicherstellen. Ohne Error-Tracking (Sentry) bleiben Fehler in der Beta unsichtbar.
- OPS-05, OPS-07, OPS-08 sind Should, weil das System in der Closed Beta mit 10–20 Nutzern auch ohne automatisiertes Alerting manuell überwachbar ist.

---

### Content (CNT)

| ID     | Kriterium                                                                               | Must/Should | Status | Quelle                          | Verantwortlich |
| ------ | --------------------------------------------------------------------------------------- | :---------: | :----: | ------------------------------- | -------------- |
| CNT-01 | Landing Page aktuell (Features stimmen mit MVP überein, CTA führt zu Waitlist/Register) |    Must     |   ✅   | GTM_PLAN: Abschnitt 7 Woche 1–2 | Projektleitung |
| CNT-02 | README aktuell (Projektbeschreibung, Setup-Anleitung)                                   |   Should    |   ⏳   | Allgemein                       | Entwicklung    |
| CNT-03 | Changelog aktuell (letzte Änderungen dokumentiert)                                      |   Should    |   ⏳   | Allgemein                       | Entwicklung    |

**Begründung Must/Should:**

- CNT-01 ist Must, weil die Landing Page der erste Kontaktpunkt für eingeladene Nutzer ist.
- CNT-02 und CNT-03 sind Should, weil Beta-Nutzer über 1-on-1-Onboarding eingeführt werden und keine Selbst-Setup-Dokumentation benötigen.

---

### Zusammenfassung Closed Beta

| Kategorie  | Must gesamt | Must ✅ | Must ❌/⏳ | Should gesamt | Should ✅ | Should ❌/⏳ |
| ---------- | :---------: | :-----: | :--------: | :-----------: | :-------: | :----------: |
| Security   |      8      |    5    |     3      |       2       |     0     |      2       |
| Legal      |      6      |    3    |     3      |       1       |     0     |      1       |
| Quality    |      5      |    3    |     2      |       1       |     1     |      0       |
| UX         |      2      |    0    |     2      |       3       |     0     |      3       |
| Analytics  |      1      |    0    |     1      |       2       |     0     |      2       |
| Operations |      5      |    3    |     2      |       3       |     0     |      3       |
| Content    |      1      |    1    |     0      |       2       |     0     |      2       |
| **Gesamt** |   **28**    | **15**  |   **13**   |    **14**     |   **1**   |    **13**    |

**Fazit:** 15 von 28 Must-Kriterien erfüllt. **13 Must-Kriterien blockieren den Closed-Beta-Launch.** Schwerpunkte: Rechtliche Pflichtdokumente (LEG-01 bis LEG-04), Security-Findings (SEC-02, SEC-03, SEC-08) und Error-Tracking (OPS-03).

---

## 3. Readiness-Checkliste: Open Beta

Alle Must-Kriterien der Closed Beta werden vorausgesetzt. Alle Should-Kriterien der Closed Beta werden zu Must. Zusätzlich gelten folgende Kriterien:

### Zusätzliche Security-Kriterien

| ID        | Kriterium                                                              | Must/Should | Status | Quelle                                                   | Verantwortlich |
| --------- | ---------------------------------------------------------------------- | :---------: | :----: | -------------------------------------------------------- | -------------- |
| SEC-OB-01 | Dependabot oder Renovate für automatische Dependency-Updates aktiviert |    Must     |   ❌   | security-audit.md: Finding A06-F01, SUPPORT_OPS #8       | Entwicklung    |
| SEC-OB-02 | Docker-Image-Signierung evaluiert und bei Bedarf implementiert         |   Should    |   ❌   | security-audit.md: Finding A08-F01, LEGAL_COMPLIANCE W-7 | Entwicklung    |
| SEC-OB-03 | SSRF-Schutz als zentrale URL-Validierungsfunktion implementiert        |   Should    |   ❌   | security-audit.md: Finding A10-F01                       | Entwicklung    |

### Zusätzliche Legal-Kriterien

| ID        | Kriterium                                                                            | Must/Should | Status | Quelle                                               | Verantwortlich |
| --------- | ------------------------------------------------------------------------------------ | :---------: | :----: | ---------------------------------------------------- | -------------- |
| LEG-OB-01 | Formale DSFA durchgeführt (Art. 35 DSGVO) – Fokus: LLM-Verarbeitung, Knowledge Graph |    Must     |   ❌   | LEGAL_COMPLIANCE: W-1                                | Projektleitung |
| LEG-OB-02 | Verarbeitungsverzeichnis (VVT) erstellt (Art. 30 DSGVO)                              |    Must     |   ✅   | LEGAL_COMPLIANCE: W-2, security-audit.md: Art. 30 ✅ | Projektleitung |
| LEG-OB-03 | KI-Kennzeichnung in Briefings implementiert (Art. 50 EU AI Act, Frist August 2026)   |   Should    |   ❌   | LEGAL_COMPLIANCE: Abschnitt 6.3, W-5                 | Entwicklung    |
| LEG-OB-04 | Consent-Dokumentation erweitert (DSE-Version in ConnectorConsent-Tabelle)            |   Should    |   ❌   | LEGAL_COMPLIANCE: W-6                                | Entwicklung    |

### Zusätzliche Quality-Kriterien

| ID       | Kriterium                                                   | Must/Should | Status | Quelle                                        | Verantwortlich |
| -------- | ----------------------------------------------------------- | :---------: | :----: | --------------------------------------------- | -------------- |
| QA-OB-01 | Load-Test mit erwarteter Open-Beta-Last bestanden (500 VUs) |    Must     |   ❌   | GTM_PLAN: Abschnitt 6 Phase B Voraussetzung 2 | Entwicklung    |
| QA-OB-02 | Test-Coverage-Report eingerichtet (pytest-cov)              |   Should    |   ❌   | workspace-audit: Empfehlungen                 | Entwicklung    |

### Zusätzliche UX-Kriterien

| ID       | Kriterium                                                          | Must/Should | Status | Quelle                                        | Verantwortlich |
| -------- | ------------------------------------------------------------------ | :---------: | :----: | --------------------------------------------- | -------------- |
| UX-OB-01 | Self-Serve-Onboarding funktional (kein 1-on-1 nötig für Open Beta) |    Must     |   ❌   | GTM_PLAN: Abschnitt 6 Phase B Voraussetzung 4 | Entwicklung    |
| UX-OB-02 | Fortschrittsindikator im Onboarding mit geschätzter Restdauer      |   Should    |   ❌   | UX_ONBOARDING_SPEC: Heuristik 1 Empfehlung    | Entwicklung    |
| UX-OB-03 | Post-Onboarding-Checklist auf Dashboard                            |   Should    |   ❌   | UX_ONBOARDING_SPEC: Heuristik 10 Empfehlung   | Entwicklung    |

### Zusätzliche Analytics-Kriterien

| ID        | Kriterium                                                                           | Must/Should | Status | Quelle                               | Verantwortlich |
| --------- | ----------------------------------------------------------------------------------- | :---------: | :----: | ------------------------------------ | -------------- |
| ANA-OB-01 | Client-Side-Events implementiert (onboarding\_\*, briefing_viewed, app_page_viewed) |    Must     |   ❌   | TRACKING_PLAN: Phase 2 Tasks 9–15    | Entwicklung    |
| ANA-OB-02 | Consent-Banner implementiert (TDDDG § 25 konform)                                   |    Must     |   ❌   | TRACKING_PLAN: Abschnitt 7.7, Task 9 | Entwicklung    |
| ANA-OB-03 | Retention-Kohorten-Analyse konfiguriert                                             |   Should    |   ❌   | TRACKING_PLAN: Phase 3 Task 20       | Entwicklung    |

### Zusätzliche Operations-Kriterien

| ID        | Kriterium                                                       | Must/Should | Status | Quelle                        | Verantwortlich |
| --------- | --------------------------------------------------------------- | :---------: | :----: | ----------------------------- | -------------- |
| OPS-OB-01 | Status-Page eingerichtet (Instatus, Cachet oder statische HTML) |   Should    |   ❌   | SUPPORT_OPS: Abschnitt 10 #4  | Entwicklung    |
| OPS-OB-02 | Auto-Scaling konfiguriert (ECS Target-Tracking CPU < 70 %)      |   Should    |   ❌   | SUPPORT_OPS: Abschnitt 10 #14 | Entwicklung    |
| OPS-OB-03 | Connector-Debugging-Runbook vorhanden                           |   Should    |   ❌   | SUPPORT_OPS: Runbook-Index    | Entwicklung    |
| OPS-OB-04 | LLM-Fallback-Runbook vorhanden                                  |   Should    |   ❌   | SUPPORT_OPS: Runbook-Index    | Entwicklung    |

### Zusätzliche Content-/Community-Kriterien

| ID        | Kriterium                                           | Must/Should | Status | Quelle                                        | Verantwortlich |
| --------- | --------------------------------------------------- | :---------: | :----: | --------------------------------------------- | -------------- |
| CNT-OB-01 | Discord-Community-Server eingerichtet und moderiert |    Must     |   ❌   | GTM_PLAN: Abschnitt 6 Phase B Voraussetzung 5 | Projektleitung |
| CNT-OB-02 | Demo-Video vorhanden (90 Sek. Screencast)           |   Should    |   ❌   | GTM_PLAN: Abschnitt 7 Woche 1–2               | Projektleitung |
| CNT-OB-03 | FAQ-Seite oder Hilfe-Center vorhanden               |   Should    |   ❌   | UX_ONBOARDING_SPEC: Heuristik 10              | Projektleitung |

---

## 4. Readiness-Checkliste: General Availability

Alle Must-Kriterien der Open Beta werden vorausgesetzt. Alle Should-Kriterien der Open Beta werden zu Must. Zusätzlich gelten folgende Kriterien:

### Zusätzliche Security-Kriterien

| ID        | Kriterium                                     | Must/Should | Status | Quelle                                                | Verantwortlich |
| --------- | --------------------------------------------- | :---------: | :----: | ----------------------------------------------------- | -------------- |
| SEC-GA-01 | Externer Penetration-Test durchgeführt        |    Must     |   ❌   | security-audit.md: Empfehlungen, LEGAL_COMPLIANCE G-6 | Projektleitung |
| SEC-GA-02 | MFA implementiert (optionaler zweiter Faktor) |   Should    |   ❌   | LEGAL_COMPLIANCE: G-3                                 | Entwicklung    |

### Zusätzliche Legal-Kriterien

| ID        | Kriterium                                                  | Must/Should | Status | Quelle                                            | Verantwortlich |
| --------- | ---------------------------------------------------------- | :---------: | :----: | ------------------------------------------------- | -------------- |
| LEG-GA-01 | DPA-Template für Enterprise-Kunden vorhanden               |   Should    |   ❌   | LEGAL_COMPLIANCE: G-1                             | Projektleitung |
| LEG-GA-02 | KI-Kennzeichnung vollständig konform mit Art. 50 EU AI Act |    Must     |   ❌   | LEGAL_COMPLIANCE: Abschnitt 6 – Frist August 2026 | Entwicklung    |
| LEG-GA-03 | Drittdaten-Strategie abschließend rechtlich bewertet       |   Should    |   ❌   | LEGAL_COMPLIANCE: W-3, W-10                       | Projektleitung |

### Zusätzliche Produkt-Kriterien

| ID        | Kriterium                                                  | Must/Should | Status | Quelle                        | Verantwortlich |
| --------- | ---------------------------------------------------------- | :---------: | :----: | ----------------------------- | -------------- |
| PRD-GA-01 | Pricing-Seite live (Free/Pro/Enterprise-Tiers)             |    Must     |   ❌   | GTM_PLAN: Abschnitt 4         | Projektleitung |
| PRD-GA-02 | D30-Retention > 50 % über ≥ 3 aufeinanderfolgende Kohorten |    Must     |   ❌   | GTM_PLAN: Abschnitt 6 Phase C | Projektleitung |
| PRD-GA-03 | NPS > 40                                                   |   Should    |   ❌   | GTM_PLAN: Abschnitt 6 Phase C | Projektleitung |

### Zusätzliche Operations-Kriterien

| ID        | Kriterium                                                   | Must/Should | Status | Quelle                                           | Verantwortlich |
| --------- | ----------------------------------------------------------- | :---------: | :----: | ------------------------------------------------ | -------------- |
| OPS-GA-01 | SLA-Definitionen publiziert (99,5 % Uptime für Pro-Kunden)  |    Must     |   ❌   | GTM_PLAN: Abschnitt 6 Phase C                    | Projektleitung |
| OPS-GA-02 | Support-Prozess formalisiert (E-Mail-Support mit Ticketing) |    Must     |   ❌   | SUPPORT_OPS: Abschnitt 5                         | Projektleitung |
| OPS-GA-03 | Uptime > 99,5 % über den letzten Monat nachgewiesen         |    Must     |   ❌   | GTM_PLAN: Abschnitt 6 Phase C, SUPPORT_OPS: SLOs | Entwicklung    |

---

## 5. Rollback-Plan

### 5.1 Code-Rollback

| Verfahren                        | Beschreibung                                                                                                     | Auslöser                                                         |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **ECS Task Definition Revision** | Vorherige stabile Task Definition Revision aktivieren: `aws ecs update-service --task-definition pwbs-api:<REV>` | Error Rate > 5 % nach Deploy oder Health-Check 3× fehlgeschlagen |
| **ECS Circuit Breaker**          | Automatischer Rollback bei fehlgeschlagenem Deployment (konfiguriert mit `rollback`)                             | Automatisch bei Deploy-Failure                                   |
| **Docker Image Tag**             | Produktions-Image-Tag auf vorherigen stabilen Tag zurücksetzen                                                   | Manuell bei schwerwiegenden Regressionen                         |

**Prozess:**

1. Problem erkennen (Grafana Alert oder manuell)
2. Vorherige stabile Task Definition Revision identifizieren
3. `aws ecs update-service --cluster pwbs --service api --task-definition pwbs-api:<VORHERIGE_REVISION>`
4. `aws ecs wait services-stable --cluster pwbs --services api`
5. Health-Check verifizieren

### 5.2 Feature-Flag-Deaktivierung

Folgende Features können sofort per Feature-Flag deaktiviert werden:

| Feature-Flag                  | Wirkung                                  | Verfahren                                       |
| ----------------------------- | ---------------------------------------- | ----------------------------------------------- |
| `beta_registration_open`      | Neue Registrierungen sperren (Notbremse) | ENV-Override oder DB-Update                     |
| `briefing_generation_enabled` | Briefing-Generierung deaktivieren        | Bei LLM-Problemen oder Halluzinations-Incidents |
| `neo4j_enabled`               | Knowledge-Graph-Features deaktivieren    | Graceful Degradation über `NullGraphService`    |
| `connector_sync_enabled`      | Automatische Connector-Syncs stoppen     | Bei API-Rate-Limit-Problemen der Quell-APIs     |

**Verfahren:** Feature-Flags über Admin-Endpoint oder direkte DB-Änderung:

```sql
UPDATE feature_flags SET enabled = false WHERE name = '<flag_name>';
```

Alternativ: ENV-Override → ECS Service Update.

### 5.3 Datenbank-Rollback

| Szenario                          | Verfahren                                                                 | RPO / RTO                  |
| --------------------------------- | ------------------------------------------------------------------------- | -------------------------- |
| **Fehlerhafte Alembic-Migration** | `alembic downgrade -1` + vorheriges Docker Image deployen                 | RPO: 0 (kein Datenverlust) |
| **Destruktive Migration**         | RDS Snapshot vor Migration erzwingen, bei Fehler: Snapshot Restore        | RPO < 1h / RTO < 4h        |
| **Datenkorruption**               | Disaster-Recovery-Runbook: PostgreSQL → Weaviate → Neo4j (FK-Reihenfolge) | RPO < 1h / RTO < 4h        |

**Regel:** Destruktive Migrationen (`DROP COLUMN`, `DROP TABLE`) nur mit vorherigem RDS Snapshot.

### 5.4 Kommunikation bei Rollback

| Aktion                  | Kanal                                          | Zeitvorgabe          |
| ----------------------- | ---------------------------------------------- | -------------------- |
| Incident-Erkennung      | Grafana Alert → Discord `#ops-alerts`          | Automatisch          |
| Status-Update an Nutzer | Discord `#ankündigungen` + Status-Page         | Innerhalb 1 Stunde   |
| Entwarnung              | Discord `#ankündigungen` + Status-Page         | Nach Stabilisierung  |
| Post-Mortem (bei P0/P1) | `docs/runbooks/postmortems/` + Discord-Summary | Innerhalb 48 Stunden |

---

## 6. Sign-off-Log

Formale Freigabe vor jedem Gate-Übergang. Jede Kategorie muss von einer verantwortlichen Person abgezeichnet werden.

### Closed Beta Sign-off

| Kategorie  | Freigegeben von | Datum | Anmerkung |
| ---------- | --------------- | ----- | --------- |
| Security   |                 |       |           |
| Legal      |                 |       |           |
| Quality    |                 |       |           |
| UX         |                 |       |           |
| Analytics  |                 |       |           |
| Operations |                 |       |           |
| Content    |                 |       |           |

### Open Beta Sign-off

| Kategorie  | Freigegeben von | Datum | Anmerkung |
| ---------- | --------------- | ----- | --------- |
| Security   |                 |       |           |
| Legal      |                 |       |           |
| Quality    |                 |       |           |
| UX         |                 |       |           |
| Analytics  |                 |       |           |
| Operations |                 |       |           |
| Content    |                 |       |           |
| Community  |                 |       |           |

### General Availability Sign-off

| Kategorie  | Freigegeben von | Datum | Anmerkung |
| ---------- | --------------- | ----- | --------- |
| Security   |                 |       |           |
| Legal      |                 |       |           |
| Quality    |                 |       |           |
| UX         |                 |       |           |
| Analytics  |                 |       |           |
| Operations |                 |       |           |
| Content    |                 |       |           |
| Produkt    |                 |       |           |

---

## 7. Known Issues & Accepted Risks

Bewusst akzeptierte Einschränkungen für den jeweiligen Release-Gate.

### Closed Beta – Akzeptierte Risiken

| ID    | Beschreibung                                                                                                      | Schweregrad | Begründung für Akzeptanz                                                                                                                             | Geplante Behebung                                |
| ----- | ----------------------------------------------------------------------------------------------------------------- | :---------: | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| KI-01 | Health-Endpoint (`/api/v1/admin/health`) ist öffentlich zugänglich                                                |   Niedrig   | Beabsichtigt für Load-Balancer-Checks. Exponiert keine internen Details (security-audit.md: A01-F01)                                                 | Kein Fix geplant                                 |
| KI-02 | Neo4j ist optional – Knowledge-Graph-Features liefern leere Ergebnisse wenn Neo4j nicht verfügbar                 |   Niedrig   | Architektonische Entscheidung (ADR-016). Briefings und Suche funktionieren ohne Graph                                                                | Neo4j in Phase 3 stabilisieren                   |
| KI-03 | Kein Cookie-Banner, solange nicht-essentielles Tracking deaktiviert bleibt                                        |   Niedrig   | Vercel Analytics deaktiviert. JWT in `localStorage` ist technisch notwendig (TDDDG § 25 Abs. 2 Nr. 2)                                                | Banner bei Tracking-Aktivierung                  |
| KI-04 | Audit-Trail (A09-F01) nur teilweise implementiert – datenschutzrelevante Aktionen nicht vollständig protokolliert |    Hoch     | Closed-Beta-Nutzer werden manuell betreut, Aktionen sind über Application-Logs nachvollziehbar. Compliance-Risiko bei Audit gering bei 10–20 Nutzern | Phase 3 Backlog: vollständiger Audit-Log-Service |
| KI-05 | ecdsa 0.19.1 hat CVE-2024-23342 – kein Fix verfügbar                                                              |   Mittel    | Kein direkter Exploit-Pfad im PWBS-Kontext (workspace-audit). Wird monatlich geprüft                                                                 | Fix bei Verfügbarkeit anwenden                   |
| KI-06 | Keine formale DSFA durchgeführt (Art. 35 DSGVO)                                                                   |   Mittel    | Vorabeinschätzung vorhanden. Bei 10–20 Nutzern ist das Risiko begrenzt. Erforderlich vor Open Beta                                                   | Vor Open Beta: DSFA mit Anwalt                   |
| KI-07 | Briefings ohne explizite KI-Kennzeichnung (Art. 50 EU AI Act greift erst August 2026)                             |   Niedrig   | Pflicht erst ab August 2026. Quellenreferenzen sind bereits vorhanden                                                                                | Vor August 2026 implementieren                   |
| KI-08 | Onboarding-Wizard-Integration nicht vollständig (Fortschritts-Persistierung fehlt)                                |   Mittel    | Closed Beta nutzt 1-on-1-Onboarding. Wizard-Abbruch wird durch persönliche Betreuung kompensiert                                                     | Vor Open Beta: Self-Serve-Wizard                 |
| KI-09 | Error States zeigen teilweise technische Fehlermeldungen                                                          |   Mittel    | Closed-Beta-Nutzer sind technisch affin und tolerieren Beta-Rauheit. Support über Discord                                                            | Vor Open Beta: Error-Mapping                     |
| KI-10 | Kein automatisiertes Grafana-Alerting konfiguriert                                                                |   Mittel    | System wird bei 10–20 Nutzern manuell überwacht. Health-Checks und ECS Auto-Recovery sind aktiv                                                      | Vor Open Beta: Alerting-Setup                    |

---

## Anhang: Quell-Referenzen

| Dokument                                                                                   | Referenzierte Kriterien                                |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------ |
| [LEGAL_COMPLIANCE.md](LEGAL_COMPLIANCE.md)                                                 | LEG-_, KI-03, KI-04, KI-06, KI-07, LEG-OB-_, LEG-GA-\* |
| [GTM_PLAN.md](GTM_PLAN.md)                                                                 | QA-03, UX-05, ANA-_, QA-OB-01, CNT-OB-01, PRD-GA-_     |
| [UX_ONBOARDING_SPEC.md](UX_ONBOARDING_SPEC.md)                                             | UX-_, KI-08, KI-09, UX-OB-_, CNT-OB-03                 |
| [TRACKING_PLAN.md](TRACKING_PLAN.md)                                                       | ANA-_, ANA-OB-_                                        |
| [SUPPORT_OPERATIONS_PLAN.md](SUPPORT_OPERATIONS_PLAN.md)                                   | OPS-_, OPS-OB-_, Rollback-Plan                         |
| [security-audit.md](../legal/security-audit.md)                                            | SEC-_, KI-01, KI-04, KI-05, SEC-OB-_, SEC-GA-01        |
| [audit-reports/2026-03-16-workspace-audit.md](audit-reports/2026-03-16-workspace-audit.md) | QA-02, KI-05                                           |

---

_Erstellt: 17. März 2026 | Nächste Review: Vor Closed Beta Go-Live_
