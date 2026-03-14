use crate::offline::vault::{CachedBriefing, CachedEntity, OfflineVault};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use thiserror::Error;
use tokio::sync::RwLock;

#[derive(Error, Debug)]
pub enum SyncError {
    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),
    #[error("Vault error: {0}")]
    Vault(#[from] crate::offline::vault::VaultError),
    #[error("API error: {0}")]
    Api(String),
    #[error("Lock error: {0}")]
    Lock(String),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "snake_case")]
pub enum SyncStatus {
    Online {
        last_sync: Option<String>,
    },
    Offline {
        last_sync: Option<String>,
    },
    Syncing {
        progress: f32,
    },
}

impl Default for SyncStatus {
    fn default() -> Self {
        Self::Offline { last_sync: None }
    }
}

#[derive(Debug, Deserialize)]
struct ApiBriefingResponse {
    briefings: Vec<ApiBriefing>,
}

#[derive(Debug, Deserialize)]
struct ApiBriefing {
    id: String,
    owner_id: String,
    briefing_type: String,
    title: String,
    content: String,
    created_at: String,
    #[serde(default)]
    sources: serde_json::Value,
}

#[derive(Debug, Deserialize)]
struct ApiEntityResponse {
    entities: Vec<ApiEntity>,
}

#[derive(Debug, Deserialize)]
struct ApiEntity {
    id: String,
    owner_id: String,
    entity_type: String,
    name: String,
    #[serde(default)]
    mention_count: i64,
    #[serde(default)]
    metadata: serde_json::Value,
}

pub struct SyncEngine {
    client: Client,
    base_url: String,
    status: Arc<RwLock<SyncStatus>>,
}

impl SyncEngine {
    pub fn new(base_url: String) -> Self {
        Self {
            client: Client::new(),
            base_url,
            status: Arc::new(RwLock::new(SyncStatus::default())),
        }
    }

    pub async fn get_status(&self) -> SyncStatus {
        self.status.read().await.clone()
    }

    /// Check if the backend API is reachable.
    pub async fn check_connectivity(&self) -> bool {
        self.client
            .get(format!("{}/api/v1/health", self.base_url))
            .timeout(std::time::Duration::from_secs(5))
            .send()
            .await
            .map(|r| r.status().is_success())
            .unwrap_or(false)
    }

    /// Run a full sync cycle: briefings + entities + push vault changes.
    /// Uses short-lived locks on the vault to avoid holding it across awaits.
    pub async fn sync_all(
        &self,
        vault: &Arc<Mutex<OfflineVault>>,
        token: &str,
        _owner_id: &str,
    ) -> Result<(), SyncError> {
        {
            let mut s = self.status.write().await;
            *s = SyncStatus::Syncing { progress: 0.0 };
        }

        let briefing_count = self.sync_briefings(vault, token).await?;
        {
            let mut s = self.status.write().await;
            *s = SyncStatus::Syncing { progress: 0.33 };
        }

        let entity_count = self.sync_entities(vault, token).await?;
        {
            let mut s = self.status.write().await;
            *s = SyncStatus::Syncing { progress: 0.66 };
        }

        self.push_vault_changes(vault, token).await?;

        // Purge old briefings
        {
            let v = vault.lock().map_err(|e| SyncError::Lock(e.to_string()))?;
            let _ = v.purge_old_briefings(7);
            v.update_sync_state("full", (briefing_count + entity_count) as i64)?;
        }

        let now = chrono::Utc::now().to_rfc3339();
        {
            let mut s = self.status.write().await;
            *s = SyncStatus::Online {
                last_sync: Some(now),
            };
        }

        Ok(())
    }

    async fn sync_briefings(
        &self,
        vault: &Arc<Mutex<OfflineVault>>,
        token: &str,
    ) -> Result<usize, SyncError> {
        let resp = self
            .client
            .get(format!("{}/api/v1/briefings", self.base_url))
            .bearer_auth(token)
            .query(&[("days", "7")])
            .send()
            .await?;

        if !resp.status().is_success() {
            return Err(SyncError::Api(format!("Briefings API returned {}", resp.status())));
        }

        let data: ApiBriefingResponse = resp.json().await?;
        let count = data.briefings.len();

        // Short-lived lock for DB writes
        {
            let v = vault.lock().map_err(|e| SyncError::Lock(e.to_string()))?;
            for b in data.briefings {
                v.upsert_briefing(&CachedBriefing {
                    id: b.id,
                    owner_id: b.owner_id,
                    briefing_type: b.briefing_type,
                    title: b.title,
                    content: b.content,
                    created_at: b.created_at,
                    sources_json: b.sources.to_string(),
                })?;
            }
        }

        Ok(count)
    }

    async fn sync_entities(
        &self,
        vault: &Arc<Mutex<OfflineVault>>,
        token: &str,
    ) -> Result<usize, SyncError> {
        let resp = self
            .client
            .get(format!("{}/api/v1/entities", self.base_url))
            .bearer_auth(token)
            .query(&[("top_k", "50"), ("sort", "mention_count")])
            .send()
            .await?;

        if !resp.status().is_success() {
            return Err(SyncError::Api(format!("Entities API returned {}", resp.status())));
        }

        let data: ApiEntityResponse = resp.json().await?;
        let count = data.entities.len();

        {
            let v = vault.lock().map_err(|e| SyncError::Lock(e.to_string()))?;
            for e in data.entities {
                v.upsert_entity(&CachedEntity {
                    id: e.id,
                    owner_id: e.owner_id,
                    entity_type: e.entity_type,
                    name: e.name,
                    mention_count: e.mention_count,
                    metadata_json: e.metadata.to_string(),
                })?;
            }
        }

        Ok(count)
    }

    async fn push_vault_changes(
        &self,
        vault: &Arc<Mutex<OfflineVault>>,
        token: &str,
    ) -> Result<(), SyncError> {
        // Read pending changes with short lock
        let changes = {
            let v = vault.lock().map_err(|e| SyncError::Lock(e.to_string()))?;
            v.get_pending_changes()?
        };

        for (queue_id, file_path, event_type) in &changes {
            let payload = serde_json::json!({
                "file_path": file_path,
                "event_type": event_type,
            });

            let resp = self
                .client
                .post(format!("{}/api/v1/connectors/obsidian/sync", self.base_url))
                .bearer_auth(token)
                .json(&payload)
                .send()
                .await?;

            if resp.status().is_success() {
                let v = vault.lock().map_err(|e| SyncError::Lock(e.to_string()))?;
                v.mark_synced(*queue_id)?;
            } else {
                log::warn!("Failed to sync vault change {}: {}", queue_id, resp.status());
            }
        }

        Ok(())
    }

    /// Mark status as offline.
    pub async fn set_offline(&self) {
        let mut s = self.status.write().await;
        let last = match &*s {
            SyncStatus::Online { last_sync } => last_sync.clone(),
            SyncStatus::Offline { last_sync } => last_sync.clone(),
            SyncStatus::Syncing { .. } => None,
        };
        *s = SyncStatus::Offline { last_sync: last };
    }
}
