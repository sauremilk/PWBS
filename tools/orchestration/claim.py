#!/usr/bin/env python3
"""
Atomares Task-Claiming für PWBS-Multi-Orchestrator-Sessions.

Das Push-Gate-Prinzip: git push ist der atomare Linearisierungspunkt.
Schlägt der Push fehl (anderer Agent war schneller), wird der Claim
zurückgesetzt und der gesamte Claim-Zyklus neu gestartet.

Usage:
    python tools/orchestration/claim.py --orch ORCH-E --stream STREAM-CONNECTORS
    python tools/orchestration/claim.py --orch ORCH-E --task TASK-041
    python tools/orchestration/claim.py --orch ORCH-E --stream STREAM-CONNECTORS --dry-run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_STATE_PATH = REPO_ROOT / "docs" / "orchestration" / "task-state.json"

# Tasks, die länger als diesen Schwellwert in in_progress verweilen, gelten als stale.
STALE_THRESHOLD_HOURS = 4

PRIORITY_ORDER: dict[str, int] = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


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


# ── Task-Logik ────────────────────────────────────────────────────────────────


def is_unblocked(task_id: str, tasks: dict) -> bool:
    return all(
        tasks.get(dep, {}).get("status") == "done"
        for dep in tasks[task_id].get("blocked_by", [])
    )


def is_stale(task: dict) -> bool:
    if task.get("status") != "in_progress" or not task.get("claimed_at"):
        return False
    try:
        claimed = datetime.fromisoformat(task["claimed_at"])
        if claimed.tzinfo is None:
            claimed = claimed.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - claimed) > timedelta(
            hours=STALE_THRESHOLD_HOURS
        )
    except (ValueError, TypeError):
        return False


def find_open_task(stream: str, tasks: dict) -> str | None:
    """Findet den nächsten verfügbaren, unblockierten Task im Stream (P0 > P3, TASK-n aufsteigend)."""
    candidates = [
        (tid, t)
        for tid, t in tasks.items()
        if t.get("stream") == stream
        and t.get("status") in ("open", "ready")
        and is_unblocked(tid, tasks)
    ]

    stale_tasks = [
        (tid, t)
        for tid, t in tasks.items()
        if t.get("stream") == stream and is_stale(t)
    ]
    if stale_tasks:
        print(
            f"⚠️  {len(stale_tasks)} stale Task(s) gefunden "
            f"(>{STALE_THRESHOLD_HOURS}h ohne Abschluss):"
        )
        for tid, t in stale_tasks:
            print(
                f"   {tid} – geclaimed von {t.get('claimed_by', '?')} seit {t.get('claimed_at', '?')}"
            )
        print("   → Manuell prüfen: python tools/orchestration/status.py --stale")

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (PRIORITY_ORDER.get(x[1].get("priority", "P3"), 3), x[0])
    )
    return candidates[0][0]


# ── Kern: Atomarer Claim ──────────────────────────────────────────────────────


def claim(task_id: str, orchestrator: str, dry_run: bool = False) -> bool:
    """
    Versucht, einen Task atomar zu claimen.

    Ablauf:
      1. git pull --rebase  (aktuelle Basis holen)
      2. task-state.json lesen
      3. Status prüfen (noch open/ready?)
      4. Claim schreiben
      5. git commit + git push
      6. Bei Push-Fehler: Commit zurückrollen, kurz warten, nochmal ab Schritt 1

    Der git push fungiert als verteiltes Commit / Linearisierungspunkt.
    """
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        # Schritt 1: Pull
        code, _out, err = git("pull", "--rebase")
        if code != 0:
            print(f"❌ git pull --rebase fehlgeschlagen:\n{err}")
            return False

        # Schritt 2: Frischen Zustand lesen
        state = read_state()
        tasks = state["tasks"]
        task = tasks.get(task_id)
        if not task:
            print(f"❌ Task {task_id} nicht in task-state.json gefunden.")
            return False

        # Schritt 3: Verfügbarkeit prüfen
        current_status = task.get("status")
        if current_status not in ("open", "ready"):
            claimed_by = task.get("claimed_by", "?")
            print(
                f"❌ {task_id} ist nicht mehr verfügbar "
                f"(status={current_status}, claimed_by={claimed_by})"
            )
            if is_stale(task):
                print(
                    f"   → Task scheint stale (>{STALE_THRESHOLD_HOURS}h in_progress). "
                    "Manuellen Reset via status.py erwägen."
                )
            return False

        # Schritt 4: Claim schreiben
        tasks[task_id].update(
            {
                "status": "in_progress",
                "claimed_by": orchestrator,
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        if dry_run:
            print(f"[dry-run] Würde {task_id} für {orchestrator} claimen.")
            print(f"          Titel: {task.get('title', '?')}")
            # Änderungen nicht wegschreiben
            return True

        write_state(state)

        # Schritt 5: Commit
        git("add", str(TASK_STATE_PATH))
        code, _out, err = git(
            "commit", "-m", f"claim: {orchestrator} nimmt {task_id} in Bearbeitung"
        )
        if code != 0:
            print(f"❌ git commit fehlgeschlagen: {err}")
            git("checkout", "--", str(TASK_STATE_PATH))
            return False

        # Schritt 6: Push – atomarer Linearisierungspunkt
        code, _out, err = git("push")
        if code == 0:
            print(f"✅ {task_id} erfolgreich geclaimed von {orchestrator}")
            print(f"   Titel:    {task.get('title', '?')}")
            print(f"   Stream:   {task.get('stream', '?')}")
            print(
                f"   Priorität:{task.get('priority', '?')}  Aufwand: {task.get('effort', '?')}"
            )
            return True

        # Push fehlgeschlagen → anderer Agent war schneller
        print(
            f"⚠️  Push-Konflikt (Versuch {attempt}/{max_retries}) – "
            "anderer Orchestrator hat zuerst committed. Reset & Retry..."
        )
        git(
            "reset", "HEAD~1"
        )  # Commit rückgängig machen (Änderungen bleiben im Working Tree)
        git("checkout", "--", str(TASK_STATE_PATH))  # Dateiänderung verwerfen

        if attempt < max_retries:
            sleep_s = 2**attempt  # 2s → 4s → (kein weiterer Versuch)
            print(f"   Warte {sleep_s}s vor nächstem Versuch...")
            time.sleep(sleep_s)

    print(
        f"❌ Claim für {task_id} nach {max_retries} Versuchen fehlgeschlagen. "
        "Vermutlich von anderem Orchestrator geclaimed – nächsten Task suchen."
    )
    return False


# ── Entry Point ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atomic task claiming for PWBS orchestrators.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--orch", required=True, help="Orchestrator-Slot, z.B. ORCH-E")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--stream",
        metavar="STREAM",
        help="Auto-Auswahl: nächster Task im Stream, z.B. STREAM-CONNECTORS",
    )
    group.add_argument(
        "--task",
        metavar="TASK_ID",
        help="Direkter Claim eines bestimmten Tasks, z.B. TASK-041",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Nur simulieren, kein Commit/Push"
    )
    args = parser.parse_args()

    # Lokalen Zustand laden (ohne Pull – erst im Claim-Loop)
    state = read_state()

    if args.task:
        task_id = args.task
        task = state["tasks"].get(task_id)
        if not task:
            print(f"❌ Task {task_id} nicht in task-state.json gefunden.")
            sys.exit(1)
        print(f"📋 Direkter Claim: {task_id} – {task.get('title', '?')}")
    else:
        task_id = find_open_task(args.stream, state["tasks"])
        if not task_id:
            print(
                f"ℹ️  Kein offener, unblockierter Task in Stream '{args.stream}' gefunden."
            )
            sys.exit(0)
        print(
            f"📋 Nächster Task: {task_id} – {state['tasks'][task_id].get('title', '?')}"
        )

    success = claim(task_id, args.orch, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
