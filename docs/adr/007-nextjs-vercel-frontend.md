# ADR-007: Next.js on Vercel (Frontend)

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

The PWBS requires a frontend for dashboard, briefing display, semantic search, connector management, knowledge graph explorer, and profile/GDPR settings. The framework must provide server-side rendering for marketing pages (SEO), reactive client interactions for the knowledge explorer, and an excellent developer experience. Deployment simplicity and preview environments for rapid feedback are important.

---

## Decision

We use **Next.js (App Router) with React and TypeScript** on **Vercel** as the frontend stack, because the combination of Server Components, Edge Functions, and zero-config deployment offers the best DX and performance.

---

## Options Evaluated

| Option                         | Advantages                                                                                                                                                                                                         | Disadvantages                                                                                                                  | Exclusion Reasons                   |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------- |
| **Next.js on Vercel** (chosen) | SSR for SEO (marketing pages), Edge Functions for auth, excellent DX (hot reload, preview deployments), App Router + Server Components. Vercel: zero-config deployment, automatic preview environments per branch. | Vendor lock-in with Vercel. Server Components require a learning curve.                                                        | –                                   |
| SPA (Vite + React)             | Maximum control, no server rendering needed, simpler mental model.                                                                                                                                                 | No SSR (bad for marketing page SEO), no edge computing, no preview deployment out-of-the-box.                                  | Missing SSR for marketing           |
| Remix                          | Nested routes, good data loading, web-standards-focused.                                                                                                                                                           | Smaller ecosystem than Next.js, less community support. Deployment options less mature than Vercel.                            | Ecosystem size                      |
| SvelteKit                      | Excellent performance, less boilerplate than React.                                                                                                                                                                | Significantly smaller ecosystem and talent pool. Svelte-specific knowledge required. UI library selection limited (vs. React). | Talent pool and ecosystem too small |

---

## Consequences

### Positive Consequences

- Server Components reduce client bundle size (dashboard, briefing lists can be fully server-side rendered)
- Edge Functions for auth middleware (token validation at the edge, low latency)
- Preview deployments per branch enable rapid visual feedback
- Tailwind CSS as utility-first framework for consistent design
- TypeScript strict mode for compile-time type safety

### Negative Consequences / Trade-offs

- Vendor lock-in with Vercel (mitigated: Next.js also runs on Docker/Node, Vercel-specific features can be abstracted)
- Server Components require a clear client/server boundary (`"use client"` directive) – learning curve for developers
- Vercel costs increase with traffic (mitigated: self-hosting option on Docker for Phase 4)

### Open Questions

- Create cost projection for Vercel at expected user volume
- Decide SSG vs. SSR for marketing pages

---

## GDPR Implications

- **Data Processing:** Vercel processes requests (IP addresses, cookies) as a data processor. Data Processing Agreement (DPA) with Vercel required.
- **Analytics:** No third-party analytics (Google Analytics etc.) without explicit cookie consent. Evaluate Vercel Web Analytics as a privacy-friendly alternative.
- **Cookie Consent:** Implement cookie banner with granular consent (essential, functional, analytics).
- **Data Residency:** Vercel Edge Functions can be restricted to EU regions (Edge Config).
- **No User Data Cached in Frontend:** Briefings and search results are not persisted in the browser cache (Cache-Control: no-store for sensitive API responses).

---

## Security Implications

- Automatic HTTPS (TLS 1.3) through Vercel
- Content Security Policy (CSP) headers against XSS attacks
- API calls abstracted via `/src/lib/api/` – no direct `fetch()` calls in components (centralized error handling and auth header injection)
- CSRF protection through SameSite cookies and origin validation
- Environment variables for API URLs and feature flags (never client-side exposed, except `NEXT_PUBLIC_` prefix)

---

## Revision Date

2027-03-13 – Assessment of Vercel costs and performance metrics after 12 months. Evaluation of self-hosting vs. Vercel.
