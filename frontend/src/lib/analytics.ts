/**
 * Plausible Analytics  DSGVO-konformes Event-Tracking ohne Cookies (TASK-179).
 *
 * Plausible setzt keine Cookies und speichert keine personenbezogenen Daten.
 * Custom Events werden nur gesendet, wenn das Plausible-Script geladen ist
 * (d.h. NEXT_PUBLIC_PLAUSIBLE_DOMAIN gesetzt und Script nicht geblockt).
 */

/** Custom-Event-Namen, die an Plausible gesendet werden. */
export type PlausibleEvent =
  | "signup"
  | "first_connector"
  | "first_briefing"
  | "search"
  | "referral";

/** Props-Map pro Event (alle optional, keine PII). */
interface EventPropsMap {
  signup: Record<string, never>;
  first_connector: { connector_type: string };
  first_briefing: { briefing_type: string };
  search: { mode: string };
  referral: Record<string, never>;
}

/** Globale Plausible-Funktion, injiziert durch das Script-Tag. */
declare global {
  interface Window {
    plausible?: (
      event: string,
      options?: { props?: Record<string, string> },
    ) => void;
  }
}

/**
 * Sende ein Custom Event an Plausible Analytics.
 * No-op wenn Plausible nicht geladen ist (z.B. lokal ohne Domain-Konfiguration).
 */
export function trackEvent<E extends PlausibleEvent>(
  event: E,
  ...args: EventPropsMap[E] extends Record<string, never>
    ? []
    : [props: EventPropsMap[E]]
): void {
  if (typeof window === "undefined" || !window.plausible) return;
  const props = args[0] as Record<string, string> | undefined;
  window.plausible(event, props ? { props } : undefined);
}

/** Shorthand-Funktionen fuer die definierten Events. */
export function trackSignup(): void {
  trackEvent("signup");
}

export function trackFirstConnector(connectorType: string): void {
  trackEvent("first_connector", { connector_type: connectorType });
}

export function trackFirstBriefing(briefingType: string): void {
  trackEvent("first_briefing", { briefing_type: briefingType });
}

export function trackSearch(mode: string): void {
  trackEvent("search", { mode });
}

export function trackReferral(): void {
  trackEvent("referral");
}
