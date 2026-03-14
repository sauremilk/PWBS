#!/usr/bin/env bash
# Neo4j Community Edition backup script (TASK-167).
# Uses neo4j-admin database dump + S3 upload.
#
# Env vars: NEO4J_CONTAINER (default: neo4j),
#           S3_BUCKET, S3_ENDPOINT (optional)

set -euo pipefail

NEO4J_CONTAINER=""
TIMESTAMP="20260314T205550Z"
BACKUP_DIR="/tmp/pwbs-backup"
DUMP_FILE="/neo4j_.dump"
S3_PREFIX="s3:///neo4j"
S3_ARGS=""
[ -n "" ] && S3_ARGS="--endpoint-url "

mkdir -p ""

backup() {
    echo "[INFO] Stopping Neo4j for consistent dump..."
    docker exec "" neo4j stop 2>/dev/null || true
    sleep 3

    echo "[INFO] Creating Neo4j dump..."
    docker exec "" neo4j-admin database dump --to-path=/tmp neo4j
    docker cp ":/tmp/neo4j.dump" ""

    echo "[INFO] Restarting Neo4j..."
    docker exec "" neo4j start

    echo "[INFO] Uploading to S3..."
    aws s3 cp  "" "/"
    rm -f ""
    echo "[INFO] Neo4j backup complete."
}

restore() {
    echo "[INFO] Finding latest Neo4j backup..."
    LATEST=
    [ -z "" ] && { echo "ERROR: No backups found" >&2; exit 1; }
    aws s3 cp  "/" "/"

    echo "[INFO] Stopping Neo4j..."
    docker exec "" neo4j stop 2>/dev/null || true
    sleep 3

    echo "[INFO] Loading dump..."
    docker cp "/" ":/tmp/neo4j.dump"
    docker exec "" neo4j-admin database load --from-path=/tmp neo4j --overwrite-destination

    echo "[INFO] Starting Neo4j..."
    docker exec "" neo4j start
    rm -f "/"
    echo "[INFO] Neo4j restore complete."
}

case "" in
    --restore) restore ;;
    *)         backup  ;;
esac
