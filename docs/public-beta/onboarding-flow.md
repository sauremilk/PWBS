# Automatisierter Onboarding-Flow – Public Beta (TASK-148)

## Ziel

Jeder neue Nutzer durchläuft innerhalb von 5 Minuten den Weg: **Registrierung → erster Konnektor → erstes Briefing** – ohne manuelle Intervention.

---

## Flow-Schritte

### 1. Registrierung (`POST /api/v1/auth/register`)

- E-Mail + Passwort (min. 12 Zeichen, Großbuchstabe, Ziffer)
- Automatische DEK-Generierung (Envelope Encryption, ADR-009)
- JWT-Token-Paar wird sofort ausgestellt

**Frontend:** `/register` → Formular → Welcome-Screen

### 2. Welcome-Screen

Nach erfolgreicher Registrierung wird der Nutzer auf den Welcome-Screen weitergeleitet:

- **Schritt 1:** "Verbinde deine erste Datenquelle" → Link zu `/connectors`
- **Schritt 2:** "Dein erstes Briefing" → Wird automatisch generiert

### 3. Erster Konnektor (`/connectors`)

- Konnektor-Auswahl: Google Calendar, Gmail, Notion, Slack
- OAuth-Flow startet (`GET /api/v1/connectors/{type}/auth-url`)
- Nach Callback: automatische Initial-Sync (`POST /api/v1/connectors/{id}/sync`)
- Fortschrittsanzeige im Frontend

### 4. Erstes Briefing (automatisch)

Nach erfolgreicher Ingestion des ersten Konnektors:

1. ProcessingAgent generiert Embeddings + Entities
2. BriefingAgent generiert automatisch ein Morning Briefing
3. Dashboard zeigt das Briefing als erstes Widget

**Trigger:** `briefing_auto_generate: true` (Default in User-Settings)

---

## Technische Umsetzung

### Backend-Flow

```
register_user()
  → create User + DEK
  → issue JWT
  → Frontend redirect to /connectors

connect_connector()
  → OAuth callback
  → IngestionAgent.run(connector)
  → ProcessingAgent.process(documents)
  → if first_sync AND briefing_auto_generate:
      BriefingAgent.generate(type="morning", user_id=user.id)
```

### Frontend-Flow

```
/register
  → [Registrierung erfolgreich]
  → /welcome (Welcome-Screen mit Stepper)
    → Schritt 1: Konnektor verbinden (/connectors)
    → Schritt 2: Warten auf Sync-Completion (Polling /connectors/status)
    → Schritt 3: Redirect zu Dashboard (/ mit erstem Briefing)
```

### API-Endpunkte im Onboarding

| Schritt              | Methode | Endpunkt                               |
| -------------------- | ------- | -------------------------------------- |
| Registrierung        | POST    | `/api/v1/auth/register`                |
| Konnektor-Liste      | GET     | `/api/v1/connectors/`                  |
| OAuth starten        | GET     | `/api/v1/connectors/{type}/auth-url`   |
| OAuth Callback       | POST    | `/api/v1/connectors/{type}/callback`   |
| Sync starten         | POST    | `/api/v1/connectors/{id}/sync`         |
| Sync-Status prüfen   | GET     | `/api/v1/connectors/status`            |
| Briefing abrufen     | GET     | `/api/v1/briefings?type=morning`       |

---

## Metriken

| Metrik                           | Ziel      |
| -------------------------------- | --------- |
| Time-to-First-Briefing           | < 5 min   |
| Onboarding-Completion-Rate       | > 70%     |
| Konnektor-Verbindungs-Erfolgsrate| > 90%     |
| Drop-off nach Registrierung      | < 30%     |

---

## Monitoring

- **Audit-Log:** Jeder Onboarding-Schritt wird mit `AuditAction` geloggt
- **CloudWatch Metrics:** Custom Metrics für Onboarding-Funnel
- **Alerting:** Slack-Alert wenn Completion-Rate unter 50% fällt
