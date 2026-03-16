# ADR-018: Obsidian-Konnektor von Filesystem-Watcher auf Upload-basierte Ingestion umstellen

**Status:** Vorgeschlagen
**Datum:** 2026-03-16
**Entscheider:** PWBS Core Team

---

## Kontext

Der Obsidian-Konnektor (TASK-051/052) verwendet `watchdog` für File-System-Watching und direkten Filesystem-Zugriff via `Path.stat()` und `scan_vault_files()`. Dies setzt voraus, dass das Backend auf der gleichen Maschine läuft wie der Obsidian-Vault des Nutzers. Die geplante Deployment-Topologie (ECS Fargate, ADR-001/006) ist ein containerisierter Cloud-Service ohne Zugriff auf lokale Nutzer-Dateisysteme. Der Obsidian-Konnektor ist damit der einzige der Kern-4-Konnektoren, der architektonisch inkompatibel mit dem Produktions-Deployment ist.

Ohne diese Entscheidung kann PWBS nicht mit Obsidian-Daten in der Cloud-Umgebung arbeiten, oder Nutzer wären gezwungen, das Backend lokal zu betreiben  was dem Web-App-Modell widerspricht.

---

## Entscheidung

Wir werden den Obsidian-Konnektor von Filesystem-basiertem Zugriff (watchdog + lokales Scanning) auf Upload-basierte Ingestion umstellen, weil dies Cloud-Deployment-Kompatibilität herstellt, den bestehenden Markdown-Parser und die `normalize()`-Logik vollständig wiederverwendet, und Forward-Kompatibilität mit der Desktop-App (Tauri, Phase 3) gewährleistet, deren `SyncEngine` bereits einen Push-to-API-Mechanismus implementiert hat.

Konkret:

1. **Neuer Endpunkt:** `POST /api/v1/connectors/obsidian/upload` akzeptiert ZIP-Archive oder einzelne Markdown-Dateien (multipart/form-data).
2. **Filesystem-Watcher entfernen:** `ObsidianWatcher`, `ObsidianFileHandler` und die `watchdog`-Abhängigkeit werden aus dem aktiven MVP-Code entfernt (Code bleibt für Desktop-App-Nutzung in Phase 3 erhalten).
3. **`fetch_since()` refaktorieren:** Arbeitet auf hochgeladenem Content statt auf direktem Dateisystem-Scan.
4. **Content-Hash-Dedup:** Bereits vorhandene Dokumente werden per Content-Hash erkannt, nur geänderte/neue Dateien werden verarbeitet.
5. **Löscherkennung:** Dateien, die in einem neuen Upload fehlen, werden als gelöscht markiert.
6. **Frontend:** Vault-Pfad-Eingabefeld wird durch Drag-and-Drop/File-Upload-Komponente ersetzt.

---

## Optionen bewertet

| Option | Vorteile | Nachteile | Ausschlussgründe |
|--------|----------|-----------|-------------------|
| A: Nur Upload-Konnektor | Cloud-kompatibel, einfach, existierender Parser wiederverwendbar | Kein automatisches Syncing, UX-Friction | Kein expliziter Migrationspfad zur Desktop-App |
| B: Obsidian nach `_deferred/` verschieben (Phase 3) | Sauberer architektonischer Schnitt, kein Kompromiss bei UX | Kern-4  Kern-3, Obsidian-Hypothese im MVP nicht testbar, Beta-Tester mit Obsidian-Fokus unversorgt | Persona Lena" verliert MVP-Zugang vollständig |
| **C: Hybrid  Upload jetzt + Desktop-Watcher in Phase 3 (gewählt)** | Cloud-kompatibel, Kern-4 bleibt erhalten, Forward-kompatibel mit Tauri SyncEngine, bestehender Parser wiederverwendbar, Hypothese testbar | Zwei Sync-Modi müssen langfristig koexistieren (Upload + Auto-Sync), Upload-UX inferior zu Auto-Sync |  |

---

## Konsequenzen

### Positive Konsequenzen

- **Cloud-Deployment-Kompatibilität:** Kein Filesystem-Zugriff im Backend nötig  ECS Fargate funktioniert sofort.
- **Kern-4 bleibt komplett:** Obsidian ist weiterhin als Konnektor verfügbar, die Hypothese ist testbar.
- **Forward-Kompatibilität:** Die Tauri Desktop-App (`SyncEngine` in `desktop-app/src-tauri/src/offline/sync.rs`) nutzt denselben Upload/Push-Endpunkt transparent  kein zusätzlicher Backend-Code nötig.
- **Sicherheit:** Kein Server braucht Zugriff auf lokale Dateisysteme. Alle Daten kommen über authentifizierte API-Calls.
- **~400 LOC weniger** im aktiven Backend (Watcher-Code wird aus dem Hot-Path entfernt).

### Negative Konsequenzen / Trade-offs

- **Kein Auto-Sync im MVP:** Nutzer müssen Vault-Inhalte manuell hochladen (alle 12 Tage). Persona Lena hat höhere Friction als bei Real-Time-Watcher.
- **Upload-Größenlimit:** Große Vaults (>50 MB, >5.000 Dateien) benötigen Batching oder höhere Limits.
- **ZIP-Sicherheit:** Neuer Angriffsvektor (ZIP-Bombs, Path-Traversal) muss mitigiert werden.

### Offene Fragen

- Soll der Upload-Endpunkt auch von der Public API (`/api/v1/public/...`) erreichbar sein, oder nur über JWT-Auth?
- Maximale Upload-Größe: 50 MB ausreichend für typische Obsidian-Vaults?
- Soll ein Obsidian Community Plugin" als alternativer Push-Kanal evaluiert werden (Plugin synct direkt zur PWBS-API)?

---

## DSGVO-Implikationen

- **Keine Änderung:** Hochgeladene Markdown-Dateien durchlaufen dieselbe UDF-Pipeline wie bisher. `owner_id`, `expires_at` und Löschbarkeit bleiben identisch.
- **Upload-Daten:** Werden nach Verarbeitung nicht als Rohdatei gespeichert, nur die extrahierten `UnifiedDocument`-Objekte mit vollständiger DSGVO-Metadatenstruktur.
- **Delete-Cascade:** Bei Connector-Disconnect werden alle aus Uploads stammenden Dokumente gelöscht (bestehende CASCADE-Logik).

---

## Sicherheitsimplikationen

- **ZIP-Bomb-Schutz:** Maximale entpackte Größe limitieren (z.B. 200 MB), Maximale Dateianzahl (5.000), Abbruch bei Überschreitung.
- **Path-Traversal:** Alle Pfade in ZIP-Archiven werden sanitized  keine `../`-Pfade, nur `.md`-Dateien extrahiert.
- **Rate Limiting:** Upload-Endpunkt erhält eigenes Rate-Limit (z.B. 5 Uploads/Stunde/User) wegen großer Payloads.
- **Auth:** Endpunkt hinter bestehender JWT-Middleware, `owner_id` aus Token.
- **Keine neuen externen Calls:** Upload ist rein eingehend, kein SSRF-Risiko.

---

## Revisionsdatum

Phase 3  Desktop-App-Release (voraussichtlich Q3 2026). Dann prüfen ob Upload-Modus beibehalten oder durch Auto-Sync via Tauri ersetzt wird.
