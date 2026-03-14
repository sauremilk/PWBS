#!/usr/bin/env bash
# Weaviate backup script (TASK-167).
# Uses the Weaviate Backup API with S3 backend.
#
# Env vars: WEAVIATE_URL, S3_BUCKET, S3_ENDPOINT (optional)

set -euo pipefail

WEAVIATE_URL=""
BACKUP_ID="pwbs-20260314T205550Z"

backup() {
    echo "[INFO] Starting Weaviate backup (id: )..."
    curl -sf -X POST "/v1/backups/s3" \
        -H "Content-Type: application/json" \
        -d "{\"id\": \"\", \"include\": []}"

    echo "[INFO] Waiting for backup to complete..."
    for i in ; do
        STATUS=
        echo "  Status: "
        [ "" = "SUCCESS" ] && { echo "[INFO] Weaviate backup complete."; return 0; }
        [ "" = "FAILED" ] && { echo "ERROR: Backup failed" >&2; return 1; }
        sleep 5
    done
    echo "ERROR: Backup timed out" >&2
    return 1
}

restore() {
    RESTORE_ID=""
    echo "[INFO] Restoring Weaviate backup ..."
    curl -sf -X POST "/v1/backups/s3//restore" \
        -H "Content-Type: application/json" \
        -d "{}"

    for i in ; do
        STATUS=
        echo "  Status: "
        [ "" = "SUCCESS" ] && { echo "[INFO] Weaviate restore complete."; return 0; }
        [ "" = "FAILED" ] && { echo "ERROR: Restore failed" >&2; return 1; }
        sleep 5
    done
    echo "ERROR: Restore timed out" >&2
    return 1
}

case "" in
    --restore) shift; restore "$@" ;;
    *)         backup ;;
esac
