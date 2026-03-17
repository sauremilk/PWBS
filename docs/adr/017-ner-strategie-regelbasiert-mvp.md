# ADR-017: NER Strategy MVP – Rule-Based Instead of LLM per Chunk

**Status:** Accepted
**Date:** 2026-03-16
**Decision Makers:** Architecture Review

---

## Context

The NER pipeline is designed as a two-stage process: rule-based extraction (TASK-061) followed by LLM-based extraction (TASK-062) via Claude Structured Output per chunk. The LLM stage is complete as code (`llm_ner.py`, 515 LOC) but **not yet integrated into the pipeline** – the extraction task exclusively uses `RuleBasedNER`.

At planned full deployment with 10–20 Early Adopters (~5,000 chunks/day), ~150,000 Claude calls/month would be incurred (~$450/month just for NER). The rate limit of 100 calls/user/day is insufficient for power users. The briefings use their own LLM call anyway, which can pick up missing entities in context.

---

## Decision

In the MVP, we will **not execute LLM-based NER per chunk**, but instead extend the rule-based extraction (`RuleBasedNER`) with additional regex patterns for dates, decision keywords, question keywords, and goal keywords. `llm_ner.py` remains as code and is held behind a feature flag (`NER_LLM_ENABLED=false`) for later activation (Phase 3 / premium tier).

---

## Options Evaluated

| Option                              | Advantages                                                                    | Disadvantages                                                                                  | Exclusion Reasons                                     |
| ----------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| A: Rule-Only Extended (chosen)      | Zero cost, deterministic, <1ms/chunk, no new dependencies, trivially testable | Lower recall for entities in free text (Zoom transcripts)                                      | –                                                     |
| B: Rule + spaCy                     | Good person recognition in prose, local inference                             | 200 MB model dependency, does not recognize domain-specific entities (Decisions, Goals, Risks) | Disproportionate dependency for marginal MVP benefit  |
| C: Rule + LLM-Selective (Zoom only) | Best quality for transcripts, existing code reusable                          | Still LLM costs, rate limit issues, non-deterministic                                          | Routing complexity, cost/benefit not justified in MVP |

---

## Consequences

### Positive Consequences

- ~$450/month operational cost savings with 20 Early Adopters
- No rate limit bottleneck (100 calls/user/day irrelevant without LLM-NER)
- Deterministic, reproducible extraction – identical results on re-processing
- Faster processing pipeline (~1ms instead of ~2s per chunk)
- No external API dependency in the NER stage (GDPR advantage: data does not leave the system)

### Negative Consequences / Trade-offs

- Lower extraction quality for unstructured texts (especially Zoom transcripts)
- Entity types GOAL, RISK, HYPOTHESIS only detectable via keyword heuristics (confidence ~0.85 vs. LLM ~0.8–0.95)
- Persons in prose without @-mention/email are not recognized
- Briefings partially compensate through their own LLM call

### Open Questions

- Define threshold: At what recall gap should LLM-NER be activated? (Measurement after 4 weeks of MVP operation)
- Feature flag granularity: Per user, per source type, or global?

---

## GDPR Implications

Positive impact: Without LLM-NER, no chunk contents leave the system for entity extraction. Personal data is processed exclusively locally. Existing `owner_id` filters and `expires_at` cascades remain unchanged.

---

## Security Implications

No additional risk. Regex patterns parse content locally and generate no external requests. Extracted entity names pass through `normalized_name` normalization (lowercase, whitespace collapse). No new injection vectors.

---

## Revision Date

2026-07-16 (4 months after MVP launch: evaluate extraction quality based on real user data, decide on LLM-NER activation)
