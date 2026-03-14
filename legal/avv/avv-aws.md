# Auftragsverarbeitungsvertrag (AVV) – Amazon Web Services (AWS)

**Vertrag zwischen:**
- **Verantwortlicher:** [Firma/Name], Betreiber des PWBS
- **Auftragsverarbeiter:** Amazon Web Services EMEA SARL

**Datum:** [Datum einsetzen]
**Version:** 1.0

---

## 1. Gegenstand der Auftragsverarbeitung

AWS stellt Hosting-Infrastruktur für das PWBS bereit. Die Verarbeitung umfasst Speicherung und Bereitstellung aller Nutzerdaten in verschlüsselter Form.

## 2. Dauer

Der AVV gilt für die Laufzeit des AWS-Servicevertrags. Nach Beendigung erfolgt die Löschung gemäß Abschnitt 8.

## 3. Art und Zweck der Verarbeitung

| Aspekt | Beschreibung |
|--------|-------------|
| **Services** | ECS Fargate (Compute), RDS PostgreSQL 16 (Datenbank), ElastiCache Redis 7 (Cache/Queue), S3 (Backups) |
| **Zweck** | Hosting der PWBS-Backend-Infrastruktur |
| **Art** | Speicherung, Bereitstellung, automatisierte Verarbeitung |

## 4. Kategorien betroffener Personen

- Registrierte PWBS-Nutzer
- In Dokumenten genannte Dritte (Meeting-Teilnehmer, E-Mail-Korrespondenzpartner)

## 5. Kategorien personenbezogener Daten

- Authentifizierungsdaten (E-Mail, Name, Passwort-Hashes)
- Importierte Dokumente (Kalender, Notizen, E-Mails, Transkripte, Slack-Nachrichten)
- Abgeleitete Daten (Briefings, Knowledge-Graph-Entitäten)
- Audit-Logs (user_id, Aktionstypen, Zeitstempel)

## 6. Pflichten des Auftragsverarbeiters

### 6.1 Datenresidenz
- **Ausschließlich Region `eu-central-1` (Frankfurt)** für alle Services
- Keine automatische Datenweitergabe an Sub-Processors außerhalb der EU
- Backups ausschließlich in `eu-central-1`

### 6.2 Verschlüsselung
- **At Rest:** AES-256 via AWS KMS (Customer Managed Key)
- **In Transit:** TLS 1.2+ für alle Verbindungen
- KMS Master Key unter Kontrolle des Verantwortlichen

### 6.3 Zugriffskontrolle
- IAM-Policies nach Least-Privilege-Prinzip
- Kein AWS-Mitarbeiterzugriff auf Kundendaten ohne explizite Genehmigung
- CloudTrail-Logging aller API-Zugriffe

### 6.4 Weisungsgebundenheit
- Verarbeitung ausschließlich auf Weisung des Verantwortlichen
- Keine Nutzung der Daten für eigene Zwecke

## 7. Unterauftragsverarbeitung

AWS-Sub-Processors werden unter https://aws.amazon.com/compliance/sub-processors/ aufgelistet. Änderungen werden 30 Tage vor Inkrafttreten mitgeteilt. Widerspruchsrecht des Verantwortlichen.

## 8. Löschung und Rückgabe

- Bei Vertragsende: Vollständige Löschung aller Daten innerhalb von 90 Tagen
- Auf Anfrage: Datenexport im maschinenlesbaren Format
- Nachweis der Löschung auf Verlangen

## 9. Unterstützungspflichten

- Unterstützung bei Betroffenenrechten (Art. 15–22 DSGVO)
- Meldung von Datenschutzvorfällen innerhalb von 24 Stunden
- Unterstützung bei Datenschutz-Folgenabschätzungen

## 10. Technische und organisatorische Maßnahmen (TOM)

Verweis auf AWS SOC 2 Type II Report und ISO 27001-Zertifizierung. Zusätzlich gelten die in `legal/tom.md` definierten kundenseitigen Maßnahmen.

## 11. Prüfrechte

- Recht auf Audits durch den Verantwortlichen oder beauftragte Dritte
- AWS stellt SOC-Reports, ISO-Zertifizierungen und Penetration-Test-Ergebnisse bereit

---

## Referenzen

- AWS GDPR DPA: https://aws.amazon.com/de/compliance/gdpr-center/
- AWS Sub-Processors: https://aws.amazon.com/compliance/sub-processors/
- Projekt-TOM: `legal/tom.md`
- DSGVO-Erstkonzept: `docs/dsgvo-erstkonzept.md`

---

**Unterschriften:**

| Verantwortlicher | Auftragsverarbeiter (AWS) |
|:---:|:---:|
| ___________________________ | ___________________________ |
| Name, Datum | Name, Datum |
