"use client";

import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";

/**
 * Client-Wrapper, der den Onboarding-Wizard im Dashboard rendert (TASK-181).
 * Der Wizard zeigt sich nur bei Nutzern, die das Onboarding noch nicht abgeschlossen haben.
 */
export function OnboardingGate() {
  return <OnboardingWizard />;
}
