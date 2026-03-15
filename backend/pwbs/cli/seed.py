"""Seed-Data-Generator: realistic demo data for PWBS (TASK-198).

Creates a demo user and 50 documents across all 4 core connectors
(Google Calendar, Notion, Obsidian, Zoom). The data is inserted into
PostgreSQL and can be cleaned up with ``--clean``.

Weaviate indexing and embedding generation are triggered separately
via the processing pipeline (``python -m pwbs.cli seed`` writes DB
records; a subsequent sync or scheduled job produces embeddings).

Usage::

    python -m pwbs.cli seed
    python -m pwbs.cli seed --user demo@pwbs.dev --documents 50
    python -m pwbs.cli seed --clean
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)

# Fixed UUID for deterministic demo user (idempotent).
DEMO_USER_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")
DEMO_PASSWORD = "DemoPwbs2026!"  # only for local dev

# ---------------------------------------------------------------------------
# Document templates (German, realistic knowledge-worker content)
# ---------------------------------------------------------------------------

_CALENDAR_EVENTS = [
    ("Produkt-Sync mit Team Alpha", "Fortschritt der API-Migration besprechen. Thomas hat Bedenken zur Abwaertskompatibilitaet."),
    ("1:1 mit Teamlead Maria", "Quartals-Review vorbereiten. Feedback zum neuen Onboarding-Prozess sammeln."),
    ("Sprint Retrospektive Q1", "Was lief gut: Deployment-Automatisierung. Action Items aus letztem Retro pruefen."),
    ("Architektur-Review: Microservices", "Entscheidung ob monolithische Architektur beibehalten oder auf Microservices migriert wird."),
    ("Kunden-Demo Projekt Phoenix", "Neues Dashboard-Feature vorstellen. Live-Demo der Echtzeit-Datenvisualisierung."),
    ("DevOps-Workshop: Kubernetes Basics", "Einfuehrung in Container-Orchestrierung. Hands-on mit kubectl."),
    ("Budget-Planung 2026 H2", "Cloud-Kosten optimieren. Neue Tooling-Investitionen: Monitoring, Testing."),
    ("Onboarding: Neue Entwicklerin Sarah", "Entwicklungsumgebung einrichten. Git-Workflow erklaeren."),
    ("Security Audit Vorbereitung", "OWASP Top 10 Checkliste durchgehen. DSGVO-Compliance-Status pruefen."),
    ("Quartals-OKR-Review", "Objectives und Key Results fuer Q2 besprechen. Team-Velocity analysieren."),
    ("Stakeholder-Praesentation ML-Pipeline", "Ergebnisse des ML-PoC vorstellen. ROI-Berechnung praesentieren."),
    ("Pair-Programming Session: Auth-Modul", "JWT-Refresh-Token-Logik implementieren mit Sarah."),
    ("Team-Standup Woche 12", "Blocker: CI/CD Pipeline instabil. Sarah uebernimmt Deployment-Fix."),
]

_NOTION_PAGES = [
    ("Projektplan Q2 2026", "## Meilensteine\n- MVP-Launch: 15. April\n- Beta-Test: 1. Mai\n- GA-Release: 15. Juni\n\n## Risiken\n- Abhaengigkeit von externem API-Provider\n- Personalengpass im Frontend-Team"),
    ("Meeting-Notizen: Architektur-Board", "### Entscheidung\nModularer Monolith bleibt bestehen. Service-Split erst ab Phase 3.\n\n### Begruendung\n- Team-Groesse rechtfertigt keinen Microservice-Overhead\n- Latenz-Vorteile bei In-Process-Kommunikation"),
    ("DSGVO-Checkliste Datenverarbeitung", "- [x] Datenschutzerklaerung aktualisiert\n- [x] Auftragsverarbeitungsvertrag mit Cloud-Provider\n- [ ] Cookie-Banner implementieren\n- [ ] Loeschkonzept dokumentieren"),
    ("Onboarding-Guide Neue Entwickler", "## Tag 1\n1. Laptop einrichten\n2. Git-Zugang und Branch-Konventionen\n3. Docker Compose starten\n\n## Tag 2\n1. Code-Walkthrough Backend\n2. Pair-Programming mit Mentor"),
    ("API-Design-Guidelines", "## Versionierung\nAlle Endpunkte unter `/api/v1/`. Breaking Changes erfordern neue Version.\n\n## Pagination\nCursor-basiert mit `after`-Parameter. Maximal 100 Elemente pro Seite."),
    ("Sprint-Review Ergebnisse W11", "### Abgeschlossene Stories\n- TASK-142: Briefing-Generierung optimiert\n- TASK-145: Search-API mit Hybrid-Modus\n\n### Offene Punkte\n- Performance-Test steht noch aus"),
    ("Technische Schulden Backlog", "| Technische Schuld | Prioritaet | Aufwand |\n|---|---|---|\n| Legacy-Auth migrieren | Hoch | 3 Tage |\n| Test-Coverage erhoehen | Mittel | 5 Tage |"),
    ("Incident Report: API-Ausfall 2026-03-10", "## Timeline\n- 14:23 Alarm ausgeloest\n- 14:25 On-Call benachrichtigt\n- 14:40 Root Cause identifiziert: DB Connection Pool exhausted\n- 14:55 Fix deployed, Service wieder verfuegbar"),
    ("Wissensmanagement-Strategie", "## Vision\nJeder Mitarbeiter findet relevantes Wissen in unter 30 Sekunden.\n\n## Massnahmen\n1. Zentrales Knowledge-Base-System (PWBS)\n2. Automatische Briefings vor Meetings"),
    ("Performance-Benchmarks Q1", "| Metrik | Ziel | Ist |\n|---|---|---|\n| API P95 Latenz | <200ms | 145ms |\n| Search P95 | <500ms | 380ms |\n| Briefing-Generierung | <5s | 3.2s |"),
    ("Code-Review-Richtlinien", "## Pflicht-Checks\n1. Typing vollstaendig (kein `Any`)\n2. owner_id Filter in jeder DB-Query\n3. Idempotente Writes (UPSERT statt INSERT)\n4. Keine Secrets im Code"),
    ("Roadmap 2026 H2", "## Fokus\n- Konnektoren: Gmail, Slack, Outlook\n- Knowledge Graph: Neo4j-Integration vertiefen\n- Enterprise: SSO, RBAC, Multi-Tenancy"),
]

_OBSIDIAN_NOTES = [
    ("Gedanken zur Wissensarbeit", "Die groesste Herausforderung moderner Wissensarbeit ist nicht der Mangel an Information, sondern deren Fragmentierung. Notizen in 5 verschiedenen Tools, Meetings ohne Kontext, Entscheidungen die niemand dokumentiert."),
    ("Ideen fuer Briefing-Verbesserungen", "- Kontext aus vorherigen Meetings einbeziehen\n- Projekt-Timeline als visuelle Komponente\n- Automatische Erkennung von Entscheidungen vs. offenen Fragen"),
    ("Reflexion: Teamdynamik Q1", "Das Team hat sich gut eingespielt. Sarah bringt frischen Wind in die Code-Reviews. Thomas' Bedenken zur Architektur waren berechtigt und haben uns vor einem teuren Refactoring bewahrt."),
    ("Lernnotizen: Vector Databases", "## Konzepte\n- HNSW Index: Hierarchical Navigable Small World\n- Cosine Similarity vs. Euclidean Distance\n- Hybrid Search: Kombination aus Vektor- und Keyword-Suche\n\nWeaviate nutzt HNSW standardmaessig."),
    ("Buchnotizen: Team Topologies", "Vier Team-Typen: Stream-aligned, Enabling, Complicated Subsystem, Platform.\nUnsere Backend-Crew ist stream-aligned. DevOps-Team ist ein Platform-Team. Klare Boundaries definieren!"),
    ("Tagesnotiz 2026-03-15", "Produktiver Tag. Briefing-Feature fast fertig. Search-Relevanz muss noch getuned werden. Abends: Paper zu RAG-Architekturen gelesen."),
    ("Wochenrueckblick KW11", "- Erfolgreich: E2E-Pipeline-Test implementiert\n- Gelernt: Circuit Breaker Pattern spart viel Debugging-Zeit\n- Naechste Woche: DSGVO-Export fertigstellen"),
    ("Meeting-Prep: Investoren-Update", "## Key Metrics\n- MAU: 47 Early Adopters\n- Retention 30d: 78%\n- NPS: 62\n\n## Highlights\n- Hybrid-Suche 3x schneller als GPT-only\n- DSGVO-Compliance vollstaendig"),
    ("Technische Vision 2027", "Langfristig: PWBS als persoenliches Betriebssystem fuer Wissensarbeit. Nicht nur Suche, sondern proaktive Kontextualisierung. Der Knowledge Graph wird zur zentralen Denkstruktur."),
    ("Debugging-Notizen: Memory Leak", "Problem: Weaviate-Client haelt Connections offen.\nLoesung: Connection Pool mit max_connections=10 und idle_timeout=300s.\nGelernt: Immer async context manager verwenden!"),
    ("Rezept: Gutes Standup", "1. Max 15 Min\n2. Jeder: Was gestern, was heute, Blocker\n3. Details offline klaeren\n4. Standup-Notiz automatisch ins Wiki"),
    ("Prompt Engineering Notizen", "- Structured Output mit JSON Schema erzwingen\n- Temperature 0.3 fuer sachliche Inhalte\n- Quellenreferenzen immer als separate Liste anfuegen"),
]

_ZOOM_TRANSCRIPTS = [
    ("Sprint Planning - Transkript", "Moderator: Ok, lasst uns die Stories fuer Sprint 12 durchgehen. Thomas, kannst du TASK-201 schaetzen? Thomas: Ich wuerde sagen M, also 2-3 Tage. Der Reranker braucht gutes Benchmarking. Maria: Einverstanden. Sarah, uebernimmst du TASK-202? Sarah: Ja, der DSGVO-Export ist klar definiert. Ich schaetze S."),
    ("Architektur-Diskussion Transkript", "Lena: Die Frage ist ob wir Neo4j im MVP brauchen. Thomas: Ich plaediere fuer optional. Wir koennen mit NullGraphService fallbacken. Maria: Guter Punkt. Dann machen wir es optional mit Docker Profile."),
    ("Retro-Transkript KW10", "Facilitator: Was lief gut? Sarah: Die neuen Unit-Tests haben 3 Bugs beim Refactoring gefangen. Thomas: CI/CD ist jetzt stabil. Was kann besser? Maria: Code-Reviews dauern manchmal 3 Tage. Vorschlag: SLA von 24h."),
    ("Kunden-Interview Transkript", "Interviewer: Wie managen Sie aktuell Ihr Wissen? Kunde: Ehrlich gesagt gar nicht systematisch. Notion fuer Notizen, Google Calendar fuer Termine, Slack fuer Kommunikation. Nichts davon ist verbunden."),
    ("Standup-Zusammenfassung Transkript", "Sarah: Gestern TASK-200 abgeschlossen, heute starte ich mit TASK-202. Blocker: Brauche Zugang zum Test-Mailserver. Thomas: Ich arbeite weiter an der Search-Relevanz. Kein Blocker. Maria: Bin im Kunden-Call bis 14 Uhr."),
    ("Tech-Talk: Embedding-Modelle", "Referent: Sentence Transformers sind fuer deutsche Texte gut geeignet. Wir nutzen paraphrase-multilingual-MiniLM-L12-v2. Frage: Wie ist die Performance? Referent: ~50ms pro Embedding auf GPU, ~200ms auf CPU."),
    ("Projekt-Phoenix Statusmeeting", "PM: Wir liegen im Zeitplan. Der MVP ist zu 85% fertig. Offene Punkte: Search-Tuning und DSGVO-Export. Beides ist fuer diese Woche eingeplant. Risiko: Frontend-Redesign koennte sich verzoegern."),
    ("1:1 Maria-Thomas Transkript", "Maria: Wie geht es dir mit der neuen Architektur? Thomas: Gut. Der modulare Monolith war die richtige Entscheidung. Die klaren Modul-Grenzen helfen enorm. Maria: Freut mich. Und das Onboarding von Sarah? Thomas: Sie ist super. Hat schon eigenstaendig den Circuit Breaker implementiert."),
]


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _doc_id(source_type: str, index: int) -> uuid.UUID:
    """Deterministic UUID for a seed document (idempotent)."""
    return uuid.uuid5(DEMO_USER_ID, f"{source_type}:{index}")


def generate_documents(
    user_id: uuid.UUID,
    count: int,
) -> list[dict[str, Any]]:
    """Build a list of document dicts ready for bulk insert."""
    docs: list[dict[str, Any]] = []
    now = datetime.now(tz=timezone.utc)
    sources = [
        ("google_calendar", _CALENDAR_EVENTS),
        ("notion", _NOTION_PAGES),
        ("obsidian", _OBSIDIAN_NOTES),
        ("zoom", _ZOOM_TRANSCRIPTS),
    ]

    idx = 0
    while len(docs) < count:
        for source_type, templates in sources:
            if len(docs) >= count:
                break
            tpl_idx = idx % len(templates)
            title, content = templates[tpl_idx]

            # Make each document unique even when cycling
            cycle = idx // len(templates)
            if cycle > 0:
                title = f"{title} (#{cycle + 1})"
                content = f"{content}\n\n[Wiederholung {cycle + 1}]"

            doc_id = _doc_id(source_type, idx)
            docs.append({
                "id": doc_id,
                "user_id": user_id,
                "source_type": source_type,
                "source_id": f"seed-{source_type}-{idx:04d}",
                "title": title,
                "content": content,
                "content_hash": _content_hash(content),
                "language": "de",
                "chunk_count": 0,
                "processing_status": "pending",
                "visibility": "private",
                "created_at": now - timedelta(days=count - idx),
                "updated_at": now,
            })
            idx += 1

    return docs


async def _seed_async(
    user_email: str,
    document_count: int,
    database_url: str,
) -> None:
    """Core async seed logic."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            async with session.begin():
                # 1. Upsert demo user
                from pwbs.services.user import hash_password, _generate_encrypted_dek
                from pwbs.models.user import User

                existing = await session.execute(
                    select(User).where(User.id == DEMO_USER_ID)
                )
                user = existing.scalar_one_or_none()

                if user is None:
                    user = User(
                        id=DEMO_USER_ID,
                        email=user_email,
                        display_name="Demo User",
                        password_hash=hash_password(DEMO_PASSWORD),
                        encryption_key_enc=_generate_encrypted_dek(),
                    )
                    session.add(user)
                    await session.flush()
                    print(f"Created demo user: {user_email} (ID: {DEMO_USER_ID})")
                else:
                    print(f"Demo user already exists: {user.email} (ID: {DEMO_USER_ID})")

                # 2. Delete existing seed documents (idempotent)
                from pwbs.models.document import Document

                del_result = await session.execute(
                    delete(Document).where(
                        Document.user_id == DEMO_USER_ID,
                        Document.source_id.like("seed-%"),
                    )
                )
                if del_result.rowcount:
                    print(f"Cleaned {del_result.rowcount} existing seed documents")

                # 3. Insert new documents
                docs = generate_documents(DEMO_USER_ID, document_count)
                # Strip fields not in DB model (content is for display/test only;
                # created_at/updated_at are auto-generated by SQLAlchemy)
                db_columns = {c.name for c in Document.__table__.columns}
                for doc_dict in docs:
                    filtered = {k: v for k, v in doc_dict.items() if k in db_columns}
                    session.add(Document(**filtered))

                print(f"Inserted {len(docs)} documents across 4 connectors")

                # Summary
                for st in ("google_calendar", "notion", "obsidian", "zoom"):
                    n = sum(1 for d in docs if d["source_type"] == st)
                    print(f"  - {st}: {n}")

        print("\nSeed complete. Run processing pipeline to generate embeddings.")
    finally:
        await engine.dispose()


