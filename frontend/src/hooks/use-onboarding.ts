"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "pwbs_onboarding_completed";

/**
 * Hook zum Verwalten des Onboarding-Status (TASK-181).
 * Persistiert in localStorage, da das User-Model serverseitig
 * noch kein onboarding_completed-Feld hat.
 */
export function useOnboarding() {
  const [completed, setCompleted] = useState<boolean | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    setCompleted(stored === "true");
  }, []);

  const complete = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, "true");
    setCompleted(true);
  }, []);

  const reset = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setCompleted(false);
  }, []);

  return {
    /** null = wird noch geladen, true = abgeschlossen, false = noch offen */
    completed,
    /** Markiert das Onboarding als abgeschlossen */
    complete,
    /** Setzt den Onboarding-Status zurueck (z.B. fuer Tests) */
    reset,
  };
}
