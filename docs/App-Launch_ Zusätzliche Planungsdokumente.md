# **1\. Kurzfazit**

Der Übergang von einer abgeschlossenen technischen Implementierung hin zu einem erfolgreichen, öffentlichen Launch ist in der professionellen Softwareentwicklung eine der kritischsten Phasen. Wenn eine Applikation auf technischer Ebene vollständig codiert ist (häufig als "Code Complete" bezeichnet), die Organisation jedoch noch nicht auf die Veröffentlichung vorbereitet ist, manifestiert sich eine signifikante Lücke in der "Organizational Readiness".1 In dieser Phase fehlen in der Regel keine weiteren Implementierungsartefakte oder Architekturdokumente. Vielmehr mangelt es an Planungs- und Steuerungsdokumenten, die den operativen Betrieb, die rechtliche Absicherung, die systematische Vermarktung und die Erfolgsmessung orchestrieren.

In professionellen Produktorganisationen, die beispielsweise nach den Prinzipien des "Product Operating Models" der Silicon Valley Product Group (SVPG) arbeiten, wird scharf zwischen der Produktspezifikation (der Definition der Lösung) und der Go-to-Market- sowie Betriebsplanung (der Einführung und Überwachung im Markt) getrennt.2 Ein technisch fertiges Produkt bedeutet lediglich, dass ein Artefakt existiert; es bedeutet nicht, dass das Unternehmen in der Lage ist, dieses Produkt sicher zu betreiben, rechtlich abzusichern, Support-Anfragen effizient zu bearbeiten oder den initialen Wertbeitrag gegenüber dem Endnutzer klar zu kommunizieren.1 Fehlen diese nachgelagerten Steuerungsdokumente, kommt es regelmäßig zu unkoordinierten Releases, in denen das Marketingkampagnen-Timing nicht mit der Bereitstellung übereinstimmt, rechtliche Risiken übersehen werden oder das Produktteam blind agiert, da die Telemetrie nicht an strategischen Geschäftszielen ausgerichtet wurde.7

Um diese Lücke professionell zu schließen, müssen spezifische Dokumenttypen etabliert werden, die den gewünschten Release-Zustand definieren und klare Handlungsanweisungen für alle beteiligten Disziplinen liefern. Die wichtigsten fünf bis zehn Dokumente in dieser Phase umfassen:

1. **Go-to-Market Plan (GTM Plan):** Das operative Handbuch, das Zielgruppen, Positionierung, Pricing und Vertriebskanäle für das spezifische Release detailliert definiert und orchestriert.10  
2. **Product Launch Brief:** Ein taktisches Koordinationsdokument, das als "Single Source of Truth" für alle funktionsübergreifenden Stakeholder (Marketing, Support, Legal, Engineering) dient und Verantwortlichkeiten sowie Zeitpläne bis zur General Availability (GA) festlegt.2  
3. **Analytics Tracking Plan:** Ein präzises Spezifikationsdokument, das strategische Key Performance Indicators (KPIs) in konkrete Nutzerflüsse und schließlich in spezifische Telemetrie-Events übersetzt, die vor dem Launch in den Code integriert werden müssen.7  
4. **UX Audit Report & First Run Experience (FRE) Specification:** Dokumente zur formalisierten Evaluierung der Usability und zur bewussten Gestaltung des Onboarding-Erlebnisses, um die "Time-to-Value" für neue Nutzer drastisch zu reduzieren.12  
5. **Release Readiness Gate (Go/No-Go Checklist):** Ein formaler Kriterienkatalog, der vor dem finalen Deployment abgearbeitet wird und Aspekte wie Systemstabilität, Datenmigration, Security und User Acceptance Testing (UAT) abprüft.15  
6. **Legal & Compliance Checklist:** Eine systematische Dokumentation zur Sicherstellung zwingender rechtlicher Vorgaben wie der Datenschutz-Grundverordnung (DSGVO), dem Digitale-Dienste-Gesetz (DDG) und potenziell dem EU AI Act, um rechtliche Konsequenzen zu vermeiden.17  
7. **Support & Operations Plan:** Ein Betriebshandbuch, das Service-Level-Ziele (SLOs) definiert und Support-Teams mit den notwendigen Ressourcen, Eskalationspfaden und Makros ausstattet.20  
8. **Incident Response Plan:** Ein Notfallprotokoll, das Reaktionspfade und Eindämmungsmaßnahmen für kritische Systemausfälle oder Datenlecks nach dem Launch festlegt.22

Diese Dokumente transformieren ein reines Software-Artefakt in ein marktfähiges, betreubares und messbares Produkt.

# **2\. Dokumentlandkarte**

Die folgende tabellarische Übersicht ordnet die zentralen Dokumente für die Launch-Vorbereitung systematisch ein. Sie verdeutlicht die direkten Abhängigkeiten, die verantwortlichen Rollen sowie die Einordnung in den prozessualen und strategischen Kontext.

| Dokumentname | Primärer Zweck | Typische Inhalte | Input (Voraussetzungen) | Output / Abgeleitete Tasks | Verantwortliche Rolle | Typ & Zeitpunkt | Priorität |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **GTM\_PLAN.md** | Operative Definition der Markteinführung und des Vertriebs. | Ideal Customer Profile (ICP), Value Proposition, Pricing, Marketing Channels, 90-Tage-Timeline. | VISION.md, ROADMAP.md, PRD\_SPEC.md | Marketing-Kampagnen, Sales-Material, Setup der Vertriebskanäle. | Product Marketing Manager / Product Manager | Taktisch/Operativ; 3-6 Monate vor Launch | Pflicht |
| **LAUNCH\_BRIEF.md** | Interne "Single Source of Truth" für die Launch-Koordination. | Executive Summary, Beta-Phasen, General Availability Timeline, Core Team RACI. | GTM\_PLAN.md, PRD\_SPEC.md | Interne Kommunikations-Tasks, Terminierung von Beta-Tests. | Product Manager | Taktisch; Start der Entwicklungsphase bis Launch | Pflicht |
| **TRACKING\_PLAN.md** | Übersetzung von KPIs in technische Telemetrie-Spezifikationen. | Event-Namen, Event Properties, User Properties, Trigger-Bedingungen. | PRD\_SPEC.md, GTM\_PLAN.md | Spezifische Tracking-Implementierungs-Tasks im Code, Setup von Analytics-Dashboards. | Product Manager / Data Analyst | Taktisch; Während der Entwicklungsphase | Pflicht |
| **UX\_AUDIT.md** | Formale Usability-Prüfung vor dem Launch zur Identifikation von Reibungspunkten. | Heuristische Evaluation, Accessibility-Prüfung, Identifizierte Usability-Hürden. | Technischer App-Prototyp / Staging-Umgebung | UI/UX-Refactoring-Tasks, Bug-Reports. | UX Researcher / Product Designer | Operativ; Nach "Code Complete" | Sinnvoll |
| **FRE\_SPEC.md** | Design und Spezifikation des "First Run Experience" (Onboarding). | User Journey des ersten Logins, Tooltips, Empty States, Value-Placemats. | PRD\_SPEC.md, UX\_AUDIT.md | Implementierungs-Tasks für Onboarding-Flows und Tooltip-Texte. | Product Designer / Product Manager | Taktisch; Späte Entwicklungsphase | Sinnvoll |
| **LEGAL\_COMPLIANCE.md** | Absicherung gegen rechtliche Risiken und Erfüllung von Plattform-Richtlinien. | DSGVO-Consent-Spezifikation, TDDDG/DDG-Impressum, AGB, System-Inventar (EU AI Act). | ARCHITECTURE.md, PRD\_SPEC.md | Erstellung von Rechtstexten, Implementierung von Consent-Bannern. | Legal Counsel / Product Owner | Strategisch/Operativ; Früh im Projekt, finalisiert vor Launch | Pflicht |
| **OPERATIONS\_PLAN.md** | Definition des laufenden Betriebs, der Überwachung und des Supports. | SLA/SLO-Definitionen, Support-Makros, Eskalationspfade, Runbooks. | ARCHITECTURE.md, PRD\_SPEC.md | Erstellung von Schulungsunterlagen, Konfiguration von Support-Tools (z.B. Zendesk). | Operations Lead / Support Lead | Taktisch; Vor den Beta-Phasen | Pflicht |
| **INCIDENT\_RESPONSE.md** | Notfallprotokoll zur Handhabung von Systemausfällen oder Sicherheitsvorfällen. | Tier-Klassifizierung, Verantwortlichkeiten, Kommunikationsrichtlinien, Containment-Strategien. | ARCHITECTURE.md, OPERATIONS\_PLAN.md | Setup von Alerting-Regeln (PagerDuty), Durchführung von Fallback-Tests. | Site Reliability Engineer (SRE) / SecOps | Operativ; Vor General Availability | Pflicht (skaliert) |
| **RELEASE\_READINESS.md** | Formaler Kriterienkatalog für die Go/No-Go-Entscheidung. | Security-Sign-off, QA-Sign-off, UAT-Status, Ops-Readiness, Rollback-Plan. | Alle Spezifikationen und Pläne | Finales Deployment, Freigabe an App Stores (General Availability). | Engineering Lead / Release Manager | Operativ; Unmittelbar vor dem Launch | Pflicht |
| **LAUNCH\_RETRO.md** | Strukturierte Auswertung des Produkterfolgs und der Teamprozesse post-Launch. | Evaluation der Launch-KPIs, Erfolge, Herausforderungen, Customer Feedback. | GTM\_PLAN.md, TRACKING\_PLAN.md | Iterations-Tasks für den nächsten Sprint, Prozessanpassungen. | Scrum Master / Product Manager | Taktisch; 1-4 Wochen nach dem Launch | Sinnvoll |

