# Disaster Recovery Runbook (TASK-167)

> **RPO:** 1 Stunde | **RTO:** 4 Stunden
>
> Dieses Runbook beschreibt die Wiederherstellung aller drei Datenbanken
> (PostgreSQL, Weaviate, Neo4j) aus Backups.

---

## 1. Voraussetzungen

- AWS CLI konfiguriert mit Zugriff auf den S3-Backup-Bucket
- Docker installiert und lauffaehig
- Zugang zu den Backup-Skripten in infra/backup/
- Umgebungsvariablen gesetzt (siehe .env.example)

## 2. Backup-Uebersicht

| Datenbank   | Methode                        | Frequenz       | Retention |
| ----------- | ------------------------------ | -------------- | --------- |
| PostgreSQL  | pg_dump (custom format)        | Stuendlich     | 30 Tage   |
| Weaviate    | Weaviate Backup API + S3       | Stuendlich     | 30 Tage   |
| Neo4j       | neo4j-admin database dump + S3 | Stuendlich     | 30 Tage   |

## 3. Wiederherstellung PostgreSQL

### 3.1 Automatisch (empfohlen)

`ash
export PGHOST=<host> PGPORT=5432 PGUSER=pwbs PGPASSWORD=<pw> PGDATABASE=pwbs
export S3_BUCKET=pwbs-backups
# Optional fuer MinIO: export S3_ENDPOINT=http://localhost:9000
bash infra/backup/backup_postgres.sh --restore
`

### 3.2 Manuell

1. Letztes Backup finden:
   `ash
   aws s3 ls s3://pwbs-backups/postgres/ | sort | tail -5
   `
2. Backup herunterladen:
   `ash
   aws s3 cp s3://pwbs-backups/postgres/<dateiname>.dump /tmp/restore.dump
   `
3. Restore ausfuehren:
   `ash
   pg_restore --clean --if-exists --verbose --dbname=pwbs /tmp/restore.dump
   `
4. Integritaet pruefen:
   `ash
   psql -d pwbs -c "SELECT count(*) FROM users;"
   psql -d pwbs -c "SELECT count(*) FROM documents;"
   psql -d pwbs -c "SELECT count(*) FROM briefings;"
   `

## 4. Wiederherstellung Weaviate

### 4.1 Automatisch

`ash
export WEAVIATE_URL=http://localhost:8080
# Backup-ID aus S3-Listing ermitteln:
aws s3 ls s3://pwbs-backups/weaviate/
bash infra/backup/backup_weaviate.sh --restore <backup-id>
`

### 4.2 Manuell

1. Backup-ID identifizieren (Format: pwbs-YYYYMMDDTHHMMSSz)
2. Restore via API:
   `ash
   curl -X POST http://localhost:8080/v1/backups/s3/<backup-id>/restore \
     -H "Content-Type: application/json" -d "{}"
   `
3. Status pruefen:
   `ash
   curl http://localhost:8080/v1/backups/s3/<backup-id>/restore
   `
4. Validierung:
   `ash
   curl http://localhost:8080/v1/schema
   curl "http://localhost:8080/v1/objects?limit=5"
   `

## 5. Wiederherstellung Neo4j

### 5.1 Automatisch

`ash
export NEO4J_CONTAINER=neo4j S3_BUCKET=pwbs-backups
bash infra/backup/backup_neo4j.sh --restore
`

### 5.2 Manuell

1. Letztes Backup finden:
   `ash
   aws s3 ls s3://pwbs-backups/neo4j/ | sort | tail -5
   `
2. Neo4j stoppen:
   `ash
   docker exec neo4j neo4j stop
   `
3. Dump laden:
   `ash
   aws s3 cp s3://pwbs-backups/neo4j/<dateiname>.dump /tmp/neo4j.dump
   docker cp /tmp/neo4j.dump neo4j:/tmp/neo4j.dump
   docker exec neo4j neo4j-admin database load --from-path=/tmp neo4j --overwrite-destination
   `
4. Neo4j starten:
   `ash
   docker exec neo4j neo4j start
   `
5. Validierung:
   `ash
   cypher-shell -u neo4j -p <pw> "MATCH (n) RETURN count(n);"
   `

## 6. Vollstaendige Wiederherstellung (alle DBs)

`ash
# Alle Umgebungsvariablen setzen (siehe .env)
bash infra/backup/backup_all.sh --restore
`

**Reihenfolge beachten:** PostgreSQL -> Weaviate -> Neo4j (FK-Abhaengigkeiten).

## 7. Validierung nach Recovery

- [ ] API Health-Check: curl http://localhost:8000/api/v1/admin/health
- [ ] Login mit Testnutzer moeglich
- [ ] Suche liefert Ergebnisse (Weaviate-Vektoren vorhanden)
- [ ] Knowledge-Graph-Abfragen funktionieren (Neo4j)
- [ ] Briefing-Generierung erfolgreich
- [ ] Konnektoren zeigen korrekten letzten Sync-Zeitpunkt

## 8. Eskalation

| Szenario                        | Aktion                                    |
| ------------------------------- | ----------------------------------------- |
| Backup nicht im S3              | Pruefe Backup-Job-Logs, manuell triggern  |
| pg_restore schlaegt fehl        | --no-owner --no-privileges versuchen    |
| Weaviate Restore timeout        | Weaviate-Container neu starten, erneut    |
| Neo4j startet nicht nach Load   | Logs pruefen, ggf. 
eo4j-admin Rebuild  |
| RTO ueberschritten (>4h)        | Incident eskalieren, Stakeholder benachr.  |

---

*Zuletzt aktualisiert: TASK-167*
