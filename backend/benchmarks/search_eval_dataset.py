"""Search quality evaluation dataset for PWBS hybrid search.

Contains 30 realistic knowledge-worker queries with graded relevance
judgments.  Each query simulates a real information need that a PWBS user
would have (meeting prep, project context, decision history, person
lookup, etc.).

The IDs are synthetic chunk identifiers.  To run the benchmark against a
live Weaviate instance, replace them with real chunk UUIDs from the
``Document`` and ``Chunk`` tables after ingesting the sample corpus.

Usage
-----
::

    from benchmarks.search_eval_dataset import EVAL_DATASET
    from pwbs.search.evaluation import SearchEvaluator

    evaluator = SearchEvaluator(EVAL_DATASET)
    report = await evaluator.evaluate(search_fn, top_k=10)
    print(report.summary())

"""

from __future__ import annotations

from pwbs.search.evaluation import EvalDataset, EvalQuery

# fmt: off

EVAL_DATASET = EvalDataset(
    name="pwbs-search-v1",
    queries=[
        # ── Meeting context ────────────────────────────────────
        EvalQuery(
            query="Q2 product roadmap planning meeting notes",
            relevant_ids=frozenset({"chunk-001", "chunk-002", "chunk-003", "chunk-004"}),
            relevance_grades={"chunk-001": 3, "chunk-002": 3, "chunk-003": 2, "chunk-004": 1},
        ),
        EvalQuery(
            query="action items from last sprint retrospective",
            relevant_ids=frozenset({"chunk-010", "chunk-011", "chunk-012"}),
            relevance_grades={"chunk-010": 3, "chunk-011": 2, "chunk-012": 1},
        ),
        EvalQuery(
            query="next week's calendar events with external stakeholders",
            relevant_ids=frozenset({"chunk-020", "chunk-021", "chunk-022", "chunk-023"}),
            relevance_grades={"chunk-020": 3, "chunk-021": 2, "chunk-022": 2, "chunk-023": 1},
        ),
        EvalQuery(
            query="one-on-one meeting with Julia about performance review",
            relevant_ids=frozenset({"chunk-030", "chunk-031"}),
            relevance_grades={"chunk-030": 3, "chunk-031": 2},
        ),
        EvalQuery(
            query="board meeting preparation materials and agenda",
            relevant_ids=frozenset({"chunk-040", "chunk-041", "chunk-042"}),
            relevance_grades={"chunk-040": 3, "chunk-041": 2, "chunk-042": 1},
        ),

        # ── Project context ────────────────────────────────────
        EvalQuery(
            query="migration from PostgreSQL to CockroachDB decision",
            relevant_ids=frozenset({"chunk-050", "chunk-051", "chunk-052"}),
            relevance_grades={"chunk-050": 3, "chunk-051": 2, "chunk-052": 1},
        ),
        EvalQuery(
            query="API versioning strategy for mobile clients",
            relevant_ids=frozenset({"chunk-060", "chunk-061"}),
            relevance_grades={"chunk-060": 3, "chunk-061": 2},
        ),
        EvalQuery(
            query="infrastructure cost reduction initiatives Q1",
            relevant_ids=frozenset({"chunk-070", "chunk-071", "chunk-072"}),
            relevance_grades={"chunk-070": 3, "chunk-071": 2, "chunk-072": 1},
        ),
        EvalQuery(
            query="authentication service redesign progress",
            relevant_ids=frozenset({"chunk-080", "chunk-081", "chunk-082", "chunk-083"}),
            relevance_grades={"chunk-080": 3, "chunk-081": 3, "chunk-082": 2, "chunk-083": 1},
        ),
        EvalQuery(
            query="data pipeline latency optimization results",
            relevant_ids=frozenset({"chunk-090", "chunk-091"}),
            relevance_grades={"chunk-090": 3, "chunk-091": 2},
        ),

        # ── Person context ─────────────────────────────────────
        EvalQuery(
            query="what is Thomas working on this quarter",
            relevant_ids=frozenset({"chunk-100", "chunk-101", "chunk-102"}),
            relevance_grades={"chunk-100": 3, "chunk-101": 2, "chunk-102": 1},
        ),
        EvalQuery(
            query="Sarah's feedback on the new onboarding flow",
            relevant_ids=frozenset({"chunk-110", "chunk-111"}),
            relevance_grades={"chunk-110": 3, "chunk-111": 2},
        ),
        EvalQuery(
            query="who raised concerns about GDPR compliance",
            relevant_ids=frozenset({"chunk-120", "chunk-121", "chunk-122"}),
            relevance_grades={"chunk-120": 3, "chunk-121": 2, "chunk-122": 1},
        ),

        # ── Decision history ───────────────────────────────────
        EvalQuery(
            query="why did we choose Weaviate over Pinecone",
            relevant_ids=frozenset({"chunk-130", "chunk-131"}),
            relevance_grades={"chunk-130": 3, "chunk-131": 2},
        ),
        EvalQuery(
            query="decision to use event sourcing for audit log",
            relevant_ids=frozenset({"chunk-140", "chunk-141", "chunk-142"}),
            relevance_grades={"chunk-140": 3, "chunk-141": 2, "chunk-142": 1},
        ),
        EvalQuery(
            query="vendor evaluation for monitoring stack",
            relevant_ids=frozenset({"chunk-150", "chunk-151"}),
            relevance_grades={"chunk-150": 3, "chunk-151": 2},
        ),
        EvalQuery(
            query="trade-offs discussed for monolith vs microservices",
            relevant_ids=frozenset({"chunk-160", "chunk-161", "chunk-162"}),
            relevance_grades={"chunk-160": 3, "chunk-161": 2, "chunk-162": 1},
        ),

        # ── Topic/Keyword exact-match ─────────────────────────
        EvalQuery(
            query="Kubernetes cluster autoscaling configuration",
            relevant_ids=frozenset({"chunk-170", "chunk-171"}),
            relevance_grades={"chunk-170": 3, "chunk-171": 2},
        ),
        EvalQuery(
            query="DSGVO Löschkonzept personenbezogene Daten",
            relevant_ids=frozenset({"chunk-180", "chunk-181", "chunk-182"}),
            relevance_grades={"chunk-180": 3, "chunk-181": 3, "chunk-182": 2},
        ),
        EvalQuery(
            query="Celery task timeout and retry configuration",
            relevant_ids=frozenset({"chunk-190", "chunk-191"}),
            relevance_grades={"chunk-190": 3, "chunk-191": 2},
        ),

        # ── Cross-source correlation ──────────────────────────
        EvalQuery(
            query="topics discussed in both Zoom calls and Notion pages about launch",
            relevant_ids=frozenset({"chunk-200", "chunk-201", "chunk-202", "chunk-203"}),
            relevance_grades={"chunk-200": 3, "chunk-201": 2, "chunk-202": 2, "chunk-203": 1},
        ),
        EvalQuery(
            query="recurring themes from weekly standups this month",
            relevant_ids=frozenset({"chunk-210", "chunk-211", "chunk-212"}),
            relevance_grades={"chunk-210": 3, "chunk-211": 2, "chunk-212": 1},
        ),
        EvalQuery(
            query="open questions that have not been resolved across meetings",
            relevant_ids=frozenset({"chunk-220", "chunk-221"}),
            relevance_grades={"chunk-220": 3, "chunk-221": 2},
        ),

        # ── Temporal queries ───────────────────────────────────
        EvalQuery(
            query="decisions made in the last two weeks",
            relevant_ids=frozenset({"chunk-230", "chunk-231", "chunk-232", "chunk-233"}),
            relevance_grades={"chunk-230": 3, "chunk-231": 2, "chunk-232": 2, "chunk-233": 1},
        ),
        EvalQuery(
            query="what changed in the backend architecture since January",
            relevant_ids=frozenset({"chunk-240", "chunk-241", "chunk-242"}),
            relevance_grades={"chunk-240": 3, "chunk-241": 2, "chunk-242": 1},
        ),

        # ── Negative / edge-case queries ──────────────────────
        EvalQuery(
            query="company holiday party photos",
            relevant_ids=frozenset(),
            relevance_grades={},
        ),
        EvalQuery(
            query="budget approval for new hire in marketing",
            relevant_ids=frozenset({"chunk-260"}),
            relevance_grades={"chunk-260": 2},
        ),

        # ── Obsidian-specific ──────────────────────────────────
        EvalQuery(
            query="personal notes on system design interview preparation",
            relevant_ids=frozenset({"chunk-270", "chunk-271", "chunk-272"}),
            relevance_grades={"chunk-270": 3, "chunk-271": 2, "chunk-272": 1},
        ),
        EvalQuery(
            query="reading list and book summaries from Obsidian vault",
            relevant_ids=frozenset({"chunk-280", "chunk-281"}),
            relevance_grades={"chunk-280": 3, "chunk-281": 2},
        ),

        # ── Briefing preparation ───────────────────────────────
        EvalQuery(
            query="context needed for tomorrow's executive review",
            relevant_ids=frozenset({"chunk-290", "chunk-291", "chunk-292", "chunk-293"}),
            relevance_grades={"chunk-290": 3, "chunk-291": 3, "chunk-292": 2, "chunk-293": 1},
        ),
        EvalQuery(
            query="unresolved blockers from project Alpha",
            relevant_ids=frozenset({"chunk-300", "chunk-301"}),
            relevance_grades={"chunk-300": 3, "chunk-301": 2},
        ),
    ],
)

# fmt: on
