# Auftragsverarbeitungsvertrag (AVV) – Anthropic

**Vertrag zwischen:**
- **Verantwortlicher:** [Firma/Name], Betreiber des PWBS
- **Auftragsverarbeiter:** Anthropic, PBC

**Datum:** [Datum einsetzen]
**Version:** 1.0

---

## 1. Gegenstand der Auftragsverarbeitung

Anthropic ist der primäre LLM-Provider des PWBS. Die Claude API wird für Briefing-Generierung, Kontextaufbereitung und Antwortgenerierung genutzt. Nutzer-Dokumentkontext wird als Prompt-Bestandteil übermittelt.

## 2. Dauer

Der AVV gilt für die Laufzeit der API-Nutzung.

## 3. Art und Zweck der Verarbeitung

| Aspekt | Beschreibung |
|--------|-------------|
| **Services** | Claude API (Messages API, primärer LLM-Provider) |
| **Zweck** | Briefing-Generierung (Morning, Meeting, Weekly), Suchantworten, Entscheidungsextraktion |
| **Art** | Transiente Verarbeitung mit Structured Output (JSON-Schema) |

## 4. Kategorien betroffener Personen

- PWBS-Nutzer (indirekt über Dokumentkontext in Prompts)
- In Dokumenten genannte Dritte (Meeting-Teilnehmer, Projektbeteiligte)

## 5. Kategorien personenbezogener Daten

- Dokumenten-Chunks als Prompt-Kontext (Kalender, Notizen, E-Mails, Transkripte, Slack)
- Entitäten aus Knowledge Graph (Personen, Projekte, Entscheidungen)
- Briefing-Prompts mit strukturierten Kontextdaten

## 6. Pflichten des Auftragsverarbeiters

### 6.1 Datenspeicherung und -nutzung
- **Kein Training mit API-Daten** (vertragliche Bestätigung gemäß Anthropic API Terms)
- **Klärungsbedarf:** Speicherdauer von API-Logs/Prompts bei Anthropic
  - Safety-Evaluations: Welche Daten werden für wie lange gespeichert?
  - Prompt-Logging: Opt-Out verfügbar?
- Zero Data Retention Status vertraglich absichern

### 6.2 Datenresidenz
- **Klärungsbedarf:** EU-Datenresidenz verfügbar?
- Falls kein EU-Endpoint:
  - Standardvertragsklauseln (SCCs) gemäß Art. 46 Abs. 2c DSGVO
  - Transfer Impact Assessment (TIA) dokumentiert in `legal/tia-anthropic.md`
  - Risikominimierung durch Chunking (keine vollständigen Dokumente)

### 6.3 Weisungsgebundenheit
- Verarbeitung ausschließlich gemäß API-Aufrufen des PWBS
- Keine eigenständige Nutzung, Weitergabe oder Aggregation

### 6.4 Sicherheit
- TLS 1.2+ für alle API-Kommunikation
- API-Key mit AES-256-GCM verschlüsselt in Datenbank
- Rate Limiting auf PWBS-Seite konfiguriert

## 7. Unterauftragsverarbeitung

Sub-Processors gemäß Anthropic DPA. Änderungsbenachrichtigung mit 30 Tagen Vorlauf. Widerspruchsrecht besteht.

## 8. Löschung

- Bestätigung der Löschung/Nicht-Persistierung auf Anfrage
- Nachweis der Zero-Retention-Policy

## 9. Unterstützungspflichten

- Meldung von Datenschutzvorfällen innerhalb von 72 Stunden
- Kooperation bei Betroffenenanfragen
- Bereitstellung von Compliance-Nachweisen (SOC 2, Zertifizierungen)

## 10. Besondere Vereinbarungen

### 10.1 Prompt-Safety-Logging
Anthropic führt Safety-Evaluations durch. Klärung erforderlich:
- Werden Prompts, die Safety-Filter auslösen, gespeichert?
- Für wie lange?
- Opt-Out-Möglichkeit für API-Kunden?
- Falls Speicherung: Rechtsgrundlage und Mindestspeicherfristen definieren

### 10.2 Risikominimierung PWBS-seitig
- Chunks auf maximal 512 Token begrenzt (kein vollständiger Dokumentkontext)
- LLM-Temperatur 0.3 (reduziert Varianz/Halluzinationen)
- Grounding-Validierung: Quellenreferenzen werden gegen Originaldokumente geprüft
- Owner_id wird NICHT in Prompts übermittelt
- Fallback auf OpenAI GPT-4 bei Nichtverfügbarkeit (separater AVV)
- Lokaler Ollama-Fallback für Offline-Nutzung (kein Drittlandtransfer)

### 10.3 Datenminimierung
- Nur relevante Chunks werden übermittelt (RAG-Selektion, Top-K)
- System-Prompts enthalten keine nutzerspezifischen PII
- Nutzerbezogene Kontextdaten sind auf das Minimum für die Aufgabe beschränkt

---

## Referenzen

- Anthropic Commercial Terms: https://www.anthropic.com/policies
- Projekt-TOM: `legal/tom.md`
- DSGVO-Erstkonzept: `docs/dsgvo-erstkonzept.md`

---

**Unterschriften:**

| Verantwortlicher | Auftragsverarbeiter (Anthropic) |
|:---:|:---:|
| ___________________________ | ___________________________ |
| Name, Datum | Name, Datum |
