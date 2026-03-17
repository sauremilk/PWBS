"""Prompt Registry – versionierte Jinja2-Templates laden und rendern (TASK-067).

Prompts liegen als ``.j2``-Dateien im ``pwbs/prompts/``-Verzeichnis.
Namenskonvention: ``{use_case}.v{version}.j2``
(z.B. ``briefing_morning.v1.j2``).

Jede Datei enthält einen optionalen YAML-Front-Matter-Block (``---``), gefolgt
vom Jinja2-Template-Body.  Das Front-Matter definiert Metadaten wie
``model_preference``, ``temperature`` usw.

Beispiel::

    ---
    model_preference: claude-sonnet-4-20250514
    max_output_tokens: 2000
    temperature: 0.3
    system_prompt: |
      Du bist ein präziser Briefing-Assistent.
    required_context:
      - calendar_events
      - recent_documents
    ---
    ## Morgenbriefing für {{ date }}

    {{ calendar_events }}
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined, select_autoescape

logger = logging.getLogger(__name__)

__all__ = [
    "MissingContextError",
    "PromptNotFoundError",
    "PromptRegistry",
    "PromptRenderError",
    "PromptTemplate",
]

# Regex to extract YAML front matter delimited by ``---``
_FRONT_MATTER_RE = re.compile(
    r"\A\s*---\s*\n(.*?)\n---\s*\n(.*)",
    re.DOTALL,
)

# Regex to parse file names: {use_case}.v{version}.j2
_FILENAME_RE = re.compile(r"^(?P<use_case>.+)\.v(?P<version>\d+)\.j2$")


# ------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------


class PromptNotFoundError(Exception):
    """Raised when the requested prompt template cannot be found."""


class MissingContextError(Exception):
    """Raised when required context variables are missing."""

    def __init__(self, template_id: str, missing: list[str]) -> None:
        self.template_id = template_id
        self.missing = missing
        super().__init__(
            f"Prompt '{template_id}' benötigt fehlende Kontextvariablen: {', '.join(missing)}"
        )


class PromptRenderError(Exception):
    """Raised when Jinja2 rendering fails."""


# ------------------------------------------------------------------
# PromptTemplate dataclass (D1 §3.4)
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """A versioned prompt template loaded from disk.

    Fields match the specification in D1 §3.4 / ARCHITECTURE.md.
    """

    id: str
    """Unique identifier, e.g. ``briefing_morning.v1``."""

    template: str
    """Raw Jinja2 template body (without front matter)."""

    model_preference: str
    """Preferred LLM model, e.g. ``claude-sonnet-4-20250514``."""

    max_output_tokens: int
    """Maximum output tokens for the LLM call."""

    temperature: float
    """LLM temperature setting."""

    system_prompt: str
    """System prompt sent to the LLM alongside the rendered user prompt."""

    required_context: list[str] = field(default_factory=list)
    """Context variable names that MUST be provided at render time."""

    version: int = 1
    """Monotonically increasing version number."""


# ------------------------------------------------------------------
# PromptRegistry
# ------------------------------------------------------------------


class PromptRegistry:
    """Loads, indexes, and renders versioned prompt templates.

    Parameters
    ----------
    prompts_dir:
        Path to the directory containing ``.j2`` template files.
        Defaults to the ``pwbs/prompts/`` package directory.
    """

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self._prompts_dir = prompts_dir or Path(__file__).parent
        # {use_case -> {version -> PromptTemplate}}
        self._templates: dict[str, dict[int, PromptTemplate]] = {}
        self._jinja_env = Environment(
            undefined=StrictUndefined,
            autoescape=select_autoescape(default_for_string=True, default=True),
            keep_trailing_newline=True,
        )
        self._load_all()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, use_case: str, version: int | None = None) -> PromptTemplate:
        """Return a prompt template by use-case and optional version.

        If *version* is ``None``, the highest available version is returned.

        Raises
        ------
        PromptNotFoundError
            If no template matches the request.
        """
        versions = self._templates.get(use_case)
        if not versions:
            raise PromptNotFoundError(
                f"Kein Prompt-Template für use_case='{use_case}' gefunden. "
                f"Verfügbare: {list(self._templates.keys())}"
            )

        if version is not None:
            tpl = versions.get(version)
            if tpl is None:
                raise PromptNotFoundError(
                    f"Prompt '{use_case}' hat keine Version {version}. "
                    f"Verfügbare Versionen: {sorted(versions.keys())}"
                )
            return tpl

        # Latest version
        latest = max(versions.keys())
        return versions[latest]

    def render(
        self,
        template: PromptTemplate,
        context: dict[str, Any],
    ) -> str:
        """Render a prompt template with the given context variables.

        Validates ``required_context`` before rendering.

        Raises
        ------
        MissingContextError
            If any required context variable is missing.
        PromptRenderError
            If Jinja2 rendering fails.
        """
        # Validate required context
        missing = [k for k in template.required_context if k not in context]
        if missing:
            raise MissingContextError(template.id, missing)

        try:
            jinja_tpl = self._jinja_env.from_string(template.template)
            return jinja_tpl.render(**context)
        except Exception as exc:
            raise PromptRenderError(
                f"Rendering von Prompt '{template.id}' fehlgeschlagen: {exc}"
            ) from exc

    def list_use_cases(self) -> list[str]:
        """Return all registered use-case names."""
        return sorted(self._templates.keys())

    def list_versions(self, use_case: str) -> list[int]:
        """Return all registered versions for a use-case."""
        versions = self._templates.get(use_case)
        if not versions:
            return []
        return sorted(versions.keys())

    def reload(self) -> None:
        """Re-scan the prompts directory and reload all templates."""
        self._templates.clear()
        self._load_all()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        """Scan the prompts directory for ``.j2`` files and load them."""
        if not self._prompts_dir.is_dir():
            logger.warning("Prompts-Verzeichnis existiert nicht: %s", self._prompts_dir)
            return

        for path in sorted(self._prompts_dir.glob("*.j2")):
            try:
                self._load_file(path)
            except Exception:
                logger.exception("Fehler beim Laden von Prompt-Datei: %s", path)

    def _load_file(self, path: Path) -> None:
        """Parse a single ``.j2`` file and register its template."""
        match = _FILENAME_RE.match(path.name)
        if not match:
            logger.warning(
                "Prompt-Datei '%s' entspricht nicht dem Schema "
                "{use_case}.v{version}.j2 – wird übersprungen.",
                path.name,
            )
            return

        use_case = match.group("use_case")
        version = int(match.group("version"))
        template_id = f"{use_case}.v{version}"

        raw = path.read_text(encoding="utf-8")
        meta, body = self._parse_front_matter(raw)

        tpl = PromptTemplate(
            id=template_id,
            template=body,
            model_preference=str(meta.get("model_preference", "")),
            max_output_tokens=int(meta.get("max_output_tokens", 4096)),
            temperature=float(meta.get("temperature", 0.3)),
            system_prompt=str(meta.get("system_prompt", "")),
            required_context=list(meta.get("required_context", [])),
            version=version,
        )

        self._templates.setdefault(use_case, {})[version] = tpl
        logger.debug("Prompt geladen: %s (v%d) aus %s", use_case, version, path)

    @staticmethod
    def _parse_front_matter(raw: str) -> tuple[dict[str, Any], str]:
        """Split a template file into YAML front matter dict and body string."""
        match = _FRONT_MATTER_RE.match(raw)
        if not match:
            return {}, raw

        yaml_str = match.group(1)
        body = match.group(2)

        meta = yaml.safe_load(yaml_str)
        if not isinstance(meta, dict):
            return {}, raw

        return meta, body
