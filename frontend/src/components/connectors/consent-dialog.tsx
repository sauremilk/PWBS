"use client";

import { useState } from "react";
import { ShieldCheck, AlertTriangle, X, Loader2 } from "lucide-react";
import { useConsentStatus, useGrantConsent } from "@/hooks/use-connectors";

interface ConsentDialogProps {
  connectorType: string;
  connectorName: string;
  onConsented: () => void;
  onCancel: () => void;
}

export function ConsentDialog({
  connectorType,
  connectorName,
  onConsented,
  onCancel,
}: ConsentDialogProps) {
  const { data: consent, isLoading } = useConsentStatus(connectorType);
  const grantMutation = useGrantConsent();
  const [accepted, setAccepted] = useState(false);

  async function handleGrant() {
    await grantMutation.mutateAsync({
      connectorType,
      consentVersion: 1,
    });
    onConsented();
  }

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div role="status" className="rounded-lg bg-white p-8">
          <Loader2
            aria-hidden="true"
            className="h-8 w-8 animate-spin text-gray-400"
          />
          <span className="sr-only">Wird geladen</span>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="consent-dialog-title"
        className="mx-4 max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4">
          <div className="flex items-center gap-2">
            <ShieldCheck aria-hidden="true" className="h-5 w-5 text-blue-600" />
            <h2
              id="consent-dialog-title"
              className="text-lg font-semibold text-gray-900"
            >
              Datenverarbeitung: {connectorName}
            </h2>
          </div>
          <button
            onClick={onCancel}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
            aria-label="Schließen"
          >
            <X aria-hidden="true" className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-5 px-6 py-5">
          {/* Data types */}
          <div>
            <h3 className="mb-2 text-sm font-semibold text-gray-800">
              Welche Daten werden importiert?
            </h3>
            <ul className="space-y-1">
              {consent?.data_types.map((dt) => (
                <li
                  key={dt}
                  className="flex items-center gap-2 text-sm text-gray-600"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
                  {dt}
                </li>
              ))}
            </ul>
          </div>

          {/* Processing purpose */}
          <div>
            <h3 className="mb-1 text-sm font-semibold text-gray-800">
              Verarbeitungszweck
            </h3>
            <p className="text-sm text-gray-600">
              {consent?.processing_purpose}
            </p>
          </div>

          {/* LLM providers */}
          <div>
            <h3 className="mb-2 text-sm font-semibold text-gray-800">
              KI-Provider für die Verarbeitung
            </h3>
            <ul className="space-y-1">
              {consent?.llm_providers.map((lp) => (
                <li
                  key={lp}
                  className="flex items-center gap-2 text-sm text-gray-600"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                  {lp}
                </li>
              ))}
            </ul>
          </div>

          {/* Info box */}
          <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
            <div className="flex gap-2">
              <AlertTriangle
                aria-hidden="true"
                className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600"
              />
              <p className="text-xs text-amber-800">
                Du kannst deine Einwilligung jederzeit unter Konnektoren
                widerrufen. Beim Widerruf werden alle importierten Daten dieser
                Quelle unwiderruflich gelöscht.
              </p>
            </div>
          </div>

          {/* Checkbox */}
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={accepted}
              onChange={(e) => setAccepted(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700">
              Ich stimme der Verarbeitung meiner Daten zu den oben genannten
              Zwecken zu. Ich bin mir bewusst, dass meine Daten an die
              aufgeführten KI-Provider übermittelt werden.
            </span>
          </label>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t px-6 py-4">
          <button
            onClick={onCancel}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Abbrechen
          </button>
          <button
            onClick={handleGrant}
            disabled={!accepted || grantMutation.isPending}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {grantMutation.isPending && (
              <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
            )}
            Einwilligung erteilen & Verbinden
          </button>
        </div>
      </div>
    </div>
  );
}
