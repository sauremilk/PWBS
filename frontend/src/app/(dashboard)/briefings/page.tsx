"use client";

import Link from "next/link";
import { FileText, Calendar, ChevronRight, Loader2, Plus } from "lucide-react";
import { useBriefingList, useGenerateBriefing } from "@/hooks/use-briefings";
import { trackFirstBriefing } from "@/lib/analytics";
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
      className="flex items-center gap-4 rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-sm"
    >
      <FileText
        aria-hidden="true"
        className="h-5 w-5 flex-shrink-0 text-blue-600"
      />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-gray-900">
          {item.title}
        </p>
        <div className="mt-0.5 flex items-center gap-2 text-xs text-gray-500">
          <span className="rounded bg-gray-100 px-1.5 py-0.5 font-medium">
            {BRIEFING_TYPE_LABELS[item.briefing_type]}
          </span>
          <Calendar aria-hidden="true" className="h-3 w-3" />
          <span>{new Date(item.generated_at).toLocaleDateString("de-DE")}</span>
        </div>
      </div>
      <ChevronRight
        aria-hidden="true"
        className="h-5 w-5 flex-shrink-0 text-gray-400"
      />
    </Link>
  );
}

export default function BriefingsPage() {
  const { data, isLoading } = useBriefingList({ limit: 50 });
  const generate = useGenerateBriefing();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Briefings</h1>
        <button
          onClick={() => {
            trackFirstBriefing("morning");
            generate.mutate({ type: "morning" });
          }}
          disabled={generate.isPending}
          className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          <Plus aria-hidden="true" className="h-4 w-4" />
          Neues Briefing
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12" role="status">
          <Loader2
            aria-hidden="true"
            className="h-8 w-8 animate-spin text-gray-400"
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
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
          <FileText
            aria-hidden="true"
            className="mx-auto mb-3 h-10 w-10 text-gray-300"
          />
          <h3 className="mb-1 text-sm font-semibold text-gray-900">
            Noch keine Briefings
          </h3>
          <p className="text-sm text-gray-500">
            Erstelle dein erstes Briefing, um loszulegen.
          </p>
        </div>
      )}
    </div>
  );
}
