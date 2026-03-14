"""Tests for pwbs.processing.ner  RuleBasedNER (TASK-061)."""

from __future__ import annotations

import pytest

from pwbs.processing.ner import (
    ExtractedEntity,
    ExtractedMention,
    NERConfig,
    RuleBasedNER,
)
from pwbs.schemas.enums import EntityType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract(content: str, metadata: dict | None = None, config: NERConfig | None = None) -> list[ExtractedEntity]:
    ner = RuleBasedNER(config=config)
    return ner.extract(content, metadata)


def _names(entities: list[ExtractedEntity]) -> set[str]:
    return {e.normalized_name for e in entities}


def _by_name(entities: list[ExtractedEntity], normalized: str) -> ExtractedEntity | None:
    for e in entities:
        if e.normalized_name == normalized:
            return e
    return None


# ---------------------------------------------------------------------------
# Email extraction
# ---------------------------------------------------------------------------


class TestEmailExtraction:
    def test_simple_email(self) -> None:
        result = _extract("Contact john.doe@example.com for details.")
        assert len(result) == 1
        entity = result[0]
        assert entity.entity_type == EntityType.PERSON
        assert entity.normalized_name == "john doe"
        assert entity.name == "John Doe"
        assert entity.mentions[0].extraction_method == "rule"
        assert entity.mentions[0].confidence == 1.0
        assert entity.mentions[0].source_pattern == "email"

    def test_multiple_emails(self) -> None:
        text = "alice@corp.com und bob.smith@example.org"
        result = _extract(text)
        names = _names(result)
        assert "alice" in names
        assert "bob smith" in names

    def test_duplicate_emails(self) -> None:
        text = "john@example.com und john@example.com nochmal"
        result = _extract(text)
        # Should deduplicate
        john = _by_name(result, "john")
        assert john is not None
        assert len(john.mentions) == 2

    def test_no_emails(self) -> None:
        result = _extract("No emails here.")
        assert len(result) == 0

    def test_complex_email_local_part(self) -> None:
        result = _extract("user.name+tag@domain.co.uk")
        assert len(result) == 1
        assert result[0].normalized_name == "user name tag"

    def test_email_extraction_disabled(self) -> None:
        config = NERConfig(extract_emails=False)
        result = _extract("john@example.com", config=config)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# @-Mention extraction
# ---------------------------------------------------------------------------


class TestAtMentionExtraction:
    def test_simple_mention(self) -> None:
        result = _extract("Hey @alice, can you review?")
        assert len(result) == 1
        entity = result[0]
        assert entity.entity_type == EntityType.PERSON
        assert entity.normalized_name == "alice"
        assert entity.mentions[0].source_pattern == "at_mention"

    def test_dotted_mention(self) -> None:
        result = _extract("cc @john.doe for info")
        entity = _by_name(result, "john doe")
        assert entity is not None
        assert entity.entity_type == EntityType.PERSON

    def test_underscore_mention(self) -> None:
        result = _extract("Assigned to @bob_smith")
        entity = _by_name(result, "bob smith")
        assert entity is not None

    def test_multiple_mentions(self) -> None:
        text = "@alice @bob @charlie"
        result = _extract(text)
        assert len(result) == 3

    def test_no_mention_in_email(self) -> None:
        # @domain in emails should not be extracted as @-mention
        result = _extract("user@domain.com")
        # Only the email extraction should fire, not @-mention for "domain.com"
        types = {e.mentions[0].source_pattern for e in result}
        assert "at_mention" not in types

    def test_mention_extraction_disabled(self) -> None:
        config = NERConfig(extract_mentions=False)
        result = _extract("Hey @alice", config=config)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Calendar participant extraction
# ---------------------------------------------------------------------------


class TestParticipantExtraction:
    def test_participants_with_name(self) -> None:
        metadata = {
            "participants": [
                {"name": "Alice Smith", "email": "alice@corp.com"},
                {"name": "Bob Jones", "email": "bob@corp.com"},
            ]
        }
        result = _extract("", metadata=metadata)
        assert len(result) == 2
        names = _names(result)
        assert "alice smith" in names
        assert "bob jones" in names

    def test_participant_email_only(self) -> None:
        metadata = {
            "participants": [
                {"email": "john.doe@example.com"},
            ]
        }
        result = _extract("", metadata=metadata)
        assert len(result) == 1
        assert result[0].normalized_name == "john doe"
        assert result[0].mentions[0].source_pattern == "participant"

    def test_participant_no_name_no_email(self) -> None:
        metadata = {"participants": [{"role": "organizer"}]}
        result = _extract("", metadata=metadata)
        assert len(result) == 0

    def test_no_participants_field(self) -> None:
        result = _extract("", metadata={"other": "data"})
        assert len(result) == 0

    def test_invalid_participants_type(self) -> None:
        result = _extract("", metadata={"participants": "not a list"})
        assert len(result) == 0

    def test_invalid_participant_entry(self) -> None:
        metadata = {"participants": ["not a dict", 42]}
        result = _extract("", metadata=metadata)
        assert len(result) == 0

    def test_participant_extraction_disabled(self) -> None:
        config = NERConfig(extract_participants=False)
        metadata = {"participants": [{"name": "Alice"}]}
        result = _extract("", metadata=metadata, config=config)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Notion link extraction
