"""Queue topology configuration (TASK-121).

Defines the five dedicated queues as specified in ARCHITECTURE.md Section 6.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class QueueConfig:
    """Configuration for a single Celery queue."""

    name: str
    description: str
    workers: int
    priority: Literal["high", "medium", "low"]
    timeout: int  # seconds (soft time limit)


# Queue-Topologie gemaess D1 Abschnitt 6.3
QUEUE_TOPOLOGY: dict[str, QueueConfig] = {
    "ingestion.high": QueueConfig(
        name="ingestion.high",
        description="Webhook-getriggerte Echtzeit-Syncs",
        workers=2,
        priority="high",
        timeout=300,  # 5 Minuten
    ),
    "ingestion.bulk": QueueConfig(
        name="ingestion.bulk",
        description="Initial-Syncs und Backfills",
        workers=4,
        priority="low",
        timeout=3600,  # 1 Stunde
    ),
    "processing.embed": QueueConfig(
        name="processing.embed",
        description="Embedding-Generierung",
        workers=2,
        priority="medium",
        timeout=600,  # 10 Minuten
    ),
    "processing.extract": QueueConfig(
        name="processing.extract",
        description="LLM-basierte Entitaetsextraktion",
        workers=2,
        priority="medium",
        timeout=120,  # 2 Minuten
    ),
    "briefing.generate": QueueConfig(
        name="briefing.generate",
        description="Briefing-Generierung",
        workers=2,
        priority="high",
        timeout=60,  # 1 Minute
    ),
}

# Priority mapping for Celery (0 = highest)
PRIORITY_MAP: dict[str, int] = {
    "high": 0,
    "medium": 5,
    "low": 9,
}

ALL_QUEUE_NAMES: list[str] = list(QUEUE_TOPOLOGY.keys())