async def _clean_async(database_url: str) -> None:
    """Remove all demo data."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from pwbs.models.user import User
    from pwbs.models.document import Document

    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            async with session.begin():
                # Delete documents first (FK constraint)
                doc_result = await session.execute(
                    delete(Document).where(Document.user_id == DEMO_USER_ID)
                )
                print(f"Deleted {doc_result.rowcount} demo documents")

                # Delete demo user
                user_result = await session.execute(
                    delete(User).where(User.id == DEMO_USER_ID)
                )
                if user_result.rowcount:
                    print(f"Deleted demo user (ID: {DEMO_USER_ID})")
                else:
                    print("Demo user not found (already clean)")

        print("Clean complete.")
    finally:
        await engine.dispose()


def run_seed(
    user_email: str = "demo@pwbs.dev",
    document_count: int = 50,
    clean: bool = False,
) -> None:
    """Entry point called from ``pwbs.cli.__main__``."""
    from pwbs.core.config import get_settings

    settings = get_settings()
    db_url = settings.database_url

    if not db_url:
        print("ERROR: DATABASE_URL not configured.", file=sys.stderr)
        sys.exit(1)

    if clean:
        asyncio.run(_clean_async(db_url))
    else:
        asyncio.run(_seed_async(user_email, document_count, db_url))