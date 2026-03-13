"""Shared pytest fixtures for PWBS backend tests.

All external dependencies (databases, LLM, HTTP) must be mocked.
No real network access in unit tests.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def anyio_backend() -> str:
    """Use asyncio as the default async backend."""
    return "asyncio"