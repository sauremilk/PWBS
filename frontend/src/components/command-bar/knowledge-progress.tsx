"use client";

import { Cable, FileText, Sparkles, CheckCircle2, Circle } from "lucide-react";
import Link from "next/link";
import { useConnectionStatus } from "@/hooks/use-connectors";
import { useLatestBriefing } from "@/hooks/use-briefings";

interface Milestone {
  label: string;
  done: boolean;
  href: string;
}

export function KnowledgeProgress({ className = "" }: { className?: string }) {
  const { data: connData } = useConnectionStatus();
  const { data: briefing } = useLatestBriefing("morning");

  const connections = connData?.connections ?? [];
  const activeCount = connections.filter((c) => c.status === "active").length;
  const totalDocs = connections.reduce((sum, c) => sum + c.doc_count, 0);
  const hasBriefing = !!briefing;

  const milestones: Milestone[] = [
    {
      label: "Datenquelle verbunden",
      done: activeCount > 0,
      href: "/connectors",
    },
    {
      label: "Dokumente synchronisiert",
      done: totalDocs > 0,
      href: "/connectors",
    },
    {
      label: "Erstes Briefing generiert",
      done: hasBriefing,
      href: "/briefings",
    },
  ];

  const completedCount = milestones.filter((m) => m.done).length;
  const allDone = completedCount === milestones.length;
  const progressPercent = Math.round(
    (completedCount / milestones.length) * 100,
  );

  // Once everything is set up, show a compact knowledge score instead
  if (allDone) {
    return (
      <div
        className={`rounded-xl border border-border bg-surface p-4 ${className}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-text">
                Wissensbasis aktiv
              </p>
              <p className="text-xs text-text-tertiary">
                {activeCount} Quellen · {totalDocs.toLocaleString("de-DE")}{" "}
                Dokumente
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <Cable className="h-3.5 w-3.5 text-text-tertiary" />
              <span className="text-sm font-bold text-text">{activeCount}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5 text-text-tertiary" />
              <span className="text-sm font-bold text-text">
                {totalDocs.toLocaleString("de-DE")}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-text-tertiary" />
              <span className="text-sm font-bold text-text">
                {hasBriefing ? "1" : "0"}
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl border border-border bg-surface p-5 ${className}`}
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text">Einrichtung</h3>
        <span className="text-xs font-medium text-text-tertiary">
          {completedCount}/{milestones.length} erledigt
        </span>
      </div>

      {/* Progress bar */}
      <div className="mb-4 h-1.5 rounded-full bg-surface-secondary">
        <div
          className="h-1.5 rounded-full bg-indigo-500 transition-all duration-500"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Milestones */}
      <ul className="space-y-2.5">
        {milestones.map((m) => (
          <li key={m.label}>
            <Link
              href={m.href}
              className="flex items-center gap-3 rounded-lg p-1.5 -mx-1.5 transition-colors hover:bg-surface-secondary"
            >
              {m.done ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              ) : (
                <Circle className="h-4 w-4 text-text-tertiary" />
              )}
              <span
                className={`text-sm ${
                  m.done
                    ? "text-text-secondary line-through"
                    : "font-medium text-text"
                }`}
              >
                {m.label}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
