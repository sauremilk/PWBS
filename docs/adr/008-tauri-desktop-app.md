# ADR-008: Tauri Instead of Electron (Desktop App, Phase 3+)

**Status:** Accepted
**Date:** 2026-03-13
**Decision Makers:** PWBS Core Team

---

## Context

In Phase 3+, a desktop app will provide the PWBS as a native application on macOS, Windows, and Linux. The desktop app enables offline access, local encryption without cloud dependency, and quick access via the taskbar. The choice of desktop framework affects binary size, memory consumption, security architecture, and the ability to perform local vault operations.

---

## Decision

We use **Tauri** instead of Electron for the desktop app, because the significantly smaller binary, lower memory consumption, and Rust backend enable local encryption and vault access without Node.js overhead.

---

## Options Evaluated

| Option                    | Advantages                                                                                                                                                                                                                                 | Disadvantages                                                                                                                                | Exclusion Reasons                                |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| **Tauri** (chosen)        | Significantly smaller binary (~10 MB vs. ~150 MB Electron). Lower memory consumption (native WebView instead of Chromium). Rust backend enables local encryption and vault access without Node.js. Cross-platform (macOS, Windows, Linux). | Smaller ecosystem than Electron, fewer plugins. Rust knowledge required for system layer.                                                    | –                                                |
| Electron                  | Largest desktop app ecosystem, many plugins and examples. Unified Chromium base guarantees consistent rendering.                                                                                                                           | ~150 MB binary per platform. High memory consumption (~200-300 MB RAM). Node.js for system layer less suitable for cryptographic operations. | Binary size and RAM consumption unacceptable     |
| Progressive Web App (PWA) | No separate download, works in any browser, automatic updates.                                                                                                                                                                             | No access to local filesystem (vault), limited offline capabilities, no taskbar/system tray. Not suitable for local encryption.              | Missing filesystem access and local cryptography |

---

## Consequences

### Positive Consequences

- ~10 MB binary instead of ~150 MB (Electron) – faster download, lower system requirements
- Rust backend for system layer: native AES-256-GCM encryption, local key vault, filesystem access
- Desktop app uses the same web frontend (WebView) – no separate UI codebase
- Lower memory consumption: native WebView instead of embedded Chromium
- Auto-updates via Tauri's built-in update system

### Negative Consequences / Trade-offs

- Smaller plugin ecosystem than Electron (mitigated: PWBS requires few desktop-specific plugins – main functionality runs in the web frontend)
- Rust knowledge required for the system layer (mitigated: system layer is small and clearly scoped – primarily cryptography and filesystem access)
- WebView rendering can vary between platforms (macOS: WebKit, Windows: WebView2/Edge, Linux: WebKitGTK) – requires cross-platform testing

### Open Questions

- Tauri v2 vs. v1 decision (v2 brings mobile support)
- CI/CD pipeline for cross-platform builds (macOS agent for code signing)

---

## GDPR Implications

- **Local Data Storage:** Desktop app can serve as a GDPR strict mode – all data remains on the local device.
- **Local Vault:** Rust backend enables a local keystore (keyring integration) for DEK storage without cloud.
- **No Cloud Dependency:** In offline mode, no data is transmitted to external services.
- **Erasability:** App uninstallation plus local data deletion (AppData directory) completely removes all user data.

---

## Security Implications

- Rust backend: memory safety without garbage collector – reduces risk of buffer overflows and use-after-free bugs in the system layer
- Local encryption: AES-256-GCM via Rust crypto libraries (ring, aes-gcm) instead of JavaScript cryptography
- System keyring integration: DEKs are stored in the OS-specific keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Tauri IPC boundary: frontend (WebView) has restricted access to system APIs – explicit allowlisting required
- Code signing for all distributions (macOS notarization, Windows code signing)

---

## Revision Date

2027-09-13 – Assessment before Phase 3 start. Evaluation of Tauri v2 and cross-platform testing results.
