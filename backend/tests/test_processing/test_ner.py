"""Tests for pwbs.processing.ner  RuleBasedNER (TASK-061)."""

from __future__ import annotations

from pwbs.processing.ner import (
    ExtractedEntity,
    NERConfig,
    RuleBasedNER,
)
from pwbs.schemas.enums import EntityType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract(
    content: str, metadata: dict | None = None, config: NERConfig | None = None
) -> list[ExtractedEntity]:
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
        assert ner.config.extract_dates is True
        assert ner.config.extract_decisions is True
        assert ner.config.extract_questions is True
        assert ner.config.extract_goals is True
        assert ner.config.extract_risks is True

    def test_custom_config(self) -> None:
        cfg = NERConfig(extract_emails=False, extract_mentions=False)
        ner = RuleBasedNER(config=cfg)
        assert ner.config.extract_emails is False


# ---------------------------------------------------------------------------
# Combined extraction
# ---------------------------------------------------------------------------


class TestCombined:
    def test_all_sources(self) -> None:
        content = (
            "Email john@example.com, cc @alice. "
            "Entscheidung: Wir nutzen PostgreSQL als Datenbank. "
            "Ziel: MVP bis 2026-03-31 fertig. "
            "Risiko: Vendor Lock-in bei AWS."
        )
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
        # ADR-017 additions
        types = {e.entity_type for e in result}
        assert EntityType.DATE_REF in types
        assert EntityType.DECISION in types
        assert EntityType.GOAL in types
        assert EntityType.RISK in types

    def test_empty_content_no_metadata(self) -> None:
        result = _extract("")
        assert result == []

    def test_none_metadata(self) -> None:
        result = _extract("@alice", metadata=None)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Date extraction (ADR-017)
# ---------------------------------------------------------------------------


class TestDateExtraction:
    def test_iso_date(self) -> None:
        result = _extract("Termin am 2026-03-16 festgelegt.")
        entity = _by_name(result, "2026-03-16")
        assert entity is not None
        assert entity.entity_type == EntityType.DATE_REF
        assert entity.mentions[0].source_pattern == "date_iso"
        assert entity.mentions[0].confidence == 1.0

    def test_german_date(self) -> None:
        result = _extract("Abgabe am 16.03.2026.")
        entity = _by_name(result, "16.03.2026")
        assert entity is not None
        assert entity.entity_type == EntityType.DATE_REF

    def test_us_date(self) -> None:
        result = _extract("Due 03/16/2026.")
        entity = _by_name(result, "03/16/2026")
        assert entity is not None
        assert entity.entity_type == EntityType.DATE_REF

    def test_deadline_with_day(self) -> None:
        result = _extract("Deadline: Freitag")
        entity = _by_name(result, "freitag")
        assert entity is not None
        assert entity.entity_type == EntityType.DATE_REF
        assert entity.mentions[0].source_pattern == "deadline_keyword"
        assert entity.mentions[0].confidence == 0.85

    def test_deadline_tomorrow(self) -> None:
        result = _extract("Frist: morgen")
        entity = _by_name(result, "morgen")
        assert entity is not None

    def test_bis_zum_date(self) -> None:
        result = _extract("Bitte bis zum 2026-04-01 erledigen.")
        entity = _by_name(result, "2026-04-01")
        assert entity is not None

    def test_due_by_english(self) -> None:
        result = _extract("Due by Friday")
        entity = _by_name(result, "friday")
        assert entity is not None

    def test_duplicate_dates_dedup(self) -> None:
        result = _extract("2026-03-16 und nochmal 2026-03-16.")
        date_entities = [e for e in result if e.entity_type == EntityType.DATE_REF]
        assert len(date_entities) == 1

    def test_date_extraction_disabled(self) -> None:
        config = NERConfig(extract_dates=False)
        result = _extract("Termin am 2026-03-16.", config=config)
        date_entities = [e for e in result if e.entity_type == EntityType.DATE_REF]
        assert len(date_entities) == 0


# ---------------------------------------------------------------------------
# Decision extraction (ADR-017)
# ---------------------------------------------------------------------------


class TestDecisionExtraction:
    def test_decision_keyword_de(self) -> None:
        result = _extract("Entscheidung: Wir nutzen PostgreSQL statt MySQL.")
        entity = _by_name(result, "wir nutzen postgresql statt mysql")
        assert entity is not None
        assert entity.entity_type == EntityType.DECISION
        assert entity.mentions[0].source_pattern == "decision_keyword"
        assert entity.mentions[0].confidence == 0.85

    def test_beschluss_keyword(self) -> None:
        result = _extract("Beschluss: Budget wird um 20% erhoeht")
        entities = [e for e in result if e.entity_type == EntityType.DECISION]
        assert len(entities) == 1

    def test_decision_keyword_en(self) -> None:
        result = _extract("Decision: Switch to Kubernetes for orchestration")
        entities = [e for e in result if e.entity_type == EntityType.DECISION]
        assert len(entities) == 1
        assert "kubernetes" in entities[0].normalized_name

    def test_action_item(self) -> None:
        result = _extract("Action Item: Alice erstellt das Konzept bis Freitag")
        entities = [e for e in result if e.entity_type == EntityType.DECISION]
        assert len(entities) == 1

    def test_wir_haben_entschieden(self) -> None:
        result = _extract("Wir haben entschieden, den Release zu verschieben.")
        entities = [e for e in result if e.entity_type == EntityType.DECISION]
        assert len(entities) == 1

    def test_we_decided(self) -> None:
        result = _extract("We decided to use React instead of Vue.")
        entities = [e for e in result if e.entity_type == EntityType.DECISION]
        assert len(entities) == 1

    def test_decision_too_short_ignored(self) -> None:
        result = _extract("Entscheidung: Ja.")
        entities = [e for e in result if e.entity_type == EntityType.DECISION]
        assert len(entities) == 0

    def test_decision_extraction_disabled(self) -> None:
        config = NERConfig(extract_decisions=False)
        result = _extract("Entscheidung: PostgreSQL nutzen", config=config)
        entities = [e for e in result if e.entity_type == EntityType.DECISION]
        assert len(entities) == 0


