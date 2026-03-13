# ADR-011: Celery + Redis statt AWS SQS (Phase 3)

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

Ab Phase 3 benötigt das PWBS eine Aufgabenqueue für asynchrone Verarbeitung: Ingestion-Zyklen, Embedding-Generierung, Briefing-Generierung, Reprocessing-Jobs und DSGVO-Löschkaskaden. Im MVP (Phase 2) erfolgt die Verarbeitung direkt (synchron/async innerhalb des Monolithen). Die Queue-Lösung muss Python-nativ sein, einfach zu betreiben und sich in die bestehende Infrastruktur einfügen.

---

## Entscheidung

Wir verwenden **Celery mit Redis als Message Broker** für die Aufgabenqueue ab Phase 3, weil Celery Python-nativ, gut dokumentiert ist und Redis bereits für Caching und Session-Management genutzt wird.

---

## Optionen bewertet

| Option | Vorteile | Nachteile | Ausschlussgründe |
|--------|----------|-----------|-------------------|
| **Celery + Redis** (gewählt) | Python-nativ, exzellent dokumentiert, großes Ökosystem (Flower für Monitoring, django-celery-beat für Scheduling). Redis wird bereits für Caching genutzt – keine zusätzliche Infrastruktur. Einfache lokale Entwicklung. | Redis als Broker weniger resilient als SQS (Nachrichten bei Redis-Crash verloren). | – |
| AWS SQS + Lambda | Fully managed, keine Betriebskomplexität. SQS garantiert At-Least-Once-Delivery. Serverless Workers skalieren automatisch. | Vendor Lock-in (AWS-spezifisch). Lambda Cold-Starts problematisch für langläufige Processing-Jobs. Schwierigere lokale Entwicklung. | Cold-Starts und Vendor Lock-in |
| RabbitMQ | Robust, AMQP-Standard, garantiert Message-Delivery, flexible Routing-Patterns. | Separater Service mit eigenem Betriebsaufwand. Redundant, wenn Redis bereits läuft. Komplexere Konfiguration als Redis als Broker. | Redundant zu bereits vorhandenem Redis |
| Kafka | Exzellent für Event Streaming, hoher Durchsatz, persistente Messages, Replay-Fähigkeit. | Massiver Betriebsaufwand (ZooKeeper/KRaft, Topic-Management). Overkill für die erwartete Message-Rate im MVP/Phase 3. Steile Lernkurve. | Overkill für erwartete Skala |

---

## Konsequenzen

### Positive Konsequenzen

- Keine zusätzliche Infrastruktur: Redis läuft bereits für Caching und Sessions
- Python-native API: Tasks sind normale Python-Funktionen mit `@celery.task` Decorator
- Flower-Dashboard für Task-Monitoring und -Debugging
- Celery Beat für Cron-basiertes Scheduling (Morning Briefings, Ingestion-Zyklen)
- Einfacher Übergang: Modularer Monolith → Celery-Workers ist ein Interface-Swap (`await agent.run()` → `agent.run.delay()`)

### Negative Konsequenzen / Trade-offs

- Redis als Broker: Bei Redis-Crash gehen unverarbeitete Messages verloren (mitigiert: Redis-Persistenz mit AOF, kritische Jobs werden zusätzlich in PostgreSQL als Fallback geloggt – `scheduled_job_runs` Tabelle)
- Celery-Workers sind Single-Threaded per default – CPU-bound Tasks (Embedding-Generierung) erfordern separate Worker-Pools (mitigiert: Celery unterstützt Prefork-Pool und Gevent-Pool)
- Migration zu SQS in Phase 5 erfordert Broker-Wechsel (mitigiert: Celery unterstützt SQS als Broker nativ)

### Offene Fragen

- Redis-Persistenz-Konfiguration (AOF vs. RDB) für Broker-Reliability definieren
- Worker-Pool-Strategie: Separate Worker für I/O-bound (Ingestion) vs. CPU-bound (Embeddings)?
- Retry-Strategie standardisieren: Max 3 Retries mit Exponential Backoff (1min → 5min → 25min)

---

## DSGVO-Implikationen

- **Daten in Transit in Queue:** Messages in Redis enthalten Referenzen (IDs), nicht Klartext-Nutzerdaten. OAuth-Tokens oder Dokument-Inhalte werden nicht als Task-Parameter übergeben – Worker laden diese aus der DB.
- **Löschkaskaden:** DSGVO-Löschjobs (`cleanup_expired`, Account-Deletion) laufen als Celery-Tasks mit höchster Priorität.
- **Audit-Logging:** Jede Task-Ausführung wird in `scheduled_job_runs` protokolliert (Task-ID, Status, Dauer, Fehler).
- **Datenresidenz:** Redis läuft auf AWS ElastiCache (eu-central-1) mit Encryption at Rest.

---

## Sicherheitsimplikationen

- Redis-Zugang: Nur aus privatem Subnet, Passwort-authentifiziert (AUTH), TLS-verschlüsselt
- Keine Secrets in Task-Parametern – Worker laden Credentials aus der DB oder Environment
- Flower-Dashboard nur über internen Port erreichbar (nicht öffentlich exponiert)
- Rate-Limiting auf Task-Submission für LLM-basierte Tasks (Kostenkontrolle)
- Dead-Letter-Queue-Pattern: Fehlgeschlagene Tasks nach 3 Retries in Fehler-Tabelle persistieren (nicht endlos wiederholen)

---

## Revisionsdatum

2027-09-13 – Bewertung nach Phase-3-Rollout. Evaluation Redis-Reliability vs. SQS-Migration basierend auf tatsächlichen Ausfallraten.
