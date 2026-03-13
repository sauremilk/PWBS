"""Generates sample data for the PWBS Embedding PoC.

Creates >=50 documents across two sources:
- Google Calendar events (JSON)
- Obsidian/Notion markdown notes (Markdown files)
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

CALENDAR_DIR = Path(__file__).parent / "sample_data" / "calendar"
NOTES_DIR = Path(__file__).parent / "sample_data" / "notes"

CALENDAR_EVENTS: list[dict[str, str]] = [
    {
        "summary": "Produkt-Sync mit Team Alpha",
        "description": "Fortschritt der API-Migration besprechen. Thomas hat Bedenken zur Abwaertskompatibilitaet. Lena stellt den neuen Authentifizierungsflow vor.",
        "location": "Konferenzraum A3",
    },
    {
        "summary": "1:1 mit Teamlead Maria",
        "description": "Quartals-Review vorbereiten. Feedback zum neuen Onboarding-Prozess sammeln. OKR-Fortschritt pruefen.",
        "location": "Meeting-Raum B2",
    },
    {
        "summary": "Sprint Retrospektive Q1",
        "description": "Was lief gut: Deployment-Automatisierung. Was kann besser: Code-Reviews dauern zu lange. Action Items aus letztem Retro pruefen.",
        "location": "Grosser Meetingraum",
    },
    {
        "summary": "Architektur-Review: Microservices",
        "description": "Entscheidung ob monolithische Architektur beibehalten oder auf Microservices migriert wird. Kosten-Nutzen-Analyse vorbereiten.",
        "location": "Online (Zoom)",
    },
    {
        "summary": "Kunden-Demo fuer Projekt Phoenix",
        "description": "Neues Dashboard-Feature vorstellen. Live-Demo der Echtzeit-Datenvisualisierung. Feedback-Runde mit Product Owner.",
        "location": "Kundenzentrum",
    },
    {
        "summary": "DevOps-Workshop: Kubernetes Basics",
        "description": "Einfuehrung in Container-Orchestrierung. Hands-on mit kubectl. Deployment-Strategien (Rolling, Blue-Green).",
        "location": "Schulungsraum 1",
    },
    {
        "summary": "Budget-Planung 2026 H2",
        "description": "Cloud-Kosten optimieren. Neue Tooling-Investitionen: Monitoring, Testing. Headcount-Planung fuer Q3.",
        "location": "Finanzsaal",
    },
    {
        "summary": "Onboarding: Neue Entwicklerin Sarah",
        "description": "Entwicklungsumgebung einrichten. Git-Workflow und Branch-Konventionen erklaeren. Pair-Programming-Session mit dem Backend-Team.",
        "location": "Open Space",
    },
    {
        "summary": "Security Audit Vorbereitung",
        "description": "OWASP Top 10 Checkliste durchgehen. Penetration-Test-Ergebnisse besprechen. DSGVO-Compliance-Status pruefen.",
        "location": "Sicherheitslabor",
    },
    {
        "summary": "Innovations-Tag: KI-Prototypen",
        "description": "Drei Teams stellen KI-Prototypen vor. Bewertungskriterien: Nutzen, Machbarkeit, Datenschutz. Abstimmung ueber Weiterentwicklung.",
        "location": "Innovationshub",
    },
    {
        "summary": "Standup Team Backend",
        "description": "Taeglicher Standup. Aktuelle Blocker: Datenbankmigrationen, API-Versionierung.",
        "location": "Online (Teams)",
    },
    {
        "summary": "Performance-Review Meeting",
        "description": "Zielvereinbarungen pruefen. Neue Ziele fuer H2 definieren. Weiterbildungsplan besprechen.",
        "location": "HR-Raum",
    },
    {
        "summary": "Tech Talk: Event-Driven Architecture",
        "description": "Einfuehrung in Event Sourcing und CQRS. Praxisbericht vom Payments-Team. Diskussion ueber Einsatz im PWBS.",
        "location": "Grosser Meetingraum",
    },
    {
        "summary": "Release Planning Sprint 14",
        "description": "Backlog-Priorisierung. Kapazitaetsplanung. Feature-Flags fuer experimentelle Features definieren.",
        "location": "Scrum-Raum",
    },
    {
        "summary": "Datenbank-Workshop: PostgreSQL Tuning",
        "description": "Query-Optimierung mit EXPLAIN ANALYZE. Index-Strategien. Connection Pooling mit PgBouncer.",
        "location": "Schulungsraum 2",
    },
    {
        "summary": "Wochenplanung Marketing-Sync",
        "description": "Content-Kalender abstimmen. Launch-Kampagne fuer neues Feature koordinieren. Analytics-Dashboard-Updates.",
        "location": "Marketing-Raum",
    },
    {
        "summary": "Code Review Session",
        "description": "Pull Requests der Woche gemeinsam reviewen. Fokus auf Test-Coverage und Clean Code Prinzipien.",
        "location": "Online (Zoom)",
    },
    {
        "summary": "Quartals-All-Hands",
        "description": "CEO-Update. Produkt-Roadmap-Vorstellung. Q&A-Runde. Neue Bueroregelung ab April.",
        "location": "Auditorium",
    },
    {
        "summary": "Infrastruktur-Migration AWS",
        "description": "Status der Migration von On-Premise zu AWS. Verbleibende Services identifizieren. Kostenvergleich aktualisieren.",
        "location": "Ops-Raum",
    },
    {
        "summary": "Accessibility Audit",
        "description": "WCAG 2.1 Compliance pruefen. Screen-Reader-Tests. Farbkontrast-Analyse. Action Items priorisieren.",
        "location": "UX-Lab",
    },
    {
        "summary": "Pair Programming: Auth-Modul",
        "description": "OAuth2-Flow implementieren. Token-Rotation testen. Refresh-Token-Verschluesselung integrieren.",
        "location": "Dev Area",
    },
    {
        "summary": "Product Discovery Workshop",
        "description": "Nutzerbeduerfnisse fuer Knowledge-Graph-Feature validieren. Jobs-to-be-Done Framework anwenden.",
        "location": "Design Studio",
    },
    {
        "summary": "Monitoring & Alerting Setup",
        "description": "Prometheus und Grafana konfigurieren. SLOs definieren. PagerDuty-Integration einrichten.",
        "location": "Online (Teams)",
    },
    {
        "summary": "Dokumentations-Sprint",
        "description": "API-Dokumentation aktualisieren. Onboarding-Guide ueberarbeiten. ADRs nachpflegen.",
        "location": "Bibliothek",
    },
    {
        "summary": "Stakeholder Update Projekt Orion",
        "description": "Meilensteinbericht praesentieren. Risiko-Register aktualisieren. Naechste Schritte abstimmen.",
        "location": "Executive Boardroom",
    },
    {
        "summary": "Lunch & Learn: GraphQL vs REST",
        "description": "Technischer Vergleich. Migration-Erfahrungsbericht. Entscheidungshilfe fuer neue API-Endpunkte.",
        "location": "Kantine",
    },
    {
        "summary": "Incident Postmortem: API-Ausfall",
        "description": "Root Cause: Connection Pool Exhaustion. Timeline rekonstruieren. Massnahmen: Circuit Breaker, bessere Alerts.",
        "location": "War Room",
    },
    {
        "summary": "Design System Review",
        "description": "Neue Komponenten pruefen. Token-System vereinheitlichen. Dark-Mode-Unterstuetzung besprechen.",
        "location": "Design Studio",
    },
    {
        "summary": "Cross-Team Dependency Mapping",
        "description": "Abhaengigkeiten zwischen Frontend, Backend, Data-Team visualisieren. Engpaesse identifizieren.",
        "location": "Grosser Meetingraum",
    },
    {
        "summary": "Datenqualitaets-Review",
        "description": "Embedding-Qualitaet pruefen. Duplikaterkennung testen. Normalisierungspipeline optimieren.",
        "location": "Data Lab",
    },
]

NOTES: list[dict[str, str]] = [
    {
        "title": "Meeting Notes - API Migration",
        "content": "# API Migration Diskussion\n\n## Teilnehmer\n- Thomas K., Lena W., Maria S.\n\n## Kernpunkte\n- Migration von REST v1 auf v2 geplant fuer Q2\n- Abwaertskompatibilitaet muss 6 Monate gewährleistet sein\n- Deprecation-Header ab sofort in allen v1-Responses\n- Automatisierte Migrationstests werden aufgesetzt\n\n## Action Items\n- [ ] Thomas: Kompatibilitaetsmatrix erstellen\n- [ ] Lena: Neue Auth-Middleware testen\n- [ ] Maria: Stakeholder informieren",
    },
    {
        "title": "Architekturentscheidung - Datenbank",
        "content": "# ADR: PostgreSQL als primaere Datenbank\n\n## Kontext\nWir brauchen eine relationale Datenbank fuer das PWBS. Kandidaten: PostgreSQL, MySQL, CockroachDB.\n\n## Entscheidung\nPostgreSQL gewaehlt wegen: tsvector fuer Volltextsuche, JSONB fuer flexible Metadaten, starke Community.\n\n## Konsequenzen\n- Migration von SQLite (PoC) notwendig\n- Alembic fuer Schema-Migrationen einrichten\n- Connection Pooling von Anfang an",
    },
    {
        "title": "DSGVO Anforderungen",
        "content": "# DSGVO Anforderungen PWBS\n\n## Relevante Artikel\n- Art. 5: Datenminimierung\n- Art. 6: Rechtsgrundlage (Einwilligung/Vertrag)\n- Art. 17: Recht auf Loeschung\n- Art. 20: Datenportabilitaet\n- Art. 25: Privacy by Design\n\n## Massnahmen\n1. Jedes Datum bekommt owner_id und expires_at\n2. Verschluesselung at rest (AES-256)\n3. Audit-Log fuer Datenzugriffe\n4. Export-API fuer Nutzer-Daten\n5. Automatische Loeschung nach Ablauf",
    },
    {
        "title": "Sprint Retro Notizen",
        "content": "# Sprint 13 Retrospektive\n\n## Was lief gut\n- Deployment Pipeline laeuft stabil seit 3 Wochen\n- Code Coverage von 62% auf 78% gestiegen\n- Neue Team-Mitglieder gut eingearbeitet\n\n## Was kann besser\n- Code Reviews dauern durchschnittlich 3 Tage\n- Ticket-Beschreibungen oft ungenuegend\n- Zu viele Meetings am Mittwoch\n\n## Action Items\n- Review-SLA: max 24h\n- Template fuer Ticket-Beschreibungen\n- Meeting-freier Donnerstag",
    },
    {
        "title": "Knowledge Graph Design",
        "content": "# Knowledge Graph Schema\n\n## Node-Typen\n- Person: Name, Rolle, Abteilung\n- Project: Name, Status, Deadline\n- Decision: Beschreibung, Datum, Beteiligte\n- Document: Titel, Typ, Erstelldatum\n- Topic: Name, Beschreibung\n\n## Relationen\n- MENTIONED_IN: Person -> Document\n- DECIDED_IN: Decision -> Meeting\n- WORKS_ON: Person -> Project\n- RELATED_TO: Topic -> Topic\n\n## Neo4j Queries\nMERGE statt CREATE fuer Idempotenz",
    },
    {
        "title": "Embedding Strategie",
        "content": "# Embedding-Strategie fuer PWBS\n\n## Modell-Auswahl\n- text-embedding-3-small (OpenAI): 1536 Dim, guenstiger\n- text-embedding-3-large (OpenAI): 3072 Dim, besser fuer lange Texte\n- Sentence Transformers (lokal): Kein API-Kosten, aber schwaecher\n\n## Entscheidung Phase1\ntext-embedding-3-small fuer PoC.\n\n## Chunking\n- Paragraph-basiert fuer PoC\n- Semantisches Splitting im MVP (128-512 Tokens, 32 Overlap)\n\n## Batch-Verarbeitung\nBatch-Groesse 64 fuer API-Calls",
    },
    {
        "title": "Weaviate Setup Notizen",
        "content": "# Weaviate Setup\n\n## Docker\n```bash\ndocker run -d -p 8080:8080 cr.weaviate.io/semitechnologies/weaviate:1.28.2\n```\n\n## Schema\n- Collection: UnifiedDocument\n- Properties: title, content, source_type, metadata\n- Vectorizer: none (externe Embeddings)\n\n## Wichtig\n- Upsert via source_id (Idempotenz)\n- Tenant-Isolation ueber owner_id Filter\n- Backup: weaviate backup API + S3",
    },
    {
        "title": "Projektplan PWBS Phase 2",
        "content": "# PWBS Phase 2 - MVP\n\n## Timeline\n- Maerz 2026: Foundation (PoC, DSGVO, ADRs)\n- April-Mai: Core Infrastructure\n- Juni-Juli: MVP Features\n- August: Testing & Launch\n\n## Module\n1. Ingestion Pipeline (Konnektoren)\n2. Processing (Chunking, Embedding, NER)\n3. Search (Hybrid: Semantic + Keyword)\n4. Briefing Engine\n5. Auth & API\n6. Frontend\n\n## Risiken\n- LLM-API-Kosten schwer kalkulierbar\n- DSGVO-Compliance komplex\n- Knowledge Graph Qualitaet",
    },
    {
        "title": "Obsidian Workflow",
        "content": "# Mein Obsidian Workflow\n\n## Tagesnotizen\nJeder Tag bekommt eine Notiz: YYYY-MM-DD.md\nInhalt: Todos, Meeting-Notizen, Gedanken\n\n## Verlinkung\n- [[Projekte]] fuer Projekt-Uebersichten\n- [[Personen]] fuer Kontakt-Kontexte\n- Tags: #meeting #entscheidung #idee #todo\n\n## Templates\n- Meeting-Template mit Agenda, Teilnehmer, Action Items\n- Weekly Review mit Highlights, Learnings, Next Week\n\n## Sync\nObsidian Vault liegt in iCloud. PWBS soll diesen Ordner lesen.",
    },
    {
        "title": "OAuth2 Flow Notizen",
        "content": "# OAuth2 Implementation\n\n## Google Calendar\n1. User klickt 'Verbinden'\n2. Redirect zu Google Consent Screen\n3. Callback mit Authorization Code\n4. Backend tauscht Code gegen Access+Refresh Token\n5. Tokens verschluesselt in DB speichern\n\n## Token Rotation\n- Access Token: 1h Lebensdauer\n- Refresh Token: 30 Tage\n- Automatische Rotation bei Ablauf\n- Fallback: User muss neu autorisieren\n\n## Sicherheit\n- Tokens mit AES-256-GCM verschluesseln\n- Kein Token im Frontend speichern",
    },
    {
        "title": "Performance Benchmarks",
        "content": "# Embedding Performance\n\n## text-embedding-3-small\n- Single Request: ~200ms\n- Batch (64 Docs): ~2.1s\n- Kosten: $0.02 / 1M Tokens\n\n## Weaviate Insert\n- Single Object: ~5ms\n- Batch (100 Objects): ~50ms\n- Query (Nearest Neighbor, k=10): ~15ms\n\n## Zielwerte MVP\n- Ingestion: 1000 Docs/min\n- Search P95 Latency: <500ms\n- Briefing Generation: <10s\n\n## Optimierungen\n- Embedding Batch Size: 64\n- Weaviate Batch Insert: 100\n- Connection Pooling: 20 Connections",
    },
    {
        "title": "Celery Task Queue Design",
        "content": "# Celery Integration (Phase 3)\n\n## Warum Celery\n- Asynchrone Verarbeitung langer Tasks\n- Retry-Mechanismus eingebaut\n- Scheduling (celery-beat)\n- Result Backend (Redis)\n\n## Task-Typen\n1. ingestion.fetch_source: Daten von Konnektor abrufen\n2. processing.generate_embeddings: Batch-Embedding\n3. processing.extract_entities: NER-Pipeline\n4. briefing.generate: Briefing erstellen\n\n## Konfiguration\n- Broker: Redis\n- Concurrency: 4 Worker\n- Max Retries: 3\n- Exponential Backoff",
    },
    {
        "title": "Frontend Architektur",
        "content": "# Frontend Architektur\n\n## Tech Stack\n- Next.js 14+ (App Router)\n- React 18+\n- TypeScript (strict mode)\n- Tailwind CSS\n\n## Seitenstruktur\n- /dashboard: Tagesuebersicht + Briefing\n- /search: Semantische Suche\n- /connections: Datenquellen verwalten\n- /settings: Profil, DSGVO, API-Keys\n\n## API-Client\nAlle Calls ueber src/lib/api/\nKein direktes fetch() in Komponenten\n\n## State Management\nServer Components first. Client State minimal (Zustand fuer UI-State).",
    },
    {
        "title": "NER Pipeline Design",
        "content": "# Named Entity Recognition\n\n## Entitaetstypen\n- PERSON: Mitarbeiter, Kunden, Partner\n- PROJECT: Projektnamen\n- DECISION: Entscheidungen mit Datum\n- ORGANIZATION: Firmen, Teams\n- DATE: Zeitangaben\n- TOPIC: Fachbegriffe, Technologien\n\n## Pipeline\n1. spaCy fuer Basis-NER (de_core_news_lg)\n2. Custom Rules fuer Projekt- und Entscheidungserkennung\n3. LLM-basierte Extraktion fuer komplexe Zusammenhaenge\n\n## Graph-Integration\nExtrahierte Entities werden als Neo4j-Nodes gespeichert\nRelationen aus Kookurrenz im selben Dokument",
    },
    {
        "title": "Monitoring Konzept",
        "content": "# Monitoring & Observability\n\n## Metriken\n- API: Request Rate, Latency P50/P95/P99, Error Rate\n- Ingestion: Documents/min, Failure Rate\n- LLM: Tokens/Request, Kosten/Tag, Latency\n- Search: Query Time, Result Quality (Click-Through)\n\n## Tools\n- Prometheus: Metrik-Sammlung\n- Grafana: Dashboards\n- Sentry: Error Tracking\n- Structured Logging: JSON-Format\n\n## Alerts\n- Error Rate > 5%: Warning\n- Error Rate > 15%: Critical\n- API Latency P95 > 2s: Warning\n- LLM Cost > Budget: Critical",
    },
    {
        "title": "Briefing Engine Design",
        "content": "# Briefing Engine\n\n## Briefing-Typen\n1. Morning Briefing: Taeglich 6:30, max 800 Woerter\n2. Meeting Briefing: 30min vor Termin, max 400 Woerter\n3. Project Briefing: On-Demand, max 1200 Woerter\n4. Weekly Briefing: Freitags 17:00, max 600 Woerter\n\n## Prozess\n1. Relevante Dokumente via SearchAgent abrufen\n2. Kontext aus Knowledge Graph holen\n3. LLM-Call mit strukturiertem Prompt\n4. Quellenreferenzen validieren\n5. Briefing speichern und ausliefern\n\n## Regeln\n- Nie ohne Quellen ausliefern\n- Temperatur: 0.3\n- Nur RAG-Wissen, kein LLM-Vorwissen",
    },
    {
        "title": "Testing Strategie",
        "content": "# Testing Strategie PWBS\n\n## Unit Tests\n- pytest + pytest-asyncio\n- Fixtures fuer DB, Weaviate, Neo4j (Mocks)\n- Kein Netzwerkzugriff\n- Coverage-Ziel: 80%\n\n## Integration Tests\n- Echte DB-Container via Docker\n- Prueft Zusammenspiel der Module\n- Separater CI-Job\n\n## E2E Tests\n- Playwright fuer Frontend\n- Full-Stack mit Docker Compose\n- Kritische User-Flows abdecken\n\n## Prinzipien\n- Happy Path + Fehlerfall testen\n- Idempotenz explizit testen\n- Keine flaky Tests tolerieren",
    },
    {
        "title": "Verschluesselungsstrategie",
        "content": "# Verschluesselung im PWBS\n\n## At Rest\n- PostgreSQL: TDE oder Spalten-Verschluesselung (AES-256)\n- Weaviate: Disk-Encryption auf Infrastrukturebene\n- Neo4j: Encryption at Rest\n- Tokens: AES-256-GCM pro Nutzer\n\n## In Transit\n- TLS 1.3 fuer alle API-Aufrufe\n- mTLS zwischen internen Services (Phase 3)\n\n## Key Management\n- AWS KMS fuer Master-Keys\n- Nutzer-spezifische DEKs (Data Encryption Keys)\n- Key Rotation alle 90 Tage\n\n## Backup\n- Backups verschluesselt mit separatem Key\n- Key-Escrow-Prozess dokumentiert",
    },
    {
        "title": "Datenquellen Roadmap",
        "content": "# Datenquellen Roadmap\n\n## Phase 2 (MVP)\n1. Google Calendar\n2. Notion\n3. Obsidian (lokaler Vault)\n4. Zoom Transcripts\n\n## Phase 3\n5. Gmail\n6. Slack\n7. Google Docs\n\n## Phase 4\n8. Microsoft Outlook\n9. Microsoft Teams\n10. Confluence\n11. Jira\n\n## Phase 5\n12. Custom REST APIs\n13. RSS Feeds\n14. Browser Extension (Bookmarks, Highlights)\n\n## Konnektor-Prinzipien\n- Cursor-basierte Pagination\n- OAuth2 wo moeglich\n- Idempotente Ingestion\n- Rate-Limiting respektieren",
    },
    {
        "title": "Wochenreview KW10",
        "content": "# Weekly Review - KW10 2026\n\n## Highlights\n- PWBS PoC-Konzept finalisiert\n- Architektur-Dokument v1 fertig\n- Team-Agreement fuer Clean Code\n\n## Learnings\n- Weaviate Batch Import 10x schneller als Einzel-Inserts\n- text-embedding-3-small reicht fuer unseren Use Case\n- Neo4j MERGE ist essentiell fuer Idempotenz\n\n## Naechste Woche\n- TASK-001 starten (Embedding PoC)\n- DSGVO-Beratung Termin am Dienstag\n- Infrastruktur-Entscheidung Docker Compose vs K8s",
    },
    {
        "title": "API Versionierung",
        "content": "# API Versionierung\n\n## Strategie\n- URL-basiert: /api/v1/, /api/v2/\n- Header-basiert als Alternative: Accept-Version\n\n## Regeln\n- Breaking Changes nur in neuer Major-Version\n- Deprecation-Warning 6 Monate vor Abschaltung\n- Automatisierte Kompatibilitaetstests\n\n## Aktuelle Versionen\n- v1: MVP (Phase 2)\n- v2: Geplant fuer Phase 4\n\n## Dokumentation\n- OpenAPI/Swagger automatisch generiert\n- Changelog pro Version pflegen",
    },
]


def generate_calendar_events() -> int:
    """Generate sample calendar events as JSON files."""
    os.makedirs(CALENDAR_DIR, exist_ok=True)
    base_date = datetime(2026, 3, 1, 9, 0)
    count = 0

    for i, event in enumerate(CALENDAR_EVENTS):
        event_date = base_date + timedelta(days=i, hours=(i % 8))
        event_data = {
            "id": f"cal_evt_{i + 1:03d}",
            "summary": event["summary"],
            "description": event["description"],
            "location": event["location"],
            "start": {"dateTime": event_date.isoformat() + "+01:00"},
            "end": {
                "dateTime": (event_date + timedelta(hours=1)).isoformat() + "+01:00"
            },
            "attendees": [
                {"email": f"person{j}@example.com"} for j in range(1, (i % 4) + 2)
            ],
            "source": "google_calendar",
            "created": (event_date - timedelta(days=7)).isoformat() + "Z",
        }

        filepath = CALENDAR_DIR / f"event_{i + 1:03d}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(event_data, f, indent=2, ensure_ascii=False)
        count += 1

    return count


def generate_notes() -> int:
    """Generate sample Obsidian/Notion markdown notes."""
    os.makedirs(NOTES_DIR, exist_ok=True)
    base_date = datetime(2026, 2, 15)
    count = 0

    for i, note in enumerate(NOTES):
        note_date = base_date + timedelta(days=i)
        filename = (
            note["title"].replace(" ", "-").replace(":", "").replace("/", "-").lower()
        )
        filepath = NOTES_DIR / f"{filename}.md"

        header = (
            f"---\n"
            f'title: "{note["title"]}"\n'
            f"created: {note_date.strftime('%Y-%m-%d')}\n"
            f"source: obsidian\n"
            f"tags: [pwbs, knowledge-management]\n"
            f"---\n\n"
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header + note["content"])
        count += 1

    return count


def main() -> None:
    cal_count = generate_calendar_events()
    notes_count = generate_notes()
    total = cal_count + notes_count
    print(f"Generated {cal_count} calendar events in {CALENDAR_DIR}")
    print(f"Generated {notes_count} notes in {NOTES_DIR}")
    print(f"Total: {total} documents (requirement: >=50)")

    if total < 50:
        raise SystemExit(f"ERROR: Only {total} documents generated, need >=50")


if __name__ == "__main__":
    main()
