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
