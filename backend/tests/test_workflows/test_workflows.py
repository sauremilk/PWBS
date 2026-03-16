"""Tests for Workflow Automation – TASK-160.

Sections:
  1. Schema validation (triggers, actions, CRUD)
  2. Trigger evaluation (new_document, keyword_match, schedule)
  3. Action execution (email, create_reminder, generate_briefing)
  4. Engine orchestration (evaluate_rules_for_event)
  5. API router configuration
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

# ── Section 1: Schema Validation ─────────────────────────────────────────────


class TestTriggerSchemas:
    """Pydantic schema validation for trigger types."""

    def test_new_document_trigger_defaults(self) -> None:
        from pwbs.workflows.schemas import NewDocumentTrigger

        t = NewDocumentTrigger()
        assert t.type == "new_document"
        assert t.source_types is None

    def test_new_document_trigger_with_source_types(self) -> None:
        from pwbs.workflows.schemas import NewDocumentTrigger

        t = NewDocumentTrigger(source_types=["notion", "obsidian"])
        assert t.source_types == ["notion", "obsidian"]

    def test_keyword_trigger_requires_keywords(self) -> None:
        from pwbs.workflows.schemas import KeywordMatchTrigger

        with pytest.raises(ValidationError):
            KeywordMatchTrigger()  # type: ignore[call-arg]

    def test_keyword_trigger_empty_list_rejected(self) -> None:
        from pwbs.workflows.schemas import KeywordMatchTrigger

        with pytest.raises(ValidationError):
            KeywordMatchTrigger(keywords=[])

    def test_keyword_trigger_valid(self) -> None:
        from pwbs.workflows.schemas import KeywordMatchTrigger

        t = KeywordMatchTrigger(keywords=["project", "deadline"])
        assert t.type == "keyword_match"
        assert len(t.keywords) == 2
        assert t.match_all is False

    def test_keyword_trigger_match_all(self) -> None:
        from pwbs.workflows.schemas import KeywordMatchTrigger

        t = KeywordMatchTrigger(keywords=["important"], match_all=True)
        assert t.match_all is True

    def test_schedule_trigger_requires_cron(self) -> None:
        from pwbs.workflows.schemas import ScheduleTrigger

        with pytest.raises(ValidationError):
            ScheduleTrigger()  # type: ignore[call-arg]

    def test_schedule_trigger_valid(self) -> None:
        from pwbs.workflows.schemas import ScheduleTrigger

        t = ScheduleTrigger(cron_expression="0 9 * * 1-5")
        assert t.type == "schedule"
        assert t.cron_expression == "0 9 * * 1-5"

    def test_schedule_trigger_invalid_cron(self) -> None:
        from pwbs.workflows.schemas import ScheduleTrigger

        with pytest.raises(ValidationError):
            ScheduleTrigger(cron_expression="invalid_cron!")


class TestActionSchemas:
    """Pydantic schema validation for action types."""

    def test_email_action_requires_fields(self) -> None:
        from pwbs.workflows.schemas import EmailAction

        with pytest.raises(ValidationError):
            EmailAction()  # type: ignore[call-arg]

    def test_email_action_valid(self) -> None:
        from pwbs.workflows.schemas import EmailAction

        a = EmailAction(subject_template="Alert: {event}", body_template="Details here")
        assert a.type == "email"
        assert a.subject_template == "Alert: {event}"

    def test_email_action_subject_too_long(self) -> None:
        from pwbs.workflows.schemas import EmailAction

        with pytest.raises(ValidationError):
            EmailAction(subject_template="x" * 201, body_template="body")

    def test_create_reminder_action_defaults(self) -> None:
        from pwbs.workflows.schemas import CreateReminderAction

        a = CreateReminderAction(title_template="Remember this")
        assert a.type == "create_reminder"
        assert a.urgency == "medium"

    def test_create_reminder_action_urgency_validation(self) -> None:
        from pwbs.workflows.schemas import CreateReminderAction

        a = CreateReminderAction(title_template="Urgent", urgency="high")
        assert a.urgency == "high"

        with pytest.raises(ValidationError):
            CreateReminderAction(title_template="Test", urgency="critical")

    def test_generate_briefing_action_defaults(self) -> None:
        from pwbs.workflows.schemas import GenerateBriefingAction

        a = GenerateBriefingAction()
        assert a.type == "generate_briefing"
        assert a.briefing_type == "project"

    def test_generate_briefing_action_valid_types(self) -> None:
        from pwbs.workflows.schemas import GenerateBriefingAction

        for bt in ("morning", "meeting_prep", "project", "weekly"):
            a = GenerateBriefingAction(briefing_type=bt)
            assert a.briefing_type == bt

    def test_generate_briefing_action_invalid_type(self) -> None:
        from pwbs.workflows.schemas import GenerateBriefingAction

        with pytest.raises(ValidationError):
            GenerateBriefingAction(briefing_type="invalid")


class TestCRUDSchemas:
    """Pydantic schema validation for CRUD request/response schemas."""

    def test_workflow_rule_create_minimal(self) -> None:
        from pwbs.workflows.schemas import EmailAction, NewDocumentTrigger, WorkflowRuleCreate

        rule = WorkflowRuleCreate(
            name="Test Rule",
            trigger_config=NewDocumentTrigger(),
            action_config=EmailAction(subject_template="New doc", body_template="Body"),
        )
        assert rule.name == "Test Rule"
        assert rule.is_active is True
        assert rule.description == ""

    def test_workflow_rule_create_name_required(self) -> None:
        from pwbs.workflows.schemas import EmailAction, NewDocumentTrigger, WorkflowRuleCreate

        with pytest.raises(ValidationError):
            WorkflowRuleCreate(
                name="",
                trigger_config=NewDocumentTrigger(),
                action_config=EmailAction(subject_template="S", body_template="B"),
            )

    def test_workflow_rule_update_all_optional(self) -> None:
        from pwbs.workflows.schemas import WorkflowRuleUpdate

        u = WorkflowRuleUpdate()
        assert u.name is None
        assert u.trigger_config is None
        assert u.action_config is None
        assert u.is_active is None

    def test_workflow_rule_response_model(self) -> None:
        from pwbs.workflows.schemas import WorkflowRuleResponse

        now = datetime.now(tz=timezone.utc)
        r = WorkflowRuleResponse(
            id=uuid.uuid4(),
            name="My Rule",
            description="",
            trigger_config={"type": "new_document"},
            action_config={"type": "email", "subject_template": "S", "body_template": "B"},
            is_active=True,
            execution_count=0,
            created_at=now,
            updated_at=now,
        )
        assert r.name == "My Rule"
        assert r.execution_count == 0

    def test_workflow_execution_response_model(self) -> None:
        from pwbs.workflows.schemas import WorkflowExecutionResponse

        now = datetime.now(tz=timezone.utc)
        e = WorkflowExecutionResponse(
            id=uuid.uuid4(),
            rule_id=uuid.uuid4(),
            trigger_event="new_document",
            trigger_data={"source_type": "notion"},
            action_result="success",
            action_data={"action": "email"},
            executed_at=now,
        )
        assert e.trigger_event == "new_document"
        assert e.action_result == "success"

    def test_discriminated_union_trigger_parsing(self) -> None:
        """WorkflowRuleCreate correctly parses discriminated trigger union."""
        from pwbs.workflows.schemas import EmailAction, WorkflowRuleCreate

        rule = WorkflowRuleCreate.model_validate(
            {
                "name": "Keyword Rule",
                "trigger_config": {"type": "keyword_match", "keywords": ["important"]},
                "action_config": {"type": "email", "subject_template": "S", "body_template": "B"},
            }
        )
        assert rule.trigger_config.type == "keyword_match"  # type: ignore[union-attr]

    def test_discriminated_union_action_parsing(self) -> None:
        """WorkflowRuleCreate correctly parses discriminated action union."""
        from pwbs.workflows.schemas import WorkflowRuleCreate

        rule = WorkflowRuleCreate.model_validate(
            {
                "name": "Reminder Rule",
                "trigger_config": {"type": "new_document"},
                "action_config": {"type": "create_reminder", "title_template": "Do this"},
            }
        )
        assert rule.action_config.type == "create_reminder"  # type: ignore[union-attr]


# ── Section 2: Trigger Evaluation ────────────────────────────────────────────


class TestNewDocumentTrigger:
    """Tests for new_document trigger evaluation."""

    def test_matches_all_sources_when_no_filter(self) -> None:
        from pwbs.workflows.engine import evaluate_new_document_trigger

        trigger = {"type": "new_document", "source_types": None}
        event = {"source_type": "notion"}
        assert evaluate_new_document_trigger(trigger, event) is True

    def test_matches_matching_source(self) -> None:
        from pwbs.workflows.engine import evaluate_new_document_trigger

        trigger = {"type": "new_document", "source_types": ["notion", "obsidian"]}
        event = {"source_type": "notion"}
        assert evaluate_new_document_trigger(trigger, event) is True

    def test_rejects_non_matching_source(self) -> None:
        from pwbs.workflows.engine import evaluate_new_document_trigger

        trigger = {"type": "new_document", "source_types": ["notion"]}
        event = {"source_type": "zoom"}
        assert evaluate_new_document_trigger(trigger, event) is False

    def test_missing_source_type_in_event(self) -> None:
        from pwbs.workflows.engine import evaluate_new_document_trigger

        trigger = {"type": "new_document", "source_types": ["notion"]}
        event: dict[str, object] = {}
        assert evaluate_new_document_trigger(trigger, event) is False


class TestKeywordTrigger:
    """Tests for keyword_match trigger evaluation."""

    def test_single_keyword_match_in_content(self) -> None:
        from pwbs.workflows.engine import evaluate_keyword_trigger

        trigger = {"type": "keyword_match", "keywords": ["deadline"], "match_all": False}
        event = {"content": "The project deadline is tomorrow.", "title": ""}
        assert evaluate_keyword_trigger(trigger, event) is True

    def test_single_keyword_match_in_title(self) -> None:
        from pwbs.workflows.engine import evaluate_keyword_trigger

        trigger = {"type": "keyword_match", "keywords": ["deadline"], "match_all": False}
        event = {"content": "", "title": "Deadline approaching"}
        assert evaluate_keyword_trigger(trigger, event) is True

    def test_keyword_case_insensitive(self) -> None:
        from pwbs.workflows.engine import evaluate_keyword_trigger

        trigger = {"type": "keyword_match", "keywords": ["URGENT"], "match_all": False}
        event = {"content": "This is urgent", "title": ""}
        assert evaluate_keyword_trigger(trigger, event) is True

    def test_no_keyword_match(self) -> None:
        from pwbs.workflows.engine import evaluate_keyword_trigger

        trigger = {"type": "keyword_match", "keywords": ["budget"], "match_all": False}
        event = {"content": "Meeting notes from today", "title": "Weekly sync"}
        assert evaluate_keyword_trigger(trigger, event) is False

    def test_match_all_true_all_present(self) -> None:
        from pwbs.workflows.engine import evaluate_keyword_trigger

        trigger = {"type": "keyword_match", "keywords": ["project", "deadline"], "match_all": True}
        event = {"content": "The project deadline is close", "title": ""}
        assert evaluate_keyword_trigger(trigger, event) is True

    def test_match_all_true_partial_match(self) -> None:
        from pwbs.workflows.engine import evaluate_keyword_trigger

        trigger = {"type": "keyword_match", "keywords": ["project", "budget"], "match_all": True}
        event = {"content": "The project deadline is close", "title": ""}
        assert evaluate_keyword_trigger(trigger, event) is False

    def test_empty_keywords_returns_false(self) -> None:
        from pwbs.workflows.engine import evaluate_keyword_trigger

        trigger = {"type": "keyword_match", "keywords": [], "match_all": False}
        event = {"content": "anything", "title": ""}
        assert evaluate_keyword_trigger(trigger, event) is False


class TestScheduleTrigger:
    """Tests for schedule trigger evaluation."""

    def test_matches_schedule_event(self) -> None:
        from pwbs.workflows.engine import evaluate_schedule_trigger

        trigger = {"type": "schedule", "cron_expression": "0 9 * * 1-5"}
        event: dict[str, object] = {"event_type": "schedule"}
        assert evaluate_schedule_trigger(trigger, event) is True

    def test_rejects_non_schedule_event(self) -> None:
        from pwbs.workflows.engine import evaluate_schedule_trigger

        trigger = {"type": "schedule", "cron_expression": "0 9 * * 1-5"}
        event: dict[str, object] = {"event_type": "new_document"}
        assert evaluate_schedule_trigger(trigger, event) is False


# ── Section 3: Action Execution ──────────────────────────────────────────────


class TestEmailAction:
    """Tests for email action execution."""

    @pytest.mark.asyncio
    async def test_email_action_returns_queued(self) -> None:
        from pwbs.workflows.engine import execute_email_action

        action_config: dict[str, object] = {
            "type": "email",
            "subject_template": "Alert: New Document",
            "body_template": "A new document was ingested.",
        }
        user_id = uuid.uuid4()
        db = AsyncMock()

        result = await execute_email_action(action_config, {}, user_id, db)
        assert result["action"] == "email"
        assert result["status"] == "queued"
        assert result["subject"] == "Alert: New Document"


class TestCreateReminderAction:
    """Tests for create_reminder action execution."""

    @pytest.mark.asyncio
    async def test_creates_reminder_with_defaults(self) -> None:
        from pwbs.workflows.engine import execute_create_reminder_action

        mock_db = AsyncMock()
        # Mock the reminder so it has an id after flush
        with patch("pwbs.models.reminder.Reminder") as MockReminder:
            mock_reminder = MagicMock()
            mock_reminder.id = uuid.uuid4()
            MockReminder.return_value = mock_reminder

            action_config: dict[str, object] = {
                "type": "create_reminder",
                "title_template": "Follow up",
                "urgency": "high",
            }
            result = await execute_create_reminder_action(
                action_config, {"event_type": "new_document"}, uuid.uuid4(), mock_db
            )

            assert result["action"] == "create_reminder"
            assert result["status"] == "created"
            assert result["title"] == "Follow up"
            mock_db.add.assert_called_once()
            mock_db.flush.assert_awaited_once()


class TestGenerateBriefingAction:
    """Tests for generate_briefing action execution."""

    @pytest.mark.asyncio
    async def test_briefing_action_returns_queued(self) -> None:
        from pwbs.workflows.engine import execute_generate_briefing_action

        action_config: dict[str, object] = {
            "type": "generate_briefing",
            "briefing_type": "morning",
        }
        result = await execute_generate_briefing_action(
            action_config, {}, uuid.uuid4(), AsyncMock()
        )
        assert result["action"] == "generate_briefing"
        assert result["briefing_type"] == "morning"
        assert result["status"] == "queued"


# ── Section 4: Engine Orchestration ──────────────────────────────────────────


class TestEvaluateRulesForEvent:
    """Tests for the main engine entry point."""

    def _make_rule(
        self,
        trigger_config: dict[str, Any],
        action_config: dict[str, Any],
        *,
        user_id: uuid.UUID | None = None,
        is_active: bool = True,
    ) -> MagicMock:
        rule = MagicMock()
        rule.id = uuid.uuid4()
        rule.user_id = user_id or uuid.uuid4()
        rule.trigger_config = trigger_config
        rule.action_config = action_config
        rule.is_active = is_active
        rule.execution_count = 0
        return rule

    @pytest.mark.asyncio
    async def test_no_rules_returns_empty(self) -> None:
        from pwbs.workflows.engine import evaluate_rules_for_event

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        executions = await evaluate_rules_for_event(
            mock_db,
            user_id=uuid.uuid4(),
            event_type="new_document",
            event_data={"source_type": "notion"},
        )
        assert executions == []

    @pytest.mark.asyncio
    async def test_matching_rule_creates_execution(self) -> None:
        from pwbs.workflows.engine import evaluate_rules_for_event

        user_id = uuid.uuid4()
        rule = self._make_rule(
            trigger_config={"type": "new_document", "source_types": None},
            action_config={"type": "email", "subject_template": "New doc", "body_template": "Body"},
            user_id=user_id,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [rule]
        mock_db.execute.return_value = mock_result

        executions = await evaluate_rules_for_event(
            mock_db,
            user_id=user_id,
            event_type="new_document",
            event_data={"source_type": "notion"},
        )
        assert len(executions) == 1
        assert executions[0].trigger_event == "new_document"
        assert executions[0].action_result == "success"
        # DB add called for execution
        assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_non_matching_rule_skipped(self) -> None:
        from pwbs.workflows.engine import evaluate_rules_for_event

        user_id = uuid.uuid4()
        rule = self._make_rule(
            trigger_config={"type": "new_document", "source_types": ["obsidian"]},
            action_config={"type": "email", "subject_template": "S", "body_template": "B"},
            user_id=user_id,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [rule]
        mock_db.execute.return_value = mock_result

        executions = await evaluate_rules_for_event(
            mock_db,
            user_id=user_id,
            event_type="new_document",
            event_data={"source_type": "notion"},
        )
        assert executions == []

    @pytest.mark.asyncio
    async def test_unknown_action_type_fails_gracefully(self) -> None:
        from pwbs.workflows.engine import evaluate_rules_for_event

        user_id = uuid.uuid4()
        rule = self._make_rule(
            trigger_config={"type": "new_document", "source_types": None},
            action_config={"type": "unknown_action"},
            user_id=user_id,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [rule]
        mock_db.execute.return_value = mock_result

        executions = await evaluate_rules_for_event(
            mock_db,
            user_id=user_id,
            event_type="new_document",
            event_data={"source_type": "notion"},
        )
        assert len(executions) == 1
        assert executions[0].action_result == "failed"
        assert "Unknown action type" in str(executions[0].action_data.get("error", ""))

    @pytest.mark.asyncio
    async def test_action_exception_logged_as_failed(self) -> None:
        from pwbs.workflows.engine import _ACTION_EXECUTORS, evaluate_rules_for_event

        user_id = uuid.uuid4()
        rule = self._make_rule(
            trigger_config={"type": "new_document", "source_types": None},
            action_config={"type": "create_reminder", "title_template": "Test"},
            user_id=user_id,
        )

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [rule]
        mock_db.execute.return_value = mock_result

        # Make the action throw by replacing the executor in the dict
        original = _ACTION_EXECUTORS["create_reminder"]
        _ACTION_EXECUTORS["create_reminder"] = AsyncMock(side_effect=RuntimeError("DB error"))
        try:
            executions = await evaluate_rules_for_event(
                mock_db,
                user_id=user_id,
                event_type="new_document",
                event_data={"source_type": "notion"},
            )
        finally:
            _ACTION_EXECUTORS["create_reminder"] = original

        assert len(executions) == 1
        assert executions[0].action_result == "failed"
        assert "DB error" in str(executions[0].action_data.get("error", ""))


# ── Section 5: API Router Configuration ──────────────────────────────────────


class TestWorkflowsAPIRouter:
    """Tests for the workflows API router configuration."""

    def test_router_prefix(self) -> None:
        from pwbs.api.v1.routes.workflows import router

        assert router.prefix == "/api/v1/workflows"

    def test_router_tags(self) -> None:
        from pwbs.api.v1.routes.workflows import router

        assert "workflows" in router.tags

    def test_crud_endpoints_exist(self) -> None:
        from pwbs.api.v1.routes.workflows import router

        paths = [r.path for r in router.routes]  # type: ignore[attr-defined]
        assert "/api/v1/workflows/" in paths
        assert "/api/v1/workflows/{rule_id}" in paths
        assert "/api/v1/workflows/{rule_id}/log" in paths

    def test_crud_methods(self) -> None:
        from pwbs.api.v1.routes.workflows import router

        method_map: dict[str, set[str]] = {}
        for route in router.routes:  # type: ignore[attr-defined]
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set())
            if path not in method_map:
                method_map[path] = set()
            method_map[path].update(methods)

        assert "POST" in method_map.get("/api/v1/workflows/", set())
        assert "GET" in method_map.get("/api/v1/workflows/", set())
        assert "GET" in method_map.get("/api/v1/workflows/{rule_id}", set())
        assert "PATCH" in method_map.get("/api/v1/workflows/{rule_id}", set())
        assert "DELETE" in method_map.get("/api/v1/workflows/{rule_id}", set())

    def test_execution_log_endpoint_is_get(self) -> None:
        from pwbs.api.v1.routes.workflows import router

        for route in router.routes:  # type: ignore[attr-defined]
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set())
            if path == "/api/v1/workflows/{rule_id}/log":
                assert "GET" in methods
                return
        pytest.fail("Execution log endpoint not found")

    def test_router_registered_in_app(self) -> None:
        """Workflows router is included in the main app."""
        pytest.importorskip("prometheus_client")
        from unittest.mock import patch as mock_patch

        with mock_patch("pwbs.db.postgres.get_engine"):
            from pwbs.api.main import create_app

            app = create_app()
            routes = [r.path for r in app.routes]  # type: ignore[attr-defined]
            assert any("/api/v1/workflows" in r for r in routes)