# **3\. Typische Ableitungskette**

In professionellen Produktorganisationen existiert eine strikte, logische Hierarchie, in der Dokumente nicht isoliert entstehen, sondern kaskadierend aus übergeordneten Entscheidungen abgeleitet werden.23 Wenn die technische Spezifikation (PRD\_SPEC.md) und die Architektur (ARCHITECTURE.md) stehen, verschiebt sich der Fokus von der *Lösungsfindung* (Solution Discovery) zur *Markt- und Betriebsbereitschaft* (Organizational Readiness). Dieser Prozess wird häufig durch Methodiken wie den "Stage-Gate-Prozess" strukturiert, bei dem an vordefinierten Kontrollpunkten (Gates) die Erfüllung spezifischer Dokumentations- und Qualitätskriterien geprüft wird, bevor die nächste Phase eingeleitet wird.25

Die Ableitungskette für den Launch verläuft typischerweise in vier aufeinander aufbauenden Phasen:

**Phase 1: Strategische Marktausrichtung und rechtliches Fundament (Das Fundament)**

Aus der VISION.md und der fertigen PRD\_SPEC.md wird primär der GTM\_PLAN.md (Go-to-Market Plan) abgeleitet. Dieser definiert, wem das fertige Produkt wie verkauft wird. Ohne dieses Dokument fehlt allen nachfolgenden taktischen Plänen der Fokus. Aus den im GTM-Plan formulierten Geschäftszielen ergeben sich direkt die Anforderungen an das Tracking: Der TRACKING\_PLAN.md wird erstellt, um genau die Metriken messbar zu machen, die der GTM-Plan als erfolgskritisch definiert hat. Parallel muss die rechtliche Realität über eine LEGAL\_COMPLIANCE.md abgesteckt werden, da dies fundamentale Auswirkungen auf das Daten-Tracking und die Funktionalität hat.

**Phase 2: Taktische Koordination und Nutzererlebnis (Die Ausgestaltung)**

Sobald die strategischen Parameter stehen, wird die Koordination der internen Teams über den LAUNCH\_BRIEF.md orchestriert. Dieses Dokument übersetzt den GTM-Plan in konkrete Meilensteine (Beta, GA) und Team-Zuweisungen. Parallel wird das Nutzererlebnis final für den Launch poliert: Ein UX\_AUDIT.md prüft den technischen Ist-Zustand gegen UX-Best-Practices. Daraus abgeleitet wird die FRE\_SPEC.md (First Run Experience), die definiert, wie Nutzer durch das Onboarding geführt werden, um die im GTM-Plan versprochene Value Proposition sofort erlebbar zu machen.

**Phase 3: Operative Vorbereitung von Betrieb und Risiko (Die Absicherung)**

Während das Marketing die Kampagnen vorbereitet, müssen die technischen und administrativen Teams den Betrieb sichern. Aus der Architektur und den erwarteten Nutzerzahlen des GTM-Plans wird der OPERATIONS\_PLAN.md abgeleitet. Für den Fall, dass die hier definierten Service Level Objectives (SLOs) gerissen werden, wird der INCIDENT\_RESPONSE.md spezifiziert, der exakt regelt, wer bei einem Ausfall alarmiert wird und wie die Kommunikation verläuft.

**Phase 4: Readiness-Gates und Ausführung (Die Exekution)**

Unmittelbar vor dem Launch fließen alle Stränge in der RELEASE\_READINESS.md zusammen. Dies ist ein rein operativer Checklisten-Mechanismus, der abprüft, ob alle vorherigen Pläne erfüllt sind (z.B. Tracking implementiert? Legal-Texte online? Support geschult?). Ist dies der Fall, erfolgt der Launch. Nach dem Launch schließt sich der Kreis mit der LAUNCH\_RETRO.md, in der die Daten aus dem Tracking-Plan ausgewertet und neue Tasks für die nächste Iteration generiert werden.

Die logische Flussrichtung stellt sich tabellarisch wie folgt dar:

| Ebene | Dokument / Artefakt | Funktion im Prozess |
| :---- | :---- | :---- |
| **1\. Ausgangsbasis** | PRD\_SPEC.md & ARCHITECTURE.md | Definiert, was technisch existiert. |
| **2\. Strategische Pläne** | GTM\_PLAN.md & LEGAL\_COMPLIANCE.md | Definiert, wie und unter welchen Bedingungen das Produkt den Markt betritt. |
| **3\. Abgeleitete Spezifikationen** | TRACKING\_PLAN.md, FRE\_SPEC.md, OPERATIONS\_PLAN.md, INCIDENT\_RESPONSE.md | Übersetzt die Strategie in konkrete Anforderungen an Telemetrie, UX, Support und Notfall-Infrastruktur. |
| **4\. Taktische Koordination** | LAUNCH\_BRIEF.md | Orchestriert alle Teams entlang einer Zeitachse bis zur Freigabe. |
| **5\. Operatives Gate** | RELEASE\_READINESS.md | Prüft die Erfüllung aller Spezifikationen vor dem Go-Live. |
| **6\. Konkrete Tasks** | Jira/Linear-Tickets | Ausführung der identifizierten To-dos. |
| **7\. Post-Launch** | LAUNCH\_RETRO.md | Bewertet den Erfolg und speist Erkenntnisse in künftige Planungen ein. |

# **4\. Detaillierte Analyse je Dokument**

Im Folgenden werden die kritischen Dokumenttypen für die Launch-Phase tiefgreifend analysiert. Es wird strikt zwischen den Dimensionen Produkt/Koordination, Vermarktung, Nutzererlebnis, Analytics und Betrieb/Risiko getrennt.

## **4.1. Dokumente für Produktdefinition und Koordination**

Obwohl die Produktdefinition primär durch das Product Requirements Document (PRD\_SPEC.md) abgedeckt ist, bedarf es in der Phase vor dem Launch eines übergreifenden Koordinationsdokuments, das den technischen Fokus verlässt und die organisatorische Synchronisation in den Mittelpunkt stellt.

## **LAUNCH\_BRIEF.md (Product Launch Brief)**

Der Product Launch Brief fungiert als die zentrale, taktische "Single Source of Truth" für die Einführungsphase eines Produkts oder signifikanten Features. Während technische Spezifikationen detailliert beschreiben, wie ein System operiert, abstrahiert der Launch Brief diese Informationen, um sicherzustellen, dass funktionsübergreifende Teams – von Marketing über Sales bis hin zum Support – einheitlich und termingerecht agieren.2 Nach den Praktiken etablierter Organisationen wie Pendo oder Intercom dient dieses Dokument dazu, den Prozess von der Beta-Phase bis zur General Availability (GA) transparent zu orchestrieren.2

