"use client";

import { Shield, CheckCircle2, MapPin, Brain, Loader2 } from "lucide-react";
import { useSecurityStatus } from "@/hooks/use-security";

export function SecurityStatusPanel() {
  const { data, isLoading } = useSecurityStatus();

  if (isLoading) {
    return (
      <div role="status" className="flex items-center justify-center py-8">
        <Loader2
          aria-hidden="true"
          className="h-6 w-6 animate-spin text-text-tertiary"
        />
        <span className="sr-only">Wird geladen</span>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Shield aria-hidden="true" className="h-5 w-5 text-green-600" />
        <h3 className="text-sm font-semibold text-text">
          Verschl\u00fcsselungsstatus
        </h3>
      </div>

      <div className="space-y-3">
        {data.storage_layers.map((layer) => (
          <div
            key={layer.layer}
            className="flex items-center justify-between rounded-lg border border-border bg-surface p-3"
          >
            <div className="flex items-center gap-2">
              <CheckCircle2
                aria-hidden="true"
                className={`h-4 w-4 ${layer.encrypted ? "text-green-500" : "text-red-500"}`}
              />
              <span className="text-sm font-medium text-text">
                {layer.layer}
              </span>
            </div>
            <div className="text-right">
              <span className="text-sm text-text-secondary">
                {layer.encrypted
                  ? (layer.encryption_type ?? "Verschl\u00fcsselt")
                  : "Nicht verschl\u00fcsselt"}
              </span>
              {layer.note && (
                <p className="text-xs text-text-tertiary">{layer.note}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-2 pt-2">
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <MapPin aria-hidden="true" className="h-4 w-4 text-indigo-500" />
          <span>Datenstandort: {data.data_location}</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <Brain aria-hidden="true" className="h-4 w-4 text-purple-500" />
          <span>{data.llm_usage}</span>
        </div>
      </div>
    </div>
  );
}
