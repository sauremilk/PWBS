# ADR-014: Beta Launch Strategy – Hybrid Go-to-Market for 100-500 Users

**Status:** Accepted
**Date:** 2026-03-14
**Decision Makers:** Project Team

---

## Context

PWBS is production-ready with 159/175 tasks (91%). The roadmap defines as Phase 3 goal "100-500 active beta users" with > 60% 30-day retention and > 30% willingness to pay. There is no large advertising budget (roadmap assumption: "community-driven growth"). The target audience (founders, PMs, consultants with PKM affinity) is a clearly delineated niche, reachable via PKM communities (Obsidian, Zettelkasten, Notion). The technical infrastructure (Discord community setup, feature flags, billing, k6 load tests) is prepared, but a coordinated launch strategy is missing.

---

## Decision

We will pursue a **hybrid strategy** (community building + coordinated launch + referral loop), because it combines the high niche conversion of community marketing (4-8%) with the visibility of a launch event and ensures sustainable growth through a referral system.

### Phases

1. **Weeks 1-2 (Foundation):** GDPR-compliant analytics (Plausible/Fathom), landing page with demo video, minimal referral mechanism (UUID-based invite codes), load testing at 500 VUs
2. **Weeks 2-4 (Community):** Authentic presence in Obsidian Discord, Reddit (r/Zettelkasten, r/PKMS), LinkedIn. 5-10 hand-picked "Design Partners" with 1-on-1 onboarding. Goal: 200 Discord members before launch
3. **Week 5 (Launch):** Coordinated ProductHunt + HackerNews "Show HN" + newsletter + LinkedIn announcement. Community as upvote and testimonial base
4. **Week 6+ (Growth):** Referral activation after 7 days of active usage, content pipeline (blog, use cases), monthly community events

### Channels and Expected Conversion

| Channel                            | Reach             | Signups       | Active Beta Users |
| ---------------------------------- | ----------------- | ------------- | ----------------- |
| PKM Communities (Obsidian, Reddit) | 5,000             | 160-350       | 65-140            |
| LinkedIn (organic)                 | 5,000             | 50-100        | 20-40             |
| ProductHunt + HackerNews           | 7,000-25,000      | 140-500       | 55-200            |
| Design Partners                    | 10                | 10            | 8-10              |
| Referral (from Week 4)             | -                 | 30-80         | 15-40             |
| **TOTAL**                          | **17,000-35,000** | **390-1,040** | **163-430**       |

---

## Options Evaluated

| Option                 | Advantages                                                                | Disadvantages                                         | Exclusion Reasons                        |
| ---------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------- |
| A: Community Only      | Low cost, high conversion, sustainable                                    | Too slow (3-6 months for 100 users), momentum is lost | Speed incompatible with roadmap timeline |
| B: Launch Event Only   | High visibility, fast                                                     | One-time spike, no safety net, no testimonials        | Too risky without community base         |
| **C: Hybrid (chosen)** | Combines community base with launch peak, referral ensures sustainability | Highest coordination effort                           | -                                        |

---

## Consequences

### Positive Consequences

- Product-market fit validation with high-quality feedback (Design Partners + community)
- Building a community asset that scales further for Phase 4 (1,000-5,000 users)
- NPS and testimonial base for later marketing activities
- Low cost (primarily time investment, no ad spend needed)

### Negative Consequences / Trade-offs

- Significant time investment for community engagement (10-15h/week in Phase 2)
- ProductHunt/HN launch is not repeatable — must succeed on the first attempt
- Referral mechanism requires minimal engineering effort

### Open Questions

- Who is the "Hunter" for ProductHunt? (Ideally someone with a follower base in the PKM niche)
- Should the beta be limited (e.g., "500 spots") or open? Artificial scarcity increases FOMO but can hinder authentic community growth
- Pricing during beta: Free with upgrade path or immediately $20/month with 50% beta discount?

---

## GDPR Implications

- **Analytics:** Plausible/Fathom instead of Google Analytics (no cookie banner needed, EU hosting)
- **Referral codes:** UUID-based, not linked to email, no PII
- **Community data:** Discord accounts not linked to PWBS accounts (existing rule from community-setup.md)
- **Landing page signups:** Email addresses with explicit consent (double opt-in), deletion after beta start

---

## Security Implications

- **Registration spam at launch:** Rate limiting on /api/v1/auth/register exists (TASK-108)
- **Referral abuse:** Max 20 invites per user, codes with 7-day expiry
- **Launch spike load:** Validate k6 load test at 500 VUs BEFORE launch, check connection pool and Redis cache
- **Waitlist fallback:** Feature flag `beta_registration_open` for immediate cutoff on overload

---

## Revision Date

After reaching 100 active beta users (estimated weeks 5-6 after start) or after 8 weeks, whichever comes first.