Die Bedeutung dieses Dokuments in der Vor-Launch-Phase kann nicht überbetont werden. Ohne einen Launch Brief verfallen Organisationen häufig in Silodenken: Entwickler schalten Funktionen frei, ohne dass das Support-Team geschult wurde, oder Marketingkampagnen verweisen auf Features, die noch in der Qualitätssicherung feststecken.27 Der Launch Brief verhindert diese Diskrepanzen durch klare Zuweisung von Rollen und Abhängigkeiten.

| Attribut | Spezifikation |
| :---- | :---- |
| **Zweck** | Taktische Koordination aller beteiligten Disziplinen und Sicherstellung des Informationsflusses. |
| **Zeitpunkt / Typ** | Erstellung parallel zur späten Entwicklungsphase; Taktisches Dokument. |
| **Verantwortlichkeit** | Product Manager / Product Marketing Manager. |
| **Typische Kapitel** | \- Executive Summary (TL;DR des Features und des Zielpublikums) \- Launch Level (Klassifizierung der Wichtigkeit, z.B. Tier 1 vs. Tier 3\) \- Customer Impact Assessment (Anzahl der betroffenen Nutzer/Accounts) \- Beta-Program-Phasen & spezifische Ziele \- Timeline für General Availability (GA) \- Core Team RACI-Matrix (Zuständigkeiten).2 |
| **Abhängigkeiten** | Extrahiert und referenziert Kerninformationen aus der PRD\_SPEC.md und dem GTM\_PLAN.md. |
| **Risiken bei Fehlen** | Desynchronisation der Teams; Support-Chaos bei Kundenanfragen zu unangekündigten Features; Verpasste Kommunikationsfenster. |
| **Abgeleitete Tasks** | Terminierung von internen Enablement-Meetings (Schulungen); Vorbereitung der Beta-Nutzer-Kommunikation; Zuweisung von QA-Ressourcen für spezifische Testläufe. |

## **4.2. Dokumente für Launch und Vermarktung**

Die rein technische Bereitstellung einer Applikation garantiert keine Marktdurchdringung. Die strategische und operative Vorbereitung der Markteinführung erfordert dedizierte Planungsdokumente, die den Übergang von der Produktentwicklung zur Nachfragegenerierung strukturieren.

## **GTM\_PLAN.md (Go-to-Market Plan)**

Der Go-to-Market Plan ist der konkrete, zeitgebundene operative Bauplan, der die übergeordnete Unternehmensstrategie in ausführbare Handlungen für ein spezifisches Release in einem definierten Markt übersetzt.10 Es ist zwingend erforderlich, zwischen einer langfristigen GTM-Strategie (die oft 12 bis 24 Monate umfasst) und dem GTM-Plan zu unterscheiden, der typischerweise als 90-Tage-Playbook fungiert und exakt spezifiziert, wer was bis wann tun muss, um das Produkt erfolgreich zu positionieren.10

In dieser Phase ist der GTM-Plan essenziell, da er die Brücke zwischen dem Produktwert und dem Endkunden schlägt. Das Dokument definiert das Ideal Customer Profile (ICP), formuliert die Value Proposition aus der Perspektive des Kunden und legt fest, über welche Distributionskanäle das Produkt vertrieben wird.10 Ohne diese fundierte Planung drohen Marketingbudgets ineffizient eingesetzt zu werden, da Botschaften nicht mit den tatsächlichen Schmerzpunkten der Zielgruppe resonieren oder das Pricing nicht an die Zahlungsbereitschaft angepasst ist.1

| Attribut | Spezifikation |
| :---- | :---- |
| **Zweck** | Ausrichtung aller kundenorientierten Funktionen auf eine kohärente Vermarktungs- und Vertriebsstrategie. |
| **Zeitpunkt / Typ** | 3-6 Monate vor Launch; Operativ/Taktisches Dokument. |
| **Verantwortlichkeit** | Product Marketing Manager / RevOps Lead. |
| **Typische Kapitel** | \- Target Market & Ideal Customer Profile (ICP) \- Problem Definition & Value Proposition \- Competitive Landscape (Wettbewerbsanalyse) \- Offering & Pricing (Verpackung und Preisstrategie) \- Distribution & Sales Model \- Marketing Channels & Campaigns \- Budget-Allokation \- Timeline (T-90 bis T+90).10 |
| **Abhängigkeiten** | Baut auf den funktionalen Versprechen der PRD\_SPEC.md auf und diktiert die Erfolgskennzahlen für den TRACKING\_PLAN.md. |
| **Risiken bei Fehlen** | Schwache Marktresonanz; Fehlallokation von Marketingbudgets; Unklare Positionierung gegenüber Wettbewerbern; Diskrepanz zwischen Produktfähigkeiten und Verkaufsversprechen. |
| **Abgeleitete Tasks** | Erstellung von Copywriting für App Stores und Landingpages; Setup von Advertising-Kampagnen (z.B. Google Ads, Social Media); Konfiguration von Pricing-Tiers in Billing-Systemen (wie Stripe). |

## **4.3. Dokumente für Nutzererlebnis / UX**

Wenn der technische Unterbau steht, rückt die Qualität der Interaktion in den Vordergrund. Die ergonomische und psychologische Ausgestaltung der Benutzeroberfläche entscheidet maßgeblich über Aktivierungs- und Bindungsraten.

## **UX\_AUDIT.md (UX Audit Report)**

Ein UX Audit Report ist das Resultat einer systematischen, expertengetriebenen Evaluierung der Benutzeroberfläche und der Interaktionsflüsse vor dem öffentlichen Launch. Er nutzt etablierte Frameworks, wie beispielsweise die 10 Usability-Heuristiken von Jakob Nielsen (z.B. Sichtbarkeit des Systemstatus, Konsistenz, Fehlervermeidung), um strukturelle Mängel zu identifizieren, die über rein funktionale Bugs hinausgehen.12 Laut etablierten Methoden, wie sie etwa von der Plattform Maze propagiert werden, umfasst ein solcher Audit typischerweise Phasen der heuristischen Evaluation, der Analyse der Informationsarchitektur und potenziell unmoderierte Usability-Tests.12

Die Relevanz in dieser Projektphase ergibt sich aus der Tatsache, dass Entwickler und Produktmanager häufig "betriebsblind" gegenüber der eigenen Applikation werden. Ein formalisiertes Audit deckt auf, wo Nutzer kognitiv überlastet werden, wo Accessibility-Standards missachtet wurden oder wo das Design-System inkonsistent angewendet wurde. Das Dokument transformiert vage "Gefühle" bezüglich der Bedienbarkeit in objektivierbare, priorisierte Handlungsempfehlungen.

| Attribut | Spezifikation |
| :---- | :---- |
| **Zweck** | Objektive Identifikation und Priorisierung von Usability-Problemen und Barrierefreiheits-Mängeln. |
| **Zeitpunkt / Typ** | Nach Fertigstellung eines funktionalen Prototyps / Staging-Deployments; Operativ. |
| **Verantwortlichkeit** | UX Researcher / Senior Product Designer. |
| **Typische Kapitel** | \- Project Scope & Objectives \- Methodologie (z.B. Heuristische Evaluation, Usability Testing) \- Findings & Results (Identifizierte Reibungspunkte inkl. Schweregrad) \- UI/UX Analysis (Typografie, Kontraste, Ladezeiten, Fehlerbehandlung) \- Actionable Recommendations (Priorisierte Empfehlungen zur Behebung).12 |
| **Abhängigkeiten** | Evaluierung des aktuellen technischen Standes auf Basis der in der PRD\_SPEC.md definierten User Flows. |
| **Risiken bei Fehlen** | Hohe Absprungraten durch frustrierende Nutzererfahrungen; Erhöhtes Aufkommen von Support-Tickets wegen Verständnisschwierigkeiten; Nicht-Erfüllung von Accessibility-Standards. |
| **Abgeleitete Tasks** | Redesign-Tickets für spezifische Screens; Überarbeitung von Fehlermeldungen (Microcopy); Anpassung von Farbkontrasten zur Erfüllung von WCAG-Richtlinien. |

## **FRE\_SPEC.md (First Run Experience Specification)**

