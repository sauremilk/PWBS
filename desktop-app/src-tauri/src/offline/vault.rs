use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use std::path::Path;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum VaultError {
    #[error("SQLite error: {0}")]
    Sqlite(#[from] rusqlite::Error),
    #[error("Serialization error: {0}")]
    Serde(#[from] serde_json::Error),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CachedBriefing {
    pub id: String,
    pub owner_id: String,
    pub briefing_type: String,
    pub title: String,
    pub content: String,
    pub created_at: String,
    pub sources_json: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CachedEntity {
    pub id: String,
    pub owner_id: String,
    pub entity_type: String,
    pub name: String,
    pub mention_count: i64,
    pub metadata_json: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CachedEmbedding {
    pub chunk_id: String,
    pub owner_id: String,
    pub content: String,
    pub source_title: String,
    pub embedding: Vec<f32>,
}

pub struct OfflineVault {
    conn: Connection,
}

impl OfflineVault {
    /// Open or create the SQLite vault at the given path.
    pub fn open(db_path: &Path) -> Result<Self, VaultError> {
        let conn = Connection::open(db_path)?;
        let vault = Self { conn };
        vault.initialize_schema()?;
        Ok(vault)
    }

    fn initialize_schema(&self) -> Result<(), VaultError> {
        self.conn.execute_batch(
            "
            CREATE TABLE IF NOT EXISTS briefings (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                briefing_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]',
                cached_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL,
                mention_count INTEGER NOT NULL DEFAULT 0,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                cached_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                content TEXT NOT NULL,
                source_title TEXT NOT NULL DEFAULT '',
                embedding BLOB NOT NULL,
                cached_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sync_state (
                resource_type TEXT PRIMARY KEY,
                last_sync_at TEXT NOT NULL,
                last_sync_status TEXT NOT NULL DEFAULT 'success',
                items_synced INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS vault_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                event_type TEXT NOT NULL,
                detected_at TEXT NOT NULL DEFAULT (datetime('now')),
                synced INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_briefings_owner ON briefings(owner_id);
            CREATE INDEX IF NOT EXISTS idx_briefings_created ON briefings(created_at);
            CREATE INDEX IF NOT EXISTS idx_entities_owner ON entities(owner_id);
            CREATE INDEX IF NOT EXISTS idx_entities_mentions ON entities(mention_count DESC);
            CREATE INDEX IF NOT EXISTS idx_embeddings_owner ON embeddings(owner_id);
            CREATE INDEX IF NOT EXISTS idx_vault_queue_synced ON vault_queue(synced);
            ",
        )?;
        Ok(())
    }

    // --- Briefings ---

    pub fn upsert_briefing(&self, b: &CachedBriefing) -> Result<(), VaultError> {
        self.conn.execute(
            "INSERT INTO briefings (id, owner_id, briefing_type, title, content, created_at, sources_json)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)
             ON CONFLICT(id) DO UPDATE SET
                 title = excluded.title,
                 content = excluded.content,
                 sources_json = excluded.sources_json,
                 cached_at = datetime('now')",
            params![b.id, b.owner_id, b.briefing_type, b.title, b.content, b.created_at, b.sources_json],
        )?;
        Ok(())
    }

    pub fn get_briefings(&self, owner_id: &str, days: i64) -> Result<Vec<CachedBriefing>, VaultError> {
        let mut stmt = self.conn.prepare(
            "SELECT id, owner_id, briefing_type, title, content, created_at, sources_json
             FROM briefings
             WHERE owner_id = ?1 AND created_at >= datetime('now', ?2)
             ORDER BY created_at DESC",
        )?;
        let cutoff = format!("-{} days", days);
        let rows = stmt.query_map(params![owner_id, cutoff], |row| {
            Ok(CachedBriefing {
                id: row.get(0)?,
                owner_id: row.get(1)?,
                briefing_type: row.get(2)?,
                title: row.get(3)?,
                content: row.get(4)?,
                created_at: row.get(5)?,
                sources_json: row.get(6)?,
            })
        })?;
        rows.collect::<Result<Vec<_>, _>>().map_err(VaultError::from)
    }

    pub fn purge_old_briefings(&self, days: i64) -> Result<usize, VaultError> {
        let cutoff = format!("-{} days", days);
        let count = self.conn.execute(
            "DELETE FROM briefings WHERE created_at < datetime('now', ?1)",
            params![cutoff],
        )?;
        Ok(count)
    }

    // --- Entities ---

    pub fn upsert_entity(&self, e: &CachedEntity) -> Result<(), VaultError> {
        self.conn.execute(
            "INSERT INTO entities (id, owner_id, entity_type, name, mention_count, metadata_json)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)
             ON CONFLICT(id) DO UPDATE SET
                 name = excluded.name,
                 mention_count = excluded.mention_count,
                 metadata_json = excluded.metadata_json,
                 cached_at = datetime('now')",
            params![e.id, e.owner_id, e.entity_type, e.name, e.mention_count, e.metadata_json],
        )?;
        Ok(())
    }

    pub fn get_top_entities(&self, owner_id: &str, limit: i64) -> Result<Vec<CachedEntity>, VaultError> {
        let mut stmt = self.conn.prepare(
            "SELECT id, owner_id, entity_type, name, mention_count, metadata_json
             FROM entities
             WHERE owner_id = ?1
             ORDER BY mention_count DESC
             LIMIT ?2",
        )?;
        let rows = stmt.query_map(params![owner_id, limit], |row| {
            Ok(CachedEntity {
                id: row.get(0)?,
                owner_id: row.get(1)?,
                entity_type: row.get(2)?,
                name: row.get(3)?,
                mention_count: row.get(4)?,
                metadata_json: row.get(5)?,
            })
        })?;
        rows.collect::<Result<Vec<_>, _>>().map_err(VaultError::from)
    }

    // --- Embeddings ---

    pub fn upsert_embedding(&self, e: &CachedEmbedding) -> Result<(), VaultError> {
        let blob = embedding_to_bytes(&e.embedding);
        self.conn.execute(
            "INSERT INTO embeddings (chunk_id, owner_id, content, source_title, embedding)
             VALUES (?1, ?2, ?3, ?4, ?5)
             ON CONFLICT(chunk_id) DO UPDATE SET
                 content = excluded.content,
                 source_title = excluded.source_title,
                 embedding = excluded.embedding,
                 cached_at = datetime('now')",
            params![e.chunk_id, e.owner_id, e.content, e.source_title, blob],
        )?;
        Ok(())
    }

    pub fn get_all_embeddings(&self, owner_id: &str) -> Result<Vec<CachedEmbedding>, VaultError> {
        let mut stmt = self.conn.prepare(
            "SELECT chunk_id, owner_id, content, source_title, embedding
             FROM embeddings WHERE owner_id = ?1",
        )?;
        let rows = stmt.query_map(params![owner_id], |row| {
            let blob: Vec<u8> = row.get(4)?;
            Ok(CachedEmbedding {
                chunk_id: row.get(0)?,
                owner_id: row.get(1)?,
                content: row.get(2)?,
                source_title: row.get(3)?,
                embedding: bytes_to_embedding(&blob),
            })
        })?;
        rows.collect::<Result<Vec<_>, _>>().map_err(VaultError::from)
    }

    // --- Sync State ---

    pub fn update_sync_state(&self, resource_type: &str, items: i64) -> Result<(), VaultError> {
        self.conn.execute(
            "INSERT INTO sync_state (resource_type, last_sync_at, last_sync_status, items_synced)
             VALUES (?1, datetime('now'), 'success', ?2)
             ON CONFLICT(resource_type) DO UPDATE SET
                 last_sync_at = datetime('now'),
                 last_sync_status = 'success',
                 items_synced = excluded.items_synced",
            params![resource_type, items],
        )?;
        Ok(())
    }

    pub fn get_last_sync(&self, resource_type: &str) -> Result<Option<String>, VaultError> {
        let mut stmt = self.conn.prepare(
            "SELECT last_sync_at FROM sync_state WHERE resource_type = ?1",
        )?;
        let result = stmt
            .query_row(params![resource_type], |row| row.get::<_, String>(0))
            .ok();
        Ok(result)
    }

    // --- Vault Queue (Obsidian file changes) ---

    pub fn enqueue_file_change(&self, path: &str, event: &str) -> Result<(), VaultError> {
        self.conn.execute(
            "INSERT INTO vault_queue (file_path, event_type) VALUES (?1, ?2)",
            params![path, event],
        )?;
        Ok(())
    }

    pub fn get_pending_changes(&self) -> Result<Vec<(i64, String, String)>, VaultError> {
        let mut stmt = self.conn.prepare(
            "SELECT id, file_path, event_type FROM vault_queue WHERE synced = 0 ORDER BY detected_at",
        )?;
        let rows = stmt.query_map([], |row| {
            Ok((row.get(0)?, row.get(1)?, row.get(2)?))
        })?;
        rows.collect::<Result<Vec<_>, _>>().map_err(VaultError::from)
    }

    pub fn mark_synced(&self, queue_id: i64) -> Result<(), VaultError> {
        self.conn.execute(
            "UPDATE vault_queue SET synced = 1 WHERE id = ?1",
            params![queue_id],
        )?;
        Ok(())
    }
}

fn embedding_to_bytes(embedding: &[f32]) -> Vec<u8> {
    embedding
        .iter()
        .flat_map(|f| f.to_le_bytes())
        .collect()
}

fn bytes_to_embedding(bytes: &[u8]) -> Vec<f32> {
    bytes
        .chunks_exact(4)
        .map(|chunk| f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]))
        .collect()
}
