# ADR-019: Email as Primary Briefing Delivery Channel

**Status:** Accepted
**Date:** 2026-03-16
**Decision Makers:** Architecture Review (Deep Analysis)

---

## Context

Briefings are generated and displayed in the web dashboard. Users must actively open the app to read their morning briefing. The PRD hypothesis (3 briefing retrievals per week) fails if users don't open the app. Email is the channel all three personas use first thing in the morning.

The email infrastructure is ~80% implemented through TASK-177: `EmailService` with SMTP/SendGrid backends, Jinja2 templates, Celery task `send_briefing_emails`, user fields `email_briefing_enabled` and `briefing_email_time`, frontend settings UI. Six gaps prevent its use as a primary channel: default set to False, missing Markdown→HTML conversion, empty sources, no meeting prep email, no per-user timezone, no event-based meeting trigger.

---

## Decision

We close the six gaps in the existing TASK-177 architecture and make email the primary delivery channel (opt-out instead of opt-in). The web dashboard remains as a detail view. Specifically:

1. **Change Default:** `email_briefing_enabled` default to `True` (Alembic migration + ORM)
2. **Markdown→HTML:** `markdown` package for email rendering, template with `| safe`
3. **Pass Sources Through:** Load source references from DB instead of `sources=[]`
4. **Meeting Prep Email:** Extend `bt_map`, chain after on-demand generation
5. **Idempotency Guard:** `briefing_email_sent_at` on `briefings` table
6. Per-user timezone and event-based meeting trigger remain Phase 3 tasks

---

## Options Evaluated

| Option                    | Advantages                                  | Disadvantages                                                        | Exclusion Reasons                                        |
| ------------------------- | ------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------- |
| A: Close Gaps (minimal)   | 80% exists, isolated changes, no new module | Per-user timezone remains UTC                                        | **Chosen**                                               |
| B: New Delivery Service   | Future-proof for push                       | Over-engineering for MVP, delays impact                              | No immediate engagement improvement                      |
| C: External Email Service | SPF/DKIM out-of-the-box                     | Vendor lock-in, GDPR DPA (Data Processing Agreement) required, costs | Dependency on third-party service for core functionality |

---

## Consequences

### Positive Consequences

- Massively higher engagement rate: Briefings land directly in the inbox
- Activation barrier eliminated: Users don't need to open the app
- Meeting briefings 30 min. before via email (on-demand trigger)
- Source references in emails strengthen the explainability principle
- Minimal effort: Builds entirely on TASK-177

### Negative Consequences / Trade-offs

- Existing users receive emails after migration (mitigation: unsubscribe link in every email)
- Markdown→HTML conversion must be implemented XSS-safe (Jinja2 autoescaping + Markdown safe mode)
- Email duplicates possible on Celery retry without idempotency guard
- Per-user timezone scheduling only in Phase 3

### Open Questions

- Should the default change apply only to new registrations or also update existing users?
- SPF/DKIM/DMARC DNS setup: Which domain? (pwbs.app? briefings.pwbs.app?)
- Should an onboarding email announce the switch to the email channel?

---

## GDPR Implications

- **No new PII fields.** Emails are sent to `users.email` (already existing).
- **Unsubscribe link** in every email (already implemented in base template).
- **Opt-out instead of opt-in:** Legal basis Art. 6(1)(b) (contract performance) – briefing delivery is a core function of the service. Users can deactivate at any time.
- **No tracking pixels** in emails (GDPR-compliant).

---

## Security Implications

- **Markdown→HTML:** Must use sanitized Markdown rendering (no raw HTML allowed in Markdown). `markdown` package with disabled raw HTML extensions.
- **Jinja2 Autoescaping:** `| safe` only used after Markdown conversion, not on user input.
- **SMTP Credentials:** Already configured via environment variables (SMTP_PASSWORD, SENDGRID_API_KEY).
- **Idempotency Guard:** Prevents spam on Celery retries.

---

## Revision Date

Phase 3 start: Evaluate per-user timezone scheduling and event-based meeting trigger.
