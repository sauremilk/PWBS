# ADR-012: React Query Instead of Redux/Zustand for Server State

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

The PWBS frontend must manage server state (briefings, search results, connector status, user profile) and client state (UI state, open modals, filter settings). Server state and client state have fundamentally different requirements: server state must be cached, refetched, invalidated, and synchronized, while client state is local and synchronous. The choice of state management strategy affects bundle size, boilerplate amount, and caching behavior.

---

## Decision

We use **React Query (TanStack Query)** for server state management and **Zustand** minimally for client UI state, because this separation reduces complexity and uses the right tool for each state category.

---

## Options Evaluated

| Option                                       | Advantages                                                                                                                                                                                       | Disadvantages                                                                                                                                                                       | Exclusion Reasons                  |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **React Query + Zustand (minimal)** (chosen) | Server state: optimized caching, stale-while-revalidate, automatic refetching, deduplication. Client state: Zustand is lightweight (~1KB), no boilerplate. Clear separation of responsibilities. | Two libraries instead of one. React Query has a learning curve (query keys, invalidation, mutations).                                                                               | –                                  |
| Redux Toolkit + RTK Query                    | Unified state library, RTK Query for server state, Redux Toolkit for client state. Large ecosystem, DevTools.                                                                                    | Significantly more boilerplate (slices, reducers, actions). Redux mental model (immutable state, dispatch) oversized for PWBS requirements. RTK Query less mature than React Query. | Too much boilerplate for MVP       |
| Zustand for everything                       | One library, minimal API footprint, no provider needed.                                                                                                                                          | Manual implementation of caching, refetching, stale-while-revalidate, deduplication. Fetch logic separate in each store.                                                            | Missing server state optimizations |
| Apollo Client                                | Excellent caching, optimistic updates, subscriptions.                                                                                                                                            | Designed for GraphQL – PWBS uses REST. REST support (apollo-rest-link) cumbersome and less mature. Larger bundle size.                                                              | REST API, not GraphQL              |

---

## Consequences

### Positive Consequences

- Stale-while-revalidate: Instant UI response from cache, background refetch for freshness
- Automatic query deduplication: Multiple components needing the same data trigger only one API call
- Focused refetching: `invalidateQueries` after mutations selectively updates affected cache entries
- Zustand (~1KB) for minimal client state: No global store complexity for UI toggles and filters
- DevTools for React Query and Zustand simplify debugging

### Negative Consequences / Trade-offs

- Two state libraries instead of one (mitigated: clear separation – React Query for everything from the server; Zustand only for local UI state like sidebar collapse, theme preference)
- React Query has a learning curve: Query keys as cache IDs, invalidation strategies, mutation callbacks (mitigated: standardized query key factory and custom hooks in `/src/lib/api/`)
- Zustand store can become unwieldy with uncontrolled growth (mitigated: strict Zustand budget – only UI state, no server state)

### Open Questions

- Standardize query key convention (e.g., `['briefings', userId, type]`, `['search', query, filters]`)
- Prefetching strategy for briefings (Server Components prefetch, client hydrates)
- React Query + Server Components integration (Next.js Hydration Boundary)

---

## GDPR Implications

- **Client cache:** React Query caches server responses in browser memory. Sensitive data (briefings, search results) is refetched when staleTime expires and invalidated on logout (queryClient.clear()).
- **No persistent cache:** By default, no LocalStorage/SessionStorage caching for API responses (no user data persisted in the browser).
- **Cache-Control:** API responses with `Cache-Control: no-store` for sensitive endpoints prevent browser disk caching.
- **Logout cleanup:** `queryClient.clear()` on logout removes all cached user data from memory.

---

## Security Implications

- All API calls via central `/src/lib/api/` abstraction with automatic auth header injection
- Token refresh logic integrated in React Query retry handler (401 → refresh → retry)
- No secrets or tokens stored in Zustand store (only UI state)
- Query results in DevTools panel show user data – DevTools only enabled in development builds
- XSS protection: Cached API responses are rendered via React DOM (automatic escaping)

---

## Revision Date

2027-03-13 – Assessment of state management complexity and developer experience after 12 months. Evaluation of whether Zustand is still needed or Server Components suffice.
