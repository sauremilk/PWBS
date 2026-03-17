# ADR-005: Claude API as Primary LLM Provider

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

The PWBS uses Large Language Models for generating briefings, answering search queries with source references, and extracting entities (NER). The chosen LLM provider must offer structured output capabilities (JSON schema), a large context window for RAG workflows, and an acceptable compliance positioning for use with personal data. Vendor lock-in must be avoided through abstraction and fallback options.

---

## Decision

We use the **Claude API (Anthropic)** as the primary LLM provider with **GPT-4 (OpenAI)** as fallback and **Ollama** as a local/offline option, because Claude offers the best overall package of structured output, large context window, and compliance suitability.

---

## Options Evaluated

| Option                                                | Advantages                                                                                                                                                                    | Disadvantages                                                                                                                             | Exclusion Reasons                    |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| **Claude API (primary) + GPT-4 (fallback)** (chosen)  | Strong structured output capability (JSON schema), 200K token context window, good compliance positioning (Anthropic). GPT-4 as fallback prevents vendor lock-in.             | Dependency on US-based provider. API costs at high volume.                                                                                | \u2013                                    |
| GPT-4 only                                            | Broadest ecosystem, function calling, stable API.                                                                                                                             | Single-vendor risk. Smaller standard context window than Claude. OpenAI privacy policies less clear for EU customers.                     | Single-vendor lock-in                |
| Open-source only (Llama/Mistral)                      | Full data control, no API costs, on-premise capable.                                                                                                                          | Significantly lower quality for complex briefings and structured output. High GPU requirements for hosting.                               | Quality not sufficient for MVP       |
| Multi-provider from the start                         | Maximum flexibility, no lock-in.                                                                                                                                              | Significantly higher implementation effort in MVP. Prompt engineering required separately for each provider. Inconsistent result quality. | Too high effort for MVP              |

---

## Consequences

### Positive Consequences

- 200K token context window enables extensive RAG contexts without aggressive chunking
- Structured output (JSON schema) reduces post-processing and parsing errors in briefings
- GPT-4 as fallback provides redundancy during Claude API outages
- Ollama as a local option enables offline usage and GDPR-strict mode (no data sent to US providers)
- LLM orchestration service abstracts provider details \u2013 new provider = new adapter, no refactoring

### Negative Consequences / Trade-offs

- Dependency on US-based provider for the primary cloud variant (mitigated: Ollama as local alternative, EU-based LLM providers can be added in Phase 4)
- API costs scale with user count and briefing frequency (mitigated: caching of briefings, temperature 0.3 for deterministic results, pre-generation with temporal jitter)
- Prompt engineering must be optimized separately for Claude and GPT-4 (mitigated: structured output via JSON schema reduces provider-specific variance)

### Open Questions

- Evaluate EU-based LLM providers (e.g., Aleph Alpha, Mistral via EU hosting) for GDPR-strict mode
- Implement cost monitoring and budget alerts for LLM API calls

---

## GDPR Implications

- **Data Transfer:** LLM API calls to Claude/GPT-4 transmit user data to US providers. Requires a Data Processing Agreement (DPA) with Anthropic and OpenAI. EU Standard Contractual Clauses (SCCs) required.
- **Data Minimization:** Only relevant chunks are sent as context, not the entire user database. Prompt templates minimize personal data.
- **No Training:** Contractual assurance that user data is not used for LLM training (API TOS from Anthropic and OpenAI confirm this for API customers).
- **GDPR-Strict Mode:** Ollama as a local alternative \u2013 no data leaves the infrastructure. EU-based LLM providers as cloud alternative in Phase 4.
- **Auditability:** Every LLM call is logged in the audit log (prompt hash, not plaintext prompt).

---

## Security Implications

- TLS 1.3 for all API calls to Claude/GPT-4
- API keys via environment variables, never in code
- Rate limiting on LLM calls for cost control and abuse prevention
- Prompt injection protection: user inputs are treated as user messages separated from system prompts
- No storage of LLM responses in plaintext in logs (only briefing results in DB)

---

## Revision Date

2027-03-13 \u2013 Assessment of LLM costs, API availability, and quality comparison of Claude vs. GPT-4 vs. open-source models after 12 months.
