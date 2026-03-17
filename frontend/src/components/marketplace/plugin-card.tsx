"use client";

import Link from "next/link";
import { Puzzle, CheckCircle2, Download } from "lucide-react";
import { AverageRating } from "@/components/marketplace/rating-stars";
import type { PluginSummary } from "@/types/marketplace";

const TYPE_LABELS: Record<string, string> = {
  connector: "Konnektor",
  briefing_template: "Briefing-Template",
  processing: "Processing",
  agent: "Agent",
};

export function PluginCard({ plugin }: { plugin: PluginSummary }) {
  return (
    <Link
      href={`/marketplace/${plugin.id}`}
      className="group rounded-lg border border-border bg-surface p-4 transition-shadow hover:shadow-md"
    >
      <div className="mb-3 flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-surface-secondary text-text-tertiary">
          {plugin.icon_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={plugin.icon_url} alt="" className="h-8 w-8 rounded" />
          ) : (
            <Puzzle aria-hidden="true" className="h-5 w-5" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <h3 className="truncate text-sm font-semibold text-text group-hover:text-indigo-700">
              {plugin.name}
            </h3>
            {plugin.is_verified && (
              <CheckCircle2
                aria-label="Verifiziert"
                className="h-4 w-4 shrink-0 text-indigo-500"
              />
            )}
          </div>
          <span className="text-xs text-text-tertiary">
            {TYPE_LABELS[plugin.plugin_type] ?? plugin.plugin_type} · v
            {plugin.version}
          </span>
        </div>
      </div>

      <p className="mb-3 line-clamp-2 text-sm text-text-secondary">
        {plugin.description || "Keine Beschreibung."}
      </p>

      <div className="flex items-center justify-between">
        <AverageRating ratingSum={0} ratingCount={0} />
        <span className="inline-flex items-center gap-1 text-xs text-text-tertiary">
          <Download aria-hidden="true" className="h-3.5 w-3.5" />
          {plugin.install_count}
        </span>
      </div>
    </Link>
  );
}
