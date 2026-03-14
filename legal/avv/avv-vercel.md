# Auftragsverarbeitungsvertrag (AVV) – Vercel

**Vertrag zwischen:**
- **Verantwortlicher:** [Firma/Name], Betreiber des PWBS
- **Auftragsverarbeiter:** Vercel Inc.

**Datum:** [Datum einsetzen]
**Version:** 1.0

---

## 1. Gegenstand der Auftragsverarbeitung

Vercel hostet das PWBS-Frontend (Next.js App Router). Die Verarbeitung umfasst das Ausliefern statischer und serverseitig gerenderter Seiten sowie Edge Functions.

## 2. Dauer

Der AVV gilt für die Laufzeit des Vercel-Servicevertrags.

## 3. Art und Zweck der Verarbeitung

| Aspekt | Beschreibung |
|--------|-------------|
| **Services** | Frontend-Hosting (Next.js), Edge Functions, Build Pipeline |
| **Zweck** | Bereitstellung der PWBS-Benutzeroberfläche |
| **Art** | Auslieferung statischer Assets, serverseitiges Rendering |

## 4. Kategorien betroffener Personen

- PWBS-Nutzer (Browser-Interaktion)

## 5. Kategorien personenbezogener Daten

- **Minimaler Datenumfang:** Keine Backend-Nutzerdaten werden über Vercel verarbeitet
- Browser-Metadaten (IP-Adresse, User-Agent) bei HTTP-Requests
- Potenziell: Analytics-Daten (falls Vercel Analytics aktiviert)

## 6. Pflichten des Auftragsverarbeiters

### 6.1 Datenresidenz
- **Edge Functions auf EU-Region beschränken** (Vercel Edge Network Region Lock)
- CDN-Caching: Keine nutzerspezifischen Daten im CDN-Cache
- Build-Logs: Keine sensiblen Umgebungsvariablen in Build-Output

### 6.2 Datensparsamkeit
- Keine sensiblen Nutzerdaten im Frontend rendern, die Vercel einsehen könnte
- API-Calls gehen direkt vom Client zum PWBS-Backend (nicht über Vercel Serverless)
- JWT-Tokens nur im Browser, nicht in Vercel-Logs

### 6.3 Sicherheit
- TLS 1.2+ für alle Verbindungen
- Automatische HTTPS-Konfiguration
- Content-Security-Policy und Security-Header im Frontend

### 6.4 Weisungsgebundenheit
- Verarbeitung ausschließlich zum Zweck des Frontend-Hostings
- Keine Nutzung von Browser-Metadaten für eigene Zwecke

## 7. Unterauftragsverarbeitung

Sub-Processors: AWS (Hosting der Vercel-Infrastruktur), Cloudflare (ggf. CDN).
Änderungsbenachrichtigung mit 30 Tagen Vorlauf.

## 8. Löschung

- Build-Artifacts: Löschung bei Deployment-Überschreibung
- Access-Logs: Maximale Speicherdauer gemäß Vercel-Policy (30 Tage)
- Nachweis der Löschung auf Anfrage

## 9. Unterstützungspflichten

- Meldung von Sicherheitsvorfällen innerhalb von 72 Stunden
- Bereitstellung von Compliance-Nachweisen (SOC 2)

## 10. Besondere Vereinbarungen

### 10.1 Analytics/Monitoring
- **Vercel Analytics:** Standardmäßig deaktiviert
- Falls aktiviert: Nur anonymisierte Metriken (Web Vitals), keine PII
- Vercel Speed Insights: Opt-in, keine personenbezogenen Daten

### 10.2 Risikominimierung PWBS-seitig
- Frontend ist eine Thin Client — Business-Logik und Datenhaltung liegen im Backend
- Keine PII in Server Components, die Vercel rendern könnte
- API-Abstraktionsschicht (`/src/lib/api/`) stellt sicher, dass keine direkten API-Calls mit Tokens in Vercel-Logs landen
- `"use client"` nur wo nötig — Server Components rendern keine sensitiven Daten

### 10.3 Environment Variables
- Vercel Environment Variables (API-URLs) sind nicht-sensitiv
- Keine Secrets, API-Keys oder DB-Credentials in Vercel-Umgebung
- Backend-URLs als einzige konfigurierte Variable

---

## Referenzen

- Vercel DPA: https://vercel.com/legal/dpa
- Vercel Sub-Processors: https://vercel.com/legal/sub-processors
- Projekt-TOM: `legal/tom.md`
- DSGVO-Erstkonzept: `docs/dsgvo-erstkonzept.md`

---

**Unterschriften:**

| Verantwortlicher | Auftragsverarbeiter (Vercel) |
|:---:|:---:|
| ___________________________ | ___________________________ |
| Name, Datum | Name, Datum |
