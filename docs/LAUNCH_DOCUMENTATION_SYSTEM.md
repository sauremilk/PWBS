# Launch-Dokumentensystem: Phase „Code Complete → Public Launch"

Version: 1.0.0 | Stand: 17. März 2026  
Basis: [App-Launch: Zusätzliche Planungsdokumente](App-Launch_%20Zusätzliche%20Planungsdokumente.md)  
Scope: PWBS – Persönliches Wissens-Betriebssystem

---

## Vorhandene Ausgangsbasis

| Datei | Ebene | Status |
|-------|-------|--------|
| `vision-wissens-os.md` | Strategisch | ✅ Vorhanden |
| `ARCHITECTURE.md` | Strategisch/Taktisch | ✅ Vorhanden |
| `ROADMAP.md` | Strategisch | ✅ Vorhanden |
| `PRD-SPEC.md` | Taktisch | ✅ Vorhanden |
| `tasks.md` | Operativ | ✅ Vorhanden |
| `GOVERNANCE.md` | Strategisch | ✅ Vorhanden |
| `ORCHESTRATION.md` | Operativ | ✅ Vorhanden |
| `docs/dsgvo-erstkonzept.md` | Taktisch | ✅ Vorhanden |
| `docs/encryption-strategy.md` | Taktisch | ✅ Vorhanden |
| `docs/runbooks/disaster-recovery.md` | Operativ | ✅ Vorhanden |
| `docs/public-beta/onboarding-flow.md` | Taktisch | ✅ Vorhanden |
| `docs/public-beta/community-setup.md` | Taktisch | ✅ Vorhanden |
| `docs/adr/014-beta-launch-strategie.md` | Strategisch | ✅ Vorhanden |
| `legal/` (tom.md, avv/, security-audit.md) | Taktisch | ✅ Teilweise vorhanden |

---

# 1. Zielarchitektur der Dokumente

Das Dokumentensystem für die Launch-Phase ist in drei Ebenen organisiert, die aufeinander aufbauen:

### Ebene 1 – Strategische Zielzustände (Was und Warum)
Definiert die angestrebten Endzustände für Marktpositionierung, rechtliche Absicherung und Erfolgsmessung. Diese Ebene ist stabiler und ändert sich selten nach erstmaliger Festlegung.

**Dokumente:** GTM_PLAN.md, LEGAL_COMPLIANCE.md

### Ebene 2 – Taktische Spezifikationen (Wie genau)
Konkretisiert die strategischen Ziele in umsetzbare Spezifikationen für UX, Analytics, Betrieb und Support. Diese Ebene enthält die detaillierten Anforderungen, aus denen Tasks abgeleitet werden.

**Dokumente:** TRACKING_PLAN.md, UX_ONBOARDING_SPEC.md, SUPPORT_OPERATIONS_PLAN.md

### Ebene 3 – Operative Readiness-Gates (Ist es fertig?)
Operationalisiert alle Spezifikationen in prüfbare Checklisten und konkrete Tasks. Diese Ebene ist rein exekutiv und beantwortet die Frage: „Sind alle Voraussetzungen erfüllt?"

**Dokumente:** RELEASE_READINESS.md, LAUNCH_TASKS.md

### Ableitungsrichtung

```
   ┌──────────────────────────────────────────────────────────┐
   │                 VORHANDENE BASIS                          │
   │  vision-wissens-os.md → ROADMAP.md → PRD-SPEC.md        │
   │  ARCHITECTURE.md       GOVERNANCE.md   tasks.md          │
   └──────────────┬───────────────────────────┬───────────────┘
                  │                           │
                  ▼                           ▼
   ┌─────────────────────────┐  ┌─────────────────────────────┐
   │   EBENE 1: STRATEGIE    │  │   EBENE 1: STRATEGIE        │
   │   GTM_PLAN.md           │  │   LEGAL_COMPLIANCE.md       │
   └──────┬──────────────────┘  └──────┬──────────────────────┘
          │                            │
          ▼                            ▼
   ┌─────────────────────────────────────────────────────────┐
   │                EBENE 2: SPEZIFIKATION                    │
   │  TRACKING_PLAN.md    UX_ONBOARDING_SPEC.md              │
   │                      SUPPORT_OPERATIONS_PLAN.md          │
   └──────────────────────────┬──────────────────────────────┘
                              │
                              ▼
   ┌─────────────────────────────────────────────────────────┐
   │              EBENE 3: READINESS & EXECUTION              │
   │  RELEASE_READINESS.md        LAUNCH_TASKS.md            │
   └─────────────────────────────────────────────────────────┘
```

---

# 2. Empfohlene Dateihierarchie

## Neue Dateien (zu erstellen)

