"use client";

import {
  Search,
  FileText,
  Cable,
  CheckCircle2,
  Sparkles,
  CalendarDays,
} from "lucide-react";

export function ProductPreview({ className = "" }: { className?: string }) {
  return (
    <div className={`mx-auto max-w-4xl ${className}`}>
      {/* Browser frame */}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-2xl shadow-indigo-500/10">
        {/* Browser top bar */}
        <div className="flex items-center gap-2 border-b border-gray-100 bg-gray-50 px-4 py-2.5">
          <div className="flex gap-1.5">
            <div className="h-3 w-3 rounded-full bg-red-400" />
            <div className="h-3 w-3 rounded-full bg-amber-400" />
            <div className="h-3 w-3 rounded-full bg-emerald-400" />
          </div>
          <div className="flex-1 text-center">
            <span className="inline-block rounded-md border border-gray-200 bg-white px-16 py-1 text-xs text-gray-400">
              app.pwbs.de
            </span>
          </div>
        </div>

        {/* App content preview */}
        <div className="space-y-5 p-6 sm:p-8">
          {/* Greeting */}
          <div className="text-center">
            <h3 className="text-xl font-bold text-gray-900">Guten Morgen</h3>
            <p className="text-sm text-gray-500">Was kann ich für dich tun?</p>
          </div>

          {/* Command Bar preview */}
          <div className="mx-auto max-w-lg">
            <div className="flex items-center gap-3 rounded-2xl border border-indigo-200 bg-white px-5 py-3.5 shadow-lg shadow-indigo-500/10 ring-2 ring-indigo-500/20">
              <Search className="h-5 w-5 text-gray-400" aria-hidden="true" />
              <span className="text-gray-900">
                Bereite mich auf mein Meeting vor
              </span>
            </div>
          </div>

          {/* Quick prompts preview */}
          <div className="mx-auto flex max-w-lg flex-wrap justify-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-600">
              <Sparkles className="h-3 w-3" aria-hidden="true" />
              Morgen-Briefing
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-600">
              <CalendarDays className="h-3 w-3" aria-hidden="true" />
              Meetings heute
            </span>
          </div>

          {/* Briefing result preview */}
          <div className="mx-auto max-w-lg rounded-xl border border-gray-200 bg-white p-5">
            <div className="mb-3 flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-100">
                <FileText
                  className="h-4 w-4 text-indigo-600"
                  aria-hidden="true"
                />
              </div>
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
                  Meeting-Briefing
                </span>
                <span className="ml-2 text-xs text-gray-400">09:42</span>
              </div>
            </div>
            <div className="space-y-2 text-sm text-gray-600">
              <p className="font-medium text-gray-900">
                Team-Standup · Heute, 10:00
              </p>
              <div className="flex items-center gap-2">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <span>3 Action Items aus Sprint-Retro – 2/3 erledigt</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <span>Budget-Freigabe für Phase 2 erteilt</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
                <span>Architektur-Entscheidung offen – Notiz verknüpft</span>
              </div>
              <p className="pt-2 text-xs italic text-gray-400">
                4 Quellen · Notion, Calendar, Obsidian, Zoom
              </p>
            </div>
          </div>

          {/* Status bar preview */}
          <div className="mx-auto flex max-w-lg items-center justify-between text-xs text-gray-400">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5">
                <Cable className="h-3 w-3" aria-hidden="true" /> 4 Quellen aktiv
              </span>
              <span className="flex items-center gap-1.5">
                <FileText className="h-3 w-3" aria-hidden="true" /> 1.247
                Dokumente
              </span>
            </div>
            <span className="flex items-center gap-1.5">
              <CheckCircle2
                className="h-3 w-3 text-emerald-500"
                aria-hidden="true"
              />{" "}
              Wissensbasis aktiv
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
