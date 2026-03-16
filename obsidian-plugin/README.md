# PWBS – Smart Briefings for Obsidian

> Verwandle dein Obsidian-Vault in kontextbezogene AI-Briefings – morgens, vor Meetings oder für Projekte.

## Was macht dieses Plugin?

**PWBS** (Persönliches Wissens-Betriebssystem) verbindet dein Obsidian-Vault mit einer AI-Engine, die dein Wissen versteht und dir genau dann die richtigen Informationen liefert, wenn du sie brauchst.

### 🔄 Vault Sync

- **One-Click Sync** deines gesamten Vaults zu PWBS
- Nur Markdown-Dateien werden synchronisiert – Einstellungen, Themes etc. bleiben lokal
- **Inkrementell** – nur geänderte Dateien werden verarbeitet
- **Auto-Sync** konfigurierbar (alle 15–120 Minuten)

### ⚡ AI Briefings

- **Morning Briefing** – Starte den Tag mit einer Zusammenfassung deiner wichtigsten Themen
- **Meeting Prep** – Automatische Vorbereitung basierend auf deinem Kalender und relevanten Notizen
- **Project Briefing** – Kontext zu jedem Projekt auf Abruf
- Direkt in der **Obsidian-Sidebar** lesbar – kein Tab-Wechsel nötig

### 🔗 Cross-Source Intelligence

Verbinde zusätzlich Google Calendar, Notion und Zoom – PWBS verknüpft alles:

- Meeting-Notizen + Kalendereinträge + Vault-Wissen = vollständiges Bild
- Quellenreferenzen bei jeder Aussage – keine Halluzinationen

## Installation

### Aus der Community (empfohlen)

1. Öffne Obsidian → Einstellungen → Community Plugins
2. Suche nach **"PWBS"**
3. Installieren → Aktivieren

### Manuell

1. Lade `main.js`, `manifest.json` und `styles.css` aus dem [neuesten Release](https://github.com/sauremilk/obsidian-pwbs-sync/releases) herunter
2. Erstelle den Ordner `.obsidian/plugins/pwbs-sync/` in deinem Vault
3. Kopiere die drei Dateien dorthin
4. Aktiviere das Plugin in den Obsidian-Einstellungen

## Einrichtung

1. **Erstelle ein kostenloses Konto** auf [pwbs.app](https://pwbs.app/signup)
2. Kopiere deinen **API-Token** aus PWBS → Einstellungen → API
3. In Obsidian: Einstellungen → PWBS → Token einfügen
4. Klicke auf **"Verbindung testen"** ✅

## Verwendung

| Aktion                 | Shortcut                                      |
| ---------------------- | --------------------------------------------- |
| Vault synchronisieren  | `Cmd/Ctrl+P` → "PWBS: Vault synchronisieren"  |
| Briefing anzeigen      | `Cmd/Ctrl+P` → "PWBS: Briefing anzeigen"      |
| Briefing aktualisieren | `Cmd/Ctrl+P` → "PWBS: Briefing aktualisieren" |
| Quick Sync             | ⚡-Icon in der Sidebar                        |

### Ordner ausschließen

In den Plugin-Einstellungen kannst du Ordner vom Sync ausschließen (komma-getrennt):

```
private,archiv,templates,daily-notes
```

Standardmäßig ausgeschlossen: `.obsidian`, `.git`, `.trash`, `node_modules`

## Datenschutz & Sicherheit

- 🔒 **Ende-zu-Ende verschlüsselt** – Daten werden verschlüsselt übertragen
- 🇪🇺 **DSGVO-konform** – Server in der EU, Löschrecht jederzeit
- 🚫 **Kein LLM-Training** – Deine Daten werden niemals für Modell-Training verwendet
- ⏰ **Ablaufdatum** – Alle Daten haben ein konfigurierbares Verfallsdatum
- 🗑️ **Vollständige Löschung** – Account löschen = alle Daten weg

## Development

```bash
# Dependencies installieren
npm install

# Development Build (mit watch)
npm run dev

# Production Build
npm run build
```

## Support

- 🐛 [Bug melden](https://github.com/sauremilk/obsidian-pwbs-sync/issues)
- 💬 [Discussions](https://github.com/sauremilk/obsidian-pwbs-sync/discussions)
- 📧 support@pwbs.app

## License

MIT
