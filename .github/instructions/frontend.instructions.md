---
applyTo: "frontend/**/*.{ts,tsx}"
---

# Frontend-Instruktionen: Next.js / React / TypeScript

## Projekt-Struktur (App Router)

```
frontend/
├── src/
│   ├── app/                  # Next.js App Router: Seiten, Layouts, Routen
│   │   ├── (auth)/           # Authentifizierte Route-Gruppe
│   │   ├── (public)/         # Öffentliche Route-Gruppe
│   │   └── api/              # API Route Handler (nur für BFF-Patterns)
│   ├── components/
│   │   ├── ui/               # Primitive UI-Komponenten (Button, Card, etc.)
│   │   ├── features/         # Feature-spezifische Komponenten
│   │   └── layouts/          # Layout-Komponenten
│   ├── lib/
│   │   ├── api/              # API-Client-Abstraktionen (PFLICHT für alle Fetches)
│   │   ├── hooks/            # Custom React Hooks
│   │   └── utils/            # Utility-Funktionen
│   └── types/                # Globale TypeScript-Typen und Interfaces
```

## Pflichtregeln

### TypeScript

- `"strict": true` in `tsconfig.json`. Keine impliziten `any`.
- Explizite Props-Interfaces für jede Komponente:

  ```tsx
  interface BriefingCardProps {
    briefing: Briefing;
    onExpand?: (id: string) => void;
  }

  export function BriefingCard({ briefing, onExpand }: BriefingCardProps) { ... }
  ```

- Enums vermeiden – stattdessen `as const`-Objekte oder Union-Types verwenden.
- `unknown` statt `any` für unbekannte Typen aus externen Quellen.

### Server/Client Components

- Standard-Annahme: Server Component. `"use client"` nur wenn zwingend nötig.
- `"use client"` ist nötig für: Event-Handler, Browser-APIs, React-State/-Effekte.
- Daten-Fetching immer in Server Components, nie in Client Components mit `useEffect`.
- Sensible Daten (API-Keys, Nutzer-PII) niemals in Client Components exponieren.

### API-Aufrufe

```typescript
// KORREKT – über /src/lib/api/ abstrahieren
import { briefingApi } from "@/lib/api/briefing";
const briefing = await briefingApi.getMorningBriefing(userId);

// FALSCH – direkte fetch()-Aufrufe in Komponenten
const res = await fetch("/api/briefings/morning"); // VERBOTEN in Komponenten
```

### State Management

- Server State: `fetch()` in Server Components oder React Server Actions.
- Client State: `useState`/`useReducer` für lokale UI-Zustände.
- Kein globaler Client-State-Store (kein Zustand/Redux) für Server-Daten.
- Formulare über React Server Actions (kein extra API-Endpunkt nötig).

### Quellenreferenzen (DSGVO + Erklärbarkeit)

- Jede LLM-generierte Aussage im Frontend MUSS Quellenreferenzen anzeigen.
- Komponente `<SourceBadge source={ref} />` für Quellenangaben verwenden.
- Fakten und Interpretationen visuell unterscheiden (z.B. Farb-Coding).

### Sicherheit

- Keine Nutzerdaten in Browser-Storage (localStorage, sessionStorage) ablegen.
- JWT-Tokens nur in `httpOnly`-Cookies – nie im JS-zugänglichen Speicher.
- CSP-Header in `next.config.ts` konfigurieren.
- XSS-Prävention: `dangerouslySetInnerHTML` vermeiden. Wenn nötig: DOMPurify.

### Styling

- Tailwind CSS für alle Styles. Keine inline Styles.
- `cn()` utility (clsx + tailwind-merge) für bedingte Klassen.
- `shadcn/ui`-Primitive als Basis für Komponenten.
- Dark Mode via `class`-Strategie in Tailwind.

## Frontend-Ästhetik

Generische "AI Slop"-Ästhetik vermeiden. Kreative, distinkte Frontends erstellen, die überraschen und Freude bereiten.

### Typografie

- Schriftarten wählen, die schön, einzigartig und charaktervoll sind.
- Generische Schriftarten vermeiden: Inter, Roboto, Arial, System-Fonts.
- Auch häufig von KI gewählte Alternativen meiden (z.B. Space Grotesk) – aktiv unkonventionelle Optionen suchen.
- Google Fonts oder Fontsource für distinctive Typefaces nutzen.

### Farbe & Thema

- Sich zu einer kohärenten Ästhetik verpflichten. CSS-Variablen für Konsistenz verwenden.
- Dominante Farben mit scharfen Akzenten übertreffen timide, gleichmäßig verteilte Paletten.
- Inspiration aus IDE-Themen, kulturellen Ästhetiken, Printdesign schöpfen.
- Klischeehafte Farbschemen vermeiden – insbesondere violette Gradienten auf weißem Hintergrund.
- Zwischen hellen und dunklen Themen variieren, nicht immer dieselbe Basis wählen.

### Motion & Micro-Interaktionen

- Animationen für Effekte und Micro-Interaktionen einsetzen.
- CSS-only-Lösungen bevorzugen (`@keyframes`, `transition`, `animation-delay`).
- Für React: `motion`-Bibliothek (Framer Motion) wenn verfügbar.
- Hochwertige Momente priorisieren: Ein orchestriertes Page-Load mit gestaffelten Reveals (`animation-delay`) schafft mehr Freude als verstreute Micro-Interaktionen.

### Hintergründe & Atmosphäre

- Atmosphäre und Tiefe schaffen statt Vollfarben zu verwenden.
- CSS-Gradienten schichten, geometrische Muster nutzen, kontextuelle Effekte einsetzen.
- Hintergründe zur Gesamtästhetik passen, nicht isoliert betrachten.

### Anti-Patterns (aktiv vermeiden)

- Übernutzte Schriftfamilien (Inter, Roboto, Arial, Space Grotesk, System-Fonts)
- Klischeehafte Farbschemen (violette Gradienten, generisches Blau/Weiß)
- Vorhersehbare Layouts und Cookie-Cutter-Komponentenmuster
- Design ohne kontextspezifischen Charakter

Kreativ interpretieren und unerwartete Entscheidungen treffen, die sich für den Kontext genuine designt anfühlen.

## Briefing-Feature (Kern-UX)

Die Briefing-Ansicht ist das Herzstück der App:

- Briefing-Karten zeigen Quellenreferenzen immer sichtbar an.
- Meeting-Briefings sind pre-rendering fähig (ISR mit 5-Min-Revalidierung).
- Morgenbriefing wird per Cron-Job (Route Handler) gecacht und als Static Segment ausgeliefert.

## Fehlerbehandlung

```typescript
// Error Boundaries für Feature-Abschnitte
import { ErrorBoundary } from "react-error-boundary";

// Strukturierte API-Fehler (entsprechend Backend-Format)
interface ApiError {
  code: string;
  message: string;
  field?: string;
}
```
