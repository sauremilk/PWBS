"""Validate Locust JSON report against TASK-112 thresholds.

Usage:
  python -m tests.load.validate_report load_report.json

Exit code 0 = all thresholds met, 1 = violations found.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Default thresholds (can be overridden via config.json)
_DEFAULT_THRESHOLDS = {
    "api_general_p95_ms": 500,
    "search_p95_ms": 2000,
    "briefing_gen_p95_ms": 10000,
    "max_error_rate_percent": 1.0,
}

# Endpoint name patterns for grouping
_SEARCH_PATTERNS = ["search"]
_BRIEFING_GEN_PATTERNS = ["briefings/generate"]


def _classify_endpoint(name: str) -> str:
    """Classify a Locust request name into a threshold group."""
    name_lower = name.lower()
    for pattern in _BRIEFING_GEN_PATTERNS:
        if pattern in name_lower:
            return "briefing_gen"
    for pattern in _SEARCH_PATTERNS:
        if pattern in name_lower:
            return "search"
    return "api_general"


def validate_report(
    report_data: list[dict],
    thresholds: dict[str, float] | None = None,
) -> list[str]:
    """Validate Locust stats against thresholds.

    Returns a list of violation messages (empty = all OK).
    """
    thresholds = thresholds or _DEFAULT_THRESHOLDS
    violations: list[str] = []

    total_requests = 0
    total_failures = 0

    for entry in report_data:
        name = entry.get("name", "")
        if name == "Aggregated":
            total_requests = entry.get("num_requests", 0)
            total_failures = entry.get("num_failures", 0)
            continue

        p95 = entry.get("response_times", {}).get("95%", 0) if isinstance(
            entry.get("response_times"), dict
        ) else 0

        # Locust JSON format uses different keys depending on version
        if not p95:
            p95 = entry.get("95%", 0)

        group = _classify_endpoint(name)
        threshold_key = f"{group}_p95_ms"
        threshold = thresholds.get(threshold_key, _DEFAULT_THRESHOLDS.get(threshold_key, 10000))

        if p95 > threshold:
            violations.append(
                f"THRESHOLD VIOLATION: {name} p95={p95}ms > {threshold}ms ({group})"
            )

    # Error rate check
    if total_requests > 0:
        error_rate = (total_failures / total_requests) * 100
        max_error_rate = thresholds.get(
            "max_error_rate_percent",
            _DEFAULT_THRESHOLDS["max_error_rate_percent"],
        )
        if error_rate > max_error_rate:
            violations.append(
                f"ERROR RATE VIOLATION: {error_rate:.2f}% > {max_error_rate}% "
                f"({total_failures}/{total_requests} requests failed)"
            )

    return violations


def main() -> None:
    """CLI entry point for report validation."""
    if len(sys.argv) < 2:
        print("Usage: python -m tests.load.validate_report <report.json> [config.json]")
        sys.exit(2)

    report_path = Path(sys.argv[1])
    if not report_path.exists():
        print(f"Report file not found: {report_path}")
        sys.exit(2)

    thresholds = dict(_DEFAULT_THRESHOLDS)
    if len(sys.argv) >= 3:
        config_path = Path(sys.argv[2])
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                thresholds.update(config.get("thresholds", {}))

    with open(report_path) as f:
        report_data = json.load(f)

    violations = validate_report(report_data, thresholds)

    if violations:
        print("LOAD TEST FAILED -- Threshold violations:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("LOAD TEST PASSED -- All thresholds met.")
        sys.exit(0)


if __name__ == "__main__":
    main()
