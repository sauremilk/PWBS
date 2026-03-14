# ADR-001: Python/FastAPI als Backend

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

Das PWBS benötigt ein Backend-Framework, das sowohl klassische REST-API-Endpunkte als auch datenintensive ML/NLP-Pipelines (Embedding-Generierung, NER, LLM-Orchestrierung) effizient unterstützt. Die Wahl des Backend-Stacks beeinflusst die gesamte Entwicklungsgeschwindigkeit, das verfügbare Ökosystem für ML-Bibliotheken und die langfristige Wartbarkeit. Das Team hat primär Python-Expertise im ML/Data-Science-Bereich.

---

## Entscheidung

Wir verwenden **Python 3.12+ mit FastAPI** als Backend-Framework, weil das Python-Ökosystem für ML/NLP-Workloads unübertroffen ist und FastAPI die beste Kombination aus Performance, Typsicherheit und Developer Experience bietet.

---

## Optionen bewertet

| Option                       | Vorteile                                                                                                                                                                                 | Nachteile                                                                                                                              | Ausschlussgründe                                     |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| **Python/FastAPI** (gewählt) | Python-Ökosystem für ML/NLP unübertroffen (Sentence Transformers, LangChain, spaCy). Async-Support, automatische OpenAPI-Docs, native Pydantic-v2-Validierung. Team-Expertise vorhanden. | Höhere Latenz als Go/Rust bei reinen I/O-Operationen. GIL limitiert CPU-bound Parallelismus.                                           | –                                                    |
| Node.js/Express              | Exzellente I/O-Performance, großes npm-Ökosystem, einheitliche Sprache mit Frontend (TypeScript).                                                                                        | ML/NLP-Ökosystem deutlich schwächer. Kein nativer Support für Sentence Transformers, spaCy etc. Python-Bridges (child_process) fragil. | ML-Ökosystem-Lücke zu groß                           |
| Go/Gin                       | Hervorragende Performance und Concurrency. Kleine Binaries, einfaches Deployment.                                                                                                        | Minimales ML/NLP-Ökosystem. Team müsste Go lernen. Kein Pydantic-Äquivalent für automatische Validierung.                              | Fehlende ML-Bibliotheken                             |
| Rust/Actix                   | Beste Performance aller Optionen. Memory Safety ohne GC.                                                                                                                                 | Steile Lernkurve, langsame Compile-Zeiten. ML-Ökosystem noch unreif. Entwicklungsgeschwindigkeit deutlich niedriger.                   | Entwicklungsgeschwindigkeit nicht akzeptabel für MVP |

---

## Konsequenzen

### Positive Konsequenzen

- Direkter Zugriff auf das gesamte Python-ML-Ökosystem (Sentence Transformers, spaCy, LangChain, OpenAI SDK)
- Pydantic v2 als Datenvalidierungsschicht für alle API-Requests und interne Modelle
- Automatische OpenAPI/Swagger-Dokumentation durch FastAPI
- Async-Support für alle I/O-gebundenen Operationen (DB-Queries, LLM-Calls, externe APIs)
- Schnelle Iterationszyklen im MVP dank Python-Flexibilität

### Negative Konsequenzen / Trade-offs

- Höhere Latenz als Go/Rust bei reinen I/O-gebundenen Pfaden (mitigiert durch async und horizontale Skalierung in Phase 4+)
- GIL limitiert CPU-bound Parallelismus bei Embedding-Generierung (mitigiert durch `asyncio.to_thread()` und separate Worker-Prozesse via Celery in Phase 3)
- Typ-Enforcement nur zur Laufzeit (mitigiert durch mypy in CI/CD)

### Offene Fragen

- Evaluation von PyPy oder mypyc für Performance-kritische Pfade in Phase 4

---

## DSGVO-Implikationen

Keine direkten DSGVO-Implikationen durch die Framework-Wahl. FastAPI ermöglicht durch Middleware-Support die Implementierung von Audit-Logging, Rate-Limiting und Verschlüsselungs-Middleware. Pydantic v2 stellt sicher, dass alle eingehenden Daten validiert werden, bevor sie verarbeitet werden.

---

## Sicherheitsimplikationen

- FastAPI bietet eingebauten Schutz gegen viele OWASP-Top-10-Angriffe (automatische Input-Validierung via Pydantic, CORS-Konfiguration, Security-Header-Middleware)
- Dependency-Scanning via `pip-audit` und Dependabot für Python-Pakete erforderlich
- Async-Code erfordert sorgfältige Handhabung von Shared State (keine globalen Variablen für Nutzerdaten)

---

## Revisionsdatum

2027-03-13 – Erneute Bewertung nach 12 Monaten MVP-Betrieb, insbesondere Performance-Metriken unter Last.
