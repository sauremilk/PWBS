"""Neo4j Graph Query Services for Briefing Context Assembly.

Implements three protocols used by the briefing assemblers:

- ``Neo4jGraphQueryService``   → ``MorningContextAssembler``
- ``Neo4jProjectGraphService`` → ``ProjectContextAssembler``
- ``Neo4jWeeklyGraphService``  → ``WeeklyContextAssembler``

All queries use parametrized Cypher (no string concatenation) and include
``userId`` for tenant isolation.  Every service accepts a driver that may be
``None``; in that case calls silently return empty results so the briefing
pipeline degrades gracefully without Neo4j.

D1 §3.3.3, D1 §3.5, AGENTS.md GraphAgent.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from neo4j import AsyncDriver  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)

__all__ = [
    "Neo4jGraphQueryService",
    "Neo4jProjectGraphService",
    "Neo4jWeeklyGraphService",
]

# ---------------------------------------------------------------------------
# Cypher queries (parametrized, no string concatenation)
# ---------------------------------------------------------------------------

# Morning: participant history
_PARTICIPANT_HISTORY_QUERY = """
MATCH (p:Person {userId: $userId})
WHERE p.name IN $names
OPTIONAL MATCH (p)-[:PARTICIPATED_IN]->(m:Meeting {userId: $userId})
OPTIONAL MATCH (p)-[:WORKS_ON]->(proj:Project {userId: $userId})
OPTIONAL MATCH (p)-[:MENTIONED_IN]->(q:OpenQuestion {userId: $userId})
RETURN p.name                              AS name,
       collect(DISTINCT m.title)[0..3]   AS meetings,
       collect(DISTINCT proj.name)[0..3] AS projects,
       collect(DISTINCT q.text)[0..2]    AS open_items
"""

# Morning: pending decisions (no SUPERSEDES successor = unresolved)
_PENDING_DECISIONS_QUERY = """
MATCH (d:Decision {userId: $userId})
WHERE NOT (d)-[:SUPERSEDES]->()
OPTIONAL MATCH (d)-[:DECIDED_IN]->(proj:Project {userId: $userId})
RETURN d.summary   AS title,
       proj.name   AS project,
       d.firstSeen AS created_date,
       d.context   AS context
ORDER BY d.firstSeen ASC
LIMIT $limit
"""

# Project: decisions linked to a project
_PROJECT_DECISIONS_QUERY = """
MATCH (proj:Project {userId: $userId})
WHERE toLower(proj.name) CONTAINS toLower($projectName)
MATCH (d:Decision {userId: $userId})-[:DECIDED_IN|:RELATES_TO]->(proj)
RETURN d.summary   AS summary,
       d.firstSeen AS created_date,
       d.context   AS context
ORDER BY d.firstSeen DESC
LIMIT $limit
"""

# Project: participants (people who work on the project)
_PROJECT_PARTICIPANTS_QUERY = """
MATCH (p:Person {userId: $userId})-[:WORKS_ON]->(proj:Project {userId: $userId})
WHERE toLower(proj.name) CONTAINS toLower($projectName)
RETURN p.name                        AS name,
       p.mentionCount                AS mention_count,
       collect(DISTINCT p.role)[0]   AS role
ORDER BY p.mentionCount DESC
LIMIT $limit
"""

# Project: timeline events (decisions + documents)
_PROJECT_TIMELINE_QUERY = """
MATCH (proj:Project {userId: $userId})
WHERE toLower(proj.name) CONTAINS toLower($projectName)
OPTIONAL MATCH (d:Decision {userId: $userId})-[:DECIDED_IN|:RELATES_TO]->(proj)
OPTIONAL MATCH (doc:Document {userId: $userId})-[:MENTIONS|:COVERS]->(proj)
WITH proj,
     collect(DISTINCT {type: 'decision', title: d.summary,    date: d.firstSeen}) AS decisions,
     collect(DISTINCT {type: 'document', title: doc.title,    date: doc.createdAt}) AS docs
RETURN decisions + docs AS events
"""

# Project: open questions linked to a project
_PROJECT_OPEN_ITEMS_QUERY = """
MATCH (q:OpenQuestion {userId: $userId})-[:RELATED_TO]->(proj:Project {userId: $userId})
WHERE toLower(proj.name) CONTAINS toLower($projectName)
RETURN q.text AS text
ORDER BY q.mentionCount DESC
LIMIT $limit
"""

# Weekly: decisions from the current week
_WEEK_DECISIONS_QUERY = """
MATCH (d:Decision {userId: $userId})
WHERE d.firstSeen >= $since
OPTIONAL MATCH (d)-[:DECIDED_IN]->(proj:Project {userId: $userId})
RETURN d.summary   AS summary,
       proj.name   AS project,
       d.firstSeen AS created_date,
       d.context   AS context
