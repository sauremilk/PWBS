# Community-Plattform: Setup und Moderationsregeln (TASK-148)

## Plattform-Entscheidung: Discord

**Begründung:** Discord bietet niedrigere Einstiegshürden als Discourse für eine Beta-Community, integrierte Voice-Channels für Live-Feedback-Sessions und Bot-Integrationen für automatische Benachrichtigungen.

**Fallback:** Discourse-Forum für langfristige Wissensbasis (ab Phase 5).

---

## Server-Struktur

### Kategorien / Channels

```
📢 INFORMATION
├── #ankündigungen        — Releases, Wartungsfenster, Updates (read-only)
├── #roadmap              — Öffentliche Roadmap + Voting
└── #changelog            — Automatische Release-Notes (Bot)

💬 COMMUNITY
├── #allgemein            — Offene Diskussionen
├── #vorstellungen        — "Stell dich vor" für neue Mitglieder
└── #show-and-tell        — Nutzer teilen ihre PWBS-Setups

🐛 FEEDBACK & SUPPORT
├── #bug-reports          — Strukturierte Bug-Meldungen (Template)
├── #feature-requests     — Feature-Wünsche + Voting
├── #hilfe-und-support    — Fragen zur Nutzung
└── #feedback-beta        — Allgemeines Beta-Feedback

🔧 ENTWICKLUNG
├── #api-und-integrationen — Technische API-Diskussionen
├── #self-hosting         — Hilfe bei Self-Hosted-Installationen
└── #contributing         — Open-Source-Beiträge

🔒 INTERN (nur Team)
├── #team-sync            — Tägliche Updates
├── #incidents            — Incident-Channel
└── #user-insights        — Anonymisierte Nutzerdaten-Analyse
```

### Rollen

| Rolle            | Berechtigungen                                       |
| ---------------- | ---------------------------------------------------- |
| **Admin**        | Volller Zugriff, Channel-Management                  |
| **Moderator**    | Nachrichten löschen, Timeouts, Channel-Moderation    |
| **Beta-Tester**  | Zugang zu allen Community-Channels                   |
| **Contributor**  | Zusätzlich: Entwicklungs-Channels                    |
| **Neues Mitglied** | Eingeschränkt: nur #allgemein + #hilfe bis Verifizierung |

---

## Moderationsregeln

### Community-Richtlinien

1. **Respektvoller Umgang** — Kein Harassment, keine Diskriminierung, keine persönlichen Angriffe.
2. **Konstruktives Feedback** — Bug-Reports und Feature-Requests mit Kontext und Reproduktionsschritten.
3. **Keine sensiblen Daten** — Keine persönlichen API-Keys, Passwörter oder vertrauliche Firmendaten teilen.
4. **Kein Spam** — Keine Werbung, Self-Promotion oder irrelevante Links.
5. **Datenschutz** — Keine Nutzerdaten anderer teilen. DSGVO gilt auch in der Community.
6. **Sprache** — Deutsch und Englisch sind Hauptsprachen. Andere Sprachen in #allgemein toleriert.

### Eskalationsstufen

| Stufe | Aktion               | Anlass                               |
| ----- | -------------------- | ------------------------------------ |
| 1     | Warnung (DM)         | Erster Regelverstoß                  |
| 2     | Timeout (24h)        | Wiederholter Verstoß                 |
| 3     | Timeout (7 Tage)     | Schwerer Verstoß oder Wiederholung   |
| 4     | Permanenter Ban      | Harassment, Spam, Sicherheitsverstoß |

### Bug-Report-Template

```markdown
**Beschreibung:**
Was ist passiert?

**Erwartetes Verhalten:**
Was sollte passieren?

**Schritte zur Reproduktion:**
1. ...
2. ...
3. ...

**Umgebung:**
- Browser/OS:
- PWBS-Version:
- Self-Hosted oder Cloud:

**Screenshots/Logs:**
(Falls vorhanden)
```

---

## Bot-Integrationen

### Automatische Benachrichtigungen

| Trigger                    | Channel            | Inhalt                           |
| -------------------------- | ------------------ | -------------------------------- |
| Neuer GitHub-Release       | #changelog         | Release-Notes + Download-Link    |
| GitHub Issue geschlossen   | #bug-reports       | "Bug XY wurde behoben in vX.Y"  |
| Wartungsfenster geplant    | #ankündigungen     | Zeitfenster + betroffene Services|
| Neues Community-Mitglied   | #vorstellungen     | Welcome-Nachricht mit Onboarding |

### Willkommensnachricht (Auto-DM)

```
👋 Willkommen bei PWBS, {username}!

Du bist jetzt Teil der Beta-Community. Hier ein paar Tipps:

1. Stell dich in #vorstellungen vor
2. Lies die Regeln in #ankündigungen
3. Bei Fragen: #hilfe-und-support
4. Feature-Wünsche: #feature-requests

Viel Spaß beim Entdecken! 🚀
```

---

## Metriken & Feedback-Loop

| Metrik                        | Ziel (Phase 4)  | Messung                    |
| ----------------------------- | ---------------- | -------------------------- |
| Community-Mitglieder          | 500–2.000        | Discord Member Count       |
| Aktive Nutzer (wöchentlich)   | > 30% der Member | Discord Insights           |
| Bug-Reports pro Woche         | < 20 kritische   | #bug-reports Channel Count |
| Feature-Requests bearbeitet   | > 80% in 14 Tagen| GitHub Project Board       |
| NPS (Net Promoter Score)      | > 40             | Monatliche Umfrage         |

---

## Datenschutz in der Community

- Discord-Server ist **nicht öffentlich** – Einladungslinks mit Ablaufdatum
- Keine automatische Verknüpfung von Discord-Accounts mit PWBS-Accounts
- Bug-Reports werden vor Weiterleitung an GitHub anonymisiert
- Keine Analytics-Tools, die personenbezogene Daten aus Discord extrahieren
- DSGVO-Auskunftsrechte: Nutzer können ihre Community-Daten anfordern
