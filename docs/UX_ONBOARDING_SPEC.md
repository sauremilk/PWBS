# UX-Audit & Onboarding-Spezifikation – PWBS

**Version:** 1.0
**Datum:** 17. März 2026
**Status:** Aktiv
**Basisdokumente:** [PRD-SPEC.md](../PRD-SPEC.md), [GTM_PLAN.md](GTM_PLAN.md), [onboarding-flow.md](public-beta/onboarding-flow.md), [ARCHITECTURE.md](../ARCHITECTURE.md)

---

## Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [UX-Audit: Heuristische Evaluation](#2-ux-audit-heuristische-evaluation)
3. [Accessibility-Quick-Check](#3-accessibility-quick-check)
4. [Critical User Journey: Register → First Briefing](#4-critical-user-journey-register--first-briefing)
5. [Onboarding-Wizard-Spezifikation](#5-onboarding-wizard-spezifikation)
6. [Empty States](#6-empty-states)
7. [Error States](#7-error-states)
8. [Time-to-Value-Optimierung](#8-time-to-value-optimierung)
9. [Priorisierte Maßnahmenliste](#9-priorisierte-maßnahmenliste)

---

## 1. Executive Summary

### Ziele

| Ziel         | Metrik                            | Zielwert                 |
| ------------ | --------------------------------- | ------------------------ |
| **Primär**   | Time-to-First-Briefing            | < 5 Minuten (Self-Serve) |
| **Sekundär** | Onboarding-Completion-Rate        | > 70 %                   |
| **Tertiär**  | Konnektor-Verbindungs-Erfolgsrate | > 90 %                   |

### Kritischste UX-Befunde

1. **Retention-Lücke zwischen Registration und erstem Briefing:** Der Onboarding-Wizard (`OnboardingWizard` in `frontend/src/components/onboarding/onboarding-wizard.tsx`) existiert als 4-Schritt-Flow, liefert aber keinen Fortschrittsindikator mit Zeitschätzung. Nutzer wissen nicht, wie lange der Sync dauert, und brechen ab.

2. **Kein Fallback bei langsamem Sync:** Wenn die initiale Datensynchronisation > 2 Minuten dauert, fehlt ein Demo-Briefing oder Partial-Briefing als Zwischenergebnis. Der Nutzer sieht nur einen Spinner ohne kontextuelle Erklärung.

3. **Empty States sind funktional, aber nicht motivierend:** Die bestehende `EmptyStates`-Komponente (`frontend/src/components/ui/empty-states.tsx`) zeigt generische Hinweise. Es fehlen personalisierte CTAs, die den Nutzer zum nächsten logischen Schritt führen.

4. **Error States ohne Recovery-Pfad:** `ErrorCard` und `NetworkErrorBanner` (`frontend/src/components/ui/error-states.tsx`) zeigen Fehlermeldungen, bieten aber keinen spezifischen Recovery-Pfad für OAuth-Fehler, Sync-Timeouts oder LLM-Ausfälle.

5. **Kein Fortschritts-Tracking über Sessions hinweg:** Wenn ein Nutzer den Onboarding-Wizard abbricht und später zurückkehrt, startet er nicht automatisch am letzten Schritt. Die `OnboardingGate` (`frontend/src/components/onboarding/onboarding-gate.tsx`) prüft nur, ob Onboarding abgeschlossen ist – nicht, wo der Nutzer steht.

---

## 2. UX-Audit: Heuristische Evaluation

Die folgende Evaluation basiert auf der Inspektion der Frontend-Codebase (`frontend/src/`) und prüft gegen die 10 Nielsen-Heuristiken.

### 2.1 Sichtbarkeit des Systemstatus

**Bewertung: ⚠️ Verbesserungswürdig**

**Befund:**

- Loading States sind gut implementiert: `Spinner`, `PageLoader`, `BriefingCardSkeleton`, `ConnectorStatusSkeleton`, `SearchResultSkeleton` und `DashboardWidgetSkeleton` in `frontend/src/components/ui/loading-states.tsx` geben visuelles Feedback.
- Der Sync-Schritt im Onboarding-Wizard zeigt einen Fortschrittsindikator (`StepSync`), aber ohne geschätzte Restdauer.
- Der WebSocket-Status-Indikator (`ws-status-indicator.tsx`) zeigt den Verbindungsstatus in der Footer-Leiste.
- `SyncHistoryAccordion` in `frontend/src/components/connectors/sync-history-accordion.tsx` zeigt vergangene Syncs mit Timestamp, Dokumentenanzahl und Dauer.

**Empfehlung:**

- Im Sync-Schritt des Onboarding-Wizards eine geschätzte Restdauer anzeigen (z.B. „Noch ca. 30 Sekunden – wir importieren deine Termine").
- Bei der Briefing-Generierung einen Mehrstufen-Fortschritt anzeigen: „Daten werden analysiert → Kontext wird aufgebaut → Briefing wird erstellt".

---

### 2.2 Übereinstimmung zwischen System und realer Welt

**Bewertung: ✅ Gut**

**Befund:**

- Die Sprache ist durchgehend Deutsch und nutzergerecht: „Briefing", „Datenquelle verbinden", „Konnektoren", „Suche".
- Die Navigation in `frontend/src/components/layout/sidebar.tsx` verwendet verständliche Labels: „Dashboard", „Briefings", „Projekte", „Suche", „Knowledge", „Entscheidungen", „Konnektoren".
- Icons aus Lucide (LayoutDashboard, FileText, FolderKanban, Search, Network, Scale, Cable, Shield) unterstützen die Verständlichkeit.
- Das Consent-Dialog (`frontend/src/components/connectors/consent-dialog.tsx`) erklärt Datenverarbeitungszwecke und LLM-Provider in verständlicher Sprache.

**Empfehlung:**

- „Knowledge" in der Navigation könnte als „Wissensgraph" oder „Wissenslandkarte" für deutschsprachige Nutzer verständlicher sein.

---

### 2.3 Nutzerkontrolle und Freiheit

**Bewertung: ⚠️ Verbesserungswürdig**

**Befund:**

- Der Onboarding-Wizard bietet einen „Überspringen"-Link auf allen Schritten – Nutzer können den Wizard verlassen.
- Konnektoren können über die Settings-Seite getrennt werden (US-5.1: kaskadierte Löschung aller Daten der Quelle).
- Account-Löschung hat eine 30-Tage-Karenzfrist mit Rücknahme-Option (US-5.3).
- `FocusTrap` in `frontend/src/components/ui/focus-trap.tsx` gibt Fokus korrekt zurück nach dem Schließen von Modalen.

**Empfehlung:**

- Im Onboarding-Wizard einen sichtbaren „Zurück"-Button pro Schritt implementieren (aktuell nur vorwärts-Navigation).
- Nach dem Überspringen des Wizards: einen persistenten, aber nicht-aufdringlichen Banner anzeigen, der zum Abschließen des Onboardings einlädt.

---

### 2.4 Konsistenz und Standards

**Bewertung: ✅ Gut**

**Befund:**

- Die Tailwind-Konfiguration (`frontend/tailwind.config.ts`) nutzt ein konsistentes CSS-Variablen-basiertes Farbsystem: `brand`, `surface`, `sidebar`, `text`, `border` – alle als `rgb(var(--color-*))`.
- Status-Farben sind einheitlich: `emerald` (Erfolg), `red` (Fehler), `amber` (Warnung), `indigo` (primär/Brand).
- Animationen sind standardisiert: `fade-in`, `slide-in`, `slide-up`, `scale-in` mit einheitlichen 200ms/300ms Timings.
- Alle API-Aufrufe laufen über den zentralen `apiClient` in `frontend/src/lib/api-client.ts` mit automatischem JWT-Handling und 401-Retry-Logik.
- Button-Styles, Card-Layouts und Spacing folgen einem erkennbaren System.

**Empfehlung:**

- Keine kritischen Inkonsistenzen identifiziert.

---

### 2.5 Fehlervermeidung

**Bewertung: ⚠️ Verbesserungswürdig**

**Befund:**

- Registrierung: Echtzeit-Passwort-Validierung in `frontend/src/app/(auth)/register/page.tsx` zeigt Kriterien (≥ 12 Zeichen, Großbuchstabe, Ziffer) während der Eingabe. Submit-Button ist disabled bis alle Kriterien erfüllt sind. Das ist gute Fehlervermeidung.
- OAuth-Consent wird über `ConsentDialog` vor dem Flow erklärt – Nutzer wissen vorher, welche Daten geteilt werden.
- `SyncHistoryAccordion` zeigt vergangene Fehler expandierbar an.

**Empfehlung:**

- Vor dem OAuth-Flow einen Hinweis anzeigen, dass ein Pop-up-Fenster geöffnet wird (Pop-up-Blocker können den Flow unterbrechen).
- Bei der Obsidian-Vault-Pfadeingabe: Beispielpfad und Format-Hinweis voranstellen, bevor der Nutzer einen ungültigen Pfad eingibt.

---

### 2.6 Wiedererkennung statt Erinnerung

**Bewertung: ⚠️ Verbesserungswürdig**

**Befund:**

- Die Sidebar-Navigation (`frontend/src/components/layout/sidebar.tsx`) zeigt aktive Seiten mit `bg-sidebar-active`-Styling und `aria-current="page"` an.
- Das Dashboard (`frontend/src/app/(dashboard)/page.tsx`) zeigt den aktuellen Briefing-Status, verbundene Konnektoren und Quick Actions auf einen Blick.
- Suchverlauf wird über `searchApi.getHistory` bereitgestellt.

**Empfehlung:**

- Im Onboarding: Den Fortschritt des Nutzers persistent speichern und beim erneuten Login visuell anzeigen (z.B. „Du hast bereits Google Calendar verbunden – verbinde jetzt eine weitere Quelle").
- Auf dem Dashboard: Den zuletzt verbundenen Konnektor und den Zeitpunkt des letzten Syncs prominent anzeigen.

---

### 2.7 Flexibilität und Effizienz

**Bewertung: ✅ Gut**

**Befund:**

- Power-User-Features sind vorhanden: Manueller Sync-Trigger pro Konnektor, Briefing-Regenerierung, Suchfilter nach Entitätstyp und Zeitraum.
- Quick Actions auf dem Dashboard bieten Shortcuts für häufige Aktionen.
- Die Suchseite unterstützt natürlichsprachliche Eingaben mit Filter-Kombinationen.
- API-Client unterstützt alle CRUD-Operationen programmatisch.

**Empfehlung:**

- Keyboard-Shortcuts für häufige Aktionen (z.B. `/` zum Fokussieren der Suche, `Ctrl+B` für neues Briefing) implementieren.

---

### 2.8 Ästhetisches und minimalistisches Design

**Bewertung: ✅ Gut**

**Befund:**

- Das Design folgt einem klaren, reduzierten Stil: Slate-Töne für die Auth-Seiten mit Glasmorphism-Effekten (Gradient-Blur-Orbs in indigo/purple).
- Dashboard nutzt ein 2-spaltiges Layout mit Sidebar + Content, responsive ab `md:` Breakpoint.
- Skeleton-Loaders statt Spinner für Content-Bereiche – erhält die Layout-Stabilität.
- Cards, Badges und Status-Dots verwenden einheitliches visuelles Vokabular.

**Empfehlung:**

- Im Onboarding-Wizard: Die visuelle Dichte reduzieren. Jeder Schritt sollte maximal eine Aktion vom Nutzer erfordern. Texte auf das Minimum beschränken.

---

### 2.9 Fehlererkennung, -diagnose und -behebung

**Bewertung: ❌ Kritisch**

**Befund:**

- `ErrorBoundary` (`frontend/src/components/ui/error-boundary.tsx`) fängt React-Fehler ab und zeigt `error.message` mit „Retry"-Button.
- `ErrorCard` zeigt generische Fehlermeldungen mit rotem AlertTriangle-Icon und Retry-Button.
- `NetworkErrorBanner` zeigt einen gelben Banner bei Netzwerkausfall (WifiOff-Icon).
- `DashboardError` (`frontend/src/app/(dashboard)/error.tsx`) zeigt route-level Fehler mit Reset-Option.

**Problem:** Die Fehlermeldungen sind generisch (`error.message` direkt angezeigt). Technische Fehlermeldungen des Backends (z.B. „500 Internal Server Error", „Connection refused") werden ungefiltert weitergegeben. Es fehlen:

- Nutzerfreundliche Übersetzungen technischer Fehler
- Spezifische Recovery-Pfade je nach Fehlertyp
- Kontextuelle Hilfe (z.B. „OAuth-Zeitlimit überschritten – bitte versuche es erneut")

**Empfehlung:**

- Ein Error-Mapping implementieren, das Backend-Fehlercodes in nutzerfreundliche deutsche Texte mit konkreten Recovery-Aktionen übersetzt (siehe Abschnitt 7).
- Für OAuth-Fehler, Sync-Fehler und LLM-Timeouts spezifische Error-Komponenten erstellen.

---

### 2.10 Hilfe und Dokumentation

**Bewertung: ❌ Kritisch**

**Befund:**

- Keine In-App-Hilfe, Tooltips oder kontextuelle Erklärungen in der aktuellen Codebase identifiziert.
- Kein FAQ-Bereich, kein Hilfe-Center, keine Wissensdatenbank für Endnutzer.
- Der Onboarding-Wizard enthält kurze Erklärungstexte pro Schritt, aber keine weiterführenden Links.
- Kein Onboarding-Fortschritts-Checklist nach dem Wizard.

**Empfehlung:**

- Tooltips an kritischen Stellen implementieren: Konnektor-Auswahl (was wird importiert), Briefing-Typen (wann wird was generiert), Suchsyntax.
- Eine „Was kann ich hier tun?"-Hilfe-Overlay pro Seite als optionales Feature.
- Post-Onboarding-Checklist auf dem Dashboard: „Nächste Schritte: Weitere Quelle verbinden / Erste Suche durchführen / Briefing-Einstellungen anpassen".

---

### Zusammenfassung der heuristischen Evaluation

| #   | Heuristik                                | Bewertung              |
| --- | ---------------------------------------- | ---------------------- |
| 1   | Sichtbarkeit des Systemstatus            | ⚠️ Verbesserungswürdig |
| 2   | Übereinstimmung System/Realwelt          | ✅ Gut                 |
| 3   | Nutzerkontrolle und Freiheit             | ⚠️ Verbesserungswürdig |
| 4   | Konsistenz und Standards                 | ✅ Gut                 |
| 5   | Fehlervermeidung                         | ⚠️ Verbesserungswürdig |
| 6   | Wiedererkennung statt Erinnerung         | ⚠️ Verbesserungswürdig |
| 7   | Flexibilität und Effizienz               | ✅ Gut                 |
| 8   | Ästhetisches und minimalistisches Design | ✅ Gut                 |
| 9   | Fehlererkennung, -diagnose und -behebung | ❌ Kritisch            |
| 10  | Hilfe und Dokumentation                  | ❌ Kritisch            |

---

## 3. Accessibility-Quick-Check

### 3.1 Farbkontraste

**Bewertung: ⚠️ Codebase-Review erforderlich: CSS-Variablenwerte**

**Befund:**

- Die Tailwind-Konfiguration nutzt CSS-Variablen (`--color-text`, `--color-surface`, etc.) – die tatsächlichen RGB-Werte sind in einer separaten CSS-Datei definiert, die nicht direkt inspiziert wurde.
- Hard-coded Status-Farben: `emerald-50` auf `emerald-500`, `red-50` auf `red-500`, `amber-50` auf `amber-500` – diese Kombinationen erfüllen typischerweise WCAG AA-Kontrast (4.5:1 für normalen Text).
- Auth-Seiten nutzen `slate-900` Background mit hellen Texten – vermutlich ausreichender Kontrast, aber die Glasmorphism-Overlays (indigo/purple Gradients mit Blur) können die Lesbarkeit beeinträchtigen.

**Empfehlung:**

- Lighthouse Accessibility-Audit auf allen Seiten ausführen und Kontrastverhältnisse der CSS-Variablen-Werte verifizieren.
- Bei den Auth-Seiten sicherstellen, dass Text auf den Gradient-Blur-Orbs mindestens 4.5:1 Kontrast behält.

---

### 3.2 Keyboard-Navigation

**Bewertung: ✅ Gut**

**Befund:**

- `SkipLink` in `frontend/src/components/ui/skip-link.tsx` implementiert: „Zum Hauptinhalt springen" als visuell versteckter Link (`sr-only`, sichtbar bei `:focus`), springt zu `#main-content`.
- `FocusTrap` in `frontend/src/components/ui/focus-trap.tsx` fängt Tab-Navigation in Modalen korrekt ein: Shift+Tab auf dem ersten Element springt zum letzten, Tab auf dem letzten zum ersten. Nach dem Schließen wird der Fokus korrekt zum Trigger-Element zurückgegeben.
- Sidebar-Navigation zeigt `aria-current="page"` auf dem aktiven Link.

**Empfehlung:**

- Sicherstellen, dass der Onboarding-Wizard-Modal den `FocusTrap` einsetzt (der `OnboardingWizard` nutzt `z-50` und `bg-black/50` Backdrop, aber die `FocusTrap`-Nutzung sollte explizit verifiziert werden).
- Keyboard-Shortcut-Dokumentation als Hilfe-Overlay bereitstellen.

---

### 3.3 Screen-Reader-Labels

**Bewertung: ✅ Gut**

**Befund:**

- `aria-label` auf interaktiven Elementen: Buttons („Schließen", „Navigation öffnen"), Sidebar-Toggle.
- `aria-modal="true"` auf Dialogen (ConsentDialog, OnboardingWizard).
- `aria-labelledby="dialog-title"` verbindet Dialogtitel mit dem Modal.
- `role="status"` auf Loading-Spinner für Live-Region-Announcements.
- `<span className="sr-only">` für Screen-Reader-only Text an Icons und Status-Indikatoren.
- `aria-hidden="true"` auf dekorativen Icons.

**Empfehlung:**

- Die `StepIndicator`-Komponente im Onboarding-Wizard sollte `aria-valuenow` und `aria-valuemax` tragen, um den aktuellen Schritt für Screen-Reader zu kommunizieren.
- Error-Announcements bei Formularfehlern über `aria-live="polite"` oder `role="alert"` sicherstellen.

---

### 3.4 Fokus-Management bei Modals/Dialogen

**Bewertung: ✅ Gut**

**Befund:**

- `FocusTrap` erfasst alle fokussierbaren Elemente per Selector (Links, Buttons, Inputs, Textareas, Selects, Elemente mit `tabindex`).
- Tab-Cycling funktioniert korrekt (vorwärts und rückwärts).
- Focus-Return zum Trigger-Element nach dem Schließen ist implementiert (`returnFocusTo`-Prop).

**Empfehlung:**

- Bei Auto-Advance im Onboarding (Sync → Briefing) den Fokus explizit auf die neue Schritt-Überschrift setzen, damit Screen-Reader den Kontextwechsel erfassen.

---

### 3.5 Formular-Labels und Error-Announcements

**Bewertung: ⚠️ Verbesserungswürdig**

**Befund:**

- Registrierungsformular (`frontend/src/app/(auth)/register/page.tsx`): Passwort-Validierungskriterien werden visuell mit Farben (rot/grün) und Symbolen (✕/✓) angezeigt.
- Login-Formular nutzt `<label htmlFor="id">` für Input-Verbindung.
- Semantisches HTML: `<form>`, nicht `<div>`, für Formulare.

**Empfehlung:**

- Passwort-Validierungskriterien zusätzlich mit `aria-live="polite"` oder `aria-describedby` an das Passwortfeld binden, damit Screen-Reader Änderungen mitteilen.
- Bei Formular-Submit-Fehlern eine `role="alert"`-Region nutzen, die den Fehlertext automatisch vorliest.
- Die visuelle Farbcodierung (rot/grün) der Passwort-Kriterien um ein zusätzliches Textsymbol ergänzen (bereits vorhanden als ✕/✓ – das ist korrekt).

---

### Zusammenfassung Accessibility

| Kriterium            | WCAG 2.1 AA   | Bewertung                       |
| -------------------- | ------------- | ------------------------------- |
| Farbkontraste        | 1.4.3 / 1.4.6 | ⚠️ Codebase-Review erforderlich |
| Keyboard-Navigation  | 2.1.1 / 2.1.2 | ✅ Gut                          |
| Screen-Reader-Labels | 4.1.2 / 1.3.1 | ✅ Gut                          |
| Fokus-Management     | 2.4.3 / 2.4.7 | ✅ Gut                          |
| Formular-Labels      | 1.3.1 / 3.3.2 | ⚠️ Verbesserungswürdig          |

---

## 4. Critical User Journey: Register → First Briefing

### Flow-Übersicht

| #   | Schritt                       | Screen/Route                        | Nutzeraktion                                                               | System-Reaktion                                                                              | Erwartete Dauer | Potenzielle Abbruchstelle                                                           |
| --- | ----------------------------- | ----------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | --------------- | ----------------------------------------------------------------------------------- |
| 1   | Landing Page                  | `/` (Landing)                       | Klickt auf CTA „Kostenlos starten" oder „Jetzt registrieren"               | Weiterleitung zu `/register`                                                                 | 5–10 Sek.       | CTA nicht sichtbar above-the-fold (Mobile); Value Proposition unklar                |
| 2   | Registrierung                 | `/register`                         | Gibt E-Mail, Passwort (≥ 12 Z., Großbuchstabe, Ziffer) und Anzeigename ein | Echtzeit-Passwort-Validierung; bei Submit: Account erstellen, DEK generieren, JWT ausstellen | 30–60 Sek.      | Passwort-Anforderungen zu komplex; generische Fehlermeldung bei Duplikat-E-Mail     |
| 3   | Welcome-Screen                | `/register` (Post-Success-View)     | Liest Begrüßung; klickt auf „Konnektoren einrichten"                       | Weiterleitung zum Dashboard mit Onboarding-Wizard                                            | 5 Sek.          | „Später einrichten"-Option führt zum leeren Dashboard ohne Orientierung             |
| 4   | Onboarding-Wizard: Willkommen | Dashboard `/` + Modal Overlay       | Liest Value Proposition; klickt auf „Los geht's"                           | Wizard schreitet zu Schritt 2 fort                                                           | 5 Sek.          | –                                                                                   |
| 5   | Konnektor-Auswahl             | Wizard Schritt 2                    | Wählt einen der 4 Konnektoren (Google Calendar empfohlen)                  | ConsentDialog öffnet sich mit Datentypen, Verarbeitungszweck, LLM-Providern                  | 10–15 Sek.      | Nutzer versteht nicht, warum die Daten geteilt werden; überspringt aus Unsicherheit |
| 6   | DSGVO-Consent                 | ConsentDialog Modal                 | Aktiviert Checkbox „Ich stimme zu…"; klickt auf „Zugriff gewähren"         | Redirect zum OAuth-Provider (Google, Notion, Zoom)                                           | 5 Sek.          | Consent-Text zu lang; Checkbox wird übersehen                                       |
| 7   | OAuth-Flow                    | Externe Seite (Google/Notion/Zoom)  | Meldet sich beim Provider an; erteilt Scopes                               | OAuth-Callback an Backend; Token wird verschlüsselt gespeichert                              | 15–30 Sek.      | Pop-up-Blocker; Nutzer verweigert Zugriff; Netzwerkfehler beim Token-Exchange       |
| 8   | OAuth-Callback + Sync-Start   | Wizard Schritt 3 (StepSync)         | Wartet; sieht Fortschrittsindikator                                        | Initial-Sync startet automatisch; Dokumente werden importiert und verarbeitet                | 30–120 Sek.     | Sync dauert zu lang (> 2 Min.); kein Feedback, was passiert; Nutzer schließt Tab    |
| 9   | Briefing-Generierung          | Wizard Schritt 4 (StepBriefing)     | Wartet; sieht Briefing-Generierungsanzeige                                 | ProcessingAgent erzeugt Embeddings; BriefingAgent generiert Morning Briefing                 | 10–30 Sek.      | LLM-Timeout; zu wenig Daten für sinnvolles Briefing                                 |
| 10  | Erstes Briefing anzeigen      | Wizard Schritt 4 (Briefing-Anzeige) | Liest Briefing mit Quellenreferenzen; klickt „Zum Dashboard"               | Wizard wird geschlossen; Onboarding als abgeschlossen markiert; Dashboard zeigt Briefing     | 30–60 Sek.      | Briefing irrelevant (zu wenig Daten); kein Aha-Moment                               |

### Fehlerszenarien pro Schritt

#### Schritt 2: Registrierung

| Fehler             | Auslöser                   | Aktuelle Behandlung                                 | Empfohlene Behandlung                                                                                  |
| ------------------ | -------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Duplikat-E-Mail    | E-Mail bereits registriert | 409-Fehler → „E-Mail wird bereits verwendet"        | Beibehalten (sicherheitskonform, kein E-Mail-Enumeration)                                              |
| Schwaches Passwort | Kriterien nicht erfüllt    | Submit-Button disabled + visuelle Kriterien-Anzeige | Zusätzlich: `aria-live="polite"` für Screen-Reader                                                     |
| Netzwerkfehler     | Keine Verbindung           | Generische Fehlermeldung                            | Spezifischer Hinweis: „Keine Internetverbindung. Bitte prüfe deine Verbindung und versuche es erneut." |

#### Schritt 7: OAuth-Flow

| Fehler                        | Auslöser                               | Aktuelle Behandlung      | Empfohlene Behandlung                                                                                                                        |
| ----------------------------- | -------------------------------------- | ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Zugriff verweigert            | Nutzer klickt „Ablehnen" beim Provider | Fehlermeldung im Wizard  | Spezifischer Text: „Du hast den Zugriff nicht erteilt. Ohne Verbindung können wir keine Daten importieren. Möchtest du es erneut versuchen?" |
| Token-Exchange fehlgeschlagen | Backend-Fehler beim Callback           | Generische Fehlermeldung | „Die Verbindung konnte nicht hergestellt werden. Bitte versuche es in einer Minute erneut."                                                  |
| Pop-up blockiert              | Browser blockiert OAuth-Fenster        | Kein Feedback            | Hinweis: „Dein Browser hat ein Fenster blockiert. Bitte erlaube Pop-ups für diese Seite."                                                    |

#### Schritt 8: Sync

| Fehler                | Auslöser                       | Aktuelle Behandlung                 | Empfohlene Behandlung                                                                                                                                        |
| --------------------- | ------------------------------ | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| API nicht erreichbar  | Provider-API down              | Fehlermeldung nach Timeout          | „Der Dienst [Google Calendar] ist gerade nicht erreichbar. Wir versuchen es automatisch erneut. Du kannst in der Zwischenzeit eine andere Quelle verbinden." |
| Keine Daten vorhanden | Leerer Kalender / leerer Vault | Sync abgeschlossen mit 0 Dokumenten | „Wir haben noch keine Daten gefunden. Hast du Termine in deinem Kalender? Versuche alternativ eine andere Quelle."                                           |

#### Schritt 9: Briefing-Generierung

| Fehler         | Auslöser                              | Aktuelle Behandlung          | Empfohlene Behandlung                                                                                                                                    |
| -------------- | ------------------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LLM-Timeout    | Claude/GPT antwortet nicht in 30 Sek. | Timeout-Fehler               | „Die Briefing-Erstellung dauert etwas länger als üblich. Wir senden dir eine Benachrichtigung, sobald es fertig ist." + Fallback: Demo-Briefing anzeigen |
| Zu wenig Daten | < 3 Dokumente importiert              | Briefing mit geringem Inhalt | Transparenter Hinweis: „Dein erstes Briefing basiert auf wenigen Daten. Je mehr Quellen du verbindest, desto hilfreicher werden die Briefings."          |

---

## 5. Onboarding-Wizard-Spezifikation

Der Onboarding-Wizard wird als modaler Overlay über dem Dashboard angezeigt (`frontend/src/components/onboarding/onboarding-wizard.tsx`). Die `OnboardingGate` (`frontend/src/components/onboarding/onboarding-gate.tsx`) steuert die Sichtbarkeit basierend auf dem Onboarding-Status des Nutzers.

### Step 1: Willkommen + Wertversprechen

**Zweck:** Orientierung geben, Vertrauen aufbauen, erste Aktion motivieren.

**Wireframe-Beschreibung:**

```
┌────────────────────────────────────────────────┐
│  [StepIndicator: ● ○ ○ ○]                     │
│                                                │
│         [Sparkles-Icon, 48px, brand-color]     │
│                                                │
│     Willkommen bei PWBS, {Anzeigename}!        │
│                                                │
│  Dein Arbeitswissen – automatisch vernetzt,    │
│  im richtigen Moment verfügbar.                │
│                                                │
│  In 2 Minuten verbindest du deine erste        │
│  Datenquelle und erhältst dein erstes          │
│  automatisches Tagesbriefing.                  │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │          [ Los geht's → ]                │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│         Überspringen (als Link, dezent)        │
│                                                │
└────────────────────────────────────────────────┘
```

**Inhalt:**

- Personalisierte Begrüßung mit Anzeigename aus der Registrierung
- 1-Satz Value Proposition: „Dein Arbeitswissen – automatisch vernetzt, im richtigen Moment verfügbar."
- Zeitschätzung: „In 2 Minuten verbindest du deine erste Datenquelle und erhältst dein erstes automatisches Tagesbriefing."

**Interaktion:**

- CTA: „Los geht's" – primärer Button, volle Breite, `brand`-Farbe
- Skip: „Überspringen" als dezenter Text-Link unterhalb des Buttons
- Dauer: ≤ 5 Sekunden Lesezeit
- Skip-Konsequenz: Dashboard wird geladen; persistenter Banner „Verbinde deine erste Quelle, um dein Wissenssystem zu aktivieren" wird angezeigt

---

### Step 2: Datenquelle verbinden

**Zweck:** Ersten Konnektor auswählen und OAuth-Verbindung herstellen.

**Wireframe-Beschreibung:**

```
┌────────────────────────────────────────────────┐
│  [StepIndicator: ✓ ● ○ ○]      [← Zurück]    │
│                                                │
│     Verbinde deine erste Datenquelle           │
│                                                │
│  ┌────────────────────────────────────────┐    │
│  │ ⭐ Google Calendar      [Verbinden →]  │    │
│  │    Termine und Meeting-Kontext          │    │
│  │    "Empfohlen – höchster Sofortwert"    │    │
│  └────────────────────────────────────────┘    │
│                                                │
│  ┌────────────────────────────────────────┐    │
│  │    Notion                [Verbinden →]  │    │
│  │    Seiten und Datenbanken               │    │
│  └────────────────────────────────────────┘    │
│                                                │
│  ┌────────────────────────────────────────┐    │
│  │    Zoom                  [Verbinden →]  │    │
│  │    Meeting-Transkripte                  │    │
│  └────────────────────────────────────────┘    │
│                                                │
│  ┌────────────────────────────────────────┐    │
│  │    Obsidian              [Verbinden →]  │    │
│  │    Markdown-Notizen aus deinem Vault    │    │
│  └────────────────────────────────────────┘    │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │    Später verbinden (als Link)           │  │
│  └──────────────────────────────────────────┘  │
│  ⓘ Briefings sind erst nach der ersten         │
│    Verbindung möglich.                         │
│                                                │
└────────────────────────────────────────────────┘
```

**Inhalt:**

- Überschrift: „Verbinde deine erste Datenquelle"
- 4 Konnektor-Karten mit Icon, Name und kurzer Beschreibung
- Google Calendar hervorgehoben mit ⭐-Badge und „Empfohlen – höchster Sofortwert" (Begründung: Kalender hat die höchste Sofort-Wert-Dichte für Briefings; GTM_PLAN betont Kalenderdaten als zentral für den Value Moment)
- Jede Karte hat einen „Verbinden →"-Button

**Interaktion:**

- Klick auf „Verbinden" → ConsentDialog öffnet sich (vorhandene Komponente)
- Nach Consent-Bestätigung → OAuth-Flow wird gestartet (Redirect zum Provider)
- OAuth-Callback → automatischer Übergang zu Step 3
- „Später verbinden" als Text-Link mit Hinweis: „Briefings sind erst nach der ersten Verbindung möglich."
- Zurück-Button: Navigiert zu Step 1

**OAuth-Flow-Feedback:**

- Während OAuth: Spinner mit „Verbindung wird hergestellt…"
- Erfolg: Grünes Häkchen + „Google Calendar verbunden!" für 1 Sekunde, dann Auto-Advance
- Fehler: Rote ErrorCard mit spezifischem Text (siehe Abschnitt 7)

---

### Step 3: Synchronisierung

**Zweck:** Visuelles Feedback während des Initial-Syncs geben, Abbrüche verhindern.

**Wireframe-Beschreibung:**

```
┌────────────────────────────────────────────────┐
│  [StepIndicator: ✓ ✓ ● ○]                     │
│                                                │
│     Deine Daten werden importiert              │
│                                                │
│  ┌────────────────────────────────────────┐    │
│  │  [Google Calendar Icon]                │    │
│  │                                        │    │
│  │  ████████████░░░░░░░░  67%             │    │
│  │                                        │    │
│  │  42 Termine importiert                 │    │
│  │  Noch ca. 15 Sekunden                  │    │
│  └────────────────────────────────────────┘    │
│                                                │
│  Was passiert gerade?                          │
│  ✓ Verbindung hergestellt                      │
│  ✓ Termine werden abgerufen                    │
│  ◌ Inhalte werden analysiert                   │
│  ○ Wissensmodell wird aufgebaut                │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  💡 Wusstest du? PWBS erkennt automa-   │  │
│  │  tisch Personen, Projekte und Themen    │  │
│  │  aus deinen Daten und verknüpft sie.    │  │
│  └──────────────────────────────────────────┘  │
│                                                │
└────────────────────────────────────────────────┘
```

**Inhalt:**

- Überschrift: „Deine Daten werden importiert"
- Fortschrittsbalken mit Prozentangabe und importierter Dokumentenzahl
- Geschätzte Restdauer (basierend auf bisheriger Geschwindigkeit)
- Mehrstufen-Checkliste: Verbindung → Abruf → Analyse → Wissensmodell
- Educational Snippet: Kurzer Fakt über PWBS (rotierend aus Pool), um die Wartezeit zu überbrücken

**Interaktion:**

- Kein aktiver User-Input erforderlich
- Auto-Advance zu Step 4 nach abgeschlossenem Sync
- Bei Dauer > 2 Minuten: Zusätzlicher Hinweis „Das dauert etwas länger als üblich. Du kannst dieses Fenster offen lassen – wir benachrichtigen dich."
- Fallback bei Timeout (> 3 Min.): „Wir verarbeiten deine Daten im Hintergrund weiter. Du kannst jetzt schon dein Dashboard erkunden." + Link zum Dashboard

---

### Step 4: Erstes Briefing

**Zweck:** Den Aha-Moment liefern – das erste KI-generierte Briefing zeigt den Wert des Systems.

**Wireframe-Beschreibung:**

```
┌────────────────────────────────────────────────┐
│  [StepIndicator: ✓ ✓ ✓ ●]                     │
│                                                │
│     🎉 Dein erstes Briefing ist da!            │
│                                                │
│  ┌────────────────────────────────────────┐    │
│  │  Morgenbriefing – 17. März 2026        │    │
│  │                                        │    │
│  │  ## Dein Tag im Überblick              │    │
│  │                                        │    │
│  │  Du hast heute 4 Termine, darunter     │    │
│  │  ein Meeting mit [Person] um 10:00.    │    │
│  │  [Quelle: Google Calendar, 17.03.]     │    │
│  │                                        │    │
│  │  ## Relevante Kontexte                 │    │
│  │  ...                                   │    │
│  │                                        │    │
│  │  📎 3 Quellen verwendet                │    │
│  └────────────────────────────────────────┘    │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │      [ Zum Dashboard → ]                 │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │  [ Weitere Quelle verbinden ]            │  │
│  └──────────────────────────────────────────┘  │
│                                                │
└────────────────────────────────────────────────┘
```

**Inhalt:**

- Konfetti-/Feier-Element: „Dein erstes Briefing ist da!"
- Vollständiges Briefing mit Markdown-Rendering, Quellenreferenzen und Quellenzähler
- Hinweis, wenn das Briefing auf wenigen Daten basiert: „Dieses Briefing entstand aus [N] Dokumenten. Verbinde weitere Quellen für noch reichere Kontexte."

**Interaktion:**

- Primärer CTA: „Zum Dashboard" – schließt den Wizard und markiert Onboarding als abgeschlossen
- Sekundärer CTA: „Weitere Quelle verbinden" – navigiert zurück zu Step 2 (mit bereits verbundenem Konnektor ausgegraut)
- Briefing-Feedback: Daumen-hoch/runter direkt integriert (US-3.4)

**Loading-State während Briefing-Generierung:**

```
┌────────────────────────────────────────────────┐
│  [StepIndicator: ✓ ✓ ✓ ●]                     │
│                                                │
│     Dein Briefing wird erstellt…               │
│                                                │
│  ┌────────────────────────────────────────┐    │
│  │  [BriefingCardSkeleton]                │    │
│  │  ████████████████░░░░                  │    │
│  │  ████████░░░░░░░░░░░░                  │    │
│  │  ██████████████░░░░░░                  │    │
│  └────────────────────────────────────────┘    │
│                                                │
│  ✓ Daten wurden importiert                     │
│  ✓ Kontext wird aufgebaut                      │
│  ◌ KI erstellt dein persönliches Briefing…     │
│                                                │
└────────────────────────────────────────────────┘
```

---

## 6. Empty States

Alle Texte sind fertige, einsetzbare deutsche Texte. Die bestehende `EmptyStates`-Komponente in `frontend/src/components/ui/empty-states.tsx` wird als Basis verwendet.

| Seite               | Route         | Zustand                                                              | Überschrift                            | Beschreibungstext                                                                                                                                                                         | CTA-Text                   | CTA-Ziel                 |
| ------------------- | ------------- | -------------------------------------------------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ------------------------ |
| **Dashboard**       | `/`           | Kein Briefing vorhanden, kein Konnektor                              | Dein Wissenssystem wartet auf dich     | Verbinde deine erste Datenquelle, und PWBS erstellt dir automatisch ein tägliches Kontextbriefing für deinen Arbeitstag.                                                                  | Erste Quelle verbinden     | `/connectors`            |
| **Dashboard**       | `/`           | Konnektor vorhanden, aber noch kein Briefing                         | Dein erstes Briefing wird vorbereitet  | Deine Daten werden gerade verarbeitet. Sobald die Analyse abgeschlossen ist, erscheint hier dein erstes Morgenbriefing.                                                                   | Briefing-Status prüfen     | `/briefings`             |
| **Briefings-Liste** | `/briefings`  | Keine Briefings generiert                                            | Noch keine Briefings erstellt          | Briefings werden automatisch jeden Morgen generiert, sobald du mindestens eine Datenquelle verbunden hast. Du kannst auch jederzeit manuell ein Briefing anfordern.                       | Jetzt Briefing erstellen   | Briefing-Generate-Action |
| **Briefings-Liste** | `/briefings`  | Keine Konnektoren verbunden                                          | Verbinde zuerst eine Datenquelle       | Für Briefings braucht PWBS Zugriff auf deine Daten. Verbinde eine Quelle wie Google Calendar oder Notion, und du erhältst innerhalb weniger Minuten dein erstes Briefing.                 | Datenquelle verbinden      | `/connectors`            |
| **Konnektoren**     | `/connectors` | Keine Konnektoren verbunden                                          | Verbinde deine Werkzeuge mit PWBS      | PWBS kann Daten aus Google Calendar, Notion, Zoom und Obsidian importieren. Je mehr Quellen du verbindest, desto hilfreicher werden deine Briefings und die Suche.                        | Erste Quelle verbinden     | Konnektor-Auswahl-Dialog |
| **Suche**           | `/search`     | Keine Suchergebnisse                                                 | Keine Ergebnisse gefunden              | Versuche es mit anderen Begriffen oder weniger spezifischen Filtern. PWBS durchsucht alle deine verbundenen Quellen semantisch – stelle deine Frage gerne in natürlicher Sprache.         | Filter anpassen            | Suchfilter-Reset-Action  |
| **Suche**           | `/search`     | Noch keine Dokumente indexiert                                       | Noch keine Dokumente vorhanden         | Verbinde eine Datenquelle, damit PWBS deine Inhalte indexieren und durchsuchbar machen kann. Die Suche wird automatisch aktiv, sobald deine ersten Dokumente verarbeitet sind.            | Datenquelle verbinden      | `/connectors`            |
| **Knowledge**       | `/knowledge`  | Knowledge Graph leer                                                 | Dein Wissensgraph entsteht automatisch | Sobald PWBS Dokumente verarbeitet, erkennt es automatisch Personen, Projekte und Themen und verknüpft sie miteinander. Verbinde weitere Quellen, um ein reicheres Wissensnetz aufzubauen. | Quellen verwalten          | `/connectors`            |
| **Erinnerungen**    | `/reminders`  | Keine Erinnerungen vorhanden _(Route: erschlossen aus remindersApi)_ | Keine Erinnerungen gesetzt             | Erinnerungen helfen dir, wichtige Themen im Blick zu behalten. Du kannst Erinnerungen aus Briefings, Suchergebnissen oder direkt erstellen.                                               | Erste Erinnerung erstellen | Reminder-Create-Action   |
| **Projekte**        | `/projects`   | Keine Projekte erkannt                                               | Noch keine Projekte erkannt            | PWBS erkennt Projekte automatisch aus deinen Datenquellen. Verbinde Google Calendar und Notion, um Projekte und ihre Zusammenhänge zu entdecken.                                          | Datenquelle verbinden      | `/connectors`            |
| **Entscheidungen**  | `/decisions`  | Keine Entscheidungen erfasst                                         | Noch keine Entscheidungen erfasst      | PWBS extrahiert Entscheidungen aus deinen Meeting-Transkripten und Notizen. Verbinde Zoom oder Notion, um Entscheidungen automatisch zu erkennen.                                         | Datenquelle verbinden      | `/connectors`            |

---

## 7. Error States

Alle Texte sind nutzerfreundlich, auf Deutsch, frei von technischem Jargon und mit konkreter Recovery-Aktion.

### Onboarding- und Konnektor-Fehler

| Fehlertyp                                | Trigger                                                                                                          | Nutzertext (Deutsch)                                                                                                                                                                                          | Technischer Kontext                                               | Recovery-Aktion                                                                                                     |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **OAuth: Zugriff verweigert**            | Nutzer klickt „Ablehnen" im Google/Notion/Zoom-Consent-Screen                                                    | **Zugriff nicht erteilt.** Du hast die Verbindung abgelehnt. Ohne Zugriff auf deine Daten kann PWBS kein Briefing erstellen. Du kannst es jederzeit erneut versuchen.                                         | OAuth callback mit `error=access_denied`                          | Button: „Erneut verbinden" → Startet OAuth-Flow neu                                                                 |
| **OAuth: Token-Exchange fehlgeschlagen** | Backend kann Authorization Code nicht gegen Token tauschen (Provider-Fehler, abgelaufener Code, Netzwerkproblem) | **Verbindung fehlgeschlagen.** Die Verbindung zu [Anbietername] konnte nicht hergestellt werden. Das liegt möglicherweise an einer kurzzeitigen Störung. Bitte versuche es in einer Minute erneut.            | HTTP 400/500 beim Token-Exchange; `ConnectorAuthError`            | Button: „Erneut versuchen" → Startet OAuth-Flow neu; Link: „Hilfe" (öffnet FAQ)                                     |
| **OAuth: Pop-up blockiert**              | Browser-Pop-up-Blocker verhindert OAuth-Fenster                                                                  | **Pop-up blockiert.** Dein Browser hat das Anmeldefenster blockiert. Bitte erlaube Pop-ups für diese Seite und versuche es erneut.                                                                            | `window.open()` gibt `null` zurück                                | Anleitung: „So erlaubst du Pop-ups: [Browser-Name] → Einstellungen → Pop-ups erlauben" + Button: „Erneut versuchen" |
| **Konnektor-Sync: API nicht erreichbar** | Provider-API (Google, Notion, Zoom) antwortet nicht oder gibt 5xx zurück                                         | **[Anbietername] ist gerade nicht erreichbar.** Der Dienst scheint vorübergehend gestört zu sein. Wir versuchen es automatisch erneut. Du kannst in der Zwischenzeit eine andere Quelle verbinden.            | HTTP 5xx oder Timeout bei Provider-API; Circuit Breaker aktiviert | Buttons: „Andere Quelle verbinden" + automatischer Retry-Hinweis                                                    |
| **Konnektor-Sync: Keine Daten**          | Sync abgeschlossen, aber 0 Dokumente importiert                                                                  | **Keine Daten gefunden.** In deinem [Anbietername]-Konto konnten keine Inhalte gefunden werden. Stelle sicher, dass du Termine, Seiten oder Transkripte hast, und versuche es erneut.                         | Sync-Job erfolgreich, `doc_count = 0`                             | Buttons: „Erneut synchronisieren" + „Andere Quelle verbinden"                                                       |
| **Obsidian: Ungültiger Vault-Pfad**      | Eingegebener Pfad existiert nicht oder enthält keine `.md`-Dateien                                               | **Kein Obsidian-Vault gefunden.** Der angegebene Pfad enthält keinen gültigen Obsidian-Vault. Bitte prüfe, ob der Pfad korrekt ist und Markdown-Dateien enthält. Beispiel: `C:\Users\Name\Obsidian\MeinVault` | Dateisystem-Check: Pfad nicht existent oder keine `.md`-Dateien   | Pfad-Eingabe bleibt offen; Hinweis: „Ein Obsidian-Vault enthält einen `.obsidian`-Ordner und `.md`-Dateien."        |

### Briefing- und System-Fehler

| Fehlertyp                            | Trigger                                                                | Nutzertext (Deutsch)                                                                                                                                                            | Technischer Kontext                                        | Recovery-Aktion                                                                                               |
| ------------------------------------ | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **LLM-Timeout**                      | Briefing-Generierung dauert > 30 Sekunden (Claude/GPT antwortet nicht) | **Die Erstellung dauert etwas länger.** Dein Briefing wird gerade erzeugt, aber der KI-Dienst braucht etwas mehr Zeit. Du kannst warten oder es später erneut versuchen.        | LLM-API Timeout; `asyncio.TimeoutError` in BriefingAgent   | Buttons: „Warten" (Polling fortsetzen) + „Später erneut versuchen" (Dashboard)                                |
| **LLM-Fehler**                       | LLM-API gibt Fehler zurück (Rate Limit, Server Error)                  | **Briefing konnte nicht erstellt werden.** Der KI-Dienst ist vorübergehend nicht verfügbar. Dein Briefing wird automatisch erstellt, sobald der Dienst wieder erreichbar ist.   | HTTP 429/500/503 von Anthropic/OpenAI; Circuit Breaker     | Button: „Erneut versuchen" + Info: „Du erhältst eine Benachrichtigung, wenn dein Briefing fertig ist."        |
| **Rate-Limit erreicht**              | Nutzer hat zu viele Anfragen in kurzer Zeit gestellt                   | **Du bist gerade sehr aktiv!** Um die Qualität für alle Nutzer sicherzustellen, gibt es ein kurzes Limit. Bitte warte einen Moment und versuche es dann erneut.                 | HTTP 429; Redis-Rate-Limiter; `RateLimitExceeded`          | Countdown-Timer anzeigen: „Verfügbar in [X] Sekunden"                                                         |
| **Netzwerk-Fehler (Client offline)** | Keine Internetverbindung; `fetch` schlägt fehl                         | **Keine Internetverbindung.** Bitte prüfe deine Netzwerkverbindung. PWBS benötigt eine aktive Internetverbindung, um deine Daten zu synchronisieren und Briefings zu erstellen. | `TypeError: Failed to fetch`; `navigator.onLine === false` | `NetworkErrorBanner` (vorhandene Komponente) oben im Viewport; automatisches Ausblenden bei Wiederherstellung |
| **Session abgelaufen**               | JWT Access-Token und Refresh-Token abgelaufen                          | **Deine Sitzung ist abgelaufen.** Bitte melde dich erneut an, um fortzufahren. Deine Daten und Einstellungen sind sicher gespeichert.                                           | 401 nach Refresh-Versuch; `clearTokens()` → Redirect       | Automatischer Redirect zu `/login?expired=1` (vorhandene Login-Seite zeigt Amber-Banner)                      |

---

## 8. Time-to-Value-Optimierung

### Messbares Ziel

**< 5 Minuten von Registration bis erstes Briefing** (Self-Serve, ohne 1-on-1-Onboarding).

Dies setzt voraus, dass der Nutzer den OAuth-Flow in < 30 Sekunden durchläuft, der Initial-Sync < 2 Minuten dauert und die Briefing-Generierung < 30 Sekunden benötigt.

### Identifizierte Engstellen im aktuellen Flow

| #   | Engstelle                             | Erwartete Dauer | Problem                                                                                                                                                                                                                      |
| --- | ------------------------------------- | --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Welcome-Screen nach Registrierung** | 5 Sek.          | Unnötiger Zwischenschritt: Der Nutzer muss explizit „Konnektoren einrichten" klicken, bevor der Wizard startet. Direkte Weiterleitung zum Dashboard (wo der Wizard automatisch startet via `OnboardingGate`) wäre schneller. |
| 2   | **ConsentDialog**                     | 10–15 Sek.      | DSGVO-konform und notwendig, aber der Textumfang (Datentypen, Verarbeitungszweck, LLM-Provider, Info-Box, Checkbox) kann einschüchternd wirken.                                                                              |
| 3   | **OAuth-Flow (externer Provider)**    | 15–30 Sek.      | Nicht kontrollierbar – der Nutzer muss sich beim Provider anmelden und Scopes erteilen. Bei Erstanmeldung bei Google/Notion zusätzlich 2FA möglich.                                                                          |
| 4   | **Initial-Sync**                      | 30–120 Sek.     | Größte Varianz. Abhängig von der Datenmenge beim Provider. Bei > 500 Kalendereinträgen kann der Sync > 2 Minuten dauern.                                                                                                     |
| 5   | **Processing (Embedding + NER)**      | 10–30 Sek.      | Batch-Processing der importierten Dokumente. Bei vielen Dokumenten sequentiell.                                                                                                                                              |
| 6   | **Briefing-Generierung**              | 10–30 Sek.      | LLM-Call mit Kontext-Aufbau. Abhängig von Claude-/GPT-Latenz.                                                                                                                                                                |

### Optimierungsvorschläge

#### O-1: Direkt-Redirect zum Dashboard nach Registration

**Befund:** Der Welcome-Screen nach Registrierung (`/register` Post-Success-View) ist ein zusätzlicher Klick, bevor der Onboarding-Wizard startet.
**Spezifikation:** Nach erfolgreicher Registrierung direkt auf `/` (Dashboard) weiterleiten. Die `OnboardingGate` öffnet den Wizard automatisch. Der Welcome-Step im Wizard übernimmt die Begrüßung.
**Erwartete Ersparnis:** 5–10 Sekunden.

#### O-2: ConsentDialog-Vereinfachung

**Befund:** Der vollständige ConsentDialog zeigt Datentypen, Verarbeitungszweck, LLM-Provider und eine Info-Box – das ist DSGVO-konform, aber für den Onboarding-Kontext überladen.
**Spezifikation:** Während des Onboarding-Wizards eine verkürzte Consent-Variante anzeigen: 1-Satz Zusammenfassung + Checkbox + Link „Vollständige Datenschutzinformationen anzeigen" (expandierbar). Die vollständige Version wird auf der Konnektor-Einstellungsseite beibehalten.
**Erwartete Ersparnis:** 5–10 Sekunden.

#### O-3: Sync-Preview während des Imports

**Befund:** Während des Syncs wartet der Nutzer ohne Interaktionsmöglichkeit.
**Spezifikation:** Sobald die ersten 10 Dokumente importiert sind, eine Vorschau der erkannten Termine/Seiten/Transkripte anzeigen. Der Nutzer sieht sofort, dass seine Daten ankommen, bevor der vollständige Sync abgeschlossen ist.
**Erwartete Ersparnis:** Keine Zeitersparnis, aber signifikante Reduktion der subjektiv gefühlten Wartezeit.

#### O-4: Partial Briefing als Frühstarter

**Befund:** Das Briefing wird erst nach vollständigem Sync und Processing generiert.
**Spezifikation:** Sobald ≥ 5 Dokumente verarbeitet sind, ein vorläufiges Briefing generieren und anzeigen. Hinweis: „Vorläufiges Briefing – wird mit weiteren Daten ergänzt." Das vollständige Briefing ersetzt es nach Abschluss des Syncs.
**Erwartete Ersparnis:** 30–90 Sekunden (Briefing erscheint während der Sync noch läuft).

#### O-5: Demo-Briefing als Fallback

**Befund:** Wenn der Sync > 2 Minuten dauert oder die Briefing-Generierung fehlschlägt, sieht der Nutzer nur einen Spinner.
**Spezifikation:** Nach 2 Minuten Wartezeit ein Demo-Briefing anzeigen, das die Briefing-Struktur und den Nutzen demonstriert: „So sieht dein tägliches Briefing aus" – mit Beispieldaten und echten Formatierungen. Sobald das echte Briefing verfügbar ist, wird das Demo-Briefing ersetzt.
**Erwartete Ersparnis:** Verhindert Abbruch bei langen Sync-Zeiten; liefert den Aha-Moment auch ohne echte Daten.

#### O-6: Hintergrund-Processing nach Wizard-Abschluss

**Befund:** Der Nutzer muss den gesamten Processing-Vorgang im Wizard abwarten.
**Spezifikation:** Den Wizard nach erfolgreichem Sync (aber vor vollendetem Processing) abschließen lassen. Das Dashboard zeigt einen Fortschritts-Widget: „Dein Briefing wird erstellt… (2 Minuten)" – und das Briefing erscheint via WebSocket-Update automatisch auf dem Dashboard.
**Erwartete Ersparnis:** 30–60 Sekunden (Nutzer kann Dashboard erkunden).

### Optimierter Ziel-Flow

```
Registration (30 Sek.)
  → Auto-Redirect zum Dashboard
  → OnboardingGate öffnet Wizard
  → Step 1: Willkommen (5 Sek.)
  → Step 2: Konnektor wählen + Consent (15 Sek.)
  → OAuth-Flow (20 Sek.)
  → Step 3: Sync mit Live-Preview (60 Sek.)
  → Step 4: Partial/Demo-Briefing (sofort)
  → Dashboard mit vollständigem Briefing (via WebSocket)

Gesamt: ~2:30 Minuten (Ziel: < 5 Minuten)
```

---

## 9. Priorisierte Maßnahmenliste

Alle identifizierten UX-Issues und Empfehlungen, sortiert nach Schweregrad.

### Kritisch (Blockiert Onboarding-Erfolg)

| #   | Maßnahme                                                                                                                                                                                                                                 | Schweregrad | Betroffener Flow  | Geschätzter Aufwand | Abhängigkeit                             |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------- | ------------------- | ---------------------------------------- |
| 1   | **Error-Mapping implementieren:** Backend-Fehlercodes in nutzerfreundliche deutsche Texte mit Recovery-Aktionen übersetzen (siehe Abschnitt 7). Betreffende Komponente: `ErrorCard` und `ErrorBoundary` in `frontend/src/components/ui/` | Kritisch    | Alle Flows        | M (2–3 Tage)        | –                                        |
| 2   | **Demo-Briefing als Fallback:** Bei Sync > 2 Min. oder LLM-Fehler ein vorbereitetes Demo-Briefing anzeigen, das die Briefing-Struktur demonstriert (O-5)                                                                                 | Kritisch    | Onboarding Step 4 | M (2–3 Tage)        | Backend: Demo-Briefing-Template          |
| 3   | **Fortschrittsanzeige im Sync-Schritt verbessern:** Geschätzte Restdauer, mehrstufige Checkliste, Educational Snippets während der Wartezeit (O-3)                                                                                       | Kritisch    | Onboarding Step 3 | S (1–2 Tage)        | –                                        |
| 4   | **Onboarding-Fortschritt persistent speichern:** Wenn der Nutzer den Wizard abbricht und zurückkehrt, am letzten Schritt fortsetzen statt von vorne zu beginnen. Betreffende Komponente: `OnboardingGate`                                | Kritisch    | Onboarding Wizard | S (1–2 Tage)        | Backend: Onboarding-State in User-Profil |

### Major (Beeinträchtigt Nutzererlebnis signifikant)

| #   | Maßnahme                                                                                                                                                                                              | Schweregrad | Betroffener Flow                        | Geschätzter Aufwand | Abhängigkeit                     |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | --------------------------------------- | ------------------- | -------------------------------- |
| 5   | **Zurück-Navigation im Wizard:** Sichtbaren „Zurück"-Button in jedem Wizard-Schritt implementieren. Betreffende Komponente: `OnboardingWizard`                                                        | Major       | Onboarding Wizard                       | XS (< 1 Tag)        | –                                |
| 6   | **Empty States erweitern:** Alle Dashboard-Seiten mit spezifischen, motivierenden Empty States ausstatten (siehe Abschnitt 6). Betreffende Komponente: `EmptyStates`                                  | Major       | Dashboard, Briefings, Search, Knowledge | M (2–3 Tage)        | –                                |
| 7   | **In-App-Hilfe / Tooltips:** Kontextuelle Erklärungen an kritischen Stellen: Konnektor-Auswahl, Briefing-Typen, Suchsyntax, Knowledge Graph                                                           | Major       | Alle Seiten                             | M (3–4 Tage)        | –                                |
| 8   | **Post-Onboarding-Checklist:** Nach Wizard-Abschluss eine nicht-aufdringliche Checklist auf dem Dashboard anzeigen: „Nächste Schritte: Weitere Quelle / Erste Suche / Briefing-Einstellungen"         | Major       | Dashboard                               | S (1–2 Tage)        | –                                |
| 9   | **Partial Briefing:** Briefing-Generierung starten bevor der Sync vollständig abgeschlossen ist (O-4). Sobald ≥ 5 Dokumente verarbeitet sind, vorläufiges Briefing erstellen.                         | Major       | Onboarding Step 4                       | L (3–5 Tage)        | Backend: BriefingAgent-Anpassung |
| 10  | **Skip-Banner nach Wizard-Abbruch:** Wenn der Nutzer den Wizard überspringt, einen persistenten aber schließbaren Banner anzeigen: „Verbinde deine erste Quelle, um dein Wissenssystem zu aktivieren" | Major       | Dashboard                               | XS (< 1 Tag)        | –                                |

### Minor (Verbessert Nutzererlebnis, nicht kritisch)

| #   | Maßnahme                                                                                                                                                         | Schweregrad | Betroffener Flow          | Geschätzter Aufwand | Abhängigkeit                           |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------- | ------------------- | -------------------------------------- |
| 11  | **Direct-Redirect nach Registration:** Welcome-Screen überspringen und direkt zum Dashboard weiterleiten, wo der Wizard auto-startet (O-1)                       | Minor       | Registration → Onboarding | XS (< 1 Tag)        | –                                      |
| 12  | **ConsentDialog vereinfachen:** Während des Onboarding eine verkürzte Consent-Variante anzeigen mit Link zur vollständigen Version (O-2)                         | Minor       | Onboarding Step 2         | S (1–2 Tage)        | DSGVO-Review erforderlich              |
| 13  | **Keyboard-Shortcuts:** `/` für Suche, `Ctrl+B` für Briefing; Shortcut-Hilfe-Overlay mit `?`-Taste                                                               | Minor       | Power-User-Workflow       | S (1–2 Tage)        | –                                      |
| 14  | **Navigation-Label „Knowledge" → „Wissensgraph":** Deutsches Label für bessere Verständlichkeit. Betreffende Datei: `frontend/src/components/layout/sidebar.tsx` | Minor       | Navigation                | XS (< 1 Stunde)     | –                                      |
| 15  | **ARIA-Optimierungen:** `aria-valuenow`/`aria-valuemax` auf StepIndicator; `aria-live="polite"` auf Passwort-Validierung; `role="alert"` auf Formularfehler      | Minor       | Accessibility             | S (1–2 Tage)        | –                                      |
| 16  | **Pop-up-Blocker-Warnung:** Vor dem OAuth-Flow prüfen, ob Pop-ups erlaubt sind, und ggf. Hinweis anzeigen                                                        | Minor       | Onboarding Step 2         | XS (< 1 Tag)        | –                                      |
| 17  | **Hintergrund-Processing-Widget:** Wizard nach Sync abschließen; Dashboard zeigt Fortschritts-Widget für Briefing-Generierung (O-6)                              | Minor       | Onboarding Completion     | M (2–3 Tage)        | WebSocket-Events für Processing-Status |
| 18  | **Lighthouse Accessibility-Audit durchführen:** Kontrastverhältnisse der CSS-Variablen-Werte auf allen Seiten verifizieren                                       | Minor       | Accessibility             | S (1 Tag)           | –                                      |

### Aufwandslegende

| Kürzel | Aufwand  |
| ------ | -------- |
| XS     | < 1 Tag  |
| S      | 1–2 Tage |
| M      | 2–4 Tage |
| L      | 3–5 Tage |

---

## Anhang: Referenzierte Dateien und Komponenten

| Datei                                                           | Beschreibung                                                                |
| --------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `frontend/src/components/onboarding/onboarding-wizard.tsx`      | 4-Schritt-Onboarding-Wizard (Welcome, Connector, Sync, Briefing)            |
| `frontend/src/components/onboarding/onboarding-gate.tsx`        | Steuerung der Wizard-Sichtbarkeit basierend auf Onboarding-Status           |
| `frontend/src/components/ui/empty-states.tsx`                   | Wiederverwendbare Empty-State-Komponente mit Icon, Titel, Beschreibung, CTA |
| `frontend/src/components/ui/error-states.tsx`                   | ErrorCard und NetworkErrorBanner                                            |
| `frontend/src/components/ui/error-boundary.tsx`                 | React Error Boundary mit Retry                                              |
| `frontend/src/components/ui/loading-states.tsx`                 | Spinner, Skeletons für Briefings, Connectors, Search, Dashboard             |
| `frontend/src/components/ui/focus-trap.tsx`                     | Fokus-Einschluss in Modalen/Dialogen                                        |
| `frontend/src/components/ui/skip-link.tsx`                      | Skip-Navigation für Keyboard-Nutzer                                         |
| `frontend/src/components/connectors/consent-dialog.tsx`         | DSGVO-Consent-Dialog vor OAuth-Flow                                         |
| `frontend/src/components/connectors/sync-history-accordion.tsx` | Sync-Verlauf pro Konnektor                                                  |
| `frontend/src/components/layout/sidebar.tsx`                    | Dashboard-Sidebar mit Navigation                                            |
| `frontend/src/components/layout/header.tsx`                     | Dashboard-Header mit Notifications                                          |
| `frontend/src/app/(dashboard)/layout.tsx`                       | Dashboard-Layout mit ProtectedRoute, WebSocket, OnboardingGate              |
| `frontend/src/app/(dashboard)/page.tsx`                         | Dashboard-Hauptseite mit Briefing, Connectors, Quick Actions                |
| `frontend/src/app/(dashboard)/error.tsx`                        | Route-Level Error-Handler                                                   |
| `frontend/src/app/(auth)/register/page.tsx`                     | Registrierung mit Echtzeit-Passwort-Validierung                             |
| `frontend/src/app/(auth)/login/page.tsx`                        | Login mit Google OAuth + Session-Expired-Banner                             |
| `frontend/src/lib/api-client.ts`                                | Zentraler API-Client mit JWT-Handling und 401-Retry                         |
| `frontend/tailwind.config.ts`                                   | Tailwind-Konfiguration mit CSS-Variablen-basiertem Farbsystem               |
