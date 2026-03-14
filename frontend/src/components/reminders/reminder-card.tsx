"use client";

import { Clock, AlertTriangle, HelpCircle, FileText } from "lucide-react";
import type { Reminder, ReminderStatus } from "@/types/api";

interface ReminderCardProps {
  reminder: Reminder;
  onAction: (id: string, status: ReminderStatus) => void;
  isPending?: boolean;
}

const TYPE_CONFIG = {
  follow_up: { icon: Clock, label: "Follow-up", color: "text-blue-600" },
  inactive_topic: { icon: AlertTriangle, label: "Inaktives Thema", color: "text-amber-600" },
  open_question: { icon: HelpCircle, label: "Offene Frage", color: "text-purple-600" },
} as const;

const URGENCY_BADGE = {
  high: "bg-red-100 text-red-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-gray-100 text-gray-700",
} as const;

function timeAgo(dateString: string): string {
  const now = Date.now();
  const then = new Date(dateString).getTime();
  const diffMs = now - then;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "heute";
  if (diffDays === 1) return "gestern";
  if (diffDays < 7) return `vor ${diffDays} Tagen`;
  if (diffDays < 30) return `vor ${Math.floor(diffDays / 7)} Wochen`;
  return `vor ${Math.floor(diffDays / 30)} Monaten`;
}

export function ReminderCard({ reminder, onAction, isPending }: ReminderCardProps) {
  const config = TYPE_CONFIG[reminder.reminder_type];
  const Icon = config.icon;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 flex-shrink-0 ${config.color}`} />
          <span className={`text-xs font-medium ${config.color}`}>{config.label}</span>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${URGENCY_BADGE[reminder.urgency]}`}>
            {reminder.urgency}
          </span>
        </div>
        <span className="text-xs text-gray-400 whitespace-nowrap">
          {timeAgo(reminder.created_at)}
        </span>
      </div>

      {/* Content */}
      <div>
        <h4 className="text-sm font-semibold text-gray-900">{reminder.title}</h4>
        {reminder.description && (
          <p className="mt-1 text-sm text-gray-600 line-clamp-2">{reminder.description}</p>
        )}
      </div>

      {/* Context info */}
      <div className="flex flex-wrap gap-3 text-xs text-gray-500">
        {reminder.due_at && (
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            Fällig: {new Date(reminder.due_at).toLocaleDateString("de-DE")}
          </span>
        )}
        {reminder.source_document_id && (
          <span className="flex items-center gap-1">
            <FileText className="h-3 w-3" />
            Quellenreferenz
          </span>
        )}
        {reminder.responsible_person && (
          <span>Verantwortlich: {reminder.responsible_person}</span>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => onAction(reminder.id, "acknowledged")}
          disabled={isPending}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Noch relevant
        </button>
        <button
          onClick={() => onAction(reminder.id, "dismissed")}
          disabled={isPending}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Erledigt
        </button>
        <button
          onClick={() => onAction(reminder.id, "snoozed")}
          disabled={isPending}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Später erinnern
        </button>
      </div>
    </div>
  );
}
