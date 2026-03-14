"""Tests für Prompt-Management mit versionierten Templates (TASK-067)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from pwbs.prompts.registry import (
    MissingContextError,
    PromptNotFoundError,
    PromptRegistry,
    PromptRenderError,
    PromptTemplate,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def prompts_dir(tmp_path: Path) -> Path:
    """Create a temp directory with sample prompt files."""
    # Version 1 of morning briefing
    v1 = tmp_path / "briefing_morning.v1.j2"
    v1.write_text(
        textwrap.dedent("""\
        ---
        model_preference: claude-sonnet-4-20250514
        max_output_tokens: 2000
        temperature: 0.3
        system_prompt: |
          Du bist ein Briefing-Assistent.
        required_context:
          - date
          - calendar_events
        ---
        ## Briefing für {{ date }}

        {% for event in calendar_events %}
        - {{ event }}
        {% endfor %}
        """),
        encoding="utf-8",
    )

    # Version 2 of morning briefing (newer)
    v2 = tmp_path / "briefing_morning.v2.j2"
    v2.write_text(
        textwrap.dedent("""\
        ---
        model_preference: gpt-4o
        max_output_tokens: 3000
        temperature: 0.2
        system_prompt: |
          Verbesserter Briefing-Assistent v2.
        required_context:
          - date
          - calendar_events
          - recent_documents
        ---
        # Morgenbriefing {{ date }}

        ## Termine
        {% for event in calendar_events %}
        - {{ event }}
        {% endfor %}

        ## Dokumente
        {% for doc in recent_documents %}
        - {{ doc }}
        {% endfor %}
        """),
        encoding="utf-8",
    )

    # A meeting prep template
    meeting = tmp_path / "briefing_meeting_prep.v1.j2"
    meeting.write_text(
        textwrap.dedent("""\
        ---
        model_preference: claude-sonnet-4-20250514
        max_output_tokens: 1000
        temperature: 0.3
        system_prompt: Meeting-Vorbereitung
        required_context:
          - meeting_title
          - participants
        ---
        ## Vorbereitung: {{ meeting_title }}

        Teilnehmer: {{ participants | join(', ') }}
        """),
        encoding="utf-8",
    )

    # Template without front matter
    plain = tmp_path / "simple.v1.j2"
    plain.write_text("Hallo {{ name }}!", encoding="utf-8")

    return tmp_path


@pytest.fixture()
def registry(prompts_dir: Path) -> PromptRegistry:
    """Create a PromptRegistry pointing at test fixtures."""
    return PromptRegistry(prompts_dir=prompts_dir)


# ------------------------------------------------------------------
# PromptTemplate dataclass
# ------------------------------------------------------------------


class TestPromptTemplate:
    """Tests for the PromptTemplate dataclass."""

    def test_create_template(self) -> None:
        tpl = PromptTemplate(
            id="test.v1",
            template="Hello {{ name }}",
            model_preference="claude-sonnet-4-20250514",
            max_output_tokens=1000,
            temperature=0.3,
            system_prompt="Test system",
            required_context=["name"],
            version=1,
        )
        assert tpl.id == "test.v1"
        assert tpl.version == 1
        assert tpl.required_context == ["name"]

    def test_template_is_frozen(self) -> None:
        tpl = PromptTemplate(
            id="test.v1",
            template="Hello",
            model_preference="gpt-4o",
            max_output_tokens=100,
            temperature=0.5,
            system_prompt="",
            version=1,
        )
        with pytest.raises(AttributeError):
            tpl.version = 2  # type: ignore[misc]

    def test_default_required_context(self) -> None:
        tpl = PromptTemplate(
            id="test.v1",
            template="Hello",
            model_preference="gpt-4o",
            max_output_tokens=100,
            temperature=0.5,
            system_prompt="",
        )
        assert tpl.required_context == []
        assert tpl.version == 1


# ------------------------------------------------------------------
# PromptRegistry – Loading
# ------------------------------------------------------------------


class TestPromptRegistryLoading:
    """Tests for template loading and indexing."""

    def test_loads_all_templates(self, registry: PromptRegistry) -> None:
        cases = registry.list_use_cases()
        assert "briefing_morning" in cases
        assert "briefing_meeting_prep" in cases
        assert "simple" in cases

    def test_loads_multiple_versions(self, registry: PromptRegistry) -> None:
        versions = registry.list_versions("briefing_morning")
        assert versions == [1, 2]

    def test_get_latest_version_by_default(self, registry: PromptRegistry) -> None:
        tpl = registry.get("briefing_morning")
        assert tpl.version == 2
        assert tpl.model_preference == "gpt-4o"
        assert tpl.max_output_tokens == 3000

    def test_get_specific_version(self, registry: PromptRegistry) -> None:
        tpl = registry.get("briefing_morning", version=1)
        assert tpl.version == 1
        assert tpl.model_preference == "claude-sonnet-4-20250514"
        assert tpl.max_output_tokens == 2000

    def test_get_nonexistent_use_case_raises(self, registry: PromptRegistry) -> None:
        with pytest.raises(PromptNotFoundError, match="nonexistent"):
            registry.get("nonexistent")

    def test_get_nonexistent_version_raises(self, registry: PromptRegistry) -> None:
        with pytest.raises(PromptNotFoundError, match="Version 99"):
            registry.get("briefing_morning", version=99)

    def test_template_without_front_matter(self, registry: PromptRegistry) -> None:
        tpl = registry.get("simple")
        assert tpl.template == "Hallo {{ name }}!"
        assert tpl.model_preference == ""
        assert tpl.max_output_tokens == 4096  # default
        assert tpl.system_prompt == ""
        assert tpl.required_context == []

    def test_front_matter_parsed_correctly(self, registry: PromptRegistry) -> None:
        tpl = registry.get("briefing_meeting_prep")
        assert tpl.temperature == 0.3
        assert tpl.system_prompt.strip() == "Meeting-Vorbereitung"
        assert tpl.required_context == ["meeting_title", "participants"]

    def test_empty_directory(self, tmp_path: Path) -> None:
        reg = PromptRegistry(prompts_dir=tmp_path)
        assert reg.list_use_cases() == []

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        reg = PromptRegistry(prompts_dir=tmp_path / "does_not_exist")
        assert reg.list_use_cases() == []

    def test_malformed_filename_skipped(self, tmp_path: Path) -> None:
        # File without version in name
        bad = tmp_path / "no_version.j2"
        bad.write_text("Hello", encoding="utf-8")
        reg = PromptRegistry(prompts_dir=tmp_path)
        assert reg.list_use_cases() == []

    def test_reload_picks_up_new_files(self, prompts_dir: Path, registry: PromptRegistry) -> None:
        assert "new_template" not in registry.list_use_cases()
        new_file = prompts_dir / "new_template.v1.j2"
        new_file.write_text("---\ntemperature: 0.5\n---\nNeu!", encoding="utf-8")
        registry.reload()
        assert "new_template" in registry.list_use_cases()


# ------------------------------------------------------------------
# PromptRegistry – Rendering
# ------------------------------------------------------------------


class TestPromptRegistryRendering:
    """Tests for Jinja2 template rendering and context validation."""

    def test_render_simple_template(self, registry: PromptRegistry) -> None:
        tpl = registry.get("simple")
        result = registry.render(tpl, {"name": "Welt"})
        assert result == "Hallo Welt!"

    def test_render_with_list_context(self, registry: PromptRegistry) -> None:
        tpl = registry.get("briefing_morning", version=1)
        result = registry.render(
            tpl,
            {
                "date": "2026-03-15",
                "calendar_events": ["Standup 09:00", "Review 14:00"],
            },
        )
        assert "Briefing für 2026-03-15" in result
        assert "Standup 09:00" in result
        assert "Review 14:00" in result

    def test_render_meeting_prep_with_join_filter(self, registry: PromptRegistry) -> None:
        tpl = registry.get("briefing_meeting_prep")
        result = registry.render(
            tpl,
            {
                "meeting_title": "Sprint Planning",
                "participants": ["Alice", "Bob", "Carol"],
            },
        )
        assert "Sprint Planning" in result
        assert "Alice, Bob, Carol" in result

    def test_missing_required_context_raises(self, registry: PromptRegistry) -> None:
        tpl = registry.get("briefing_morning", version=1)
        with pytest.raises(MissingContextError) as exc_info:
            registry.render(tpl, {"date": "2026-03-15"})
        assert "calendar_events" in exc_info.value.missing
        assert exc_info.value.template_id == "briefing_morning.v1"

    def test_missing_multiple_context_vars(self, registry: PromptRegistry) -> None:
        tpl = registry.get("briefing_morning", version=2)
        with pytest.raises(MissingContextError) as exc_info:
            registry.render(tpl, {})
        missing = set(exc_info.value.missing)
        assert missing == {"date", "calendar_events", "recent_documents"}

    def test_extra_context_does_not_raise(self, registry: PromptRegistry) -> None:
        tpl = registry.get("simple")
        result = registry.render(tpl, {"name": "Welt", "extra": "ignored"})
        assert result == "Hallo Welt!"

    def test_render_error_on_undefined_variable(self, registry: PromptRegistry) -> None:
        """Template body references a var not in required_context and not provided."""
        tpl = PromptTemplate(
            id="broken.v1",
            template="{{ undefined_var }}",
            model_preference="",
            max_output_tokens=100,
            temperature=0.5,
            system_prompt="",
            required_context=[],
            version=1,
        )
        with pytest.raises(PromptRenderError):
            registry.render(tpl, {})

    def test_autoescape_html(self, registry: PromptRegistry) -> None:
        """Verify that auto-escaping prevents XSS in rendered output."""
        tpl = registry.get("simple")
        result = registry.render(tpl, {"name": "<script>alert('xss')</script>"})
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
