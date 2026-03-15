"""Seed-Data-Generator for demo and test environments (TASK-198).

Generates a demo user with realistic documents across all 4 MVP connectors
(Google Calendar, Notion, Zoom, Obsidian). Uses fixed UUIDs for idempotency.

Usage:
    python -m pwbs.cli seed [--user demo@pwbs.dev] [--documents 50] [--clean]
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fixed UUIDs for idempotent seeding
# ---------------------------------------------------------------------------

DEMO_USER_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")
DEMO_USER_PASSWORD = "DemoPassword123!"  # noqa: S105 -- dev-only seed data

# Deterministic document IDs: UUID5 namespace for reproducibility
_NS = uuid.UUID("c0ffee00-cafe-4000-b000-000000000000")


def _doc_id(source_type: str, index: int) -> uuid.UUID:
    """Generate a deterministic document UUID from source type and index."""
    return uuid.uuid5(_NS, f"{source_type}:{index}")


# ---------------------------------------------------------------------------
# Document templates (derived from poc/generate_sample_data.py)
# ---------------------------------------------------------------------------

_CALENDAR_EVENTS: list[dict[str, Any]] = [
    {
        "title": "Produkt-Sync mit Team Alpha",
        "content": "Fortschritt der API-Migration besprechen. Thomas hat Bedenken zur Abwaertskompatibilitaet. Lena stellt den neuen Authentifizierungsflow vor.",
        "participants": ["Thomas Mueller", "Lena Schmidt", "Max Bauer"],
        "location": "Konferenzraum A3",
    },
    {
        "title": "1:1 mit Teamlead Maria",
        "content": "Quartals-Review vorbereiten. Feedback zum neuen Onboarding-Prozess sammeln. OKR-Fortschritt pruefen.",
        "participants": ["Maria Weber"],
        "location": "Meeting-Raum B2",
    },
    {
        "title": "Sprint Retrospektive Q1",
        "content": "Was lief gut: Deployment-Automatisierung. Was kann besser: Code-Reviews dauern zu lange. Action Items aus letztem Retro pruefen.",
        "participants": ["Team Backend", "Scrum Master Jan"],
        "location": "Grosser Meetingraum",
    },
    {
        "title": "Architektur-Review: Microservices",
        "content": "Entscheidung ob monolithische Architektur beibehalten oder auf Microservices migriert wird. Kosten-Nutzen-Analyse vorbereiten.",
        "participants": ["CTO Anna", "Lead Dev Max", "DevOps Lars"],
        "location": "Online (Zoom)",
    },
    {
        "title": "Kunden-Demo fuer Projekt Phoenix",
        "content": "Neues Dashboard-Feature vorstellen. Live-Demo der Echtzeit-Datenvisualisierung. Feedback-Runde mit Product Owner.",
        "participants": ["PO Sarah", "Kunde: Dr. Hoffmann"],
        "location": "Kundenzentrum",
    },
    {
        "title": "Budget-Planung 2026 H2",
        "content": "Cloud-Kosten optimieren. Neue Tooling-Investitionen: Monitoring, Testing. Headcount-Planung fuer Q3.",
        "participants": ["CFO Peter", "CTO Anna", "HR Lisa"],
        "location": "Finanzsaal",
    },
    {
        "title": "Security Audit Vorbereitung",
        "content": "OWASP Top 10 Checkliste durchgehen. Penetration-Test-Ergebnisse besprechen. DSGVO-Compliance-Status pruefen.",
        "participants": ["Security Lead Jonas", "DPO Martina"],
        "location": "Sicherheitslabor",
    },
    {
        "title": "Standup Team Backend",
        "content": "Taeglicher Standup. Aktuelle Blocker: Datenbankmigrationen, API-Versionierung.",
        "participants": ["Team Backend"],
        "location": "Online (Teams)",
    },
    {
        "title": "Tech Talk: Event-Driven Architecture",
        "content": "Einfuehrung in Event Sourcing und CQRS. Praxisbericht vom Payments-Team. Diskussion ueber Einsatz im PWBS.",
        "participants": ["Speaker: Dr. Klein", "Engineering Team"],
        "location": "Grosser Meetingraum",
    },
    {
        "title": "Onboarding: Neue Entwicklerin Sarah",
        "content": "Entwicklungsumgebung einrichten. Git-Workflow und Branch-Konventionen erklaeren. Pair-Programming-Session.",
        "participants": ["Sarah Neumann", "Mentor Max"],
        "location": "Open Space",
    },
    {
        "title": "Performance-Review Meeting",
        "content": "Zielvereinbarungen pruefen. Neue Ziele fuer H2 definieren. Weiterbildungsplan besprechen.",
        "participants": ["HR Lisa", "Manager Maria"],
        "location": "HR-Raum",
    },
    {
        "title": "Innovations-Tag: KI-Prototypen",
        "content": "Drei Teams stellen KI-Prototypen vor: Chatbot, Dokumentenklassifikation, Meeting-Zusammenfassung. Abstimmung ueber Weiterentwicklung.",
        "participants": ["Engineering Team", "Product Team"],
        "location": "Innovationshub",
    },
]

_NOTION_PAGES: list[dict[str, Any]] = [
    {
        "title": "Projektplan Q2 2026",
        "content": "# Projektplan Q2 2026\n\n## Ziele\n- API v2 fertigstellen\n- Monitoring-Dashboard deployen\n- Onboarding-Rate auf 80% steigern\n\n## Meilensteine\n- KW14: API Beta\n- KW18: Dashboard GA\n- KW22: Onboarding v2\n\n## Risiken\n- Abhaengigkeit vom externen Payment-Provider\n- Teamkapazitaet durch Urlaube eingeschraenkt",
    },
    {
        "title": "Meeting-Protokoll: Architektur-Entscheidung",
        "content": "# Architektur-Entscheidung: Modularer Monolith\n\nTeilnehmer: Anna, Max, Lars\nDatum: 2026-02-15\n\n## Entscheidung\nWir bleiben beim modularen Monolith bis Phase 3. Microservices erst bei >10k Nutzern.\n\n## Begruendung\n- Deployment-Komplexitaet bleibt niedrig\n- Team-Groesse (5 Devs) rechtfertigt keinen Service-Split\n- Feature-Velocity ist aktuell hoeher als bei verteiltem System",
    },
    {
        "title": "DSGVO-Checkliste",
        "content": "# DSGVO-Compliance Checkliste\n\n- [x] owner_id in allen Tabellen\n- [x] expires_at fuer automatische Loeschung\n- [x] Datenexport-Endpunkt\n- [x] Konto-Loeschung mit Karenzfrist\n- [ ] AVV mit LLM-Providern abschliessen\n- [ ] Datenschutzerklaerung uebersetzen",
    },
    {
        "title": "API-Design-Richtlinien",
        "content": "# API-Design-Richtlinien\n\n## Versionierung\n- URL-Prefix: /api/v1/\n- Breaking Changes erfordern neue Major-Version\n\n## Authentifizierung\n- JWT Bearer Tokens\n- Access Token: 15 Min\n- Refresh Token: 7 Tage\n\n## Fehlerformat\n```json\n{\"code\": \"ERROR_CODE\", \"message\": \"Beschreibung\"}\n```",
    },
    {
        "title": "Sprint-Retro KW10",
        "content": "# Sprint Retro KW10\n\n## Was lief gut\n- CI/CD Pipeline stabil\n- Code-Review-Turnaround unter 4h\n\n## Was kann besser\n- Test-Abdeckung in Frontend niedrig (42%)\n- Zu viele parallele Branches\n\n## Action Items\n- Frontend-Test-Sprint in KW12\n- Branch-Limit auf 3 pro Entwickler",
    },
    {
        "title": "Wissensmanagement-Konzept",
        "content": "# Wissensmanagement im Team\n\n## Problem\nWissen ist in Koepfen, Slack-Threads und lokalen Notizen verstreut.\n\n## Loesung: PWBS\n- Alle Quellen in einem System zusammenfuehren\n- Semantische Suche statt Keyword-Suche\n- Automatische Briefings vor jedem Meeting\n\n## Erwartetes Ergebnis\n- 30% weniger Meetings durch bessere Vorbereitung\n- Onboarding neuer Mitarbeiter in 3 statt 10 Tagen",
    },
    {
        "title": "Datenquellen Roadmap",
        "content": "# Datenquellen Roadmap\n\n## Phase 2 (MVP)\n1. Google Calendar\n2. Notion\n3. Obsidian (lokaler Vault)\n4. Zoom Transcripts\n\n## Phase 3\n5. Gmail\n6. Slack\n7. Google Docs\n\n## Konnektor-Prinzipien\n- Cursor-basierte Pagination\n- OAuth2 wo moeglich\n- Idempotente Ingestion\n- Rate-Limiting respektieren",
    },
    {
        "title": "Team-OKRs Q2",
        "content": "# Team-OKRs Q2 2026\n\n## Objective 1: MVP-Launch\n- KR1: 20 Early Adopter angemeldet (aktuell: 8)\n- KR2: Time-to-First-Briefing < 5 Min\n- KR3: Null kritische Bugs in Produktion\n\n## Objective 2: Datenqualitaet\n- KR1: Embedding-Recall > 85%\n- KR2: NER-Precision > 90%\n- KR3: Deduplizierungs-Rate 100%",
    },
]

_ZOOM_TRANSCRIPTS: list[dict[str, Any]] = [
    {
        "title": "Sprint Planning KW11  Transkript",
        "content": "Max: Okay, fangen wir an. Was sind die Top-3 Items fuer diesen Sprint?\nLena: Ich schlage vor, wir priorisieren den Konnektor-Resilience-Task. Letzte Woche hatten wir drei Sync-Fehler.\nThomas: Stimme zu. Ausserdem sollten wir die OpenAPI-Doku fertigstellen.\nMax: Gut. Drittes Item?\nLena: Die Seed-Data fuer Demo-Umgebungen. Ohne realistische Testdaten koennen wir nicht vernuenftig testen.\nMax: Einverstanden. Thomas, uebernimmst du die Doku?\nThomas: Ja, mache ich.",
        "participants": ["Max Bauer", "Lena Schmidt", "Thomas Mueller"],
        "duration_minutes": 45,
    },
    {
        "title": "Architektur-Review: Embedding-Pipeline  Transkript",
        "content": "Anna: Die aktuelle Embedding-Pipeline hat eine Latenz von 200ms pro Dokument. Ist das akzeptabel?\nLars: Fuer den MVP ja, aber wir sollten Batch-Processing einbauen. 64er-Batches wuerden den Durchsatz vervierfachen.\nAnna: Welches Modell nutzen wir?\nLars: all-MiniLM-L6-v2 lokal, mit Fallback auf OpenAI Ada. Die lokale Variante ist 3x guenstiger.\nAnna: Entscheidung: Wir bleiben beim lokalen Modell. Fallback nur bei Ausfall.",
        "participants": ["CTO Anna", "DevOps Lars"],
        "duration_minutes": 30,
    },
    {
        "title": "Kunden-Feedback-Session: Dr. Hoffmann  Transkript",
        "content": "Dr. Hoffmann: Die Suche funktioniert gut, aber ich vermisse eine Filterfunktion nach Datum.\nSarah: Das ist geplant fuer die naechste Version. Aktuell koennen Sie ueber die Suchsyntax filtern.\nDr. Hoffmann: Die Briefings sind sehr nuetzlich. Koennte man die auch per E-Mail bekommen?\nSarah: Gute Idee, wir nehmen das in den Backlog auf.\nDr. Hoffmann: Insgesamt bin ich beeindruckt. Die Vorbereitung auf Meetings ist viel effizienter geworden.",
        "participants": ["Kunde: Dr. Hoffmann", "PO Sarah"],
        "duration_minutes": 25,
    },
    {
        "title": "DSGVO-Review mit DPO  Transkript",
        "content": "Martina: Ich habe die neue Datenexport-Funktion getestet. Der Export enthaelt alle relevanten Daten und ist DSGVO-konform.\nMax: Wie sieht es mit der Loeschung aus?\nMartina: Die Karenzfrist von 72 Stunden ist korrekt implementiert. Nach Ablauf werden alle Daten kaskadiert geloescht.\nMax: Und die LLM-Verarbeitung?\nMartina: Wir brauchen noch die AVV mit Anthropic. Aktuell ist die Datenverarbeitung durch die Einwilligung gedeckt, aber die vertragliche Grundlage fehlt.",
        "participants": ["DPO Martina", "Max Bauer"],
        "duration_minutes": 35,
    },
    {
        "title": "Pair Programming: OAuth-Token-Rotation  Transkript",
        "content": "Thomas: Okay, ich teile meinen Bildschirm. Der aktuelle Token-Refresh schlaegt fehl wenn der Refresh-Token selbst abgelaufen ist.\nMax: Wann laeuft der ab?\nThomas: Bei Google nach 6 Monaten Inaktivitaet, bei Zoom nach 15 Jahren.\nMax: Also nur bei Google ein Problem. Wir sollten den Nutzer informieren und einen Re-Auth-Flow starten.\nThomas: Genau. Ich baue einen Token-Health-Check ein, der 24h vor Ablauf warnt.\nMax: Perfekt. Lass uns das als Middleware implementieren.",
        "participants": ["Thomas Mueller", "Max Bauer"],
        "duration_minutes": 60,
    },
]

_OBSIDIAN_NOTES: list[dict[str, Any]] = [
    {
        "title": "Forschungsnotizen: Vector-Datenbanken",
        "content": "# Vector-Datenbanken Vergleich\n\nFuer PWBS evaluiert:\n- **Weaviate**: Open-Source, REST+GraphQL API, gute Python-Integration\n- **Pinecone**: Managed, schnell, aber EU-Datenhaltung unklar\n- **Milvus**: Performant, aber komplexe Ops\n\n## Entscheidung\nWeaviate wegen EU-Hosting und einfacher Self-Hosting-Moeglichkeit.\n\n## Links\n- [[DSGVO-Checkliste]]\n- [[Embedding-Pipeline-Design]]",
    },
    {
        "title": "Ideen: Automatische Meeting-Zusammenfassung",
        "content": "# Automatische Meeting-Zusammenfassung\n\n## Konzept\nNach jedem Zoom-Meeting automatisch:\n1. Transkript abrufen\n2. Entitaeten extrahieren (Personen, Entscheidungen, Action Items)\n3. Zusammenfassung generieren (max. 200 Woerter)\n4. An Teilnehmer senden\n\n## Offene Fragen\n- Wie mit vertraulichen Meetings umgehen?\n- Opt-in oder Opt-out?\n\n## Tags\n#feature-idea #zoom #briefing",
    },
    {
        "title": "Lernnotizen: FastAPI Best Practices",
        "content": "# FastAPI Best Practices\n\n## Dependency Injection\n- `Depends()` fuer DB-Sessions und Auth\n- Keine globalen States in Route-Handlern\n\n## Middleware-Reihenfolge\n1. CORS\n2. TrustedHost\n3. RequestID\n4. RateLimit\n5. Auth\n6. Audit\n\n## Pydantic v2\n- `model_validator` statt `root_validator`\n- `ConfigDict` statt `class Config`\n\n## Links\n- [[API-Design-Richtlinien]]",
    },
    {
        "title": "Wochenreview KW10",
        "content": "# Wochenreview KW10\n\n## Erledigt\n- OAuth-Flow fuer Google Calendar implementiert\n- 15 Unit-Tests fuer Auth-Module geschrieben\n- ADR fuer Embedding-Modell-Auswahl erstellt\n\n## Gelernt\n- `contextvars` sind essentiell fuer Request-Tracing in async Code\n- Strukturiertes Logging mit structlog spart 50% Debugging-Zeit\n\n## Naechste Woche\n- Notion-Konnektor fertigstellen\n- Briefing-Pipeline testen\n\n## Stimmung: 4/5",
    },
    {
        "title": "Architektur-Notizen: Knowledge Graph",
        "content": "# Knowledge Graph Design\n\n## Schema (Neo4j)\n- Person: name, role, organization\n- Project: name, status, deadline\n- Decision: title, date, rationale\n- Document: title, source, date\n\n## Beziehungen\n- MENTIONED_IN: Person -> Document\n- MADE_IN: Decision -> Meeting\n- DISCUSSED_IN: Topic -> Document\n- INVOLVED_IN: Person -> Project\n\n## MVP: Optional\nNeo4j ist im MVP optional. NullGraphService als Fallback.",
    },
    {
        "title": "Debugging-Log: Sync-Timeout-Problem",
        "content": "# Sync-Timeout bei grossen Notion-Workspaces\n\n## Problem\nBei >500 Seiten tritt ein Timeout auf (30s Default).\n\n## Ursache\nDie Notion-API liefert max. 100 Seiten pro Request. Bei 500 Seiten sind 5 API-Calls noetig, die sequenziell ausgefuehrt werden.\n\n## Loesung\n- Timeout auf 120s erhoehen (nur fuer Notion)\n- Hintergrund-Task fuer initialen Sync\n- Cursor persistent speichern fuer Resume\n\n## Status: geloest",
    },
    {
        "title": "Daily Note 2026-03-14",
        "content": "# 2026-03-14 Donnerstag\n\n## Meetings\n- 09:00 Sprint Planning -> gute Priorisierung\n- 14:00 1:1 mit Maria -> OKR-Fortschritt besprochen\n\n## Tasks\n- [x] OpenAPI-Specs vervollstaendigt\n- [x] Postman-Collection generiert\n- [ ] Seed-Data-Generator starten\n\n## Notizen\n- Der neue CorrelationId-Middleware funktioniert gut im Tracing\n- Naechste Woche: Early-Adopter-Onboarding testen",
    },
    {
        "title": "Buchnotizen: Designing Data-Intensive Applications",
        "content": "# DDIA  Kapitel 3: Storage and Retrieval\n\n## Key Insights\n- LSM-Trees vs. B-Trees: LSM besser fuer Write-Heavy Workloads\n- Bloom-Filter reduzieren unnoetige Disk-Reads\n- Indexing-Strategien: Composite Indexes fuer Multi-Column-Queries\n\n## Anwendung auf PWBS\n- Weaviate nutzt HNSW (nicht LSM/B-Tree) fuer Vektoren\n- PostgreSQL: B-Tree-Indexes fuer owner_id-Queries\n- Composite Index auf (user_id, source_type, source_id) fuer Deduplizierung",
    },
]


def generate_documents(
    user_id: uuid.UUID,
    count: int = 50,
) -> list[dict[str, Any]]:
    """Generate seed documents across all 4 MVP connectors.

    Returns a list of dicts suitable for database insertion. Each dict
    contains UDF-compatible fields with deterministic IDs for idempotency.
    """
    now = datetime.now(tz=timezone.utc)
    documents: list[dict[str, Any]] = []
    idx = 0

    sources = [
        ("google_calendar", _CALENDAR_EVENTS, "plaintext"),
        ("notion", _NOTION_PAGES, "markdown"),
        ("zoom", _ZOOM_TRANSCRIPTS, "plaintext"),
        ("obsidian", _OBSIDIAN_NOTES, "markdown"),
    ]

    while len(documents) < count:
        for source_type, templates, content_type in sources:
            if len(documents) >= count:
                break

            template = templates[idx % len(templates)]
            doc_uuid = _doc_id(source_type, idx)
            content = template["content"]
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            # Vary dates across the last 30 days
            days_ago = (idx * 3) % 30
            created = now - timedelta(days=days_ago, hours=idx % 12)

            doc = {
                "id": doc_uuid,
                "user_id": user_id,
                "source_type": source_type,
                "source_id": f"seed-{source_type}-{idx:04d}",
                "title": template["title"],
                "content": content,
                "content_type": content_type,
                "content_hash": content_hash,
                "language": "de",
                "metadata": {},
                "participants": template.get("participants", []),
                "created_at": created,
                "updated_at": created,
                "fetched_at": now,
                "processing_status": "completed",
                "chunk_count": max(1, len(content) // 300),
            }

            if "location" in template:
                doc["metadata"]["location"] = template["location"]
            if "duration_minutes" in template:
                doc["metadata"]["duration_minutes"] = template["duration_minutes"]

            documents.append(doc)
        idx += 1

    return documents


async def _seed_database(
    user_email: str,
    document_count: int,
) -> None:
    """Insert demo user and documents into PostgreSQL."""
    import os
    os.environ.setdefault("DEBUG", "1")

    from sqlalchemy import delete, select, text

    from pwbs.core.config import get_settings
    from pwbs.db.postgres import get_engine
    from pwbs.models.base import Base
    from pwbs.models.chunk import Chunk
    from pwbs.models.document import Document
    from pwbs.models.user import User

    settings = get_settings()
    engine = get_engine(str(settings.database_url))

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Check if demo user exists
        result = await session.execute(
            select(User).where(User.id == DEMO_USER_ID)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user is None:
            # Create demo user with hashed password
            from pwbs.services.auth import hash_password
            user = User(
                id=DEMO_USER_ID,
                email=user_email,
                password_hash=hash_password(DEMO_USER_PASSWORD),
                display_name="Demo User",
                is_active=True,
            )
            session.add(user)
            await session.flush()
            logger.info("Created demo user: %s (ID: %s)", user_email, DEMO_USER_ID)
        else:
            logger.info("Demo user already exists: %s", user_email)

        # Delete existing demo documents (idempotent upsert)
        await session.execute(
            delete(Document).where(
                Document.user_id == DEMO_USER_ID,
                Document.source_id.like("seed-%"),
            )
        )

        # Generate and insert documents
        docs = generate_documents(DEMO_USER_ID, document_count)
        for doc in docs:
            orm_doc = Document(
                id=doc["id"],
                user_id=doc["user_id"],
                source_type=doc["source_type"],
                source_id=doc["source_id"],
                title=doc["title"],
                content_hash=doc["content_hash"],
                language=doc["language"],
                chunk_count=doc["chunk_count"],
                processing_status=doc["processing_status"],
            )
            session.add(orm_doc)

        await session.commit()
        logger.info(
            "Seeded %d documents across 4 connectors for user %s",
            len(docs),
            user_email,
        )


async def _clean_database() -> None:
    """Remove all demo data from PostgreSQL."""
    import os
    os.environ.setdefault("DEBUG", "1")

    from sqlalchemy import delete, select

    from pwbs.core.config import get_settings
    from pwbs.db.postgres import get_engine
    from pwbs.models.chunk import Chunk
    from pwbs.models.document import Document
    from pwbs.models.user import User

    settings = get_settings()
    engine = get_engine(str(settings.database_url))

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Cascading delete: removing the user deletes all related data
        result = await session.execute(
            select(User).where(User.id == DEMO_USER_ID)
        )
        user = result.scalar_one_or_none()
        if user:
            await session.delete(user)
            await session.commit()
            logger.info("Cleaned all demo data for user %s", DEMO_USER_ID)
        else:
            logger.info("No demo user found  nothing to clean")


def run_seed(
    user_email: str = "demo@pwbs.dev",
    document_count: int = 50,
    clean: bool = False,
) -> None:
    """Entry point called by the CLI __main__."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if clean:
        print(f"Cleaning demo data for user {DEMO_USER_ID}...")
        asyncio.run(_clean_database())
        print("Done.")
    else:
        print(f"Seeding {document_count} documents for {user_email}...")
        asyncio.run(_seed_database(user_email, document_count))
        print(f"Done. Demo user: {user_email} / {DEMO_USER_PASSWORD}")
