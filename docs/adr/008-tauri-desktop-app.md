# ADR-008: Tauri statt Electron (Desktop-App, Phase 3+)

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

In Phase 3+ soll eine Desktop-App das PWBS als native Anwendung auf macOS, Windows und Linux bereitstellen. Die Desktop-App ermöglicht Offline-Zugriff, lokale Verschlüsselung ohne Cloud-Abhängigkeit und schnellen Zugriff über die Taskbar. Die Wahl des Desktop-Frameworks beeinflusst Binary-Größe, Speicherverbrauch, Sicherheitsarchitektur und die Möglichkeit, lokale Vault-Operationen durchzuführen.

---

## Entscheidung

Wir verwenden **Tauri** statt Electron für die Desktop-App, weil die deutlich kleinere Binary, der geringere Speicherverbrauch und das Rust-Backend lokale Verschlüsselung und Vault-Zugriff ohne Node.js-Overhead ermöglichen.

---

## Optionen bewertet

| Option                    | Vorteile                                                                                                                                                                                                                                     | Nachteile                                                                                                                                             | Ausschlussgründe                                     |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| **Tauri** (gewählt)       | Deutlich kleinere Binary (~10 MB vs. ~150 MB Electron). Geringerer Speicherverbrauch (native WebView statt Chromium). Rust-Backend ermöglicht lokale Verschlüsselung und Vault-Zugriff ohne Node.js. Cross-Platform (macOS, Windows, Linux). | Kleineres Ökosystem als Electron, weniger Plugins. Rust-Kenntnisse für System-Layer erforderlich.                                                     | –                                                    |
| Electron                  | Größtes Desktop-App-Ökosystem, sehr viele Plugins und Beispiele. Einheitliche Chromium-Basis garantiert konsistentes Rendering.                                                                                                              | ~150 MB Binary pro Platform. Hoher Speicherverbrauch (~200-300 MB RAM). Node.js für System-Layer weniger geeignet für Kryptografie-Operationen.       | Binary-Größe und RAM-Verbrauch inakzeptabel          |
| Progressive Web App (PWA) | Kein separater Download, funktioniert in jedem Browser, automatische Updates.                                                                                                                                                                | Kein Zugriff auf lokales Filesystem (Vault), eingeschränkte Offline-Fähigkeiten, kein Taskbar/System-Tray. Nicht geeignet für lokale Verschlüsselung. | Fehlender Filesystem-Zugriff und lokale Kryptografie |

---

## Konsequenzen

### Positive Konsequenzen

- ~10 MB Binary statt ~150 MB (Electron) – schnellerer Download, geringere Systemanforderungen
- Rust-Backend für System-Layer: native AES-256-GCM-Verschlüsselung, lokaler Key-Vault, Filesystem-Zugriff
- Desktop-App nutzt dasselbe Web-Frontend (WebView) – kein separates UI-Codebase
- Geringerer Speicherverbrauch: Native WebView statt eingebettetes Chromium
- Auto-Updates über Tauri-eigenes Update-System

### Negative Konsequenzen / Trade-offs

- Kleineres Plugin-Ökosystem als Electron (mitigiert: PWBS benötigt wenige Desktop-spezifische Plugins – Hauptfunktionalität läuft im Web-Frontend)
- Rust-Kenntnisse erforderlich für den System-Layer (mitigiert: System-Layer ist klein und klar abgegrenzt – hauptsächlich Kryptografie und Filesystem-Zugriff)
- WebView-Rendering kann zwischen Plattformen variieren (macOS: WebKit, Windows: WebView2/Edge, Linux: WebKitGTK) – erfordert Cross-Platform-Testing

### Offene Fragen

- Tauri v2 vs. v1 Entscheidung (v2 bringt Mobile-Support)
- CI/CD-Pipeline für Cross-Platform-Builds (macOS Agent für Code Signing)

---

## DSGVO-Implikationen

- **Lokale Datenhaltung:** Desktop-App kann als DSGVO-Strict-Modus dienen – alle Daten bleiben auf dem lokalen Gerät.
- **Lokaler Vault:** Rust-Backend ermöglicht lokalen Schlüsselkasten (Keyring-Integration) für DEK-Speicherung ohne Cloud.
- **Keine Cloud-Abhängigkeit:** Im Offline-Modus werden keine Daten an externe Services übermittelt.
- **Löschbarkeit:** App-Deinstallation plus lokaler Datenlöschung (AppData-Verzeichnis) entfernt alle Nutzerdaten vollständig.

---

## Sicherheitsimplikationen

- Rust-Backend: Memory Safety ohne Garbage Collector – reduziert Risiko von Buffer Overflows und Use-After-Free-Bugs im System-Layer
- Lokale Verschlüsselung: AES-256-GCM über Rust-Crypto-Libraries (ring, aes-gcm) statt JavaScript-Kryptografie
- System-Keyring-Integration: DEKs werden im OS-spezifischen Keyring gespeichert (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Tauri-IPC-Boundary: Frontend (WebView) hat eingeschränkten Zugriff auf System-APIs – explizites Allowlisting erforderlich
- Code Signing für alle Distributionen (macOS Notarization, Windows Code Signing)

---

## Revisionsdatum

2027-09-13 – Bewertung vor Phase-3-Start. Evaluation von Tauri v2 und Cross-Platform-Testing-Ergebnisse.
