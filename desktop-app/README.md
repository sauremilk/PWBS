# PWBS Desktop App

Tauri v2-basierte Desktop-Anwendung fuer das Persoenliche Wissens-Betriebssystem.

## Architektur

- **Tauri v2** mit Rust-Backend und WebView-Frontend
- Die Desktop-App laedt dieselbe Next.js-Web-App im WebView
- System-Tray mit Schnellzugriff auf Dashboard, Suche und Briefings
- Native OS-Benachrichtigungen fuer neue Briefings und Erinnerungen
- Auto-Updater prueft und installiert Updates im Hintergrund

Siehe [ADR-008](../docs/adr/008-tauri-desktop-app.md) fuer die Architekturentscheidung.

## Voraussetzungen

- [Rust](https://rustup.rs/) >= 1.77
- [Tauri CLI v2](https://v2.tauri.app/start/prerequisites/): `cargo install tauri-cli --version "^2"`
- Plattform-spezifische Abhaengigkeiten:
  - **Windows:** WebView2 (in Windows 10/11 bereits enthalten)
  - **macOS:** Xcode Command Line Tools
  - **Linux:** `libwebkit2gtk-4.1-dev`, `libappindicator3-dev`, `librsvg2-dev`

## Entwicklung

```bash
# Frontend im Dev-Modus starten (in separatem Terminal)
cd ../frontend && npm run dev

# Desktop-App im Dev-Modus starten (laedt http://localhost:3000)
cargo tauri dev
```

## Build

```bash
# Produktions-Build (kompiliert Frontend + Rust-Binary)
cargo tauri build
```

Das Binary liegt unter `src-tauri/target/release/bundle/`.

## Release & Distribution

Releases werden automatisiert ueber GitHub Actions erstellt:

```bash
# Neues Release taggen (loest CI/CD-Pipeline aus)
git tag desktop-v0.1.0
git push origin desktop-v0.1.0
```

Der Workflow `.github/workflows/desktop-release.yml` baut automatisch:

| Platform              | Installer           |
| --------------------- | ------------------- |
| Windows (x64)         | `.exe` (NSIS)       |
| macOS (Intel)         | `.dmg`              |
| macOS (Apple Silicon) | `.dmg`              |
| Linux (x64)           | `.AppImage`, `.deb` |

Artefakte werden als GitHub Release publiziert inkl. `latest.json` fuer den Auto-Updater.

### Secrets (in GitHub Repository Settings konfigurieren)

| Secret                               | Beschreibung                                                                   |
| ------------------------------------ | ------------------------------------------------------------------------------ |
| `TAURI_SIGNING_PRIVATE_KEY`          | Tauri Updater-Signaturschluessel (generiert mit `cargo tauri signer generate`) |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | Passwort fuer den Signaturschluessel                                           |
| `APPLE_CERTIFICATE`                  | Base64-kodiertes Apple Developer Certificate (.p12)                            |
| `APPLE_CERTIFICATE_PASSWORD`         | Passwort des Zertifikats                                                       |
| `KEYCHAIN_PASSWORD`                  | Temporaeres Keychain-Passwort fuer CI                                          |

### Updater-Schluessel generieren

```bash
cargo tauri signer generate -w ~/.tauri/pwbs.key
```

Den Public Key in `tauri.conf.json` unter `plugins.updater.pubkey` eintragen.

## Projektstruktur

```
desktop-app/
+-- src-tauri/
|   +-- Cargo.toml          # Rust-Abhaengigkeiten
|   +-- build.rs             # Tauri Build-Script
|   +-- tauri.conf.json      # Tauri-Konfiguration (Window, Bundle, Updater)
|   +-- capabilities/        # Tauri v2 Permission System
|   |   +-- default.json     # Erlaubte APIs (Notification, Shell, Updater)
|   +-- icons/               # App-Icons (generiert mit `cargo tauri icon`)
|   +-- src/
|       +-- main.rs          # Entry Point (Windows Subsystem)
|       +-- lib.rs           # App-Setup, Plugins, IPC-Commands
|       +-- tray.rs          # System-Tray mit Kontextmenue
+-- package.json             # npm-Scripts fuer Tauri CLI
+-- README.md
```

## Features

### System Tray

Kontextmenue mit:

- **Dashboard oeffnen** Hauptfenster zeigen, Navigation zu `/`
- **Suche** Navigation zu `/search`
- **Heutiges Briefing** Navigation zu `/briefings`
- **Beenden** App schliessen

Linksklick auf das Tray-Icon zeigt/fokussiert das Hauptfenster.

### Native Benachrichtigungen

IPC-Command `send_notification` fuer Frontend-Integration:

```typescript
import { invoke } from "@tauri-apps/api/core";

await invoke("send_notification", {
  title: "Neues Morgenbriefing",
  body: "Dein Briefing fuer heute ist bereit.",
});
```

### Auto-Updater

- Prueft beim App-Start automatisch auf Updates
- IPC-Command `check_for_updates` fuer manuelle Pruefung
- Konfiguration in `tauri.conf.json` unter `plugins.updater`
- Signierte Updates ueber konfigurierbaren Endpoint

### Offline-Modus (TASK-136)

Lokaler SQLite-Vault (`offline_vault.db` im App-Data-Verzeichnis) fuer Offline-Zugriff:

- **Briefings**: Letzte 7 Tage werden automatisch gecacht
- **Entitaeten**: Top-50 nach Mention-Count werden lokal gespeichert
- **Embeddings**: Vektoren im SQLite als BLOB fuer lokale Cosine-Similarity-Suche
- **Obsidian-Vault-Watcher**: Filesystem-Events werden gepuffert und bei Reconnect synchronisiert
- **Sync**: Last-Write-Wins-Strategie, periodische Konnektivitaetspruefung alle 5 Minuten

```typescript
import { invoke } from '@tauri-apps/api/core';

// Sync-Status abfragen
const status = await invoke('get_sync_status');
// => { "online": { "last_sync": "2024-01-15T08:30:00Z" } }
// => { "offline": { "last_sync": "2024-01-15T08:30:00Z" } }
// => { "syncing": { "progress": 0.66 } }

// Manuellen Sync ausloesen
await invoke('trigger_sync', { token: 'jwt...', ownerId: 'uuid...' });

// Offline-Briefings abrufen
const briefings = await invoke('get_offline_briefings', { ownerId: 'uuid...' });

// Offline-Suche (mit vorberechnetem Query-Embedding)
const results = await invoke('offline_search', {
  ownerId: 'uuid...',
  queryEmbedding: [0.1, 0.2, ...],
  topK: 5
});
```

Umgebungsvariablen:

- `PWBS_API_URL`: Backend-URL (Standard: `http://localhost:8000`)
- `PWBS_OBSIDIAN_VAULT`: Pfad zum Obsidian-Vault-Verzeichnis (optional)
