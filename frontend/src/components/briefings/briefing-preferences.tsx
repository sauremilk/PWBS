"use client";

import { useState, useEffect } from "react";
import { Settings, X, Plus, Loader2 } from "lucide-react";
import {
  useBriefingPreferences,
  useUpdateBriefingPreferences,
} from "@/hooks/use-briefings";

function TagInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder: string;
}) {
  const [input, setInput] = useState("");

  function addTag() {
    const tag = input.trim();
    if (tag && !value.includes(tag)) {
      onChange([...value, tag]);
    }
    setInput("");
  }

  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-text-secondary">
        {label}
      </label>
      <div className="flex flex-wrap gap-1.5 mb-2">
        {value.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700"
          >
            {tag}
            <button
              type="button"
              onClick={() => onChange(value.filter((t) => t !== tag))}
              className="ml-0.5 rounded-full p-0.5 hover:bg-indigo-100"
              aria-label={`${tag} entfernen`}
            >
              <X aria-hidden="true" className="h-3 w-3" />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTag();
            }
          }}
          placeholder={placeholder}
          className="flex-1 rounded-md border border-border px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <button
          type="button"
          onClick={addTag}
          disabled={!input.trim()}
          aria-label="Hinzufügen"
          className="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-sm text-text-secondary hover:bg-surface-secondary disabled:opacity-40"
        >
          <Plus aria-hidden="true" className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

export default function BriefingPreferencesPanel() {
  const { data, isLoading } = useBriefingPreferences();
  const update = useUpdateBriefingPreferences();

  const [focusProjects, setFocusProjects] = useState<string[]>([]);
  const [excludedSources, setExcludedSources] = useState<string[]>([]);
  const [priorityTopics, setPriorityTopics] = useState<string[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (data) {
      setFocusProjects(data.focus_projects);
      setExcludedSources(data.excluded_sources);
      setPriorityTopics(data.priority_topics);
    }
  }, [data]);

  function handleSave() {
    update.mutate({
      focus_projects: focusProjects,
      excluded_sources: excludedSources,
      priority_topics: priorityTopics,
    });
  }

  if (isLoading) return null;

  return (
    <div className="rounded-lg border border-border bg-surface">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        aria-expanded={open ? "true" : "false"}
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-text">
          <Settings aria-hidden="true" className="h-4 w-4 text-text-tertiary" />
          Briefing-Personalisierung
        </span>
        <span
          className={`text-xs text-text-tertiary transition-transform ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        >
          ▾
        </span>
      </button>

      {open && (
        <div className="space-y-4 border-t border-border px-4 py-4">
          <TagInput
            label="Fokus-Projekte"
            value={focusProjects}
            onChange={setFocusProjects}
            placeholder="Projektname eingeben…"
          />
          <TagInput
            label="Prioritäts-Themen"
            value={priorityTopics}
            onChange={setPriorityTopics}
            placeholder="Thema eingeben…"
          />
          <TagInput
            label="Ausgeschlossene Quellen"
            value={excludedSources}
            onChange={setExcludedSources}
            placeholder="z.B. slack, gmail…"
          />
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleSave}
              disabled={update.isPending}
              className="inline-flex items-center gap-1.5 rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {update.isPending && (
                <Loader2
                  aria-hidden="true"
                  className="h-3.5 w-3.5 animate-spin"
                />
              )}
              Speichern
            </button>
          </div>
          {update.isSuccess && (
            <p className="text-xs text-green-600">
              Präferenzen gespeichert.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
