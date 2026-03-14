"""Unit tests for compare_baseline.py (TASK-170)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from tests.performance.compare_baseline import (
    compare,
    load_benchmark_results,
)


def _make_benchmark_json(benchmarks: list[dict]) -> str:
    """Create a minimal pytest-benchmark JSON structure."""
    full = {
        "machine_info": {},
        "commit_info": {},
        "benchmarks": benchmarks,
    }
    return json.dumps(full)


def _make_bench(name: str, mean_s: float) -> dict:
    return {
        "name": name,
        "stats": {
            "mean": mean_s,
            "median": mean_s,
            "stddev": mean_s * 0.1,
            "min": mean_s * 0.9,
            "max": mean_s * 1.1,
            "rounds": 5,
        },
    }


class TestLoadBenchmarkResults:
    def test_loads_and_converts_to_ms(self, tmp_path: Path) -> None:
        data = _make_benchmark_json([_make_bench("test_foo", 0.1)])
        p = tmp_path / "bench.json"
        p.write_text(data, encoding="utf-8")

        results = load_benchmark_results(p)
        assert "test_foo" in results
        assert abs(results["test_foo"]["mean_ms"] - 100.0) < 0.01

    def test_empty_benchmarks(self, tmp_path: Path) -> None:
        data = _make_benchmark_json([])
        p = tmp_path / "bench.json"
        p.write_text(data, encoding="utf-8")

        results = load_benchmark_results(p)
        assert results == {}


class TestCompare:
    def test_no_baseline_all_under_threshold(self) -> None:
        current = {"test_a": {"mean_ms": 50.0}}
        thresholds = {"api_general_p95_ms": 500}

        violations, warnings, report = compare(current, None, thresholds)
        assert len(violations) == 0
        assert "test_a" in report
        assert "OK" in report

    def test_regression_detected(self) -> None:
        current = {"test_a": {"mean_ms": 200.0}}
        baseline = {"test_a": {"mean_ms": 100.0}}
        thresholds = {"api_general_p95_ms": 500}

        violations, warnings, report = compare(current, baseline, thresholds)
        assert len(violations) > 0
        assert "REGRESSION" in report

    def test_threshold_exceeded(self) -> None:
        current = {"test_a": {"mean_ms": 600.0}}
        thresholds = {"api_general_p95_ms": 500}

        violations, warnings, report = compare(current, None, thresholds)
        assert len(violations) > 0
        assert "THRESHOLD" in report

    def test_warning_for_moderate_increase(self) -> None:
        current = {"test_a": {"mean_ms": 115.0}}
        baseline = {"test_a": {"mean_ms": 100.0}}
        thresholds = {"api_general_p95_ms": 500}

        violations, warnings, report = compare(current, baseline, thresholds)
        assert len(violations) == 0
        assert len(warnings) > 0
        assert "WARNING" in report

    def test_new_benchmark_without_baseline(self) -> None:
        current = {"test_new": {"mean_ms": 50.0}}
        baseline = {"test_old": {"mean_ms": 100.0}}
        thresholds = {"api_general_p95_ms": 500}

        violations, warnings, report = compare(current, baseline, thresholds)
        assert len(violations) == 0
        assert "new" in report