Die First Run Experience (FRE) beschreibt sämtliche Interaktionen und emotionalen Eindrücke eines Nutzers während der allerersten Nutzung der Applikation nach der Registrierung. Die FRE-Spezifikation dokumentiert gezielt, wie dieser initiale Kontaktpunkt gestaltet wird, um die "Time-to-Value" zu minimieren.13 Während technische Spezifikationen oft vom Idealzustand eines gefüllten Systems ausgehen, adressiert die FRE-Spezifikation explizit den "Empty State" (den leeren Zustand ohne Nutzerdaten).

Ein wirkungsvolles FRE-Design ist datengetrieben und fokussiert sich auf die wesentlichen Handlungen, die ein Nutzer ausführen muss, um den Kernwert des Produkts zu begreifen.14 Es spezifiziert den Einsatz von Onboarding-Carousels, progressiven Profilvervollständigungen und kontextuellen Tooltips. Ohne dieses Dokument werden Nutzer nach dem Login häufig allein gelassen, was zu massiven Einbrüchen in der Retention-Rate führt.

| Attribut | Spezifikation |
| :---- | :---- |
| **Zweck** | Gezielte Gestaltung des Onboardings zur Maximierung der initialen Nutzeraktivierung und Retention. |
| **Zeitpunkt / Typ** | Späte Entwicklungsphase; Taktisch/Operativ. |
| **Verantwortlichkeit** | Product Designer / Product Manager. |
| **Typische Kapitel** | \- Onboarding Objectives (Kernaktionen, die der Nutzer ausführen soll) \- Value Placemat / Carousel Logic (Willkommens-Design und Kernbotschaften) \- Empty State Designs (Gestaltung von Dashboards ohne Daten) \- Progress Indicators & Gamification-Elemente \- Skip & Exit Logic (Flexibilität für erfahrene Nutzer).13 |
| **Abhängigkeiten** | Integriert Feedback aus dem UX\_AUDIT.md und referenziert die im GTM\_PLAN.md definierte Value Proposition. |
| **Risiken bei Fehlen** | Nutzer verstehen den Wert der App nicht sofort und deinstallieren sie umgehend; Hohe Abbrecherquoten im Registrierungsprozess. |
| **Abgeleitete Tasks** | Implementierung von Welcome-Screens; Schreiben von Texten für Tooltips; Programmierung von Initialdaten ("Dummy-Daten"), um Empty States zu vermeiden. |

## **4.4. Dokumente für Analytics und Erfolgsmessung**

Die objektive Beurteilung eines Software-Launches erfordert präzise Telemetrie. Die Definition dieser Metriken muss strukturiert erfolgen, bevor der Code finalisiert wird, um eine konsistente Datenqualität sicherzustellen.

## **TRACKING\_PLAN.md (Analytics Tracking Plan)**

Ein Tracking Plan ist ein zentralisiertes, fortlaufend gepflegtes Dokument ("Living Document"), das die Informationsbasis für jegliche datengetriebene Produktentscheidung bildet. Er fungiert als Übersetzer zwischen übergeordneten geschäftlichen Key Performance Indicators (KPIs) und der konkreten technischen Implementierung von Telemetrie-Events im Codecode.7 Etablierte Methodiken, wie sie von Mixpanel oder Amplitude empfohlen werden, verlangen, dass Geschäftsziele identifiziert, in spezifische User Flows gemappt und schließlich in klar definierte Events (Aktionen) und Properties (Kontext) zerlegt werden.7

In der Vor-Launch-Phase ist dieses Dokument unverzichtbar, da ein unstrukturierter Einbau von Tracking-Codes (das sogenannte "Track-Everything"-Antipattern) zu einem unbrauchbaren Datensumpf führt, der spätere Analysen erschwert oder unmöglich macht.7 Der Plan etabliert verbindliche Namenskonventionen (z.B. das Object-Action-Framework wie Button\_Clicked) und definiert exakt, unter welchen technischen Bedingungen ein Event gefeuert wird.

| Attribut | Spezifikation |
| :---- | :---- |
| **Zweck** | Standardisierung und Dokumentation der Datenerfassung zur Sicherstellung der analytischen Integrität. |
| **Zeitpunkt / Typ** | Während der Implementierungsphase, zwingend vor Release; Operativ. |
| **Verantwortlichkeit** | Product Manager / Data Analyst. |
| **Typische Kapitel** | \- Business Goals & prioritäres KPI-Mapping \- Event Dictionary (Event-Name, Beschreibung, Trigger-Bedingung) \- Property Dictionary (Globale vs. Event-spezifische Eigenschaften) \- Naming Conventions & Taxonomie-Regeln \- QA- und Validierungs-Prozesse für Tracking-Code.7 |
| **Abhängigkeiten** | Leitet sich aus den Erfolgskriterien des GTM\_PLAN.md und den Features der PRD\_SPEC.md ab. |
| **Risiken bei Fehlen** | Verlust kritischer Daten zum Nutzerverhalten unmittelbar nach dem Launch; Inkonsistente Metriken, die keine verlässlichen Geschäftsentscheidungen zulassen. |
| **Abgeleitete Tasks** | Implementierung der SDK-Methoden im Frontend- und Backend-Code; Setup von Conversion-Funnels und Retention-Dashboards in Analytics-Tools; QA-Testing der Event-Trigger. |

## **LAUNCH\_RETRO.md (Post-Launch Evaluation & Retrospective)**

Die Post-Launch Evaluation ist ein strukturierter Rahmen zur Analyse der Projektergebnisse nach erfolgtem Release. Sie institutionalisiert den kontinuierlichen Verbesserungsprozess, indem sie den Erfolg des Produktlaunches anhand der vorab definierten Metriken bewertet und die Teamleistung reflektiert.31 Formate wie das "4 L's"-Modell (Liked, Learned, Lacked, Longed for) oder iterative Scrum-Retrospektiven dienen dazu, sowohl technische, geschäftliche als auch prozessuale Erkenntnisse zu sichern.33

Die Planung dieses Dokuments vor dem Launch ist relevant, da es die Erwartungshaltung etabliert, dass ein Release nicht das Ende, sondern der Beginn eines neuen Iterationszyklus ist. Es zwingt Teams dazu, qualitative Daten (Kundenfeedback, Support-Tickets) und quantitative Daten (Analytics) zu synthetisieren, um fundierte Entscheidungen für die zukünftige ROADMAP.md zu treffen.35

| Attribut | Spezifikation |
| :---- | :---- |
| **Zweck** | Systematische Auswertung des Launches zur Generierung von Action Items für zukünftige Sprints. |
| **Zeitpunkt / Typ** | Vorbereitet vor Launch, durchgeführt 1-4 Wochen nach Launch; Taktisch. |
| **Verantwortlichkeit** | Scrum Master / Product Manager. |
| **Typische Kapitel** | \- Executive Summary des Launch-Erfolgs \- KPI Evaluation (Soll/Ist-Vergleich der Tracking-Daten) \- What Went Well & Challenges Faced (Prozess-Evaluierung) \- Customer Feedback Synthesis (Zusammenfassung von Nutzerstimmen) \- Action Items & Recommendations.31 |
| **Abhängigkeiten** | Benötigt die Daten aus dem TRACKING\_PLAN.md und bewertet die Ziele des GTM\_PLAN.md. |
| **Risiken bei Fehlen** | Wiederholung prozessualer Fehler in zukünftigen Projekten; Mangelnde Anpassung der Produktstrategie trotz vorliegender Nutzerdaten; Fehlende Würdigung von Teamerfolgen. |
| **Abgeleitete Tasks** | Generierung neuer Tickets im Backlog zur Fehlerbehebung oder Feature-Verbesserung; Aktualisierung von internen Prozess-Richtlinien. |

## **4.5. Dokumente für Betrieb, Support, Risiko und Compliance**

Die Transition von einer Entwicklungsumgebung in den Live-Betrieb erfordert strikte Governance, rechtliche Absicherung und vorbereitete Notfallmechanismen, um die Integrität des Systems und des Unternehmens zu schützen.

## **OPERATIONS\_PLAN.md (inkl. SLAs, SLOs und Support)**

