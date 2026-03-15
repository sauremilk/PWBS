#!/usr/bin/env python3
"""
Markiert einen Task als abgeschlossen und schreibt die Statusänderung atomar per git push.

Usage:
    python tools/orchestration/complete.py --orch ORCH-E --task TASK-041
    python tools/orchestration/complete.py --orch ORCH-E --task TASK-041 \\
        --notes "SearchService fertig – ORCH-G kann TASK-088 starten"
    python tools/orchestration/complete.py --orch ORCH-E --task TASK-041 --blocked \\
        --notes "Weaviate-Client fehlt, warte auf TASK-028 (ORCH-C)"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_STATE_PATH = REPO_ROOT / "docs" / "orchestration" / "task-state.json"


# ── Git-Helper ────────────────────────────────────────────────────────────────


def git(*args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ── State I/O ─────────────────────────────────────────────────────────────────


def read_state() -> dict:
    with open(TASK_STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def write_state(state: dict) -> None:
    with open(TASK_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


# ── Kern: Atomarer Complete / Blocked ─────────────────────────────────────────


def finalize(
    task_id: str,
    orchestrator: str,
    new_status: str,
    notes: str | None,
    max_retries: int = 3,
) -> bool:
    """
    Setzt den Task-Status auf `done` oder `blocked` und schreibt das Ergebnis
    atomar per git push.  Dieselbe Retry-Logik wie claim.py.
    """
    for attempt in range(1, max_retries + 1):
        # Schritt 1: Pull
        code, _out, err = git("pull", "--rebase")
        if code != 0:
            print(f"❌ git pull --rebase fehlgeschlagen:\n{err}")
            return False

        # Schritt 2: Frischen Zustand lesen
        state = read_state()
        task = state["tasks"].get(task_id)
        if not task:
            print(f"❌ Task {task_id} nicht in task-state.json gefunden.")
            return False

        # Schritt 3: Ownership-Check (Warnung, kein Hard-Fail)
        actual_owner = task.get("claimed_by")
        if actual_owner and actual_owner != orchestrator:
            print(
                f"⚠️  {task_id} ist geclaimed von '{actual_owner}', nicht von '{orchestrator}'. "
                "Mit Ctrl+C abbrechen, sonst wird fortgefahren..."
            )

        # Schritt 4: Status setzen
        task["status"] = new_status
        if new_status == "done":
            task["completed_at"] = datetime.now(timezone.utc).isoformat()
        if notes is not None:
            task["notes"] = notes

        write_state(state)

        # Schritt 5: Commit
        git("add", str(TASK_STATE_PATH))
        verb = "schließt ab" if new_status == "done" else "blockiert"
        code, _out, err = git(
            "commit", "-m", f"{new_status}: {orchestrator} {verb} {task_id}"
        )
        if code != 0:
            print(f"❌ git commit fehlgeschlagen: {err}")
            git("checkout", "--", str(TASK_STATE_PATH))
            return False

        # Schritt 6: Push
        code, _out, err = git("push")
        if code == 0:
            icon = "✅" if new_status == "done" else "⛔"
            print(f"{icon} {task_id} als '{new_status}' markiert von {orchestrator}.")
            if notes:
                print(f"   Notiz: {notes}")
            if new_status == "done":
                _print_unblocked_followups(task_id, state["tasks"])
            return True

        # Push fehlgeschlagen → Retry
        print(f"⚠️  Push-Konflikt (Versuch {attempt}/{max_retries}) – Reset & Retry...")
        git("reset", "HEAD~1")
        git("checkout", "--", str(TASK_STATE_PATH))
        if attempt < max_retries:
            sleep_s = 2**attempt
            print(f"   Warte {sleep_s}s...")
            time.sleep(sleep_s)

    print(f"❌ Finalize für {task_id} nach {max_retries} Versuchen fehlgeschlagen.")
    return False


def _print_unblocked_followups(completed_task_id: str, tasks: dict) -> None:
    """Zeigt Tasks, die durch diesen Abschluss neu freigeschaltet werden."""
    newly_unblocked = [
        (tid, t)
        for tid, t in tasks.items()
        if completed_task_id in t.get("blocked_by", [])
        and t.get("status") in ("open", "ready")
        and all(
            tasks.get(dep, {}).get("status") == "done"
            for dep in t.get("blocked_by", [])
        )
    ]
    if newly_unblocked:
        print("   Freigeschaltete Follow-up-Tasks:")
        for tid, t in sorted(newly_unblocked, key=lambda x: x[0]):
            stream = t.get("stream", "?")
            print(f"   🔓 {tid} [{stream}] {t.get('title', '?')}")


# ── Entry Point ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Markiert einen PWBS-Task als done oder blocked.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--orch", required=True, help="Orchestrator-Slot, z.B. ORCH-E")
    parser.add_argument(
        "--task", required=True, metavar="TASK_ID", help="Task-ID, z.B. TASK-041"
    )
    parser.add_argument(
        "--blocked",
        action="store_true",
        help="Task als 'blocked' statt 'done' markieren",
    )
    parser.add_argument(
        "--notes",
        metavar="TEXT",
        help="Optionale Notiz (Übergabe-Info oder Blocker-Beschreibung)",
    )
    args = parser.parse_args()

    new_status = "blocked" if args.blocked else "done"
    success = finalize(args.task, args.orch, new_status, args.notes)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
