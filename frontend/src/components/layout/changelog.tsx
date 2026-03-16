"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Megaphone } from "lucide-react";

interface ChangelogEntry {
  version: string;
  date: string;
  title: string;
  entries: string[];
}

const STORAGE_KEY = "pwbs_changelog_last_read";

function getLastReadDate(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(STORAGE_KEY);
}

function markAsRead(date: string): void {
  localStorage.setItem(STORAGE_KEY, date);
}

export function ChangelogButton() {
  const [open, setOpen] = useState(false);
  const [changelog, setChangelog] = useState<ChangelogEntry[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);

  // Load changelog data
  useEffect(() => {
    fetch("/changelog.json")
      .then((res) => {
        if (!res.ok) return [];
        return res.json() as Promise<ChangelogEntry[]>;
      })
      .then((data) => {
        setChangelog(data);
        const lastRead = getLastReadDate();
        const unread = lastRead
          ? data.filter((e) => e.date > lastRead).length
          : data.length;
        setUnreadCount(unread);
      })
      .catch(() => {
        setChangelog([]);
      });
  }, []);

  const handleOpen = useCallback(() => {
    setOpen((prev) => {
      if (!prev && changelog.length > 0) {
        markAsRead(changelog[0].date);
        setUnreadCount(0);
      }
      return !prev;
    });
  }, [changelog]);

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
        onClick={handleOpen}
        className="relative rounded-md p-2 text-gray-500 hover:bg-gray-100 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        aria-label={`Neuigkeiten${unreadCount ? ` (${unreadCount} neu)` : ""}`}
        aria-expanded={open}
        aria-haspopup="true"
      >
        <Megaphone className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-blue-500 px-1 text-[10px] font-bold text-white">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && <ChangelogPanel entries={changelog} />}
    </div>
  );
}

function ChangelogPanel({ entries }: { entries: ChangelogEntry[] }) {
  return (
    <div
      className="absolute right-0 top-full z-50 mt-2 w-96 max-h-[32rem] overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg"
      role="dialog"
      aria-label="Neuigkeiten"
    >
      <div className="sticky top-0 border-b border-gray-200 bg-white px-4 py-3">
        <h3 className="text-sm font-semibold text-gray-900">Neuigkeiten</h3>
      </div>

      <div className="divide-y divide-gray-100">
        {entries.length === 0 && (
          <p className="py-6 text-center text-sm text-gray-500">
            Keine Eintraege vorhanden.
          </p>
        )}

        {entries.map((entry) => (
          <div key={entry.version} className="px-4 py-3">
            <div className="flex items-baseline justify-between">
              <span className="text-sm font-semibold text-gray-900">
                {entry.title}
              </span>
              <span className="ml-2 shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                v{entry.version}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-gray-500">{entry.date}</p>
            <ul className="mt-2 space-y-1">
              {entry.entries.map((line, i) => (
                <li
                  key={i}
                  className="flex items-start gap-2 text-sm text-gray-700"
                >
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />
                  {line}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
