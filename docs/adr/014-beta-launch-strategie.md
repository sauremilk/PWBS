# ADR-014: Beta-Launch-Strategie  Hybrid Go-to-Market fuer 100-500 Nutzer

**Status:** Akzeptiert
**Datum:** 2026-03-14
**Entscheider:** Projektteam

---

## Kontext

PWBS ist mit 159/175 Tasks (91%) produktionsreif. Die Roadmap definiert als Phase-3-Ziel "100-500 aktive Beta-Nutzer" mit > 60% 30-Tage-Retention und > 30% Zahlungsbereitschaft. Es existiert kein grosses Werbebudget (Roadmap-Annahme: "Community-getriebenes Wachstum"). Die Zielgruppe (Gruender, PMs, Berater mit PKM-Affinitaet) ist eine klar abgrenzbare Nische, erreichbar ueber PKM-Communities (Obsidian, Zettelkasten, Notion). Die technische Infrastruktur (Discord-Community-Setup, Feature-Flags, Billing, k6-Load-Tests) ist vorbereitet, aber eine koordinierte Launch-Strategie fehlt.

---

## Entscheidung

Wir werden eine **Hybrid-Strategie** (Community-Aufbau + koordinierter Launch + Referral-Loop) verfolgen, weil sie die hohe Nischen-Conversion von Community-Marketing (4-8%) mit der Sichtbarkeit eines Launch-Events kombiniert und durch ein Referral-System nachhaltiges Wachstum sichert.

### Phasen

1. **Wochen 1-2 (Fundament):** DSGVO-konformes Analytics (Plausible/Fathom), Landing Page mit Demo-Video, minimaler Referral-Mechanismus (UUID-basierte Invite-Codes), Load-Testing auf 500 VUs
2. **Wochen 2-4 (Community):** Authentische Praesenz in Obsidian-Discord, Reddit (r/Zettelkasten, r/PKMS), LinkedIn. 5-10 handverlesene "Design Partners" mit 1-on-1-Onboarding. Ziel: 200 Discord-Mitglieder vor Launch
3. **Woche 5 (Launch):** Koordinierter ProductHunt + HackerNews "Show HN" + Newsletter + LinkedIn-Announcement. Community als Upvote- und Testimonial-Basis
4. **Woche 6+ (Wachstum):** Referral-Aktivierung nach 7 Tagen aktiver Nutzung, Content-Pipeline (Blog, Use Cases), monatliche Community-Events

### Kanaele und erwartete Conversion

| Kanal | Reach | Signups | Aktive Beta-Nutzer |
|---|---|---|---|
| PKM-Communities (Obsidian, Reddit) | 5.000 | 160-350 | 65-140 |
| LinkedIn (organisch) | 5.000 | 50-100 | 20-40 |
| ProductHunt + HackerNews | 7.000-25.000 | 140-500 | 55-200 |
| Design Partners | 10 | 10 | 8-10 |
| Referral (ab Woche 4) | - | 30-80 | 15-40 |
| **TOTAL** | **17.000-35.000** | **390-1.040** | **163-430** |

---

## Optionen bewertet

| Option | Vorteile | Nachteile | Ausschlussgruende |
|---|---|---|---|
| A: Community-Only | Kostenarm, hohe Conversion, nachhaltig | Zu langsam (3-6 Monate fuer 100 Nutzer), Momentum geht verloren | Geschwindigkeit inkompatibel mit Roadmap-Timeline |
| B: Launch-Event-Only | Hohe Sichtbarkeit, schnell | Einmal-Spike, kein Sicherheitsnetz, keine Testimonials | Zu riskant ohne Community-Basis |
| **C: Hybrid (gewaehlt)** | Kombiniert Community-Basis mit Launch-Peak, Referral sichert Nachhaltigkeit | Hoechster Koordinationsaufwand | - |

---

## Konsequenzen

### Positive Konsequenzen

- Product-Market-Fit-Validierung mit qualitativ hochwertigem Feedback (Design Partners + Community)
- Aufbau einer Community-Asset, das fuer Phase 4 (1.000-5.000 Nutzer) weiter skaliert
- NPS- und Testimonial-Basis fuer spaetere Marketing-Aktivitaeten
- Niedrige Kosten (primaer Zeitinvestition, kein Ad-Spend noetig)

### Negative Konsequenzen / Trade-offs

- Signifikanter Zeitaufwand fuer Community-Engagement (10-15h/Woche in Phase 2)
- ProductHunt/HN-Launch ist nicht wiederholbar  muss beim ersten Mal sitzen
- Referral-Mechanismus erfordert minimalen Engineering-Aufwand

### Offene Fragen

- Wer ist der "Hunter" fuer ProductHunt? (Idealerweise jemand mit Follower-Basis in der PKM-Nische)
- Soll die Beta limitiert sein (z.B. "500 Plaetze") oder offen? Kuenstliche Verknappung erhoehe FOMO, kann aber even authentischer Community-Wachstum bremsen
- Pricing waehrend Beta: Gratis mit Upgrade-Pfad oder sofort $20/Monat mit 50% Beta-Discount?

---

## DSGVO-Implikationen

- **Analytics:** Plausible/Fathom statt Google Analytics (kein Cookie-Banner noetig, EU-Hosting)
- **Referral-Codes:** UUID-basiert, nicht mit E-Mail verknuepft, kein PII
- **Community-Daten:** Discord-Accounts nicht mit PWBS-Accounts verknuepft (existierende Regel aus community-setup.md)
- **Landing-Page-Signups:** E-Mail-Adressen mit explizitem Consent (Double-Opt-in), Loeschmoel nach Beta-Start

---

## Sicherheitsimplikationen

- **Registrierungs-Spam bei Launch:** Rate-Limiting auf /api/v1/auth/register existiert (TASK-108)
- **Referral-Abuse:** Max 20 Invites pro Nutzer, Codes mit 7-Tage-Ablauf
- **Launch-Spike-Last:** k6-Load-Test auf 500 VUs validieren VOR Launch, Connection-Pool und Redis-Cache pruefen
- **Waitlist-Fallback:** Feature-Flag `beta_registration_open` fuer sofortigen Cutoff bei Ueberlast

---

## Revisionsdatum

Nach Erreichen von 100 aktiven Beta-Nutzern (voraussichtlich Woche 5-6 nach Start) oder nach 8 Wochen, je nachdem was frueher eintritt.