"""Shared enums for PWBS Pydantic schemas (TASK-032)."""

from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    """Supported data-source types.

    Extensible: add new members as new connectors are implemented.
    """

    GOOGLE_CALENDAR = "google_calendar"
    GOOGLE_DOCS = "google_docs"
    GMAIL = "gmail"
    NOTION = "notion"
    OBSIDIAN = "obsidian"
    OUTLOOK_MAIL = "outlook_mail"
    SLACK = "slack"
    ZOOM = "zoom"


class ContentType(str, Enum):
    """Content format of the normalised document body."""

    PLAINTEXT = "plaintext"
    MARKDOWN = "markdown"
    HTML = "html"


class EntityType(str, Enum):
    """Types of knowledge-graph entities extracted from documents."""

    PERSON = "person"
    PROJECT = "project"
    TOPIC = "topic"
    DECISION = "decision"


class BriefingType(str, Enum):
    """Types of briefings the system can generate.

    Extensible: PROJECT and WEEKLY added in Phase 3.
    """

    MORNING = "morning"
    MEETING_PREP = "meeting_prep"
    PROJECT = "project"
    WEEKLY = "weekly"


class ConnectionStatus(str, Enum):
    """Status of a data-source connection."""

    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    REVOKED = "revoked"


class ReminderType(str, Enum):
    """Types of reminders the trigger engine can generate."""

    FOLLOW_UP = "follow_up"
    INACTIVE_TOPIC = "inactive_topic"
    OPEN_QUESTION = "open_question"


class ReminderStatus(str, Enum):
    """Lifecycle status of a reminder."""

    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    SNOOZED = "snoozed"


class Urgency(str, Enum):
    """Urgency level for reminders."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OrgRole(str, Enum):
    """Role of a user within an organization."""

    OWNER = "owner"
    MEMBER = "member"
    VIEWER = "viewer"


class DocumentVisibility(str, Enum):
    """Visibility scope of a document."""

    PRIVATE = "private"
    TEAM = "team"


class SubscriptionPlan(str, Enum):
    """Available subscription plans."""

    FREE = "free"
    PRO = "pro"


class SubscriptionStatus(str, Enum):
    """Stripe-derived subscription status (cached locally)."""

    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
