"""Locust load-test scenarios for PWBS API (TASK-112).

Simulates 20 concurrent users with three scenario groups:
  1. Dashboard load (GET briefings + connectors status)
  2. Search queries (POST /api/v1/search/)
  3. Briefing generation (POST /api/v1/briefings/generate)

Target thresholds (p95):
  - API endpoints (general): < 500ms
  - Semantic search: < 2000ms
  - Briefing generation: < 10000ms
  - Error rate: < 1%

Usage:
  # Headless (CI):
  locust -f tests/load/locustfile.py --headless -u 20 -r 5 -t 60s \
         --host http://localhost:8000 --json > load_report.json

  # With Web UI:
  locust -f tests/load/locustfile.py --host http://localhost:8000
"""

from __future__ import annotations

import uuid

from locust import HttpUser, between, tag, task

# ---------------------------------------------------------------------------
# Auth helper -- login once per simulated user
# ---------------------------------------------------------------------------


class PWBSUser(HttpUser):
    """Simulated PWBS user that authenticates on start and runs mixed scenarios."""

    wait_time = between(1, 3)
    abstract = True

    #: Auth token acquired in on_start
    _token: str = ""
    _user_id: str = ""

    def on_start(self) -> None:
        """Register + login a test user; store JWT for subsequent requests."""
        email = f"loadtest-{uuid.uuid4().hex[:8]}@pwbs-test.local"
        password = "LoadTest!Secure#2026"

        # Register
        resp = self.client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "display_name": "Load Test"},
            name="/api/v1/auth/register",
        )
        if resp.status_code not in (201, 409):  # 409 = already exists
            resp.failure(f"Register failed: {resp.status_code}")

        # Login
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
            name="/api/v1/auth/login",
        )
        if resp.status_code == 200:
            data = resp.json()
            self._token = data.get("access_token", "")
        else:
            resp.failure(f"Login failed: {resp.status_code}")

    @property
    def _headers(self) -> dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}


# ---------------------------------------------------------------------------
# Scenario 1: Dashboard Load
# ---------------------------------------------------------------------------


class DashboardUser(PWBSUser):
    """Simulates dashboard page load -- parallel GETs for briefings + connectors."""

    weight = 5  # most common scenario

    @tag("dashboard")
    @task(3)
    def get_briefings(self) -> None:
        self.client.get(
            "/api/v1/briefings/",
            headers=self._headers,
            name="/api/v1/briefings/ [list]",
        )

    @tag("dashboard")
    @task(2)
    def get_latest_briefings(self) -> None:
        self.client.get(
            "/api/v1/briefings/latest",
            headers=self._headers,
            name="/api/v1/briefings/latest",
        )

    @tag("dashboard")
    @task(2)
    def get_connectors(self) -> None:
        self.client.get(
            "/api/v1/connectors/",
            headers=self._headers,
            name="/api/v1/connectors/ [list]",
        )

    @tag("dashboard")
    @task(1)
    def get_user_settings(self) -> None:
        self.client.get(
            "/api/v1/user/settings",
            headers=self._headers,
            name="/api/v1/user/settings",
        )


# ---------------------------------------------------------------------------
# Scenario 2: Search
# ---------------------------------------------------------------------------


class SearchUser(PWBSUser):
    """Simulates search queries."""

    weight = 3

    _QUERIES = [
        "Projektfortschritt letzte Woche",
        "Meeting-Notizen mit Team",
        "Entscheidungen Q1 2026",
        "Budget-Planung nächstes Quartal",
        "Kunde XYZ Vertragsstatus",
    ]

    @tag("search")
    @task
    def search_hybrid(self) -> None:
        import random

        query = random.choice(self._QUERIES)
        self.client.post(
            "/api/v1/search/",
            json={"query": query, "mode": "hybrid", "top_k": 10},
            headers=self._headers,
            name="/api/v1/search/ [hybrid]",
        )


# ---------------------------------------------------------------------------
# Scenario 3: Briefing Generation
# ---------------------------------------------------------------------------


class BriefingGenerationUser(PWBSUser):
    """Simulates on-demand briefing generation."""

    weight = 2

    @tag("briefing-gen")
    @task
    def generate_morning_briefing(self) -> None:
        self.client.post(
            "/api/v1/briefings/generate",
            json={"type": "morning"},
            headers=self._headers,
            name="/api/v1/briefings/generate [morning]",
        )

    @tag("briefing-gen")
    @task
    def generate_project_briefing(self) -> None:
        self.client.post(
            "/api/v1/briefings/generate",
            json={"type": "project", "context": {"project_name": "PWBS MVP"}},
            headers=self._headers,
            name="/api/v1/briefings/generate [project]",
        )
