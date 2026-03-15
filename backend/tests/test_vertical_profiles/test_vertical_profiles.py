"""Tests for vertical specialization profiles (TASK-154)."""

from __future__ import annotations

import pytest

from pwbs.briefing.vertical_profiles import (
    VERTICAL_CONFIGS,
    VerticalConfig,
    get_vertical_config,
)
from pwbs.schemas.enums import EntityType, VerticalProfile


# ---------------------------------------------------------------------------
# VerticalConfig dataclass
# ---------------------------------------------------------------------------


class TestVerticalConfig:
    """Tests for the VerticalConfig dataclass."""

    def test_all_profiles_registered(self) -> None:
        """Every VerticalProfile enum member has a config entry."""
        for vp in VerticalProfile:
            assert vp in VERTICAL_CONFIGS, f"Missing config for {vp}"

    def test_config_count_matches_enum(self) -> None:
        assert len(VERTICAL_CONFIGS) == len(VerticalProfile)

    def test_configs_are_frozen(self) -> None:
        cfg = VERTICAL_CONFIGS[VerticalProfile.GENERAL]
        with pytest.raises(AttributeError):
            cfg.display_name = "overwritten"  # type: ignore[misc]

    @pytest.mark.parametrize("profile", list(VerticalProfile))
    def test_config_has_required_fields(self, profile: VerticalProfile) -> None:
        cfg = VERTICAL_CONFIGS[profile]
        assert isinstance(cfg, VerticalConfig)
        assert cfg.profile == profile
        assert cfg.display_name
        assert cfg.description
        assert len(cfg.entity_priorities) > 0
        assert len(cfg.briefing_sections) > 0
        assert isinstance(cfg.ner_focus_instructions, str)
        assert isinstance(cfg.briefing_context_instructions, str)

    @pytest.mark.parametrize("profile", list(VerticalProfile))
    def test_entity_priorities_contain_only_valid_types(
        self, profile: VerticalProfile
    ) -> None:
        cfg = VERTICAL_CONFIGS[profile]
        for et in cfg.entity_priorities:
            assert isinstance(et, EntityType)

    @pytest.mark.parametrize("profile", list(VerticalProfile))
    def test_boosted_entity_types_are_subset_of_priorities(
        self, profile: VerticalProfile
    ) -> None:
        cfg = VERTICAL_CONFIGS[profile]
        prio_set = set(cfg.entity_priorities)
        for et in cfg.boosted_entity_types:
            assert et in prio_set, f"{et} boosted but not in priorities"


# ---------------------------------------------------------------------------
# Profile-specific assertions
# ---------------------------------------------------------------------------


class TestResearcherProfile:
    def test_hypotheses_first(self) -> None:
        cfg = VERTICAL_CONFIGS[VerticalProfile.RESEARCHER]
        assert cfg.entity_priorities[0] == EntityType.HYPOTHESIS

    def test_boosted_types(self) -> None:
        cfg = VERTICAL_CONFIGS[VerticalProfile.RESEARCHER]
        assert EntityType.HYPOTHESIS in cfg.boosted_entity_types
        assert EntityType.OPEN_QUESTION in cfg.boosted_entity_types

    def test_higher_confidence_boost(self) -> None:
        cfg = VERTICAL_CONFIGS[VerticalProfile.RESEARCHER]
        general = VERTICAL_CONFIGS[VerticalProfile.GENERAL]
        assert cfg.confidence_boost >= general.confidence_boost

    def test_morning_sections_include_research(self) -> None:
        cfg = VERTICAL_CONFIGS[VerticalProfile.RESEARCHER]
        assert "research_progress" in cfg.briefing_sections["morning"]
        assert "hypothesis_status" in cfg.briefing_sections["morning"]


class TestConsultantProfile:
    def test_project_first(self) -> None:
        cfg = VERTICAL_CONFIGS[VerticalProfile.CONSULTANT]
        assert cfg.entity_priorities[0] == EntityType.PROJECT

    def test_boosted_types(self) -> None:
        cfg = VERTICAL_CONFIGS[VerticalProfile.CONSULTANT]
        assert EntityType.PROJECT in cfg.boosted_entity_types
        assert EntityType.RISK in cfg.boosted_entity_types

    def test_morning_sections_include_clients(self) -> None:
        cfg = VERTICAL_CONFIGS[VerticalProfile.CONSULTANT]
        assert "client_meetings_today" in cfg.briefing_sections["morning"]


class TestDeveloperProfile:
    def test_decision_first(self) -> None:
        cfg = VERTICAL_CONFIGS[VerticalProfile.DEVELOPER]
        assert cfg.entity_priorities[0] == EntityType.DECISION

    def test_boosted_types(self) -> None:
        cfg = VERTICAL_CONFIGS[VerticalProfile.DEVELOPER]
        assert EntityType.DECISION in cfg.boosted_entity_types
        assert EntityType.RISK in cfg.boosted_entity_types

    def test_morning_sections_include_tech(self) -> None:
        cfg = VERTICAL_CONFIGS[VerticalProfile.DEVELOPER]
        sections = cfg.briefing_sections["morning"]
        assert "sprint_status" in sections
        assert "architecture_decisions" in sections


# ---------------------------------------------------------------------------
# get_vertical_config()
# ---------------------------------------------------------------------------


class TestGetVerticalConfig:
    def test_get_by_enum(self) -> None:
        cfg = get_vertical_config(VerticalProfile.RESEARCHER)
        assert cfg.profile == VerticalProfile.RESEARCHER

    def test_get_by_string(self) -> None:
        cfg = get_vertical_config("consultant")
        assert cfg.profile == VerticalProfile.CONSULTANT

    def test_unknown_string_fallback(self) -> None:
        cfg = get_vertical_config("astronaut")
        assert cfg.profile == VerticalProfile.GENERAL

    def test_empty_string_fallback(self) -> None:
        cfg = get_vertical_config("")
        assert cfg.profile == VerticalProfile.GENERAL

    def test_general_by_default(self) -> None:
        cfg = get_vertical_config(VerticalProfile.GENERAL)
        assert cfg.profile == VerticalProfile.GENERAL

    @pytest.mark.parametrize("name", ["general", "researcher", "consultant", "developer"])
    def test_all_string_names_resolve(self, name: str) -> None:
        cfg = get_vertical_config(name)
        assert cfg.profile.value == name
