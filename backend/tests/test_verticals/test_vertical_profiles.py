"""Tests for vertical profile configurations (TASK-154)."""

from __future__ import annotations

import pytest

from pwbs.schemas.enums import EntityType, VerticalProfile
from pwbs.verticals.profiles import (
    VERTICAL_PROFILES,
    get_vertical_config,
)

# ------------------------------------------------------------------
# Registry completeness
# ------------------------------------------------------------------


class TestVerticalProfilesRegistry:
    """All declared VerticalProfile enum members have a config."""

    def test_all_profiles_registered(self) -> None:
        for member in VerticalProfile:
            assert member in VERTICAL_PROFILES, f"Missing config for {member}"

    def test_registry_length_matches_enum(self) -> None:
        assert len(VERTICAL_PROFILES) == len(VerticalProfile)


# ------------------------------------------------------------------
# get_vertical_config lookup
# ------------------------------------------------------------------


class TestGetVerticalConfig:
    def test_lookup_by_enum(self) -> None:
        cfg = get_vertical_config(VerticalProfile.RESEARCHER)
        assert cfg.profile == VerticalProfile.RESEARCHER

    def test_lookup_by_string(self) -> None:
        cfg = get_vertical_config("consultant")
        assert cfg.profile == VerticalProfile.CONSULTANT

    def test_lookup_general_default(self) -> None:
        cfg = get_vertical_config(VerticalProfile.GENERAL)
        assert cfg.profile == VerticalProfile.GENERAL

    def test_unknown_string_falls_back_to_general(self) -> None:
        cfg = get_vertical_config("nonexistent_vertical")
        assert cfg.profile == VerticalProfile.GENERAL

    def test_unknown_enum_value_falls_back_to_general(self) -> None:
        cfg = get_vertical_config("xyz")
        assert cfg.profile == VerticalProfile.GENERAL


# ------------------------------------------------------------------
# VerticalConfig content
# ------------------------------------------------------------------


class TestVerticalConfigContent:
    """Each profile has the required structural properties."""

    @pytest.mark.parametrize("profile", list(VerticalProfile))
    def test_has_label(self, profile: VerticalProfile) -> None:
        cfg = get_vertical_config(profile)
        assert cfg.label != ""

    @pytest.mark.parametrize("profile", list(VerticalProfile))
    def test_has_description(self, profile: VerticalProfile) -> None:
        cfg = get_vertical_config(profile)
        assert cfg.description != ""

    @pytest.mark.parametrize("profile", list(VerticalProfile))
    def test_entity_priorities_non_empty(self, profile: VerticalProfile) -> None:
        cfg = get_vertical_config(profile)
        assert len(cfg.entity_priorities) > 0

    @pytest.mark.parametrize("profile", list(VerticalProfile))
    def test_briefing_focus_areas_non_empty(self, profile: VerticalProfile) -> None:
        cfg = get_vertical_config(profile)
        assert len(cfg.briefing_focus_areas) > 0

    @pytest.mark.parametrize("profile", list(VerticalProfile))
    def test_entity_priorities_are_entity_types(self, profile: VerticalProfile) -> None:
        cfg = get_vertical_config(profile)
        for et in cfg.entity_priorities:
            assert isinstance(et, EntityType)


# ------------------------------------------------------------------
# Researcher-specific
# ------------------------------------------------------------------


class TestResearcherProfile:
    def test_hypothesis_is_top_priority(self) -> None:
        cfg = get_vertical_config(VerticalProfile.RESEARCHER)
        assert cfg.entity_priorities[0] == EntityType.HYPOTHESIS

    def test_ner_focus_includes_hypothesis(self) -> None:
        cfg = get_vertical_config(VerticalProfile.RESEARCHER)
        assert EntityType.HYPOTHESIS in cfg.ner_focus

    def test_system_supplement_mentions_forscher(self) -> None:
        cfg = get_vertical_config(VerticalProfile.RESEARCHER)
        assert "Forscher" in cfg.briefing_system_supplement


# ------------------------------------------------------------------
# Consultant-specific
# ------------------------------------------------------------------


class TestConsultantProfile:
    def test_project_is_top_priority(self) -> None:
        cfg = get_vertical_config(VerticalProfile.CONSULTANT)
        assert cfg.entity_priorities[0] == EntityType.PROJECT

    def test_ner_focus_includes_risk(self) -> None:
        cfg = get_vertical_config(VerticalProfile.CONSULTANT)
        assert EntityType.RISK in cfg.ner_focus

    def test_system_supplement_mentions_berater(self) -> None:
        cfg = get_vertical_config(VerticalProfile.CONSULTANT)
        assert "Berater" in cfg.briefing_system_supplement


# ------------------------------------------------------------------
# Developer-specific
# ------------------------------------------------------------------


class TestDeveloperProfile:
    def test_decision_is_top_priority(self) -> None:
        cfg = get_vertical_config(VerticalProfile.DEVELOPER)
        assert cfg.entity_priorities[0] == EntityType.DECISION

    def test_ner_focus_includes_decision(self) -> None:
        cfg = get_vertical_config(VerticalProfile.DEVELOPER)
        assert EntityType.DECISION in cfg.ner_focus

    def test_system_supplement_mentions_entwickler(self) -> None:
        cfg = get_vertical_config(VerticalProfile.DEVELOPER)
        assert "Software-Entwickler" in cfg.briefing_system_supplement


# ------------------------------------------------------------------
# General profile
# ------------------------------------------------------------------


class TestGeneralProfile:
    def test_no_ner_focus(self) -> None:
        cfg = get_vertical_config(VerticalProfile.GENERAL)
        assert cfg.ner_focus == ()

    def test_empty_system_supplement(self) -> None:
        cfg = get_vertical_config(VerticalProfile.GENERAL)
        assert cfg.briefing_system_supplement == ""


# ------------------------------------------------------------------
# Frozen dataclass
# ------------------------------------------------------------------


class TestVerticalConfigFrozen:
    def test_is_frozen(self) -> None:
        cfg = get_vertical_config(VerticalProfile.GENERAL)
        with pytest.raises(AttributeError):
            cfg.label = "changed"  # type: ignore[misc]
