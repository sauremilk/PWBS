"""Slack bot integration for PWBS (TASK-141).

Handles slash commands: /pwbs search <query>, /pwbs briefing.
Verifies Slack request signatures, resolves PWBS users, enforces rate limits.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwbs.models.briefing import Briefing as BriefingORM
from pwbs.models.slack_user_mapping import SlackUserMapping

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate limiter (sliding window, in-memory)
# ---------------------------------------------------------------------------

MAX_REQUESTS_PER_HOUR = 10


@dataclass
class _RateLimitBucket:
    timestamps: list[float] = field(default_factory=list)


class SlackRateLimiter:
    """In-memory sliding-window rate limiter per Slack user."""

    def __init__(self, max_requests: int = MAX_REQUESTS_PER_HOUR, window_seconds: int = 3600) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._buckets: dict[str, _RateLimitBucket] = defaultdict(_RateLimitBucket)

    def is_allowed(self, slack_user_id: str) -> bool:
        """Return True if the user has not exceeded their rate limit."""
        now = time.monotonic()
        bucket = self._buckets[slack_user_id]
        # Prune old entries
        bucket.timestamps = [t for t in bucket.timestamps if now - t < self._window]
        if len(bucket.timestamps) >= self._max:
            return False
        bucket.timestamps.append(now)
        return True

    def remaining(self, slack_user_id: str) -> int:
        """Return number of remaining requests in the current window."""
        now = time.monotonic()
        bucket = self._buckets[slack_user_id]
        active = [t for t in bucket.timestamps if now - t < self._window]
        return max(0, self._max - len(active))


# Module-level rate limiter instance
rate_limiter = SlackRateLimiter()


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def verify_slack_signature(
    signing_secret: str,
    timestamp: str,
    body: bytes,
    signature: str,
    *,
    max_age_seconds: int = 300,
) -> bool:
    """Verify a Slack request signature (HMAC-SHA256).

    Returns False if the signature is invalid or the timestamp is too old.
    """
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        return False

    if abs(time.time() - ts) > max_age_seconds:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed = "v0=" + hmac.new(
        signing_secret.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, signature)


# ---------------------------------------------------------------------------
# User resolution
# ---------------------------------------------------------------------------


async def resolve_pwbs_user(
    session: AsyncSession,
    slack_user_id: str,
    slack_workspace_id: str,
) -> uuid.UUID | None:
    """Look up the PWBS user ID for a Slack user. Returns None if not linked."""
    stmt = select(SlackUserMapping.pwbs_user_id).where(
        SlackUserMapping.slack_user_id == slack_user_id,
        SlackUserMapping.slack_workspace_id == slack_workspace_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def link_slack_user(
    session: AsyncSession,
    slack_user_id: str,
    slack_workspace_id: str,
    pwbs_user_id: uuid.UUID,
) -> SlackUserMapping:
    """Link a Slack user to a PWBS account (upsert)."""
    existing = await session.execute(
        select(SlackUserMapping).where(
            SlackUserMapping.slack_user_id == slack_user_id,
            SlackUserMapping.slack_workspace_id == slack_workspace_id,
        )
    )
    mapping = existing.scalar_one_or_none()
    if mapping is not None:
        mapping.pwbs_user_id = pwbs_user_id
    else:
        mapping = SlackUserMapping(
            slack_user_id=slack_user_id,
            slack_workspace_id=slack_workspace_id,
            pwbs_user_id=pwbs_user_id,
        )
        session.add(mapping)
    await session.flush()
    return mapping


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SlackCommandResult:
    """Result of a slash command execution."""

    response_type: str  # "ephemeral" or "in_channel"
    text: str
    blocks: list[dict[str, object]] | None = None


def _format_search_blocks(results: list[dict[str, object]]) -> list[dict[str, object]]:
    """Format search results as Slack Block Kit blocks."""
    blocks: list[dict[str, object]] = []
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": ":mag: PWBS Suchergebnisse"},
    })

    if not results:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_Keine Ergebnisse gefunden._"},
        })
        return blocks

    for i, r in enumerate(results[:3], 1):
        title = r.get("title", "Ohne Titel")
        source = r.get("source_type", "")
        score = r.get("score", 0.0)
        content = str(r.get("content", ""))[:200]
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{i}. {title}*\nQuelle: `{source}` | Relevanz: {score:.0%}\n>{content}",
            },
        })

    return blocks


def _format_briefing_blocks(briefing: BriefingORM | None) -> list[dict[str, object]]:
    """Format a morning briefing as Slack Block Kit blocks."""
    blocks: list[dict[str, object]] = []
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": ":sunrise: PWBS Morgenbriefing"},
    })

    if briefing is None:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "_Kein aktuelles Morgenbriefing verfuegbar._"},
        })
        return blocks

    # Title
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*{briefing.title}*"},
    })

    # Content (truncate for Slack 3000 char limit per block)
    content = briefing.content or ""
    if len(content) > 2900:
        content = content[:2900] + "\n\n_...gekuerzt. Vollstaendiges Briefing in der PWBS Web-App._"
    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": content},
    })

    # Footer with timestamp
    ts = briefing.generated_at.strftime("%d.%m.%Y %H:%M") if briefing.generated_at else ""
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"Generiert: {ts}"}],
    })

    return blocks


async def handle_search_command(
    query: str,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> SlackCommandResult:
    """Execute a semantic search and return formatted Slack response."""
    from pwbs.db.weaviate_client import get_weaviate_client
    from pwbs.processing.embedding import EmbeddingService
    from pwbs.search.enrichment import SearchResultEnricher
    from pwbs.search.hybrid import HybridSearchService
    from pwbs.search.keyword import KeywordSearchService
    from pwbs.search.service import SemanticSearchService

    if not query.strip():
        return SlackCommandResult(
            response_type="ephemeral",
            text="Bitte gib einen Suchbegriff an: `/pwbs search <query>`",
        )

    try:
        weaviate_client = get_weaviate_client()
        embedding_service = EmbeddingService()
        semantic = SemanticSearchService(weaviate_client, embedding_service)
        keyword = KeywordSearchService(session)
        hybrid = HybridSearchService(semantic, keyword)
        enricher = SearchResultEnricher(session=session)

        hybrid_results = await hybrid.search(query=query, user_id=user_id, top_k=3)
        enriched = await enricher.enrich(results=hybrid_results, user_id=user_id)

        results = [
            {
                "title": e.title,
                "source_type": e.source_type,
                "score": e.score,
                "content": e.content,
            }
            for e in enriched
        ]
    except Exception:
        logger.exception("Slack search command failed for user %s", user_id)
        return SlackCommandResult(
            response_type="ephemeral",
            text="Suche fehlgeschlagen. Bitte versuche es spaeter erneut.",
        )

    blocks = _format_search_blocks(results)
    return SlackCommandResult(
        response_type="ephemeral",
        text=f"Suchergebnisse fuer: {query}",
        blocks=blocks,
    )


async def handle_briefing_command(
    user_id: uuid.UUID,
    session: AsyncSession,
) -> SlackCommandResult:
    """Fetch the latest morning briefing and return formatted Slack response."""
    try:
        stmt = (
            select(BriefingORM)
            .where(
                BriefingORM.user_id == user_id,
                BriefingORM.briefing_type == "morning",
            )
            .order_by(BriefingORM.generated_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        briefing = result.scalar_one_or_none()
    except Exception:
        logger.exception("Slack briefing command failed for user %s", user_id)
        return SlackCommandResult(
            response_type="ephemeral",
            text="Briefing konnte nicht geladen werden.",
        )

    blocks = _format_briefing_blocks(briefing)
    return SlackCommandResult(
        response_type="ephemeral",
        text="PWBS Morgenbriefing",
        blocks=blocks,
    )


async def dispatch_command(
    command_text: str,
    slack_user_id: str,
    slack_workspace_id: str,
    session: AsyncSession,
) -> SlackCommandResult:
    """Parse and dispatch a /pwbs slash command."""
    # Rate limit check
    if not rate_limiter.is_allowed(slack_user_id):
        return SlackCommandResult(
            response_type="ephemeral",
            text="Rate-Limit erreicht (max. 10 Anfragen pro Stunde). Bitte spaeter erneut versuchen.",
        )

    # Resolve PWBS user
    pwbs_user_id = await resolve_pwbs_user(session, slack_user_id, slack_workspace_id)
    if pwbs_user_id is None:
        return SlackCommandResult(
            response_type="ephemeral",
            text="Dein Slack-Account ist nicht mit PWBS verknuepft. Bitte verknuepfe ihn zuerst in den PWBS-Einstellungen.",
        )

    # Parse sub-command
    parts = command_text.strip().split(None, 1)
    sub_command = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""

    if sub_command == "search":
        return await handle_search_command(args, pwbs_user_id, session)
    elif sub_command == "briefing":
        return await handle_briefing_command(pwbs_user_id, session)
    else:
        return SlackCommandResult(
            response_type="ephemeral",
            text="Unbekannter Befehl. Verfuegbare Befehle:\n- `/pwbs search <query>` - Semantische Suche\n- `/pwbs briefing` - Aktuelles Morgenbriefing",
        )
