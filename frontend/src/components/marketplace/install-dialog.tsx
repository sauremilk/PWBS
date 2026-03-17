"use client";

import { useState } from "react";
import { Shield, X, AlertTriangle, Loader2 } from "lucide-react";
import type { PluginDetail } from "@/types/marketplace";

interface InstallDialogProps {
  plugin: PluginDetail;
  onConfirm: () => void;
  onCancel: () => void;
  isInstalling: boolean;
}

export function InstallDialog({
  plugin,
  onConfirm,
  onCancel,
  isInstalling,
}: InstallDialogProps) {
  const [accepted, setAccepted] = useState(false);
  const hasPermissions = plugin.permissions.length > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="install-dialog-title"
    >
      <div className="mx-4 w-full max-w-md rounded-lg bg-surface shadow-xl">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2
            id="install-dialog-title"
            className="text-lg font-semibold text-text"
          >
            Plugin installieren
          </h2>
          <button
            onClick={onCancel}
            className="rounded-lg p-1 text-text-tertiary hover:bg-surface-secondary hover:text-text-secondary"
            aria-label="Schliessen"
          >
            <X aria-hidden="true" className="h-5 w-5" />
          </button>
        </div>

        <div className="px-6 py-4">
          <p className="mb-3 text-sm text-text-secondary">
            <strong>{plugin.name}</strong> (v{plugin.version}) wird installiert.
          </p>

          {hasPermissions && (
            <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium text-yellow-800">
                <Shield aria-hidden="true" className="h-4 w-4" />
                Angeforderte Berechtigungen
              </div>
              <ul className="space-y-1">
                {plugin.permissions.map((perm) => (
                  <li
                    key={perm}
                    className="flex items-center gap-2 text-sm text-yellow-700"
                  >
                    <AlertTriangle
                      aria-hidden="true"
                      className="h-3.5 w-3.5 shrink-0"
                    />
                    {perm}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {hasPermissions && (
            <label className="flex items-center gap-2 text-sm text-text-secondary">
              <input
                type="checkbox"
                checked={accepted}
                onChange={(e) => setAccepted(e.target.checked)}
                className="rounded border-border"
              />
              Ich akzeptiere die angeforderten Berechtigungen
            </label>
          )}
        </div>

        <div className="flex justify-end gap-3 border-t border-border px-6 py-4">
          <button
            onClick={onCancel}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-text-secondary hover:bg-surface-secondary"
          >
            Abbrechen
          </button>
          <button
            onClick={onConfirm}
            disabled={isInstalling || (hasPermissions && !accepted)}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {isInstalling && (
              <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
            )}
            Installieren
          </button>
        </div>
      </div>
    </div>
  );
}
