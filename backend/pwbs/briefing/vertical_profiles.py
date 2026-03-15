"""Vertical specialization profiles for knowledge workers (TASK-154).

Each profile configures:
- Entity type priorities (which NER entities are most relevant)
- Briefing section priorities (which sections appear first / get more space)
- Custom NER extraction hints (additional entity types to focus on)
- Briefing template context adjustments (vertical-specific instructions)

Profiles: GENERAL (default), RESEARCHER, CONSULTANT, DEVELOPER.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pwbs.schemas.enums import EntityType, VerticalProfile

__all__ = [
    "VERTICAL_CONFIGS",
    "VerticalConfig",
    "get_vertical_config",
]


@dataclass(frozen=True, slots=True)
class VerticalConfig:
    """Configuration for a vertical specialization profile."""

    profile: VerticalProfile
    display_name: str
    description: str

    # Entity priorities: ordered list from most to least important
    entity_priorities: list[EntityType]

    # Briefing section priorities (key = briefing type, value = ordered section list)
    briefing_sections: dict[str, list[str]]

    # Additional NER extraction hints injected into the LLM prompt
    ner_focus_instructions: str

    # Extra context for briefing generation prompts
    briefing_context_instructions: str

    # Entity types that get a confidence bonus for this profile
    boosted_entity_types: list[EntityType] = field(default_factory=list)

    # Confidence boost factor (applied to boosted_entity_types)
    confidence_boost: float = 0.1


# ---------------------------------------------------------------------------
# Profile definitions
# ---------------------------------------------------------------------------

_GENERAL = VerticalConfig(
    profile=VerticalProfile.GENERAL,
    display_name="Allgemein",
    description="Standard-Profil ohne vertikale Spezialisierung.",
    entity_priorities=[
        EntityType.PERSON,
        EntityType.PROJECT,
        EntityType.DECISION,
        EntityType.TOPIC,
        EntityType.GOAL,
        EntityType.RISK,
        EntityType.HYPOTHESIS,
        EntityType.OPEN_QUESTION,
    ],
    briefing_sections={
        "morning": [
            "calendar_overview",
            "action_items",
            "key_decisions",
            "open_questions",
        ],
        "meeting_prep": [
            "context",
            "participants",
            "open_items",
            "decisions_needed",
        ],
        "weekly": [
            "highlights",
            "decisions",
            "open_items",
            "next_week",
        ],
    },
    ner_focus_instructions="",
    briefing_context_instructions="",
)

_RESEARCHER = VerticalConfig(
    profile=VerticalProfile.RESEARCHER,
    display_name="Forscher",
    description=(
        "Optimiert für wissenschaftliche Arbeit: "
        "Literaturnachweise, Hypothesen-Tracking, Experiment-Verknüpfung."
    ),
    entity_priorities=[
        EntityType.HYPOTHESIS,
        EntityType.OPEN_QUESTION,
        EntityType.TOPIC,
        EntityType.DECISION,
        EntityType.PERSON,
        EntityType.PROJECT,
        EntityType.GOAL,
        EntityType.RISK,
    ],
    briefing_sections={
        "morning": [
            "research_progress",
            "hypothesis_status",
            "literature_updates",
            "open_questions",
            "calendar_overview",
        ],
        "meeting_prep": [
            "research_context",
            "hypotheses_under_discussion",
            "participants",
            "open_questions",
        ],
        "weekly": [
            "research_milestones",
            "hypotheses_updated",
            "literature_reviewed",
            "next_experiments",
        ],
    },
    ner_focus_instructions=(
        "Priorisiere die Extraktion von: "
        "Hypothesen (mit Status: offen/bestätigt/widerlegt), "
        "Forschungsfragen, Literaturverweise (Autor + Jahr), "
        "Methoden und Experimenten, Datensätze. "
        "Markiere kausale Zusammenhänge zwischen Hypothesen und Evidenz."
    ),
    briefing_context_instructions=(
        "Der Nutzer ist Forscher. Strukturiere Briefings um Erkenntnisfortschritt: "
        "Welche Hypothesen wurden getestet? Welche offenen Fragen bestehen? "
        "Welche Literatur ist neu relevant? Verknüpfe Erkenntnisse mit bestehenden Hypothesen."
    ),
    boosted_entity_types=[EntityType.HYPOTHESIS, EntityType.OPEN_QUESTION],
    confidence_boost=0.15,
)

_CONSULTANT = VerticalConfig(
    profile=VerticalProfile.CONSULTANT,
    display_name="Berater",
    description=(
        "Optimiert für Beratungsarbeit: "
        "Kundenprojekte, Lessons Learned, Cross-Projekt-Muster."
    ),
    entity_priorities=[
        EntityType.PROJECT,
        EntityType.DECISION,
        EntityType.PERSON,
        EntityType.RISK,
        EntityType.GOAL,
        EntityType.TOPIC,
        EntityType.OPEN_QUESTION,
        EntityType.HYPOTHESIS,
    ],
    briefing_sections={
        "morning": [
            "client_meetings_today",
            "project_status",
            "action_items",
            "risk_alerts",
            "cross_project_patterns",
        ],
        "meeting_prep": [
            "client_context",
            "project_history",
            "key_stakeholders",
            "open_deliverables",
            "lessons_from_similar_projects",
        ],
        "weekly": [
            "project_progress",
            "client_satisfaction",
            "risks_and_mitigations",
            "lessons_learned",
            "next_milestones",
        ],
    },
    ner_focus_instructions=(
        "Priorisiere die Extraktion von: "
        "Kundennamen und Projektcodes, Deliverables und Meilensteine, "
        "Risiken mit Auswirkungsgrad (hoch/mittel/niedrig), "
        "Lessons Learned und Best Practices, Stakeholder-Beziehungen. "
        "Identifiziere Cross-Projekt-Muster (ähnliche Probleme in verschiedenen Kundenprojekten)."
    ),
    briefing_context_instructions=(
        "Der Nutzer ist Berater. Strukturiere Briefings um Kundenprojekte: "
        "Was steht heute beim Kunden an? Welche Risiken sind aktiv? "
        "Welche Lessons Learned aus vergangenen Projekten sind hier relevant? "
        "Hebe Cross-Projekt-Muster hervor."
    ),
    boosted_entity_types=[EntityType.PROJECT, EntityType.RISK, EntityType.DECISION],
    confidence_boost=0.1,
)

_DEVELOPER = VerticalConfig(
    profile=VerticalProfile.DEVELOPER,
    display_name="Entwickler",
    description=(
        "Optimiert für Softwareentwicklung: "
        "Architekturentscheidungen, technische Schulden, Code-Review-Verknüpfung."
    ),
    entity_priorities=[
        EntityType.DECISION,
        EntityType.PROJECT,
        EntityType.RISK,
        EntityType.TOPIC,
        EntityType.GOAL,
        EntityType.PERSON,
        EntityType.OPEN_QUESTION,
        EntityType.HYPOTHESIS,
    ],
    briefing_sections={
        "morning": [
            "sprint_status",
            "pr_reviews_pending",
            "architecture_decisions",
            "tech_debt_alerts",
            "calendar_overview",
        ],
        "meeting_prep": [
            "technical_context",
            "recent_architecture_decisions",
            "open_pull_requests",
            "tech_debt_related",
            "participants",
        ],
        "weekly": [
            "sprint_achievements",
            "architecture_decisions",
            "tech_debt_status",
            "code_quality_trends",
            "next_sprint_priorities",
        ],
    },
    ner_focus_instructions=(
        "Priorisiere die Extraktion von: "
        "Architekturentscheidungen (ADRs) mit Begründung, "
        "Technische Schulden mit Dringlichkeit, "
        "API-Änderungen und Breaking Changes, "
        "Performance-Metriken und SLA-Verletzungen, "
        "Code-Review-Feedback und Refactoring-Vorschläge."
    ),
    briefing_context_instructions=(
        "Der Nutzer ist Softwareentwickler. Strukturiere Briefings um technische Arbeit: "
        "Welche Architekturentscheidungen stehen an? Welche Tech-Debt-Items sind dringend? "
        "Welche Pull Requests brauchen Review? "
        "Verknüpfe technische Entscheidungen mit ihren langfristigen Auswirkungen."
    ),
    boosted_entity_types=[EntityType.DECISION, EntityType.RISK],
    confidence_boost=0.1,
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

VERTICAL_CONFIGS: dict[VerticalProfile, VerticalConfig] = {
    VerticalProfile.GENERAL: _GENERAL,
    VerticalProfile.RESEARCHER: _RESEARCHER,
    VerticalProfile.CONSULTANT: _CONSULTANT,
    VerticalProfile.DEVELOPER: _DEVELOPER,
}


def get_vertical_config(profile: VerticalProfile | str) -> VerticalConfig:
    """Get the configuration for a vertical profile.

    Falls back to GENERAL if the profile is unknown.
    """
    if isinstance(profile, str):
        try:
            profile = VerticalProfile(profile)
        except ValueError:
            return VERTICAL_CONFIGS[VerticalProfile.GENERAL]
    return VERTICAL_CONFIGS.get(profile, VERTICAL_CONFIGS[VerticalProfile.GENERAL])