Der Operations Plan regelt den Übergang der Software in den stabilen Alltagsbetrieb. Er definiert die Qualitätsstandards für die Dienstbereitstellung und legt fest, wie die Organisation die Applikation überwacht und wie sie mit Endkunden interagiert.20 Ein zentraler Bestandteil ist die Definition von Service-Level-Agreements (SLAs), Service-Level-Objectives (SLOs) und Service-Level-Indicators (SLIs).21 Während SLAs vertragliche, externe Zusicherungen sind (deren Bruch finanzielle Konsequenzen haben kann), sind SLOs strengere, interne Zielvorgaben für Parameter wie Verfügbarkeit (Uptime) oder Latenz. Die Einhaltung dieser SLOs wird durch die Messung der SLIs überprüft.21

In der Vor-Launch-Phase ist dieser Plan kritisch, um sicherzustellen, dass die Applikation nicht nur funktioniert, sondern auch messbar performt. Zudem rüstet der Plan das Support-Team aus. Eine App ohne vorbereitete Support-Pfade (z.B. FAQ-Artikel, Zendesk-Makros) führt unweigerlich zu Frustration auf Seiten der Nutzer und zur Überlastung der internen Ressourcen.20

| Attribut | Spezifikation |
| :---- | :---- |
| **Zweck** | Etablierung von Betriebsparametern, Überwachungsmechanismen und Support-Prozessen. |
| **Zeitpunkt / Typ** | Vor den Beta-Phasen finalisiert; Taktisch/Operativ. |
| **Verantwortlichkeit** | Operations Lead / Support Lead / SRE. |
| **Typische Kapitel** | \- SLO-, SLI- und SLA-Definitionen inkl. Error Budgets \- Support-Levels & Erreichbarkeitszeiten (z.B. 8/5 vs. 24/7) \- Support Request Procedures & Eskalationspfade \- Monitoring- und Alerting-Konfiguration \- Basis-FAQ und Runbooks für wiederkehrende Anfragen.20 |
| **Abhängigkeiten** | Basiert auf der Infrastruktur der ARCHITECTURE.md und den Funktionalitäten der PRD\_SPEC.md. |
| **Risiken bei Fehlen** | Unklare Verantwortlichkeiten bei Performance-Einbrüchen; Überlastung des Supports; Verletzung vertraglicher Pflichten gegenüber Nutzern. |
| **Abgeleitete Tasks** | Konfiguration von Uptime-Monitoring (z.B. Datadog); Erstellung von Help-Center-Artikeln aus Entwickler-Notizen; Training der Customer-Success-Mitarbeiter. |

## **INCIDENT\_RESPONSE.md (Incident Response Plan)**

Ein Incident Response Plan (IRP) ist ein präskriptives Notfallprotokoll, das Organisationen anleitet, wie sie systematisch auf Sicherheitsvorfälle, Datenlecks oder kritische Systemausfälle reagieren. Besonders in modernen Cloud- und SaaS-Umgebungen, in denen die Verantwortung oft zwischen dem Unternehmen und Cloud-Service-Providern geteilt ist, ist ein maßgeschneiderter IRP zwingend.22 Gemäß Best Practices (etwa von Wiz oder SANS) untergliedert sich die Reaktion auf Vorfälle in klar definierte Phasen: Vorbereitung, Erkennung, Untersuchung, Eindämmung (Containment), Behebung (Eradication) und Nachbereitung.22

Das Dokument ist in dieser Phase von höchster Bedeutung, da ein Ausfall nach dem Launch eintreten *wird*. Ohne einen strukturierten Plan verschwenden Teams in Krisensituationen wertvolle Zeit mit der Suche nach Zuständigkeiten, Passwörtern oder Kommunikationsrichtlinien. Der IRP definiert Severity-Level (z.B. P1 für vollständigen Ausfall, P4 für geringfügige Anomalien) und regelt zwingende rechtliche Meldepflichten.22

| Attribut | Spezifikation |
| :---- | :---- |
| **Zweck** | Schadensminimierung und strukturierte Problembehebung bei kritischen Ausfällen oder Security-Breaches. |
| **Zeitpunkt / Typ** | Vor General Availability etabliert und getestet; Operativ (im Krisenfall). |
| **Verantwortlichkeit** | Site Reliability Engineer (SRE) / Chief Information Security Officer (CISO). |
| **Typische Kapitel** | \- Severity-Klassifizierung (P1 bis P4) \- Rollen im Krisenstab (Incident Commander, Communications Lead) \- Containment- & Eradication-Strategien (z.B. Workload-Isolation) \- Kommunikationsprotokolle (intern, Kunden, Behörden) \- Business Continuity und Disaster Recovery (BCDR) Sync.22 |
| **Abhängigkeiten** | Erweitert den OPERATIONS\_PLAN.md für Ausnahmesituationen; referenziert rechtliche Vorgaben der LEGAL\_COMPLIANCE.md. |
| **Risiken bei Fehlen** | Panik und unkoordinierte Reaktionen im Krisenfall; Verstöße gegen behördliche Meldepflichten bei Datenschutzvorfällen; Massiver Reputationsverlust. |
| **Abgeleitete Tasks** | Setup von PagerDuty-Eskalationsketten; Durchführung von "Tabletop Exercises" (Simulation von Ausfällen); Vorbereitung von Notfall-Templates für Statusseiten. |

## **LEGAL\_COMPLIANCE.md**

Die Legal & Compliance Checklist ist ein zentrales Dokument zur Erfassung, Prüfung und Sicherstellung aller regulatorischen, gesetzlichen und plattformspezifischen Anforderungen vor der Veröffentlichung einer Software.18 Die Rechtslage, insbesondere in Deutschland und der EU, hat sich massiv verdichtet. Neben der Datenschutz-Grundverordnung (DSGVO) müssen neue Regulatorien wie das Digitale-Dienste-Gesetz (DDG) für Impressumspflichten und der ab 2026 vollumfänglich greifende EU AI Act (sofern KI-Komponenten genutzt werden) zwingend beachtet werden.18

Rechtliche Compliance kann nicht nachträglich in eine Applikation integriert werden ("bolted on"); sie muss das fundamentale Systemdesign beeinflussen.46 Das Dokument dokumentiert, welche Daten auf welcher Rechtsgrundlage (Legal Basis) verarbeitet werden, welche Auftragsverarbeitungsverträge (AVV) mit Drittanbietern geschlossen wurden und wie Einwilligungen (Consent) technisch sauber eingeholt werden, bevor Tracking-SDKs feuern.17

| Attribut | Spezifikation |
| :---- | :---- |
| **Zweck** | Präventiver Schutz vor Abmahnungen, Bußgeldern und der Ablehnung in App-Stores durch Erfüllung rechtlicher Normen. |
| **Zeitpunkt / Typ** | Kontinuierlicher Prozess, finalisiert vor Code-Freeze; Strategisch/Operativ. |
| **Verantwortlichkeit** | Legal Counsel / Data Protection Officer (DPO) / Product Owner. |
| **Typische Kapitel** | \- Impressum & Anbieterkennzeichnung (DDG/TDDDG-konform) \- Datenschutzerklärung (spezifisch für App-Nutzung, keine Web-Kopien) \- Consent Management Spezifikation (Opt-in vor SDK-Initialisierung) \- Third-Party Vendor Inventory & AVV-Status \- AGB und Widerrufsbelehrungen (bei E-Commerce/In-App-Käufen) \- AI System Inventory & Risk Classification (gemäß EU AI Act).17 |
| **Abhängigkeiten** | Muss die Datenströme aus der ARCHITECTURE.md und dem TRACKING\_PLAN.md zwingend rechtlich legitimieren. |
| **Risiken bei Fehlen** | App-Store-Rejections wegen Privacy-Verstößen; Abmahnungen durch Mitbewerber; Erhebliche Bußgelder durch Datenschutzbehörden; Reputationsschäden. |
| **Abgeleitete Tasks** | Integration eines Consent Management Providers (CMP); Verfassen und Einbinden spezifischer Rechtstexte im App-Menü; Unterzeichnung ausstehender Auftragsverarbeitungsverträge. |

## **RELEASE\_READINESS.md (Go/No-Go Checklist)**

