"""Tests for generate_initial_briefing Celery task (TASK-177).

Verifies:
  - Task registration and configuration
  - Happy path: first sync triggers briefing generation
  - Idempotent: no briefing if user already has briefings
  - User not found: returns gracefully without error
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OWNER_ID = str(uuid.uuid4())
_OWNER_UUID = uuid.UUID(_OWNER_ID)


@dataclass(frozen=True, slots=True)
class _FakeLLMResult:
    """Minimal stand-in for BriefingLLMResult."""

    content: str = "# Willkommen\nDein erstes Briefing."
    briefing_type: str = "morning"
    grounding_result: object = None
    usage: object = None
    model: str = "test-model"
    template_id: str = "briefing_morning"
    generated_at: datetime = datetime(2026, 3, 15, tzinfo=UTC)
    word_count: int = 4


def _scalar_one_result(value: object) -> MagicMock:
    """Build a mock execute-result that returns *value* for .scalar_one()."""
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _scalar_one_or_none_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ---------------------------------------------------------------------------
# Task registration
# ---------------------------------------------------------------------------


class TestTaskRegistration:
    def test_task_is_registered(self) -> None:
        import pwbs.queue.tasks.briefing  # noqa: F401

        from pwbs.queue.celery_app import app

        assert "pwbs.queue.tasks.briefing.generate_initial_briefing" in app.tasks

    def test_task_config(self) -> None:
        from pwbs.queue.tasks.briefing import generate_initial_briefing

        assert generate_initial_briefing.max_retries == 2
        assert generate_initial_briefing.queue == "briefing.generate"


# ---------------------------------------------------------------------------
# Async implementation (_generate_initial_briefing_async)
# ---------------------------------------------------------------------------


class TestGenerateInitialBriefingAsync:
    """Tests for the async implementation directly (bypasses Celery)."""

    @pytest.mark.asyncio
    async def test_generates_when_no_briefings_exist(self) -> None:
        """First sync: 0 existing briefings → briefing generated and persisted."""
        from pwbs.queue.tasks.briefing import _generate_initial_briefing_async

        mock_user = MagicMock()
        mock_user.id = _OWNER_UUID

        # Sequential DB queries: 1) count=0, 2) user found
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_one_result(0),
                _scalar_one_or_none_result(mock_user),
            ]
        )
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)

        mock_generator = AsyncMock()
        mock_generator.generate = AsyncMock(return_value=_FakeLLMResult())

        mock_persistence = AsyncMock()
        mock_persistence.save = AsyncMock()

        with (
            patch(
                "pwbs.db.postgres.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "pwbs.briefing.generator.BriefingGenerator",
                return_value=mock_generator,
            ),
            patch("pwbs.core.llm_gateway.LLMGateway"),
            patch("pwbs.prompts.registry.PromptRegistry"),
            patch(
                "pwbs.briefing.persistence.BriefingPersistenceService",
                return_value=mock_persistence,
            ),
        ):
            result = await _generate_initial_briefing_async(_OWNER_ID)

        assert result["generated"] is True
        assert result["owner_id"] == _OWNER_ID
        mock_generator.generate.assert_awaited_once()
        mock_persistence.save.assert_awaited_once()

        # Verify persistence call includes trigger context
        save_kwargs = mock_persistence.save.call_args[1]
        assert save_kwargs["title"] == "Dein erstes Briefing"
        assert save_kwargs["trigger_context"]["initial_sync"] is True
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_when_briefings_exist(self) -> None:
        """Idempotent: user already has 3 briefings → no generation."""
        from pwbs.queue.tasks.briefing import _generate_initial_briefing_async

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=_scalar_one_result(3),
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)

        with patch(
            "pwbs.db.postgres.get_session_factory",
            return_value=mock_factory,
        ):
            result = await _generate_initial_briefing_async(_OWNER_ID)

        assert result["generated"] is False
        assert result["reason"] == "briefings_exist"

    @pytest.mark.asyncio
    async def test_skips_when_user_not_found(self) -> None:
        """User deleted between job dispatch and execution → graceful skip."""
        from pwbs.queue.tasks.briefing import _generate_initial_briefing_async

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[
                _scalar_one_result(0),
                _scalar_one_or_none_result(None),
            ]
        )
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_session)

        with patch(
            "pwbs.db.postgres.get_session_factory",
            return_value=mock_factory,
        ):
            result = await _generate_initial_briefing_async(_OWNER_ID)

        assert result["generated"] is False
        assert result["reason"] == "user_not_found"

    @pytest.mark.asyncio
    async def test_double_call_only_generates_once(self) -> None:
        """Simulates concurrent dispatches: second call sees count > 0."""
        from pwbs.queue.tasks.briefing import _generate_initial_briefing_async

        mock_user = MagicMock()
        mock_user.id = _OWNER_UUID

        # First call: count=0 → generates
        session_1 = AsyncMock()
        session_1.execute = AsyncMock(
            side_effect=[
                _scalar_one_result(0),
                _scalar_one_or_none_result(mock_user),
            ]
        )
        session_1.commit = AsyncMock()
        session_1.__aenter__ = AsyncMock(return_value=session_1)
        session_1.__aexit__ = AsyncMock(return_value=False)

        # Second call: count=1 → skips
        session_2 = AsyncMock()
        session_2.execute = AsyncMock(return_value=_scalar_one_result(1))
        session_2.__aenter__ = AsyncMock(return_value=session_2)
        session_2.__aexit__ = AsyncMock(return_value=False)

        call_count = 0

        def factory_side_effect() -> AsyncMock:
            nonlocal call_count
            call_count += 1
            return session_1 if call_count == 1 else session_2

        mock_factory = MagicMock(side_effect=factory_side_effect)
        mock_generator = AsyncMock()
        mock_generator.generate = AsyncMock(return_value=_FakeLLMResult())
        mock_persistence = AsyncMock()
        mock_persistence.save = AsyncMock()

        with (
            patch(
                "pwbs.db.postgres.get_session_factory",
                return_value=mock_factory,
            ),
            patch(
                "pwbs.briefing.generator.BriefingGenerator",
                return_value=mock_generator,
            ),
            patch("pwbs.core.llm_gateway.LLMGateway"),
            patch("pwbs.prompts.registry.PromptRegistry"),
            patch(
                "pwbs.briefing.persistence.BriefingPersistenceService",
                return_value=mock_persistence,
            ),
        ):
            r1 = await _generate_initial_briefing_async(_OWNER_ID)
            r2 = await _generate_initial_briefing_async(_OWNER_ID)

        assert r1["generated"] is True
        assert r2["generated"] is False
        assert mock_generator.generate.await_count == 1


# ---------------------------------------------------------------------------
# Pipeline integration (process_documents triggers initial briefing)
# ---------------------------------------------------------------------------


class TestPipelineTriggersInitialBriefing:
    def test_process_documents_enqueues_initial_briefing(self) -> None:
        """process_documents should dispatch generate_initial_briefing.delay()."""
        from pwbs.queue.tasks.pipeline import process_documents

        mock_chain_instance = MagicMock()
        mock_initial = MagicMock()

        with (
            patch(
                "pwbs.queue.tasks.pipeline.chain",
                return_value=mock_chain_instance,
            ),
            patch(
                "pwbs.queue.tasks.briefing.generate_initial_briefing",
                mock_initial,
            ),
        ):
            # bind=True: Celery injects self, so we only pass the real args
            result = process_documents(["doc-1", "doc-2"], _OWNER_ID)

        mock_chain_instance.apply_async.assert_called_once()
        mock_initial.delay.assert_called_once_with(_OWNER_ID)
        assert "initial_briefing_check" in result["pipeline_steps"]
