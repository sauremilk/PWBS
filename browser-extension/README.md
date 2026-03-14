# PWBS Browser Extension (TASK-140)

Chrome-Extension-Prototyp fuer das Persoenliche Wissens-Betriebssystem (PWBS).

## Features

- **Kontextuelle Sidebar**: Zeigt relevante Entitaeten und Dokumente basierend auf der aktuell besuchten Notion- oder Google-Docs-Seite
- **Quick Search**: Semantische Suche ueber die PWBS-API direkt aus der Extension
- **JWT-Authentifizierung**: Session-Sharing mit der PWBS Web-App ueber gespeicherten JWT-Token

## Unterstuetzte Seiten

- Notion (notion.so)
- Google Docs (docs.google.com)

## Installation (Entwicklung)

1. Chrome oeffnen und `chrome://extensions` aufrufen
2. "Entwicklermodus" aktivieren (oben rechts)
3. "Entpackte Erweiterung laden" klicken
4. Den `browser-extension/` Ordner auswaehlen
5. Extension-Icon klicken und JWT-Token eingeben

## Architektur

```
browser-extension/
  manifest.json          # Chrome Manifest V3
  src/
    api.js               # PWBS API Client (JWT-auth, search, entities)
    background.js        # Service Worker (Message-Routing)
    content.js           # Content Script (Seitentitel-Extraktion)
    popup.html/js        # Login-Popup (JWT-Token-Eingabe)
    sidepanel.html/js    # Sidebar (Entitaeten, Dokumente, Suche)
  icons/
    icon16.png           # Extension-Icons
    icon48.png
    icon128.png
```

## Prototyp-Scope

- Nur Chrome (kein Firefox)
- Nur Notion und Google Docs
- Keine Daten-Ingestion ueber die Extension
- Lese-Zugriff auf PWBS Search-API und Knowledge-API

## API-Endpunkte

Die Extension nutzt ausschliesslich bestehende Backend-Endpunkte:

- `GET /api/v1/search?q=...&top_k=5`  Semantische Suche
- `GET /api/v1/knowledge/entities?q=...&limit=10`  Entitaeten-Abfrage