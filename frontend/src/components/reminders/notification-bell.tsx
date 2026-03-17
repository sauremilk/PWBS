"use client";

import { useState, useRef, useEffect } from "react";
import { Bell, Loader2 } from "lucide-react";
import {
  useReminders,
  useReminderCount,
  useUpdateReminderStatus,
} from "@/hooks/use-reminders";
import { ReminderCard } from "@/components/reminders/reminder-card";
import type { ReminderStatus } from "@/types/api";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const { data: count } = useReminderCount();

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () =>
        document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [open]);

  // Close on Escape
  useEffect(() => {
    function handleEsc(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    if (open) {
      document.addEventListener("keydown", handleEsc);
      return () => document.removeEventListener("keydown", handleEsc);
    }
  }, [open]);

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="relative rounded-md p-2 text-text-tertiary hover:bg-surface-secondary hover:text-text-secondary focus:outline-none focus:ring-2 focus:ring-indigo-500"
        aria-label={`Erinnerungen${count ? ` (${count} offen)` : ""}`}
        aria-expanded={open}
        aria-haspopup="true"
      >
        <Bell className="h-5 w-5" />
        {!!count && count > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>

      {open && <NotificationPanel onClose={() => setOpen(false)} />}
    </div>
  );
}

function NotificationPanel({ onClose }: { onClose: () => void }) {
  const { data, isLoading } = useReminders(20);
  const updateStatus = useUpdateReminderStatus();

  function handleAction(id: string, status: ReminderStatus) {
    updateStatus.mutate({ id, status });
  }

  return (
    <div
      className="absolute right-0 top-full z-50 mt-2 w-96 max-h-[32rem] overflow-y-auto rounded-xl border border-border bg-surface shadow-lg"
      role="dialog"
      aria-label="Erinnerungen"
    >
      <div className="sticky top-0 border-b border-border bg-surface px-4 py-3">
        <h3 className="text-sm font-semibold text-text">
          Erinnerungen
          {data && data.count > 0 && (
            <span className="ml-2 rounded-full bg-surface-secondary px-2 py-0.5 text-xs text-text-secondary">
              {data.count}
            </span>
          )}
        </h3>
      </div>

      <div className="p-3 space-y-3">
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-text-tertiary" />
          </div>
        )}

        {!isLoading && (!data || data.items.length === 0) && (
          <p className="py-6 text-center text-sm text-text-tertiary">
            Keine offenen Erinnerungen.
          </p>
        )}

        {data?.items.map((reminder) => (
          <ReminderCard
            key={reminder.id}
            reminder={reminder}
            onAction={handleAction}
            isPending={updateStatus.isPending}
          />
        ))}
      </div>
    </div>
  );
}
