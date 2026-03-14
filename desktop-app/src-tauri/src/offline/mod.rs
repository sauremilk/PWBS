pub mod vault;
pub mod sync;
pub mod search;
pub mod watcher;

pub use vault::OfflineVault;
pub use sync::{SyncEngine, SyncStatus};
pub use search::LocalSearch;
pub use watcher::VaultWatcher;
