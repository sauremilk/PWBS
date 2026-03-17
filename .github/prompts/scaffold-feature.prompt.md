---
agent: agent
description: "Feature-Scaffolding: Erstellt alle Artefakte für ein neues Feature (Backend-Service, API-Route, Frontend-Komponente, Tests). Generalisiertes Template für beliebige Features."
tools:
  - codebase
  - editFiles
  - runCommands
  - problems
---

# Feature-Scaffolding

Du erstellst alle notwendigen Artefakte für ein neues Feature im PWBS.

**Feature-Name:** ${input:feature_name:z.B. "WeeklyBriefing", "Reminder", "ProjectDashboard", "SearchHistory"}
**Bereich:** ${input:domain:Backend / Frontend / Full-Stack}
**Agent-Zuordnung:** ${input:agent:IngestionAgent / ProcessingAgent / BriefingAgent / SearchAgent / GraphAgent / SchedulerAgent / keiner}

---

## Phase 0: Kontext laden

Lies diese Dateien um den Implementierungskontext zu verstehen:

1. **ARCHITECTURE.md** → Modul-Zuordnung, Schichtenmodell
2. **AGENTS.md** → Verantwortlichkeit von ${input:agent}
3. **PRD-SPEC.md** → Anforderungen für ${input:feature_name} (falls dokumentiert)
4. **Existierende ähnliche Features** → Patterns und Konventionen ableiten

Prüfe:

- Welches Modul ist für ${input:feature_name} zuständig?
- Welche bestehenden Patterns können wiederverwendet werden?
- Gibt es Abhängigkeiten zu anderen Features?

---

## Phase 1: Artefakt-Planung

### Backend-Artefakte (wenn `${input:domain}` = Backend oder Full-Stack)

| Artefakt           | Pfad                                                             | Beschreibung                       |
| ------------------ | ---------------------------------------------------------------- | ---------------------------------- |
| Pydantic-Modelle   | `pwbs/models/${input:feature_name.lower()}.py`                   | Request/Response-Schemas           |
| SQLAlchemy-Tabelle | `pwbs/db/models/${input:feature_name.lower()}.py`                | DB-Modell (falls Persistenz nötig) |
| Service-Klasse     | `pwbs/{modul}/services/${input:feature_name.lower()}_service.py` | Business-Logik                     |
| FastAPI-Router     | `pwbs/api/routers/${input:feature_name.lower()}.py`              | API-Endpunkte                      |
| Alembic-Migration  | `migrations/versions/..._add_${input:feature_name.lower()}.py`   | Schema-Änderung                    |

### Frontend-Artefakte (wenn `${input:domain}` = Frontend oder Full-Stack)

| Artefakt         | Pfad                                                                  | Beschreibung           |
| ---------------- | --------------------------------------------------------------------- | ---------------------- |
| TypeScript-Typen | `frontend/src/types/${input:feature_name.lower()}.ts`                 | Interface-Definitionen |
| API-Client       | `frontend/src/lib/api/${input:feature_name.lower()}.ts`               | Fetch-Wrapper          |
| Komponenten      | `frontend/src/components/features/${input:feature_name}/`             | React-Komponenten      |
| Page/Route       | `frontend/src/app/(dashboard)/${input:feature_name.lower()}/page.tsx` | Next.js Page           |

### Tests

| Artefakt           | Pfad                                                                |
| ------------------ | ------------------------------------------------------------------- |
| Unit-Tests Backend | `tests/unit/test_${input:feature_name.lower()}.py`                  |
| API-Tests          | `tests/integration/test_${input:feature_name.lower()}_api.py`       |
| Component-Tests    | `frontend/src/components/features/${input:feature_name}/__tests__/` |

---

## Phase 2: Backend implementieren

### 2.1 Pydantic-Modelle

```python
# pwbs/models/${input:feature_name.lower()}.py
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class ${input:feature_name}Base(BaseModel):
    """Basis-Schema für ${input:feature_name}."""
    # Gemeinsame Felder
    ...

class ${input:feature_name}Create(${input:feature_name}Base):
    """Request-Schema für Erstellung."""
    ...

class ${input:feature_name}Response(${input:feature_name}Base):
    """Response-Schema mit DB-Feldern."""
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 2.2 SQLAlchemy-Modell (falls Persistenz)

```python
# pwbs/db/models/${input:feature_name.lower()}.py
from sqlalchemy import Column, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pwbs.db.base import Base

class ${input:feature_name}(Base):
    __tablename__ = "${input:feature_name.lower()}s"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Feature-spezifische Felder...
    expires_at = Column(DateTime, nullable=True)  # DSGVO!
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

### 2.3 Service-Klasse

```python
# pwbs/{modul}/services/${input:feature_name.lower()}_service.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

class ${input:feature_name}Service:
    """Business-Logik für ${input:feature_name}."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, owner_id: UUID, data: ${input:feature_name}Create) -> ${input:feature_name}Response:
        """Erstellt ein neues ${input:feature_name}."""
        # WICHTIG: owner_id aus JWT, nicht aus Request!
        ...

    async def get_by_id(self, owner_id: UUID, ${input:feature_name.lower()}_id: UUID) -> ${input:feature_name}Response | None:
        """Lädt ${input:feature_name} mit owner_id-Filter."""
        # WICHTIG: WHERE owner_id = ...
        ...

    async def list_for_user(self, owner_id: UUID, limit: int = 50) -> list[${input:feature_name}Response]:
        """Listet alle ${input:feature_name}s eines Users."""
        ...

    async def delete(self, owner_id: UUID, ${input:feature_name.lower()}_id: UUID) -> bool:
        """Löscht ${input:feature_name} (DSGVO-konform)."""
        ...
```