ORDER BY d.firstSeen DESC
LIMIT $limit
"""

# Weekly: project entities active during the week
_WEEK_PROJECT_ENTITIES_QUERY = """
MATCH (proj:Project {userId: $userId})-[r]-(doc:Document {userId: $userId})
WHERE doc.createdAt >= $since
WITH proj, count(DISTINCT doc) AS doc_count
OPTIONAL MATCH (proj)-[:HAS_DECISION]-(d:Decision {userId: $userId})
  WHERE d.firstSeen >= $since
WITH proj, doc_count, count(DISTINCT d) AS decision_count
RETURN proj.name        AS name,
       doc_count        AS document_count,
       decision_count   AS decision_count
ORDER BY doc_count DESC
LIMIT 10
"""

# Weekly: open items across all projects
_OPEN_ITEMS_QUERY = """
MATCH (q:OpenQuestion {userId: $userId})
WHERE q.mentionCount >= 1
RETURN q.text AS text
ORDER BY q.mentionCount DESC
LIMIT $limit
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _safe_query(
    driver: AsyncDriver,
    cypher: str,
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """Execute a Cypher query and return rows as dicts.

    Returns an empty list on any error so briefing assembly is never blocked
    by graph availability.
    """
    try:
        async with driver.session() as session:
            result = await session.run(cypher, params)
            return await result.data()
    except Exception:
        logger.debug("Neo4j query failed – returning empty result", exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Morning Briefing Graph Service
# ---------------------------------------------------------------------------


class Neo4jGraphQueryService:
    """Real Neo4j implementation of the ``GraphQueryService`` protocol.

    Used by ``MorningContextAssembler``.  All queries include
    ``userId`` for tenant isolation and use parametrized Cypher.

    Parameters
    ----------
    driver:
        Active Neo4j async driver.  If ``None``, all methods return
        empty results without raising.
    """

    def __init__(self, driver: AsyncDriver | None) -> None:
        self._driver = driver

    async def get_participant_history(
        self,
        participant_names: list[str],
        owner_id: UUID,
    ) -> list[Any]:
        """Return interaction history for the given participants."""
        from pwbs.briefing.context import ParticipantHistory

        if self._driver is None or not participant_names:
            return []

        rows = await _safe_query(
            self._driver,
            _PARTICIPANT_HISTORY_QUERY,
            {"userId": str(owner_id), "names": participant_names},
        )

        results: list[ParticipantHistory] = []
        for row in rows:
            results.append(
                ParticipantHistory(
                    name=row.get("name", ""),
                    last_meetings=[m for m in (row.get("meetings") or []) if m],
                    shared_projects=[p for p in (row.get("projects") or []) if p],
                    open_items=[i for i in (row.get("open_items") or []) if i],
                )
            )

        logger.info(
            "get_participant_history: owner=%s names=%d returned=%d",
            owner_id,
            len(participant_names),
            len(results),
        )
        return results

    async def get_pending_decisions(
        self,
        owner_id: UUID,
        limit: int = 10,
    ) -> list[Any]:
        """Return pending (unresolved) decisions from the graph."""
        from pwbs.briefing.context import PendingDecision

        if self._driver is None:
            return []

        rows = await _safe_query(
            self._driver,
            _PENDING_DECISIONS_QUERY,
            {"userId": str(owner_id), "limit": limit},
        )

        results: list[PendingDecision] = []
        for row in rows:
            results.append(
                PendingDecision(
                    title=row.get("title") or "",
                    project=row.get("project"),
                    created_date=row.get("created_date"),
                    context=row.get("context"),
                )
            )

        logger.info(
            "get_pending_decisions: owner=%s returned=%d", owner_id, len(results)
        )
        return results


# ---------------------------------------------------------------------------
# Project Briefing Graph Service
# ---------------------------------------------------------------------------


class Neo4jProjectGraphService:
    """Real Neo4j implementation of the ``ProjectGraphService`` protocol.

    Used by ``ProjectContextAssembler``.  All queries filter by
    ``userId`` and use parametrized Cypher.

    Parameters
    ----------
    driver:
        Active Neo4j async driver.  If ``None``, all methods return
        empty results without raising.
    """

    def __init__(self, driver: AsyncDriver | None) -> None:
        self._driver = driver

    async def get_project_decisions(
        self,
        owner_id: UUID,
        project_name: str,
        limit: int = 20,
    ) -> list[Any]:
        """Return decisions associated with the project."""
        from pwbs.briefing.project_context import ProjectDecision

        if self._driver is None:
            return []

        rows = await _safe_query(
            self._driver,
            _PROJECT_DECISIONS_QUERY,
            {"userId": str(owner_id), "projectName": project_name, "limit": limit},
        )

        return [
            ProjectDecision(
                title=row.get("summary") or "",
                date=row.get("created_date") or "",
            )
            for row in rows
        ]

    async def get_project_participants(
        self,
        owner_id: UUID,
        project_name: str,
        limit: int = 15,
    ) -> list[Any]:
        """Return people involved in the project."""
        from pwbs.briefing.project_context import ProjectParticipant

        if self._driver is None:
            return []

        rows = await _safe_query(
            self._driver,
            _PROJECT_PARTICIPANTS_QUERY,
            {"userId": str(owner_id), "projectName": project_name, "limit": limit},
        )

        return [
            ProjectParticipant(
                name=row.get("name") or "",
                role=row.get("role") or None,
                contribution_count=row.get("mention_count") or 0,
            )
            for row in rows
        ]

    async def get_project_timeline(
        self,
        owner_id: UUID,
        project_name: str,
        limit: int = 20,
    ) -> list[Any]:
        """Return timeline events for the project."""
        from pwbs.briefing.project_context import ProjectMilestone

        if self._driver is None:
            return []

        rows = await _safe_query(
            self._driver,
            _PROJECT_TIMELINE_QUERY,
            {"userId": str(owner_id), "projectName": project_name},
        )

        milestones: list[ProjectMilestone] = []
        for row in rows:
            for evt in (row.get("events") or []):
                if not evt or not evt.get("title"):
                    continue
                milestones.append(
                    ProjectMilestone(
                        title=evt["title"],
                        date=evt.get("date") or "",
                        event_type=evt.get("type", "document"),
                    )
                )
        # Sort chronologically and cap to limit
        milestones.sort(key=lambda m: m.date or "")
        return milestones[:limit]

    async def get_project_open_items(
        self,
        owner_id: UUID,
        project_name: str,
        limit: int = 10,
    ) -> list[str]:
        """Return open questions for the project."""
        if self._driver is None:
            return []

        rows = await _safe_query(
            self._driver,
            _PROJECT_OPEN_ITEMS_QUERY,
            {"userId": str(owner_id), "projectName": project_name, "limit": limit},
        )

        return [row["text"] for row in rows if row.get("text")]


# ---------------------------------------------------------------------------
# Weekly Briefing Graph Service
# ---------------------------------------------------------------------------


class Neo4jWeeklyGraphService:
    """Real Neo4j implementation of the ``WeeklyGraphService`` protocol.

    Used by ``WeeklyContextAssembler``.

    Parameters
    ----------
    driver:
        Active Neo4j async driver.  If ``None``, all methods return
        empty results without raising.
    """

    def __init__(self, driver: AsyncDriver | None) -> None:
        self._driver = driver

    async def get_week_decisions(
        self,
        owner_id: UUID,
        since: datetime,
        limit: int = 15,
    ) -> list[Any]:
        """Return decisions logged during the week."""
        from pwbs.briefing.weekly_context import WeeklyDecision

        if self._driver is None:
            return []

        rows = await _safe_query(
            self._driver,
            _WEEK_DECISIONS_QUERY,
            {"userId": str(owner_id), "since": since.isoformat(), "limit": limit},
        )

        return [
            WeeklyDecision(
                title=row.get("summary") or "",
                project=row.get("project") or None,
            )
            for row in rows
        ]

    async def get_project_entities(
        self,
        owner_id: UUID,
        since: datetime,
    ) -> list[dict]:
        """Return project entities with document counts from the week."""
        if self._driver is None:
            return []

        rows = await _safe_query(
            self._driver,
            _WEEK_PROJECT_ENTITIES_QUERY,
            {"userId": str(owner_id), "since": since.isoformat()},
        )

        return [
            {
                "name": row.get("name") or "",
                "document_count": row.get("document_count") or 0,
                "decision_count": row.get("decision_count") or 0,
            }
            for row in rows
            if row.get("name")
        ]

    async def get_open_items(
        self,
        owner_id: UUID,
        limit: int = 10,
    ) -> list[str]:
        """Return top open questions across all projects."""
        if self._driver is None:
            return []

        rows = await _safe_query(
            self._driver,
            _OPEN_ITEMS_QUERY,
            {"userId": str(owner_id), "limit": limit},
        )

        return [row["text"] for row in rows if row.get("text")]
