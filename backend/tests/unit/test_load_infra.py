"""Tests for load-test infrastructure (TASK-112).

Tests the load-test tooling itself (threshold validation, endpoint
classification, Locust user definitions), NOT the actual load against
a running server.
"""

from __future__ import annotations

import importlib

import pytest

from tests.load.validate_report import (
    _DEFAULT_THRESHOLDS,
    _classify_endpoint,
    validate_report,
)


# ---------------------------------------------------------------------------
# _classify_endpoint
# ---------------------------------------------------------------------------


class TestClassifyEndpoint:
    def test_search_endpoint(self) -> None:
        assert _classify_endpoint("/api/v1/search/ [hybrid]") == "search"

    def test_briefing_generate(self) -> None:
        assert _classify_endpoint("/api/v1/briefings/generate [morning]") == "briefing_gen"

    def test_general_endpoint(self) -> None:
        assert _classify_endpoint("/api/v1/user/settings") == "api_general"

    def test_connectors_endpoint(self) -> None:
        assert _classify_endpoint("/api/v1/connectors/ [list]") == "api_general"

    def test_briefing_list_is_general(self) -> None:
        # Listing briefings is NOT generation
        assert _classify_endpoint("/api/v1/briefings/ [list]") == "api_general"


# ---------------------------------------------------------------------------
# validate_report
# ---------------------------------------------------------------------------


class TestValidateReport:
    def test_all_within_thresholds(self) -> None:
        report = [
            {
                "name": "/api/v1/user/settings",
                "response_times": {"95%": 200},
                "num_requests": 100,
                "num_failures": 0,
            },
            {
                "name": "/api/v1/search/ [hybrid]",
                "response_times": {"95%": 1500},
                "num_requests": 50,
                "num_failures": 0,
            },
            {
                "name": "Aggregated",
                "num_requests": 150,
                "num_failures": 0,
            },
        ]
        violations = validate_report(report)
        assert violations == []

    def test_p95_violation_general(self) -> None:
        report = [
            {
                "name": "/api/v1/user/settings",
                "response_times": {"95%": 600},
                "num_requests": 100,
                "num_failures": 0,
            },
            {
                "name": "Aggregated",
                "num_requests": 100,
                "num_failures": 0,
            },
        ]
        violations = validate_report(report)
        assert len(violations) == 1
        assert "THRESHOLD VIOLATION" in violations[0]
        assert "600" in violations[0]

    def test_p95_violation_search(self) -> None:
        report = [
            {
                "name": "/api/v1/search/ [hybrid]",
                "response_times": {"95%": 2500},
                "num_requests": 50,
                "num_failures": 0,
            },
            {
                "name": "Aggregated",
                "num_requests": 50,
                "num_failures": 0,
            },
        ]
        violations = validate_report(report)
        assert len(violations) == 1
        assert "search" in violations[0]

    def test_p95_violation_briefing_gen(self) -> None:
        report = [
            {
                "name": "/api/v1/briefings/generate [morning]",
                "response_times": {"95%": 12000},
                "num_requests": 20,
                "num_failures": 0,
            },
            {
                "name": "Aggregated",
                "num_requests": 20,
                "num_failures": 0,
            },
        ]
        violations = validate_report(report)
        assert len(violations) == 1
        assert "briefing_gen" in violations[0]

    def test_error_rate_violation(self) -> None:
        report = [
            {
                "name": "Aggregated",
                "num_requests": 100,
                "num_failures": 5,  # 5% > 1%
            },
        ]
        violations = validate_report(report)
        assert len(violations) == 1
        assert "ERROR RATE" in violations[0]
        assert "5.00%" in violations[0]

    def test_error_rate_within_threshold(self) -> None:
        report = [
            {
                "name": "Aggregated",
                "num_requests": 1000,
                "num_failures": 5,  # 0.5% < 1%
            },
        ]
        violations = validate_report(report)
        assert violations == []

    def test_custom_thresholds(self) -> None:
        report = [
            {
                "name": "/api/v1/user/settings",
                "response_times": {"95%": 300},
                "num_requests": 50,
                "num_failures": 0,
            },
            {
                "name": "Aggregated",
                "num_requests": 50,
                "num_failures": 0,
            },
        ]
        # Strict threshold: 200ms
        violations = validate_report(report, {"api_general_p95_ms": 200, "max_error_rate_percent": 1.0})
        assert len(violations) == 1

    def test_empty_report(self) -> None:
        violations = validate_report([])
        assert violations == []

    def test_multiple_violations(self) -> None:
        report = [
            {
                "name": "/api/v1/user/settings",
                "response_times": {"95%": 600},
                "num_requests": 100,
                "num_failures": 0,
            },
            {
                "name": "/api/v1/search/ [hybrid]",
                "response_times": {"95%": 3000},
                "num_requests": 50,
                "num_failures": 0,
            },
            {
                "name": "Aggregated",
                "num_requests": 150,
                "num_failures": 10,
            },
        ]
        violations = validate_report(report)
        assert len(violations) == 3  # 2 p95 + 1 error rate


# ---------------------------------------------------------------------------
# Locustfile definitions
# ---------------------------------------------------------------------------


class TestLocustConfig:
    def test_locustfile_imports(self) -> None:
        """Verify locustfile can be imported without errors."""
        mod = importlib.import_module("tests.load.locustfile")
        assert hasattr(mod, "DashboardUser")
        assert hasattr(mod, "SearchUser")
        assert hasattr(mod, "BriefingGenerationUser")

    def test_user_weights(self) -> None:
        from tests.load.locustfile import (
            BriefingGenerationUser,
            DashboardUser,
            SearchUser,
        )

        assert DashboardUser.weight == 5
        assert SearchUser.weight == 3
        assert BriefingGenerationUser.weight == 2

    def test_pwbs_user_is_abstract(self) -> None:
        from tests.load.locustfile import PWBSUser

        assert PWBSUser.abstract is True


# ---------------------------------------------------------------------------
# Config file
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_config_json_valid(self) -> None:
        import json
        from pathlib import Path

        config_path = Path(__file__).parent.parent.parent / "tests" / "load" / "config.json"
        with open(config_path) as f:
            config = json.load(f)

        assert config["users"] == 20
        assert config["spawn_rate"] == 5
        assert "thresholds" in config
        assert config["thresholds"]["api_general_p95_ms"] == 500
        assert config["thresholds"]["search_p95_ms"] == 2000
        assert config["thresholds"]["briefing_gen_p95_ms"] == 10000
        assert config["thresholds"]["max_error_rate_percent"] == 1.0
