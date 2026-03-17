"use client";

import {
  Sparkles,
  CalendarDays,
  Search,
  FolderKanban,
  ArrowRight,
  TrendingUp,
} from "lucide-react";

export interface QuickPrompt {
  label: string;
  prompt: string;
  icon: React.ReactNode;
  color: string;
}

function getTimeOfDay(): "morning" | "afternoon" | "evening" {
  const hour = new Date().getHours();
  if (hour < 12) return "morning";
  if (hour < 18) return "afternoon";
  return "evening";
}

function getGreeting(): string {
  const time = getTimeOfDay();
  if (time === "morning") return "Guten Morgen";
  if (time === "afternoon") return "Guten Tag";
  return "Guten Abend";
}

function getContextualPrompts(): QuickPrompt[] {
  const time = getTimeOfDay();
  const isMonday = new Date().getDay() === 1;
  const isFriday = new Date().getDay() === 5;

  const prompts: QuickPrompt[] = [];

  if (time === "morning") {
    prompts.push({
      label: "Morgen-Briefing",
      prompt: "Morgen-Briefing generieren",
      icon: <Sparkles className="h-4 w-4" />,
      color: "bg-indigo-50 text-indigo-600 hover:bg-indigo-100",
    });
    prompts.push({
      label: "Meetings heute",
      prompt: "Was steht heute an?",
      icon: <CalendarDays className="h-4 w-4" />,
      color: "bg-amber-50 text-amber-600 hover:bg-amber-100",
    });
  }

  if (time === "afternoon") {
    prompts.push({
      label: "Meeting vorbereiten",
      prompt: "Bereite mich auf mein nächstes Meeting vor",
      icon: <CalendarDays className="h-4 w-4" />,
      color: "bg-amber-50 text-amber-600 hover:bg-amber-100",
    });
  }

  if (isFriday) {
    prompts.push({
      label: "Wochenrückblick",
      prompt: "Wochen-Briefing generieren",
      icon: <TrendingUp className="h-4 w-4" />,
      color: "bg-emerald-50 text-emerald-600 hover:bg-emerald-100",
    });
  }

  if (isMonday) {
    prompts.push({
      label: "Wochenstart",
      prompt: "Was war letzte Woche wichtig?",
      icon: <TrendingUp className="h-4 w-4" />,
      color: "bg-emerald-50 text-emerald-600 hover:bg-emerald-100",
    });
  }

  // Always available
  prompts.push({
    label: "Projekt-Status",
    prompt: "Briefing für Projekt ",
    icon: <FolderKanban className="h-4 w-4" />,
    color: "bg-violet-50 text-violet-600 hover:bg-violet-100",
  });

  prompts.push({
    label: "Wissen durchsuchen",
    prompt: "",
    icon: <Search className="h-4 w-4" />,
    color: "bg-sky-50 text-sky-600 hover:bg-sky-100",
  });

  return prompts.slice(0, 4);
}

interface SmartPromptsProps {
  onSelect: (prompt: string) => void;
  className?: string;
}

export function SmartPrompts({ onSelect, className = "" }: SmartPromptsProps) {
  const prompts = getContextualPrompts();

  return (
    <div className={className}>
      <div className="flex flex-wrap gap-2">
        {prompts.map((p) => (
          <button
            key={p.label}
            onClick={() => onSelect(p.prompt)}
            className={`
              inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium
              transition-all ${p.color}
            `}
          >
            {p.icon}
            {p.label}
            <ArrowRight className="h-3 w-3 opacity-50" aria-hidden="true" />
          </button>
        ))}
      </div>
    </div>
  );
}

export function DashboardGreeting({ className = "" }: { className?: string }) {
  const greeting = getGreeting();

  return (
    <div className={className}>
      <h1 className="text-2xl font-bold text-text sm:text-3xl">{greeting}</h1>
      <p className="mt-1 text-text-secondary">Was kann ich für dich tun?</p>
    </div>
  );
}
