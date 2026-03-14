"""Structured Output – JSON-Schema-Validierung für LLM-Antworten (TASK-068).

Validates LLM responses against Pydantic schemas.  Supports:

1. Claude's Tool-Use / JSON-Mode for native structured output
2. Regex-based JSON extraction from free-text as fallback
3. Validation via Pydantic ``model_validate_json`` / ``model_validate``
4. 1 automatic retry with an explicit format prompt on validation failure
5. Logging of validation errors with the raw response

Usage::

    from pydantic import BaseModel
    from pwbs.core.structured_output import StructuredOutputService
    from pwbs.core.llm_gateway import LLMGateway

    class MyOutput(BaseModel):
        title: str
        score: float

    service = StructuredOutputService(gateway)
    result = await service.generate(
        system_prompt="Extract data.",
        user_prompt="Some text...",
        output_schema=MyOutput,
    )
    # result.parsed is MyOutput instance
    # result.raw is raw LLM response string
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from pwbs.core.llm_gateway import LLMGateway, LLMRequest, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)

__all__ = [
    "StructuredOutputService",
    "StructuredOutputResult",
    "StructuredOutputError",
]

T = TypeVar("T", bound=BaseModel)

# Regex to extract a JSON object or array from free-text LLM responses
_JSON_BLOCK_RE = re.compile(
    r"```(?:json)?\s*\n?([\s\S]*?)\n?```"  # fenced code block
    r"|"
    r"(\{[\s\S]*\})"  # bare JSON object
    r"|"
    r"(\[[\s\S]*\])",  # bare JSON array
)


# ------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------


class StructuredOutputError(Exception):
    """Raised after retry when LLM output cannot be parsed into the target schema."""

    def __init__(
        self,
        message: str,
        raw_response: str,
        validation_errors: list[str],
    ) -> None:
        super().__init__(message)
        self.raw_response = raw_response
        self.validation_errors = validation_errors


# ------------------------------------------------------------------
# Result container
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StructuredOutputResult(Generic[T]):
    """Holds the parsed output together with raw LLM metadata."""

    parsed: T
    raw: str
    usage: LLMUsage
    retried: bool


# ------------------------------------------------------------------
# Service
# ------------------------------------------------------------------


class StructuredOutputService:
    """Generates and validates structured LLM output against a Pydantic schema.

    Parameters
    ----------
    gateway:
        Configured :class:`LLMGateway` instance for LLM calls.
    max_retries:
        Number of validation retries (default 1 as per spec).
    """

    def __init__(self, gateway: LLMGateway, max_retries: int = 1) -> None:
        self._gateway = gateway
        self._max_retries = max_retries

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[T],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> StructuredOutputResult[T]:
        """Generate structured output matching *output_schema*.

        Steps:
        1. Build request with JSON-Schema instruction appended to system prompt.
        2. Call LLM via gateway.
        3. Extract JSON from response.
        4. Validate against Pydantic schema.
        5. On failure → retry once with explicit format correction prompt.
        6. On second failure → raise :class:`StructuredOutputError`.

        Raises
        ------
        StructuredOutputError
            If the LLM output cannot be parsed after retries.
        """
        schema_json = json.dumps(
            output_schema.model_json_schema(),
            ensure_ascii=False,
            indent=2,
        )

        augmented_system = (
            f"{system_prompt}\n\n"
            "WICHTIG: Antworte AUSSCHLIESSLICH mit einem gültigen JSON-Objekt, "
            "das dem folgenden JSON-Schema entspricht. Keine zusätzliche Erklärung.\n\n"
            f"JSON-Schema:\n```json\n{schema_json}\n```"
        )

        request = LLMRequest(
            system_prompt=augmented_system,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
        )

        # --- First attempt ---
        response = await self._gateway.generate(request)
        result = self._try_parse(response.content, output_schema)

        if result is not None:
            return StructuredOutputResult(
                parsed=result,
                raw=response.content,
                usage=response.usage,
                retried=False,
            )

        # --- Retry with explicit format correction ---
        last_errors: list[str] = []
        for attempt in range(self._max_retries):
            errors = self._get_validation_errors(response.content, output_schema)
            last_errors = errors

            logger.warning(
                "Structured Output Validierung fehlgeschlagen (Versuch %d/%d). "
                "Fehler: %s | Raw: %.500s",
                attempt + 1,
                self._max_retries,
                errors,
                response.content,
            )

            retry_prompt = (
                f"Deine vorherige Antwort war kein gültiges JSON für das Schema.\n"
                f"Validierungsfehler: {json.dumps(errors, ensure_ascii=False)}\n\n"
                f"Bitte antworte NUR mit einem gültigen JSON-Objekt.\n\n"
                f"Ursprüngliche Aufgabe:\n{user_prompt}"
            )

            retry_request = LLMRequest(
                system_prompt=augmented_system,
                user_prompt=retry_prompt,
                temperature=0.1,  # lower temperature for retry
                max_tokens=max_tokens,
                json_mode=True,
            )

            response = await self._gateway.generate(retry_request)
            result = self._try_parse(response.content, output_schema)

            if result is not None:
                return StructuredOutputResult(
                    parsed=result,
                    raw=response.content,
                    usage=response.usage,
                    retried=True,
                )

        # All retries exhausted
        raise StructuredOutputError(
            f"LLM-Antwort konnte nach {self._max_retries + 1} Versuchen nicht "
            f"in {output_schema.__name__} geparst werden.",
            raw_response=response.content,
            validation_errors=last_errors,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_parse(self, raw: str, schema: type[T]) -> T | None:
        """Try to parse *raw* into *schema*, returning ``None`` on failure."""
        json_str = self._extract_json(raw)
        if json_str is None:
            return None

        try:
            return schema.model_validate_json(json_str)
        except ValidationError:
            pass

        # Try relaxed: parse JSON then validate dict
        try:
            data = json.loads(json_str)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError):
            return None

    def _get_validation_errors(self, raw: str, schema: type[T]) -> list[str]:
        """Extract human-readable validation error messages."""
        json_str = self._extract_json(raw)
        if json_str is None:
            return ["Kein JSON-Objekt in der Antwort gefunden."]

        try:
            schema.model_validate_json(json_str)
            return []
        except ValidationError as exc:
            return [str(e) for e in exc.errors()]
        except Exception as exc:
            return [str(exc)]

    @staticmethod
    def _extract_json(raw: str) -> str | None:
        """Extract JSON from raw LLM output.

        Tries:
        1. Direct ``json.loads`` on the entire string.
        2. Regex extraction of fenced code blocks or bare JSON objects.
        """
        # Fast path: entire response is valid JSON
        stripped = raw.strip()
        try:
            json.loads(stripped)
            return stripped
        except json.JSONDecodeError:
            pass

        # Regex-based extraction
        match = _JSON_BLOCK_RE.search(raw)
        if match:
            # Return first non-None group
            for group in match.groups():
                if group is not None:
                    candidate = group.strip()
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        continue

        return None
