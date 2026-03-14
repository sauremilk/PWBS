"use client";

import { Shield, CheckCircle2, MapPin, Brain, Loader2 } from "lucide-react";
import { useSecurityStatus } from "@/hooks/use-security";

export function SecurityStatusPanel() {
  const { data, isLoading } = useSecurityStatus();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Shield className="h-5 w-5 text-green-600" />
        <h3 className="text-sm font-semibold text-gray-900">Verschl\u00fcsselungsstatus</h3>
      </div>

      <div className="space-y-3">
        {data.storage_layers.map((layer) => (
          <div
            key={layer.layer}
            className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3"
          >
            <div className="flex items-center gap-2">
              <CheckCircle2
                className={`h-4 w-4 ${layer.encrypted ? "text-green-500" : "text-red-500"}`}
              />
              <span className="text-sm font-medium text-gray-900">{layer.layer}</span>
            </div>
            <div className="text-right">
              <span className="text-sm text-gray-600">
                {layer.encrypted
                  ? layer.encryption_type ?? "Verschl\u00fcsselt"
                  : "Nicht verschl\u00fcsselt"}
              </span>
              {layer.note && (
                <p className="text-xs text-gray-500">{layer.note}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-2 pt-2">
        <div className="flex items-center gap-2 text-sm text-gray-700">
          <MapPin className="h-4 w-4 text-blue-500" />
          <span>Datenstandort: {data.data_location}</span>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-700">
          <Brain className="h-4 w-4 text-purple-500" />
          <span>{data.llm_usage}</span>
        </div>
      </div>
    </div>
  );
}
