# ADR-021: Embedding-basiertes Semantic Coherence Chunking

## Status

Accepted

## Datum

2026-03-17

## Kontext

Das bestehende Chunking in `pwbs/processing/chunking.py` verwendet drei Strategien (SEMANTIC, PARAGRAPH, FIXED), die alle auf Regex-basierter Satzvermeidung und Greedy-Token-Akkumulation basieren. Die "SEMANTIC"-Strategie ist dabei irreführend benannt — sie splittet an Satzgrenzen per `r"(?<=[.!?])\s+"`, nicht an semantischen Themenwechseln.

### Probleme des bestehenden Ansatzes

1. **Keine Themen-Awareness**: Chunks können mitten in einem Thema enden und ein neues Thema anfangen, was die Retrieval-Qualität verschlechtert.
2. **Fragile Satz-Erkennung**: Die naive Regex `[.!?]\s+` scheitert an Abkürzungen (Dr., Prof.), Dezimalzahlen (3.14), und Initialen (J. K. Rowling).
3. **Keine Qualitätsmetrik**: Chunks tragen keine Information darüber, wie kohärent ihr Inhalt ist.

### Anforderung

Ein Chunking-Verfahren, das **Chunk-Grenzen an tatsächlichen Themenwechseln** platziert, gemessen via Embedding-Ähnlichkeit benachbarter Sätze.

## Entscheidung

Implementierung eines neuen `SemanticCoherenceChunker` in `pwbs/processing/semantic_chunker.py`, der Chunk-Grenzen über eine Kohärenzkurve bestimmt.

### Algorithmus

```
Input:  Text T
Output: list[CoherenceChunk]

1. SEGMENT(T) → sentences[0..n-1]
   - Robuste Satzerkennung mit Abbreviation-Filter und Dezimalzahl-Erkennung

2. EMBED(sentences) → embeddings[0..n-1] ∈ ℝ^d
   - Batched async embedding (provider-agnostisch via Callback)

3. SIMILARITY(embeddings) → sims[0..n-2]
   - sims[i] = cos(embeddings[i], embeddings[i+1])

4. BREAKPOINTS(sims) → positions[]
   - Adaptive Threshold: τ = μ(sims) − σ · stdev(sims)
   - Breakpoint bei Position i+1 wenn:
     a) sims[i] ist lokales Minimum (< beide Nachbarn)
     b) sims[i] < τ
     c) Abstand zum letzten Breakpoint ≥ min_gap

5. GROUP(sentences, positions) → groups[]
   - Sätze zwischen Breakpoints zu Gruppen zusammenfassen
   - Durchschnittliche Kohärenz pro Gruppe berechnen

6. ENFORCE_LIMITS(groups) → bounded_groups[]
   - Oversized: Rekursiver Midpoint-Split bis max_tokens eingehalten
   - Undersized: Merge in Vorgänger wenn combined ≤ max_tokens

7. OVERLAP(bounded_groups) → chunks[]
   - Letzte overlap_sentences des Vorgänger-Chunks voranstellen
```

### Konfiguration

| Parameter | Default | Beschreibung |
|---|---|---|
| `max_tokens` | 512 | Hard Cap pro Chunk |
| `min_tokens` | 48 | Merge-Schwelle für Trailing-Chunks |
| `overlap_sentences` | 2 | Überlappende Sätze für Cross-Chunk-Kontext |
| `sensitivity` | 1.0 | Breakpoint-Empfindlichkeit (σ-Multiplikator) |
| `min_sentences_per_group` | 2 | Minimaler Abstand zwischen Breakpoints |
| `embed_batch_size` | 64 | API-Batch-Größe für Embeddings |

### Design-Entscheidungen

1. **Provider-agnostisch**: Die Embedding-Funktion wird als async Callback injiziert (`EmbedFn`), kein Import von `EmbeddingService`. Ermöglicht lokale Modelle (Sentence Transformers) und Cloud-APIs (OpenAI) ohne Code-Änderung.

2. **Adaptiver Threshold statt fester Cutoff**: Der Breakpoint-Threshold passt sich der Statistik des Dokuments an (`mean − σ × stdev`). Ein Dokument mit generell hoher Kohärenz (Fachtext) und eines mit niedrigerer (Meeting-Notizen) werden gleich gut segmentiert.

3. **Keine NumPy-Dependency**: Lineare Algebra (dot, norm, cosine) in reinem Python implementiert. Vermeidet eine C-Extension-Dependency für ~100 Vektoroperationen pro Dokument (bei n=100 Sätzen).

4. **Koexistenz mit bestehendem Chunker**: Der neue Chunker ersetzt `ChunkingService` nicht, sondern ist eine eigenständige Klasse. Pipeline-Code kann beide verwenden.

## Alternativen

### A: LLM-basiertes Chunking (verworfen)

Einen LLM-Call pro Dokument, der Chunk-Grenzen bestimmt.

- **Pro**: Semantisch noch genauer, versteht Kontext.
- **Contra**: ~100x teurer pro Dokument, Latenz, nicht deterministisch, schwer testbar.

### B: Sliding-Window mit Overlap (bestehend)

Feste Token-Fenster mit Überlappung.

- **Pro**: Einfach, deterministisch, kein Embedding nötig.
- **Contra**: Ignoriert Themenstruktur → Retrieval-Qualität leidet bei Topic-Wechseln im Chunk.

### C: TextTiling (Hearst 1997) mit TF-IDF (verworfen)

Term-Frequenz-basierte Kohärenzmessung.

- **Pro**: Kein Embedding nötig, bekannter Algorithmus.
- **Contra**: Weniger genau als Embedding-basierte Ähnlichkeit bei kurzen Segmenten, erfordert eigene TF-IDF-Berechnung.

## Komplexität

Sei n = Anzahl Sätze, d = Embedding-Dimension.

| Schritt | Komplexität |
|---|---|
| Segmentierung | O(n · L) (L = Textlänge) |
| Embedding | O(⌈n/batch⌉) API-Calls |
| Pairwise Similarity | O(n · d) |
| Breakpoint Detection | O(n) |
| Grouping + Token Count | O(n · t̄) (t̄ = avg Tokens/Satz) |
| **Gesamt** | **Dominiert durch Embedding** |

## Konsequenzen

### Positiv

- Chunks respektieren Themen-Grenzen → bessere Retrieval-Qualität bei Hybrid-Suche
- Jeder Chunk trägt eine `avg_coherence`-Metrik → Monitoring und Quality-Filtering möglich
- Robustere Satzerkennung als [\.\!\?]\s+

### Negativ

- Embedding-Kosten pro Dokument (n Sätze × Embedding-Preis)
- Nicht-deterministische Satzgrenzen bei Edge Cases
- Algorithmus produziert bei uniformen Texten (ein Thema) ähnliche Ergebnisse wie Greedy-Accumulation

### Risiken

- **Embedding-Qualität**: Schlechte Embeddings → schlechte Breakpoints. Mitigation: Sensitivity-Parameter erlaubt Tuning.
- **Single-Topic-Dokumente**: [Kein Breakpoint → ein Chunk → ggf. zu groß für max_tokens]. Mitigation: Midpoint-Split als Fallback.

## Referenzen

- Hearst, M. A. (1997). "TextTiling: Segmenting Text into Multi-paragraph Subtopic Passages"
- Solatorio & Ramponi (2024). "Embedding-Based Topic Segmentation for Long Documents"
