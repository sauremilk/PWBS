"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Plus, X, Loader2 } from "lucide-react";
import { useCreateDecision } from "@/hooks/use-decisions";
import type { DecisionStatus } from "@/types/api";

function ListEditor({
  label,
  items,
  onChange,
  placeholder,
}: {
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
  placeholder: string;
}) {
  const [draft, setDraft] = useState("");
  const inputId = `list-editor-${label.toLowerCase().replace(/\s+/g, "-")}`;

  const add = () => {
    const trimmed = draft.trim();
    if (!trimmed) return;
    onChange([...items, trimmed]);
    setDraft("");
  };

  const remove = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  return (
    <div>
      <label
        htmlFor={inputId}
        className="mb-1 block text-sm font-medium text-text-secondary"
      >
        {label}
      </label>
      <div className="flex gap-2">
        <input
          id={inputId}
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          placeholder={placeholder}
          className="flex-1 rounded-lg border border-border px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <button
          type="button"
          onClick={add}
          className="rounded-lg border border-border px-2 py-1.5 text-text-secondary hover:bg-surface-secondary"
          aria-label="Eintrag hinzufügen"
        >
          <Plus aria-hidden="true" className="h-4 w-4" />
        </button>
      </div>
      {items.length > 0 && (
        <ul className="mt-2 space-y-1">
          {items.map((item, i) => (
            <li
              key={i}
              className="flex items-center justify-between rounded-md bg-surface-secondary px-3 py-1.5 text-sm"
            >
              <span className="text-text-secondary">{item}</span>
              <button
                type="button"
                onClick={() => remove(i)}
                className="ml-2 text-text-tertiary hover:text-red-500"
                aria-label="Eintrag entfernen"
              >
                <X aria-hidden="true" className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function DecisionForm() {
  const router = useRouter();
  const createMutation = useCreateDecision();

  const [summary, setSummary] = useState("");
  const [proArgs, setProArgs] = useState<string[]>([]);
  const [contraArgs, setContraArgs] = useState<string[]>([]);
  const [assumptions, setAssumptions] = useState<string[]>([]);
  const [dependencies, setDependencies] = useState<string[]>([]);
  const [status, setStatus] = useState<DecisionStatus>("pending");
  const [decidedBy, setDecidedBy] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!summary.trim()) return;

    const result = await createMutation.mutateAsync({
      summary: summary.trim(),
      pro_arguments: proArgs,
      contra_arguments: contraArgs,
      assumptions,
      dependencies,
      status,
      decided_by: decidedBy.trim() || null,
    });

    router.push(`/decisions/${result.id}`);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => router.push("/decisions")}
          className="rounded p-1 text-text-tertiary hover:text-text-secondary"
          aria-label="Zurück zur Übersicht"
        >
          <ArrowLeft aria-hidden="true" className="h-5 w-5" />
        </button>
        <h1 className="text-xl font-bold text-text">Neue Entscheidung</h1>
      </div>

      {/* Summary */}
      <div>
        <label
          htmlFor="summary"
          className="mb-1 block text-sm font-medium text-text-secondary"
        >
          Zusammenfassung *
        </label>
        <textarea
          id="summary"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          required
          maxLength={2000}
          rows={3}
          placeholder="Was wurde entschieden?"
          className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      {/* Status + Decided By */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <label
            htmlFor="status"
            className="mb-1 block text-sm font-medium text-text-secondary"
          >
            Status
          </label>
          <select
            id="status"
            value={status}
            onChange={(e) => setStatus(e.target.value as DecisionStatus)}
            className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="pending">Ausstehend</option>
            <option value="made">Entschieden</option>
            <option value="revised">Revidiert</option>
          </select>
        </div>
        <div>
          <label
            htmlFor="decidedBy"
            className="mb-1 block text-sm font-medium text-text-secondary"
          >
            Entschieden von
          </label>
          <input
            id="decidedBy"
            type="text"
            value={decidedBy}
            onChange={(e) => setDecidedBy(e.target.value)}
            placeholder="Name oder Rolle"
            className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Pro/Contra */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ListEditor
          label="Pro-Argumente"
          items={proArgs}
          onChange={setProArgs}
          placeholder="Argument hinzuf&uuml;gen..."
        />
        <ListEditor
          label="Contra-Argumente"
          items={contraArgs}
          onChange={setContraArgs}
          placeholder="Argument hinzuf&uuml;gen..."
        />
      </div>

      {/* Assumptions & Dependencies */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ListEditor
          label="Annahmen"
          items={assumptions}
          onChange={setAssumptions}
          placeholder="Annahme hinzuf&uuml;gen..."
        />
        <ListEditor
          label="Abh&auml;ngigkeiten"
          items={dependencies}
          onChange={setDependencies}
          placeholder="Abh&auml;ngigkeit hinzuf&uuml;gen..."
        />
      </div>

      {/* Submit */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={!summary.trim() || createMutation.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {createMutation.isPending && (
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
          )}
          Entscheidung erstellen
        </button>
      </div>

      {createMutation.isError && (
        <p className="text-sm text-red-600">
          Fehler beim Erstellen: {createMutation.error.message}
        </p>
      )}
    </form>
  );
}
