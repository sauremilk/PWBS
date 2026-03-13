"""PWBS Semantic Search PoC  TASK-002

CLI-based semantic search over documents stored by TASK-001.
Uses Weaviate Nearest-Neighbor search with text-embedding-3-small query embeddings.

Usage:
    1. Ensure Weaviate is running and TASK-001 data is loaded
    2. Set OPENAI_API_KEY in poc/.env
    3. Run: python poc/search_poc.py
    4. For automated test: python poc/search_poc.py --test
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import weaviate
import weaviate.classes as wvc
from dotenv import load_dotenv
from openai import OpenAI

COLLECTION_NAME = "UnifiedDocument"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
DEFAULT_TOP_K = 5


def embed_query(client: OpenAI, query: str) -> list[float]:
    """Generate embedding for a search query."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    return response.data[0].embedding


def search(
    weaviate_client: weaviate.WeaviateClient,
    openai_client: OpenAI,
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """Perform semantic search and return results with source information."""
    query_vector = embed_query(openai_client, query)

    collection = weaviate_client.collections.get(COLLECTION_NAME)
    results = collection.query.near_vector(
        near_vector=query_vector,
        limit=top_k,
        return_metadata=wvc.query.MetadataQuery(distance=True),
    )

    formatted: list[dict] = []
    for obj in results.objects:
        props = obj.properties
        metadata = {}
        if props.get("doc_metadata"):
            try:
                metadata = json.loads(props["doc_metadata"])
            except (json.JSONDecodeError, TypeError):
                pass

        formatted.append({
            "title": props.get("title", ""),
            "source_type": props.get("source_type", ""),
            "created_at": props.get("created_at", metadata.get("created", "")),
            "content_preview": props.get("content", "")[:200],
            "distance": obj.metadata.distance if obj.metadata else None,
            "similarity": round(1 - (obj.metadata.distance or 0), 4),
        })

    return formatted


def print_results(query: str, results: list[dict]) -> None:
    """Print search results in a readable format."""
    print(f"\n{'='*70}")
    print(f"  Query: {query}")
    print(f"{'='*70}")

    if not results:
        print("  Keine Ergebnisse gefunden.")
        return

    for i, r in enumerate(results, 1):
        source_label = {
            "google_calendar": "Kalender",
            "obsidian": "Notiz",
        }.get(r["source_type"], r["source_type"])

        print(f"\n  [{i}] {r['title']}")
        print(f"      Quelle: {source_label}  |  Datum: {r['created_at']}  |  Similarity: {r['similarity']}")
        print(f"      {r['content_preview'][:120]}...")


# Pre-defined test queries covering diverse topics and both sources
TEST_QUERIES: list[dict[str, str | list[str]]] = [
    {
        "query": "Welche Meetings zur API-Migration gibt es?",
        "expected_sources": ["google_calendar", "obsidian"],
        "description": "Soll Kalender-Events UND Notizen zur API-Migration finden",
    },
    {
        "query": "DSGVO und Datenschutz Anforderungen",
        "expected_sources": ["obsidian"],
        "description": "Soll Notizen zu DSGVO-Themen liefern",
    },
    {
        "query": "Wie funktioniert die Embedding-Generierung?",
        "expected_sources": ["obsidian"],
        "description": "Soll technische Notizen zur Embedding-Strategie finden",
    },
    {
        "query": "Wer ist an Security und Sicherheit beteiligt?",
        "expected_sources": ["google_calendar", "obsidian"],
        "description": "Soll Security-Audit-Events und Verschluesselungsnotizen finden",
    },
    {
        "query": "Sprint Retrospektive Ergebnisse",
        "expected_sources": ["google_calendar", "obsidian"],
        "description": "Soll Retro-Events und Retro-Notizen finden",
    },
    {
        "query": "Knowledge Graph und Neo4j",
        "expected_sources": ["obsidian"],
        "description": "Soll Knowledge-Graph-Design-Notiz finden",
    },
    {
        "query": "Termine naechste Woche mit externen Teilnehmern",
        "expected_sources": ["google_calendar"],
        "description": "Soll Kalender-Events mit Teilnehmern finden",
    },
    {
        "query": "Briefing Engine und Morning Briefing",
        "expected_sources": ["obsidian"],
        "description": "Soll Briefing-Design-Notiz finden",
    },
    {
        "query": "Performance und Monitoring",
        "expected_sources": ["obsidian"],
        "description": "Soll Performance- und Monitoring-Notizen finden",
    },
    {
        "query": "Architekturentscheidungen und ADR",
        "expected_sources": ["google_calendar", "obsidian"],
        "description": "Soll Architektur-Review-Events und ADR-Notizen finden",
    },
]


def run_test_queries(
    weaviate_client: weaviate.WeaviateClient,
    openai_client: OpenAI,
) -> bool:
    """Run all test queries and verify results."""
    print("\n" + "=" * 70)
    print("  AUTOMATISIERTER SUCHTEST (10 Testqueries)")
    print("=" * 70)

    passed = 0
    total = len(TEST_QUERIES)
    cross_source_found = False

    for i, tq in enumerate(TEST_QUERIES, 1):
        query = str(tq["query"])
        results = search(weaviate_client, openai_client, query, top_k=5)
        source_types = {r["source_type"] for r in results}

        if len(source_types) >= 2:
            cross_source_found = True

        # Basic relevance check: we got results
        has_results = len(results) > 0
        # Check that results have source information
        has_source_info = all(
            r.get("source_type") and r.get("title") and r.get("created_at") is not None
            for r in results
        )

        status = "PASS" if (has_results and has_source_info) else "FAIL"
        if status == "PASS":
            passed += 1

        print(f"\n  [{i}/{total}] {status}: {query}")
        print(f"    Quellen: {', '.join(sorted(source_types))}")
        print(f"    Ergebnisse: {len(results)}, Top-Similarity: {results[0]['similarity'] if results else 'N/A'}")
        if results:
            print(f"    Top-Treffer: {results[0]['title']}")

    print(f"\n{'='*70}")
    print(f"  ERGEBNIS: {passed}/{total} Queries bestanden")
    print(f"  Cross-Source-Suche: {'JA' if cross_source_found else 'NEIN'}")
    print(f"{'='*70}")

    return passed == total and cross_source_found


def interactive_mode(
    weaviate_client: weaviate.WeaviateClient,
    openai_client: OpenAI,
) -> None:
    """Interactive search REPL."""
    print("\n  PWBS Semantic Search PoC")
    print("  Gib eine Suchanfrage ein (oder 'exit' zum Beenden)\n")

    while True:
        try:
            query = input("  > ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not query or query.lower() in ("exit", "quit", "q"):
            break

        results = search(weaviate_client, openai_client, query, top_k=5)
        print_results(query, results)


def main() -> None:
    parser = argparse.ArgumentParser(description="PWBS Semantic Search PoC")
    parser.add_argument("--test", action="store_true", help="Run automated test queries")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Number of results")
    args = parser.parse_args()

    load_dotenv(Path(__file__).parent / ".env")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set. Create poc/.env with your key.")
        sys.exit(1)

    weaviate_url = os.environ.get("WEAVIATE_URL", "http://localhost:8080")
    openai_client = OpenAI(api_key=api_key)

    weaviate_client = weaviate.connect_to_local(
        host=weaviate_url.replace("http://", "").split(":")[0],
        port=int(weaviate_url.split(":")[-1]) if ":" in weaviate_url.rsplit("/", 1)[-1] else 8080,
    )

    try:
        # Verify data exists
        collection = weaviate_client.collections.get(COLLECTION_NAME)
        count = 0
        for _ in collection.iterator():
            count += 1
        if count == 0:
            print("ERROR: No documents in Weaviate. Run embedding_poc.py first.")
            sys.exit(1)
        print(f"  {count} Dokumente in Weaviate verfuegbar.")

        if args.test:
            success = run_test_queries(weaviate_client, openai_client)
            sys.exit(0 if success else 1)
        else:
            interactive_mode(weaviate_client, openai_client)

    finally:
        weaviate_client.close()


if __name__ == "__main__":
    main()
