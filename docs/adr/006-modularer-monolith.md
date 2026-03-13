# ADR-006: Modularer Monolith statt Microservices (MVP)

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

Das PWBS wird in Phase 2 (MVP) von einem kleinen Team (2–5 Entwickler) gebaut. Die Architektur muss schnelle Iterationszyklen ermöglichen und gleichzeitig eine spätere Aufteilung in Services unterstützen (Phase 3+). Die Wahl zwischen Monolith und Microservices beeinflusst Entwicklungsgeschwindigkeit, Deployment-Komplexität, Testing-Aufwand und die Fähigkeit, Modul-Grenzen sauber zu enforced.

---

## Entscheidung

Wir verwenden einen **modularen Monolithen** im MVP, bei dem Module über definierte Python-Interfaces kommunizieren (nicht über HTTP). Service-Split erfolgt erst in Phase 3 über Celery + Redis.

---

## Optionen bewertet

| Option | Vorteile | Nachteile | Ausschlussgründe |
|--------|----------|-----------|-------------------|
| **Modularer Monolith** (gewählt) | 2–5 Entwickler können einen Monolithen deutlich schneller iterieren. Kein Overhead durch Service-Mesh, distributed Tracing, API-Contracts. Modul-Grenzen im Code erzwingen Separation of Concerns durch Python-Interfaces. Einfaches Debugging (ein Prozess). | Späterer Service-Split erfordert Refactoring. Alle Module teilen sich einen Prozess – ein Memory Leak betrifft alle. | – |
| Microservices ab Start | Unabhängiges Deployment pro Service, technologische Flexibilität, unabhängige Skalierung. | Massiver Overhead für kleines Team: Service-Mesh, distributed Tracing, API-Contracts, Inter-Service-Auth. Deutlich langsamere Entwicklung im MVP. | Zu hoher Overhead für MVP-Team |
| Serverless Functions | Pay-per-Use, automatische Skalierung, kein Server-Management. | Cold-Start-Latenz problematisch für Echtzeit-Suche. Schwierige lokale Entwicklung. Vendor Lock-in (AWS Lambda). State-Management komplex. | Cold-Start-Latenz und State-Komplexität |

---

## Konsequenzen

### Positive Konsequenzen

- Schnelle Iterationszyklen: Ein Deployment-Artefakt, ein Docker-Container, ein Log-Stream
- Einfaches Debugging: Breakpoints über Modulgrenzen hinweg, kein Netzwerk-Overhead zwischen Modulen
- Python-Interfaces als Modul-Grenzen: `await ingestion_agent.run(context)` statt `httpx.post("/api/internal/process")`
- Transaktionen über Modulgrenzen: Ein DB-Commit kann Änderungen aus Ingestion + Processing atomar persistieren
- Testbarkeit: Unit-Tests mocken Interfaces, keine Service-Stubs oder Container nötig

### Negative Konsequenzen / Trade-offs

- Service-Split in Phase 3 erfordert Refactoring der Modul-Kommunikation (mitigiert: Module kommunizieren über definierte Interfaces, nicht über globalen State – der Übergang zu Message-Queues ist ein Interface-Swap, kein Rewrite)
- Ein fehlerhaftes Modul kann den gesamten Prozess beeinflussen (mitigiert: Error-Isolation via try/except auf Modul-Ebene, Health-Checks)
- Keine unabhängige Skalierung einzelner Module (mitigiert: MVP-Skala erfordert keine unabhängige Skalierung)

### Offene Fragen

- Definieren, welche Module als Erste in Phase 3 zu eigenständigen Services werden (Kandidaten: IngestionAgent, ProcessingAgent)
- Monitoring-Strategie für Modul-Level-Metriken innerhalb des Monolithen

---

## DSGVO-Implikationen

Keine direkten DSGVO-Implikationen durch die Monolith-Entscheidung. Alle DSGVO-Maßnahmen (owner_id-Filter, Verschlüsselung, Löschkaskaden) werden auf Modul-Ebene implementiert, unabhängig von der Deployment-Topologie. Der Monolith vereinfacht sogar die DSGVO-Compliance, da Datenflüsse innerhalb eines Prozesses leichter auditierbar sind als über Service-Grenzen hinweg.

---

## Sicherheitsimplikationen

- Ein Prozess = eine Angriffsfläche (statt N Services mit jeweils eigenen Endpoints)
- Alle Module teilen sich die gleiche Authentifizierungs-Middleware – keine vergessenen Auth-Checks auf internen Endpoints
- Nachteil: Kompromittierung eines Moduls gefährdet alle Module im gleichen Prozess (mitigiert: Module haben keinen direkten DB-Zugriff auf andere Module – nur über Interfaces)
- Secrets-Management ist einfacher (ein .env statt N)

---

## Revisionsdatum

2027-06-13 – Bewertung des Service-Split-Bedarfs nach MVP-Launch. Trigger: Wenn unabhängige Skalierung oder unabhängige Deployment-Zyklen für einzelne Module erforderlich werden.
