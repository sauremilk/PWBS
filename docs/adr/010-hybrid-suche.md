# ADR-010: Hybrid-Suche (Vektor + BM25) statt reiner Vektorsuche

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

Das PWBS muss über heterogene Dokumente (Kalendereinträge, Notizen, Transkripte, Briefings) semantisch und keyword-basiert suchen können. Reine Vektorsuche hat Schwächen bei exakten Eigennamen, Projektnamen und Fachbegriffen. Reine Keyword-Suche versteht keine semantischen Zusammenhänge. Die Suche ist ein Kernfeature – Qualität und Relevanz der Ergebnisse bestimmen die Nutzererfahrung maßgeblich.

---

## Entscheidung

Wir verwenden **Hybrid-Suche (Vektor + BM25)** mit Reciprocal Rank Fusion (RRF) für die Ergebnis-Kombination, weil die Kombination beider Ansätze die jeweils Schwächen des anderen kompensiert und Weaviate beide nativ unterstützt.

---

## Optionen bewertet

| Option                                     | Vorteile                                                                                                                                                                  | Nachteile                                                                                                                                           | Ausschlussgründe                                  |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| **Hybrid-Suche (Vektor + BM25)** (gewählt) | Vektorsuche für semantische Ähnlichkeit + BM25 für exakte Matches. Weaviate bietet beides nativ mit konfigurierbarem Alpha (Gewichtung). RRF als bewährte Ranking-Fusion. | Erhöhte Indexing-Kosten (zwei Indizes pro Collection). Komplexere Relevanz-Tuning.                                                                  | –                                                 |
| Pure Vector Search                         | Einfacheres Setup, starke semantische Suche, funktioniert sprachübergreifend.                                                                                             | Versagt bei exakten Eigennamen (z.B. „Projekt Meridian"), Fachbegriffen und Akronymen. Halluziniert Ähnlichkeiten bei kurzen, spezifischen Queries. | Eigennamen- und Fachbegriff-Schwäche inakzeptabel |
| Pure Keyword Search                        | Schnell, deterministisch, exzellent für exakte Matches und Filterung.                                                                                                     | Versteht keine Synonyme, keine semantischen Zusammenhänge. „Besprechung" findet nicht „Meeting". Schlecht für natürliche Sprache.                   | Keine semantische Verständnisfähigkeit            |
| Elasticsearch                              | Ausgereiftes BM25, viele Analyzer, gute Facettierung. Semantische Suche über Plugin möglich.                                                                              | Separater Service mit hohem Ressourcenbedarf. Kein natives Vektor-Embedding (Plugin-Abhängigkeit). Redundant zu Weaviate.                           | Redundant – Weaviate bietet BM25 nativ            |

---

## Konsequenzen

### Positive Konsequenzen

- Beste Suchergebnisse durch Kombination: Semantische Ähnlichkeit (Vektor) + exakte Matches (BM25)
- Konfigurierbarer Alpha-Parameter: Gewichtung zwischen Vektor und BM25 kann pro Use Case angepasst werden (z.B. Alpha=0.7 für semantisch-dominante Suche, Alpha=0.3 für keyword-dominante Suche)
- Kein zusätzlicher Service erforderlich – Weaviate bietet beides nativ
- RRF als Fusion-Algorithmus ist robust und erfordert kein query-spezifisches Training
- PostgreSQL tsvector als zusätzlicher Keyword-Fallback für Szenarien ohne Weaviate

### Negative Konsequenzen / Trade-offs

- Doppelte Indexing-Kosten: Jedes Dokument wird sowohl als Vektor als auch als BM25-Index gespeichert (mitigiert: marginal bei erwarteter MVP-Datenmenge)
- Relevanz-Tuning ist komplexer als bei reiner Vektorsuche (Alpha-Parameter, RRF k-Parameter)
- BM25 erfordert Klartext-Speicherung der Chunk-Inhalte in Weaviate (DSGVO-Trade-off, dokumentiert in ADR-009)

### Offene Fragen

- Optimaler Alpha-Wert für verschiedene Query-Typen (kurze Fragen vs. natürliche Sprache vs. Eigennamen) evaluieren
- Relevanz-Feedback-Schleife für Alpha-Tuning implementieren (Phase 3)
- Graph-Suche (Neo4j Traversal) als vierter Such-Modus integrieren

---

## DSGVO-Implikationen

- **BM25-Index:** Erfordert Klartext-Speicherung der Chunk-Inhalte in Weaviate. Dieser Trade-off ist in ADR-009 dokumentiert und durch Volume Encryption, Netzwerkisolation und Tenant-Separation mitigiert.
- **Mandantenisolation:** Jede Suchanfrage enthält `owner_id` als Filter – keine Cross-User-Ergebnisse möglich. Weaviate Multi-Tenancy garantiert physische Isolation.
- **Audit-Logging:** Jede Suchanfrage wird im Audit-Log protokolliert (`search.executed` Event mit Query-Hash, nicht Klartext-Query).

---

## Sicherheitsimplikationen

- owner_id als Pflicht-Filter in jeder Suchanfrage verhindert Information Disclosure zwischen Nutzern
- Query-Validierung: Maximale Query-Länge, top_k-Limit (max. 50) gegen ressourcenintensive Suchanfragen
- Keine Speicherung von Such-Queries im Klartext in Logs (nur Query-Hash für Audit)
- Rate-Limiting auf Search-Endpoint gegen Brute-Force-Enumeration

---

## Revisionsdatum

2027-03-13 – Bewertung der Suchqualität und Alpha-Tuning-Ergebnisse nach 12 Monaten MVP-Betrieb.
