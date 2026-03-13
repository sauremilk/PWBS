# Architektur: Persönliches Wissens-Betriebssystem (PWBS)

**Version:** 0.1.0 – MVP-Architektur  
**Stand:** März 2026  
**Zielgruppe:** Seniorentwickler, technische Mitgründer  
**Scope:** MVP (Phase 2) mit Skalierungspfad bis Phase 5

---

## Inhaltsverzeichnis

1. [Überblick](#1-überblick)
2. [System-Übersicht](#2-system-übersicht)
3. [Komponenten-Architektur](#3-komponenten-architektur)
4. [Datenfluss](#4-datenfluss)
5. [Datenschutz & Sicherheit](#5-datenschutz--sicherheit)
6. [Skalierungsstrategie](#6-skalierungsstrategie)
7. [Entscheidungsprotokoll (ADR-Tabelle)](#7-entscheidungsprotokoll-adr-tabelle)
8. [Entwicklungs- und Deployment-Setup](#8-entwicklungs--und-deployment-setup)
9. [Phase-Mapping](#9-phase-mapping)
10. [Offene technische Fragen](#10-offene-technische-fragen)

---

## 1. Überblick

### 1.1 Architekturphilosophie

Das PWBS ist eine kognitive Infrastruktur – kein klassisches SaaS-Dashboard. Die Architektur reflektiert diese Identität: Sie muss heterogene, hochpersönliche Daten in Echtzeit zusammenführen, semantisch durchdringen und kontextbezogen aufbereiten – ohne dabei die Datensouveränität des Nutzers zu kompromittieren.

Die Architektur folgt dem Prinzip **„Progressive Complexity"**: Im MVP wird jede Komponente als einzelner Service mit klaren Interfaces betrieben. Die Grenzen zwischen Services sind so geschnitten, dass sie bei steigender Last unabhängig skaliert, bei Self-Hosting-Anforderungen selektiv isoliert und bei Team-Features kontrolliert geöffnet werden können.

### 1.2 Designprinzipien

| Prinzip | Implikation |
|---------|-------------|
| **DSGVO by Design** | Verschlüsselung, Datenminimierung und Löschbarkeit sind keine Features, sondern Grundstruktur. Jedes Datum hat einen Owner, einen Zweck und ein Ablaufdatum. |
| **Erklärbarkeit** | Jede LLM-generierte Aussage transportiert Quellenreferenzen. Der Knowledge Graph ist die Audit-Schicht zwischen Rohdaten und generierten Briefings. |
| **Modularität** | Konnektoren, Processing-Schritte und Storage-Backends sind austauschbar. Neue Datenquellen erfordern nur einen neuen Konnektor, keinen Umbau der Pipeline. |
| **Cloud + On-Premise** | Die Architektur trennt Compute von State. Alle stateful Komponenten (Postgres, Weaviate, Neo4j) laufen containerisiert. Self-Hosting ist ein Deployment-Profil, kein Fork. |
| **Offline-First-Fähigkeit** | Lokale Embedding-Modelle (Sentence Transformers via Ollama) und lokale LLMs ermöglichen einen vollständig offline-fähigen Modus ab Phase 3. |
| **Idempotenz** | Jeder Ingestion- und Processing-Schritt ist idempotent. Konnektoren verwenden Cursor/Watermarks, die Pipeline kann ohne Datenverlust oder Duplikate neu gestartet werden. |

### 1.3 Evolutionsstufen

```
Phase 1          Phase 2          Phase 3           Phase 4           Phase 5
Discovery        MVP              Private Beta      Launch            Plattform
─────────────────────────────────────────────────────────────────────────────────

PoC:             Monolith mit     Service-Split:    Multi-Tenancy,    API-Plattform,
Embeddings +     klaren Modul-    Queue-basierte    Self-Hosting,     Marketplace,
Semantic Search  grenzen,         Pipeline,         Team-Features     Mobile, Vertikale
über 2 Quellen   4 Konnektoren,   Desktop-App                        Spezialisierungen
                 Web-Frontend     (Tauri)
```

Die MVP-Architektur (Phase 2) ist ein **modularer Monolith**: Ein einzelner FastAPI-Prozess beinhaltet alle Backend-Logik, nutzt aber intern klar getrennte Module. Die Module kommunizieren über definierte Python-Interfaces – nicht über HTTP. Dieses Design erlaubt schnelle Iteration bei kleinem Team und ermöglicht späteren Service-Split ohne Rewrite.

---

## 2. System-Übersicht

### 2.1 Gesamtarchitektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATENQUELLEN                                   │
│                                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │  Google   │ │  Notion  │ │ Obsidian │ │   Zoom   │ │  Slack   │  ...    │
│  │ Calendar  │ │   API    │ │  Vault   │ │Transkr.  │ │   API    │         │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘         │
│       │             │            │             │             │               │
└───────┼─────────────┼────────────┼─────────────┼─────────────┼───────────────┘
        │             │            │             │             │
        ▼             ▼            ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INGESTION LAYER                                    │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ Connector Registry                                                 │     │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐     │     │
│  │  │ OAuth Token│ │  Webhook   │ │   Polling   │ │ File Watch │     │     │
│  │  │  Manager   │ │  Receiver  │ │  Scheduler  │ │  (Local)   │     │     │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘     │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │ Normalizer: Rohdaten → Unified Document Format (UDF)               │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROCESSING LAYER                                    │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Chunking   │─▶│  Embedding   │─▶│     NER /    │─▶│    Graph     │   │
│  │   Service    │  │  Generator   │  │  Extraction  │  │   Builder    │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STORAGE LAYER                                      │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │   PostgreSQL     │  │    Weaviate       │  │     Neo4j        │          │
│  │                  │  │                   │  │                  │          │
│  │ - Users/Auth     │  │ - Document        │  │ - Person         │          │
│  │ - Documents      │  │   Embeddings      │  │ - Project        │          │
│  │ - Connections    │  │ - Chunk Vectors   │  │ - Topic          │          │
│  │ - Job State      │  │ - Semantic Index  │  │ - Decision       │          │
│  │ - Audit Log      │  │                   │  │ - Meeting        │          │
│  │ - Encryption     │  │                   │  │ - RELATES_TO     │          │
│  │   Keys (wrapped) │  │                   │  │ - DECIDED_IN     │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API LAYER                                        │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐       │
│  │ FastAPI Application                                              │       │
│  │                                                                  │       │
│  │  /api/v1/auth/*          JWT + OAuth2 Flows                     │       │
│  │  /api/v1/connectors/*    Konnektor-Management                   │       │
│  │  /api/v1/search/*        Semantische Suche                      │       │
│  │  /api/v1/briefings/*     Briefing-Generierung & -Abruf          │       │
│  │  /api/v1/knowledge/*     Knowledge-Graph-Exploration            │       │
│  │  /api/v1/documents/*     Dokument-CRUD                          │       │
│  │  /api/v1/admin/*         System-Administration                  │       │
│  │                                                                  │       │
│  │  Middleware: Auth │ Rate Limiting │ Encryption │ CORS │ Logging  │       │
│  └──────────────────────────────────────────────────────────────────┘       │
│                                                                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                      │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │   Next.js Web    │  │   Tauri Desktop  │  │   Slack Bot /    │          │
│  │   (Vercel)       │  │   (Phase 3+)     │  │   Extensions     │          │
│  │                  │  │                  │  │   (Phase 3+)     │          │
│  │ - Dashboard      │  │ - Offline Mode   │  │                  │          │
│  │ - Briefing View  │  │ - Local Vault    │  │ - Context Sidebar│          │
│  │ - Search         │  │ - System Tray    │  │ - Quick Search   │          │
│  │ - Connectors     │  │                  │  │                  │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Deployment-Topologie (MVP / Phase 2)

```
                    ┌──────────────────────┐
                    │      Vercel          │
                    │  ┌────────────────┐  │
                    │  │  Next.js App   │  │
                    │  │  (SSR + Edge)  │  │
                    │  └───────┬────────┘  │
                    └──────────┼───────────┘
                               │ HTTPS
                               ▼
                    ┌──────────────────────┐
                    │   AWS (eu-central-1) │
                    │                      │
                    │  ┌────────────────┐  │
                    │  │  ALB / API GW  │  │
                    │  └───────┬────────┘  │
                    │          │           │
                    │  ┌───────▼────────┐  │
                    │  │   ECS Fargate  │  │
                    │  │   FastAPI      │  │
                    │  │   (2 Tasks)    │  │
                    │  └───────┬────────┘  │
                    │          │           │
                    │  ┌───────┼────────┐  │
                    │  │       │        │  │
                    │  ▼       ▼        ▼  │
                    │ RDS    Weaviate  Neo4j│
                    │ Postgres (EC2)  (EC2)│
                    │  (t3)  (t3.xl) (t3.l)│
                    │                      │
                    │  Redis (ElastiCache) │
                    └──────────────────────┘
```

---

## 3. Komponenten-Architektur

### 3.1 Ingestion Service

Der Ingestion Service ist das Eingangstor für alle externen Daten. Er abstrahiert die Heterogenität der Datenquellen hinter einem einheitlichen `Connector`-Interface.

#### Connector-Architektur

```python
# Basis-Interface für alle Konnektoren
class BaseConnector(ABC):
    """Jeder Konnektor implementiert dieses Interface."""

    @abstractmethod
    async def authenticate(self, credentials: OAuthCredentials) -> TokenPair:
        """OAuth2-Flow oder API-Key-Validierung."""

    @abstractmethod
    async def fetch_incremental(self, watermark: datetime) -> list[RawDocument]:
        """Holt alle Dokumente seit dem letzten Watermark."""

    @abstractmethod
    async def normalize(self, raw: RawDocument) -> UnifiedDocument:
        """Konvertiert Rohdaten in das Unified Document Format."""

    @abstractmethod
    def source_type(self) -> SourceType:
        """Identifikator der Datenquelle."""
```

#### Konnektoren im MVP (Phase 2)

| Konnektor | Auth-Methode | Sync-Strategie | Datentypen |
|-----------|-------------|----------------|------------|
| **Google Calendar** | OAuth2 (Google) | Webhook + Polling-Fallback (15 min) | Events, Teilnehmer, Beschreibungen |
| **Notion** | OAuth2 (Notion Integration) | Polling (10 min), `last_edited_time`-Cursor | Pages, Databases, Blöcke |
| **Obsidian** | Lokaler Vault-Pfad (kein OAuth) | File-System-Watcher (fswatch/watchdog) | Markdown-Dateien, Frontmatter, interne Links |
| **Zoom** | OAuth2 (Zoom Marketplace) | Webhook (Recording completed) | Meeting-Transkripte, Teilnehmer, Dauer |
| **Slack** | OAuth2 (Slack App) | Events API (Webhook) + Cursor-basiertes Backfill | Nachrichten, Channels, Threads, Reaktionen |
| **Gmail** | OAuth2 (Google) | Push Notifications (Pub/Sub) + History API | E-Mails, Threads, Anhänge (Metadaten) |

#### Unified Document Format (UDF)

Alle Konnektoren normalisieren ihre Rohdaten in ein gemeinsames Format:

```python
@dataclass
class UnifiedDocument:
    id: UUID
    user_id: UUID
    source_type: SourceType          # GOOGLE_CALENDAR, NOTION, OBSIDIAN, ...
    source_id: str                   # ID im Quellsystem
    title: str
    content: str                     # Plaintext oder Markdown
    content_type: ContentType        # PLAINTEXT, MARKDOWN, HTML
    metadata: dict                   # Quellenspezifische Metadaten
    participants: list[str]          # Beteiligte Personen (E-Mail, Name)
    created_at: datetime
    updated_at: datetime
    fetched_at: datetime
    language: str                    # ISO 639-1 (de, en, ...)
    raw_hash: str                    # SHA-256 des Rohinhalt für Deduplizierung
```

#### OAuth-Flow (vereinfacht)

```
Nutzer                   Frontend              Backend              Google/Slack/...
  │                        │                      │                       │
  │  "Verbinde Google"     │                      │                       │
  │ ──────────────────────▶│                      │                       │
  │                        │  GET /connectors/    │                       │
  │                        │    google/auth-url   │                       │
  │                        │ ────────────────────▶│                       │
  │                        │                      │  OAuth2 Auth URL      │
  │                        │  ◀────────────────── │                       │
  │  Redirect zu Google    │                      │                       │
  │ ◀──────────────────────│                      │                       │
  │                        │                      │                       │
  │  Login + Consent       │                      │                       │
  │ ─────────────────────────────────────────────────────────────────────▶│
  │                        │                      │                       │
  │  Callback mit Code     │                      │                       │
  │ ──────────────────────▶│  POST /connectors/   │                       │
  │                        │    google/callback    │                       │
  │                        │ ────────────────────▶│                       │
  │                        │                      │  Exchange Code→Token  │
  │                        │                      │ ─────────────────────▶│
  │                        │                      │  Access+Refresh Token │
  │                        │                      │ ◀─────────────────────│
  │                        │                      │                       │
  │                        │                      │  Tokens verschlüsselt │
  │                        │                      │  in DB speichern      │
  │                        │                      │                       │
  │                        │                      │  Initial Sync starten │
  │                        │  Status: connected   │                       │
  │                        │ ◀────────────────────│                       │
  │  "Google verbunden"    │                      │                       │
  │ ◀──────────────────────│                      │                       │
```

### 3.2 Processing Pipeline

Die Pipeline transformiert `UnifiedDocument`-Objekte in durchsuchbare, verknüpfte Wissenseinheiten. Im MVP läuft sie synchron innerhalb des FastAPI-Prozesses (via Background Tasks); ab Phase 3 wird sie auf eine Queue-basierte Architektur umgestellt.

#### Pipeline-Stufen

```
UnifiedDocument
      │
      ▼
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Chunking   │────▶│    Embedding    │────▶│   NER / Entity   │────▶│  Graph Builder │
│             │     │   Generation    │     │   Extraction     │     │                │
│ - Semantic  │     │                 │     │                  │     │ - Knoten       │
│   Splitting │     │ - OpenAI API    │     │ - Personen       │     │   erstellen    │
│ - Overlap   │     │   oder          │     │ - Projekte       │     │ - Kanten       │
│ - Max 512   │     │ - Sentence      │     │ - Themen         │     │   ableiten     │
│   Tokens    │     │   Transformers  │     │ - Entscheidungen │     │ - Gewichte     │
│             │     │   (lokal)       │     │ - Termine        │     │   berechnen    │
└─────────────┘     └─────────────────┘     └──────────────────┘     └────────────────┘
                                                                            │
                                                                            ▼
                                                                     ┌────────────────┐
                                                                     │  Storage Write │
                                                                     │                │
                                                                     │ → PostgreSQL   │
                                                                     │ → Weaviate     │
                                                                     │ → Neo4j        │
                                                                     └────────────────┘
```

#### Chunking-Strategie

```python
class ChunkingConfig:
    max_tokens: int = 512           # Max Tokens pro Chunk
    overlap_tokens: int = 64        # Überlappung zwischen Chunks
    strategy: str = "semantic"      # "semantic" | "fixed" | "paragraph"

# Semantic Splitting: Aufteilen an Satzgrenzen, wobei semantisch
# zusammenhängende Abschnitte erhalten bleiben.
# Paragraph Splitting: Fallback für strukturierte Dokumente (Notion, Obsidian).
# Fixed Splitting: Nur für unstrukturierte Langtext-Inputs.
```

#### Embedding-Generierung

| Modus | Modell | Dimensionen | Latenz (pro Chunk) | Kosten |
|-------|--------|-------------|---------------------|--------|
| **Cloud (Standard)** | `text-embedding-3-small` (OpenAI) | 1536 | ~50ms | ~$0.02/1M Tokens |
| **Cloud (High Quality)** | `text-embedding-3-large` (OpenAI) | 3072 | ~80ms | ~$0.13/1M Tokens |
| **Lokal** | `all-MiniLM-L6-v2` (Sentence Transformers) | 384 | ~15ms (GPU), ~100ms (CPU) | Gratis |

Im MVP wird `text-embedding-3-small` verwendet. Das Embedding-Modell ist via Konfiguration austauschbar; Weaviate-Collections werden beim Modellwechsel re-indexiert.

#### NER / Entitätsextraktion

Die Entitätsextraktion erfolgt zweistufig:

1. **Regelbasiert (schnell):** E-Mail-Adressen, @-Mentions, Kalender-Teilnehmer, Notion-Verlinkungen → direkte Entity-Erkennung.
2. **LLM-basiert (präzise):** Für Freitext-Inhalte wird ein strukturierter LLM-Call (Claude) eingesetzt:

```python
ENTITY_EXTRACTION_PROMPT = """
Analysiere den folgenden Text und extrahiere strukturiert:

1. PERSONEN: Name, Rolle (falls erkennbar), Kontext
2. PROJEKTE: Name, Status (falls erkennbar)
3. THEMEN: Schlüsselthemen und -konzepte
4. ENTSCHEIDUNGEN: Was wurde entschieden, von wem, wann
5. OFFENE FRAGEN: Unbeantwortete Fragen oder ausstehende Klärungen
6. TERMINE: Referenzierte Daten oder Deadlines

Antworte ausschließlich im folgenden JSON-Format:
{
  "persons": [{"name": "...", "role": "...", "context": "..."}],
  "projects": [{"name": "...", "status": "..."}],
  "topics": ["..."],
  "decisions": [{"what": "...", "by": "...", "date": "..."}],
  "open_questions": ["..."],
  "dates": [{"description": "...", "date": "..."}]
}

TEXT:
{chunk_text}
"""
```

Die LLM-basierte Extraktion wird nur für Chunks ausgeführt, die die regelbasierte Stufe nicht vollständig abdeckt. Kostencontrol: Max. 100 LLM-Extraction-Calls pro Nutzer/Tag im MVP.

### 3.3 Knowledge Store

Der Knowledge Store besteht aus drei spezialisierten Datenbanken, die jeweils unterschiedliche Zugriffsmuster optimieren.

#### 3.3.1 PostgreSQL – Relationale Daten & System State

PostgreSQL ist die **Single Source of Truth** für Nutzerdaten, Konnektorzustand und Audit-Logs.

```sql
-- Kern-Schema (vereinfacht)

-- Nutzer und Authentifizierung
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    display_name    TEXT NOT NULL,
    password_hash   TEXT NOT NULL,
    encryption_key_enc TEXT NOT NULL,     -- User-spezifischer DEK, verschlüsselt mit KEK
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Verbundene Datenquellen
CREATE TABLE connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    source_type     TEXT NOT NULL,         -- GOOGLE_CALENDAR, NOTION, SLACK, ...
    status          TEXT NOT NULL DEFAULT 'active',  -- active, paused, error, revoked
    credentials_enc TEXT NOT NULL,         -- Verschlüsselte OAuth-Tokens
    watermark       TIMESTAMPTZ,           -- Letzter erfolgreicher Sync-Zeitpunkt
    config          JSONB DEFAULT '{}',    -- Quellenspezifische Konfiguration
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, source_type)
);

-- Dokumente (Metadaten; Inhalt liegt in Weaviate)
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    source_type     TEXT NOT NULL,
    source_id       TEXT NOT NULL,          -- ID im Quellsystem
    title           TEXT,
    content_hash    TEXT NOT NULL,          -- SHA-256 für Deduplizierung
    language        TEXT DEFAULT 'de',
    chunk_count     INT DEFAULT 0,
    processing_status TEXT DEFAULT 'pending',  -- pending, processing, done, error
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, source_type, source_id)
);

-- Chunks (Referenz zu Weaviate-Vektoren)
CREATE TABLE chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID REFERENCES documents(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    chunk_index     INT NOT NULL,
    token_count     INT NOT NULL,
    weaviate_id     UUID,                  -- Referenz zum Vektor in Weaviate
    content_preview TEXT,                  -- Erste 200 Zeichen (für Debug/Admin)
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Extrahierte Entitäten
CREATE TABLE entities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    entity_type     TEXT NOT NULL,         -- PERSON, PROJECT, TOPIC, DECISION
    name            TEXT NOT NULL,
    normalized_name TEXT NOT NULL,          -- Lowercased, dedupliziert
    metadata        JSONB DEFAULT '{}',
    first_seen      TIMESTAMPTZ DEFAULT now(),
    last_seen       TIMESTAMPTZ DEFAULT now(),
    mention_count   INT DEFAULT 1,
    neo4j_node_id   TEXT,                  -- Referenz zum Neo4j-Knoten
    UNIQUE(user_id, entity_type, normalized_name)
);

-- Entity-Chunk-Zuordnung (M:N)
CREATE TABLE entity_mentions (
    entity_id       UUID REFERENCES entities(id) ON DELETE CASCADE,
    chunk_id        UUID REFERENCES chunks(id) ON DELETE CASCADE,
    confidence      FLOAT DEFAULT 1.0,     -- Extraktions-Konfidenz
    extraction_method TEXT DEFAULT 'rule',  -- 'rule' | 'llm'
    PRIMARY KEY (entity_id, chunk_id)
);

-- Generierte Briefings
CREATE TABLE briefings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    briefing_type   TEXT NOT NULL,         -- MORNING, MEETING_PREP, PROJECT
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,          -- Generierter Inhalt (Markdown)
    source_chunks   UUID[] NOT NULL,       -- Referenzen zu verwendeten Chunks
    source_entities UUID[],                -- Referenzierte Entitäten
    trigger_context JSONB,                 -- Was hat das Briefing ausgelöst
    generated_at    TIMESTAMPTZ DEFAULT now(),
    expires_at      TIMESTAMPTZ            -- Briefings können ablaufen
);

-- Audit-Log (unveränderlich)
CREATE TABLE audit_log (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    action          TEXT NOT NULL,          -- data.ingested, briefing.generated, ...
    resource_type   TEXT,
    resource_id     UUID,
    metadata        JSONB DEFAULT '{}',
    ip_address      INET,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Indizes
CREATE INDEX idx_documents_user_status ON documents(user_id, processing_status);
CREATE INDEX idx_chunks_document ON chunks(document_id);
CREATE INDEX idx_entities_user_type ON entities(user_id, entity_type);
CREATE INDEX idx_audit_user_time ON audit_log(user_id, created_at DESC);
CREATE INDEX idx_briefings_user_type ON briefings(user_id, briefing_type, generated_at DESC);
```

#### 3.3.2 Weaviate – Vektordatenbank

Weaviate speichert die Embedding-Vektoren aller Chunks und ermöglicht semantische Suche.

**Collection-Schema:**

```json
{
  "class": "DocumentChunk",
  "description": "Embedding-Vektoren für Dokumenten-Chunks",
  "vectorizer": "none",
  "vectorIndexType": "hnsw",
  "vectorIndexConfig": {
    "efConstruction": 128,
    "maxConnections": 16,
    "ef": 64
  },
  "properties": [
    {
      "name": "chunkId",
      "dataType": ["uuid"],
      "description": "Referenz zur chunks-Tabelle in PostgreSQL"
    },
    {
      "name": "userId",
      "dataType": ["uuid"],
      "description": "Nutzer-ID für Tenant-Isolation"
    },
    {
      "name": "sourceType",
      "dataType": ["text"],
      "description": "Datenquellentyp"
    },
    {
      "name": "content",
      "dataType": ["text"],
      "description": "Chunk-Inhalt (für Hybrid-Suche mit BM25)"
    },
    {
      "name": "title",
      "dataType": ["text"],
      "description": "Dokumenttitel"
    },
    {
      "name": "createdAt",
      "dataType": ["date"],
      "description": "Erstellungszeitpunkt des Quelldokuments"
    },
    {
      "name": "language",
      "dataType": ["text"],
      "description": "Sprache des Chunks"
    }
  ],
  "multiTenancyConfig": {
    "enabled": true
  }
}
```

**Suchstrategie:** Hybrid-Suche (Vektor + BM25) mit konfigurierbarem Alpha-Parameter:
- `alpha=0.75` (Standard): 75% semantisch, 25% keyword-basiert
- Für exakte Suchterme (Projektnamen, Personennamen): `alpha=0.3`

**Tenant-Isolation:** Weaviate Multi-Tenancy ist aktiviert. Jeder Nutzer ist ein eigener Tenant. Keine Cross-User-Suchergebnisse möglich.

#### 3.3.3 Neo4j – Knowledge Graph

Neo4j speichert die Beziehungen zwischen extrahierten Entitäten und ermöglicht Kontextabfragen, die über reine Vektorähnlichkeit hinausgehen.

**Knotentypen (Labels):**

```
(:Person {
    id: UUID,
    userId: UUID,
    name: String,
    email: String?,
    role: String?,
    organization: String?,
    firstSeen: DateTime,
    lastSeen: DateTime,
    mentionCount: Int
})

(:Project {
    id: UUID,
    userId: UUID,
    name: String,
    status: String?,         // active, completed, paused, archived
    firstSeen: DateTime,
    lastSeen: DateTime
})

(:Topic {
    id: UUID,
    userId: UUID,
    name: String,
    category: String?,       // tech, business, personal, ...
    mentionCount: Int
})

(:Decision {
    id: UUID,
    userId: UUID,
    summary: String,
    decidedBy: String?,
    decidedAt: DateTime?,
    status: String?          // made, pending, revised
})

(:Meeting {
    id: UUID,
    userId: UUID,
    title: String,
    date: DateTime,
    sourceType: String,
    sourceId: String
})

(:Document {
    id: UUID,
    userId: UUID,
    title: String,
    sourceType: String,
    createdAt: DateTime
})
```

**Kantentypen (Relationships):**

```
(:Person)-[:PARTICIPATED_IN]->(:Meeting)
(:Person)-[:WORKS_ON]->(:Project)
(:Person)-[:MENTIONED_IN]->(:Document)
(:Person)-[:KNOWS]->(:Person)                  // Abgeleitet aus Co-Occurrence

(:Project)-[:HAS_TOPIC]->(:Topic)
(:Project)-[:HAS_DECISION]->(:Decision)

(:Decision)-[:DECIDED_IN]->(:Meeting)
(:Decision)-[:AFFECTS]->(:Project)
(:Decision)-[:SUPERSEDES]->(:Decision)         // Revidierte Entscheidungen

(:Meeting)-[:DISCUSSED]->(:Topic)
(:Meeting)-[:RELATES_TO]->(:Project)
(:Meeting)-[:PRODUCED]->(:Decision)

(:Document)-[:MENTIONS]->(:Person)
(:Document)-[:COVERS]->(:Topic)
(:Document)-[:REFERENCES]->(:Project)

(:Topic)-[:RELATED_TO]->(:Topic)               // Semantische Nähe
```

**Kantengewichtung:** Alle Kanten tragen eine `weight`-Property (Float, 0.0–1.0), die die Stärke der Beziehung abbildet. Das Gewicht steigt mit der Häufigkeit der Co-Occurrence und sinkt mit zeitlichem Abstand (Decay-Faktor).

**Beispielabfragen:**

```cypher
// Meeting-Vorbereitung: Alle relevanten Kontexte zu Teilnehmern
MATCH (p:Person)-[:PARTICIPATED_IN]->(m:Meeting)
WHERE m.date > datetime() AND m.userId = $userId
WITH p, m
OPTIONAL MATCH (p)-[:WORKS_ON]->(proj:Project)
OPTIONAL MATCH (p)-[:MENTIONED_IN]->(d:Document)
WHERE d.createdAt > datetime() - duration('P30D')
RETURN m.title, p.name, collect(DISTINCT proj.name) AS projects,
       collect(DISTINCT d.title)[0..5] AS recentDocs
ORDER BY m.date ASC

// Entscheidungshistorie eines Projekts
MATCH (proj:Project {name: $projectName, userId: $userId})
      <-[:AFFECTS]-(d:Decision)
OPTIONAL MATCH (d)-[:DECIDED_IN]->(m:Meeting)
RETURN d.summary, d.decidedAt, d.status, m.title
ORDER BY d.decidedAt DESC
```

### 3.4 LLM Orchestration Service

Der LLM Orchestration Service kapselt alle Interaktionen mit externen und lokalen Sprachmodellen.

#### Architektur

```
┌──────────────────────────────────────────────────┐
│            LLM Orchestration Service             │
│                                                  │
│  ┌─────────────────────┐  ┌───────────────────┐  │
│  │  Prompt Registry    │  │  Provider Router  │  │
│  │                     │  │                   │  │
│  │  - Templates        │  │  Claude (primär)  │  │
│  │  - Versionen        │  │  GPT-4 (Fallback) │  │
│  │  - Variablen        │  │  Ollama (lokal)   │  │
│  └─────────┬───────────┘  └────────┬──────────┘  │
│            │                       │              │
│  ┌─────────▼───────────────────────▼──────────┐  │
│  │         Request Pipeline                    │  │
│  │                                             │  │
│  │  1. Prompt Assembly (Template + Context)    │  │
│  │  2. Token Budget Check                      │  │
│  │  3. Provider Selection (primary/fallback)   │  │
│  │  4. API Call mit Retry + Timeout            │  │
│  │  5. Response Validation                     │  │
│  │  6. Source Attribution                      │  │
│  │  7. Confidence Scoring                      │  │
│  │  8. Cost & Latency Logging                  │  │
│  └─────────────────────────────────────────────┘  │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### Prompt-Management

Prompts werden als versionierte Templates gespeichert:

```python
@dataclass
class PromptTemplate:
    id: str                          # z.B. "briefing.morning.v3"
    template: str                    # Jinja2-Template mit Platzhaltern
    model_preference: str            # "claude-sonnet-4-20250514", "gpt-4o", ...
    max_output_tokens: int
    temperature: float
    system_prompt: str
    required_context: list[str]      # ["calendar_events", "recent_documents", ...]
    version: int
```

#### Halluzinations-Mitigation

| Maßnahme | Beschreibung |
|----------|-------------|
| **Grounded Generation** | Jeder LLM-Call enthält expliziten Kontext aus dem Knowledge Store. Der Prompt instruiert: „Antworte ausschließlich basierend auf den bereitgestellten Quellen." |
| **Quellenreferenzierung** | Jede generierte Aussage wird mit `[Quelle: {document_title}, {date}]` annotiert. Das Frontend rendert diese als klickbare Links. |
| **Confidence Scoring** | Wenn der generierte Text Aussagen enthält, die nicht direkt aus den Quellen ableitbar sind, wird ein Confidence-Indikator (`high` / `medium` / `low`) mit ausgegeben. |
| **Fakten/Interpretation-Trennung** | Prompts erzwingen eine strukturierte Ausgabe mit Abschnitten: `Fakten`, `Zusammenhänge`, `Empfehlungen` – jeweils mit Quellenangabe. |
| **Fallback-Kaskade** | Claude → GPT-4 → Cached Response → Fehlermeldung mit Rohdaten. Kein stiller Fehler, kein halluzinierter Fallback. |

#### Token-Budget-Management

```python
TOKEN_BUDGETS = {
    "briefing.morning": {
        "context_tokens": 8000,      # Max. Tokens für Kontext-Input
        "output_tokens": 2000,       # Max. Tokens für generierte Antwort
        "model": "claude-sonnet-4-20250514",
    },
    "search.answer": {
        "context_tokens": 6000,
        "output_tokens": 1500,
        "model": "claude-sonnet-4-20250514",
    },
    "entity.extraction": {
        "context_tokens": 2000,
        "output_tokens": 1000,
        "model": "claude-haiku",     # Günstiger für strukturierte Extraktion
    },
}
```

### 3.5 Briefing Engine

Die Briefing Engine orchestriert die Generierung kontextueller Briefings. Sie ist das zentrale Wertversprechen des MVP.

#### Trigger-Logik

```python
class BriefingTrigger:
    """Definiert wann und wie Briefings generiert werden."""

    TRIGGERS = {
        "morning": {
            "schedule": "0 6 * * *",         # Täglich, 06:00 Uhr (Nutzer-Timezone)
            "conditions": ["has_calendar_events_today", "has_recent_documents"],
        },
        "meeting_prep": {
            "schedule": None,                 # Event-basiert
            "trigger": "30min_before_meeting", # 30 Minuten vor Kalendereintrag
            "conditions": ["meeting_has_participants"],
        },
        "weekly_digest": {
            "schedule": "0 8 * * 1",          # Montags, 08:00 Uhr
            "conditions": ["has_activity_last_week"],
        },
    }
```

#### Kontextassemblierung (Morning Briefing)

```
1. Kalender-Events heute abrufen (Google Calendar Connector)
         │
         ▼
2. Für jeden Termin: Teilnehmer → Neo4j-Abfrage
   → Letzte Interaktionen, gemeinsame Projekte, offene Punkte
         │
         ▼
3. Semantische Suche in Weaviate:
   → Relevante Dokumente der letzten 7 Tage
   → Gefiltert nach Topics aus den heutigen Terminen
         │
         ▼
4. Offene Entscheidungen aus Neo4j:
   → Status "pending", sortiert nach Alter und Relevanz
         │
         ▼
5. Kontext in Prompt-Template einsetzen
   → Token-Budget prüfen (Kontext ggf. priorisieren/kürzen)
         │
         ▼
6. LLM-Call (Claude) → Strukturiertes Briefing generieren
         │
         ▼
7. Quellenreferenzen validieren
   → Jede Quellenangabe gegen DB prüfen
         │
         ▼
8. Briefing in PostgreSQL speichern + an Frontend pushen (WebSocket)
```

#### Output-Format

```markdown
# Morgenbriefing – Dienstag, 18. März 2026

## Dein Tag auf einen Blick
- 3 Termine, 2 davon mit externen Teilnehmern
- 1 offene Entscheidung wartet seit 5 Tagen

## Terminvorbereitung

### 10:00 – Produkt-Sync mit Team Alpha
**Teilnehmer:** Maria S., Thomas K., Lena W.
**Letzter Stand:** Im letzten Meeting (12.03.) wurde die API-Migration
besprochen. Thomas hatte offene Bedenken bzgl. Abwärtskompatibilität.
[Quelle: Meeting-Transkript, 12.03.2026]

**Offene Punkte:**
- Entscheidung zur Migrationsstrategie steht aus [Quelle: Notion, 13.03.]
- Lena hatte Testergebnisse versprochen [Quelle: Slack #alpha, 14.03.]

### 14:00 – Investoren-Update
**Teilnehmer:** Dr. Fischer (VC Partner)
**Kontext:** Letztes Gespräch am 28.02. – Thema war Runway und
Hiring-Plan. [Quelle: Kalender + Mail-Thread, 28.02.2026]
...

## Themen im Blick
- **API-Migration:** Seit 2 Wochen aktiv, noch keine finale Entscheidung
- **Hiring Backend:** 3 Kandidaten in Pipeline [Quelle: Notion HR-Board]

---
_Generiert am 18.03.2026, 06:00 | 12 Quellen verwendet_
```

### 3.6 API Layer

#### FastAPI-Routenübersicht

```python
# Routen-Struktur

app = FastAPI(title="PWBS API", version="0.1.0")

# ── Authentifizierung ──────────────────────────────────────────────
# POST   /api/v1/auth/register          Neuen Nutzer registrieren
# POST   /api/v1/auth/login             Login → JWT-Paar (access + refresh)
# POST   /api/v1/auth/refresh           Access-Token erneuern
# POST   /api/v1/auth/logout            Refresh-Token invalidieren
# GET    /api/v1/auth/me                Aktuelles Nutzerprofil

# ── Konnektoren ───────────────────────────────────────────────────
# GET    /api/v1/connectors/            Liste aller verfügbaren Konnektoren
# GET    /api/v1/connectors/status      Status aller verbundenen Quellen
# GET    /api/v1/connectors/{type}/auth-url   OAuth2-Auth-URL generieren
# POST   /api/v1/connectors/{type}/callback   OAuth2-Callback verarbeiten
# DELETE /api/v1/connectors/{type}      Verbindung trennen + Daten löschen
# POST   /api/v1/connectors/{type}/sync       Manuellen Sync auslösen

# ── Semantische Suche ─────────────────────────────────────────────
# POST   /api/v1/search/                Volltextsuche + semantische Suche
#   Body: { "query": str, "filters": {...}, "limit": int }
#   Response: { "results": [...], "answer": str?, "sources": [...] }

# ── Briefings ─────────────────────────────────────────────────────
# GET    /api/v1/briefings/             Liste der Briefings (paginiert)
# GET    /api/v1/briefings/latest       Letztes Briefing pro Typ
# GET    /api/v1/briefings/{id}         Einzelnes Briefing mit Quellen
# POST   /api/v1/briefings/generate     Briefing manuell auslösen
#   Body: { "type": "morning" | "meeting_prep" | "project", "context": {...} }
# DELETE /api/v1/briefings/{id}         Briefing löschen

# ── Knowledge Graph ───────────────────────────────────────────────
# GET    /api/v1/knowledge/entities     Entitäten auflisten (gefiltert)
# GET    /api/v1/knowledge/entities/{id}        Entität mit Verbindungen
# GET    /api/v1/knowledge/entities/{id}/related  Verwandte Entitäten
# GET    /api/v1/knowledge/graph        Subgraph für Visualisierung
#   Query: ?center={entity_id}&depth=2&limit=50

# ── Dokumente ─────────────────────────────────────────────────────
# GET    /api/v1/documents/             Dokumente auflisten (paginiert)
# GET    /api/v1/documents/{id}         Dokument-Metadaten + Chunks
# DELETE /api/v1/documents/{id}         Dokument löschen (kaskadiert)

# ── Admin / System ────────────────────────────────────────────────
# GET    /api/v1/admin/health           Health Check
# GET    /api/v1/admin/stats            Nutzungsstatistiken
# POST   /api/v1/admin/export           DSGVO-Datenexport (async)
# DELETE /api/v1/admin/account          Account + alle Daten löschen
```

#### Authentifizierung

```
JWT-basierte Authentifizierung mit OAuth2-kompatiblem Flow:

Access Token:  RS256-signiert, 15 Minuten Gültigkeit
Refresh Token: Opaque, 30 Tage Gültigkeit, in DB gespeichert (revokierbar)
Token Rotation: Bei jedem Refresh wird ein neues Refresh-Token ausgestellt,
                das alte wird invalidiert.

Für OAuth-Konnektoren:
- Die externen OAuth-Tokens (Google, Slack, Notion, Zoom) werden
  verschlüsselt in der connections-Tabelle gespeichert.
- Refresh-Logik für externe Tokens läuft automatisch im Hintergrund.
```

#### Middleware-Stack

```python
# Reihenfolge der Middleware (außen → innen)

1. CORSMiddleware          # Erlaubte Origins: Frontend-Domain
2. TrustedHostMiddleware   # Nur konfigurierte Hosts
3. RequestIDMiddleware     # Unique Request-ID für Tracing
4. RateLimitMiddleware     # Per-User Rate Limiting (Redis-backed)
5. AuthMiddleware          # JWT-Validierung, User-Kontext setzen
6. AuditMiddleware         # Alle schreibenden Ops loggen
7. EncryptionMiddleware    # Response-Verschlüsselung (bei Bedarf)
```

### 3.7 Frontend (Next.js)

#### App-Struktur

```
frontend/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── layout.tsx                # Root Layout mit Auth-Provider
│   │   ├── page.tsx                  # Landing / Redirect
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   ├── register/page.tsx
│   │   │   └── layout.tsx            # Auth-Layout (kein Sidebar)
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx            # Dashboard-Layout mit Sidebar + Header
│   │   │   ├── page.tsx              # Dashboard Home (→ aktuelles Briefing)
│   │   │   ├── briefings/
│   │   │   │   ├── page.tsx          # Briefing-Übersicht
│   │   │   │   └── [id]/page.tsx     # Einzelnes Briefing
│   │   │   ├── search/
│   │   │   │   └── page.tsx          # Semantische Suche
│   │   │   ├── knowledge/
│   │   │   │   ├── page.tsx          # Graph-Explorer
│   │   │   │   └── [entityId]/page.tsx  # Entitäts-Detailseite
│   │   │   ├── connectors/
│   │   │   │   └── page.tsx          # Datenquellen verwalten
│   │   │   └── settings/
│   │   │       └── page.tsx          # Nutzereinstellungen
│   │   └── api/                      # Next.js API Routes (BFF-Pattern)
│   │       └── auth/[...nextauth]/route.ts
│   ├── components/
│   │   ├── ui/                       # Basis-UI-Komponenten (Shadcn/ui)
│   │   ├── briefing/                 # Briefing-Card, Source-Badge, Timeline
│   │   ├── search/                   # Search-Input, Result-Card, SourceRef
│   │   ├── knowledge/                # Graph-Visualisierung, Entity-Card
│   │   ├── connectors/               # Connector-Card, OAuth-Button
│   │   └── layout/                   # Sidebar, Header, Navigation
│   ├── lib/
│   │   ├── api-client.ts             # Typisierter HTTP-Client (fetch-basiert)
│   │   ├── auth.ts                   # Token-Management, Refresh-Logik
│   │   └── utils.ts                  # Hilfsfunktionen
│   ├── hooks/
│   │   ├── use-briefings.ts          # SWR/React-Query Hook für Briefings
│   │   ├── use-search.ts             # Debounced Search Hook
│   │   ├── use-knowledge.ts          # Graph-Daten Hook
│   │   └── use-websocket.ts          # WebSocket für Echtzeit-Updates
│   ├── stores/
│   │   └── app-store.ts              # Zustand (globaler Client-State)
│   └── types/
│       └── api.ts                    # TypeScript-Typen aus OpenAPI-Schema
├── public/
├── next.config.ts
├── tailwind.config.ts
└── package.json
```

#### State-Management

```
Strategie: Server State + minimaler Client State

Server State (Daten vom Backend):
  → React Query (TanStack Query) für Caching, Refetching, Optimistic Updates
  → SWR-Pattern für Briefings: Stale-While-Revalidate mit 5 min Stale-Time
  → WebSocket-Updates invalidieren den Query-Cache gezielt

Client State (UI-State):
  → Zustand für globalen UI-State (Sidebar offen/zu, aktiver Filter, Theme)
  → React Context für Auth-State (JWT, User-Profil)
  → URL-State für Suche und Filter (Next.js searchParams)
```

#### Schlüssel-Interaktionen

```
Dashboard-Load:
  1. JWT aus Cookie prüfen (Middleware)
  2. Parallel: GET /briefings/latest + GET /connectors/status
  3. Briefing rendern mit Source-Badges
  4. WebSocket öffnen für Echtzeit-Briefing-Updates

Semantische Suche:
  1. Nutzer tippt Query (debounced, 300ms)
  2. POST /search/ mit Query + aktiven Filtern
  3. Backend: Weaviate Hybrid Search → Top-K Chunks
  4. Optional: LLM-generierte Zusammenfassung der Ergebnisse
  5. Frontend: Result-Cards mit Source-Links + Highlight

Knowledge Graph:
  1. GET /knowledge/graph?center={entityId}&depth=2
  2. D3.js Force-Directed Graph rendern
  3. Klick auf Knoten → Entity-Detail-Seitenleiste
  4. Drill-down: Verbundene Dokumente, Meetings, Entscheidungen
```

---

## 4. Datenfluss

### 4.1 Neue Datenquelle wird eingebunden (Onboarding-Flow)

```
Nutzer              Frontend           API              Connector         Processing       Storage
  │                    │                │                   │                 │               │
  │ Klickt "Notion     │                │                   │                 │               │
  │ verbinden"         │                │                   │                 │               │
  │───────────────────▶│                │                   │                 │               │
  │                    │ GET /connectors/│                   │                 │               │
  │                    │ notion/auth-url │                   │                 │               │
  │                    │───────────────▶│                   │                 │               │
  │                    │                │ Generiert OAuth    │                 │               │
  │                    │                │ URL mit Scopes     │                 │               │
  │                    │ Auth-URL       │                   │                 │               │
  │                    │◀───────────────│                   │                 │               │
  │ Redirect           │                │                   │                 │               │
  │◀───────────────────│                │                   │                 │               │
  │                    │                │                   │                 │               │
  │ ──── OAuth bei Notion (Consent) ──────────────────────▶│                 │               │
  │ ◀─── Redirect mit Auth-Code ──────────────────────────│                  │               │
  │                    │                │                   │                 │               │
  │───────────────────▶│ POST /callback │                   │                 │               │
  │                    │───────────────▶│                   │                 │               │
  │                    │                │ Code → Token      │                 │               │
  │                    │                │──────────────────▶│                 │               │
  │                    │                │                   │ Exchange        │               │
  │                    │                │ Token (encrypted) │ Code→Token     │               │
  │                    │                │◀──────────────────│                 │               │
  │                    │                │                   │                 │               │
  │                    │                │ INSERT connection │                 │               │
  │                    │                │ (status: active)  │                 │               │
  │                    │                │──────────────────────────────────────────────────▶│
  │                    │                │                   │                 │               │
  │                    │                │ Starte Initial    │                 │               │
  │                    │                │ Sync (Background) │                 │               │
  │                    │                │──────────────────▶│                 │               │
  │                    │                │                   │                 │               │
  │                    │ WS: "syncing"  │                   │ Fetch all pages │               │
  │ Progress-Anzeige   │◀──────────────│                   │ (paginated)     │               │
  │◀───────────────────│                │                   │                 │               │
  │                    │                │                   │                 │               │
  │                    │                │                   │ Normalize →     │               │
  │                    │                │                   │ UnifiedDocs     │               │
  │                    │                │                   │────────────────▶│               │
  │                    │                │                   │                 │               │
  │                    │                │                   │                 │ Für jedes     │
  │                    │                │                   │                 │ Dokument:     │
  │                    │                │                   │                 │ 1. Chunk      │
  │                    │                │                   │                 │ 2. Embed      │
  │                    │                │                   │                 │ 3. Extract    │
  │                    │                │                   │                 │ 4. Graph-Build│
  │                    │                │                   │                 │───────────▶│  │
  │                    │                │                   │                 │  Write to  │  │
  │                    │                │                   │                 │  PG + Weav │  │
  │                    │                │                   │                 │  + Neo4j   │  │
  │                    │                │                   │                 │               │
  │                    │                │ UPDATE connection │                 │               │
  │                    │                │ (watermark=now)   │                 │               │
  │                    │                │──────────────────────────────────────────────────▶│
  │                    │                │                   │                 │               │
  │                    │ WS: "complete" │                   │                 │               │
  │ "Notion verbunden" │◀──────────────│                   │                 │               │
  │ (42 Seiten sync.)  │                │                   │                 │               │
  │◀───────────────────│                │                   │                 │               │
```

### 4.2 Morgenbriefing wird generiert (täglicher Trigger-Flow)

```
Scheduler          Briefing Engine        Storage (PG/Weav/Neo4j)      LLM Service      Frontend
  │                      │                         │                       │               │
  │ CRON: 06:00 UTC+1    │                         │                       │               │
  │─────────────────────▶│                         │                       │               │
  │                      │                         │                       │               │
  │                      │ 1. Kalender-Events      │                       │               │
  │                      │    heute abrufen         │                       │               │
  │                      │────────────────────────▶│                       │               │
  │                      │ Events + Teilnehmer     │                       │               │
  │                      │◀────────────────────────│                       │               │
  │                      │                         │                       │               │
  │                      │ 2. Für jeden Teilnehmer:│                       │               │
  │                      │    Graph-Kontext holen   │                       │               │
  │                      │────────────────────────▶│                       │               │
  │                      │ Projekte, letzte Mtgs,  │                       │               │
  │                      │ offene Entscheidungen   │                       │               │
  │                      │◀────────────────────────│                       │               │
  │                      │                         │                       │               │
  │                      │ 3. Relevante Dokumente  │                       │               │
  │                      │    (letzte 7 Tage)      │                       │               │
  │                      │ Semantic Search          │                       │               │
  │                      │────────────────────────▶│                       │               │
  │                      │ Top-20 Chunks           │                       │               │
  │                      │◀────────────────────────│                       │               │
  │                      │                         │                       │               │
  │                      │ 4. Kontext assemblieren  │                       │               │
  │                      │    Token-Budget prüfen   │                       │               │
  │                      │    Prompt bauen          │                       │               │
  │                      │                         │                       │               │
  │                      │ 5. LLM-Call             │                       │               │
  │                      │─────────────────────────────────────────────▶│               │
  │                      │                         │                       │               │
  │                      │ Strukturiertes Briefing  │                       │               │
  │                      │ (Markdown + Source-Refs) │                       │               │
  │                      │◀─────────────────────────────────────────────│               │
  │                      │                         │                       │               │
  │                      │ 6. Quellenreferenzen    │                       │               │
  │                      │    validieren           │                       │               │
  │                      │────────────────────────▶│                       │               │
  │                      │ Alle Referenzen gültig  │                       │               │
  │                      │◀────────────────────────│                       │               │
  │                      │                         │                       │               │
  │                      │ 7. Briefing speichern   │                       │               │
  │                      │────────────────────────▶│                       │               │
  │                      │                         │                       │               │
  │                      │ 8. WebSocket Push       │                       │               │
  │                      │─────────────────────────────────────────────────────────────▶│
  │                      │                         │                       │               │
  │                      │                         │                       │  Notification │
  │                      │                         │                       │  + Auto-Reload│
```

### 4.3 Nutzer stellt semantische Suchanfrage (Query-Flow)

```
Nutzer               Frontend              API                  Weaviate      Neo4j       LLM
  │                     │                    │                      │            │           │
  │ Tippt: "Was wurde   │                    │                      │            │           │
  │ zur API-Migration    │                    │                      │            │           │
  │ entschieden?"        │                    │                      │            │           │
  │────────────────────▶│                    │                      │            │           │
  │                     │ Debounce 300ms     │                      │            │           │
  │                     │                    │                      │            │           │
  │                     │ POST /search/      │                      │            │           │
  │                     │ {query, limit: 10} │                      │            │           │
  │                     │───────────────────▶│                      │            │           │
  │                     │                    │                      │            │           │
  │                     │                    │ 1. Query Embedding   │            │           │
  │                     │                    │    generieren        │            │           │
  │                     │                    │                      │            │           │
  │                     │                    │ 2. Hybrid Search     │            │           │
  │                     │                    │────────────────────▶│            │           │
  │                     │                    │ Top-K Chunks         │            │           │
  │                     │                    │ (mit Score)          │            │           │
  │                     │                    │◀────────────────────│            │           │
  │                     │                    │                      │            │           │
  │                     │                    │ 3. Entitäten aus     │            │           │
  │                     │                    │    Chunks extrahieren│            │           │
  │                     │                    │    → Graph-Kontext   │            │           │
  │                     │                    │─────────────────────────────────▶│           │
  │                     │                    │ Verwandte Entitäten, │            │           │
  │                     │                    │ Entscheidungen       │            │           │
  │                     │                    │◀─────────────────────────────────│           │
  │                     │                    │                      │            │           │
  │                     │                    │ 4. Kontext           │            │           │
  │                     │                    │    assemblieren      │            │           │
  │                     │                    │                      │            │           │
  │                     │                    │ 5. LLM: Antwort     │            │           │
  │                     │                    │    generieren        │            │           │
  │                     │                    │─────────────────────────────────────────────▶│
  │                     │                    │                      │            │           │
  │                     │                    │ Antwort mit          │            │           │
  │                     │                    │ Quellenreferenzen    │            │           │
  │                     │                    │◀─────────────────────────────────────────────│
  │                     │                    │                      │            │           │
  │                     │ Response:          │                      │            │           │
  │                     │ {                  │                      │            │           │
  │                     │   answer: "...",   │                      │            │           │
  │                     │   sources: [...],  │                      │            │           │
  │                     │   entities: [...], │                      │            │           │
  │                     │   confidence: 0.87 │                      │            │           │
  │                     │ }                  │                      │            │           │
  │                     │◀───────────────────│                      │            │           │
  │                     │                    │                      │            │           │
  │ Antwort mit         │                    │                      │            │           │
  │ klickbaren Quellen  │                    │                      │            │           │
  │◀────────────────────│                    │                      │            │           │
```

---

## 5. Datenschutz & Sicherheit

### 5.1 Verschlüsselungsstrategie

#### At Rest

```
Encryption-at-Rest: Envelope-Encryption-Schema

┌─────────────────────────────────────────────────────────┐
│                    Key Hierarchy                         │
│                                                         │
│  ┌──────────────────┐                                   │
│  │   Master Key     │  AWS KMS (oder lokal via          │
│  │   (KEK)          │  PBKDF2 aus Nutzer-Passphrase)    │
│  └────────┬─────────┘                                   │
│           │ verschlüsselt                               │
│           ▼                                             │
│  ┌──────────────────┐                                   │
│  │  User Data Key   │  Pro Nutzer ein eigener DEK       │
│  │  (DEK)           │  Gespeichert als encryption_key_  │
│  │                  │  enc in users-Tabelle (AES-256)   │
│  └────────┬─────────┘                                   │
│           │ verschlüsselt                               │
│           ▼                                             │
│  ┌──────────────────┐                                   │
│  │  Nutzerdaten     │  OAuth-Tokens, Dokument-Inhalte,  │
│  │                  │  Briefings, Entity-Metadaten       │
│  └──────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
```

| Komponente | Verschlüsselung | Details |
|-----------|-----------------|---------|
| **PostgreSQL** | AES-256 (AWS RDS Encryption) + Spalten-Ebene für Credentials | OAuth-Tokens werden zusätzlich mit dem User-DEK verschlüsselt, bevor sie in die DB geschrieben werden |
| **Weaviate** | Volume Encryption (AWS EBS Encryption) | Chunk-Inhalte werden im Klartext indexiert (für BM25-Suche). Trade-off: Vektorsuche erfordert unverschlüsselte Vektoren. Mitigation: Tenant-Isolation + Netzwerkisolation |
| **Neo4j** | Volume Encryption (AWS EBS Encryption) | Graph-Daten im Klartext für Query-Performance. Mitigation: Netzwerkisolation, kein externer Zugriff |
| **Redis** | AWS ElastiCache Encryption at Rest | Session-Tokens, Rate-Limit-Counter |
| **Backups** | AES-256-GCM, separate Backup-Keys | Backups sind unabhängig von User-DEKs verschlüsselt |

#### In Transit

| Verbindung | Protokoll | Details |
|-----------|-----------|---------|
| Client → Frontend | TLS 1.3 | Vercel Edge, automatische Zertifikate |
| Frontend → API | TLS 1.3 | ALB/API Gateway, AWS Certificate Manager |
| API → Datenbanken | TLS 1.2+ | Private Subnets, Security Groups, erzwungenes TLS |
| API → LLM-Provider | TLS 1.3 | Claude API / OpenAI API |
| Webhook-Ingress | TLS 1.3 + Signature Verification | HMAC-Validierung für Slack/Notion/Zoom Webhooks |

### 5.2 DSGVO-Maßnahmen

| Anforderung | Umsetzung |
|-------------|-----------|
| **Auskunftsrecht (Art. 15)** | `POST /api/v1/admin/export` – Generiert ein vollständiges JSON-Exportpaket aller Nutzerdaten (Dokumente, Entitäten, Briefings, Audit-Log). Async mit Download-Link. |
| **Recht auf Löschung (Art. 17)** | `DELETE /api/v1/admin/account` – Kaskadierte Löschung: PostgreSQL (CASCADE), Weaviate (Tenant löschen), Neo4j (alle Knoten mit userId), Redis (Session-Flush). Irreversibel nach 30-Tage-Karenz. |
| **Datenportabilität (Art. 20)** | Export im maschinenlesbaren Format (JSON + Markdown). Alle Rohquellen, extrahierten Entitäten und generierten Briefings. |
| **Datenminimierung (Art. 5)** | Nur Daten speichern, die für die Kernfunktion benötigt werden. E-Mail-Body wird nach Chunk-Erstellung nicht im Klartext vorgehalten (nur Chunks + Embeddings). |
| **Zweckbindung** | Nutzerdaten werden ausschließlich für die persönlichen Briefings und Suche des jeweiligen Nutzers verwendet. Kein Cross-User-Lernen, kein Training externer Modelle. |
| **Einwilligungsmanagement** | Pro Datenquelle explizite Einwilligung (OAuth-Consent). Jederzeit widerrufbar. Widerruf löscht alle Daten dieser Quelle. |
| **Auftragsverarbeitung** | AVVs mit AWS, OpenAI/Anthropic, Vercel. Dokumentiert in `/legal/avv/`. |
| **Privacy by Design** | Tenant-Isolation in allen Storage-Schichten. Keine shared Embedding-Spaces. Keine globalen Indizes über Nutzergrenzen. |

### 5.3 Datenresidenz

| Modus | Beschreibung | Datenstandort |
|-------|-------------|---------------|
| **Cloud (Standard)** | Alle Services auf AWS eu-central-1 (Frankfurt) | Deutschland/EU |
| **Cloud (DSGVO Strict)** | Kein LLM-Call an US-Provider; nur EU-basierte LLMs oder lokale Modelle | EU only |
| **On-Premise (Phase 4+)** | Docker-Compose-Setup auf kundeneigener Infrastruktur | Kundenbestimmt |
| **Hybrid** | Storage on-premise, LLM-Calls in die Cloud (mit Anonymisierung) | Gemischt |

### 5.4 Zugriffskontrolle

```
Schicht 1: Netzwerk
  → VPC mit privaten Subnets für alle Datenbanken
  → Security Groups: Nur API-Service darf auf DBs zugreifen
  → Kein direkter Internet-Zugang für DB-Instanzen

Schicht 2: Anwendung
  → JWT-basierte Authentifizierung für alle API-Endpoints
  → User-ID aus JWT wird in jede DB-Query injiziert (Row-Level-Isolation)
  → Weaviate Multi-Tenancy: physische Tenant-Isolation

Schicht 3: Daten
  → Envelope Encryption mit per-User Keys
  → OAuth-Tokens: Doppelt verschlüsselt (DB-Level + App-Level)
  → Audit-Log: Append-only, nicht löschbar (außer bei Account-Deletion)

Schicht 4: Betrieb
  → Infrastruktur-Zugriff via IAM Roles (kein root-Zugang)
  → SSH/SSM nur über Bastion Host
  → Alle Admin-Aktionen geloggt in CloudTrail
```

### 5.5 Audit-Logging

Jede datenschutzrelevante Aktion wird im `audit_log` protokolliert:

```python
AUDIT_EVENTS = [
    "user.registered",
    "user.logged_in",
    "user.logged_out",
    "user.deleted",
    "connection.created",         # Datenquelle verbunden
    "connection.revoked",         # Datenquelle getrennt
    "data.ingested",              # Neue Daten importiert
    "data.deleted",               # Daten gelöscht
    "briefing.generated",         # Briefing erzeugt
    "search.executed",            # Suche durchgeführt
    "export.requested",           # DSGVO-Export angefordert
    "llm.called",                 # LLM-API-Call (Prompt-Hash, nicht Inhalt)
    "admin.accessed",             # Admin-Endpoint aufgerufen
]
```

Retention: 12 Monate (konfigurierbar). Logs werden nach Ablauf archiviert (S3 Glacier) oder gelöscht.

---

## 6. Skalierungsstrategie

### 6.1 Bottleneck-Analyse

| Komponente | Kritischer Pfad | Bottleneck bei | Mitigation |
|-----------|-----------------|----------------|------------|
| **Embedding-Generierung** | Initial Sync einer großen Notion-DB (1000+ Seiten) | ~50ms/Chunk × tausende Chunks = Minuten | Batch-API, parallele Workers, lokale Fallback-Modelle |
| **LLM-Calls (Briefings)** | Morgenbriefing für viele Nutzer gleichzeitig um 06:00 | API Rate Limits, Latenz ~2-5s/Call | Zeitversetzte Generation (±15 min Jitter), Caching, Pre-Generation |
| **Weaviate Search** | Parallele Suchanfragen vieler Nutzer | Memory (HNSW lädt in RAM), CPU für BM25 | Vertikale Skalierung (RAM), Sharding ab Phase 4 |
| **Neo4j Queries** | Tiefe Graph-Traversals (depth > 3) | CPU, Disk I/O bei großen Graphen | Query-Timeouts, Ergebnis-Limits, Caching häufiger Patterns |
| **PostgreSQL** | Concurrent Writes bei hohem Ingestion-Volumen | Connection Pool, Write-Throughput | PgBouncer, Read-Replicas, ggf. Partitioning der documents-Tabelle |

### 6.2 Horizontale Skalierung

```
MVP (Phase 2):                    Phase 3-4:                     Phase 5:
Modularer Monolith                Service-Split                  Microservices

┌──────────────┐           ┌──────────────┐                ┌──────────────┐
│   FastAPI     │           │ API Gateway  │                │ API Gateway  │
│   (2 Tasks)   │           │     (ALB)    │                │    (ALB)     │
│               │           └──────┬───────┘                └──────┬───────┘
│ - API         │                  │                               │
│ - Ingestion   │           ┌──────┼──────────┐            ┌──────┼───────────────┐
│ - Processing  │           │      │          │            │      │      │        │
│ - Briefing    │           ▼      ▼          ▼            ▼      ▼      ▼        ▼
│ - Search      │       ┌──────┐┌──────┐ ┌────────┐   ┌──────┐┌────┐┌──────┐┌────────┐
└──────────────┘       │ API  ││Ingest││ Process. │   │ API  ││Ing.││Brief.││Search  │
                       │Server││Worker││ Worker   │   │  ×3  ││ ×N ││ ×2   ││  ×2    │
                       └──────┘└──┬───┘└────┬─────┘   └──────┘└──┬─┘└──────┘└────────┘
                                  │         │                     │
                                  ▼         ▼                     ▼
                           ┌──────────────────┐           ┌──────────────────┐
                           │   Message Queue  │           │   Message Queue  │
                           │  (Redis/Celery)  │           │   (AWS SQS)      │
                           └──────────────────┘           └──────────────────┘
```

### 6.3 Queue-System

**MVP (Phase 2):** FastAPI Background Tasks (in-process, keine externe Queue).

**Phase 3+:** Celery + Redis als Message Broker.

```python
# Queue-Topologie (Phase 3+)

QUEUES = {
    "ingestion.high": {
        "description": "Webhook-getriggerte Echtzeit-Syncs",
        "workers": 2,
        "priority": "high",
        "timeout": 300,       # 5 Minuten
    },
    "ingestion.bulk": {
        "description": "Initial-Syncs und Backfills",
        "workers": 4,
        "priority": "low",
        "timeout": 3600,      # 1 Stunde
    },
    "processing.embed": {
        "description": "Embedding-Generierung",
        "workers": 2,
        "priority": "medium",
        "timeout": 600,
    },
    "processing.extract": {
        "description": "LLM-basierte Entitätsextraktion",
        "workers": 2,
        "priority": "medium",
        "timeout": 120,
    },
    "briefing.generate": {
        "description": "Briefing-Generierung",
        "workers": 2,
        "priority": "high",
        "timeout": 60,
    },
}
```

### 6.4 Caching-Strategie

| Cache-Layer | Technologie | Was wird gecacht | TTL |
|------------|-------------|------------------|-----|
| **API Response Cache** | Redis | Briefing-Responses, Connector-Status | 5 min |
| **Search Result Cache** | Redis | Query-Hash → Ergebnis (Top-K Chunk-IDs) | 10 min |
| **Embedding Cache** | Redis | Content-Hash → Embedding-Vektor | 24h |
| **LLM Response Cache** | Redis | Prompt-Hash → LLM-Response | 1h (Briefings), 24h (Extraktion) |
| **Graph Query Cache** | In-Process (LRU) | Häufige Neo4j-Patterns (z.B. Meeting-Prep) | 15 min |
| **Static Assets** | Vercel Edge / CloudFront | JS, CSS, Bilder | 1 Jahr (versioned) |

### 6.5 Multi-Tenancy (Phase 4+)

```
Isolation-Strategie:

Logische Isolation (MVP – Phase 3):
  → user_id in jeder Tabelle, jeder Query
  → Weaviate Multi-Tenancy (Tenant pro User)
  → Neo4j: userId-Property auf allen Knoten

Physische Isolation (Phase 4+ für Enterprise):
  → Dedizierte Datenbank-Instanzen pro Tenant/Organisation
  → Eigene Weaviate-Cluster
  → Separater Neo4j-Instance
  → Deployment via Helm-Chart mit Tenant-Konfiguration

Team-Features (Phase 4):
  → Shared Knowledge Space: Nutzer einer Organisation teilen einen
    gemeinsamen Weaviate-Tenant und Neo4j-Subgraph
  → Zugriffskontrolle: Rollenbasiert (Owner, Member, Viewer)
  → Private vs. Shared Entities: Nutzer können Entitäten als
    "persönlich" oder "team-sichtbar" markieren
```

---

## 7. Entscheidungsprotokoll (ADR-Tabelle)

| # | Entscheidung | Alternativen | Begründung | Trade-offs |
|---|-------------|-------------|------------|------------|
| ADR-001 | **Python/FastAPI als Backend** | Node.js/Express, Go/Gin, Rust/Actix | Python-Ökosystem für ML/NLP unübertroffen (Sentence Transformers, LangChain, spaCy). FastAPI bietet async, automatische OpenAPI-Docs, Pydantic-Validierung. Team-Expertise vorhanden. | Höhere Latenz als Go/Rust bei reinen I/O-Operationen. Mitigiert durch async und horizontale Skalierung. |
| ADR-002 | **PostgreSQL als primäre DB** | MySQL, MongoDB, CockroachDB | JSONB für flexible Metadaten, starke Transaktionsgarantien, bewährtes Ökosystem (pgvector als Backup falls Weaviate ausfällt), hervorragendes Tooling. | Kein natives horizontales Sharding. Mitigiert durch Read-Replicas und ggf. Citus für Phase 5. |
| ADR-003 | **Weaviate als Vektor-DB** | Pinecone, Qdrant, Milvus, pgvector | Open-Source, Self-Hosting möglich (kritisch für On-Premise-Option), native Hybrid-Suche (Vektor + BM25), Multi-Tenancy, aktive Community. | Höherer Betriebsaufwand als Pinecone (managed). Mitigiert: Weaviate Cloud als Option für Cloud-Deployment. |
| ADR-004 | **Neo4j als Graph-DB** | TigerGraph, Amazon Neptune, TerminusDB | Cypher als ausdrucksstarke Query-Sprache, größte Community, ausgereifte Tooling-Landschaft (Browser, Bloom), Python-Driver stabil. Self-Hosting möglich. | Hoher RAM-Bedarf bei großen Graphen. Community Edition hat keine Cluster-Fähigkeit. Mitigiert: Neo4j Aura als managed Option, Enterprise Edition für Phase 5. |
| ADR-005 | **Claude API als primärer LLM** | GPT-4 only, Open-Source only (Llama/Mistral), Multi-Provider ab Start | Starke strukturierte Output-Fähigkeit, großes Kontextfenster (200K Tokens), gute Compliance-Positionierung (Anthropic). GPT-4 als Fallback verhindert Vendor Lock-in. | Abhängigkeit von US-basiertem Provider. Mitigiert: Ollama als lokale Option, Abstraktion über LLM-Orchestration-Service ermöglicht Provider-Wechsel. |
| ADR-006 | **Modularer Monolith statt Microservices (MVP)** | Microservices ab Start, Serverless Functions | 2–5 Entwickler können einen Monolithen schneller iterieren. Keine Overhead durch Service-Mesh, distributed Tracing, API-Contracts zwischen Services. Modul-Grenzen im Code erzwingen Separation of Concerns. | Späterer Service-Split erfordert Refactoring. Mitigiert: Module kommunizieren über definierte Python-Interfaces, nicht über globalen State. |
| ADR-007 | **Next.js auf Vercel (Frontend)** | SPA (Vite + React), Remix, SvelteKit | SSR für SEO (Marketing-Pages), Edge Functions für Auth, exzellente DX (Hot Reload, Preview Deployments), App Router + Server Components. Vercel: Zero-Config-Deployment. | Vendor Lock-in bei Vercel (mitigiert: Next.js läuft auch auf Docker/Node). Server Components erfordern Lernkurve. |
| ADR-008 | **Tauri statt Electron (Desktop-App, Phase 3+)** | Electron, Progressive Web App | Deutlich kleinere Binary (~10 MB vs. ~150 MB Electron). Geringerer Speicherverbrauch. Rust-Backend ermöglicht lokale Verschlüsselung und Vault-Zugriff ohne Node.js. | Kleineres Ökosystem als Electron, weniger Plugins. Mitigiert: Desktop-App nutzt das gleiche Web-Frontend (WebView), nur der System-Layer ist Tauri/Rust. |
| ADR-009 | **Envelope Encryption mit per-User-Keys** | Applikations-Level Encryption nur, DB-Level-Encryption only, Zero-Knowledge-Architektur | Balance zwischen Sicherheit und Funktionalität. Per-User-Keys ermöglichen Account-Löschung ohne Gesamt-Re-Encryption. AWS KMS als KEK vermeidet Key-Management-Komplexität. | Weaviate-Vektoren liegen unverschlüsselt im Index (notwendig für Suche). Mitigiert: Netzwerkisolation + Tenant-Separation. Zero-Knowledge wäre sicherer, verhindert aber serverseitige Suche und Briefing-Generierung. |
| ADR-010 | **Hybrid-Suche (Vektor + BM25) statt reiner Vektorsuche** | Pure Vector Search, Pure Keyword Search, Elasticsearch | Vektorsuche allein hat Schwächen bei exakten Eigennamen und Fachbegriffen. BM25 ergänzt durch exakte Matches. Weaviate bietet beides nativ mit konfigurierbarem Alpha. | Erhöhte Indexing-Kosten (zwei Indizes pro Collection). Mitigiert: Marginal bei der erwarteten Datenmenge im MVP. |
| ADR-011 | **Celery + Redis statt AWS SQS (Phase 3)** | AWS SQS + Lambda, RabbitMQ, Kafka | Celery ist Python-nativ, exzellent dokumentiert, und Redis wird bereits für Caching genutzt. Hält die Infrastruktur-Komplexität niedrig. Migrierbar zu SQS in Phase 5, falls nötig. | Redis als Broker ist weniger resilient als SQS (Nachrichten bei Redis-Crash verloren). Mitigiert: Redis-Persistenz (AOF), kritische Jobs werden in PostgreSQL als Fallback geloggt. |
| ADR-012 | **React Query statt Redux/Zustand für Server-State** | Redux Toolkit + RTK Query, Zustand für alles, Apollo Client | Server-State und Client-State haben grundverschiedene Anforderungen. React Query optimiert Caching, Refetching, Stale-While-Revalidate. Zustand nur für UI-State (minimal). | Zwei State-Libraries statt einer. Mitigiert: klare Trennung der Verantwortlichkeiten, weniger Boilerplate als Redux. |

---

## 8. Entwicklungs- und Deployment-Setup

### 8.1 Lokale Entwicklungsumgebung

#### Docker Compose

```yaml
# docker-compose.yml (vereinfacht)

services:
  # ── Backend ────────────────────────────────────────
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      - DATABASE_URL=postgresql://pwbs:pwbs_dev@postgres:5432/pwbs
      - WEAVIATE_URL=http://weaviate:8080
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=dev_password
      - REDIS_URL=redis://redis:6379/0
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ENCRYPTION_MASTER_KEY=${ENCRYPTION_MASTER_KEY}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENVIRONMENT=development
    depends_on:
      postgres:
        condition: service_healthy
      weaviate:
        condition: service_healthy
      neo4j:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # ── Datenbanken ────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: pwbs
      POSTGRES_USER: pwbs
      POSTGRES_PASSWORD: pwbs_dev
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/migrations/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pwbs"]
      interval: 5s
      timeout: 5s
      retries: 5

  weaviate:
    image: semitechnologies/weaviate:1.28.2
    ports:
      - "8080:8080"
      - "50051:50051"    # gRPC
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
      PERSISTENCE_DATA_PATH: "/var/lib/weaviate"
      DEFAULT_VECTORIZER_MODULE: "none"
      CLUSTER_HOSTNAME: "node1"
    volumes:
      - weaviate_data:/var/lib/weaviate
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/v1/.well-known/ready"]
      interval: 5s
      timeout: 5s
      retries: 5

  neo4j:
    image: neo4j:5.26-community
    ports:
      - "7474:7474"    # Browser
      - "7687:7687"    # Bolt
    environment:
      NEO4J_AUTH: neo4j/dev_password
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "neo4j", "status"]
      interval: 10s
      timeout: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # ── Frontend ───────────────────────────────────────
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    command: npm run dev

volumes:
  postgres_data:
  weaviate_data:
  neo4j_data:
  redis_data:
```

#### Lokaler Startup

```bash
# 1. Repository klonen
git clone git@github.com:org/pwbs.git && cd pwbs

# 2. Umgebungsvariablen kopieren
cp .env.example .env
# → API-Keys (Claude, OpenAI) eintragen

# 3. Alles starten
docker compose up -d

# 4. Datenbank-Migrationen
docker compose exec api alembic upgrade head

# 5. Weaviate-Schema initialisieren
docker compose exec api python -m app.scripts.init_weaviate

# 6. Neo4j-Constraints erstellen
docker compose exec api python -m app.scripts.init_neo4j

# 7. Frontend öffnen
open http://localhost:3000

# 8. API-Docs öffnen
open http://localhost:8000/docs
```

### 8.2 Projektstruktur

```
pwbs/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI-App, Router-Montage
│   │   ├── config.py                  # Pydantic Settings
│   │   ├── dependencies.py            # DI: DB-Sessions, Auth, Services
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── connectors.py
│   │   │   │   ├── search.py
│   │   │   │   ├── briefings.py
│   │   │   │   ├── knowledge.py
│   │   │   │   ├── documents.py
│   │   │   │   └── admin.py
│   │   │   └── middleware/
│   │   │       ├── auth.py
│   │   │       ├── rate_limit.py
│   │   │       ├── request_id.py
│   │   │       └── audit.py
│   │   ├── connectors/                # Ingestion Layer
│   │   │   ├── base.py                # BaseConnector ABC
│   │   │   ├── google_calendar.py
│   │   │   ├── notion.py
│   │   │   ├── obsidian.py
│   │   │   ├── zoom.py
│   │   │   ├── slack.py
│   │   │   ├── gmail.py
│   │   │   └── registry.py            # Connector Registry
│   │   ├── processing/                # Processing Layer
│   │   │   ├── chunking.py
│   │   │   ├── embedding.py
│   │   │   ├── extraction.py          # NER / Entity Extraction
│   │   │   ├── graph_builder.py
│   │   │   └── pipeline.py            # Pipeline-Orchestrierung
│   │   ├── services/                  # Business Logic
│   │   │   ├── briefing_engine.py
│   │   │   ├── search_service.py
│   │   │   ├── knowledge_service.py
│   │   │   ├── llm_orchestrator.py
│   │   │   └── encryption_service.py
│   │   ├── models/                    # SQLAlchemy Models
│   │   │   ├── user.py
│   │   │   ├── connection.py
│   │   │   ├── document.py
│   │   │   ├── chunk.py
│   │   │   ├── entity.py
│   │   │   ├── briefing.py
│   │   │   └── audit.py
│   │   ├── schemas/                   # Pydantic Schemas (Request/Response)
│   │   │   ├── auth.py
│   │   │   ├── connector.py
│   │   │   ├── search.py
│   │   │   ├── briefing.py
│   │   │   ├── knowledge.py
│   │   │   └── document.py
│   │   ├── db/
│   │   │   ├── postgres.py            # AsyncSession, Engine
│   │   │   ├── weaviate_client.py
│   │   │   ├── neo4j_client.py
│   │   │   └── redis_client.py
│   │   ├── prompts/                   # LLM Prompt Templates
│   │   │   ├── briefing_morning.jinja2
│   │   │   ├── briefing_meeting.jinja2
│   │   │   ├── search_answer.jinja2
│   │   │   └── entity_extraction.jinja2
│   │   └── scripts/
│   │       ├── init_weaviate.py
│   │       └── init_neo4j.py
│   ├── migrations/                    # Alembic
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_connectors/
│   │   ├── test_processing/
│   │   ├── test_services/
│   │   └── test_api/
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   ├── pyproject.toml
│   └── requirements.lock
├── frontend/
│   ├── src/                           # (Struktur siehe Abschnitt 3.7)
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   ├── package.json
│   └── tsconfig.json
├── infra/                             # Infrastructure as Code
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── modules/
│   │   │   ├── networking/            # VPC, Subnets, Security Groups
│   │   │   ├── ecs/                   # Fargate Cluster, Task Definitions
│   │   │   ├── rds/                   # PostgreSQL
│   │   │   ├── ec2_weaviate/          # Weaviate auf EC2
│   │   │   ├── ec2_neo4j/             # Neo4j auf EC2
│   │   │   ├── elasticache/           # Redis
│   │   │   ├── kms/                   # Verschlüsselungskeys
│   │   │   └── monitoring/            # CloudWatch, Alarms
│   │   └── environments/
│   │       ├── staging.tfvars
│   │       └── production.tfvars
│   └── docker/
│       └── docker-compose.prod.yml
├── docs/
│   ├── ARCHITECTURE.md                # dieses Dokument
│   ├── API.md
│   └── ONBOARDING.md
├── legal/
│   └── avv/                           # Auftragsverarbeitungsverträge
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── deploy-staging.yml
│       └── deploy-production.yml
├── docker-compose.yml
├── .env.example
└── README.md
```

### 8.3 CI/CD-Strategie

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions Pipeline                       │
│                                                                 │
│  Push / PR auf main:                                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │   Lint &   │  │   Unit     │  │ Integration│                │
│  │  Typecheck │─▶│   Tests    │─▶│   Tests    │                │
│  │            │  │            │  │ (Testcont.)│                │
│  │ - ruff     │  │ - pytest   │  │ - PG, Weav │                │
│  │ - mypy     │  │ - vitest   │  │ - Neo4j    │                │
│  │ - eslint   │  │            │  │            │                │
│  │ - tsc      │  │            │  │            │                │
│  └────────────┘  └────────────┘  └────────────┘                │
│                                        │                        │
│                                        ▼ (nur main)            │
│                               ┌────────────────┐               │
│                               │  Docker Build  │               │
│                               │  & Push to ECR │               │
│                               └───────┬────────┘               │
│                                       │                        │
│                            ┌──────────▼──────────┐             │
│                            │  Deploy Staging     │             │
│                            │  (auto)             │             │
│                            └──────────┬──────────┘             │
│                                       │                        │
│                            ┌──────────▼──────────┐             │
│                            │  E2E Tests          │             │
│                            │  (Playwright)       │             │
│                            └──────────┬──────────┘             │
│                                       │                        │
│                            ┌──────────▼──────────┐             │
│                            │  Deploy Production  │             │
│                            │  (manual approval)  │             │
│                            └─────────────────────┘             │
│                                                                 │
│  Frontend (Vercel):                                             │
│  - Automatisches Preview-Deployment für PRs                     │
│  - Production-Deployment bei Merge auf main                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Pipeline-Details

| Schritt | Tool | Trigger | Dauer (Ziel) |
|---------|------|---------|-------------|
| Lint Backend | ruff + mypy | Jeder Push | < 30s |
| Lint Frontend | eslint + tsc | Jeder Push | < 45s |
| Unit Tests Backend | pytest (ohne DB) | Jeder Push | < 2 min |
| Unit Tests Frontend | vitest | Jeder Push | < 1 min |
| Integration Tests | pytest + Testcontainers | Merge auf main | < 5 min |
| Docker Build | Docker Buildx (multi-stage) | Merge auf main | < 3 min |
| Deploy Staging | Terraform apply + ECS Update | Auto nach Build | < 5 min |
| E2E Tests | Playwright | Auto nach Staging-Deploy | < 10 min |
| Deploy Production | Terraform apply + ECS Update | Manuelles Approval | < 5 min |

### 8.4 Infrastructure as Code (Terraform)

```hcl
# infra/terraform/main.tf (Überblick)

module "networking" {
  source = "./modules/networking"

  vpc_cidr           = "10.0.0.0/16"
  availability_zones = ["eu-central-1a", "eu-central-1b"]
  # Private Subnets für DBs, Public Subnets für ALB
}

module "ecs" {
  source = "./modules/ecs"

  cluster_name   = "pwbs-${var.environment}"
  task_cpu       = 1024    # 1 vCPU
  task_memory    = 2048    # 2 GB
  desired_count  = 2       # Min. 2 Tasks für HA
  container_image = "${var.ecr_repo}:${var.image_tag}"

  environment_variables = {
    DATABASE_URL   = module.rds.connection_string
    WEAVIATE_URL   = "http://${module.ec2_weaviate.private_ip}:8080"
    NEO4J_URI      = "bolt://${module.ec2_neo4j.private_ip}:7687"
    REDIS_URL      = module.elasticache.connection_string
  }

  secrets = {
    CLAUDE_API_KEY        = var.claude_api_key_arn    # AWS Secrets Manager
    OPENAI_API_KEY        = var.openai_api_key_arn
    JWT_SECRET_KEY        = var.jwt_secret_arn
    ENCRYPTION_MASTER_KEY = module.kms.key_arn
  }
}

module "rds" {
  source = "./modules/rds"

  engine_version    = "16.4"
  instance_class    = "db.t3.medium"
  allocated_storage = 50            # GB, autoscaling enabled
  multi_az          = var.environment == "production"
  encryption        = true
  backup_retention  = 14            # Tage
}

module "kms" {
  source = "./modules/kms"

  key_alias   = "pwbs-${var.environment}-master"
  description = "Master Encryption Key für PWBS User Data Keys"
}

module "monitoring" {
  source = "./modules/monitoring"

  ecs_cluster_name = module.ecs.cluster_name
  rds_identifier   = module.rds.identifier

  alarms = {
    api_5xx_rate = { threshold = 5, period = 300 }
    api_latency  = { threshold = 2000, period = 300 }  # ms
    rds_cpu      = { threshold = 80, period = 300 }
    rds_storage  = { threshold = 85, period = 3600 }
  }
}
```

### 8.5 Monitoring & Observability

#### Drei Säulen

```
┌─────────────────────────────────────────────────────────────────┐
│                      Observability Stack                        │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │     Logging     │  │    Metrics      │  │    Tracing      │ │
│  │                 │  │                 │  │                 │ │
│  │ Structured JSON │  │ Prometheus-     │  │ OpenTelemetry   │ │
│  │ Logs via        │  │ kompatible      │  │ (OTLP)          │ │
│  │ structlog       │  │ Metriken        │  │                 │ │
│  │                 │  │                 │  │ Traces über     │ │
│  │ → CloudWatch    │  │ → CloudWatch    │  │ alle Services   │ │
│  │   Logs          │  │   Metrics       │  │ und DB-Calls    │ │
│  │                 │  │                 │  │                 │ │
│  │ Retention:      │  │ Dashboards:     │  │ → AWS X-Ray     │ │
│  │ 30 Tage aktiv   │  │ Grafana Cloud   │  │   oder          │ │
│  │ 1 Jahr Archiv   │  │ (oder CloudWatch│  │   Grafana Tempo │ │
│  │                 │  │  Dashboards)    │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

#### Kern-Metriken

| Kategorie | Metrik | Alert-Schwellwert |
|----------|--------|-------------------|
| **API** | Request-Latenz (P50, P95, P99) | P99 > 2s |
| **API** | Error-Rate (5xx) | > 1% über 5 min |
| **API** | Request-Rate (RPS) | Informativ |
| **Ingestion** | Dokumente/Stunde pro Konnektor | < 50% des Erwartungswerts |
| **Ingestion** | Connector-Fehlerrate | > 10% Failures |
| **Processing** | Embedding-Latenz (P95) | > 500ms |
| **Processing** | Pipeline-Backlog (ausstehende Dokumente) | > 100 für > 30 min |
| **LLM** | Calls/Stunde, Kosten/Tag | Kosten > Budget × 1.5 |
| **LLM** | Latenz pro Call (P95) | > 10s |
| **Briefing** | Generierungszeit (P95) | > 30s |
| **Search** | Suchlatenz (P95) | > 3s |
| **DB** | PostgreSQL Connection Pool Auslastung | > 80% |
| **DB** | Weaviate Speicherverbrauch | > 80% Disk |
| **DB** | Neo4j Heap Usage | > 80% |

#### Alerting-Kanäle

| Schweregrad | Kanal | Beispiel |
|------------|-------|---------|
| **Critical** | PagerDuty / SMS | DB down, API nicht erreichbar |
| **Warning** | Slack #ops | Hohe Latenz, Connector-Fehler |
| **Info** | Dashboard | Nutzungswachstum, Kosten-Trend |

---

## 9. Phase-Mapping

Die folgende Tabelle zeigt, welche Architekturkomponenten in welcher Roadmap-Phase eingeführt oder ausgebaut werden.

| Komponente | Phase 1 (Discovery) | Phase 2 (MVP) | Phase 3 (Private Beta) | Phase 4 (Launch) | Phase 5 (Plattform) |
|-----------|---------------------|---------------|------------------------|-------------------|---------------------|
| **Konnektoren: Calendar** | PoC | ✅ Production | ✅ Outlook hinzu | ✅ | ✅ |
| **Konnektoren: Notion** | PoC | ✅ Production | ✅ | ✅ | ✅ |
| **Konnektoren: Obsidian** | PoC | ✅ Production | ✅ | ✅ | ✅ |
| **Konnektoren: Zoom** | – | ✅ Production | ✅ Teams hinzu | ✅ | ✅ |
| **Konnektoren: Slack** | – | ✅ Production | ✅ | ✅ | ✅ |
| **Konnektoren: Gmail** | – | ✅ Production | ✅ Outlook-Mail | ✅ | ✅ |
| **Konnektoren: Google Docs** | – | – | ✅ Neu | ✅ | ✅ |
| **Konnektoren: Browser** | – | – | Prototyp | ✅ Extension | ✅ |
| **Processing: Chunking** | Einfach | ✅ Semantic | ✅ Optimiert | ✅ | ✅ |
| **Processing: Embeddings** | OpenAI | ✅ OpenAI | ✅ + Lokal (Sentence Transformers) | ✅ | ✅ Multi-lingual |
| **Processing: NER** | – | ✅ Regel + LLM | ✅ Verbessert | ✅ | ✅ Custom Models |
| **Processing: Graph-Build** | – | ✅ Basis | ✅ Erweitert (Entscheidungen, Ziele) | ✅ Team-Graphen | ✅ Orga-Graphen |
| **Storage: PostgreSQL** | PoC-Schema | ✅ Production-Schema | ✅ + Read Replica | ✅ Multi-Region | ✅ Sharding |
| **Storage: Weaviate** | PoC | ✅ Single-Node | ✅ Cluster (2 Nodes) | ✅ Sharded | ✅ Sharded + HA |
| **Storage: Neo4j** | – | ✅ Community Ed. | ✅ Community Ed. | Enterprise Ed. | ✅ Cluster |
| **Storage: Redis** | – | ✅ Cache | ✅ Cache + Queue | ✅ Cluster | ✅ Cluster |
| **LLM: Claude** | PoC | ✅ Primär | ✅ Primär | ✅ | ✅ |
| **LLM: GPT-4 Fallback** | – | ✅ Fallback | ✅ | ✅ | ✅ |
| **LLM: Ollama (lokal)** | – | – | ✅ Beta | ✅ On-Premise | ✅ |
| **Briefing Engine** | – | ✅ Morning + Meeting | ✅ + Weekly + Project | ✅ + Team-Briefings | ✅ + Vertikal |
| **Semantische Suche** | PoC | ✅ Hybrid Search | ✅ + LLM-Antworten | ✅ + Facetten | ✅ + Cross-Team |
| **Entscheidungsunterstützung** | – | – | ✅ Basis | ✅ Erweitert | ✅ + Tracking |
| **Aktive Erinnerungen** | – | – | ✅ Basis | ✅ Smart Triggers | ✅ |
| **Frontend: Web** | – | ✅ Next.js | ✅ Optimiert | ✅ | ✅ |
| **Frontend: Desktop** | – | – | ✅ Tauri MVP | ✅ Tauri Production | ✅ |
| **Frontend: Mobile** | – | – | – | Prototyp | ✅ iOS + Android |
| **Frontend: Slack Bot** | – | – | Prototyp | ✅ | ✅ |
| **Frontend: Browser Ext.** | – | – | Prototyp | ✅ | ✅ |
| **Auth** | – | ✅ JWT + OAuth2 | ✅ + MFA | ✅ + SSO (SAML) | ✅ |
| **API** | – | ✅ v1 intern | ✅ v1 stabil | ✅ + Rate Limiting | ✅ Public API |
| **Queue-System** | – | Background Tasks | ✅ Celery + Redis | ✅ | AWS SQS |
| **Multi-Tenancy** | – | Single-User | Single-User | ✅ Teams (logisch) | ✅ Orga (physisch) |
| **Self-Hosting** | – | – | Docker Compose Docs | ✅ Helm Chart | ✅ + Managed |
| **CI/CD** | – | ✅ GitHub Actions | ✅ + E2E Tests | ✅ + Canary | ✅ |
| **IaC (Terraform)** | – | ✅ Basis | ✅ Erweitert | ✅ Multi-Env | ✅ Multi-Region |
| **Monitoring** | – | ✅ Basis (Logs, Health) | ✅ Dashboards, Alerts | ✅ Tracing, SLOs | ✅ |
| **Verschlüsselung** | Konzept | ✅ Envelope Encryption | ✅ + Key Rotation | ✅ + Audit | ✅ |
| **DSGVO** | Konzept | ✅ Export + Delete | ✅ + Consent Mgmt | ✅ + Zertifizierung | ✅ |

---

## 10. Offene technische Fragen

| # | Frage | Impact | Status | Kontext |
|---|-------|--------|--------|---------|
| OQ-001 | **Embedding-Modell-Wahl für Mehrsprachigkeit:** Soll `text-embedding-3-small` (OpenAI) für alle Sprachen verwendet werden, oder brauchen deutsch-/mehrsprachige Inhalte ein dediziertes Modell (z. B. `paraphrase-multilingual-MiniLM-L12-v2`)? | **Hoch** | Offen | Betrifft Suchqualität für deutsche Inhalte. Benchmarks mit realen Nutzer-Daten notwendig. |
| OQ-002 | **Weaviate vs. pgvector als Vektor-DB im MVP:** Weaviate bringt Betriebskomplexität mit. Wäre pgvector als Start ausreichend, mit Migration zu Weaviate bei Skalierungsbedarf? | **Mittel** | Offen | pgvector reduziert Infrastrukturaufwand, aber Hybrid-Suche und Multi-Tenancy fehlen. |
| OQ-003 | **Neo4j Community vs. Enterprise Edition:** Community Edition hat keine Cluster-Fähigkeit. Reicht das bis Phase 4? Welche Graphgröße ist zu erwarten? | **Mittel** | Offen | Pro Nutzer geschätzt 5.000–50.000 Knoten. Bei 500 Nutzern: 2,5M–25M Knoten. Community Edition sollte in Phase 2–3 ausreichen. |
| OQ-004 | **LLM-Kosten-Deckel und Pricing-Implikation:** Wie viele LLM-Calls fallen pro Nutzer/Tag an? Was kostet ein aktiver Nutzer/Monat an LLM-API-Gebühren? Ist das deckbar bei 20–50 €/Monat Abo-Preis? | **Hoch** | Analyse nötig | Geschätzte Kalkulation: 1 Briefing/Tag (~8K input, ~2K output tokens) + 5 Suchanfragen + Extraktion. Proof-of-Cost im MVP notwendig. |
| OQ-005 | **Offline-Modus-Architektur (Tauri):** Wie wird die Synchronisierung zwischen lokalem Offline-Vault (Tauri/SQLite) und Cloud-Backend gelöst? Conflict Resolution? | **Mittel** | Offen (Phase 3) | CRDT-basierter Sync oder Last-Write-Wins? Betrifft UX bei wiederkehrender Konnektivität. |
| OQ-006 | **Rate Limiting für LLM-basierte Entitätsextraktion:** 100 Calls/Nutzer/Tag reichen für Normal-Betrieb. Was passiert beim Initial Sync einer großen Notion-DB (1000+ Seiten)? | **Mittel** | Offen | Optionen: Batch-Extraktion mit Haiku (günstiger), Queue mit täglichem Budget, oder initiales Backfill-Budget. |
| OQ-007 | **WebSocket- vs. SSE-Strategie für Echtzeit-Updates:** WebSockets bieten bidirektionale Kommunikation, SSE ist simpler. Welche Echtzeit-Features braucht der MVP tatsächlich? | **Niedrig** | Offen | Aktuell nur Briefing-Notification und Sync-Progress. SSE könnte ausreichen und ist einfacher hinter Load Balancern. |
| OQ-008 | **Token-Refresh-Strategie für externe OAuth-Provider:** Wie wird mit abgelaufenen oder widerrufenen Tokens umgegangen? Proaktiver Refresh oder Retry-on-401? | **Mittel** | Offen | Proaktiver Refresh (vor Ablauf) reduziert Fehler, erfordert aber Hintergrund-Scheduler. Retry-on-401 ist einfacher, aber erzeugt spürbare Latenzen beim Nutzer. |
| OQ-009 | **Graph-Deduplizierung:** Wie werden Entitäten über verschiedene Quellen hinweg dedupliziert? „Thomas K." in Slack = „Thomas Kramer" im Kalender = „t.kramer@firma.de" in Gmail? | **Hoch** | Teilweise gelöst | Ansatz: E-Mail-Adresse als primärer Merge-Key, LLM-basiertes Entity Resolution als Fallback. Benötigt Nutzerfeedback-Loop für Korrekturen. |
| OQ-010 | **Backup- und Disaster-Recovery-Strategie:** RPO/RTO-Ziele? Automatische Backups für Weaviate und Neo4j (keine managed Backups wie bei RDS)? | **Hoch** | Offen | RPO < 1h, RTO < 4h als Ziel. Weaviate: Backup-API + S3. Neo4j: neo4j-admin dump + S3. Muss automatisiert und getestet werden. |

---

*Dieses Dokument wird fortlaufend aktualisiert. Änderungen an Architekturentscheidungen werden als neue ADR-Einträge dokumentiert. Offene Fragen werden vor dem jeweiligen Phase-Gate geklärt.*
