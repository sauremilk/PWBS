#!/usr/bin/env python3
"""
Pre-Push-Boundary-Validator für PWBS-Orchestratoren.

Prüft, ob die im Staging-Bereich oder letzten Commits geänderten Dateien
zum deklarierten Stream des Orchestrators gehören.

Kann als git pre-push Hook oder manuell aufgerufen werden:
    python tools/orchestration/validate_stream.py --orch ORCH-E
    python tools/orchestration/validate_stream.py --orch ORCH-E --commit HEAD~3..HEAD
    python tools/orchestration/validate_stream.py --list-patterns  # Pattern-Übersicht

Als pre-push Hook einbinden (.git/hooks/pre-push oder über pre-commit):
    ORCH_SLOT=ORCH-E python tools/orchestration/validate_stream.py --from-hook
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_STATE_PATH = REPO_ROOT / "docs" / "orchestration" / "task-state.json"

# Dateipfad-Muster pro Stream.
# Diese Muster definieren den exklusiven Arbeitsbereich jedes Orchestrators.
# Dateien, die auf kein Muster passen, gelten als "shared" und sind für alle erlaubt.
STREAM_FILE_PATTERNS: dict[str, list[str]] = {
    "STREAM-FOUNDATION": [
        "docs/",
        "poc/",
        "vision-wissens-os.md",
        "PRD-SPEC.md",
        "ROADMAP.md",
        "ARCHITECTURE.md",
    ],
    "STREAM-INFRA": [
        "Dockerfile",
        "docker-compose",
        ".github/workflows/",
        "infra/",
        "deploy/",
        "Makefile",
        ".env",
        "backend/Dockerfile",
        "frontend/Dockerfile",
        "backend/pyproject.toml",
        "frontend/package.json",
    ],
    "STREAM-DB": [
        "backend/migrations/",
        "backend/pwbs/db/",
        "backend/alembic.ini",
    ],
    "STREAM-MODELS": [
        "backend/pwbs/models/",
        "backend/pwbs/schemas/",
        "backend/pwbs/core/",
    ],
    "STREAM-CONNECTORS": [
        "backend/pwbs/connectors/",
        "backend/pwbs/ingestion/",
    ],
    "STREAM-PROCESSING": [
        "backend/pwbs/processing/",
        "backend/pwbs/briefing/",
        "backend/pwbs/search/",
        "backend/pwbs/graph/",
        "backend/pwbs/prompts/",
    ],
    "STREAM-AUTH-API": [
        "backend/pwbs/api/",
        "backend/pwbs/core/auth",
        "backend/pwbs/core/security",
    ],
    "STREAM-FRONTEND": [
        "frontend/src/",
        "frontend/public/",
        "frontend/e2e/",
    ],
    "STREAM-DSGVO-QA": [
        "backend/tests/",
        "backend/pwbs/dsgvo/",
        "backend/pwbs/audit/",
        "tests/",
        "legal/",
    ],
    "STREAM-PHASE3": [
        "backend/pwbs/queue/",
        "backend/pwbs/integrations/",
    ],
    "STREAM-PHASE4": [
        "desktop-app/",
        "mobile-app/",
        "browser-extension/",
    ],
    "STREAM-PHASE5": [
        "backend/pwbs/marketplace/",
        "backend/pwbs/billing/",
        "backend/pwbs/analytics/",
        "backend/pwbs/developer/",
        "backend/pwbs/feature_flags/",
    ],
}

# Dateien, die für ALLE Streams erlaubt sind (Koordinationsinfrastruktur)
SHARED_PATTERNS: list[str] = [
    "docs/orchestration/task-state.json",
    "docs/orchestration/",
    "ORCHESTRATION.md",
    "AGENTS.md",
    "CHANGELOG.md",
    "README.md",
    "tasks.md",
    ".gitignore",
    ".editorconfig",
    ".pre-commit-config.yaml",
    "tools/",
]


def git(*args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def read_state() -> dict:
    with open(TASK_STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_orch_stream(orchestrator: str, state: dict) -> str | None:
    """Ermittelt den Stream eines Orchestrators aus task-state.json."""
    for stream_id, stream_info in state.get("streams", {}).items():
        if stream_info.get("orchestrator_slot") == orchestrator:
            return stream_id
    return None


def get_changed_files(commit_range: str | None = None) -> list[str]:
    """Gibt Liste der geänderten Dateien zurück (staged oder in Commit-Range)."""
    if commit_range:
        code, out, _ = git("diff", "--name-only", commit_range)
    else:
        # staged + unstaged geänderte Dateien
        code, staged, _ = git("diff", "--name-only", "--cached")
        _, unstaged, _ = git("diff", "--name-only")
        out = "\n".join(filter(None, [staged, unstaged]))
        code = 0
    if code != 0 or not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def is_allowed_for_stream(file_path: str, stream: str) -> tuple[bool, str]:
    """
    Prüft, ob eine Datei für den angegebenen Stream erlaubt ist.

    Returns:
        (erlaubt, grund)
    """
    # 1. Shared files sind immer erlaubt
    for pattern in SHARED_PATTERNS:
        if file_path.startswith(pattern) or file_path == pattern:
            return True, "shared"

    # 2. Stream-eigene Dateien
    own_patterns = STREAM_FILE_PATTERNS.get(stream, [])
    for pattern in own_patterns:
        if file_path.startswith(pattern) or file_path == pattern:
            return True, "own-stream"

    # 3. Prüfen, ob Datei exklusiv zu einem ANDEREN Stream gehört
    for other_stream, patterns in STREAM_FILE_PATTERNS.items():
        if other_stream == stream:
            continue
        for pattern in patterns:
            if file_path.startswith(pattern) or file_path == pattern:
                return False, f"belongs-to-{other_stream}"

    # 4. Unbekannte Datei → erlaubt (nicht zugeordnet)
    return True, "unassigned"


def validate(
    orchestrator: str,
    commit_range: str | None = None,
    strict: bool = False,
) -> bool:
    """
    Validiert, ob die Dateiänderungen zum Stream des Orchestrators passen.

    Args:
        orchestrator: z.B. "ORCH-E"
        commit_range: z.B. "HEAD~3..HEAD" (None = staged files)
        strict: Bei True wird auf Fehler statt Warnung eskaliert

    Returns:
        True wenn alles ok, False bei Verletzungen
    """
    state = read_state()
    stream = get_orch_stream(orchestrator, state)

    if not stream:
        print(
            f"⚠️  Orchestrator '{orchestrator}' keinem Stream zugeordnet – Validierung übersprungen."
        )
        return True

    changed = get_changed_files(commit_range)
    if not changed:
        print("ℹ️  Keine geänderten Dateien gefunden.")
        return True

    violations: list[tuple[str, str]] = []
    ok_files: list[str] = []

    for f in changed:
        allowed, reason = is_allowed_for_stream(f, stream)
        if not allowed:
            violations.append((f, reason))
        else:
            ok_files.append(f)

    if not violations:
        print(
            f"✅ Stream-Validierung OK ({orchestrator} → {stream}): {len(ok_files)} Datei(en) geprüft."
        )
        return True

    print(
        f"{'❌' if strict else '⚠️ '} Stream-Boundary-Verletzung! ({orchestrator} → {stream})"
    )
    print(f"   Folgende Dateien gehören NICHT zu {stream}:\n")
    for f, reason in violations:
        other_stream = reason.replace("belongs-to-", "")
        print(f"   ✗ {f}")
        print(f"     → Gehört zu: {other_stream}")
    print()
    print(
        "   Wenn dies absichtlich ist (z.B. Cross-Stream-Bugfix), "
        "füge '--no-verify' zum git push hinzu und dokumentiere es im Commit-Message."
    )

    return not strict


def list_patterns() -> None:
    """Gibt die Stream-Patterns tabellarisch aus."""
    print("\nStream-Dateipfad-Muster:\n")
    for stream, patterns in STREAM_FILE_PATTERNS.items():
        print(f"  {stream}:")
        for p in patterns:
            print(f"    {p}")
    print("\n  Shared (alle Streams):")
    for p in SHARED_PATTERNS:
        print(f"    {p}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validiert Stream-Grenzen für PWBS-Orchestratoren.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--orch",
        metavar="SLOT",
        help="Orchestrator-Slot, z.B. ORCH-E (oder Env-Var ORCH_SLOT)",
    )
    parser.add_argument(
        "--commit",
        metavar="RANGE",
        help="Git-Commit-Range, z.B. HEAD~3..HEAD (Standard: staged files)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fehler (exit 1) statt Warnung bei Verletzungen",
    )
    parser.add_argument(
        "--from-hook",
        action="store_true",
        help="Aufruf als git hook (liest ORCH_SLOT aus Umgebungsvariable)",
    )
    parser.add_argument(
        "--list-patterns",
        action="store_true",
        help="Stream-Muster auflisten und beenden",
    )
    args = parser.parse_args()

    if args.list_patterns:
        list_patterns()
        return

    orch = args.orch or os.environ.get("ORCH_SLOT")
    if not orch:
        if args.from_hook:
            # Im Hook-Modus ohne ORCH_SLOT: stillschweigend überspringen
            sys.exit(0)
        parser.error("--orch oder Umgebungsvariable ORCH_SLOT erforderlich")

    ok = validate(orch, commit_range=args.commit, strict=args.strict)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
