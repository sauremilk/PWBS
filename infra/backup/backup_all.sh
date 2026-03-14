#!/usr/bin/env bash
# Orchestrate all database backups (TASK-167).
# RPO: 1 hour, RTO: 4 hours.
#
# Usage:
#   ./backup_all.sh              # backup all
#   ./backup_all.sh --restore    # restore all (latest)

set -euo pipefail

SCRIPT_DIR="C:\Users\mickg\PWBS"

echo "=========================================="
echo " PWBS Database Backup"
echo " "
echo "=========================================="

if [ "" = "--restore" ]; then
    echo ""
    echo "--- PostgreSQL Restore ---"
    bash "/backup_postgres.sh" --restore

    echo ""
    echo "--- Weaviate Restore ---"
    echo "NOTE: Weaviate restore requires a known backup-id."
    echo "      Use: bash /backup_weaviate.sh --restore <backup-id>"

    echo ""
    echo "--- Neo4j Restore ---"
    bash "/backup_neo4j.sh" --restore
else
    echo ""
    echo "--- PostgreSQL Backup ---"
    bash "/backup_postgres.sh"

    echo ""
    echo "--- Weaviate Backup ---"
    bash "/backup_weaviate.sh"

    echo ""
    echo "--- Neo4j Backup ---"
    bash "/backup_neo4j.sh"
fi

echo ""
echo "=========================================="
echo " All operations complete."
echo "=========================================="
