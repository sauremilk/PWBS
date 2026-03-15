"""Vertical profile configurations for knowledge workers (TASK-154).

Each vertical profile defines:
- entity_priorities: Ordered list of EntityTypes the profile cares most about.
- ner_focus: Additional NER extraction hints (entity types to boost).
- briefing_system_supplement: Extra instructions appended to the briefing
  system prompt so the LLM tailors content for the user's domain.
- briefing_focus_areas: High-level content areas to emphasize in briefings.

Profiles are registered in VERTICAL_PROFILES and looked up via
get_vertical_config().
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pwbs.schemas.enums import EntityType, VerticalProfile

__all__ = [
    "VerticalConfig",
    "get_vertical_config",
    "VERTICAL_PROFILES",
]


# ------------------------------------------------------------------
# Configuration dataclass
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VerticalConfig:
    """Configuration for a single vertical specialization."""

    profile: VerticalProfile
    label: str
    description: str

    entity_priorities: tuple[EntityType, ...] = ()
    ner_focus: tuple[EntityType, ...] = ()
    briefing_system_supplement: str = ""
    briefing_focus_areas: tuple[str, ...] = ()


# ------------------------------------------------------------------
# Profile definitions
# ------------------------------------------------------------------

_GENERAL = VerticalConfig(
    profile=VerticalProfile.GENERAL,
    label="Allgemein",
    description="Standard-Profil ohne vertikale Spezialisierung.",
    entity_priorities=(
        EntityType.PERSON,
        EntityType.PROJECT,
        EntityType.DECISION,
        EntityType.TOPIC,
    ),
    ner_focus=(),
    briefing_system_supplement="",
    briefing_focus_areas=("Termine", "Dokumente", "Entscheidungen"),
)

_RESEARCHER = VerticalConfig(
    profile=VerticalProfile.RESEARCHER,
    label="Forscher",
    description=(
        "Optimiert fuer Literaturarbeit, Hypothesen-Tracking und Experiment-Verknuepfung."
    ),
    entity_priorities=(
        EntityType.HYPOTHESIS,
        EntityType.TOPIC,
        EntityType.OPEN_QUESTION,
        EntityType.PERSON,
        EntityType.DECISION,
    ),
    ner_focus=(EntityType.HYPOTHESIS, EntityType.OPEN_QUESTION, EntityType.RISK),
    briefing_system_supplement=(
        "Der Nutzer ist Forscher. Priorisiere:\n"
        "- Hypothesen und deren aktuellen Status (bestaetigt/widerlegt/offen)\n"
        "- Offene Forschungsfragen und deren Fortschritt\n"
        "- Literatur-Referenzen und Zitationskontext\n"
        "- Experiment-Verknuepfungen und Ergebnisse\n"
        "- Methodische Entscheidungen und ihre Begruendung\n"
        "Verwende akademisch praezise Sprache."
    ),
    briefing_focus_areas=(
        "Hypothesen",
        "Offene Fragen",
        "Literatur",
        "Experimente",
        "Methodische Entscheidungen",
    ),
)

_CONSULTANT = VerticalConfig(
    profile=VerticalProfile.CONSULTANT,
    label="Berater",
    description=("Optimiert fuer Kundenprojekte, Lessons Learned und Cross-Projekt-Muster."),
    entity_priorities=(
        EntityType.PROJECT,
        EntityType.PERSON,
        EntityType.DECISION,
        EntityType.RISK,
        EntityType.GOAL,
    ),
    ner_focus=(EntityType.PROJECT, EntityType.RISK, EntityType.GOAL),
    briefing_system_supplement=(
        "Der Nutzer ist Berater. Priorisiere:\n"
        "- Kundenprojekte: Status, naechste Schritte, offene Risiken\n"
        "- Lessons Learned aus abgeschlossenen Projekten\n"
        "- Cross-Projekt-Muster: wiederkehrende Probleme oder Erfolgsstrategien\n"
        "- Stakeholder-Beziehungen und Kommunikationshistorie\n"
        "- Projekt-Risiken und Mitigationsstrategien\n"
        "Formuliere handlungsorientiert und ergebnisfokussiert."
    ),
    briefing_focus_areas=(
        "Kundenprojekte",
        "Lessons Learned",
        "Stakeholder",
        "Risiken",
        "Cross-Projekt-Muster",
    ),
)

_DEVELOPER = VerticalConfig(
    profile=VerticalProfile.DEVELOPER,
    label="Entwickler",
    description=(
        "Optimiert fuer Architekturentscheidungen, technische Schulden "
        "und Code-Review-Verknuepfung."
    ),
    entity_priorities=(
        EntityType.DECISION,
        EntityType.PROJECT,
        EntityType.TOPIC,
        EntityType.RISK,
        EntityType.OPEN_QUESTION,
    ),
    ner_focus=(EntityType.DECISION, EntityType.RISK, EntityType.OPEN_QUESTION),
    briefing_system_supplement=(
        "Der Nutzer ist Software-Entwickler. Priorisiere:\n"
        "- Architekturentscheidungen (ADRs) und deren Kontext\n"
        "- Technische Schulden: bekannte Issues und Priorisierung\n"
        "- Code-Review-Verknuepfungen und offene Reviews\n"
        "- Sprint-/Iterations-Fortschritt und Blocker\n"
        "- Technische Risiken und ihre Auswirkungen\n"
        "Verwende technisch praezise Sprache. Vermeide Management-Jargon."
    ),
    briefing_focus_areas=(
        "Architekturentscheidungen",
        "Technische Schulden",
        "Code Reviews",
        "Sprint-Blocker",
        "Technische Risiken",
    ),
)


# ------------------------------------------------------------------
# Registry
# ------------------------------------------------------------------

VERTICAL_PROFILES: dict[VerticalProfile, VerticalConfig] = {
    VerticalProfile.GENERAL: _GENERAL,
    VerticalProfile.RESEARCHER: _RESEARCHER,
    VerticalProfile.CONSULTANT: _CONSULTANT,
    VerticalProfile.DEVELOPER: _DEVELOPER,
}


def get_vertical_config(profile: VerticalProfile | str) -> VerticalConfig:
    """Return the configuration for a vertical profile.

    Parameters
    ----------
    profile:
        A VerticalProfile enum member or its string value (e.g. "researcher").

    Returns
    -------
    VerticalConfig
        The matching configuration. Falls back to GENERAL for unknown values.
    """
    if isinstance(profile, str):
        try:
            profile = VerticalProfile(profile)
        except ValueError:
            return VERTICAL_PROFILES[VerticalProfile.GENERAL]
    return VERTICAL_PROFILES.get(profile, VERTICAL_PROFILES[VerticalProfile.GENERAL])
