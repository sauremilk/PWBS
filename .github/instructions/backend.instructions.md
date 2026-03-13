---
applyTo: "**/*.py"
---

# Backend-Instruktionen: Python / FastAPI

## Modul-Struktur

```
pwbs/
├── api/            # FastAPI Router, Dependency Injection, Middleware
├── connectors/     # Datenquellen-Konnektoren (BaseConnector + Implementierungen)
├── ingestion/      # Ingestion-Pipeline, Normalisierung ins UDF
├── processing/     # Chunking, Embedding, NER
├── storage/        # Repository-Schicht: PostgreSQL, Weaviate, Neo4j
├── briefing/       # Briefing-Generierung, Templates
├── search/         # Semantische Suche, Hybrid-Search
├── graph/          # Knowledge-Graph-Operationen
├── scheduler/      # Zeitgesteuerte Jobs
├── prompts/        # LLM-Prompt-Templates (versioniert)
└── core/           # Shared: Config, Exceptions, Basisklassen
```

## Pflichtregeln

### Typing
- Vollständige Type Annotations in jeder Funktion und Methode. `Any` nur wenn unvermeidbar und dann mit Kommentar begründen.
- `TypeVar`, `Generic`, `Protocol` für polymorphe Strukturen nutzen.
- `list[X]` statt `List[X]`, `dict[K,V]` statt `Dict[K,V]` (Python 3.12+).

### Pydantic v2
- Alle Datenmodelle erben von `pydantic.BaseModel`.
- `model_config = ConfigDict(...)` statt `class Config`.
- `@model_validator(mode="after")` statt `@validator`.
- `@field_validator` mit `mode="before"` für Input-Transformation.
- Niemals `dict()` auf Pydantic-Objekte aufrufen – `model_dump()` verwenden.

### FastAPI
- Response-Typ korrekt in Route-Signatur annotieren: `response: Response` NICHT `response: Response | None`.
- `Response`-Parameter VOR Default-Parameter-Dependencies platzieren (sonst `FastAPIError`).
- Dependency Injection über `Depends()` für DB-Sessions und Service-Instanzen.
- `APIRouter` mit `prefix` und `tags` in jedem Modul.

### Fehlerbehandlung
```python
# Eigene Exception-Hierarchie
class PWBSError(Exception): ...
class ConnectorError(PWBSError): ...
class StorageError(PWBSError): ...

# HTTP-Fehler mit strukturiertem detail
raise HTTPException(
    status_code=422,
    detail={"code": "VALIDATION_FAILED", "field": "source_id", "message": "..."}
)
```

### Async & Threading
- `async def` für alle I/O-Operationen (DB-Zugriff, HTTP-Calls, File-I/O).
- Synchroner Blocking-Code (z.B. schwere Berechnungen, sync-Bibliotheken) in `asyncio.to_thread()` auslagern.
- DB-Sessions niemals über Modul-Grenzen teilen.

### Idempotenz (KRITISCH)
- Jeder `ingest()`- und `process()`-Aufruf muss bei Wiederholung dasselbe Ergebnis liefern ohne Duplikate.
- `ON CONFLICT DO UPDATE` (upsert) in PostgreSQL-Writes nutzen.
- Vor jedem Weaviate-Insert prüfen, ob `source_id` + `owner_id` bereits existiert.
- Cursor/Watermarks in Connector-Zuständen persistieren.

### DSGVO-Pflichten
- Jedes `UnifiedDocument` braucht `owner_id` und `expires_at`.
- Jede DB-Query gegen `UnifiedDocument` oder abgeleitete Tabellen MUSS `WHERE owner_id = :user_id` enthalten.
- Keine Nutzerdaten in Logs (kein `content`, keine Embeddings, keine `metadata`-Werte).

### Tests
- Fixtures für alle externen Abhängigkeiten in `conftest.py`.
- Kein echter Netzwerkzugriff im Unit-Test – `httpx.MockTransport` oder `pytest-mock`.
- `@pytest.mark.asyncio` für async Tests, `asyncio_mode = "auto"` in `pytest.ini`.
- Test-Dateipfad: `tests/unit/`, `tests/integration/`, `tests/e2e/`.

## Konnektoren implementieren

```python
from pwbs.connectors.base import BaseConnector, ConnectorConfig, SyncResult

class MyConnector(BaseConnector):
    async def fetch_since(self, cursor: str | None) -> SyncResult:
        """Cursor-basiertes Abrufen. Gibt neuen Cursor zurück."""
        ...
    
    async def normalize(self, raw: dict) -> UnifiedDocument:
        """Rohdaten → UDF. Muss idempotent sein."""
        ...
```

## LLM-Aufrufe

- Prompts ausschließlich aus `pwbs/prompts/*.jinja2` laden, nie inline hardcoden.
- Structured Output (JSON-Schema) für alle nicht-narrativen LLM-Outputs.
- Jede LLM-Antwort mit Quellenreferenzen versehen (Pflichtfeld `sources: list[SourceRef]`).
- LLM-Calls über den `LLMGateway`-Service abstrahieren – nie direkt Anthropic/OpenAI SDK aufrufen.
- Fallback-Reihenfolge: Claude → GPT-4 → Ollama (konfigurierbar per Env-Var).
