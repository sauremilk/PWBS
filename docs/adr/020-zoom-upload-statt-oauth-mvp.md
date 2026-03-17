# ADR-019: Zoom Connector – Switch from OAuth2 to Upload-Based Ingestion in MVP

**Status:** Accepted
**Date:** 2026-03-16
**Decision Makers:** PWBS Core Team

---

## Context

The Zoom connector (TASK-053..055) uses OAuth2 via Zoom Marketplace App for automatic retrieval of cloud recording transcripts. Zoom Marketplace Apps require an approval process (review by Zoom) that can take weeks to months. This external dependency path is a silent blocker on the critical MVP path: without Marketplace approval, no Early Adopter can use the Zoom connector.

The existing OAuth2 implementation is complete (OAuth flow, polling via `fetch_since()`, webhook receiver, VTT parser, `normalize()`) and secured by 141 unit tests. The code is functionally correct — only the external approval process blocks usage.

Without this decision, Zoom remains inaccessible as one of the Core 4 connectors for beta users, even though the technical implementation is finished.

Analogous to ADR-018 (Obsidian: Filesystem Watcher → Upload), an upload fallback is introduced.

---

## Decision

We will switch the Zoom connector in the MVP from OAuth2-based auto-sync to upload-based transcript ingestion, because this removes the external Marketplace approval blocker from the critical path, fully reuses the existing VTT parser and `normalize()` logic, and gives Early Adopters immediate access to Zoom transcripts.

Specifically:

1. **New Endpoint:** `POST /api/v1/connectors/zoom/upload` accepts VTT, SRT, and TXT files (multipart/form-data).
2. **SRT Parser:** New `_parse_srt()` parser supplements the existing `_parse_vtt()`.
3. **Format Detection:** `detect_transcript_format()` automatically detects VTT, SRT, or plaintext based on file extension and content sniffing.
4. **OAuth Code Retained:** The complete OAuth2 implementation (141 tests) remains in `zoom.py`, but is not exposed via API routes in the MVP. `auth_method` in the connector metadata switches from `"oauth2"` to `"upload"`.
5. **Connection Auto-Creation:** On the first upload, a Connection record is automatically created.
6. **Idempotency:** Content-hash-based `source_id` prevents duplicates on re-upload.
7. **SourceType.ZOOM Remains:** No new SourceType — all Zoom documents run under `source_type=zoom`, regardless of whether they came via upload or (later) OAuth.

---

## Options Evaluated

| Option                                                  | Advantages                                                                                          | Disadvantages                                                                                    | Exclusion Reasons                                     |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------- |
| A: New SourceType `zoom_upload`                         | Clear separation of upload vs. OAuth                                                                | Two SourceTypes confuse search and briefings, migration unclear                                  | Unnecessary complexity, forward compatibility suffers |
| **B: SourceType.ZOOM with auth_method=upload (chosen)** | Seamless transition to OAuth, minimal change, identical search filter, existing pipeline compatible | OAuth code remains inactive in codebase                                                          | –                                                     |
| C: Move Zoom to `_deferred/`                            | Clean architectural cut                                                                             | Core 4 → Core 3, contradicts ADR-016, beta testers lose Zoom functionality, VTT parser code lost | Persona "Lena" loses Zoom hypothesis in MVP           |

---

## Consequences

### Positive Consequences

- **No External Blocker:** Zoom transcripts immediately usable, independent of Marketplace approval timeline.
- **Core 4 Remains Complete:** Hypothesis testable, Early Adopters with Zoom focus supported.
- **Code Reuse:** `_parse_vtt()`, `normalize()`, content hash dedup, UDF pipeline — all reused.
- **Forward Compatibility:** After Marketplace approval, `auth_method` is reset to `"oauth2"` and OAuth routes reactivated. Upload endpoint can continue to exist in parallel.
- **Security:** No server needs Zoom API access in MVP. No OAuth tokens stored.

### Negative Consequences / Trade-offs

- **No Auto-Sync in MVP:** Users must manually upload transcripts after each meeting. For 10–20 Early Adopters consciously testing a prototype, this is acceptable.
- **Manual Metadata:** Meeting title and meeting date optionally entered manually (with OAuth, automatically from API).
- **Speaker Extraction Format-Dependent:** VTT files contain speaker labels; SRT and TXT may not.

### Open Questions

- Should the upload endpoint also support batch uploads (multiple files at once)?
- Should a frontend hint "OAuth sync coming soon" be displayed?

---

## GDPR Implications

- **No Change:** Uploaded transcripts pass through the identical UDF pipeline. `owner_id`, `expires_at` (180-day Zoom default), and deletability remain identical.
- **Upload Data:** Not stored as raw files after parsing; only the extracted `UnifiedDocument` objects.
- **Delete Cascade:** On connector disconnect, all Zoom documents are deleted (existing CASCADE logic).
- **No External Data Exchange:** Upload is purely inbound; no data flows back to Zoom.

---

## Security Implications

- **File Upload Validation:** Extension allowlist (.vtt, .srt, .txt), maximum file size (10 MB), UTF-8 encoding check.
- **No Injection Vectors:** Transcript content is parsed as text; no dynamic SQL/Cypher/command execution.
- **No SSRF Risk:** Purely inbound; no external HTTP calls through upload.
- **Auth:** Endpoint behind existing JWT middleware, `owner_id` from token.
- **Rate Limiting:** Upload endpoint uses existing rate limiting.

---

## Revision Date

After completion of the Zoom Marketplace approval process. Then reset `auth_method` to `"oauth2"` and reactivate OAuth routes.
