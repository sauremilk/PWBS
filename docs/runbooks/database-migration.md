# Database-Migration-Runbook

Anleitung fuer sichere Alembic-Migrationen in Staging und Production.

---

## Voraussetzungen

- Zugriff auf die Ziel-Datenbank (PostgreSQL)
- Alembic installiert (`pip install alembic`)
- `DATABASE_URL` korrekt gesetzt

---

## 1. Vor der Migration

### 1.1 Backup erstellen (Pflicht bei destruktiven Migrationen)

```bash
pg_dump -Fc -h <HOST> -U pwbs -d pwbs > backup_$(date +%Y%m%d_%H%M%S).dump
```

Destruktive Migrationen (DROP COLUMN, DROP TABLE, ALTER TYPE) erfordern **immer** ein Backup vorher.

### 1.2 Migrations-Status pruefen

```bash
cd backend
alembic current   # Zeigt aktuelle Revision
alembic history   # Zeigt alle verfuegbaren Migrationen
```

### 1.3 Diff pruefen

```bash
alembic upgrade head --sql   # SQL-Preview ohne Ausfuehrung
```

Pruefen des generierten SQL auf unerwartete DROP-Statements oder Datenverlust.

---

## 2. Migration ausfuehren

### 2.1 Staging zuerst

```bash
DATABASE_URL=<STAGING_URL> alembic upgrade head
```

Staging erfolgreich? Dann Production.

### 2.2 Production

```bash
DATABASE_URL=<PRODUCTION_URL> alembic upgrade head
```

**CI/CD-Reihenfolge:**
1. `alembic upgrade head`
2. App-Deploy (neue Version)
3. Health-Check

---

## 3. Rollback-Verfahren

### 3.1 Alembic Downgrade (nicht-destruktive Migrationen)

```bash
# Eine Revision zurueck
alembic downgrade -1

# Zu einer bestimmten Revision
alembic downgrade <REVISION_ID>
```

### 3.2 Snapshot-Restore (destruktive Migrationen)

Wenn die Migration Daten geloescht hat (DROP COLUMN / DROP TABLE):

```bash
# 1. App stoppen (oder Maintenance-Mode aktivieren)
# 2. Datenbank wiederherstellen
pg_restore -h <HOST> -U pwbs -d pwbs --clean backup_YYYYMMDD_HHMMSS.dump

# 3. App-Version zurueckrollen (vorheriges Docker-Image)
# 4. Alembic-Status pruefen
alembic current
```

---

## 4. Checkliste fuer neue Migrationen

- [ ] `alembic revision --autogenerate -m "beschreibung"` ausfuehren
- [ ] Generierte Migration manuell pruefen (Autogenerate erkennt nicht alles)
- [ ] Downgrade-Funktion testen: `alembic downgrade -1` und `alembic upgrade head`
- [ ] Bei DROP-Operationen: Backup-Pflicht in der Commit-Message erwaehnen
- [ ] Migration auf Staging erfolgreich getestet

---

## 5. Haeufige Probleme

| Problem | Loesung |
|---------|---------|
| `alembic: Target database is not up to date` | `alembic stamp head` nach manuellem Schema-Fix |
| Migration-Konflikt (zwei Heads) | `alembic merge heads -m "merge"` |
| Timeout bei grossen Tabellen | `statement_timeout` erhoehen oder Migration in Batches |
| Lock-Timeout | Migration ausserhalb der Stosszeiten ausfuehren |

---

## 6. Kontakt bei Problemen

Eskalation ueber den Incident-Kanal gemaess `docs/runbooks/disaster-recovery.md`.
