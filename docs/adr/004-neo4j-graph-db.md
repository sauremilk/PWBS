# ADR-004: Neo4j als Graph-Datenbank

**Status:** Akzeptiert
**Datum:** 2026-03-13
**Entscheider:** PWBS Core Team

---

## Kontext

Das PWBS benötigt eine Graph-Datenbank für den Knowledge Graph, der Beziehungen zwischen Personen, Projekten, Entscheidungen, Dokumenten, Topics und Entities speichert. Der Graph dient als Audit-Schicht für LLM-Erklärbarkeit und ermöglicht Kontextabfragen (z.B. „Alle Entscheidungen zu Projekt X"), Muster-Erkennung und Beziehungsanalysen. Self-Hosting muss für die On-Premise-Option möglich sein.

---

## Entscheidung

Wir verwenden **Neo4j** als Graph-Datenbank, weil Cypher als ausdrucksstarke Query-Sprache, die größte Community und das ausgereifteste Tooling (Browser, Bloom) die beste Grundlage für den Knowledge Graph bieten.

---

## Optionen bewertet

| Option | Vorteile | Nachteile | Ausschlussgründe |
|--------|----------|-----------|-------------------|
| **Neo4j** (gewählt) | Cypher als ausdrucksstarke, gut dokumentierte Query-Sprache. Größte Graph-DB-Community. Ausgereifte Tools (Neo4j Browser, Bloom für Visualisierung). Stabiler Python-Driver. Self-Hosting möglich. | Hoher RAM-Bedarf bei großen Graphen. Community Edition ohne Cluster-Fähigkeit. | – |
| TigerGraph | Sehr hohe Performance bei Graph-Analytics, native parallele Traversals. | Proprietäre Query-Sprache (GSQL), kleinere Community, höhere Lernkurve. Self-Hosting komplex. | Proprietäre Query-Sprache |
| Amazon Neptune | Fully managed, unterstützt Gremlin und SPARQL. | Kein Self-Hosting (AWS only), kein Cypher-Support, höhere Kosten, Vendor Lock-in. | Kein Self-Hosting möglich |
| TerminusDB | Open-Source, Git-like Versionierung von Graph-Daten. | Kleinere Community, weniger ausgereiftes Tooling, Performance bei komplexen Traversals unklar. | Reife und Community-Größe nicht ausreichend |

---

## Konsequenzen

### Positive Konsequenzen

- Cypher ermöglicht intuitive Graph-Queries (MATCH, MERGE, WHERE) für Kontextabfragen und Muster-Erkennung
- Neo4j Browser und Bloom ermöglichen visuelle Exploration des Knowledge Graphs (nützlich für Debugging und Feature-Demos)
- MERGE-Befehl garantiert Idempotenz bei Graph-Befüllung (kein Doppel-Erstellen von Knoten/Kanten)
- Python-Driver (neo4j-python-driver) ist stabil und gut dokumentiert
- Neo4j Aura als managed Cloud-Option verfügbar

### Negative Konsequenzen / Trade-offs

- Hoher RAM-Bedarf bei großen Graphen – Community Edition hat kein Memory-Tiering (mitigiert: erwartete Graphgröße im MVP ist handhabbar, Neo4j Aura als Alternative)
- Community Edition hat keine Cluster-Fähigkeit (mitigiert: Enterprise Edition oder Neo4j Aura für Phase 5)
- Graph-Traversals mit Tiefe >3 können langsam werden (mitigiert: Query-Timeouts, Ergebnis-Limits, Caching häufiger Patterns)

### Offene Fragen

- RAM-Sizing für erwartete Graphgröße im MVP validieren
- Neo4j 5.x vs. 4.x Kompatibilität des Python-Drivers verifizieren

---

## DSGVO-Implikationen

- **Mandantenisolation:** Alle Knoten und Kanten tragen `owner_id` als Property. Jede Cypher-Query enthält `WHERE n.owner_id = $owner_id`.
- **Löschbarkeit:** Account-Deletion löscht alle Knoten und Kanten mit `owner_id` des Nutzers. `MATCH (n {owner_id: $uid}) DETACH DELETE n` entfernt kaskadiert.
- **Verschlüsselung:** Graph-Daten liegen im Klartext für Query-Performance. Mitigiert durch Volume Encryption (AWS EBS), Netzwerkisolation, kein externer Zugriff.
- **Erklärbarkeit:** Der Graph dient als Quellennachweis-Schicht – jedes LLM-generierte Briefing referenziert Graph-Knoten als Quellenbelege.

---

## Sicherheitsimplikationen

- Neo4j in privatem Subnet, kein direkter Internet-Zugang
- Bolt-Protokoll mit TLS für verschlüsselte Verbindung (API → Neo4j)
- Authentifizierung über Nutzername/Passwort (Environment-Variablen)
- Volume Encryption (AWS EBS) für at-rest-Schutz
- Query-Timeouts verhindern ressourcenintensive Endlos-Traversals (DoS-Schutz)

---

## Revisionsdatum

2027-03-13 – Bewertung von RAM-Anforderungen und Cluster-Bedarf nach 12 Monaten MVP-Betrieb. Evaluation Neo4j Aura vs. Self-Hosting.
