"use client";

import {
  useState,
  useRef,
  useCallback,
  useEffect,
  type KeyboardEvent,
} from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Search, Sparkles, Loader2 } from "lucide-react";
import { useAutoComplete } from "@/hooks/use-search";
import { useGenerateBriefing } from "@/hooks/use-briefings";
import type { AutoCompleteItem } from "@/types/api";

type IntentType = "search" | "briefing" | "navigate" | "unknown";

interface ParsedIntent {
  type: IntentType;
  query: string;
  briefingType?: "morning" | "project" | "weekly";
  projectName?: string;
}

const BRIEFING_PATTERNS: Array<{
  pattern: RegExp;
  type: "morning" | "project" | "weekly";
}> = [
  { pattern: /^(morgen|morning|tages?)[\s-]?briefing/i, type: "morning" },
  { pattern: /^(wochen|weekly)[\s-]?briefing/i, type: "weekly" },
  { pattern: /^briefing\s+(für|for|zu)\s+(.+)/i, type: "project" },
  {
    pattern: /^(bereite?|prepare|vorbereitung).*(meeting|besprechung|termin)/i,
    type: "morning",
  },
  { pattern: /^(was steht|what).*(heute|today|an)/i, type: "morning" },
  { pattern: /^(neues? |generiere? |erstelle? )?briefing$/i, type: "morning" },
];

function parseIntent(input: string): ParsedIntent {
  const trimmed = input.trim();
  if (!trimmed) return { type: "unknown", query: "" };

  for (const { pattern, type } of BRIEFING_PATTERNS) {
    const match = trimmed.match(pattern);
    if (match) {
      const projectName = type === "project" ? match[2]?.trim() : undefined;
      return {
        type: "briefing",
        query: trimmed,
        briefingType: type,
        projectName,
      };
    }
  }

  return { type: "search", query: trimmed };
}

interface CommandBarProps {
  /** Compact mode for use in headers/sidebars */
  compact?: boolean;
  /** Auto-focus the input on mount */
  autoFocus?: boolean;
  /** Initial value to pre-fill (changes reset the component) */
  initialValue?: string;
  /** Additional CSS classes */
  className?: string;
}