Das Release Readiness Dokument formalisiert den finalen Kontrollpunkt ("Stage-Gate"), bevor Software in die Produktionsumgebung überführt und der Öffentlichkeit zugänglich gemacht wird. Es manifestiert sich typischerweise als umfassende Checkliste, in der Service-Owner und funktionsübergreifende Stakeholder systematisch abprüfen, ob das Produkt alle definierten Qualitäts-, Sicherheits- und Betriebsstandards erfüllt.15 Frameworks wie der Production Readiness Review (PRR) Prozess von GitLab (PREP) zielen darauf ab, sicherzustellen, dass ausreichend Dokumentation, Observability und Stabilität für den Produktionsbetrieb vorhanden sind.49

Ohne ein solches Readiness-Gate verkommt die Freigabe zu einer subjektiven Ermessensentscheidung, die häufig durch zeitlichen Druck ("Launch-Fieber") korrumpiert wird. Die Checkliste zwingt die Organisation, harte Kriterien objektiv zu evaluieren und entweder die Freigabe zu erteilen, Ausnahmen mit Verfallsdatum zu dokumentieren oder den Launch zu verschieben.16

| Attribut | Spezifikation |
| :---- | :---- |
| **Zweck** | Objektive Risikominimierung unmittelbar vor dem Deployment durch Erzwingung einer gemeinsamen Definition von "Done". |
| **Zeitpunkt / Typ** | Wenige Tage bis Stunden vor dem geplanten Release; Operativ. |
| **Verantwortlichkeit** | Release Manager / Engineering Lead / Operations Manager. |
| **Typische Kapitel** | \- Code & Build Readiness (Code-Freeze eingehalten? QA Sign-off?) \- Security & Compliance Sign-off (Vulnerabilities geprüft?) \- Operations Readiness (Monitoring aktiv? Backups getestet?) \- Business Readiness (Legal-Texte online? Marketing ready?) \- Deployment, Rollback & Cutover Plan.15 |
| **Abhängigkeiten** | Das Meta-Dokument schlechthin: Es fragt die Erfüllung aller anderen in dieser Phase erstellten Spezifikationen und Pläne ab. |
| **Risiken bei Fehlen** | Einsatz von fehlerhafter Software in Produktion; Datenverluste bei Migrationen; Ausrollen von Features, für die der Support nicht trainiert wurde. |
| **Abgeleitete Tasks** | Formale Freigabe-Entscheidung (Sign-off) der Abteilungsleiter; Ausführung der finalen Deployment-Skripte; Aktivierung von Feature-Flags für Endnutzer. |

# **5\. Empfohlene Minimalstruktur für meinen Fall**

Unter der Prämisse, dass die Lösungs- und Architekturphase durch die bereits existierenden Dokumente (VISION.md, ARCHITECTURE.md, ROADMAP.md, PRD\_SPEC.md, TASKS.md) hervorragend abgedeckt ist, muss das Repository nun um jene Artefakte erweitert werden, die Steuerung, Qualitätssicherung, Recht und Markteinführung gewährleisten.

Es wird empfohlen, folgende Dateistruktur aufzubauen, um ein vollständiges, professionelles "Product Operating Model" abzubilden. Die Dateinamen folgen konsequent der existierenden Markdown-Konvention:

/planning

├── VISION.md (Vorhanden: Produktvision und Langzeitziele)

├── ROADMAP.md (Vorhanden: Zeitliche Priorisierung)

├── PRD\_SPEC.md (Vorhanden: Funktionale Anforderungen)

├── ARCHITECTURE.md (Vorhanden: Technische Systeme & Datenfluss)

├── TASKS.md (Vorhanden: Operatives Backlog)

│

├── GTM\_PLAN.md (NEU: Markteinführung, ICP, Positionierung, Pricing)

├── LAUNCH\_BRIEF.md (NEU: Koordination, Timeline, Stakeholder-RACI)

├── TRACKING\_PLAN.md (NEU: Definition der Telemetrie & Success Metrics)

├── UX\_AUDIT.md (NEU: Heuristische Evaluation der UI/UX)

├── FRE\_SPEC.md (NEU: Definition der Onboarding & First-Run-Experience)

├── LEGAL\_COMPLIANCE.md (NEU: DSGVO, DDG 2026, AGB, App-Store-Vorgaben)

├── OPERATIONS\_PLAN.md (NEU: Support-Makros, SLOs, Incident Response Basics)

└── RELEASE\_READINESS.md (NEU: Die finale Go/No-Go Checkliste vor dem Launch)

Diese Struktur integriert sich nahtlos und logisch. Die PRD\_SPEC.md liefert den funktionalen Input für die FRE\_SPEC.md (Wie wird das Feature dem Erstnutzer erklärt?). Die ARCHITECTURE.md liefert den technischen Input für die LEGAL\_COMPLIANCE.md (Welche SDKs verarbeiten personenbezogene Daten?). Der GTM\_PLAN.md definiert die Geschäftsziele, die im TRACKING\_PLAN.md technisch verankert werden. Die RELEASE\_READINESS.md stellt als letztes operatives Gate sicher, dass alle Aspekte aus den anderen Dateien abgearbeitet wurden, bevor die Freigabe zur Veröffentlichung erteilt wird. Für eine Erstveröffentlichung kann das oft separat geführte Notfallprotokoll pragmatisch als Unterkapitel in den OPERATIONS\_PLAN.md integriert werden, um Dokumenten-Overhead zu vermeiden.

# **6\. Priorisierte Empfehlung**

Um den Entwicklungsprozess in dieser kritischen Phase nicht durch überbordende Bürokratie zu lähmen, sollte die Erstellung der neuen Dokumente schrittweise und nach ihrer zeitlichen und operativen Dringlichkeit erfolgen.

**Phase 1: Fundament absichern (Als Nächstes erstellen)**

Diese drei Dokumente sind absolut kritisch für den rechtlichen Schutz, die Messbarkeit des Erfolgs und die interne Orchestrierung. Sie müssen finalisiert werden, bevor weiterer Code für Drittanbieter-Tools geschrieben oder Marketing-Aktivitäten gestartet werden.

1. **LEGAL\_COMPLIANCE.md**: Rechtliche Fehler bei einem öffentlichen App-Launch in Europa (insbesondere Verstöße gegen die DSGVO oder das DDG) können existenzbedrohend sein. Die Klärung von Consent-Management-Prozessen, Auftragsverarbeitungsverträgen und dem Impressum hat oberste Priorität, da sie oft architektonische Anpassungen (wie z.B. das Blockieren von SDKs vor dem Consent) erzwingen.  
2. **TRACKING\_PLAN.md**: Die Telemetrie muss konzipiert und in den Code implementiert werden, *bevor* die App gelauncht wird. Werden diese Spezifikationen erst kurz vor Release erstellt, verzögert sich das Go-Live durch technische Nacharbeiten erheblich, oder der Launch erfolgt ohne verlässliche Datenbasis.  
3. **LAUNCH\_BRIEF.md**: Es muss umgehend eine interne Orientierung geschaffen werden. Die Festlegung, wann Beta-Phasen enden und wer bis zur General Availability welche Aufgaben (Design-Polishing, Support-Setup, Marketing-Materialien) übernehmen muss, verhindert Engpässe.

**Phase 2: Markt und Nutzererlebnis optimieren (Danach folgen)**

Sobald die rechtliche Basis und die interne Zeitleiste verankert sind, verschiebt sich der Fokus auf den externen Erfolg der Applikation und die Verringerung der Reibung beim Endkunden.

4\. **GTM\_PLAN.md**: Die strategische und operative Planung, wie die App ihre Zielgruppe erreicht, wie sie bepreist wird und welche Distributionskanäle für den Launchtag bespielt werden, muss nun detailliert ausgearbeitet werden.

5\. **FRE\_SPEC.md**: (Idealerweise flankiert durch ein vorangegangenes schnelles UX\_AUDIT.md). Die Ausarbeitung des initialen Onboardings ist entscheidend. Ein Produkt kann technisch exzellent sein; wenn der Nutzer beim ersten Öffnen der App den Mehrwert nicht innerhalb weniger Sekunden begreift, wird die App unweigerlich deinstalliert.

