import type { BriefingDetailResponse } from "@/types/api";

/**
 * Demo-Briefing, das bei Sync-Timeout (>2 min) oder LLM-Fehler als
 * Fallback angezeigt wird. Wird durch das echte Briefing ersetzt,
 * sobald es verfügbar ist.
 */
export const DEMO_BRIEFING: BriefingDetailResponse = {
  id: "demo-briefing",
  briefing_type: "morning",
  title: "Dein erstes Morgen-Briefing (Demo)",
  content: `## Guten Morgen! 👋

Dies ist ein **Demo-Briefing**, das dir zeigt, wie dein persönliches Wissens-Briefing aussehen wird.

### Dein heutiger Überblick

- **3 anstehende Termine** aus deinem Kalender
- **2 aktualisierte Notion-Seiten** seit gestern
- **1 neues Zoom-Transkript** mit Zusammenfassung

### Nächster Termin: Team-Standup (10:00 Uhr)

Relevante Informationen aus deinen verbundenen Quellen:

> *In der letzten Woche wurden im Notion-Workspace drei neue Aufgaben erstellt, die mit dem aktuellen Sprint zusammenhängen. Die Zoom-Aufnahme vom Freitag enthält eine Entscheidung zur API-Architektur.*

### Projekt-Update: PWBS MVP

Basierend auf deinen Notion-Seiten und Kalendereinträgen:

- Sprint-Fortschritt: 7 von 12 Tasks abgeschlossen
- Nächster Meilenstein: Beta-Launch in 2 Wochen
- Offene Entscheidung: Deployment-Strategie (ECS vs. Kubernetes)

### Empfohlene Aktionen

1. Zoom-Transkript vom Freitag durchsehen (Architektur-Entscheidung)
2. Notion-Roadmap aktualisieren (3 neue Tasks)
3. Meeting-Vorbereitung für Team-Standup

---

*Sobald deine Daten synchronisiert sind, wird dieses Demo-Briefing durch dein persönliches Briefing ersetzt.*`,
  source_chunks: [],
  source_entities: [],
  trigger_context: { demo: true },
  generated_at: new Date().toISOString(),
  expires_at: null,
  sources: [
    {
      chunk_id: "demo-source-1",
      doc_title: "Google Calendar – Termine diese Woche",
      source_type: "google_calendar",
      date: new Date().toISOString(),
      relevance: 0.95,
    },
    {
      chunk_id: "demo-source-2",
      doc_title: "Notion – Sprint-Board",
      source_type: "notion",
      date: new Date().toISOString(),
      relevance: 0.88,
    },
    {
      chunk_id: "demo-source-3",
      doc_title: "Zoom – Team-Meeting Transkript",
      source_type: "zoom",
      date: new Date().toISOString(),
      relevance: 0.82,
    },
  ],
};

/** Mindestverzögerung in ms, ab der das Demo-Briefing gezeigt wird */
export const DEMO_BRIEFING_TIMEOUT_MS = 120_000; // 2 Minuten
