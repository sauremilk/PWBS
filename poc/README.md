# PWBS Embedding PoC (TASK-001)

Proof of Concept für Embedding-Generierung über heterogene Datenquellen.

## Was dieser PoC zeigt

- Einlesen von **Google Calendar Events** (JSON) und **Obsidian/Notion Markdown-Notizen**
- Normalisierung in ein einheitliches Dokumentenformat (UnifiedDocument)
- Embedding-Generierung via **OpenAI text-embedding-3-small** (1536 Dimensionen)
- Persistierung in einer lokalen **Weaviate**-Instanz
- Verifikation: 50 Dokumente aus 2 Quellen erfolgreich gespeichert

## Voraussetzungen

- Python 3.12+
- Docker (für Weaviate)
- OpenAI API-Key

## Schritt-für-Schritt-Anleitung

### 1. Weaviate starten

```bash
cd poc
docker compose up -d
```

Warten bis Weaviate bereit ist (~10 Sekunden):

```bash
curl http://localhost:8080/v1/.well-known/ready
```

### 2. Python-Umgebung einrichten

```bash
cd poc
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. API-Key konfigurieren

```bash
cp .env.example .env
# .env editieren und OPENAI_API_KEY eintragen
```

### 4. Beispieldaten generieren

```bash
python generate_sample_data.py
```

Output: 30 Kalendereinträge + 21 Markdown-Notizen = 51 Dokumente

### 5. Embedding-PoC ausführen

```bash
python embedding_poc.py
```

### 6. Semantische Suche (TASK-002)

Interaktiver Modus:

```bash
python search_poc.py
```

Automatisierter Test (10 vordefinierte Queries):

```bash
python search_poc.py --test
```

### Erwartete Ausgabe

```
=== Step 1: Reading documents ===
  Calendar events: 30
  Markdown notes:  21
  Total:           51

=== Step 2: Generating embeddings ===
  Embedding batch 1 (51 texts)...
  Generated 51 embeddings in X.Xs
  Dimensions: 1536

=== Step 3: Storing in Weaviate ===
  Created collection: UnifiedDocument
  Stored 51 documents in Weaviate

=== Step 4: Verification ===
  Documents in Weaviate: 51
    google_calendar: 30
    obsidian: 21

=== SUCCESS ===
  51 documents from 2 sources stored with 1536-dim embeddings
  All acceptance criteria met.
```

## Projektstruktur

```
poc/
 docker-compose.yml        # Weaviate Container
 requirements.txt          # Python-Abhängigkeiten
 .env.example              # Vorlage für Umgebungsvariablen
 generate_sample_data.py   # Erzeugt 50 Beispieldokumente
 embedding_poc.py          # Hauptskript: Lesen  Embedden  Speichern├── search_poc.py             # Semantische Suche (CLI + automatisierter Test) README.md                 # Diese Datei
 sample_data/
     calendar/             # Google Calendar Events (JSON)
     notes/                # Obsidian Markdown-Notizen
```

## Technische Details

| Aspekt          | Wert                                |
|-----------------|-------------------------------------|
| Embedding-Modell | `text-embedding-3-small`           |
| Dimensionen     | 1536                                |
| Batch-Größe     | 64                                  |
| Chunking        | Paragraph-Splitting (PoC-einfach)   |
| Weaviate        | v1.28.2, Vectorizer: none (extern) |
| Quellen         | Google Calendar JSON, Obsidian MD   |

## Nächste Schritte


- MVP: Semantisches Chunking (128512 Tokens, 32 Token Overlap)
- MVP: Sentence Transformers als lokale Alternative