### 2.4 FastAPI-Router

```python
# pwbs/api/routers/${input:feature_name.lower()}.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from uuid import UUID

router = APIRouter(prefix="/${input:feature_name.lower()}s", tags=["${input:feature_name}"])

@router.post("/", response_model=${input:feature_name}Response, status_code=status.HTTP_201_CREATED)
async def create_${input:feature_name.lower()}(
    data: ${input:feature_name}Create,
    response: Response,  # Response VOR Dependencies!
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Erstellt ein neues ${input:feature_name}."""
    service = ${input:feature_name}Service(session)
    return await service.create(current_user.id, data)

@router.get("/{${input:feature_name.lower()}_id}", response_model=${input:feature_name}Response)
async def get_${input:feature_name.lower()}(
    ${input:feature_name.lower()}_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Lädt ein ${input:feature_name} nach ID."""
    service = ${input:feature_name}Service(session)
    result = await service.get_by_id(current_user.id, ${input:feature_name.lower()}_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "${input:feature_name} not found"}
        )
    return result
```

---

## Phase 3: Frontend implementieren

### 3.1 TypeScript-Typen

```typescript
// frontend/src/types/${input:feature_name.lower()}.ts
export interface ${input:feature_name} {
  id: string;
  ownerId: string;
  // Feature-spezifische Felder...
  createdAt: string;
  updatedAt: string;
}

export interface ${input:feature_name}CreateRequest {
  // Request-Felder...
}
```

### 3.2 API-Client

```typescript
// frontend/src/lib/api/${input:feature_name.lower()}.ts
import { ${input:feature_name}, ${input:feature_name}CreateRequest } from "@/types/${input:feature_name.lower()}";

export const ${input:feature_name.lower()}Api = {
  async create(data: ${input:feature_name}CreateRequest): Promise<${input:feature_name}> {
    const response = await fetch("/api/${input:feature_name.lower()}s", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error("Failed to create ${input:feature_name}");
    return response.json();
  },

  async getById(id: string): Promise<${input:feature_name}> {
    const response = await fetch(`/api/${input:feature_name.lower()}s/${id}`);
    if (!response.ok) throw new Error("${input:feature_name} not found");
    return response.json();
  },

  async list(): Promise<${input:feature_name}[]> {
    const response = await fetch("/api/${input:feature_name.lower()}s");
    if (!response.ok) throw new Error("Failed to list ${input:feature_name}s");
    return response.json();
  },
};
```

### 3.3 Komponenten

```tsx
// frontend/src/components/features/${input:feature_name}/${input:feature_name}Card.tsx
import { ${input:feature_name} } from "@/types/${input:feature_name.lower()}";

interface ${input:feature_name}CardProps {
  ${input:feature_name.lower()}: ${input:feature_name};
  onSelect?: (id: string) => void;
}

export function ${input:feature_name}Card({ ${input:feature_name.lower()}, onSelect }: ${input:feature_name}CardProps) {
  return (
    <div className="rounded-lg border p-4 hover:border-primary">
      {/* Feature-spezifisches Rendering */}
    </div>
  );
}
```

---

## Phase 4: Tests schreiben

### Unit-Tests (Backend)

```python
# tests/unit/test_${input:feature_name.lower()}.py
import pytest
from uuid import uuid4

@pytest.fixture
def sample_${input:feature_name.lower()}_data():
    return ${input:feature_name}Create(...)

@pytest.mark.asyncio
async def test_create_${input:feature_name.lower()}(mock_session, sample_${input:feature_name.lower()}_data):
    """Test: ${input:feature_name} kann erstellt werden."""
    service = ${input:feature_name}Service(mock_session)
    owner_id = uuid4()
    result = await service.create(owner_id, sample_${input:feature_name.lower()}_data)
    assert result.owner_id == owner_id

@pytest.mark.asyncio
async def test_get_${input:feature_name.lower()}_requires_owner_id(mock_session):
    """Test: ${input:feature_name} nur mit korrektem owner_id abrufbar."""
    # Sicherstellen, dass Cross-User-Zugriff verhindert wird
    ...
```

---

## Phase 5: Qualitätsprüfung

### Checkliste vor Abschluss

**DSGVO:**

- [ ] `owner_id` in DB-Modell und allen Queries
- [ ] `expires_at` falls Feature PII speichert
- [ ] Kein PII in Logs

**Idempotenz:**

- [ ] UPSERT/MERGE wo sinnvoll
- [ ] Erneutes Erstellen mit gleichen Daten ist sicher

**Erklärbarkeit:** (falls LLM-generierte Inhalte)

- [ ] `sources: list[SourceRef]` bei allen Outputs
- [ ] Fakten vs. Interpretationen trennbar

**Code-Qualität:**

- [ ] Vollständige Type Annotations
- [ ] `async def` für alle I/O
- [ ] Keine `# TODO: implement` Platzhalter
- [ ] Tests für Happy-Path und Fehlerfälle

**MVP-Scope:**

- [ ] Keine Imports aus `backend/_deferred/`
- [ ] Neo4j-Code handelt `driver is None`

---

## Phase 6: Integration

1. **Router registrieren** in `pwbs/api/main.py`
2. **Alembic-Migration** generieren und ausführen
3. **Tests ausführen:** `pytest tests/unit/test_${input:feature_name.lower()}.py -v`
4. **Linting:** `ruff check pwbs/`
5. **Type-Check:** Falls Frontend: `npm run type-check`
