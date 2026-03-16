# ADR-019: E-Mail als primärer Briefing-Zustellkanal

**Status:** Akzeptiert
**Datum:** 2026-03-16
**Entscheider:** Architektur-Review (Tiefenanalyse)

---

## Kontext

Briefings werden generiert und im Web-Dashboard angezeigt. Nutzer müssen die App aktiv öffnen, um ihr Morgenbriefing zu lesen. Die PRD-Hypothese (3 Briefing-Abrufe pro Woche) scheitert, wenn Nutzer die App nicht öffnen. E-Mail ist der Kanal, den alle drei Personas morgens als erstes nutzen.

Die E-Mail-Infrastruktur ist durch TASK-177 zu ~80 % implementiert: `EmailService` mit SMTP/SendGrid-Backends, Jinja2-Templates, Celery-Task `send_briefing_emails`, User-Felder `email_briefing_enabled` und `briefing_email_time`, Frontend-Settings-UI. Sechs Lücken verhindern die Nutzung als primären Kanal: Default auf False, fehlendes MarkdownHTML, leere Sources, kein Meeting-Prep-E-Mail, kein Per-User-Timezone, kein Event-basierter Meeting-Trigger.

---

## Entscheidung

Wir schließen die sechs Lücken in der bestehenden TASK-177-Architektur und machen E-Mail zum primären Zustellkanal (opt-out statt opt-in). Das Web-Dashboard bleibt als Detailansicht erhalten. Konkret:

1. **Default ändern:** `email_briefing_enabled` Default auf `True` (Alembic-Migration + ORM)
2. **MarkdownHTML:** `markdown`-Paket für E-Mail-Rendering, Template mit `| safe`
3. **Sources durchreichen:** Quellenreferenzen aus DB laden statt `sources=[]`
4. **Meeting-Prep-E-Mail:** `bt_map` erweitern, Chain nach on-demand Generierung
5. **Idempotenz-Guard:** `briefing_email_sent_at` auf `briefings`-Tabelle
6. Per-User-Timezone und Event-basierter Meeting-Trigger bleiben Phase-3-Aufgaben

---

## Optionen bewertet

| Option | Vorteile | Nachteile | Ausschlussgründe |
|---|---|---|---|
| A: Lücken schließen (minimal) | 80 % existiert, isolierte Änderungen, kein neues Modul | Per-User-Timezone bleibt UTC |  **Gewählt** |
| B: Neuer Delivery-Service | Zukunftssicher für Push | Over-engineering für MVP, verzögert Wirkung | Keine sofortige Engagement-Verbesserung |
| C: Externer E-Mail-Service | SPF/DKIM out-of-the-box | Vendor-Lock-in, DSGVO-AVV nötig, Kosten | Abhängigkeit von Dritt-Service für Kernfunktion |

---

## Konsequenzen

### Positive Konsequenzen

- Massiv höhere Engagement-Rate: Briefings landen direkt in der Inbox
- Aktivierungshürde eliminiert: Nutzer muss keine App öffnen
- Meeting-Briefings 30 Min. vorher per E-Mail (on-demand Trigger)
- Quellenreferenzen in E-Mails stärken Erklärbarkeits-Prinzip
- Minimaler Aufwand: Baut vollständig auf TASK-177 auf

### Negative Konsequenzen / Trade-offs

- Bestandsnutzer erhalten nach Migration E-Mails (Mitigierung: Unsubscribe-Link in jeder E-Mail)
- MarkdownHTML-Konvertierung muss XSS-sicher implementiert werden (Jinja2-Autoescaping + Markdown safe mode)
- E-Mail-Duplikate bei Celery-Retry möglich ohne Idempotenz-Guard
- Per-User-Timezone-Scheduling erst in Phase 3

### Offene Fragen

- Soll der Default-Wechsel nur für neue Registrierungen gelten oder auch Bestandsnutzer updaten?
- SPF/DKIM/DMARC DNS-Setup: Welche Domain? (pwbs.app? briefings.pwbs.app?)
- Soll eine Onboarding-E-Mail den Wechsel zum E-Mail-Kanal ankündigen?

---

## DSGVO-Implikationen

- **Keine neuen PII-Felder.** E-Mails werden an `users.email` gesendet (bereits vorhanden).
- **Unsubscribe-Link** in jeder E-Mail (bereits im Base-Template implementiert).
- **Opt-out statt Opt-in:** Rechtsgrundlage Art. 6 Abs. 1b (Vertragserfüllung)  Briefing-Zustellung ist Kernfunktion des Dienstes. Nutzer kann jederzeit deaktivieren.
- **Keine Tracking-Pixel** in E-Mails (DSGVO-konform).

---

## Sicherheitsimplikationen

- **MarkdownHTML:** Muss über sanitized Markdown-Rendering erfolgen (kein raw HTML in Markdown erlauben). `markdown`-Paket mit deaktivierten raw-HTML-Extensions.
- **Jinja2 Autoescaping:** `| safe` nur nach Markdown-Konvertierung verwenden, nicht auf User-Input.
- **SMTP-Credentials:** Bereits über ENV-Variablen konfiguriert (SMTP_PASSWORD, SENDGRID_API_KEY).
- **Idempotenz-Guard:** Verhindert Spam bei Celery-Retries.

---

## Revisionsdatum

Phase-3-Start: Per-User-Timezone-Scheduling und Event-basierter Meeting-Trigger evaluieren.
