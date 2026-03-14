use crate::offline::vault::OfflineVault;
use notify::{Config, Event, EventKind, RecommendedWatcher, RecursiveMode, Watcher};
use std::path::{Path, PathBuf};
use std::sync::mpsc;
use std::sync::Arc;
use std::thread;

/// Watches an Obsidian vault directory for file changes.
/// Changes are queued in the SQLite vault for later sync.
pub struct VaultWatcher {
    _watcher: RecommendedWatcher,
    vault_path: PathBuf,
}

impl VaultWatcher {
    /// Start watching the given directory. File change events are stored
    /// in the offline vault queue for sync when connectivity is available.
    pub fn start(
        vault_path: PathBuf,
        offline_vault: Arc<std::sync::Mutex<OfflineVault>>,
    ) -> Result<Self, notify::Error> {
        let (tx, rx) = mpsc::channel::<notify::Result<Event>>();

        let mut watcher = RecommendedWatcher::new(tx, Config::default())?;
        watcher.watch(&vault_path, RecursiveMode::Recursive)?;

        let watched_path = vault_path.clone();
        thread::spawn(move || {
            for result in rx {
                match result {
                    Ok(event) => {
                        handle_event(&event, &watched_path, &offline_vault);
                    }
                    Err(e) => {
                        log::error!("Vault watcher error: {}", e);
                    }
                }
            }
        });

        Ok(Self {
            _watcher: watcher,
            vault_path,
        })
    }

    pub fn vault_path(&self) -> &Path {
        &self.vault_path
    }
}

fn handle_event(
    event: &Event,
    _vault_path: &Path,
    offline_vault: &Arc<std::sync::Mutex<OfflineVault>>,
) {
    let event_type = match event.kind {
        EventKind::Create(_) => "create",
        EventKind::Modify(_) => "modify",
        EventKind::Remove(_) => "remove",
        _ => return, // Ignore access and other events
    };

    for path in &event.paths {
        // Only track markdown files
        if let Some(ext) = path.extension() {
            if ext != "md" {
                continue;
            }
        } else {
            continue;
        }

        // Skip hidden files and directories (e.g., .obsidian/)
        let path_str = path.to_string_lossy();
        if path_str.contains("/.obsidian/") || path_str.contains("\\.obsidian\\") {
            continue;
        }

        log::info!("Vault change detected: {} {:?}", event_type, path);

        if let Ok(vault) = offline_vault.lock() {
            if let Err(e) = vault.enqueue_file_change(&path_str, event_type) {
                log::error!("Failed to enqueue vault change: {}", e);
            }
        }
    }
}
