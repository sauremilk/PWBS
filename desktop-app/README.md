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
- **Dashboard oeffnen**  Hauptfenster zeigen, Navigation zu `/`
- **Suche**  Navigation zu `/search`
- **Heutiges Briefing**  Navigation zu `/briefings`
- **Beenden**  App schliessen

Linksklick auf das Tray-Icon zeigt/fokussiert das Hauptfenster.

### Native Benachrichtigungen

IPC-Command `send_notification` fuer Frontend-Integration:

```typescript
import { invoke } from '@tauri-apps/api/core';

await invoke('send_notification', {
  title: 'Neues Morgenbriefing',
  body: 'Dein Briefing fuer heute ist bereit.'
});
```

### Auto-Updater

- Prueft beim App-Start automatisch auf Updates
- IPC-Command `check_for_updates` fuer manuelle Pruefung
- Konfiguration in `tauri.conf.json` unter `plugins.updater`
- Signierte Updates ueber konfigurierbaren Endpoint