# ---------------------------------------------------------------------------


class TestNotionLinkExtraction:
    def test_notion_link_with_type(self) -> None:
        metadata = {
            "notion_links": [
                {"title": "PWBS Project", "type": "project"},
            ]
        }
        result = _extract("", metadata=metadata)
        assert len(result) == 1
        assert result[0].entity_type == EntityType.PROJECT
        assert result[0].normalized_name == "pwbs project"

    def test_notion_link_person_type(self) -> None:
        metadata = {"notion_links": [{"title": "Alice", "type": "person"}]}
        result = _extract("", metadata=metadata)
        assert result[0].entity_type == EntityType.PERSON

    def test_notion_link_decision_type(self) -> None:
        metadata = {"notion_links": [{"title": "Use React", "type": "decision"}]}
        result = _extract("", metadata=metadata)
        assert result[0].entity_type == EntityType.DECISION

    def test_notion_link_default_topic(self) -> None:
        metadata = {"notion_links": [{"title": "Meeting Notes"}]}
        result = _extract("", metadata=metadata)
        assert result[0].entity_type == EntityType.TOPIC

    def test_notion_link_unknown_type(self) -> None:
        metadata = {"notion_links": [{"title": "Stuff", "type": "unknown"}]}
        result = _extract("", metadata=metadata)
        assert result[0].entity_type == EntityType.TOPIC

    def test_notion_link_empty_title(self) -> None:
        metadata = {"notion_links": [{"title": ""}]}
        result = _extract("", metadata=metadata)
        assert len(result) == 0

    def test_no_notion_links(self) -> None:
        result = _extract("", metadata={})
        assert len(result) == 0

    def test_invalid_notion_links_type(self) -> None:
        result = _extract("", metadata={"notion_links": "bad"})
        assert len(result) == 0

    def test_notion_extraction_disabled(self) -> None:
        config = NERConfig(extract_notion_links=False)
        metadata = {"notion_links": [{"title": "Test"}]}
        result = _extract("", metadata=metadata, config=config)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplication:
    def test_same_email_and_mention(self) -> None:
        """alice@example.com and @alice should deduplicate."""
        text = "Contact alice@example.com or @alice"
        result = _extract(text)
        alice = _by_name(result, "alice")
        assert alice is not None
        assert len(alice.mentions) == 2

    def test_different_entity_types_not_merged(self) -> None:
        metadata = {
            "notion_links": [
                {"title": "Alpha", "type": "person"},
                {"title": "Alpha", "type": "project"},
            ]
        }
        result = _extract("", metadata=metadata)
        # Same name but different types  separate entities
        assert len(result) == 2

    def test_case_insensitive_dedup(self) -> None:
        metadata = {
            "participants": [
                {"name": "Alice Smith"},
                {"name": "ALICE SMITH"},
                {"name": "alice smith"},
            ]
        }
        result = _extract("", metadata=metadata)
        assert len(result) == 1
        assert len(result[0].mentions) == 3


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


class TestNormalization:
    def test_lowercase(self) -> None:
        assert RuleBasedNER._normalize("ALICE") == "alice"

    def test_strip_whitespace(self) -> None:
        assert RuleBasedNER._normalize("  alice  ") == "alice"

    def test_collapse_whitespace(self) -> None:
        assert RuleBasedNER._normalize("alice   smith") == "alice smith"

    def test_email_to_name(self) -> None:
        assert RuleBasedNER._email_to_name("john.doe@example.com") == "John Doe"

    def test_email_to_name_underscore(self) -> None:
        assert RuleBasedNER._email_to_name("first_last@corp.com") == "First Last"

    def test_email_to_name_plus(self) -> None:
        assert RuleBasedNER._email_to_name("user+tag@mail.com") == "User Tag"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_default_config(self) -> None:
        ner = RuleBasedNER()
        assert ner.config.extract_emails is True
        assert ner.config.extract_mentions is True
        assert ner.config.extract_participants is True
        assert ner.config.extract_notion_links is True

    def test_custom_config(self) -> None:
        cfg = NERConfig(extract_emails=False, extract_mentions=False)
        ner = RuleBasedNER(config=cfg)
        assert ner.config.extract_emails is False


# ---------------------------------------------------------------------------
# Combined extraction
# ---------------------------------------------------------------------------


class TestCombined:
    def test_all_sources(self) -> None:
        content = "Email john@example.com, cc @alice"
        metadata = {
            "participants": [{"name": "Bob Jones"}],
            "notion_links": [{"title": "PWBS", "type": "project"}],
        }
        result = _extract(content, metadata=metadata)
        names = _names(result)
        assert "john" in names
        assert "alice" in names
        assert "bob jones" in names
        assert "pwbs" in names

    def test_empty_content_no_metadata(self) -> None:
        result = _extract("")
        assert result == []

    def test_none_metadata(self) -> None:
        result = _extract("@alice", metadata=None)
        assert len(result) == 1
