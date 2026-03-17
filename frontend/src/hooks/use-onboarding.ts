"use client";

import { useState, useCallback, useEffect } from "react";
import { getOnboardingState, updateOnboardingState } from "@/lib/api/user";

const STORAGE_KEY = "pwbs_onboarding_completed";
const STEP_KEY = "pwbs_onboarding_step";

/**
 * Hook zum Verwalten des Onboarding-Status (TASK-181 / LAUNCH-UX-005).
 * Primär über Backend-API persistiert, localStorage als Offline-Fallback.
 */
export function useOnboarding() {
  const [completed, setCompleted] = useState<boolean | null>(null);
  const [lastStep, setLastStep] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const state = await getOnboardingState();
        if (cancelled) return;
        setCompleted(state.completed);
        setLastStep(state.step);
        // Sync localStorage for offline fallback
        localStorage.setItem(STORAGE_KEY, String(state.completed));
        if (state.step) {
          localStorage.setItem(STEP_KEY, state.step);
        } else {
          localStorage.removeItem(STEP_KEY);
        }
      } catch {
        // Fallback to localStorage when API unavailable (e.g. not logged in)
        if (cancelled) return;
        const stored = localStorage.getItem(STORAGE_KEY);
        setCompleted(stored === "true");
        setLastStep(localStorage.getItem(STEP_KEY));
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  const complete = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, "true");
    localStorage.removeItem(STEP_KEY);
    setCompleted(true);
    setLastStep(null);
    updateOnboardingState({ completed: true }).catch(() => {});
  }, []);

  const saveStep = useCallback((step: string) => {
    localStorage.setItem(STEP_KEY, step);
    setLastStep(step);
    updateOnboardingState({ step }).catch(() => {});
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
