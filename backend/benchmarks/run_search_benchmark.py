"""Run search quality benchmarks against the evaluation dataset.

This script evaluates all four search modes (semantic, keyword, hybrid,
hybrid+reranked) using the ground-truth queries in ``search_eval_dataset.py``
and writes results to ``benchmarks/results/``.

Usage
-----
Against a live system (requires running Weaviate + PostgreSQL)::

    cd backend
    python -m benchmarks.run_search_benchmark --live --owner-id <UUID>

Dry run with a mock search function (validates framework correctness)::

    cd backend
    python -m benchmarks.run_search_benchmark --dry-run

"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

from benchmarks.search_eval_dataset import EVAL_DATASET
from pwbs.search.evaluation import EvalReport, SearchEvaluator


def _build_mock_search(hit_rate: float = 0.4, seed: int = 42):
    """Return a deterministic mock search function.

    Simulates a search backend that returns ``hit_rate`` fraction of
    relevant documents (randomly sampled) mixed with irrelevant results.
    Useful for validating that the evaluation framework itself works.
    """
    rng = random.Random(seed)

    async def mock_search(query: str, top_k: int) -> list[str]:
        # Find matching query in dataset
        for eq in EVAL_DATASET.queries:
            if eq.query == query:
                relevant = list(eq.relevant_ids)
                # Sample a subset of relevant docs based on hit_rate
                n_hits = max(1, int(len(relevant) * hit_rate)) if relevant else 0
                hits = rng.sample(relevant, min(n_hits, len(relevant))) if relevant else []
                # Fill remaining slots with fake IDs
                filler = [f"irrelevant-{rng.randint(1000, 9999)}" for _ in range(top_k - len(hits))]
                results = hits + filler
                rng.shuffle(results)
                return results[:top_k]
        return [f"irrelevant-{rng.randint(1000, 9999)}" for _ in range(top_k)]

    return mock_search


def _report_to_dict(report: EvalReport) -> dict:
    """Serialize an EvalReport to a JSON-compatible dict."""
    return {
        "config_name": report.config_name,
        "top_k": report.top_k,
        "num_queries": report.num_queries,
        "metrics": {
            m.name: {"mean": round(m.mean, 4), "median": round(m.median, 4), "std": round(m.std, 4)}
            for m in report.metrics
        },
    }


async def run_dry_benchmark() -> dict:
    """Run benchmark with mock search functions at different hit rates."""
    evaluator = SearchEvaluator(EVAL_DATASET)
    results: dict = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset": EVAL_DATASET.name,
        "num_queries": len(EVAL_DATASET.queries),
        "mode": "dry-run (mock search)",
        "reports": {},
    }

    configs = [
        ("mock-low (20% hit rate)", 0.2),
        ("mock-medium (40% hit rate)", 0.4),
        ("mock-high (80% hit rate)", 0.8),
        ("mock-perfect (100% hit rate)", 1.0),
    ]

    for name, hit_rate in configs:
        search_fn = _build_mock_search(hit_rate=hit_rate)
        report = await evaluator.evaluate(search_fn, top_k=10, config_name=name)
        results["reports"][name] = _report_to_dict(report)
        print(report.summary())
        print()

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PWBS search quality benchmarks")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate framework with mock search",
    )
    parser.add_argument("--live", action="store_true", help="Run against live search services")
    parser.add_argument("--owner-id", type=str, help="User UUID for live evaluation")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results per query")
    args = parser.parse_args()

    if not args.dry_run and not args.live:
        parser.error("Specify --dry-run or --live")

    if args.live:
        print(
            "Live benchmark not yet wired — run --dry-run to validate the framework.",
            file=sys.stderr,
        )
        sys.exit(1)

    results = asyncio.run(run_dry_benchmark())

    # Write results to file
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d")
    out_path = results_dir / f"search-quality-{timestamp}.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    main()