| # | Dateiname | Pfad | Ebene | Zweck | Hauptinhalte | Inputs | Outputs | Rolle | Priorität |
|---|-----------|------|-------|-------|-------------|--------|---------|-------|-----------|
| 1 | **GTM_PLAN.md** | `docs/` | Strategisch | Operative Definition der Closed-Beta- und Public-Launch-Strategie | ICP, Value Proposition, Positionierung, Kanäle, Pricing-Hypothese, 90-Tage-Timeline | `vision-wissens-os.md`, `ROADMAP.md`, `PRD-SPEC.md` | Marketing-Tasks, Kanal-Setup, Pricing-Validierung → `TRACKING_PLAN.md`, `LAUNCH_TASKS.md` | Product Owner | **Pflicht** |
| 2 | **LEGAL_COMPLIANCE.md** | `docs/` | Strategisch | Vollständige rechtliche Checkliste für EU-Launch | DSGVO-Consent-Flows, Impressum (DDG), AGB, Datenschutzerklärung, EU AI Act Inventory, Cookie-/Tracking-Consent | `ARCHITECTURE.md`, `PRD-SPEC.md`, `docs/dsgvo-erstkonzept.md`, `legal/` | Rechtstext-Tasks, Consent-Banner-Impl., DPA-Template → `RELEASE_READINESS.md` | Legal / PO | **Pflicht** |
| 3 | **TRACKING_PLAN.md** | `docs/` | Taktisch | Übersetzung strategischer KPIs in konkrete Telemetrie-Events | Event-Taxonomie, Event Properties, User Properties, Trigger-Bedingungen, Funnel-Definitionen | `GTM_PLAN.md`, `PRD-SPEC.md` | Analytics-Implementierungs-Tasks, Dashboard-Setup → `LAUNCH_TASKS.md` | PO / Data | **Pflicht** |
| 4 | **UX_ONBOARDING_SPEC.md** | `docs/` | Taktisch | Vereint UX-Audit und First-Run-Experience in einem Dokument | Heuristische Evaluation, Accessibility-Gaps, Onboarding-Flow (Register → First Briefing), Empty States, Tooltips, Time-to-Value-Optimierung | `PRD-SPEC.md`, `docs/public-beta/onboarding-flow.md`, Staging-Umgebung | UI/UX-Tasks, Onboarding-Implementierung → `LAUNCH_TASKS.md` | UX / PO | **Pflicht** |
| 5 | **SUPPORT_OPERATIONS_PLAN.md** | `docs/` | Taktisch | Definition des laufenden Betriebs, Monitorings und Supports | SLO-Definitionen, Support-Kanäle, Eskalationspfade, Runbook-Index, Alerting-Regeln, Incident-Response-Protokoll | `ARCHITECTURE.md`, `GTM_PLAN.md`, `docs/runbooks/disaster-recovery.md` | Alerting-Setup, Support-Tool-Config, Schulungsunterlagen → `RELEASE_READINESS.md` | Ops / SRE | **Pflicht** |
| 6 | **RELEASE_READINESS.md** | `docs/` | Operativ | Formaler Go/No-Go-Kriterienkatalog vor GA-Deployment | Security-Sign-off, QA-Sign-off, Legal-Sign-off, Ops-Readiness, Rollback-Plan, UAT-Status, Tracking-Verification | Alle Ebene-1- und Ebene-2-Dokumente | Go/No-Go-Entscheidung, Deployment-Freigabe | Engineering Lead | **Pflicht** |
| 7 | **LAUNCH_TASKS.md** | `docs/` | Operativ | Konsolidierte, priorisierte Task-Liste aus allen Launch-Dokumenten | Kategorisierte Tasks (UX, Legal, Ops, GTM, Analytics, Release), jeweils mit Quelle, Priorität, Akzeptanzkriterium | Alle vorherigen Dokumente | Direkte Arbeitsgrundlage für Agenten und Entwickler | PO | **Pflicht** |

## Bewusst NICHT als eigene Dateien

| Konzept | Grund | Wo stattdessen |
|---------|-------|----------------|
| **LAUNCH_BRIEF.md** | Bei Solo-/Kleinteam-Projekt wäre dies eine Dublette zum GTM_PLAN. Ein Launch Brief koordiniert cross-funktionale Teams; hier übernimmt `GTM_PLAN.md` (Strategie) + `RELEASE_READINESS.md` (Checkliste) diese Funktion. | `GTM_PLAN.md` Abschnitt „Timeline & Meilensteine" |
| **UX_AUDIT.md** + **FRE_SPEC.md** | Zwei separate Dateien für eng verzahnte Inhalte erzeugen Redundanz. Audit-Findings fließen direkt in die Onboarding-Spec. | Zusammengelegt in `UX_ONBOARDING_SPEC.md` |
| **INCIDENT_RESPONSE.md** | Existiert bereits als `docs/runbooks/disaster-recovery.md`. Incident-Response-Protokolle gehören in den Operations-Plan + Runbook-Verzeichnis. | `SUPPORT_OPERATIONS_PLAN.md` Abschnitt „Incident Response" + `docs/runbooks/` |
| **LAUNCH_RETRO.md** | Wird erst nach dem Launch erstellt. Kein Planungsdokument, sondern ein Ergebnis-Dokument. Vorlage kann im GTM_PLAN definiert werden. | Erst post-Launch anlegen |
| **GO_NO_GO.md** | Inhaltlich identisch mit Release Readiness Gate. Keine separate Datei nötig. | `RELEASE_READINESS.md` |

---

# 3. Ableitungslogik

## Ableitungsbaum

```
vision-wissens-os.md ─────────┐
ROADMAP.md ───────────────────┤
PRD-SPEC.md ──────────────────┼──► GTM_PLAN.md
                              │        │
                              │        ├──► TRACKING_PLAN.md ──────────┐
                              │        │                               │
                              │        └──► LAUNCH_TASKS.md ◄──────────┤
                              │                  ▲                     │
ARCHITECTURE.md ──────────────┤                  │                     │
docs/dsgvo-erstkonzept.md ────┤                  │                     │
legal/ ───────────────────────┼──► LEGAL_COMPLIANCE.md ────────────────┤
                              │                                        │
PRD-SPEC.md ──────────────────┤                                        │
docs/public-beta/ ────────────┼──► UX_ONBOARDING_SPEC.md ─────────────┤
                              │                                        │
ARCHITECTURE.md ──────────────┤                                        │
docs/runbooks/ ───────────────┼──► SUPPORT_OPERATIONS_PLAN.md ─────────┤
GTM_PLAN.md ──────────────────┘                                        │
                                                                       │
                                   RELEASE_READINESS.md ◄──────────────┘
                                         │
                                         ▼
                                   Go/No-Go-Entscheidung
                                         │
                                         ▼
                                   [LAUNCH_RETRO.md] (post-Launch)
```

