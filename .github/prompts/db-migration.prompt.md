---
agent: agent
description: Erstellt eine vollständige Alembic-Datenbankm­igration für Schema-Änderungen im PWBS. Prüft Konsistenz mit DSGVO-Anforderungen und Architekturprinzipien.
tools:
  - codebase
  - editFiles
  - runCommands
  - problems
---

# Datenbankm­igration erstellen

> **Robustheitsregeln:**
>
> - Prüfe vor jedem Schritt, ob die benötigten Voraussetzungen erfüllt sind (Alembic konfiguriert, Modell-Verzeichnis vorhanden, DB erreichbar).
> - Verwende plattformgerechte Shell-Befehle. Alle Shell-Beispiele sind Pseudo-Code.
> - Falls Alembic noch nicht eingerichtet ist: dokumentiere die notwendigen Setup-Schritte.
>   **Beschreibung der Änderung:** ${input:change_description:Was wird am Schema geändert? z.B. "Neue Tabelle für Connector-Zustand" oder "Spalte expires_at zu documents hinzufügen"}

## Vorgehen

### 1. Bestehende Modelle analysieren

- **Prüfe ob `pwbs/storage/models/` oder `pwbs/models/` existiert.** Lies dort die bestehenden SQLAlchemy-Modelle. Falls keins der Verzeichnisse existiert: suche im gesamten `pwbs/`-Verzeichnis nach SQLAlchemy-Modellen (`Base`, `mapped_column`, `DeclarativeBase`).
- Prüfe ob das ORM-Modell für die geplante Änderung bereits existiert oder neu erstellt werden muss.

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

1. Prüfe ob `backend/alembic.ini` oder ein `alembic/`-Verzeichnis im Backend existiert. Falls nicht: prüfe ob Alembic als Dependency in `pyproject.toml` aufgeführt ist und initialisiere ggf. mit `alembic init alembic`.
2. Generiere die Migration (leite den Slug aus der Beschreibung ab – Kleinbuchstaben, Leerzeichen durch Unterstriche, Sonderzeichen entfernen):
   ```
   cd backend
   alembic revision --autogenerate -m "<slug-der-beschreibung>"
   ```

### 4. Migration prüfen

Prüfe die generierte Migration in `backend/migrations/versions/` (oder `backend/alembic/versions/`, je nach Konfiguration) auf:

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

**Voraussetzung:** Eine laufende PostgreSQL-Instanz (z.B. via `docker compose up -d postgres`).

```
cd backend
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Falls die Datenbank nicht erreichbar ist: dokumentiere die Migration als ungetestet und notiere die benötigten Setup-Schritte.

Bericht nach abgeschlossener Migration mit:

- Erstellte/geänderte Tabellen
- Neue Indexes
- Ausstehende manuelle Schritte (z.B. Datenmigration)