6\. **RELEASE\_READINESS.md**: Der Aufbau der strikten Go/No-Go-Kriterienliste, die etwa zwei Wochen vor dem anvisierten Launch-Datum vorliegen muss, um systematisch von allen Disziplinen abgezeichnet zu werden.

**Phase 3: Skalierung und Evaluation (Später sinnvoll)**

Diese Dokumente können für den initialen Launch leichtgewichtig gehalten oder erst kurz nach dem Launch vollständig ausformuliert werden, wenn erste operative Erfahrungen vorliegen.

7\. **OPERATIONS\_PLAN.md**: Für den allerersten Launch einer neuen App reichen oft grundlegende Support-E-Mail-Adressen und Basis-Monitoring. Komplexe SLO/SLI-Konstrukte und vielschichtige Incident-Eskalationspfade werden in der Regel erst unternehmenskritisch, wenn eine signifikante Nutzerbasis oder zahlende Enterprise-Kunden erreicht sind. Das Notfallprotokoll (Incident Response) sollte in einer rudimentären Version Teil dieses Plans sein.

8\. **LAUNCH\_RETRO.md**: Wird naturgemäß erst ein bis vier Wochen nach dem Launch inhaltlich befüllt. Die strukturelle Vorlage sollte jedoch rechtzeitig bereitliegen, um die Erfassung des ersten echten Nutzer-Feedbacks und der Telemetrie-Daten systematisch und ohne Verzögerung zu kanalisieren.

#### **Referenzen**

