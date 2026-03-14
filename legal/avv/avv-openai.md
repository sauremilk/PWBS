# Auftragsverarbeitungsvertrag (AVV) – OpenAI

**Vertrag zwischen:**
- **Verantwortlicher:** [Firma/Name], Betreiber des PWBS
- **Auftragsverarbeiter:** OpenAI, L.L.C.

**Datum:** [Datum einsetzen]
**Version:** 1.0

---

## 1. Gegenstand der Auftragsverarbeitung

OpenAI stellt Embedding-Generierung (text-embedding-3-small) und GPT-4 als Fallback-LLM bereit. Dokumenten-Chunks und Suchqueries werden zur Verarbeitung an die OpenAI API übermittelt.

## 2. Dauer

Der AVV gilt für die Laufzeit der API-Nutzung. Nach Beendigung gilt die Zero-Data-Retention-Policy.

## 3. Art und Zweck der Verarbeitung

| Aspekt | Beschreibung |
|--------|-------------|
| **Services** | Embeddings API (text-embedding-3-small), Chat Completions API (GPT-4, Fallback) |
| **Zweck** | Semantische Vektorisierung von Dokumenten-Chunks, Fallback-LLM für Briefings |
| **Art** | Transiente Verarbeitung (kein Speichern von Input/Output) |

## 4. Kategorien betroffener Personen

- PWBS-Nutzer (indirekt über Dokumentinhalte)
- In Dokumenten genannte Dritte

## 5. Kategorien personenbezogener Daten

- Dokumenten-Chunks (128–512 Token, potenziell PII-haltig)
- Suchqueries (Freitext)
- Briefing-Prompts mit Kontextdaten (Kalender, Notizen, Entscheidungen)

## 6. Pflichten des Auftragsverarbeiters

### 6.1 Zero Data Retention
- **API-Inputs und -Outputs werden NICHT gespeichert** (Zero Data Retention Policy)
- **Kein Training mit API-Daten** (vertragliche Bestätigung erforderlich)
- Keine Weitergabe an Dritte

### 6.2 Datenresidenz
- **Klärungsbedarf:** EU-Endpoint verfügbar? Falls nicht:
  - Standardvertragsklauseln (SCCs) erforderlich
  - Transfer Impact Assessment (TIA) dokumentieren
  - Zusätzliche Schutzmaßnahmen: Pseudonymisierung der Chunks vor Übermittlung prüfen

### 6.3 Weisungsgebundenheit
- Verarbeitung ausschließlich gemäß API-Aufruf
- Keine eigenständige Nutzung der übermittelten Daten

### 6.4 Sicherheit
- TLS 1.2+ für alle API-Kommunikation
- API-Key-Authentifizierung (verschlüsselt gespeichert auf Clientseite)

## 7. Unterauftragsverarbeitung

Liste der Sub-Processors: Microsoft Azure (Hosting), weitere gemäß OpenAI DPA.
Änderungsbenachrichtigung: 30 Tage Vorlauf. Widerspruchsrecht besteht.

## 8. Löschung

- Zero Data Retention: Keine Löschung erforderlich (Daten werden nicht persistiert)
- Bestätigung der Nicht-Speicherung auf Anfrage

## 9. Unterstützungspflichten

- Meldung von Datenschutzvorfällen innerhalb von 72 Stunden
- Unterstützung bei Betroffenenanfragen soweit technisch möglich

## 10. Besondere Vereinbarungen

### 10.1 Kein Modell-Training
OpenAI bestätigt schriftlich, dass über die API übermittelte Daten **nicht** zum Training von KI-Modellen verwendet werden (API Business Terms).

### 10.2 Content-Filter-Logs
Klärung erforderlich: Werden Daten, die Content-Filter auslösen, separat gespeichert? Falls ja: Rechtsgrundlage und Löschfrist definieren.

### 10.3 Risikominimierung PWBS-seitig
- Chunks vor Übermittlung auf maximal 512 Token begrenzt
- Keine vollständigen Dokumente übermittelt, nur segmentierte Chunks
- Owner_id wird NICHT an API übermittelt
- Fallback auf lokale Modelle (Sentence Transformers) bei Verfügbarkeitsproblemen

---

## Referenzen

- OpenAI DPA: https://openai.com/policies/data-processing-addendum
- OpenAI API Terms: https://openai.com/policies/terms-of-use
- Projekt-TOM: `legal/tom.md`
- DSGVO-Erstkonzept: `docs/dsgvo-erstkonzept.md`

---

**Unterschriften:**

| Verantwortlicher | Auftragsverarbeiter (OpenAI) |
|:---:|:---:|
| ___________________________ | ___________________________ |
| Name, Datum | Name, Datum |
