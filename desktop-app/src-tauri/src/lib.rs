mod offline;
mod tray;

use offline::{LocalSearch, OfflineVault, SyncEngine, SyncStatus, VaultWatcher};
use std::path::PathBuf;
use std::sync::Arc;
use tauri::Manager;

struct AppState {
    vault: Arc<std::sync::Mutex<OfflineVault>>,
    sync_engine: Arc<SyncEngine>,
    _watcher: Option<VaultWatcher>,
}

/// Send a native OS notification.
/// Called from the frontend via Tauri IPC or from scheduled Rust timers.
#[tauri::command]
fn send_notification(app: tauri::AppHandle, title: String, body: String) -> Result<(), String> {
    use tauri_plugin_notification::NotificationExt;
    app.notification()
        .builder()
        .title(&title)
        .body(&body)
        .show()
        .map_err(|e| e.to_string())
}

/// Check for application updates and install if available.
#[tauri::command]
async fn check_for_updates(app: tauri::AppHandle) -> Result<String, String> {
    use tauri_plugin_updater::UpdaterExt;
    match app.updater().map_err(|e| e.to_string())?.check().await {
        Ok(Some(update)) => {
            let version = update.version.clone();
            update
                .download_and_install(|_, _| {}, || {})
                .await
                .map_err(|e| e.to_string())?;
            Ok(format!("Updated to {}", version))
        }
        Ok(None) => Ok("Already up to date".to_string()),
        Err(e) => Err(e.to_string()),
    }
}

/// Get the current sync status (Online/Offline/Syncing).
#[tauri::command]
async fn get_sync_status(state: tauri::State<'_, AppState>) -> Result<SyncStatus, String> {
    Ok(state.sync_engine.get_status().await)
}

/// Trigger a manual sync with the cloud backend.
#[tauri::command]
async fn trigger_sync(
    state: tauri::State<'_, AppState>,
    token: String,
    owner_id: String,
) -> Result<String, String> {
    state
        .sync_engine
        .sync_all(&state.vault, &token, &owner_id)
        .await
        .map_err(|e| e.to_string())?;
    Ok("Sync complete".to_string())
}

/// Get cached briefings from the local offline vault.
#[tauri::command]
fn get_offline_briefings(
    state: tauri::State<'_, AppState>,
    owner_id: String,
) -> Result<Vec<offline::vault::CachedBriefing>, String> {
    let vault = state.vault.lock().map_err(|e| e.to_string())?;
    vault.get_briefings(&owner_id, 7).map_err(|e| e.to_string())
}

/// Get top entities from the local offline vault.
#[tauri::command]
fn get_offline_entities(
    state: tauri::State<'_, AppState>,
    owner_id: String,
) -> Result<Vec<offline::vault::CachedEntity>, String> {
    let vault = state.vault.lock().map_err(|e| e.to_string())?;
    vault.get_top_entities(&owner_id, 50).map_err(|e| e.to_string())
}

/// Search locally cached embeddings (offline search).
#[tauri::command]
fn offline_search(
    state: tauri::State<'_, AppState>,
    owner_id: String,
    query_embedding: Vec<f32>,
    top_k: Option<usize>,
) -> Result<Vec<offline::search::LocalSearchResult>, String> {
    let vault = state.vault.lock().map_err(|e| e.to_string())?;
    LocalSearch::search(&vault, &owner_id, &query_embedding, top_k.unwrap_or(10))
        .map_err(|e| e.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            send_notification,
            check_for_updates,
            get_sync_status,
            trigger_sync,
            get_offline_briefings,
            get_offline_entities,
            offline_search,
        ])
        .setup(|app| {
            tray::create_tray(app)?;

            // Initialize offline vault in app data directory
            let app_data = app.path().app_data_dir().expect("no app data dir");
            std::fs::create_dir_all(&app_data).ok();
            let db_path = app_data.join("offline_vault.db");
            let vault = OfflineVault::open(&db_path)
                .expect("Failed to open offline vault");
            let vault = Arc::new(std::sync::Mutex::new(vault));

            // Initialize sync engine
            let base_url = std::env::var("PWBS_API_URL")
                .unwrap_or_else(|_| "http://localhost:8000".to_string());
            let sync_engine = Arc::new(SyncEngine::new(base_url));

            // Optionally start Obsidian vault watcher
            let watcher = std::env::var("PWBS_OBSIDIAN_VAULT")
                .ok()
                .map(|p| PathBuf::from(p))
                .and_then(|p| {
                    if p.exists() {
                        match VaultWatcher::start(p.clone(), vault.clone()) {
                            Ok(w) => {
                                log::info!("Obsidian vault watcher started: {:?}", w.vault_path());
                                Some(w)
                            }
                            Err(e) => {
                                log::error!("Failed to start vault watcher: {}", e);
                                None
                            }
                        }
                    } else {
                        log::warn!("Obsidian vault path does not exist: {:?}", p);
                        None
                    }
                });

            // Store state
            app.manage(AppState {
                vault: vault.clone(),
                sync_engine: sync_engine.clone(),
                _watcher: watcher,
            });

            // Periodic connectivity check and sync (every 5 minutes)
            let sync_handle = sync_engine.clone();
            tauri::async_runtime::spawn(async move {
                let mut interval = tokio::time::interval(std::time::Duration::from_secs(300));
                loop {
                    interval.tick().await;
                    if sync_handle.check_connectivity().await {
                        log::info!("Backend reachable, connectivity OK");
                    } else {
                        log::info!("Backend not reachable, entering offline mode");
                        sync_handle.set_offline().await;
                    }
                }
            });

            // Check for updates on startup (non-blocking)
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_updater::UpdaterExt;
                if let Ok(updater) = handle.updater() {
                    match updater.check().await {
                        Ok(Some(update)) => {
                            log::info!("Update available: {}", update.version);
                            let _ = update.download_and_install(|_, _| {}, || {}).await;
                        }
                        Ok(None) => log::info!("App is up to date"),
                        Err(e) => log::warn!("Update check failed: {}", e),
                    }
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running PWBS desktop application");
}
