"""Shared pytest fixtures for PWBS backend tests.

All external dependencies (databases, LLM, HTTP) must be mocked.
No real network access in unit tests.
"""

from __future__ import annotations

import os

import pytest

from pwbs.core.config import get_settings

# Required env vars for Settings instantiation in test mode.
# Set early via pytest_configure so module-level code like
# ``app = create_app()`` can resolve Settings at import time.
_TEST_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-for-unit-tests",
    "JWT_ALGORITHM": "HS256",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "15",
    "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "30",
    "ENCRYPTION_MASTER_KEY": "test-master-key-for-unit-tests",
}


def pytest_configure(config: pytest.Config) -> None:
    """Set required environment variables before test collection."""
    for key, value in _TEST_ENV.items():
        os.environ.setdefault(key, value)
    # Ensure Settings cache is clear so tests start fresh
    get_settings.cache_clear()


@pytest.fixture()
def anyio_backend() -> str:
    """Use asyncio as the default async backend."""
    return "asyncio"