## Entscheidungsebenen

| Ebene | Dokument | Typische Entscheidungen |
|-------|----------|------------------------|
| **Strategisch** | GTM_PLAN.md | Wer ist die Zielgruppe? Welche Kanäle? Pricing-Modell? Beta-Strategie open/closed? |
| **Strategisch** | LEGAL_COMPLIANCE.md | Welche Rechtsgrundlagen für Datenverarbeitung? Consent-Pflichten? AGB-Umfang? |
| **Taktisch** | TRACKING_PLAN.md | Welche Events messen wir? Welche Funnels? Welches Analytics-Tool? |
| **Taktisch** | UX_ONBOARDING_SPEC.md | Wie viele Onboarding-Schritte? Welche Empty States? Progressive Disclosure oder Wizard? |
| **Taktisch** | SUPPORT_OPERATIONS_PLAN.md | Welche SLOs? Support-Kanal (E-Mail, Discord, Ticket)? Eskalationsstufen? |
| **Operativ** | RELEASE_READINESS.md | Ist [X] fertig? Ja/Nein-Prüfung auf Basis aller vorherigen Dokumente. |
| **Operativ** | LAUNCH_TASKS.md | Wer macht was bis wann? Abgeleitet aus allen task-relevanten Dokumenten. |

## Punkt der Task-Entstehung

Tasks entstehen **nicht** aus den strategischen Dokumenten direkt, sondern aus der taktischen Ebene:

- `TRACKING_PLAN.md` → Task: „Event `briefing_generated` mit Properties X, Y implementieren"
- `UX_ONBOARDING_SPEC.md` → Task: „Welcome-Screen mit 3-Step-Wizard implementieren"
- `SUPPORT_OPERATIONS_PLAN.md` → Task: „Sentry-Alerting für P0-Incidents konfigurieren"
- `LEGAL_COMPLIANCE.md` → Task: „Cookie-Consent-Banner mit Opt-in implementieren"
- `RELEASE_READINESS.md` → Task: „UAT-Durchlauf mit 5 Test-Nutzern durchführen"

