"""Compare pytest-benchmark results against a stored baseline (TASK-170).

Usage:
  python -m tests.performance.compare_baseline \\
      --current .benchmarks/current.json \\
      --baseline .benchmarks/baseline.json \\
      --thresholds tests/performance/thresholds.yaml \\
      [--output report.md]

Exit code:
  0 = all within thresholds
  1 = regression detected (any benchmark exceeds baseline by >20% or absolute threshold)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path

import yaml

_REGRESSION_TOLERANCE = 0.20  # 20% tolerance for regression vs baseline


def load_benchmark_results(path: Path) -> dict[str, dict[str, float]]:
    """Load pytest-benchmark JSON output into {test_name: {stats}}."""
    with open(path) as f:
        data = json.load(f)

    results: dict[str, dict[str, float]] = {}
    for bench in data.get("benchmarks", []):
        name = bench["name"]
        stats = bench.get("stats", {})
        results[name] = {
            "mean_ms": stats.get("mean", 0) * 1000,
            "median_ms": stats.get("median", 0) * 1000,
            "stddev_ms": stats.get("stddev", 0) * 1000,
            "min_ms": stats.get("min", 0) * 1000,
            "max_ms": stats.get("max", 0) * 1000,
            "rounds": stats.get("rounds", 0),
        }
    return results


def load_thresholds(path: Path) -> dict[str, float]:
    """Load absolute thresholds from YAML."""
    with open(path) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("thresholds", {})


def compare(
    current: dict[str, dict[str, float]],
    baseline: dict[str, dict[str, float]] | None,
    thresholds: Mapping[str, float | int],
) -> tuple[list[str], list[str], str]:
    """Compare current results to baseline.

    Returns: (violations, warnings, markdown_report)
    """
    violations: list[str] = []
    warnings: list[str] = []
    rows: list[str] = []

    api_threshold = thresholds.get("api_general_p95_ms", 500)

    rows.append("| Benchmark | Current (ms) | Baseline (ms) | Delta | Status |")
    rows.append("|-----------|-------------|--------------|-------|--------|")

    for test_name, stats in sorted(current.items()):
        curr_mean = stats["mean_ms"]
        baseline_mean: float | None = None
        delta_str = "N/A"
        status = "OK"

        if baseline and test_name in baseline:
            baseline_mean = baseline[test_name]["mean_ms"]
            if baseline_mean > 0:
                delta_pct = ((curr_mean - baseline_mean) / baseline_mean) * 100
                delta_str = f"{delta_pct:+.1f}%"

                if delta_pct > _REGRESSION_TOLERANCE * 100:
                    status = "REGRESSION"
                    violations.append(
                        f"{test_name}: {curr_mean:.1f}ms vs baseline "
                        f"{baseline_mean:.1f}ms ({delta_str})"
                    )
                elif delta_pct > (_REGRESSION_TOLERANCE / 2) * 100:
                    status = "WARNING"
                    warnings.append(
                        f"{test_name}: {curr_mean:.1f}ms vs baseline "
                        f"{baseline_mean:.1f}ms ({delta_str})"
                    )
        else:
            delta_str = "new"

        # Check absolute threshold (treat all DB benchmarks as api_general)
        if curr_mean > api_threshold:
            status = "THRESHOLD"
            violations.append(f"{test_name}: {curr_mean:.1f}ms exceeds threshold {api_threshold}ms")

        baseline_str = f"{baseline_mean:.1f}" if baseline_mean is not None else "—"
        emoji = {"OK": "✅", "WARNING": "⚠️", "REGRESSION": "❌", "THRESHOLD": "🚫"}.get(
            status, "❓"
        )
        rows.append(
            f"| `{test_name}` | {curr_mean:.1f} | {baseline_str} | {delta_str} | {emoji} {status} |"
        )

    report_lines = [
        "## Performance Regression Report",
        "",
        f"**Benchmarks:** {len(current)}",
        f"**Violations:** {len(violations)}",
        f"**Warnings:** {len(warnings)}",
        "",
    ]
    report_lines.extend(rows)

    if violations:
        report_lines.extend(["", "### Violations", ""])
        for v in violations:
            report_lines.append(f"- ❌ {v}")

    if warnings:
        report_lines.extend(["", "### Warnings", ""])
        for w in warnings:
            report_lines.append(f"- ⚠️ {w}")

    markdown = "\n".join(report_lines)
    return violations, warnings, markdown


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Compare benchmark results")
    parser.add_argument("--current", required=True, help="Current benchmark JSON")
    parser.add_argument("--baseline", default=None, help="Baseline benchmark JSON")
    parser.add_argument("--thresholds", required=True, help="Thresholds YAML")
    parser.add_argument("--output", default=None, help="Output markdown report")

    args = parser.parse_args()

    current = load_benchmark_results(Path(args.current))
    baseline = (
        load_benchmark_results(Path(args.baseline))
        if args.baseline and Path(args.baseline).exists()
        else None
    )
    thresholds = load_thresholds(Path(args.thresholds))

    violations, warnings, report = compare(current, baseline, thresholds)

    print(report)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")

    sys.exit(1 if violations else 0)


if __name__ == "__main__":
    main()