export function CommandBar({
  compact = false,
  autoFocus = false,
  initialValue = "",
  className = "",
}: CommandBarProps) {
  const [value, setValue] = useState(initialValue);
  const [isFocused, setIsFocused] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const generateBriefing = useGenerateBriefing();

  // Focus on mount if requested
  useEffect(() => {
    if (autoFocus) {
      inputRef.current?.focus();
    }
  }, [autoFocus]);

  const { data: acData } = useAutoComplete(value);
  const suggestions = acData?.suggestions ?? [];

  const intent = parseIntent(value);

  const execute = useCallback(async () => {
    if (!value.trim() || isProcessing) return;

    const parsed = parseIntent(value);

    if (parsed.type === "briefing" && parsed.briefingType) {
      setIsProcessing(true);
      try {
        const triggerContext = parsed.projectName
          ? { project_name: parsed.projectName }
          : undefined;
        await generateBriefing.mutateAsync({
          type: parsed.briefingType,
          trigger_context: triggerContext,
        });
        setValue("");
        router.push("/briefings");
      } finally {
        setIsProcessing(false);
      }
      return;
    }

    // Default: navigate to search with query
    router.push(`/search?q=${encodeURIComponent(value.trim())}`);
    setValue("");
  }, [value, isProcessing, generateBriefing, router]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        e.preventDefault();
        execute();
      }
    },
    [execute],
  );

  const selectSuggestion = useCallback(
    (item: AutoCompleteItem) => {
      router.push(`/search?q=${encodeURIComponent(item.name)}`);
      setValue("");
      setIsFocused(false);
    },
    [router],
  );

  // Global keyboard shortcut: Cmd/Ctrl+K to focus
  useEffect(() => {
    function handleGlobalKey(e: globalThis.KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    document.addEventListener("keydown", handleGlobalKey);
    return () => document.removeEventListener("keydown", handleGlobalKey);
  }, []);

  const showDropdown = isFocused && value.length >= 2 && suggestions.length > 0;

  const intentHint = value.trim()
    ? intent.type === "briefing"
      ? "Enter → Briefing generieren"
      : "Enter → Suchen"
    : null;

  return (
    <div className={`relative ${className}`}>
      <div
        className={`
          flex items-center gap-3 rounded-2xl border bg-surface shadow-sm transition-all
          ${
            isFocused
              ? "border-indigo-300 shadow-lg shadow-indigo-500/10 ring-2 ring-indigo-500/20"
              : "border-border hover:border-indigo-200 hover:shadow-md"
          }
          ${compact ? "px-3 py-2" : "px-5 py-4"}
        `}
      >
        {isProcessing ? (
          <Loader2
            className="h-5 w-5 animate-spin text-indigo-500"
            aria-hidden="true"
          />
        ) : (
          <Search className="h-5 w-5 text-text-tertiary" aria-hidden="true" />
        )}
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setTimeout(() => setIsFocused(false), 200)}
          onKeyDown={handleKeyDown}
          placeholder={
            compact
              ? "Suchen oder fragen… (⌘K)"
              : "Was möchtest du wissen? Suche, stelle Fragen oder generiere ein Briefing…"
          }
          className={`
            flex-1 bg-transparent text-text placeholder:text-text-tertiary
            focus:outline-none
            ${compact ? "text-sm" : "text-base"}
          `}
          aria-label="PWBS Kommandozeile"
          role="combobox"
          aria-expanded={showDropdown || undefined}
          aria-haspopup="listbox"
          aria-controls={showDropdown ? "command-bar-listbox" : undefined}
        />
        {value.trim() && (
          <button
            onClick={execute}
            disabled={isProcessing}
            className="flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-500 disabled:opacity-50"
            aria-label={
              intent.type === "briefing" ? "Briefing generieren" : "Suchen"
            }
          >
            {isProcessing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : intent.type === "briefing" ? (
              <Sparkles className="h-3.5 w-3.5" />
            ) : (
              <ArrowRight className="h-3.5 w-3.5" />
            )}
            <span className="hidden sm:inline">
              {intent.type === "briefing" ? "Generieren" : "Suchen"}
            </span>
          </button>
        )}
        {!value.trim() && !compact && (
          <kbd className="hidden rounded-lg border border-border bg-surface-secondary px-2 py-0.5 text-xs text-text-tertiary sm:inline-block">
            ⌘K
          </kbd>
        )}
      </div>

      {/* Intent hint */}
      {intentHint && !compact && (
        <p className="mt-1.5 px-5 text-xs text-text-tertiary">{intentHint}</p>
      )}

      {/* Autocomplete dropdown */}
      {showDropdown && (
        <ul
          id="command-bar-listbox"
          role="listbox"
          aria-label="Suchvorschläge"
          className="absolute left-0 right-0 z-50 mt-2 max-h-64 overflow-y-auto rounded-xl border border-border bg-surface shadow-xl"
        >
          {suggestions.map((item) => (
            <li
              key={item.entity_id}
              role="option"
              aria-selected="false"
              onMouseDown={() => selectSuggestion(item)}
              className="flex cursor-pointer items-center gap-3 px-4 py-3 transition-colors hover:bg-surface-secondary"
            >
              <Search
                className="h-4 w-4 text-text-tertiary"
                aria-hidden="true"
              />
              <div className="flex-1">
                <p className="text-sm font-medium text-text">{item.name}</p>
                <p className="text-xs text-text-tertiary capitalize">
                  {item.entity_type}
                </p>
              </div>
              <ArrowRight
                className="h-3 w-3 text-text-tertiary"
                aria-hidden="true"
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
