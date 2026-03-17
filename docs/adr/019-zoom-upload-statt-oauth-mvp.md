# ADR-019: Zoom-Konnektor von OAuth2 auf Upload-basierte Ingestion im MVP umstellen

**Status:** Akzeptiert
**Datum:** 2026-03-16
**Entscheider:** PWBS Core Team

---

## Kontext

Der Zoom-Konnektor (TASK-053..055) nutzt OAuth2 via Zoom Marketplace App für den automatischen Abruf von Cloud-Recording-Transkripten. Zoom Marketplace Apps erfordern einen Approval-Prozess (Review durch Zoom), der Wochen bis Monate dauern kann. Dieser externe Abhängigkeitspfad ist ein stiller Blocker auf dem kritischen MVP-Pfad: Ohne Marketplace-Approval kann kein Early Adopter den Zoom-Konnektor nutzen.

Die bestehende OAuth2-Implementierung ist vollständig (OAuth-Flow, Polling via `fetch_since()`, Webhook-Receiver, VTT-Parser, `normalize()`) und durch 141 Unit-Tests abgesichert. Der Code ist funktional korrekt — nur der externe Approval-Prozess blockiert die Nutzung.

Ohne diese Entscheidung bleibt Zoom als einer der Kern-4-Konnektoren für Beta-Nutzer unzugänglich, obwohl die technische Implementierung fertig ist.

Analog zu ADR-018 (Obsidian: Filesystem-Watcher → Upload) wird ein Upload-Fallback eingeführt.

---

## Entscheidung

Wir werden den Zoom-Konnektor im MVP von OAuth2-basiertem Auto-Sync auf Upload-basierte Transkript-Ingestion umstellen, weil dies den externen Marketplace-Approval-Blocker vom kritischen Pfad entfernt, die bestehenden VTT-Parser und `normalize()`-Logik vollständig wiederverwendet, und Early Adoptern sofortigen Zugang zu Zoom-Transkripten ermöglicht.

Konkret:

1. **Neuer Endpunkt:** `POST /api/v1/connectors/zoom/upload` akzeptiert VTT-, SRT- und TXT-Dateien (multipart/form-data).
2. **SRT-Parser:** Neuer `_parse_srt()`-Parser ergänzt den bestehenden `_parse_vtt()`.
3. **Format-Erkennung:** `detect_transcript_format()` erkennt automatisch VTT, SRT oder Plaintext anhand von Dateiendung und Content-Sniffing.
4. **OAuth-Code bleibt erhalten:** Die vollständige OAuth2-Implementierung (141 Tests) bleibt in `zoom.py`, wird aber im MVP nicht über die API-Routes angeboten. `auth_method` in den Connector-Metadaten wechselt von `"oauth2"` zu `"upload"`.
5. **Connection Auto-Creation:** Beim ersten Upload wird automatisch ein Connection-Record erstellt.
6. **Idempotenz:** Content-Hash-basierte `source_id` verhindert Duplikate bei Re-Upload.
7. **SourceType.ZOOM bleibt:** Kein neuer SourceType — alle Zoom-Dokumente laufen unter `source_type=zoom`, unabhängig ob sie via Upload oder (später) OAuth kamen.

---

## Optionen bewertet

| Option                                                  | Vorteile                                                                                               | Nachteile                                                                                                  | Ausschlussgründe                                    |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| A: Neuer SourceType `zoom_upload`                       | Klare Trennung Upload vs. OAuth                                                                        | Zwei SourceTypes verwirren Suche und Briefings, Migration unklar                                           | Unnötige Komplexität, Forward-Kompatibilität leidet |
| **B: SourceType.ZOOM mit auth_method=upload (gewählt)** | Nahtlose Transition zu OAuth, minimaler Change, identischer Suchfilter, bestehende Pipeline kompatibel | OAuth-Code bleibt inaktiv im Codebase                                                                      | –                                                   |
| C: Zoom nach `_deferred/` verschieben                   | Sauberer architektonischer Schnitt                                                                     | Kern-4 → Kern-3, widerspricht ADR-016, Beta-Tester verlieren Zoom-Funktionalität, VTT-Parser-Code verloren | Persona "Lena" verliert Zoom-Hypothese im MVP       |

---

## Konsequenzen

### Positive Konsequenzen

- **Kein externer Blocker:** Zoom-Transkripte sofort nutzbar, unabhängig von Marketplace-Approval-Timeline.
- **Kern-4 bleibt komplett:** Hypothese testbar, Early Adopters mit Zoom-Fokus versorgt.
- **Code-Wiederverwendung:** `_parse_vtt()`, `normalize()`, Content-Hash-Dedup, UDF-Pipeline — alles wiederverwendet.
- **Forward-Kompatibilität:** Nach Marketplace-Approval wird `auth_method` auf `"oauth2"` zurückgesetzt und OAuth-Routes reaktiviert. Upload-Endpunkt kann parallel bestehen bleiben.
- **Sicherheit:** Kein Server braucht Zoom-API-Zugriff im MVP. Keine OAuth-Tokens gespeichert.

### Negative Konsequenzen / Trade-offs

- **Kein Auto-Sync im MVP:** Nutzer müssen Transkripte manuell nach jedem Meeting hochladen. Für 10–20 Early Adopters, die bewusst einen Prototyp testen, ist das akzeptabel.
- **Manuelle Metadaten:** Meeting-Titel und Meeting-Datum optional manuell angeben (bei OAuth automatisch aus API).
- **Speaker-Extraktion abhängig von Format:** VTT-Dateien enthalten Speaker-Labels, SRT und TXT möglicherweise nicht.

### Offene Fragen

- Soll der Upload-Endpunkt auch Batch-Uploads (mehrere Dateien gleichzeitig) unterstützen?
- Soll ein Frontend-Hinweis "OAuth-Sync kommt bald" angezeigt werden?

---

## DSGVO-Implikationen

- **Keine Änderung:** Hochgeladene Transkripte durchlaufen identische UDF-Pipeline. `owner_id`, `expires_at` (180 Tage Zoom-Default) und Löschbarkeit bleiben identisch.
- **Upload-Daten:** Werden nach dem Parsen nicht als Rohdatei gespeichert, nur die extrahierten `UnifiedDocument`-Objekte.
- **Delete-Cascade:** Bei Connector-Disconnect werden alle Zoom-Dokumente gelöscht (bestehende CASCADE-Logik).
- **Kein externer Datenaustausch:** Upload ist rein eingehend, keine Daten fließen an Zoom zurück.

---

## Sicherheitsimplikationen

- **File-Upload-Validierung:** Extension-Allowlist (.vtt, .srt, .txt), maximale Dateigröße (10 MB), UTF-8-Encoding-Prüfung.
- **Keine Injection-Vektoren:** Transkript-Content wird als Text geparst, kein dynamisches SQL/Cypher/Command-Execution.
- **Kein SSRF-Risiko:** Rein eingehend, keine externen HTTP-Calls durch Upload.
- **Auth:** Endpunkt hinter bestehender JWT-Middleware, `owner_id` aus Token.
- **Rate Limiting:** Upload-Endpunkt nutzt bestehendes Rate-Limiting.

---

## Revisionsdatum

Nach Abschluss des Zoom Marketplace Approval-Prozesses. Dann `auth_method` auf `"oauth2"` zurücksetzen und OAuth-Routes reaktivieren.
