# ADR-012: React Query statt Redux/Zustand für Server-State

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

Das PWBS-Frontend muss Server-State (Briefings, Suchergebnisse, Konnektoren-Status, Nutzerprofil) und Client-State (UI-Zustand, offene Modals, Filter-Einstellungen) verwalten. Server-State und Client-State haben grundverschiedene Anforderungen: Server-State muss gecacht, refetched, invalidiert und synchronisiert werden, während Client-State lokal und synchron ist. Die Wahl der State-Management-Strategie beeinflusst Bundle-Size, Boilerplate-Menge und Caching-Verhalten.

---

## Entscheidung

Wir verwenden **React Query (TanStack Query)** für Server-State-Management und **Zustand** minimal für Client-UI-State, weil diese Trennung die Komplexität reduziert und das richtige Tool für jede State-Kategorie verwendet.

---

## Optionen bewertet

| Option                                        | Vorteile                                                                                                                                                                                                         | Nachteile                                                                                                                                                                                        | Ausschlussgründe                    |
| --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------- |
| **React Query + Zustand (minimal)** (gewählt) | Server-State: optimiertes Caching, Stale-While-Revalidate, automatisches Refetching, Deduplication. Client-State: Zustand ist leichtgewichtig (~1KB), kein Boilerplate. Klare Trennung der Verantwortlichkeiten. | Zwei Libraries statt einer. React Query hat Lernkurve (Query Keys, Invalidation, Mutations).                                                                                                     | –                                   |
| Redux Toolkit + RTK Query                     | Einheitliche State-Library, RTK Query für Server-State, Redux Toolkit für Client-State. Großes Ökosystem, DevTools.                                                                                              | Deutlich mehr Boilerplate (Slices, Reducers, Actions). Redux-mentales Modell (immutable State, Dispatch) überdimensioniert für PWBS-Anforderungen. RTK Query weniger ausgereift als React Query. | Zu viel Boilerplate für MVP         |
| Zustand für alles                             | Eine Library, minimaler API-Footprint, kein Provider nötig.                                                                                                                                                      | Manuelles Implementieren von Caching, Refetching, Stale-While-Revalidate, Deduplication. Fetch-Logik in jedem Store separat.                                                                     | Fehlende Server-State-Optimierungen |
| Apollo Client                                 | Hervorragendes Caching, optimistic Updates, Subscriptions.                                                                                                                                                       | Designt für GraphQL – PWBS verwendet REST. REST-Support (apollo-rest-link) umständlich und weniger ausgereift. Größere Bundle-Size.                                                              | REST-API, nicht GraphQL             |

---

## Konsequenzen

### Positive Konsequenzen

- Stale-While-Revalidate: Sofortige UI-Response aus dem Cache, Background-Refetch für Aktualität
- Automatische Query-Deduplication: Mehrere Komponenten, die dieselben Daten brauchen, lösen nur einen API-Call aus
- Fokussiertes Refetching: `invalidateQueries` nach Mutations aktualisiert gezielt betroffene Cache-Einträge
- Zustand (~1KB) für minimalen Client-State: Keine globale Store-Komplexität für UI-Toggles und Filter
- DevTools für React Query und Zustand vereinfachen Debugging

### Negative Konsequenzen / Trade-offs

- Zwei State-Libraries statt einer (mitigiert: klare Trennung – React Query für alles, was vom Server kommt; Zustand nur für lokale UI-State wie Sidebar-Collapse, Theme-Preference)
- React Query hat Lernkurve: Query Keys als Cache-IDs, Invalidation-Strategien, Mutation-Callbacks (mitigiert: Standardisierte Query-Key-Factory und Custom Hooks in `/src/lib/api/`)
- Zustand-Store kann bei unkontrolliertem Wachstum unübersichtlich werden (mitigiert: striktes Zustand-Budget – nur UI-State, kein Server-State)

### Offene Fragen

- Query-Key-Konvention standardisieren (z.B. `['briefings', userId, type]`, `['search', query, filters]`)
- Prefetching-Strategie für Briefings (Server Components prefetchen, Client hydriert)
- React Query + Server Components Integration (Next.js Hydration-Boundary)

---

## DSGVO-Implikationen

- **Client-Cache:** React Query cached Server-Responses im Browser-Memory. Sensible Daten (Briefings, Suchergebnisse) werden bei staleTime-Ablauf refetched und bei Logout invalidiert (queryClient.clear()).
- **Kein persistenter Cache:** Standardmäßig kein LocalStorage/SessionStorage-Caching für API-Responses (keine Nutzerdaten persistieren im Browser).
- **Cache-Control:** API-Responses mit `Cache-Control: no-store` für sensible Endpunkte verhindern Browser-Disk-Caching.
- **Logout-Cleanup:** `queryClient.clear()` bei Logout entfernt alle gecachten Nutzerdaten aus dem Memory.

---

## Sicherheitsimplikationen

- Alle API-Calls über zentrale `/src/lib/api/` Abstraktion mit automatischer Auth-Header-Injection
- Token-Refresh-Logik in React Query Retry-Handler integriert (401 → Refresh → Retry)
- Keine Secrets oder Tokens in Zustand-Store speichern (nur UI-State)
- Query Results im DevTools-Panel zeigen Nutzerdaten – DevTools nur in Development-Builds aktiviert
- XSS-Schutz: Cached API-Responses werden via React-DOM gerendert (automatisches Escaping)

---

## Revisionsdatum

2027-03-13 – Bewertung der State-Management-Komplexität und Developer Experience nach 12 Monaten. Evaluation, ob Zustand weiterhin benötigt wird oder Server Components ausreichen.
