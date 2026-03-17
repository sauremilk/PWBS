"use client";

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "pwbs_onboarding_completed";
const STEP_KEY = "pwbs_onboarding_step";

/**
 * Hook zum Verwalten des Onboarding-Status (TASK-181).
 * Persistiert in localStorage, da das User-Model serverseitig
 * noch kein onboarding_completed-Feld hat.
 */
export function useOnboarding() {
  const [completed, setCompleted] = useState<boolean | null>(null);
  const [lastStep, setLastStep] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    setCompleted(stored === "true");
    setLastStep(localStorage.getItem(STEP_KEY));
  }, []);

  const complete = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, "true");
    localStorage.removeItem(STEP_KEY);
    setCompleted(true);
  }, []);

  const saveStep = useCallback((step: string) => {
    localStorage.setItem(STEP_KEY, step);
    setLastStep(step);
  }, []);

  const reset = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STEP_KEY);
    setCompleted(false);
    setLastStep(null);
  }, []);

  return {
    /** null = wird noch geladen, true = abgeschlossen, false = noch offen */
    completed,
    /** Letzter gespeicherter Wizard-Schritt (zur Wiederaufnahme) */
    lastStep,
    /** Markiert das Onboarding als abgeschlossen */
    complete,
    /** Speichert den aktuellen Wizard-Schritt persistent */
    saveStep,
    /** Setzt den Onboarding-Status zurueck (z.B. fuer Tests) */
    reset,
  };
}
