"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FolderKanban, Search, ArrowRight } from "lucide-react";

export default function ProjectsPage() {
  const router = useRouter();
  const [projectName, setProjectName] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = projectName.trim();
    if (trimmed) {
      router.push(`/projects/${encodeURIComponent(trimmed)}`);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Projekte</h1>

      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-2 text-lg font-semibold text-gray-900">
          Projekt-Briefing erstellen
        </h2>
        <p className="mb-4 text-sm text-gray-500">
          Gib einen Projektnamen ein, um ein On-Demand-Briefing mit
          Entscheidungen, Timeline und Beteiligten zu generieren.
        </p>
        <form onSubmit={handleSubmit} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Projektname eingeben…"
              className="w-full rounded-md border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={!projectName.trim()}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Zum Projekt
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center">
        <FolderKanban className="mx-auto mb-3 h-10 w-10 text-gray-300" />
        <h3 className="mb-1 text-sm font-semibold text-gray-900">
          Projekt-Übersicht
        </h3>
        <p className="text-sm text-gray-500">
          Suche ein Projekt, um ein detailliertes Briefing zu generieren. Das
          Briefing enthält Entscheidungen, Beteiligte und relevante Dokumente
          aus den letzten 90 Tagen.
        </p>
      </div>
    </div>
  );
}
