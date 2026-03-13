# ADR-007: Next.js auf Vercel (Frontend)

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

Das PWBS benötigt ein Frontend für Dashboard, Briefing-Anzeige, semantische Suche, Konnektoren-Verwaltung, Knowledge-Graph-Explorer und Profil-/DSGVO-Einstellungen. Das Framework muss Server-Side Rendering für Marketing-Pages (SEO), reaktive Client-Interaktionen für den Knowledge Explorer und eine exzellente Developer Experience bieten. Deployment-Einfachheit und Preview-Environments für schnelles Feedback sind wichtig.

---

## Entscheidung

Wir verwenden **Next.js (App Router) mit React und TypeScript** auf **Vercel** als Frontend-Stack, weil die Kombination aus Server Components, Edge Functions und Zero-Config-Deployment die beste DX und Performance bietet.

---

## Optionen bewertet

| Option | Vorteile | Nachteile | Ausschlussgründe |
|--------|----------|-----------|-------------------|
| **Next.js auf Vercel** (gewählt) | SSR für SEO (Marketing-Pages), Edge Functions für Auth, exzellente DX (Hot Reload, Preview Deployments), App Router + Server Components. Vercel: Zero-Config-Deployment, automatische Preview-Environments pro Branch. | Vendor Lock-in bei Vercel. Server Components erfordern Lernkurve. | – |
| SPA (Vite + React) | Maximale Kontrolle, kein Server-Rendering nötig, einfacheres mentales Modell. | Kein SSR (schlecht für SEO der Marketing-Pages), kein Edge-Computing, kein Preview-Deployment out-of-the-box. | Fehlendes SSR für Marketing |
| Remix | Nested Routes, gutes Data-Loading, Web-Standards-fokussiert. | Kleineres Ökosystem als Next.js, weniger Community-Support. Deployment-Options weniger ausgereift als Vercel. | Ökosystem-Größe |
| SvelteKit | Hervorragende Performance, weniger Boilerplate als React. | Deutlich kleineres Ökosystem und Talent-Pool. Svelte-spezifisches Wissen erforderlich. UI-Library-Auswahl eingeschränkt (vs. React). | Talent-Pool und Ökosystem zu klein |

---

## Konsequenzen

### Positive Konsequenzen

- Server Components reduzieren Client-Bundle-Size (Dashboard, Briefing-Listen können vollständig server-seitig gerendert werden)
- Edge Functions für Auth-Middleware (Token-Validierung am Edge, niedrige Latenz)
- Preview Deployments pro Branch ermöglichen schnelles visuelles Feedback
- Tailwind CSS als Utility-First-Framework für konsistentes Design
- TypeScript strict mode für Compile-Time-Typsicherheit

### Negative Konsequenzen / Trade-offs

- Vendor Lock-in bei Vercel (mitigiert: Next.js läuft auch auf Docker/Node, Vercel-spezifische Features können abstrahiert werden)
- Server Components erfordern klare Client/Server-Boundary (`"use client"` Direktive) – Lernkurve für Entwickler
- Vercel-Kosten steigen mit Traffic (mitigiert: Self-Hosting-Option auf Docker für Phase 4)

### Offene Fragen

- Kosten-Projektion für Vercel bei erwartetem Nutzervolumen erstellen
- SSG vs. SSR Entscheidung für Marketing-Pages treffen

---

## DSGVO-Implikationen

- **Datenverarbeitung:** Vercel verarbeitet Requests (IP-Adressen, Cookies) als Auftragsverarbeiter. AVV mit Vercel erforderlich.
- **Analytics:** Keine Drittanbieter-Analytics (Google Analytics etc.) ohne explizite Cookie-Einwilligung. Vercel Web Analytics als datenschutzfreundliche Alternative evaluieren.
- **Cookie-Consent:** Cookie-Banner mit granularer Einwilligung (essentiell, funktional, analytics) implementieren.
- **Datenresidenz:** Vercel Edge Functions können auf EU-Regionen begrenzt werden (Edge Config).
- **Keine Nutzerdaten im Frontend cachen:** Briefings und Suchergebnisse werden nicht im Browser-Cache persistiert (Cache-Control: no-store für sensitive API-Responses).

---

## Sicherheitsimplikationen

- Automatisches HTTPS (TLS 1.3) durch Vercel
- Content Security Policy (CSP) Header gegen XSS-Angriffe
- API-Calls über `/src/lib/api/` abstrahiert – keine direkten `fetch()`-Aufrufe in Komponenten (zentrale Error-Handling und Auth-Header-Injection)
- CSRF-Schutz durch SameSite-Cookies und Origin-Validierung
- Environment-Variablen für API-URLs und Feature-Flags (nie Client-seitig exponiert, außer `NEXT_PUBLIC_`-Prefix)

---

## Revisionsdatum

2027-03-13 – Bewertung der Vercel-Kosten und Performance-Metriken nach 12 Monaten. Evaluation Self-Hosting vs. Vercel.
