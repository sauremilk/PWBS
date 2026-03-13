# ADR-005: Claude API als primärer LLM-Provider

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

Das PWBS verwendet Large Language Models für die Generierung von Briefings, die Beantwortung von Suchanfragen mit Quellenbelegen und die Extraktion von Entitäten (NER). Der gewählte LLM-Provider muss strukturierte Output-Fähigkeiten (JSON-Schema), ein großes Kontextfenster für RAG-Workflows und eine akzeptable Compliance-Positionierung für den Einsatz mit personenbezogenen Daten bieten. Vendor Lock-in muss durch Abstraktion und Fallback-Optionen vermieden werden.

---

## Entscheidung

Wir verwenden die **Claude API (Anthropic)** als primären LLM-Provider mit **GPT-4 (OpenAI)** als Fallback und **Ollama** als lokale/offline-Option, weil Claude das beste Gesamtpaket aus strukturiertem Output, großem Kontextfenster und Compliance-Eignung bietet.

---

## Optionen bewertet

| Option | Vorteile | Nachteile | Ausschlussgründe |
|--------|----------|-----------|-------------------|
| **Claude API (primär) + GPT-4 (Fallback)** (gewählt) | Starke strukturierte Output-Fähigkeit (JSON-Schema), 200K-Token-Kontextfenster, gute Compliance-Positionierung (Anthropic). GPT-4 als Fallback verhindert Vendor Lock-in. | Abhängigkeit von US-basiertem Provider. API-Kosten bei hohem Volumen. | – |
| GPT-4 only | Breitestes Ökosystem, Function Calling, stabile API. | Single-Vendor-Risiko. Kleineres Standard-Kontextfenster als Claude. OpenAI-Datenschutzrichtlinien weniger klar für EU-Kunden. | Single-Vendor-Lock-in |
| Open-Source only (Llama/Mistral) | Volle Datenkontrolle, keine API-Kosten, On-Premise-fähig. | Deutlich geringere Qualität bei komplexen Briefings und Structured Output. Hoher GPU-Bedarf für Hosting. | Qualität nicht ausreichend für MVP |
| Multi-Provider ab Start | Maximale Flexibilität, kein Lock-in. | Deutlich höherer Implementierungsaufwand im MVP. Prompt-Engineering für jeden Provider separat. Inkonsistente Ergebnisqualität. | Zu hoher MVP-Aufwand |

---

## Konsequenzen

### Positive Konsequenzen

- 200K-Token-Kontextfenster ermöglicht umfangreiche RAG-Kontexte ohne aggressives Chunking
- Strukturierter Output (JSON-Schema) reduziert Post-Processing und Parsing-Fehler bei Briefings
- GPT-4 als Fallback bietet Redundanz bei Claude-API-Ausfällen
- Ollama als lokale Option ermöglicht Offline-Nutzung und DSGVO-Strict-Modus (keine Daten an US-Provider)
- LLM-Orchestration-Service abstrahiert Provider-Details – neuer Provider = neuer Adapter, kein Refactoring

### Negative Konsequenzen / Trade-offs

- Abhängigkeit von US-basiertem Provider für die primäre Cloud-Variante (mitigiert: Ollama als lokale Alternative, EU-basierte LLM-Provider können in Phase 4 hinzugefügt werden)
- API-Kosten skalieren mit Nutzerzahl und Briefing-Frequenz (mitigiert: Caching von Briefings, Temperatur 0.3 für deterministische Ergebnisse, Pre-Generation mit zeitlichem Jitter)
- Prompt-Engineering muss für Claude und GPT-4 separat optimiert werden (mitigiert: Structured Output über JSON-Schema reduziert Provider-spezifische Varianz)

### Offene Fragen

- EU-basierte LLM-Provider (z.B. Aleph Alpha, Mistral via EU-Hosting) für DSGVO-Strict-Modus evaluieren
- Kosten-Monitoring und Budget-Alerts für LLM-API-Calls implementieren

---

## DSGVO-Implikationen

- **Datenübermittlung:** LLM-API-Calls an Claude/GPT-4 übermitteln Nutzerdaten an US-Provider. Erfordert AVV mit Anthropic und OpenAI. EU-Standardvertragsklauseln (SCCs) erforderlich.
- **Datenminimierung:** Nur relevante Chunks werden als Kontext gesendet, nicht die gesamte Nutzerdatenbank. Prompt-Templates minimieren personenbezogene Daten.
- **Kein Training:** Vertragliche Zusicherung, dass Nutzerdaten nicht für LLM-Training verwendet werden (API-TOS von Anthropic und OpenAI bestätigen dies für API-Kunden).
- **DSGVO-Strict-Modus:** Ollama als lokale Alternative – keine Daten verlassen die Infrastruktur. EU-basierte LLM-Provider als Cloud-Alternative in Phase 4.
- **Auditierbarkeit:** Jeder LLM-Call wird im Audit-Log protokolliert (Prompt-Hash, nicht Klartext-Prompt).

---

## Sicherheitsimplikationen

- TLS 1.3 für alle API-Calls an Claude/GPT-4
- API-Keys über Environment-Variablen, nie im Code
- Rate-Limiting auf LLM-Calls zur Kostenkontrolle und Missbrauchsprävention
- Prompt-Injection-Schutz: Nutzereingaben werden als User-Messages getrennt von System-Prompts behandelt
- Keine Speicherung von LLM-Responses im Klartext in Logs (nur Briefing-Ergebnisse in DB)

---

## Revisionsdatum

2027-03-13 – Bewertung der LLM-Kosten, API-Verfügbarkeit und Qualitätsvergleich Claude vs. GPT-4 vs. Open-Source-Modelle nach 12 Monaten.