Die strategische Ebene liefert **Rahmenbedingungen** (z.B. „Closed Beta mit max. 20 Nutzern"), die taktische Ebene spezifiziert die **Umsetzungsanforderungen**, und die operative Ebene **konsolidiert und priorisiert** die resultierenden Tasks.

---

# 4. Pflichtkapitel je Datei

---

## 4.1 GTM_PLAN.md

**Ziel:** Definiert, wem das Produkt wie angeboten wird und welche Schritte zwischen „Code Complete" und „öffentlich verfügbar" liegen.

**Pflichtabschnitte:**

1. **Executive Summary** – TL;DR: Was wird gelauncht, für wen, wann.
2. **Ideal Customer Profile (ICP)** – Persona-Definition der Closed-Beta-Zielgruppe. Demographisch, psychographisch, technisch.
3. **Value Proposition & Positionierung** – Kernversprechen in einem Satz. Abgrenzung zu Notion, Obsidian, Mem.ai.
4. **Pricing-Hypothese** – Aktuell: „Free for Early Adopters". Geplante Tier-Struktur für Phase 3+.
5. **Distributionskanäle** – Waitlist, Obsidian Plugin Store, Chrome Web Store, Product Hunt, Hacker News, Discord.
6. **Beta-Strategie** – Closed Beta → Open Beta → GA. Phasen-Definitionen, Zeitrahmen, Entry-/Exit-Kriterien je Phase.
7. **90-Tage-Timeline** – Kalendarische Meilensteine von jetzt bis GA.
8. **Erfolgskennzahlen (KPIs)** – Top-5 Launch-KPIs (z.B. Waitlist Conversion, Time-to-First-Briefing, 7-Day Retention).
9. **Risiken & Mitigationen** – Top-5 Launch-Risiken mit konkreten Gegenmaßnahmen.

**Typische Entscheidungen:** ICP-Eingrenzung, Beta-Modell (invitation-only vs. self-serve), Pricing-Kommunikation, Kanal-Priorisierung.

**Abhängigkeiten:** 
- Input: `vision-wissens-os.md` (Produktvision), `ROADMAP.md` (Phasen), `PRD-SPEC.md` (Features)
- Vorhandene Vorarbeit: `docs/adr/014-beta-launch-strategie.md`, `docs/public-beta/community-setup.md`

**Was NICHT in diese Datei gehört:**
- Technische Architekturentscheidungen (→ `ARCHITECTURE.md`)
- Code-Level-Spezifikationen (→ `PRD-SPEC.md`)
- Rechtliche Details (→ `LEGAL_COMPLIANCE.md`)
- Task-Listen (→ `LAUNCH_TASKS.md`)

**Folgeartefakte:** `TRACKING_PLAN.md`, Marketing-Tasks in `LAUNCH_TASKS.md`, Beta-Invite-Texte

---

## 4.2 LEGAL_COMPLIANCE.md

**Ziel:** Stellt sicher, dass alle zwingenden rechtlichen Anforderungen für einen EU-Launch systematisch erfasst, geprüft und implementiert sind.

**Pflichtabschnitte:**

1. **Regulatorisches Inventar** – Anwendbare Gesetze: DSGVO, DDG (Digitale-Dienste-Gesetz), TDDDG (Telekommunikation-Digitale-Dienste-Datenschutz-Gesetz), EU AI Act. Je Gesetz: Relevanz für PWBS.
2. **DSGVO-Compliance-Matrix** – Verarbeitungszweck, Rechtsgrundlage (Art. 6), Speicherdauer, Löschkonzept, Betroffenenrechte-Umsetzung. Pro Datentyp (Kalender, Notizen, Transkripte, Embeddings).
3. **Consent-Architektur** – Wo ist Einwilligung erforderlich (Analytics, LLM-Verarbeitung, Drittanbieter-Konnektoren)? Granularität der Consent-Optionen. Opt-in vs. Opt-out.
4. **Pflicht-Rechtstexte** – Checklist: Impressum, Datenschutzerklärung, AGB, Cookie-Hinweis, Auftragsverarbeitungsvertrag (AVV). Status je Text (existiert / fehlt / Entwurf).
5. **EU AI Act Relevanz** – Klassifizierung des PWBS (wahrscheinlich: Limited Risk / General Purpose AI). Falls anwendbar: Transparenzpflichten und Kennzeichnung.
6. **Drittanbieter-Datenflüsse** – Inventar: Welche Daten fließen an welche externen Dienste (LLM-APIs, Weaviate Cloud, Sentry)? DPA-Status je Anbieter.
7. **Offene Punkte & Handlungsbedarf** – Priorisierte Liste offener rechtlicher Risiken.

**Typische Entscheidungen:** Rechtsgrundlage pro Verarbeitungszweck, Consent-Granularität, AGB-Umfang (minimal vs. umfassend), Haftungsausschlüsse für LLM-generierte Inhalte.

**Abhängigkeiten:**
- Input: `ARCHITECTURE.md` (Datenflüsse), `PRD-SPEC.md` (Features), `docs/dsgvo-erstkonzept.md`, `docs/encryption-strategy.md`, `legal/tom.md`, `legal/avv/`
- Externe Referenz: aktuelle DSGVO-Anforderungen, DDG, TDDDG

**Was NICHT in diese Datei gehört:**
- Technische Implementierungsdetails (→ `ARCHITECTURE.md`, Code)
- Fertige Rechtstexte (→ eigene Dateien in `legal/`)
- UX-Design der Consent-Dialoge (→ `UX_ONBOARDING_SPEC.md`)

**Folgeartefakte:** Rechtstext-Entwürfe in `legal/`, Consent-Implementierungs-Tasks in `LAUNCH_TASKS.md`, Sign-off-Kriterium in `RELEASE_READINESS.md`

---

## 4.3 TRACKING_PLAN.md

**Ziel:** Übersetzt die im GTM_PLAN definierten KPIs in eine technische Telemetrie-Spezifikation, die vor dem Launch implementiert wird.

**Pflichtabschnitte:**

1. **KPI → Event-Mapping** – Tabelle: Strategischer KPI ↔ Messbare Events ↔ Berechnung.
2. **Event-Taxonomie** – Naming-Convention (z.B. `{object}_{action}`), Event-Katalog mit Properties.
3. **Standard-Events für MVP** – Mindestens:
   - `user_registered`, `user_logged_in`
   - `connector_connected`, `connector_sync_completed`
   - `briefing_generated`, `briefing_viewed`, `briefing_feedback_given`
   - `search_executed`, `search_result_clicked`
   - `onboarding_step_completed`, `onboarding_completed`
4. **User Properties** – Persistente Nutzer-Attribute (z.B. `plan_type`, `connected_sources_count`, `days_since_signup`).
5. **Funnel-Definitionen** – Activation Funnel: Register → Connect Source → First Briefing → Return Visit.
6. **Tooling-Entscheidung** – Welches Analytics-Tool (PostHog Self-Hosted empfohlen für DSGVO)? Warum?
7. **DSGVO-Konformität des Trackings** – Consent-Abhängigkeit pro Event-Kategorie. Anonymisierung.
8. **Dashboard-Spezifikation** – Welche Dashboards werden initial benötigt (Activation, Retention, Funnel)?

**Typische Entscheidungen:** Analytics-Tool-Wahl, Granularität des Trackings, Server-Side vs. Client-Side Tracking, Consent-Pflicht pro Event-Typ.

**Abhängigkeiten:**
- Input: `GTM_PLAN.md` (KPIs), `PRD-SPEC.md` (User Flows)
- Constraint: `LEGAL_COMPLIANCE.md` (Consent-Architektur)

**Was NICHT in diese Datei gehört:**
- Backend-Metriken / Infrastruktur-Monitoring (→ `SUPPORT_OPERATIONS_PLAN.md`, Prometheus/Grafana)
- Business Intelligence / Revenue-Metriken (→ Phase 3)
- Implementierungscode (→ Tasks + Code)

**Folgeartefakte:** Tracking-Implementierungs-Tasks in `LAUNCH_TASKS.md`, Dashboard-Setup-Tasks

---

## 4.4 UX_ONBOARDING_SPEC.md

**Ziel:** Spezifiziert das Nutzererlebnis vom ersten Login bis zum ersten Wertmoment (First Briefing) und identifiziert kritische UX-Hürden vor dem Launch.

**Pflichtabschnitte:**

1. **UX-Audit: Heuristische Evaluation** – Nielsen-Heuristiken gegen aktuelle UI geprüft. Befundliste mit Schweregrad (Critical / Major / Minor).
2. **Accessibility-Quick-Check** – WCAG 2.1 AA Mindestanforderungen: Kontraste, Keyboard-Navigation, Screen-Reader-Labels, Fokus-Management.
3. **Critical User Journey: Register → First Briefing** – Schritt-für-Schritt-Flow mit Screens, Entscheidungspunkten, erwarteter Dauer.
4. **Onboarding-Wizard-Spezifikation** – Anzahl Steps, Skip-Möglichkeit, Inhalte pro Step:
   - Step 1: Willkommen + Wertversprechen (5 Sekunden)
   - Step 2: Erste Datenquelle verbinden (Konnektor-Auswahl)
   - Step 3: Erstes Briefing generieren (Wert sofort sichtbar)
5. **Empty States** – Definierte Empty-State-Texte und CTAs für: Dashboard (kein Briefing), Connectors (keine verbunden), Search (keine Ergebnisse), Knowledge Graph (leer).
6. **Error States** – Nutzerfreundliche Fehlertexte für: OAuth-Fehler, Sync-Fehler, LLM-Timeout.
7. **Time-to-Value-Ziel** – Messbares Ziel: < 5 Minuten von Registration bis erstes Briefing.

**Typische Entscheidungen:** Wizard vs. Progressive Disclosure, Pflicht-Konnektor bei Onboarding ja/nein, Skip-Optionen.

**Abhängigkeiten:**
- Input: `PRD-SPEC.md` (Features), `docs/public-beta/onboarding-flow.md` (bestehender Entwurf)
- Requires: Lauffähige Staging-Umgebung für heuristische Evaluation

**Was NICHT in diese Datei gehört:**
- Visuelle Design-Tokens / Farben / Typografie (→ Tailwind Config / Design System)
- Technische Implementierungsdetails der Komponenten (→ Code)
- Analytics-Event-Definitionen (→ `TRACKING_PLAN.md`)

**Folgeartefakte:** UI/UX-Tasks in `LAUNCH_TASKS.md`, Onboarding-Implementierungs-Tasks, Empty-State-Texte

---

## 4.5 SUPPORT_OPERATIONS_PLAN.md

**Ziel:** Definiert, wie das Produkt nach dem Launch betrieben, überwacht und supportet wird.

**Pflichtabschnitte:**

1. **Service Level Objectives (SLOs)** – Zielwerte für: API-Verfügbarkeit, Response Time (p95), Briefing-Generierungsdauer, Sync-Latenzen. Kein SLA im MVP, aber interne Zielwerte.
2. **Monitoring & Alerting** – Was wird überwacht (Health Checks, Error Rates, Queue Depth)? Alert-Schwellwerte. Eskalationskette bei Alarm.
3. **Incident-Response-Protokoll** – Severity-Stufen (P0–P3), Reaktionszeiten je Stufe, Verantwortliche, Kommunikationsplan (intern + extern). Referenz auf `docs/runbooks/disaster-recovery.md`.
4. **Support-Kanäle** – Welche Kanäle bieten wir an (E-Mail, Discord, In-App-Feedback)? Response-Zeitziele je Kanal.
5. **Runbook-Index** – Verzeichnis aller vorhandenen und noch zu erstellenden Runbooks in `docs/runbooks/`.
6. **Rollback-Strategie** – Wie wird ein fehlerhaftes Deployment zurückgerollt? DB-Migrations-Rollback, Feature-Flag-Deaktivierung.
7. **Kapazitätsplanung** – Erwartete Last (Closed Beta: 20 User → Open Beta: 200 User). Skalierungsgrenzen der aktuellen Infrastruktur.
8. **On-Call-Regelung** – Für Solo-/Kleinteam: Wer ist wann erreichbar? Wie wird bei Abwesenheit verfahren?

**Typische Entscheidungen:** SLO-Werte, Discord vs. E-Mail als primärer Support-Kanal, Alerting-Schwellwerte, Rollback-Verfahren.

**Abhängigkeiten:**
- Input: `ARCHITECTURE.md` (System-Topologie), `GTM_PLAN.md` (erwartete Nutzerzahlen), `docs/runbooks/disaster-recovery.md`
- Vorhandene Infrastruktur: `infra/prometheus/`, `infra/grafana/`

**Was NICHT in diese Datei gehört:**
- Individuelle Runbooks (→ `docs/runbooks/`)
- Detaillierte Infrastruktur-Konfiguration (→ `infra/`, `deploy/`)
- Nutzerseitiger UX-Flow für Fehlermeldungen (→ `UX_ONBOARDING_SPEC.md`)

**Folgeartefakte:** Alerting-Setup-Tasks, Runbook-Erstellungs-Tasks, Support-Tool-Config-Tasks in `LAUNCH_TASKS.md`. Sign-off-Kriterium in `RELEASE_READINESS.md`.

---

## 4.6 RELEASE_READINESS.md

**Ziel:** Formaler, binärer Kriterienkatalog für die Go/No-Go-Entscheidung vor jedem Milestone (Closed Beta, Open Beta, GA).

**Pflichtabschnitte:**

1. **Gate-Definition** – Für welchen Release-Schritt gilt diese Prüfung? (Tabelle mit Gates: Closed Beta, Open Beta, GA)
2. **Prüfkategorien mit Kriterien** – Je Kategorie: Checklisten-Items mit Status (✅/❌/⏳):
   - **Security:** Penetration-Test, Dependency Audit, Secret-Rotation, CORS-Konfiguration
   - **Legal:** Impressum online, Datenschutzerklärung online, AGB online, Consent-Banner funktioniert
   - **Quality:** Test-Coverage ≥ X%, E2E-Happy-Path bestanden, keine P0-Bugs offen
   - **UX:** Onboarding-Flow E2E-getestet, Empty States definiert, Error States nutzerfreundlich
   - **Analytics:** Tracking-Events implementiert und verifiziert, Dashboard funktional
   - **Ops:** Monitoring aktiv, Alerting konfiguriert, Rollback getestet, Backup funktional
   - **Content:** Landing Page aktuell, README aktuell, Changelog aktuell
3. **Rollback-Plan** – Wie wird bei Problemen nach Go zurückgerollt?
4. **Sign-off-Log** – Wer gibt wann welche Kategorie frei? (Audit-Trail)
5. **Known Issues & Accepted Risks** – Bewusst akzeptierte Einschränkungen, die den Launch nicht blockieren.

**Typische Entscheidungen:** Welche Kriterien sind „Must" vs. „Should" je Gate? Welche Known Issues sind akzeptabel?

**Abhängigkeiten:**
- Input: Alle Ebene-1- und Ebene-2-Dokumente (jedes liefert Kriterien)
- Vorhandene Referenzen: `legal/security-audit.md`, `docs/audit-reports/`

**Was NICHT in diese Datei gehört:**
- Detaillierte Spezifikationen (→ jeweilige Quelle)
- Task-Management (→ `LAUNCH_TASKS.md`)
- Post-Launch-Evaluation (→ zukünftige `LAUNCH_RETRO.md`)

**Folgeartefakte:** Go/No-Go-Entscheidung, finale Deployment-Tasks in `LAUNCH_TASKS.md`

---

## 4.7 LAUNCH_TASKS.md

**Ziel:** Konsolidierte, priorisierte Task-Sammlung, die aus allen Launch-Dokumenten extrahiert wird und als direkte Arbeitsgrundlage für Agenten dient.

**Pflichtabschnitte:**

1. **Metadata** – Generierungsdatum, Quell-Dokumente, Versionsstatus.
2. **Task-Tabelle** – Kategorisiert nach: UX, Legal, Ops, GTM, Analytics, Release, Content. Je Task: ID, Titel, Quelle, Priorität (P0–P3), Akzeptanzkriterium, Status.
3. **Abhängigkeitsgraph** – Welche Tasks blockieren welche? Kritischer Pfad.
4. **Sprint-Zuordnung** – Zuordnung zu Zeitfenstern (Woche 1–4).

**Typische Entscheidungen:** Priorisierung, Reihenfolge, Parallelisierbarkeit.

**Abhängigkeiten:**
- Input: Alle vorherigen Dokumente. Jedes taktische Dokument liefert Tasks.

**Was NICHT in diese Datei gehört:**
- Strategische Begründungen (→ in den Quell-Dokumenten nachlesbar)
- Feature-Backlog für Phase 3+ (→ `tasks.md`)
- Abgeschlossene, archivierte Tasks (→ entfernen oder markieren)

**Folgeartefakte:** Direkte Arbeitsanweisungen für Entwicklung, Git-Commits, Pull Requests.

---

# 5. Minimales Set für den PWBS-Fall

## Zwingend zusätzlich (4 Dateien)

Auf Basis der Projektgröße (Solo-/Kleinteam, Closed-Beta-Fokus, EU-Markt, DSGVO-Pflichten):

| # | Datei | Begründung |
|---|-------|------------|
| 1 | **LEGAL_COMPLIANCE.md** | Ohne rechtliche Absicherung ist kein Launch in der EU möglich. DSGVO-Verstöße sind existenzbedrohend. Die vorhandenen Fragmente (`dsgvo-erstkonzept.md`, `legal/`) müssen konsolidiert und zu einer vollständigen Checkliste werden. |
| 2 | **GTM_PLAN.md** | Definiert, wer die ersten 20 Beta-Nutzer sind und wie sie akquiriert werden. Ohne dies ist jede andere Planung spekulativ. |
| 3 | **UX_ONBOARDING_SPEC.md** | Die größte GTM-Gap laut Analyse: Nutzer registrieren sich, wissen aber nicht, was sie tun sollen. Onboarding entscheidet über Retention. |
| 4 | **RELEASE_READINESS.md** | Prüft, ob alles zusammenkommt. Ohne formalen Checkpoint droht ein Launch mit offenen Flanken. |

## Kann unmittelbar danach folgen (2 Dateien)

| # | Datei | Begründung |
|---|-------|------------|
| 5 | **TRACKING_PLAN.md** | Erst relevant, wenn GTM-KPIs definiert sind. Kann parallel zur Onboarding-Arbeit erstellt werden. |
| 6 | **LAUNCH_TASKS.md** | Erst sinnvoll, wenn mindestens GTM + Legal + UX fertig sind und daraus Tasks extrahiert werden können. |

## Nur bei höherer Komplexität (1 Datei)

| # | Datei | Bedingung |
|---|-------|-----------|
| 7 | **SUPPORT_OPERATIONS_PLAN.md** | Wird bei > 50 Beta-Nutzern oder bei SLA-pflichtigen Enterprise-Kunden relevant. Im Closed-Beta mit 20 Nutzern reichen das bestehende Runbook und informelle Prozesse. Spätestens vor Open Beta erstellen. |

---

# 6. Konkrete Erstellungsreihenfolge

## Schritt 1: LEGAL_COMPLIANCE.md

**Warum zuerst:** Rechtliche Anforderungen können technische Implementierung beeinflussen (Consent-Flows, Datenflüsse zu LLM-APIs, Tracking-Einschränkungen). Jede spätere Entscheidung in GTM, Tracking oder UX muss mit den rechtlichen Constraints konsistent sein. Wird dies nachgelagert erstellt, drohen Rückbauten.

**Benötigter Input:**
- `ARCHITECTURE.md` (Datenflüsse, externe Dienste)
- `PRD-SPEC.md` (Features mit Datenverarbeitung)
- `docs/dsgvo-erstkonzept.md` (vorhandene DSGVO-Analyse)
- `legal/tom.md`, `legal/avv/` (vorhandene technisch-organisatorische Maßnahmen)
- `docs/encryption-strategy.md` (Verschlüsselungsstrategie)

**Danach verfügbar:**
- Vollständiges Inventar der rechtlichen Pflichten
- Consent-Architektur als Constraint für Tracking und UX
- Handlungsbedarf-Liste als Input für Tasks

---

## Schritt 2: GTM_PLAN.md

**Warum als zweites:** Definiert die Zielgruppe und damit den Kontext für alle weiteren Spezifikationen. Ohne ICP kann weder Onboarding (für wen?) noch Tracking (was messen?) noch Operations (wie viel Last?) sinnvoll spezifiziert werden.

**Benötigter Input:**
- `vision-wissens-os.md`, `ROADMAP.md`, `PRD-SPEC.md`
- `docs/adr/014-beta-launch-strategie.md` (bereits getroffene Beta-Entscheidungen)
- `docs/public-beta/community-setup.md` (Community-Planung)
- `LEGAL_COMPLIANCE.md` (Constraints für Pricing-Kommunikation, Datennutzung)

**Danach verfügbar:**
- ICP-Definition
- Beta-Phasen und Timeline
- KPI-Definitionen als Input für Tracking
- Kanal-Strategie als Input für Marketing-Tasks

---

## Schritt 3: UX_ONBOARDING_SPEC.md

**Warum als drittes:** Setzt die GTM-Erkenntnisse (wer ist der Nutzer?) in konkrete UX-Anforderungen um. Die Staging-Umgebung ist lauffähig, sodass eine heuristische Evaluation möglich ist.

**Benötigter Input:**
- `PRD-SPEC.md` (Feature-Scope)
- `GTM_PLAN.md` (ICP, Value Proposition)
- `docs/public-beta/onboarding-flow.md` (bestehender Onboarding-Entwurf)
- Lauffähige Staging-Umgebung

**Danach verfügbar:**
- Priorisierte UX-Befundliste
- Onboarding-Flow-Spezifikation
- Empty-State- und Error-State-Texte
- UX-Tasks

---

## Schritt 4: TRACKING_PLAN.md

**Warum als viertes:** Die KPIs aus dem GTM_PLAN und die UX-Flows aus der Onboarding-Spec definieren, welche Events gemessen werden müssen. Die Consent-Architektur aus LEGAL_COMPLIANCE bestimmt die Tracking-Constraints.

**Benötigter Input:**
- `GTM_PLAN.md` (KPIs)
- `UX_ONBOARDING_SPEC.md` (User Flows, Funnel Steps)
- `LEGAL_COMPLIANCE.md` (Consent-Anforderungen)

**Danach verfügbar:**
- Event-Katalog für Implementierung
- Dashboard-Spezifikation
- Tracking-Implementierungs-Tasks

---

## Schritt 5: RELEASE_READINESS.md

**Warum als fünftes:** Konsolidiert die Anforderungen aller vorherigen Dokumente zu prüfbaren Kriterien. Kann erst sinnvoll erstellt werden, wenn die Kriterienquellen existieren.

**Benötigter Input:**
- Alle Ebene-1- und Ebene-2-Dokumente

**Danach verfügbar:**
- Vollständige Go/No-Go-Checkliste
- Klarheit über offene Blocker

---

## Schritt 6: LAUNCH_TASKS.md

**Warum zuletzt:** Extrahiert und konsolidiert Tasks aus allen vorherigen Dokumenten. Ist das Ausführungsartefakt, nicht das Planungsartefakt.

**Benötigter Input:**
- Alle vorherigen Dokumente

**Danach verfügbar:**
- Priorisierte, kategorisierte Arbeitsliste
- Grundlage für Sprint-Planung und Agenten-Orchestrierung

---

# 7. Task-Ableitungssystem

## Task-relevante Dokumenttypen

Nicht alle Dokumente erzeugen gleich viele oder gleich konkrete Tasks:

| Dokumenttyp | Task-Dichte | Task-Art |
|-------------|-------------|----------|
| `GTM_PLAN.md` | Mittel | Marketing-Tasks (Texte, Kanäle), Kommunikations-Tasks |
| `LEGAL_COMPLIANCE.md` | Hoch | Implementierungs-Tasks (Consent, Rechtstexte), Prüf-Tasks |
| `TRACKING_PLAN.md` | Hoch | Reine Implementierungs-Tasks (Events, Dashboards) |
| `UX_ONBOARDING_SPEC.md` | Hoch | UI-Implementierungs-Tasks, Content-Tasks (Texte, Empty States) |
| `SUPPORT_OPERATIONS_PLAN.md` | Mittel | Konfigurations-Tasks (Alerting, Monitoring), Prozess-Tasks |
| `RELEASE_READINESS.md` | Niedrig | Verifikations-Tasks (Prüfung, Sign-off), Lücken-Tasks |

## Regeln für Task-Extraktion

1. **Jede offene Anforderung in einem taktischen Dokument wird zu einem Task.** Beispiel: „Cookie-Consent-Banner implementieren" im LEGAL_COMPLIANCE.md → Task.
2. **Jede ❌-Markierung in RELEASE_READINESS.md wird zu einem Task**, sofern sie einen „Must"-Kriterium betrifft.
3. **Tasks werden immer mit ihrer Quelle verlinkt.** Format: `Quelle: LEGAL_COMPLIANCE.md § Consent-Architektur`
4. **Keine Dopplung.** Wenn derselbe Task in zwei Dokumenten entsteht, wird er einmal erfasst mit beiden Quellen.
5. **Tasks sind atomar.** „Legal-Texte erstellen" ist kein guter Task. „Datenschutzerklärung für PWBS erstellen und in `/legal/` ablegen" ist ein guter Task.
6. **Jeder Task hat ein binäres Akzeptanzkriterium.** Beispiel: „Consent-Banner wird beim ersten Besuch angezeigt und speichert Auswahl im Cookie."

## Task-Kategorien

| Kategorie | Präfix | Beispiel |
|-----------|--------|----------|
| **UX** | `UX-` | `UX-001: Welcome-Screen mit 3-Step-Wizard implementieren` |
| **Legal** | `LEG-` | `LEG-001: Datenschutzerklärung erstellen und unter /legal/datenschutz.md ablegen` |
| **Ops** | `OPS-` | `OPS-001: Sentry-Alerting für HTTP 5xx > 5/min konfigurieren` |
| **GTM** | `GTM-` | `GTM-001: Product-Hunt-Listing vorbereiten (Beschreibung, Screenshots)` |
| **Analytics** | `ANA-` | `ANA-001: Event briefing_generated mit properties owner_id, briefing_type implementieren` |
| **Release** | `REL-` | `REL-001: E2E-UAT-Durchlauf Register → Connect → Briefing dokumentieren` |
| **Content** | `CNT-` | `CNT-001: Landing-Page-Copy für Beta-Phase aktualisieren` |

## Pflichtfelder pro Task

```markdown
### [KATEGORIE]-[NR]: [Titel]

- **Quelle:** [Dokumentname] § [Abschnitt]
- **Priorität:** P0 / P1 / P2 / P3
- **Kategorie:** UX / Legal / Ops / GTM / Analytics / Release / Content
- **Akzeptanzkriterium:** [Binäre Aussage: wann ist der Task erledigt?]
- **Abhängigkeit:** [Task-IDs, die vorher erledigt sein müssen, oder „keine"]
- **Status:** Offen / In Arbeit / Fertig
```

---

# 8. Konkrete Empfehlung

## Empfohlene Zielstruktur (alle 7 Dateien)

```
docs/
├── GTM_PLAN.md                    ← Strategisch: Markt, Zielgruppe, Kanäle, Timeline
├── LEGAL_COMPLIANCE.md            ← Strategisch: Rechtsrahmen, Consent, Pflicht-Texte
├── TRACKING_PLAN.md               ← Taktisch: Events, Funnels, Dashboards
├── UX_ONBOARDING_SPEC.md          ← Taktisch: UX-Audit + Onboarding-Flow
├── SUPPORT_OPERATIONS_PLAN.md     ← Taktisch: SLOs, Monitoring, Incident Response
├── RELEASE_READINESS.md           ← Operativ: Go/No-Go-Checkliste
└── LAUNCH_TASKS.md                ← Operativ: Konsolidierte Task-Sammlung
```

## Empfohlene Minimalstruktur (4 Dateien)

Für den Closed-Beta-Launch mit ≤ 20 Nutzern:

```
docs/
├── LEGAL_COMPLIANCE.md            ← Nicht verhandelbar für EU-Launch
├── GTM_PLAN.md                    ← Definiert Zielgruppe und Beta-Strategie
├── UX_ONBOARDING_SPEC.md          ← Größte Retention-Hürde adressieren
└── RELEASE_READINESS.md           ← Formaler Checkpoint vor Go-Live
```

## Empfohlene nächste Datei: LEGAL_COMPLIANCE.md

**Begründung:** Die rechtliche Absicherung ist die einzige Dimension, die den Launch **objektiv blockieren** kann. Technische Mängel lassen sich iterativ beheben, UX-Probleme durch schnelles Nutzer-Feedback korrigieren – aber ein fehlender DSGVO-Consent-Flow oder eine fehlende Datenschutzerklärung riskiert Abmahnungen und Bußgelder. Zudem beeinflusst die Consent-Architektur direkt das Tracking (was darf gemessen werden?) und die UX (wo erscheinen Consent-Dialoge?), weshalb alle nachfolgenden Dokumente diese Constraints benötigen.

Die vorhandenen Fragmente (`docs/dsgvo-erstkonzept.md`, `legal/tom.md`, `legal/avv/`, `docs/encryption-strategy.md`) liefern bereits substanziellen Input. Der nächste Schritt ist die Konsolidierung dieser Fragmente in eine vollständige, prüfbare Compliance-Matrix.

---

## Zusammenfassung: Ableitungskette kompakt

```
[VORHANDEN]     →  [SCHRITT 1]          →  [SCHRITT 2]      →  [SCHRITT 3]
VISION             LEGAL_COMPLIANCE         GTM_PLAN             UX_ONBOARDING_SPEC
ARCHITECTURE       (Rechtsrahmen)           (Markt + Beta)       (Onboarding-Flow)
ROADMAP                ↓                        ↓                     ↓
PRD-SPEC          [SCHRITT 4]            [SCHRITT 5]          [SCHRITT 6]
                   TRACKING_PLAN          RELEASE_READINESS     LAUNCH_TASKS
                   (Events + KPIs)        (Go/No-Go)           (Konsolidiert)
```

Jedes Dokument hat genau einen Zweck, genau definierte Inputs und erzeugt genau definierte Outputs. Keine Datei dupliziert eine andere. Die Kette ist so gebaut, dass jedes neue Dokument die Outputs der vorherigen als Input nutzt – und dass am Ende ein Satz konkreter, priorisierter Tasks steht, der direkt in die Umsetzung überführt werden kann.
