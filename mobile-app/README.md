# PWBS Mobile App (TASK-152)

Cross-Platform Mobile App fuer iOS und Android, basierend auf React Native + Expo.

## Features

- **Briefings lesen** – Morgen-, Meeting-, Projekt- und Wochen-Briefings mit Quellenverweisen
- **Semantische Suche** – Wissensbestand durchsuchen
- **Schnellnotizen** – Text- und Spracherfassung
- **Push-Notifications** – Erinnerungen und neue Briefings
- **Offline-Caching** – Letzte 3 Briefings + Top-20 Entitaeten offline verfuegbar

## Tech Stack

- React Native 0.76 + Expo SDK 52
- TypeScript (strict mode)
- TanStack Query fuer API-State
- Expo SecureStore fuer Token-Speicherung
- Expo AV fuer Sprachaufnahme
- Expo Notifications fuer Push

## Entwicklung starten

```bash
cd mobile-app
npm install
npx expo start
```

## Projektstruktur

```
mobile-app/
  App.tsx                    # Entry point
  app.json                   # Expo config
  src/
    api/client.ts            # API client (alle Aufrufe via dieses Modul)
    components/              # Wiederverwendbare Komponenten
    hooks/                   # React Query hooks
    navigation/              # Stack + Tab Navigation
    screens/                 # Screen-Komponenten
    storage/offline.ts       # Offline-Caching mit FileSystem
    types/index.ts           # TypeScript-Typen
    utils/notifications.ts   # Push-Notification-Setup
```

## Sicherheit

- Auth-Tokens werden via Expo SecureStore gespeichert (Keychain/Keystore)
- Keine Secrets im Code
- API-Aufrufe ausschliesslich ueber `src/api/client.ts`
