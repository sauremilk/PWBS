"""PWBS Embedding PoC  TASK-001

Reads calendar events (Google Calendar JSON) and markdown notes (Obsidian/Notion),
generates embeddings via OpenAI text-embedding-3-small (1536 dimensions),
and stores them in a local Weaviate instance.

Usage:
    1. Start Weaviate: docker compose -f poc/docker-compose.yml up -d
    2. Generate sample data: python poc/generate_sample_data.py
    3. Set OPENAI_API_KEY in poc/.env
    4. Run: python poc/embedding_poc.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import weaviate
import weaviate.classes as wvc
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COLLECTION_NAME = "UnifiedDocument"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
BATCH_SIZE = 64  # OpenAI batch size for embedding calls

SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"
CALENDAR_DIR = SAMPLE_DATA_DIR / "calendar"
NOTES_DIR = SAMPLE_DATA_DIR / "notes"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class UnifiedDocument:
    """Normalized document from any source."""
    source_id: str
    source_type: str  # "google_calendar" or "obsidian"
    title: str
    content: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Source readers
# ---------------------------------------------------------------------------

def read_calendar_events(directory: Path) -> list[UnifiedDocument]:
    """Read Google Calendar JSON exports and normalize to UnifiedDocument."""
    documents: list[UnifiedDocument] = []
    if not directory.exists():
        print(f"WARNING: Calendar directory not found: {directory}")
        return documents

    for filepath in sorted(directory.glob("*.json")):
        with open(filepath, "r", encoding="utf-8") as f:
            event = json.load(f)

        content_parts = [event.get("summary", "")]
        if desc := event.get("description"):
            content_parts.append(desc)
        if loc := event.get("location"):
            content_parts.append(f"Ort: {loc}")
        if attendees := event.get("attendees"):
            emails = [a.get("email", "") for a in attendees]
            content_parts.append(f"Teilnehmer: {', '.join(emails)}")

        start_dt = event.get("start", {}).get("dateTime", "")

        doc = UnifiedDocument(
            source_id=event.get("id", filepath.stem),
            source_type="google_calendar",
            title=event.get("summary", filepath.stem),
            content="\n".join(content_parts),
            created_at=start_dt or event.get("created", ""),
            metadata={
                "location": event.get("location", ""),
                "start": start_dt,
                "end": event.get("end", {}).get("dateTime", ""),
                "attendee_count": len(event.get("attendees", [])),
            },
        )
        documents.append(doc)

    return documents


def read_markdown_notes(directory: Path) -> list[UnifiedDocument]:
    """Read Obsidian/Notion markdown notes and normalize to UnifiedDocument."""
    documents: list[UnifiedDocument] = []
    if not directory.exists():
        print(f"WARNING: Notes directory not found: {directory}")
        return documents

    for filepath in sorted(directory.glob("*.md")):
        text = filepath.read_text(encoding="utf-8")

        # Parse YAML frontmatter if present
        metadata: dict[str, Any] = {}
        content = text
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                content = parts[2].strip()
                for line in frontmatter.split("\n"):
                    if ":" in line:
                        key, _, value = line.partition(":")
                        metadata[key.strip()] = value.strip().strip('"')

        title = metadata.get("title", filepath.stem.replace("-", " ").title())
        created = metadata.get("created", "")

        doc = UnifiedDocument(
            source_id=f"note_{filepath.stem}",
            source_type="obsidian",
            title=title,
            content=content,
            created_at=created,
            metadata=metadata,
        )
        documents.append(doc)

    return documents


# ---------------------------------------------------------------------------
# Embedding generation
# ---------------------------------------------------------------------------

def generate_embeddings(
    client: OpenAI,
    texts: list[str],
    batch_size: int = BATCH_SIZE,
) -> list[list[float]]:
    """Generate embeddings in batches using OpenAI text-embedding-3-small."""
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        print(f"  Embedding batch {i // batch_size + 1} ({len(batch)} texts)...")

        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
            dimensions=EMBEDDING_DIMENSIONS,
        )

        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


# ---------------------------------------------------------------------------
# Weaviate operations
# ---------------------------------------------------------------------------

def setup_weaviate_collection(client: weaviate.WeaviateClient) -> None:
    """Create or recreate the UnifiedDocument collection in Weaviate."""
    if client.collections.exists(COLLECTION_NAME):
        client.collections.delete(COLLECTION_NAME)
        print(f"  Deleted existing collection: {COLLECTION_NAME}")

    client.collections.create(
        name=COLLECTION_NAME,
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        properties=[
            wvc.config.Property(name="source_id", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="source_type", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="created_at", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="doc_metadata", data_type=wvc.config.DataType.TEXT),
        ],
    )
    print(f"  Created collection: {COLLECTION_NAME}")


def store_documents(
    client: weaviate.WeaviateClient,
    documents: list[UnifiedDocument],
    embeddings: list[list[float]],
) -> int:
    """Store documents with embeddings in Weaviate using batch insert."""
    collection = client.collections.get(COLLECTION_NAME)
    stored = 0

    with collection.batch.dynamic() as batch:
        for doc, embedding in zip(documents, embeddings):
            batch.add_object(
                properties={
                    "source_id": doc.source_id,
                    "source_type": doc.source_type,
                    "title": doc.title,
                    "content": doc.content,
                    "created_at": doc.created_at,
                    "doc_metadata": json.dumps(doc.metadata, ensure_ascii=False),
                },
                vector=embedding,
            )
            stored += 1

    return stored


def verify_storage(client: weaviate.WeaviateClient) -> dict[str, int]:
    """Verify stored documents and return counts per source type."""
    collection = client.collections.get(COLLECTION_NAME)
    counts: dict[str, int] = {}

    for item in collection.iterator(include_vector=True):
        source_type = item.properties.get("source_type", "unknown")
        counts[source_type] = counts.get(source_type, 0) + 1

        # Verify vector dimensions on first item per type
        if counts[source_type] == 1 and item.vector:
            vec = item.vector.get("default", [])
            if len(vec) != EMBEDDING_DIMENSIONS:
                print(f"  WARNING: Expected {EMBEDDING_DIMENSIONS} dims, got {len(vec)}")

    return counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    load_dotenv(Path(__file__).parent / ".env")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set. Create poc/.env with your key.")
        sys.exit(1)

    weaviate_url = os.environ.get("WEAVIATE_URL", "http://localhost:8080")

    # --- Step 1: Read documents ---
    print("\n=== Step 1: Reading documents ===")
    calendar_docs = read_calendar_events(CALENDAR_DIR)
    notes_docs = read_markdown_notes(NOTES_DIR)
    all_docs = calendar_docs + notes_docs

    print(f"  Calendar events: {len(calendar_docs)}")
    print(f"  Markdown notes:  {len(notes_docs)}")
    print(f"  Total:           {len(all_docs)}")

    if len(all_docs) < 50:
        print(f"ERROR: Need >=50 documents, got {len(all_docs)}. Run generate_sample_data.py first.")
        sys.exit(1)

    if len({d.source_type for d in all_docs}) < 2:
        print("ERROR: Need documents from >=2 different sources.")
        sys.exit(1)

    # --- Step 2: Generate embeddings ---
    print("\n=== Step 2: Generating embeddings ===")
    openai_client = OpenAI(api_key=api_key)
    texts = [f"{doc.title}\n{doc.content}" for doc in all_docs]

    start_time = time.monotonic()
    embeddings = generate_embeddings(openai_client, texts)
    elapsed = time.monotonic() - start_time

    print(f"  Generated {len(embeddings)} embeddings in {elapsed:.1f}s")
    print(f"  Dimensions: {len(embeddings[0])}")

    assert len(embeddings) == len(all_docs), "Embedding count mismatch"
    assert all(len(e) == EMBEDDING_DIMENSIONS for e in embeddings), "Dimension mismatch"

    # --- Step 3: Store in Weaviate ---
    print("\n=== Step 3: Storing in Weaviate ===")
    weaviate_client = weaviate.connect_to_local(
        host=weaviate_url.replace("http://", "").split(":")[0],
        port=int(weaviate_url.split(":")[-1]) if ":" in weaviate_url.rsplit("/", 1)[-1] else 8080,
    )

    try:
        setup_weaviate_collection(weaviate_client)
        stored = store_documents(weaviate_client, all_docs, embeddings)
        print(f"  Stored {stored} documents in Weaviate")

        # --- Step 4: Verify ---
        print("\n=== Step 4: Verification ===")
        counts = verify_storage(weaviate_client)
        total_stored = sum(counts.values())

        print(f"  Documents in Weaviate: {total_stored}")
        for source_type, count in sorted(counts.items()):
            print(f"    {source_type}: {count}")

        # Acceptance criteria checks
        assert total_stored >= 50, f"Need >=50 stored docs, got {total_stored}"
        assert len(counts) >= 2, f"Need >=2 source types, got {len(counts)}"

        print("\n=== SUCCESS ===")
        print(f"  {total_stored} documents from {len(counts)} sources stored with {EMBEDDING_DIMENSIONS}-dim embeddings")
        print("  All acceptance criteria met.")

    finally:
        weaviate_client.close()


if __name__ == "__main__":
    main()
