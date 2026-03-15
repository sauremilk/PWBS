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
    API_UPLOAD = "api_upload"


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
    GOAL = "goal"
    RISK = "risk"
    HYPOTHESIS = "hypothesis"
    OPEN_QUESTION = "open_question"


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


class VerticalProfile(str, Enum):
    """Vertical specialization profile for knowledge workers (TASK-154).

    Each profile adjusts briefing templates, entity priorities, and NER focus.
    """

    GENERAL = "general"
    RESEARCHER = "researcher"
    CONSULTANT = "consultant"
    DEVELOPER = "developer"


class OrgRole(str, Enum):
    """Role of a user within an organization.

    Hierarchy (highest to lowest): OWNER > ADMIN > MANAGER > MEMBER > VIEWER.
    """

    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Granular permissions for RBAC on organization level (TASK-153)."""

    # Organization management
    ORG_DELETE = "org:delete"
    ORG_EDIT = "org:edit"
    ORG_VIEW = "org:view"

    # Member management
    MEMBERS_INVITE = "members:invite"
    MEMBERS_REMOVE = "members:remove"
    MEMBERS_CHANGE_ROLE = "members:change_role"
    MEMBERS_VIEW = "members:view"

    # Connector management
    CONNECTORS_MANAGE = "connectors:manage"
    CONNECTORS_SHARE = "connectors:share"
    CONNECTORS_VIEW = "connectors:view"

    # Document / knowledge
    DOCUMENTS_MANAGE_VISIBILITY = "documents:manage_visibility"
    DOCUMENTS_VIEW_TEAM = "documents:view_team"

    # Briefings
    BRIEFINGS_GENERATE = "briefings:generate"
    BRIEFINGS_VIEW = "briefings:view"

    # Audit
    AUDIT_VIEW = "audit:view"


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
