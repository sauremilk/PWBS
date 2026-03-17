/**
 * Fehlercode-Mapping: Backend-Codes  nutzerfreundliche deutsche Texte mit Recovery-Aktion.
 * Quelle: UX_ONBOARDING_SPEC §7
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ErrorMapping {
  title: string;
  message: string;
  recovery?: string;
  action?: ErrorAction;
}

export type ErrorAction =
  | { type: "retry"; label?: string }
  | { type: "link"; href: string; label: string }
  | { type: "redirect"; href: string; label: string };

// ---------------------------------------------------------------------------
// Error Code  German Message Map
// ---------------------------------------------------------------------------

const ERROR_MAP: Record<string, ErrorMapping> = {
  // --- OAuth Errors ---
  ACCESS_DENIED: {
    title: "Zugriff nicht erteilt",
    message:
      "Du hast die Verbindung abgelehnt. Ohne Zugriff auf deine Daten kann PWBS kein Briefing erstellen.",
    recovery: "Du kannst es jederzeit erneut versuchen.",
    action: { type: "retry", label: "Erneut verbinden" },
  },
  TOKEN_EXCHANGE_FAILED: {
    title: "Verbindung fehlgeschlagen",
    message:
      "Die Verbindung konnte nicht hergestellt werden. Das liegt möglicherweise an einer kurzzeitigen Störung.",
    recovery: "Bitte versuche es in einer Minute erneut.",
    action: { type: "retry", label: "Erneut versuchen" },
  },
  TOKEN_EXCHANGE_NETWORK_ERROR: {
    title: "Verbindung fehlgeschlagen",
    message:
      "Die Verbindung konnte nicht hergestellt werden. Das liegt möglicherweise an einer kurzzeitigen Störung.",
    recovery: "Bitte versuche es in einer Minute erneut.",
    action: { type: "retry", label: "Erneut versuchen" },
  },
  GOOGLE_TOKEN_EXCHANGE_FAILED: {
    title: "Google-Verbindung fehlgeschlagen",
    message:
      "Die Verbindung zu Google konnte nicht hergestellt werden. Bitte versuche es erneut.",
    action: { type: "retry", label: "Erneut versuchen" },
  },
  POPUP_BLOCKED: {
    title: "Pop-up blockiert",
    message:
      "Dein Browser hat das Anmeldefenster blockiert. Bitte erlaube Pop-ups für diese Seite und versuche es erneut.",
    recovery:
      "So erlaubst du Pop-ups: Browser-Einstellungen  Pop-ups erlauben",
    action: { type: "retry", label: "Erneut versuchen" },
  },
  GOOGLE_OAUTH_NOT_CONFIGURED: {
    title: "Google-Anmeldung nicht verfügbar",
    message:
      "Die Google-Anmeldung ist derzeit nicht konfiguriert. Bitte nutze E-Mail und Passwort.",
  },
  INVALID_STATE: {
    title: "Sitzung abgelaufen",
    message:
      "Die Verbindungsanfrage ist abgelaufen. Bitte starte den Vorgang erneut.",
    action: { type: "retry", label: "Erneut versuchen" },
  },
  NO_OAUTH_SUPPORT: {
    title: "OAuth nicht unterstützt",
    message:
      "Dieser Konnektor unterstützt keine automatische Verbindung. Bitte nutze die manuelle Konfiguration.",
  },

  // --- Connector / Sync Errors ---
  CONNECTION_NOT_FOUND: {
    title: "Verbindung nicht gefunden",
    message:
      "Die angeforderte Datenquelle wurde nicht gefunden. Möglicherweise wurde sie bereits entfernt.",
    action: {
      type: "link",
      href: "/connectors",
      label: "Zu den Datenquellen",
    },
  },
  CONNECTION_NOT_ACTIVE: {
    title: "Verbindung inaktiv",
    message:
      "Diese Datenquelle ist derzeit nicht aktiv. Bitte stelle die Verbindung wieder her.",
    action: { type: "retry", label: "Erneut verbinden" },
  },
  CONNECTION_EXISTS: {
    title: "Bereits verbunden",
    message: "Diese Datenquelle ist bereits mit deinem Konto verbunden.",
  },
  SYNC_RATE_LIMITED: {
    title: "Synchronisierung zu häufig",
    message:
      "Bitte warte einen Moment, bevor du erneut synchronisierst. Der automatische Sync läuft weiterhin im Hintergrund.",
  },
  NO_MARKDOWN_FILES: {
    title: "Kein Obsidian-Vault gefunden",
    message:
      "Der angegebene Pfad enthält keinen gültigen Obsidian-Vault. Bitte prüfe, ob der Pfad korrekt ist und Markdown-Dateien enthält.",
    recovery:
      'Ein Obsidian-Vault enthält einen ".obsidian"-Ordner und ".md"-Dateien.',
    action: { type: "retry", label: "Pfad korrigieren" },
  },
  UNKNOWN_CONNECTOR_TYPE: {
    title: "Unbekannte Datenquelle",
    message:
      "Dieser Datenquellen-Typ wird nicht unterstützt. Bitte wähle eine andere Quelle.",
    action: {
      type: "link",
      href: "/connectors",
      label: "Verfügbare Quellen anzeigen",
    },
  },

  // --- Briefing Errors ---
  BRIEFING_NOT_FOUND: {
    title: "Briefing nicht gefunden",
    message:
      "Das angeforderte Briefing konnte nicht gefunden werden. Möglicherweise wurde es bereits gelöscht.",
  },
  LLM_TIMEOUT: {
    title: "Erstellung dauert etwas länger",
    message:
      "Dein Briefing wird gerade erzeugt, aber der KI-Dienst braucht etwas mehr Zeit.",
    recovery: "Du kannst warten oder es später erneut versuchen.",
    action: { type: "retry", label: "Erneut versuchen" },
  },
  LLM_ERROR: {
    title: "Briefing konnte nicht erstellt werden",
    message:
      "Der KI-Dienst ist vorübergehend nicht verfügbar. Dein Briefing wird automatisch erstellt, sobald der Dienst wieder erreichbar ist.",
    action: { type: "retry", label: "Erneut versuchen" },
  },
  DEPENDENCY_MISSING: {
    title: "Dienst nicht verfügbar",
    message:
      "Ein benötigter Dienst ist vorübergehend nicht erreichbar. Bitte versuche es in Kürze erneut.",
    action: { type: "retry", label: "Erneut versuchen" },
  },

  // --- Auth Errors ---
  INVALID_CREDENTIALS: {
    title: "Anmeldung fehlgeschlagen",
    message: "E-Mail oder Passwort falsch. Bitte versuche es erneut.",
    action: { type: "retry", label: "Erneut versuchen" },
  },
  INVALID_PASSWORD: {
    title: "Ungültiges Passwort",
    message:
      "Das Passwort erfüllt nicht die Anforderungen. Mindestens 8 Zeichen mit Groß-/Kleinbuchstaben und Zahl.",
  },
  SESSION_EXPIRED: {
    title: "Sitzung abgelaufen",
    message:
      "Deine Sitzung ist abgelaufen. Bitte melde dich erneut an, um fortzufahren. Deine Daten und Einstellungen sind sicher gespeichert.",
    action: { type: "redirect", href: "/login?expired=1", label: "Zur Anmeldung" },
  },
  ADMIN_REQUIRED: {
    title: "Keine Berechtigung",
    message:
      "Du benötigst Administratorrechte, um diese Aktion auszuführen.",
  },
  FORBIDDEN: {
    title: "Zugriff verweigert",
    message: "Du hast keine Berechtigung für diese Aktion.",
  },

  // --- Rate Limiting ---
  RATE_LIMIT_EXCEEDED: {
    title: "Zu viele Anfragen",
    message:
      "Um die Qualität für alle Nutzer sicherzustellen, gibt es ein kurzes Limit. Bitte warte einen Moment und versuche es dann erneut.",
  },
  RATE_LIMITED: {
    title: "Zu viele Anfragen",
    message:
      "Bitte warte einen Moment und versuche es dann erneut.",
  },

  // --- Validation Errors ---
  VALIDATION_ERROR: {
    title: "Ungültige Eingabe",
    message: "Bitte überprüfe deine Eingaben und versuche es erneut.",
  },

  // --- System / Generic Errors ---
  INTERNAL_ERROR: {
    title: "Interner Fehler",
    message:
      "Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es erneut. Falls das Problem bestehen bleibt, kontaktiere den Support.",
    action: { type: "retry", label: "Erneut versuchen" },
  },
  NETWORK_ERROR: {
    title: "Keine Internetverbindung",
    message:
      "Bitte prüfe deine Netzwerkverbindung. PWBS benötigt eine aktive Internetverbindung, um deine Daten zu synchronisieren und Briefings zu erstellen.",
  },
};

// ---------------------------------------------------------------------------
// Lookup
// ---------------------------------------------------------------------------

const FALLBACK: ErrorMapping = {
  title: "Fehler aufgetreten",
  message: "Etwas ist schiefgelaufen. Bitte versuche es erneut.",
  action: { type: "retry" },
};

/**
 * Resolve an error code (from backend {code} field) to a user-facing German
 * error message with optional recovery hint and action.
 */
export function resolveError(code: string | undefined | null): ErrorMapping {
  if (!code) return FALLBACK;
  return ERROR_MAP[code] ?? FALLBACK;
}

/**
 * Resolve from an ApiClientError-style object.
 * Checks data.code first, then falls back to HTTP-status heuristics.
 */
export function resolveApiError(err: {
  status?: number;
  data?: { code?: string; message?: string };
  message?: string;
}): ErrorMapping {
  // Backend error code available
  if (err.data?.code && ERROR_MAP[err.data.code]) {
    return ERROR_MAP[err.data.code];
  }

  // HTTP status heuristics
  if (err.status === 401) {
    return ERROR_MAP.SESSION_EXPIRED;
  }
  if (err.status === 403) {
    return ERROR_MAP.FORBIDDEN;
  }
  if (err.status === 429) {
    return ERROR_MAP.RATE_LIMIT_EXCEEDED;
  }
  if (err.status === 503) {
    return ERROR_MAP.DEPENDENCY_MISSING;
  }

  // Network error (no status = fetch failed)
  if (!err.status && err.message?.includes("fetch")) {
    return ERROR_MAP.NETWORK_ERROR;
  }

  return FALLBACK;
}
