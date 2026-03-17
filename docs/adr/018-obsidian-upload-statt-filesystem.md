# ADR-018: Obsidian Connector – Switch from Filesystem Watcher to Upload-Based Ingestion

**Status:** Proposed
**Date:** 2026-03-16
**Decision Makers:** PWBS Core Team

---

## Context

The Obsidian connector (TASK-051/052) uses `watchdog` for file system watching and direct filesystem access via `Path.stat()` and `scan_vault_files()`. This requires the backend to run on the same machine as the user's Obsidian vault. The planned deployment topology (ECS Fargate, ADR-001/006) is a containerized cloud service without access to local user filesystems. The Obsidian connector is thus the only one of the Core 4 connectors that is architecturally incompatible with the production deployment.

Without this decision, PWBS cannot work with Obsidian data in the cloud environment, or users would be forced to run the backend locally – which contradicts the web app model.

---

## Decision

We will switch the Obsidian connector from filesystem-based access (watchdog + local scanning) to upload-based ingestion, because this establishes cloud deployment compatibility, fully reuses the existing Markdown parser and `normalize()` logic, and ensures forward compatibility with the desktop app (Tauri, Phase 3), whose `SyncEngine` has already implemented a push-to-API mechanism.

Specifically:

1. **New Endpoint:** `POST /api/v1/connectors/obsidian/upload` accepts ZIP archives or individual Markdown files (multipart/form-data).
2. **Remove Filesystem Watcher:** `ObsidianWatcher`, `ObsidianFileHandler`, and the `watchdog` dependency are removed from the active MVP code (code is retained for desktop app usage in Phase 3).
3. **Refactor `fetch_since()`:** Operates on uploaded content instead of direct filesystem scanning.
4. **Content Hash Dedup:** Already existing documents are detected via content hash; only changed/new files are processed.
5. **Deletion Detection:** Files missing from a new upload are marked as deleted.
6. **Frontend:** Vault path input field is replaced by a drag-and-drop/file upload component.

---

## Options Evaluated

| Option                                                           | Advantages                                                                                                                  | Disadvantages                                                                                          | Exclusion Reasons                         |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ----------------------------------------- |
| A: Upload Connector Only                                         | Cloud-compatible, simple, existing parser reusable                                                                          | No automatic syncing, UX friction                                                                      | No explicit migration path to desktop app |
| B: Move Obsidian to `_deferred/` (Phase 3)                       | Clean architectural cut, no UX compromise                                                                                   | Core 4 → Core 3, Obsidian hypothesis not testable in MVP, beta testers with Obsidian focus unsupported | Persona "Lena" loses MVP access entirely  |
| **C: Hybrid – Upload now + Desktop Watcher in Phase 3 (chosen)** | Cloud-compatible, Core 4 preserved, forward-compatible with Tauri SyncEngine, existing parser reusable, hypothesis testable | Two sync modes must coexist long-term (upload + auto-sync), upload UX inferior to auto-sync            | –                                         |

---

## Consequences

### Positive Consequences

- **Cloud Deployment Compatibility:** No filesystem access needed in backend – ECS Fargate works immediately.
- **Core 4 Remains Complete:** Obsidian is still available as a connector, the hypothesis is testable.
- **Forward Compatibility:** The Tauri desktop app (`SyncEngine` in `desktop-app/src-tauri/src/offline/sync.rs`) uses the same upload/push endpoint transparently – no additional backend code needed.
- **Security:** No server needs access to local filesystems. All data comes through authenticated API calls.
- **~400 LOC fewer** in the active backend (watcher code removed from the hot path).

### Negative Consequences / Trade-offs

- **No Auto-Sync in MVP:** Users must manually upload vault contents (every 1–2 days). Persona "Lena" has higher friction than with a real-time watcher.
- **Upload Size Limit:** Large vaults (>50 MB, >5,000 files) require batching or higher limits.
- **ZIP Security:** New attack vector (ZIP bombs, path traversal) must be mitigated.

### Open Questions

- Should the upload endpoint also be accessible from the public API (`/api/v1/public/...`), or only via JWT auth?
- Maximum upload size: Is 50 MB sufficient for typical Obsidian vaults?
- Should an "Obsidian Community Plugin" be evaluated as an alternative push channel (plugin syncs directly to the PWBS API)?

---

## GDPR Implications

- **No Change:** Uploaded Markdown files pass through the same UDF pipeline as before. `owner_id`, `expires_at`, and deletability remain identical.
- **Upload Data:** Not stored as raw files after processing; only the extracted `UnifiedDocument` objects with complete GDPR metadata structure.
- **Delete Cascade:** On connector disconnect, all documents from uploads are deleted (existing CASCADE logic).

---

## Security Implications

- **ZIP Bomb Protection:** Limit maximum unpacked size (e.g., 200 MB), maximum file count (5,000), abort on exceeding limits.
- **Path Traversal:** All paths in ZIP archives are sanitized – no `../` paths, only `.md` files extracted.
- **Rate Limiting:** Upload endpoint receives its own rate limit (e.g., 5 uploads/hour/user) due to large payloads.
- **Auth:** Endpoint behind existing JWT middleware, `owner_id` from token.
- **No New External Calls:** Upload is purely inbound, no SSRF risk.

---

## Revision Date

Phase 3 – Desktop App Release (expected Q3 2026). Then evaluate whether upload mode is retained or replaced by auto-sync via Tauri.
