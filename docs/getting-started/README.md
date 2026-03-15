# PWBS  Getting Started Guide

> **Zielgruppe:** Early Adopter (erste 1020 Nutzer)
> **Version:** MVP (Phase 2)
> **Stand:** März 2026

Willkommen beim **Persönlichen Wissens-Betriebssystem (PWBS)**! Dieses Handbuch führt dich in vier Schritten von der Ersteinrichtung bis zur täglichen Nutzung.

---

## Inhaltsverzeichnis

1. [Kapitel 1: Setup  Account erstellen & einrichten](#kapitel-1-setup--account-erstellen--einrichten)
2. [Kapitel 2: Konnektoren  Datenquellen verbinden](#kapitel-2-konnektoren--datenquellen-verbinden)
3. [Kapitel 3: Briefings  Kontextbriefings nutzen](#kapitel-3-briefings--kontextbriefings-nutzen)
4. [Kapitel 4: Suche  Semantische Wissenssuche](#kapitel-4-suche--semantische-wissenssuche)
5. [FAQ  Häufige Fragen](#faq--häufige-fragen)
6. [Troubleshooting](#troubleshooting)
7. [Glossar](#glossar)

---

## Kapitel 1: Setup  Account erstellen & einrichten

### 1.1 Registrierung

1. Öffne die PWBS-Anwendung im Browser.
2. Klicke auf **Registrieren**.
3. Gib deine E-Mail-Adresse und ein sicheres Passwort ein.

**Passwort-Anforderungen:**
- Mindestens 12 Zeichen
- Mindestens ein Großbuchstabe
- Mindestens eine Ziffer

4. Klicke auf **Account erstellen**.
5. Du wirst automatisch eingeloggt und zum Welcome-Screen weitergeleitet.

`

           PWBS Registrierung        
                                     
  E-Mail:    [________________]      
  Passwort:  [________________]      
                                     
      
      Account erstellen            
      
                                     
  Bereits registriert?  Anmelden    

`

<!-- TODO: Screenshot ersetzen wenn finales UI steht -->

> **Sicherheitshinweis:** Bei der Registrierung wird automatisch ein persönlicher Verschlüsselungsschlüssel (DEK) erzeugt. Alle deine Daten werden damit verschlüsselt gespeichert.

### 1.2 Erster Login

Nach der Registrierung bist du automatisch eingeloggt. Bei späteren Besuchen:

1. Öffne die PWBS-Anwendung.
2. Gib E-Mail und Passwort ein.
3. Klicke auf **Anmelden**.

Du erhältst ein JWT-Token-Paar (Access + Refresh Token), das deine Session absichert. Das Access Token läuft nach 15 Minuten ab und wird automatisch erneuert.

### 1.3 Dashboard-Übersicht

Nach dem Login siehst du das Dashboard:

`

  PWBS                          [Suche ]   []    

                                                     
 Dashboard    Morgenbriefing                       
 Briefings                          
 Suche       Dein tägliches Briefing erscheint       
 Quellen     hier, sobald du eine Datenquelle        
 Profil      verbunden hast.                         
                                                     
              Jetzt Datenquelle verbinden           
                                                     

`

<!-- TODO: Screenshot ersetzen wenn finales UI steht -->

---

## Kapitel 2: Konnektoren  Datenquellen verbinden

PWBS bezieht sein Wissen aus deinen persönlichen Datenquellen. Im MVP stehen vier Konnektoren zur Verfügung:

| Konnektor          | Auth-Methode   | Datentypen                                       |
| ------------------ | -------------- | ------------------------------------------------ |
| **Google Calendar** | OAuth2         | Events, Teilnehmer, Beschreibungen               |
| **Notion**          | OAuth2         | Seiten, Datenbanken, Kommentare                  |
| **Zoom**            | OAuth2         | Meeting-Transkripte, Teilnehmerlisten, Metadaten  |
| **Obsidian**        | Lokaler Pfad   | Markdown-Dateien, Frontmatter, interne Links      |

### 2.1 Konnektoren-Seite öffnen

1. Navigiere zu **Quellen** in der linken Seitenleiste.
2. Du siehst die verfügbaren Konnektoren als Karten.

`

  Datenquellen                                        
                                                      
  Verfügbare Quellen                                  
              
    Google            Notion                  
      Calendar                                    
   [Verbinden]         [Verbinden]                
              
              
    Zoom              Obsidian                
                                                  
   [Verbinden]         [Konfigurieren]            
              

`

<!-- TODO: Screenshot ersetzen wenn finales UI steht -->

### 2.2 Google Calendar verbinden

1. Klicke auf **Verbinden** bei Google Calendar.
2. Du wirst zur **Einwilligungserklärung** weitergeleitet. Lies die Datentypen, die PWBS abruft:
   - Kalendereinträge
   - Teilnehmerlisten
   - Besprechungsnotizen
3. Bestätige mit **Einwilligen & verbinden**.
4. Du wirst zum Google-Consent-Screen weitergeleitet (Scope: `calendar.events.readonly`).
5. Erteile die Berechtigung bei Google.
6. Nach der Rückkehr startet der **initiale Sync** automatisch.

`
Ablauf:
  [Verbinden]  Einwilligung  Google OAuth  Callback  Initialer Sync
                                                            
                                                            
  Karte klicken   DSGVO-Info    Google Login   Token wird   Events werden
                  bestätigen    + Consent      gespeichert  importiert
`

> **Datenschutz:** PWBS liest nur Termine  es kann keine Kalendereinträge erstellen, ändern oder löschen.

### 2.3 Notion verbinden

1. Klicke auf **Verbinden** bei Notion.
2. Bestätige die Einwilligungserklärung.
3. Du wirst zum Notion-Autorisierungs-Screen weitergeleitet.
4. Wähle den Workspace und die Seiten, die PWBS lesen darf.
5. Bestätige den Zugriff.
6. Nach der Rückkehr beginnt der Sync der freigegebenen Seiten.

> **Hinweis:** Notion-Access-Tokens laufen nicht ab. Du kannst die Integration jederzeit in deinen Notion-Einstellungen widerrufen.

### 2.4 Zoom verbinden

1. Klicke auf **Verbinden** bei Zoom.
2. Bestätige die Einwilligungserklärung.
3. Du wirst zum Zoom-OAuth-Screen weitergeleitet (Scope: `recording:read`).
4. Erteile die Berechtigung.
5. Vorhandene Meeting-Transkripte werden importiert. Neue Transkripte werden automatisch nach Abschluss einer Aufnahme synchronisiert.

### 2.5 Obsidian verbinden

Obsidian nutzt keinen OAuth-Flow  stattdessen gibst du den lokalen Pfad zu deinem Vault an:

1. Klicke auf **Konfigurieren** bei Obsidian.
2. Gib den Pfad zu deinem Obsidian-Vault ein (z. B. `C:\Users\max\Documents\MeinVault` oder `/home/max/MeinVault`).
3. Klicke auf **Verbinden**.
4. PWBS scannt den Vault und zeigt die Anzahl gefundener `.md`-Dateien an.

`

  Obsidian Vault verbinden           
                                     
  Vault-Pfad:                        
  [/home/max/Documents/MeinVault ]   
                                     
      
         Verbinden                 
      

`

<!-- TODO: Screenshot ersetzen wenn finales UI steht -->

> **Hinweis:** Der Vault-Pfad muss auf ein Verzeichnis zeigen, das `.md`-Dateien enthält. Falls keine gefunden werden, erscheint die Meldung *Kein gültiger Obsidian-Vault gefunden*.

### 2.6 Sync-Status prüfen

Nach dem Verbinden zeigt die Konnektoren-Seite den Status jeder Quelle:

| Status       | Bedeutung                                           |
| ------------ | --------------------------------------------------- |
|  Aktiv      | Konnektor verbunden, regelmäßiger Sync läuft        |
|  Pausiert   | Sync wurde manuell pausiert                         |
|  Fehler     | Sync fehlgeschlagen (z. B. Token abgelaufen)        |
|  Sync läuft | Daten werden gerade importiert                      |

Du kannst jederzeit einen **manuellen Sync** über den -Button auslösen.

---

## Kapitel 3: Briefings  Kontextbriefings nutzen

Briefings sind das Herzstück von PWBS: KI-generierte Zusammenfassungen deiner Informationen, genau dann, wenn du sie brauchst.

### 3.1 Briefing-Typen

| Typ                  | Wann                        | Umfang         |
| -------------------- | --------------------------- | -------------- |
| **Morgenbriefing**   | Täglich um 06:30 Uhr       | Max. 800 Wörter |
| **Meeting-Briefing** | 30 Min. vor jedem Meeting   | Max. 400 Wörter |
| **Projekt-Briefing** | Auf Anfrage                 | Max. 1200 Wörter|
| **Wochenbriefing**   | Freitag um 17:00 Uhr       | Max. 600 Wörter |

### 3.2 Dein erstes Briefing

Nach dem Verbinden deiner ersten Datenquelle wird automatisch ein Morgenbriefing generiert:

1. Die importierten Daten werden verarbeitet (Embeddings + Entitätserkennung).
2. Der Briefing-Agent erstellt dein erstes Morgenbriefing.
3. Das Briefing erscheint auf dem Dashboard.

`

   Morgenbriefing  15. März 2026                   
                  
                                                      
   Termine heute                                    
   09:00  Sprint Planning (Teams: Anna, Max, Lisa) 
   14:00  1:1 mit Dr. Mueller                      
                                                      
   Offene Themen                                    
   Projektbericht Q1  Deadline morgen               
   Review-Feedback von Lisa steht aus                
                                                      
   Kontext                                          
  Im letzten 1:1 mit Dr. Mueller wurde die            
  Budget-Freigabe für Q2 besprochen. [Quelle: Zoom   
  Transkript 08.03.2026]                              
                                                      
                
  Quellen: Google Calendar (3), Notion (2), Zoom (1)  

`

<!-- TODO: Screenshot ersetzen wenn finales UI steht -->

> **Wichtig:** Jedes Briefing enthält Quellenreferenzen. PWBS erfindet keine Informationen  alle Aussagen basieren auf deinen tatsächlichen Daten.

### 3.3 Meeting-Briefing

30 Minuten vor einem Kalender-Event generiert PWBS automatisch ein Meeting-Briefing mit:

- Agenda und Teilnehmer des anstehenden Meetings
- Relevante Notizen und Dokumente zu den Teilnehmern und Themen
- Offene Punkte aus früheren Meetings mit denselben Teilnehmern
- Entscheidungen und Beschlüsse aus dem letzten Meeting

### 3.4 Briefing auf Anfrage

Du kannst jederzeit ein Projekt-Briefing anfordern:

1. Navigiere zu **Briefings** in der Seitenleiste.
2. Klicke auf **Neues Briefing**.
3. Wähle den Typ **Projekt-Briefing**.
4. Gib den Projektnamen oder ein Stichwort ein.
5. PWBS durchsucht deine Daten und erstellt ein Briefing mit allen relevanten Informationen.

---

## Kapitel 4: Suche  Semantische Wissenssuche

### 4.1 Wie die Suche funktioniert

Die PWBS-Suche versteht die *Bedeutung* deiner Frage  nicht nur einzelne Stichwörter. Wenn du z. B. nach Was hat Lisa zum Budget gesagt?" suchst, findet PWBS relevante Stellen in Meeting-Transkripten, Notion-Seiten und Kalendernotizen.

**Suchmodi:**

| Modus       | Beschreibung                                               |
| ----------- | ---------------------------------------------------------- |
| **Hybrid**  | Kombiniert semantische + Keyword-Suche (Standard)          |
| **Semantisch** | Findet bedeutungsähnliche Inhalte                       |
| **Keyword** | Klassische Volltextsuche                                   |

### 4.2 Suche nutzen

1. Klicke auf das -Suchfeld im Dashboard-Header oder navigiere zu **Suche**.
2. Gib deine Frage oder Stichwörter ein.
3. Drücke Enter oder klicke auf **Suchen**.
4. Die Ergebnisse erscheinen sortiert nach Relevanz, jeweils mit:
   - Titel und Textauszug
   - Quelle (z. B. Notion", Zoom-Transkript")
   - Datum
   - Relevanz-Score

`

   [Was hat Lisa zum Budget gesagt?        ] [Suche]
                                                      
  3 Ergebnisse (0.2s)                                 
                                                      
   Sprint Planning  Zoom Transkript                
     08.03.2026  Relevanz: 94%                       
     "Lisa: Das Budget für Q2 sollte um 15%           
     erhöht werden, da wir zwei neue Tools..."        
                                                      
   Projektplanung Q2  Notion                       
     10.03.2026  Relevanz: 87%                       
     "Budget-Übersicht: Lisa hat vorgeschlagen..."    
                                                      
   1:1 Lisa/Max  Google Calendar                   
     12.03.2026  Relevanz: 72%                       
     "Agenda: Budget-Review Q2, Team-Erweiterung"     

`

<!-- TODO: Screenshot ersetzen wenn finales UI steht -->

### 4.3 Suchtipps

- **Natürliche Sprache:** Stelle Fragen wie im Gespräch  Wann war das letzte Meeting mit Anna?"
- **Filtern:** Grenze Ergebnisse nach Quelle, Datum oder Entitätstyp ein.
- **Kontext:** Je mehr Datenquellen verbunden sind, desto besser werden die Suchergebnisse.

> **Datenschutz:** Die Suche zeigt nur deine eigenen Daten an. Nutzer können niemals Daten anderer Nutzer sehen.

---

## FAQ  Häufige Fragen

### Allgemein

**1. Was genau macht PWBS mit meinen Daten?**
PWBS liest Daten aus deinen verbundenen Quellen (Calendar-Events, Notion-Seiten, Zoom-Transkripte, Obsidian-Notizen), erzeugt semantische Embeddings und speichert alles verschlüsselt. Daraus generiert die KI Briefings und ermöglicht eine semantische Suche. Deine Daten werden **niemals** zum Trainieren von KI-Modellen verwendet.

**2. Wo werden meine Daten gespeichert?**
Alle Daten werden verschlüsselt in der EU gespeichert (PostgreSQL + Weaviate). Jeder Nutzer hat einen eigenen Verschlüsselungsschlüssel (DEK). Weitere Details findest du in der [Datenschutzerklärung](../../DSGVO.md).

**3. Kann ich meine Daten exportieren oder löschen?**
Ja. Unter **Profil  Datenschutz** kannst du:
- Einen vollständigen DSGVO-Datenexport anfordern (JSON/ZIP).
- Deinen Account und alle Daten unwiderruflich löschen (nach einer 72-Stunden-Karenzfrist).

**4. Welche Datenquellen werden unterstützt?**
Im MVP: **Google Calendar**, **Notion**, **Zoom** und **Obsidian**. Weitere Quellen (Gmail, Slack, Google Docs, Outlook) folgen in Phase 3.

### Konnektoren

**5. Was passiert, wenn ich eine Datenquelle trenne?**
Beim Trennen (Disconnect) werden die OAuth-Tokens gelöscht und der Sync gestoppt. Die bereits importierten Daten bleiben erhalten, bis du sie explizit über **Profil  Datenschutz** löschst.

**6. Wie oft synchronisiert PWBS meine Daten?**
- **Google Calendar:** Alle 15 Minuten (Polling) + Webhook-Support
- **Notion:** Alle 10 Minuten (Polling via `last_edited_time`-Cursor)
- **Zoom:** Automatisch bei Abschluss einer Aufnahme (Webhook)
- **Obsidian:** Beim manuellen Sync oder nach Konfiguration

**7. Kann ich den Sync manuell auslösen?**
Ja. Auf der Konnektoren-Seite findest du bei jedem verbundenen Konnektor einen -Button für den manuellen Sync.

### Briefings & Suche

**8. Warum ist mein Briefing leer oder sehr kurz?**
Mögliche Ursachen:
- Es sind noch keine oder sehr wenige Daten importiert  verbinde eine weitere Quelle.
- Der initiale Sync ist noch nicht abgeschlossen  warte einige Minuten.
- Für den heutigen Tag liegen keine relevanten Termine oder Aktivitäten vor.

**9. Woher weiß ich, ob das Briefing korrekt ist?**
Jedes Briefing enthält Quellenreferenzen am Ende. Klicke auf eine Quelle, um den Originalinhalt zu sehen. PWBS verwendet ausschließlich deine eigenen Daten (RAG-Ansatz)  es erfindet keine Informationen.

**10. Wie genau ist die semantische Suche?**
Die Suche kombiniert Vektor-Ähnlichkeit mit klassischer Keyword-Suche (Hybrid-Modus). Die Qualität steigt mit der Menge verbundener Datenquellen. Bei sehr spezifischen Fachbegriffen kann der Keyword-Modus bessere Ergebnisse liefern.

**11. Gibt es eine API für automatisierte Abfragen?**
Die vollständige API-Dokumentation findest du in der [OpenAPI-Spezifikation](../api/openapi.json). Eine importierbare [Postman-Collection](../api/pwbs-collection.json) steht ebenfalls zur Verfügung.

---

## Troubleshooting

### OAuth-Token abgelaufen

**Symptom:** Konnektor zeigt Status  *Fehler* an.

**Ursache:** Der OAuth-Access-Token ist abgelaufen und konnte nicht automatisch erneuert werden (z. B. weil der Refresh-Token widerrufen wurde).

**Lösung:**
1. Gehe zu **Quellen**.
2. Klicke auf **Trennen** beim betroffenen Konnektor.
3. Klicke erneut auf **Verbinden** und durchlaufe den OAuth-Flow.
4. Danach startet ein neuer Sync automatisch.

> **Tipp:** Bei Google Calendar und Zoom werden Tokens automatisch über Refresh-Tokens erneuert. Falls dies fehlschlägt, wurde die Berechtigung möglicherweise in den Provider-Einstellungen widerrufen (z. B. unter https://myaccount.google.com/permissions).

---

### Sync-Fehler

**Symptom:** Der Sync bricht ab oder zeigt eine Fehlermeldung an.

**Mögliche Ursachen und Lösungen:**

| Fehler                          | Ursache                                  | Lösung                                                |
| ------------------------------- | ---------------------------------------- | ----------------------------------------------------- |
| *Token expired*                 | OAuth-Token abgelaufen                   | Konnektor trennen und neu verbinden                   |
| *Rate limit exceeded*           | Zu viele API-Anfragen                    | 15 Minuten warten, Sync wiederholt sich automatisch   |
| *Vault path not found*          | Obsidian-Pfad ungültig                   | Vault-Pfad in den Konnektor-Einstellungen korrigieren |
| *Connection timeout*            | Provider-API nicht erreichbar            | Internetverbindung prüfen, später erneut versuchen    |
| *Insufficient permissions*      | Fehlende Berechtigung beim Provider      | Konnektor trennen, neu verbinden mit korrekten Scopes |

**Generelles Vorgehen bei Sync-Fehlern:**
1. Prüfe den Fehlerstatus auf der Konnektoren-Seite.
2. PWBS versucht automatisch bis zu 3 Retries (mit Exponential Backoff: 1 Min  5 Min  25 Min).
3. Falls der Fehler bestehen bleibt: Konnektor trennen und neu verbinden.

---

### Leere Briefings

**Symptom:** Das Briefing enthält keinen oder nur minimalen Inhalt.

**Ursache 1: Noch keine Daten importiert**
- Prüfe auf der Konnektoren-Seite, ob mindestens ein Konnektor den Status  *Aktiv* hat.
- Prüfe die Dokumentenanzahl  werden 0 Dokumente angezeigt, ist der Sync noch nicht abgeschlossen.

**Ursache 2: Keine relevanten Daten für den Zeitraum**
- Das Morgenbriefing basiert auf den Terminen des aktuellen Tages und aktuellen Aktivitäten.
- An einem leeren Kalendertag ohne neue Notion-Updates kann das Briefing entsprechend kürzer ausfallen.

**Ursache 3: Embeddings noch nicht generiert**
- Nach dem ersten Import dauert die Verarbeitung (Chunking, Embedding, Entitätserkennung) einige Minuten.
- Warte 25 Minuten nach dem ersten Sync und lade das Dashboard dann neu.

**Lösung:**
1. Verbinde mindestens 2 Datenquellen für reichhaltigere Briefings.
2. Warte nach dem ersten Sync 5 Minuten.
3. Lade das Dashboard neu oder fordere ein neues Briefing manuell an.

---

## Glossar

| Begriff              | Erklärung                                                                                     |
| -------------------- | --------------------------------------------------------------------------------------------- |
| **Briefing**         | KI-generierte Zusammenfassung deiner Informationen für einen bestimmten Kontext oder Zeitraum |
| **Konnektor**        | Anbindung an eine externe Datenquelle (Google Calendar, Notion, Zoom, Obsidian)              |
| **Entität**          | Vom System erkanntes Objekt: Person, Projekt, Thema oder Entscheidung                         |
| **Knowledge Graph**  | Netzwerk aus Entitäten und ihren Beziehungen  die Wissensbasis hinter den Briefings          |
| **Embedding**        | Numerische Darstellung eines Textes, die seine Bedeutung erfasst  Grundlage der Suche       |
| **Sync**             | Abgleich zwischen einer externen Datenquelle und der PWBS-Datenbank                          |
| **UDF**              | Unified Document Format  internes Standardformat, in das alle Rohdaten normalisiert werden   |
| **RAG**              | Retrieval Augmented Generation  KI-Antworten basieren ausschließlich auf abgerufenen Daten   |
| **DEK**              | Data Encryption Key  persönlicher Verschlüsselungsschlüssel pro Nutzer                      |
| **OAuth2**           | Standardisiertes Autorisierungsprotokoll für den sicheren Zugriff auf Drittanbieter-APIs      |
| **Watermark/Cursor** | Zeitstempel des letzten erfolgreichen Syncs  sorgt für inkrementelle Updates                 |

---

## Weiterführende Links

- [API-Dokumentation (OpenAPI)](../api/openapi.json)  Vollständige REST-API-Spezifikation
- [Postman-Collection](../api/pwbs-collection.json)  Importierbar für API-Tests
- [Datenschutzkonzept](../../DSGVO.md)  DSGVO-Compliance und Datenverarbeitung
- [Architektur-Übersicht](../../ARCHITECTURE.md)  Technische Architektur des Systems
