"""Idempotent Neo4j graph schema setup (TASK-026).

Creates uniqueness constraints and composite indexes for all
node labels defined in the PWBS knowledge graph. Safe to run
multiple times (IF NOT EXISTS).

Node labels: Person, Project, Topic, Decision, Meeting, Document
Edge types:  PARTICIPATED_IN, WORKS_ON, MENTIONED_IN, KNOWS,
             HAS_TOPIC, HAS_DECISION, DECIDED_IN, AFFECTS,
             SUPERSEDES, DISCUSSED, RELATES_TO, PRODUCED,
             MENTIONS, COVERS, REFERENCES, RELATED_TO
"""

from __future__ import annotations

from neo4j import AsyncGraphDatabase

NODE_LABELS = ["Person", "Project", "Topic", "Decision", "Meeting", "Document"]

# Uniqueness constraint on id per label
_CONSTRAINT_TEMPLATE = (
    "CREATE CONSTRAINT {name} IF NOT EXISTS "
    "FOR (n:{label}) REQUIRE n.id IS UNIQUE"
)

# Composite index on userId for tenant-isolated queries
_INDEX_TEMPLATE = (
    "CREATE INDEX {name} IF NOT EXISTS "
    "FOR (n:{label}) ON (n.userId)"
)


async def ensure_neo4j_schema(uri: str, user: str, password: str) -> None:
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        async with driver.session() as session:
            for label in NODE_LABELS:
                constraint_name = f"constraint_{label.lower()}_id"
                await session.run(
                    _CONSTRAINT_TEMPLATE.format(name=constraint_name, label=label)
                )

                index_name = f"index_{label.lower()}_userId"
                await session.run(
                    _INDEX_TEMPLATE.format(name=index_name, label=label)
                )
    finally:
        await driver.close()


async def main() -> None:
    from pwbs.core.config import get_settings

    settings = get_settings()
    await ensure_neo4j_schema(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password.get_secret_value(),
    )
    print(f"Neo4j schema ready ({len(NODE_LABELS)} labels configured)")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