# ---------------------------------------------------------------------------
# Open-question extraction (ADR-017)
# ---------------------------------------------------------------------------


class TestOpenQuestionExtraction:
    def test_offene_frage_de(self) -> None:
        result = _extract("Offene Frage: Wie skaliert die Datenbank bei 10k Usern?")
        entities = [e for e in result if e.entity_type == EntityType.OPEN_QUESTION]
        assert len(entities) == 1
        assert entities[0].mentions[0].source_pattern == "question_keyword"
        assert entities[0].mentions[0].confidence == 0.85

    def test_open_question_en(self) -> None:
        result = _extract("Open question: How do we handle auth token rotation?")
        entities = [e for e in result if e.entity_type == EntityType.OPEN_QUESTION]
        assert len(entities) == 1

    def test_tbd_keyword(self) -> None:
        result = _extract("TBD: Entscheidung ueber Cloud-Provider steht noch aus")
        entities = [e for e in result if e.entity_type == EntityType.OPEN_QUESTION]
        assert len(entities) == 1

    def test_noch_zu_klaeren(self) -> None:
        result = _extract("Noch zu klaeren: Budget fuer Q2-Kampagne")
        entities = [e for e in result if e.entity_type == EntityType.OPEN_QUESTION]
        assert len(entities) == 1

    def test_open_item(self) -> None:
        result = _extract("Open Item: API rate limiting strategy")
        entities = [e for e in result if e.entity_type == EntityType.OPEN_QUESTION]
        assert len(entities) == 1

    def test_question_extraction_disabled(self) -> None:
        config = NERConfig(extract_questions=False)
        result = _extract("Offene Frage: Wie geht es weiter?", config=config)
        entities = [e for e in result if e.entity_type == EntityType.OPEN_QUESTION]
        assert len(entities) == 0


# ---------------------------------------------------------------------------
# Goal extraction (ADR-017)
# ---------------------------------------------------------------------------


class TestGoalExtraction:
    def test_ziel_keyword(self) -> None:
        result = _extract("Ziel: MVP bis Ende Q1 2026 launchen")
        entities = [e for e in result if e.entity_type == EntityType.GOAL]
        assert len(entities) == 1
        assert entities[0].mentions[0].source_pattern == "goal_keyword"

    def test_goal_keyword_en(self) -> None:
        result = _extract("Goal: Achieve 100 active beta users by April")
        entities = [e for e in result if e.entity_type == EntityType.GOAL]
        assert len(entities) == 1

    def test_objective_keyword(self) -> None:
        result = _extract("Objective: Reduce API latency below 200ms")
        entities = [e for e in result if e.entity_type == EntityType.GOAL]
        assert len(entities) == 1

    def test_milestone_keyword(self) -> None:
        result = _extract("Milestone: Database migration abgeschlossen")
        entities = [e for e in result if e.entity_type == EntityType.GOAL]
        assert len(entities) == 1

    def test_goal_extraction_disabled(self) -> None:
        config = NERConfig(extract_goals=False)
        result = _extract("Ziel: MVP launchen", config=config)
        entities = [e for e in result if e.entity_type == EntityType.GOAL]
        assert len(entities) == 0


# ---------------------------------------------------------------------------
# Risk extraction (ADR-017)
# ---------------------------------------------------------------------------


class TestRiskExtraction:
    def test_risiko_keyword(self) -> None:
        result = _extract("Risiko: Vendor Lock-in bei AWS Lambda")
        entities = [e for e in result if e.entity_type == EntityType.RISK]
        assert len(entities) == 1
        assert entities[0].mentions[0].source_pattern == "risk_keyword"

    def test_risk_keyword_en(self) -> None:
        result = _extract("Risk: Data loss during migration phase")
        entities = [e for e in result if e.entity_type == EntityType.RISK]
        assert len(entities) == 1

    def test_blocker_keyword(self) -> None:
        result = _extract("Blocker: CI Pipeline ist seit 2 Tagen rot")
        entities = [e for e in result if e.entity_type == EntityType.RISK]
        assert len(entities) == 1

    def test_risk_extraction_disabled(self) -> None:
        config = NERConfig(extract_risks=False)
        result = _extract("Risiko: Datenverlust", config=config)
        entities = [e for e in result if e.entity_type == EntityType.RISK]
        assert len(entities) == 0


# ---------------------------------------------------------------------------
# Trim-to-sentence helper
# ---------------------------------------------------------------------------


class TestTrimToSentence:
    def test_trims_at_period(self) -> None:
        assert RuleBasedNER._trim_to_sentence("Use PostgreSQL. Then migrate.") == "Use PostgreSQL"

    def test_trims_at_newline(self) -> None:
        assert RuleBasedNER._trim_to_sentence("First line\nSecond line") == "First line"

    def test_no_trim_needed(self) -> None:
        assert RuleBasedNER._trim_to_sentence("Short text") == "Short text"

    def test_strips_trailing_punctuation(self) -> None:
        assert RuleBasedNER._trim_to_sentence("Text here,") == "Text here"
