"use client";

import Link from "next/link";
import { FileText, Calendar, ChevronRight, Loader2, Plus } from "lucide-react";
import { useBriefingList, useGenerateBriefing } from "@/hooks/use-briefings";
import { trackFirstBriefing } from "@/lib/analytics";
import BriefingPreferencesPanel from "@/components/briefings/briefing-preferences";
import type { BriefingType, BriefingListItem } from "@/types/api";

const BRIEFING_TYPE_LABELS: Record<BriefingType, string> = {
  morning: "Morgen-Briefing",
  meeting: "Meeting-Briefing",
  project: "Projekt-Briefing",
  weekly: "Wochen-Briefing",
};

function BriefingRow({ item }: { item: BriefingListItem }) {
  return (
    <Link
      href={`/briefings/${item.id}`}
      className="group flex items-center gap-4 rounded-xl border border-border bg-surface p-4 transition-all hover:border-indigo-200 hover:shadow-md hover:shadow-indigo-500/5"
    >
      <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-indigo-100">
        <FileText aria-hidden="true" className="h-5 w-5 text-indigo-600" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-text group-hover:text-indigo-600">
          {item.title}
        </p>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-text-tertiary">
          <span className="rounded-md bg-indigo-50 px-1.5 py-0.5 font-medium text-indigo-600">
            {BRIEFING_TYPE_LABELS[item.briefing_type]}
          </span>
          <Calendar aria-hidden="true" className="h-3 w-3" />
          <span>{new Date(item.generated_at).toLocaleDateString("de-DE")}</span>
        </div>
      </div>
      <ChevronRight
        aria-hidden="true"
        className="h-5 w-5 flex-shrink-0 text-text-tertiary transition-transform group-hover:translate-x-0.5 group-hover:text-indigo-600"
      />
    </Link>
  );
}

export default function BriefingsPage() {
  const { data, isLoading } = useBriefingList({ limit: 50 });
  const generate = useGenerateBriefing();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Briefings</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Deine KI-generierten Wissens-Briefings
          </p>
        </div>
        <button
          onClick={() => {
            trackFirstBriefing("morning");
            generate.mutate({ type: "morning" });
          }}
          disabled={generate.isPending}
          className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-indigo-600/25 hover:bg-indigo-500 disabled:opacity-50"
        >
          <Plus aria-hidden="true" className="h-4 w-4" />
          Neues Briefing
        </button>
      </div>

      <BriefingPreferencesPanel />

      {isLoading ? (
        <div className="flex items-center justify-center py-12" role="status">
          <Loader2
            aria-hidden="true"
            className="h-8 w-8 animate-spin text-text-tertiary"
          />
          <span className="sr-only">Wird geladen</span>
        </div>
      ) : data && data.briefings.length > 0 ? (
        <div className="space-y-2">
          {data.briefings.map((item) => (
            <BriefingRow key={item.id} item={item} />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-surface p-12 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-100">
            <FileText aria-hidden="true" className="h-6 w-6 text-indigo-600" />
          </div>
          <h3 className="mb-1 text-sm font-semibold text-text">
            Noch keine Briefings
          </h3>
          <p className="text-sm text-text-secondary">
            Erstelle dein erstes Briefing, um loszulegen.
          </p>
        </div>
      )}
    </div>
  );
}
