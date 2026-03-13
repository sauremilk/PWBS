---
agent: agent
description: Erstellt eine vollständige Alembic-Datenbankm­igration für Schema-Änderungen im PWBS. Prüft Konsistenz mit DSGVO-Anforderungen und Architekturprinzipien.
tools:
  - codebase
  - editFiles
  - runCommands
---

# Datenbankm­igration erstellen

**Beschreibung der Änderung:** ${input:change_description:Was wird am Schema geändert? z.B. "Neue Tabelle für Connector-Zustand" oder "Spalte expires_at zu documents hinzufügen"}

## Vorgehen

### 1. Bestehende Modelle analysieren
- Lies `pwbs/storage/models/` – bestehende SQLAlchemy-Modelle
- Prüfe ob ORM-Modell bereits existiert oder neu erstellt werden muss

### 2. ORM-Modell aktualisieren/erstellen
Passe das SQLAlchemy-Modell an:
```python
# Pflichtfelder bei Nutzer-gebundenen Tabellen:
owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
created_at: Mapped[datetime] = mapped_column(server_default=func.now())
updated_at: Mapped[datetime] = mapped_column(onupdate=func.now())
```

### 3. Migration generieren
```bash
cd backend
alembic revision --autogenerate -m "${input:change_description:change_description|slugify}"
```

### 4. Migration prüfen
Prüfe die generierte Migration in `alembic/versions/` auf:
- [ ] `CASCADE DELETE` auf alle `owner_id`-Foreign-Keys
- [ ] Indexes auf häufig gefilterte Spalten (`owner_id`, `source_id`, `expires_at`)
- [ ] Keine `DROP TABLE`/`DROP COLUMN` ohne explizite Bestätigung
- [ ] `down_revision` korrekt auf zuletzt aktive Migration gesetzt
- [ ] `upgrade()` und `downgrade()` beide implementiert

### 5. DSGVO-Prüfung
- [ ] Neue Nutzer-bezogene Tabellen haben `owner_id` mit `CASCADE`
- [ ] Neue Tabellen mit PII haben `expires_at`
- [ ] Row-Level-Security für neue Tabellen dokumentiert

### 6. Migration testen (lokal)
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Bericht nach abgeschlossener Migration mit:
- Erstellte/geänderte Tabellen
- Neue Indexes
- Ausstehende manuelle Schritte (z.B. Datenmigration)
