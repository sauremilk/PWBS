# ADR-017: NER-Strategie MVP  Regelbasiert statt LLM pro Chunk

**Status:** Akzeptiert
**Datum:** 2026-03-16
**Entscheider:** Architektur-Review

---

## Kontext

Die NER-Pipeline ist zweistufig konzipiert: regelbasierte Extraktion (TASK-061) gefolgt von LLM-basierter Extraktion (TASK-062) via Claude Structured Output pro Chunk. Die LLM-Stufe ist als Code fertig (`llm_ner.py`, 515 LOC) aber **noch nicht in die Pipeline integriert**  der Extraction-Task nutzt ausschliesslich `RuleBasedNER`.

Bei geplantem Vollausbau wuerden bei 10-20 Early Adopters (~5.000 Chunks/Tag) ~150.000 Claude-Calls/Monat anfallen (~$450/Monat nur fuer NER). Das Rate-Limit von 100 Calls/User/Tag reicht fuer Power-User nicht. Die Briefings nutzen ohnehin einen eigenen LLM-Call, der fehlende Entitaeten im Kontext aufgreifen kann.

---

## Entscheidung

Wir werden im MVP **keine LLM-basierte NER pro Chunk ausfuehren**, sondern die regelbasierte Extraktion (`RuleBasedNER`) um zusaetzliche Regex-Patterns fuer Datum, Entscheidungs-, Frage- und Ziel-Keywords erweitern. `llm_ner.py` bleibt als Code erhalten und wird hinter einem Feature-Flag (`NER_LLM_ENABLED=false`) fuer spaetere Aktivierung (Phase 3 / Premium-Tier) vorgehalten.

---

## Optionen bewertet

| Option | Vorteile | Nachteile | Ausschlussgruende |
| --- | --- | --- | --- |
| A: Rule-Only Extended (gewaehlt) | Null Kosten, deterministisch, <1ms/Chunk, keine neuen Dependencies, trivial testbar | Geringere Recall bei Entitaeten in Freitext (Zoom-Transkripte) |  |
| B: Rule + spaCy | Gute Personenerkennung in Fliesstext, lokale Inferenz | 200 MB Modell-Dependency, erkennt keine domaenenspezifischen Entities (Decisions, Goals, Risks) | Unverhaeltnismaessige Dependency fuer marginalen MVP-Mehrwert |
| C: Rule + LLM-Selective (nur Zoom) | Beste Qualitaet fuer Transkripte, bestehender Code wiederverwendbar | Weiterhin LLM-Kosten, Rate-Limit-Probleme, nicht-deterministisch | Routing-Komplexitaet, Kosten/Nutzen im MVP nicht gerechtfertigt |

---

## Konsequenzen

### Positive Konsequenzen

- ~$450/Monat Betriebskosten-Einsparung bei 20 Early Adopters
- Kein Rate-Limit-Engpass (100 Calls/User/Tag irrelevant ohne LLM-NER)
- Deterministische, reproduzierbare Extraktion  identische Ergebnisse bei Re-Processing
- Schnellere Processing-Pipeline (~1ms statt ~2s pro Chunk)
- Keine externe API-Abhaengigkeit in der NER-Stufe (DSGVO-Vorteil: Daten verlassen System nicht)

### Negative Konsequenzen / Trade-offs

- Geringere Extraktionsqualitaet bei unstrukturierten Texten (insb. Zoom-Transkripte)
- Entity-Typen GOAL, RISK, HYPOTHESIS nur per Keyword-Heuristik erkennbar (Confidence ~0.85 statt LLM ~0.8-0.95)
- Personen in Fliesstext ohne @-Mention/Email werden nicht erkannt
- Briefings kompensieren teilweise ueber ihren eigenen LLM-Call

### Offene Fragen

- Schwellenwert definieren: Ab welcher Recall-Luecke wird LLM-NER aktiviert? (Messung nach 4 Wochen MVP-Betrieb)
- Feature-Flag-Granularitaet: Pro User, pro Source-Type, oder global?

---

## DSGVO-Implikationen

Positive Auswirkung: Ohne LLM-NER verlassen keine Chunk-Inhalte das System fuer Entity-Extraktion. Personenbezogene Daten werden ausschliesslich lokal verarbeitet. Bestehende `owner_id`-Filter und `expires_at`-Kaskaden bleiben unveraendert.

---

## Sicherheitsimplikationen

Kein zusaetzliches Risiko. Regex-Patterns parsen Content lokal und erzeugen keine externen Requests. Extrahierte Entity-Namen durchlaufen `normalized_name`-Normalisierung (lowercase, whitespace collapse). Keine neuen Injection-Vektoren.

---

## Revisionsdatum

2026-07-16 (4 Monate nach MVP-Start: Extraktionsqualitaet anhand realer Nutzerdaten evaluieren, Entscheidung ueber LLM-NER-Aktivierung treffen)
