---
agent: agent
description: Generiert oder debuggt ein Kontextbriefing für einen PWBS-Nutzer. Analysiert bestehende Briefing-Logik, prüft Quellenreferenzen und verbessert Qualität.
tools:
  - codebase
  - editFiles
---

# Briefing-Feature entwickeln

**Briefing-Typ:** ${input:briefing_type:Typ des Briefings: "morning", "pre_meeting", "project", "weekly"}

## Kontext lesen

1. Lies zuerst `pwbs/briefing/` – bestehende Templates und BriefingAgent-Implementierung.
2. Lies `pwbs/prompts/` – bestehende LLM-Prompt-Templates.
3. Prüfe `pwbs/search/` – welche Suchmethoden für das Briefing relevant sind.

## Anforderungen für alle Briefing-Typen

- **Quellenreferenzen:** Jede generierte Aussage mit mindestens einer `SourceRef` verknüpfen.
- **Fakten vs. Interpretation:** Faktische Aussagen von LLM-Interpretationen visuell trennen.
- **Structured Output:** JSON-Schema für Briefing-Struktur, dann Rendering in Template.
- **Token-Budget:** Innerhalb des Limits für den Briefing-Typ bleiben (siehe Agenten-Instruktionen).
- **LLM-Temperatur:** 0.3 für sachliche Passagen, 0.1 für Strukturdaten.

## Typspezifische Anforderungen

### morning

- Pflichtfelder: `date`, `agenda_items`, `open_threads`, `context_updates`
- Suchanfragen: Kalendereinträge des Tages + offene Tasks aus letzter Woche
- Max. 800 Wörter

### pre_meeting

- Pflichtfelder: `meeting_title`, `attendees`, `last_status`, `open_questions`, `decisions`
- Suchanfragen: Alle Dokumente zu Meeting-Teilnehmern + Thema der letzten 30 Tage
- Max. 400 Wörter

### project

- Pflichtfelder: `project_name`, `status`, `decisions`, `open_risks`, `next_steps`
- Suchanfragen: Graph-Traversal über Projekt-Node + semantische Suche nach Projekt-Name
- Max. 1200 Wörter

### weekly

- Pflichtfelder: `week_summary`, `completed_items`, `carry_overs`, `next_week_priorities`
- Suchanfragen: Alle Dokumente der letzten 7 Tage
- Max. 600 Wörter

## Prompt-Template erstellen/aktualisieren

Erstelle oder aktualisiere `pwbs/prompts/${input:briefing_type:briefing_type}_briefing.jinja2`:

- Systemrolle klar definieren
- Output-Format als JSON-Schema vorgeben
- Quellenreferenzierung in Prompt erzwingen
- Beispiel-Output als Few-Shot im Prompt

## Tests

- Unit-Test für Briefing-Generierung mit gemockten Such-Ergebnissen
- Test dass `sources` niemals leer zurückgegeben wird
- Test für Token-Budget-Einhaltung (mocked LLM-Response > Limit)

## Phase 3: Qualitätsprüfung (Selbst-Review)

Nach der Implementierung, intern prüfen:

- [ ] Wird jede Briefing-Aussage durch mindestens eine `SourceRef` belegt?
- [ ] Sind Fakten (`laut Kalender am 5.3.`) klar von Interpretationen (`möglicherweise wichtig`) getrennt?
- [ ] Bleibt der generierte Text innerhalb des Token-Budgets für den Briefing-Typ?
- [ ] Wird kein LLM-Vorwissen ohne RAG-Quelle in die Antwort eingeflossen sein?
- [ ] Ist das Prompt-Template in `pwbs/prompts/` versioniert (nicht inline im Code)?