1. Goals, Readiness and Constraints: The Three Dimensions of a Product Launch \- Pragmatic Institute, Zugriff am März 17, 2026, [https://www.pragmaticinstitute.com/resources/articles/product/goals-readiness-and-constraints-the-three-dimensions-of-product-launch/](https://www.pragmaticinstitute.com/resources/articles/product/goals-readiness-and-constraints-the-three-dimensions-of-product-launch/)  
2. Product launch brief template \- Pendo, Zugriff am März 17, 2026, [https://www.pendo.io/product-led/artifacts/product-launch-brief-template/](https://www.pendo.io/product-led/artifacts/product-launch-brief-template/)  
3. What is Product Marketing? (And How It Helps Build Products) \- Intercom, Zugriff am März 17, 2026, [https://www.intercom.com/blog/how-product-marketing-helps-build-product/](https://www.intercom.com/blog/how-product-marketing-helps-build-product/)  
4. Marty Cagan: Why Your Product Operating Model is Broken (Transformed Author & SVPG Partner) \- YouTube, Zugriff am März 17, 2026, [https://www.youtube.com/watch?v=zrGOIJzA2jM](https://www.youtube.com/watch?v=zrGOIJzA2jM)  
5. TRANSFORMED: Moving to the Product Operating Model with Marty Cagan (INSPIRED, EMPOWERED) \- YouTube, Zugriff am März 17, 2026, [https://www.youtube.com/watch?v=-uphJVVDlfE](https://www.youtube.com/watch?v=-uphJVVDlfE)  
6. Beginner's Guide to Product Launch | Readiness | by David Keith Daniels \- Medium, Zugriff am März 17, 2026, [https://brainkraft.medium.com/beginners-guide-to-product-launch-readiness-63cd8296b4ff](https://brainkraft.medium.com/beginners-guide-to-product-launch-readiness-63cd8296b4ff)  
7. Create A Tracking Plan \- Mixpanel Docs, Zugriff am März 17, 2026, [https://docs.mixpanel.com/docs/tracking-best-practices/tracking-plan](https://docs.mixpanel.com/docs/tracking-best-practices/tracking-plan)  
8. Product Success Metrics by ProductPlan, Zugriff am März 17, 2026, [https://assets.productplan.com/content/Product-Success-Metrics-by-ProductPlan.pdf](https://assets.productplan.com/content/Product-Success-Metrics-by-ProductPlan.pdf)  
9. Launch plan template guide 2026: run smoother product releases, Zugriff am März 17, 2026, [https://monday.com/blog/rnd/launching-plan-template/](https://monday.com/blog/rnd/launching-plan-template/)  
10. GTM Strategy: Complete Guide to Building a Winning Go-to-Market ..., Zugriff am März 17, 2026, [https://elefanterevops.com/blog/gtm-strategy-complete-guide-to-building-a-winning-go-to-market-plan](https://elefanterevops.com/blog/gtm-strategy-complete-guide-to-building-a-winning-go-to-market-plan)  
11. Event tracking plan template \- Amplitude, Zugriff am März 17, 2026, [https://amplitude.com/resources/event-tracking-plan-template](https://amplitude.com/resources/event-tracking-plan-template)  
12. UX audit checklist: 7 Steps to better UX | Maze, Zugriff am März 17, 2026, [https://maze.co/collections/ux-ui-design/ux-audit/](https://maze.co/collections/ux-ui-design/ux-audit/)  
13. First-run experience patterns for Office Add-ins \- Microsoft, Zugriff am März 17, 2026, [https://learn.microsoft.com/en-us/office/dev/add-ins/design/first-run-experience-patterns](https://learn.microsoft.com/en-us/office/dev/add-ins/design/first-run-experience-patterns)  
14. First-Run Experience: An Introduction | by Kavya Rastogi | Bootcamp | Medium, Zugriff am März 17, 2026, [http://medium.com/design-bootcamp/first-run-experience-an-introduction-e13f99d2b070](http://medium.com/design-bootcamp/first-run-experience-an-introduction-e13f99d2b070)  
15. Go/No Go Production Readiness Checklist \- ProjectManagement.com, Zugriff am März 17, 2026, [https://www.projectmanagement.com/checklists/777059/go-no-go-production-readiness-checklist](https://www.projectmanagement.com/checklists/777059/go-no-go-production-readiness-checklist)  
16. Production Readiness Review Checklist & Best Practices \- Cortex, Zugriff am März 17, 2026, [https://www.cortex.io/post/how-to-create-a-great-production-readiness-checklist](https://www.cortex.io/post/how-to-create-a-great-production-readiness-checklist)  
17. GDPR Compliance for Mobile Apps (2026 Guide) \- Secure Privacy, Zugriff am März 17, 2026, [https://secureprivacy.ai/blog/gdpr-compliance-mobile-apps](https://secureprivacy.ai/blog/gdpr-compliance-mobile-apps)  
18. Digitale-Dienste-Gesetz (DDG) \- Gesetze im Internet, Zugriff am März 17, 2026, [https://www.gesetze-im-internet.de/ddg/BJNR0950B0024.html](https://www.gesetze-im-internet.de/ddg/BJNR0950B0024.html)  
19. EU AI Act Compliance Checklist for Businesses in 2026 | Codebridge, Zugriff am März 17, 2026, [https://www.codebridge.tech/articles/the-eu-ai-act-compliance-checklist-ownership-evidence-and-release-control-for-businesses](https://www.codebridge.tech/articles/the-eu-ai-act-compliance-checklist-ownership-evidence-and-release-control-for-businesses)  
20. Support Plan Example, Zugriff am März 17, 2026, [https://www.well-architected-guide.com/documents/support-plan-example/](https://www.well-architected-guide.com/documents/support-plan-example/)  
21. SLA vs. SLO: Tutorial and Examples \- SolarWinds, Zugriff am März 17, 2026, [https://www.solarwinds.com/sre-best-practices/sla-vs-slo](https://www.solarwinds.com/sre-best-practices/sla-vs-slo)  
22. Incident Response Plans: Templates, Examples & Checklist | Wiz, Zugriff am März 17, 2026, [https://www.wiz.io/academy/detection-and-response/example-incident-response-plan-templates](https://www.wiz.io/academy/detection-and-response/example-incident-response-plan-templates)  
23. Product Development Process: 10 Stages Every Team Should Follow \- Aha\! software, Zugriff am März 17, 2026, [https://www.aha.io/roadmapping/guide/stages-of-product-development](https://www.aha.io/roadmapping/guide/stages-of-product-development)  
24. How to Build a Product Development Roadmap: A Complete Guide \- Planview, Zugriff am März 17, 2026, [https://www.planview.com/resources/articles/how-to-build-a-product-development-roadmap/](https://www.planview.com/resources/articles/how-to-build-a-product-development-roadmap/)  
25. Stage Gate Process: Phases, Gates & Templates \[2025\] \- Asana, Zugriff am März 17, 2026, [https://asana.com/resources/stage-gate-process](https://asana.com/resources/stage-gate-process)  
26. How to Use a Stage Gate Process Template: A Comprehensive Guide \- Cerri Project, Zugriff am März 17, 2026, [https://cerri.com/how-to-use-a-stage-gate-process-template-a-comprehensive-guide/](https://cerri.com/how-to-use-a-stage-gate-process-template-a-comprehensive-guide/)  
27. Product Launch Plan Template & Guide \- Hustle Badger, Zugriff am März 17, 2026, [https://www.hustlebadger.com/what-do-product-teams-do/product-launch-plan-template-examples-guide/](https://www.hustlebadger.com/what-do-product-teams-do/product-launch-plan-template-examples-guide/)  
28. Go-to-Market (GTM) strategy template \[Free\] \+ 2025 examples | Canva, Zugriff am März 17, 2026, [https://www.canva.com/resources/go-to-market-strategy/](https://www.canva.com/resources/go-to-market-strategy/)  
29. UX Design Audit Checklist to Examine Your Product's Usability \- Eleken, Zugriff am März 17, 2026, [https://www.eleken.co/blog-posts/a-checklist-for-ux-design-audit-based-on-jakob-nielsens-10-usability-heuristics](https://www.eleken.co/blog-posts/a-checklist-for-ux-design-audit-based-on-jakob-nielsens-10-usability-heuristics)  
30. Create a Tracking Plan: 5 Free Templates from Segment, Mixpanel, Amplitude, and more, Zugriff am März 17, 2026, [https://www.freshpaint.io/blog/event-tracking-plan-templates](https://www.freshpaint.io/blog/event-tracking-plan-templates)  
31. Post-Launch Retrospective | TeamRetro, Zugriff am März 17, 2026, [https://www.teamretro.com/retro-template/post-launch-retrospective/](https://www.teamretro.com/retro-template/post-launch-retrospective/)  
32. 7 ultimate templates for every stage of the product development process \- Conceptboard, Zugriff am März 17, 2026, [https://conceptboard.com/blog/7-ultimate-templates-product-development/](https://conceptboard.com/blog/7-ultimate-templates-product-development/)  
33. Retrospectives: How-to Guide, Templates & Examples \- Canva, Zugriff am März 17, 2026, [https://www.canva.com/online-whiteboard/retrospective/](https://www.canva.com/online-whiteboard/retrospective/)  
34. Retrospective Templates \- Miro, Zugriff am März 17, 2026, [https://miro.com/templates/retrospective/](https://miro.com/templates/retrospective/)  
35. Product launch checklist: How to ensure a successful launch \- Atlassian, Zugriff am März 17, 2026, [https://www.atlassian.com/agile/product-management/product-launch-checklist](https://www.atlassian.com/agile/product-management/product-launch-checklist)  
36. Product Manager Report Templates: The Complete Guide For 2026 \- Monday.com, Zugriff am März 17, 2026, [https://monday.com/blog/rnd/report-templates-product-managers/](https://monday.com/blog/rnd/report-templates-product-managers/)  
37. SLA vs. SLI vs. SLO: Understanding Service Levels \- Splunk, Zugriff am März 17, 2026, [https://www.splunk.com/en\_us/blog/learn/sla-vs-sli-vs-slo.html](https://www.splunk.com/en_us/blog/learn/sla-vs-sli-vs-slo.html)  
38. What is a service-level objective (SLO)? SLO vs. SLA vs. SLI \- Atlassian, Zugriff am März 17, 2026, [https://www.atlassian.com/incident-management/kpis/sla-vs-slo-vs-sli](https://www.atlassian.com/incident-management/kpis/sla-vs-slo-vs-sli)  
39. Top 10 Service Readiness Templates with Examples and Samples \- SlideTeam, Zugriff am März 17, 2026, [https://www.slideteam.net/blog/top-10-service-readiness-templates-with-examples-and-samples](https://www.slideteam.net/blog/top-10-service-readiness-templates-with-examples-and-samples)  
40. Incident response plan templates | Red Canary, Zugriff am März 17, 2026, [https://redcanary.com/cybersecurity-101/incident-response/incident-response-plan-template/](https://redcanary.com/cybersecurity-101/incident-response/incident-response-plan-template/)  
41. Top 8 Incident Response Plan Templates \- BlueVoyant, Zugriff am März 17, 2026, [https://www.bluevoyant.com/knowledge-center/top-8-incident-response-plan-templates](https://www.bluevoyant.com/knowledge-center/top-8-incident-response-plan-templates)  
42. GDPR compliance checklist \- GDPR.eu, Zugriff am März 17, 2026, [https://gdpr.eu/checklist/](https://gdpr.eu/checklist/)  
43. GDPR Preparation Planning Checklist \- Privacy Policies, Zugriff am März 17, 2026, [https://www.privacypolicies.com/blog/gdpr-preparation-planning-checklist/](https://www.privacypolicies.com/blog/gdpr-preparation-planning-checklist/)  
44. Rechtsrahmen 2026: Die wichtigsten Änderungen der digitalen Regulatorik und Rechtsprechung im Überblick \- LLR – Kanzlei für Wirtschaftsrecht, Zugriff am März 17, 2026, [https://www.llr.de/rechtsrahmen-2026-die-wichtigsten-aenderungen-der-digitalen-regulatorik-und-rechtsprechung-im-ueberblick/](https://www.llr.de/rechtsrahmen-2026-die-wichtigsten-aenderungen-der-digitalen-regulatorik-und-rechtsprechung-im-ueberblick/)  
45. EU AI Act 2026 Updates: Compliance Requirements and Business Risks \- Legal Nodes, Zugriff am März 17, 2026, [https://www.legalnodes.com/article/eu-ai-act-2026-updates-compliance-requirements-and-business-risks](https://www.legalnodes.com/article/eu-ai-act-2026-updates-compliance-requirements-and-business-risks)  
46. Going Global: The App Compliance Checklist You Actually Need, Zugriff am März 17, 2026, [https://thisisglance.com/blog/going-global-the-app-compliance-checklist-you-actually-need](https://thisisglance.com/blog/going-global-the-app-compliance-checklist-you-actually-need)  
47. EU consent requirements with data privacy laws: Checklist by country, Zugriff am März 17, 2026, [https://usercentrics.com/knowledge-hub/consent-requirements-with-data-privacy-laws-by-country/](https://usercentrics.com/knowledge-hub/consent-requirements-with-data-privacy-laws-by-country/)  
48. Rechtliche Pflichten für Websites \- Impressum, Datenschutz etc. \- IHK Ulm, Zugriff am März 17, 2026, [https://www.ihk.de/ulm/hauptnavigation/mitgliedsunternehmen/beraten-informieren/recht-steuern/rechtsauskuenfte/e-commerce/rechtliche-pflichten-fuer-websites-impressum-datenschutz-etc--6712610](https://www.ihk.de/ulm/hauptnavigation/mitgliedsunternehmen/beraten-informieren/recht-steuern/rechtsauskuenfte/e-commerce/rechtliche-pflichten-fuer-websites-impressum-datenschutz-etc--6712610)  
49. Production Readiness Review | The GitLab Handbook, Zugriff am März 17, 2026, [https://handbook.gitlab.com/handbook/engineering/infrastructure-platforms/production/readiness/](https://handbook.gitlab.com/handbook/engineering/infrastructure-platforms/production/readiness/)  
50. Implementation Readiness Review Checklist \- King County, Zugriff am März 17, 2026, [https://cdn.kingcounty.gov/-/media/king-county/depts/pao/documents/rfp-use-cases/kc001265/kc001265-exhibit-15-implementation-readiness-checklist.pdf?rev=2e9e7f4d33c54d9287b7e61233e39d7d\&hash=60927427F470F97A320E5E0CBC06484D](https://cdn.kingcounty.gov/-/media/king-county/depts/pao/documents/rfp-use-cases/kc001265/kc001265-exhibit-15-implementation-readiness-checklist.pdf?rev=2e9e7f4d33c54d9287b7e61233e39d7d&hash=60927427F470F97A320E5E0CBC06484D)
