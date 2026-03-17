# ADR-013: Governance Framework and Development Standards

**Status:** Accepted
**Date:** March 13, 2026
**Decision Makers:** Project Founder

---

## Context

The PWBS is growing from Phase 1 (PoC) into Phase 2 (MVP) with up to 12 parallel AI orchestrators. Without formalized processes for branching, commit conventions, code reviews, task lifecycle, and decision documentation, inconsistencies, hard-to-trace changes, and coordination errors between humans and AI are imminent. A binding development rulebook is a prerequisite for scalable, traceable collaboration.

---

## Decision

We will establish a central governance document (`GOVERNANCE.md`) as a binding rulebook for all development processes, because it should be the single source of truth for process questions — for both human developers and AI agents.

---

## Options Evaluated

| Option                                        | Advantages                                                          | Disadvantages                                               | Exclusion Reasons                    |
| --------------------------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------ |
| Scattered rules in README, CONTRIBUTING, ADRs | Decentralized, flexible                                             | Inconsistent, hard to find, contradictions possible         | Does not scale with 12 orchestrators |
| Wiki-based documentation (GitHub Wiki)        | Searchable, versioned                                               | Outside the repo, not in Git history, not in editor context | AI agents have no wiki access        |
| **Central GOVERNANCE.md + enforcement files** | Versioned in repo, machine-readable, pre-commit hooks enforce rules | One large document, must be maintained                      | –                                    |

---

## Consequences

### Positive Consequences

- Unified processes for humans and AI — same rules, same tools
- Commits are machine-readable and automatically evaluable through Conventional Commits
- Code reviews have a standardized checklist via the PR template (including GDPR)
- Trunk-based development with short-lived branches prevents diverging code branches
- Pre-commit hooks catch errors **before** the commit, not only in CI
- ADR framework with mandatory fields (GDPR, security, revision) prevents incomplete documentation
- CHANGELOG.md provides a human-readable change history with TASK-ID traceability

### Negative Consequences / Trade-offs

- Overhead: Every commit must follow the Conventional Commits format
- Orchestrator special rules (direct push to master) deviate from the standard — risk of conflicts
- Governance document must be actively maintained, otherwise it becomes outdated

### Open Questions

- When to switch to GitHub Actions CI/CD (TASK-012)?
- Should the `no-commit-to-branch` hook be disabled for orchestrators or bypassed via `--no-verify`?

---

## GDPR Implications

No direct GDPR implications. The governance framework **strengthens** GDPR compliance through mandatory checklists in PRs and ADRs (owner_id filters, expires_at, deletion cascades, PII checks).

---

## Security Implications

- Pre-commit hook `detect-private-key` prevents committing private keys
- PR template contains OWASP checklist
- Security gate for security-relevant changes (2 reviewers)
- Risk: Orchestrators use `--no-verify` for the `no-commit-to-branch` hook — other hooks (linting, keys) remain active

---

## Revision Date

September 2026 — after completion of Phase 2 MVP development, evaluate whether the processes scale.
