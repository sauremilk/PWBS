"use client";

import { useState } from "react";
import { Loader2, Database, Cpu, FileText, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { useDataReport, useLlmUsage } from "@/hooks/use-settings";
import type { LlmUsageEntry } from "@/types/api";

function formatDate(iso: string | null): string {
  if (!iso) return "\u2013";
  return new Date(iso).toLocaleDateString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function SourceCard({ source }: { source: { source_type: string; document_count: number; oldest_document: string | null; newest_document: string | null } }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-blue-500" />
          <span className="font-medium text-gray-900 dark:text-gray-100">{source.source_type}</span>
        </div>
        <span className="text-lg font-bold text-gray-900 dark:text-gray-100">{source.document_count}</span>
      </div>
      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        <div>{"&#196;ltestes: "}{formatDate(source.oldest_document)}</div>
        <div>Neuestes: {formatDate(source.newest_document)}</div>
      </div>
    </div>
  );
}

function LlmUsageTable({ entries }: { entries: LlmUsageEntry[] }) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Keine LLM-Aufrufe protokolliert.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            <th className="py-2 text-left font-medium text-gray-600 dark:text-gray-300">Zeitpunkt</th>
            <th className="py-2 text-left font-medium text-gray-600 dark:text-gray-300">Provider</th>
            <th className="py-2 text-left font-medium text-gray-600 dark:text-gray-300">Modell</th>
            <th className="py-2 text-right font-medium text-gray-600 dark:text-gray-300">Input</th>
            <th className="py-2 text-right font-medium text-gray-600 dark:text-gray-300">Output</th>
            <th className="py-2 text-left font-medium text-gray-600 dark:text-gray-300">Zweck</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.id} className="border-b border-gray-100 dark:border-gray-800">
              <td className="py-2 text-gray-700 dark:text-gray-300">{formatDate(e.created_at)}</td>
              <td className="py-2 text-gray-700 dark:text-gray-300">{e.provider}</td>
              <td className="py-2 text-gray-700 dark:text-gray-300">{e.model}</td>
              <td className="py-2 text-right text-gray-700 dark:text-gray-300">{formatTokens(e.input_tokens)}</td>
              <td className="py-2 text-right text-gray-700 dark:text-gray-300">{formatTokens(e.output_tokens)}</td>
              <td className="py-2 text-gray-500 dark:text-gray-400">{e.purpose}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function DataTransparencyPage() {
  const { data: report, isLoading: reportLoading, error: reportError } = useDataReport();
  const { data: llmUsage, isLoading: llmLoading } = useLlmUsage({ limit: 50 });
  const [llmExpanded, setLlmExpanded] = useState(false);

  if (reportLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (reportError) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-red-500">Fehler beim Laden des Transparenzberichts.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Datentransparenz
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {"&#220;bersicht &#252;ber Ihre gespeicherten Daten und KI-Nutzung (DSGVO Art. 15)."}
        </p>
      </div>

      {/* Document overview */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Database className="h-5 w-5 text-blue-600" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Dokumente ({report?.total_documents ?? 0} gesamt)
          </h2>
        </div>
        {report && report.sources.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {report.sources.map((s) => (
              <SourceCard key={s.source_type} source={s} />
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Keine Dokumente vorhanden.</p>
        )}
      </section>

      {/* Connections */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <RefreshCw className="h-5 w-5 text-green-600" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Verbindungen
          </h2>
        </div>
        {report && report.connections.length > 0 ? (
          <div className="space-y-2">
            {report.connections.map((c) => (
              <div
                key={c.source_type}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
              >
                <span className="font-medium text-gray-900 dark:text-gray-100">{c.source_type}</span>
                <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
                  <span className={c.status === "active" ? "text-green-600" : "text-yellow-600"}>
                    {c.status}
                  </span>
                  <span>Letzter Sync: {formatDate(c.last_sync)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Keine Verbindungen konfiguriert.</p>
        )}
      </section>

      {/* LLM Provider Summary */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Cpu className="h-5 w-5 text-purple-600" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            KI-Nutzung (Zusammenfassung)
          </h2>
        </div>
        {report && report.llm_provider_usage.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {report.llm_provider_usage.map((u) => (
              <div
                key={`${u.provider}-${u.model}`}
                className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="font-medium text-gray-900 dark:text-gray-100">
                  {u.provider} / {u.model}
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-sm text-gray-500 dark:text-gray-400">
                  <div>
                    <span className="block text-xs">Aufrufe</span>
                    <span className="font-semibold text-gray-900 dark:text-gray-100">{u.call_count}</span>
                  </div>
                  <div>
                    <span className="block text-xs">Input-Tokens</span>
                    <span className="font-semibold text-gray-900 dark:text-gray-100">{formatTokens(u.total_input_tokens)}</span>
                  </div>
                  <div>
                    <span className="block text-xs">Output-Tokens</span>
                    <span className="font-semibold text-gray-900 dark:text-gray-100">{formatTokens(u.total_output_tokens)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">Keine KI-Aufrufe protokolliert.</p>
        )}
      </section>

      {/* LLM Audit Log (expandable) */}
      <section>
        <button
          onClick={() => setLlmExpanded(!llmExpanded)}
          className="flex w-full items-center justify-between rounded-lg border border-gray-200 bg-white p-4 text-left dark:border-gray-700 dark:bg-gray-800"
        >
          <div className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-purple-600" />
            <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              LLM-Audit-Log ({llmUsage?.total ?? 0} Eintr&#228;ge)
            </span>
          </div>
          {llmExpanded ? (
            <ChevronUp className="h-5 w-5 text-gray-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-gray-400" />
          )}
        </button>
        {llmExpanded && (
          <div className="mt-2 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
            {llmLoading ? (
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            ) : (
              <LlmUsageTable entries={llmUsage?.entries ?? []} />
            )}
          </div>
        )}
      </section>
    </div>
  );
}
