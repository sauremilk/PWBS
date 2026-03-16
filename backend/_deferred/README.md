# \_deferred/ – Ausgelagerte Phase-3+-Module

Dieses Verzeichnis enthält Module, die für das MVP (Phase 2, 10–20 Early Adopters)
bewusst deaktiviert wurden. Kein Code wurde gelöscht – alles ist hier vollständig
erhalten und kann bei Bedarf reaktiviert werden.

## Enthaltene Module

| Modul          | Zweck                                  | Reaktivieren wenn                          |
| -------------- | -------------------------------------- | ------------------------------------------ |
| `billing/`     | Stripe Checkout, Webhooks, Plan-Gating | Pricing-Modell eingeführt wird (Phase 3)   |
| `teams/`       | Organisation/Team-Verwaltung           | Team-Features benötigt (Phase 3)           |
| `rbac/`        | Rollenbasierte Zugriffskontrolle       | Multi-User-Teams mit Rollen (Phase 3)      |
| `marketplace/` | Plugin-SDK, Registry, Sandbox          | Plugin-Ökosystem gestartet wird (Phase 4+) |
| `developer/`   | API-Key-Management-UI                  | Developer-Plattform live (Phase 3)         |
| `sso/`         | OIDC/SAML SSO-Integration              | Enterprise-SSO benötigt (Phase 3+)         |

## Ausgelagerte Routes

Unter `routes/` liegen die zugehörigen API-Route-Dateien:

- `billing.py`, `rbac.py`, `marketplace.py`, `developer.py`, `organizations.py`, `sso.py`

## Ausgelagerte Tests

Unter `tests/` liegen die zugehörigen Test-Suites:

- `test_billing/`, `test_teams/`, `test_rbac/`, `test_marketplace/`, `test_developer/`, `test_sso/`
- `test_gmail.py`, `test_slack.py`, `test_outlook.py`, `test_google_docs.py` (Connector-Tests)

## Ausgelagerte Konnektoren (Schritt 2)

Unter `connectors/` liegen Phase-3-Konnektoren:

| Konnektor        | Datei             | Reaktivieren wenn                     |
| ---------------- | ----------------- | ------------------------------------- |
| Gmail            | `gmail.py`        | E-Mail-Integration benötigt (Phase 3) |
| Slack            | `slack.py`        | Slack-Integration benötigt (Phase 3)  |
| Outlook          | `outlook.py`      | Outlook-Integration benötigt (Phase 3)|
| Google Docs      | `google_docs.py`  | Docs-Integration benötigt (Phase 3)   |

Unter `integrations/slack/` liegt die Slack-Bot-Integration (`bot.py`, `__init__.py`).

### Konnektoren reaktivieren

1. Konnektor-Datei zurück nach `pwbs/connectors/` verschieben
2. Tests zurück nach `tests/test_connectors/` verschieben
3. In `pwbs/api/v1/routes/connectors.py` die auskommentierten Einträge in `_CONNECTOR_META`, `_AUTH_URLS`, `_SCOPES` und Token-Maps aktivieren
4. Falls Slack: `integrations/slack/` zurück nach `pwbs/integrations/slack/` + Webhooks-Router in `main.py` aktivieren
5. Falls Gmail: Webhooks-Router in `main.py` aktivieren (Gmail Pub/Sub)

## Reaktivierung

1. Modul zurück nach `pwbs/` verschieben
2. Route-Datei zurück nach `pwbs/api/v1/routes/` verschieben
3. Tests zurück nach `tests/` verschieben
4. In `pwbs/api/main.py` die auskommentierten Import- und `include_router`-Zeilen aktivieren
5. `api_key_auth.py` ggf. zurück auf `pwbs.developer.api_key_service` umstellen
