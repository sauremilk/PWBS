#!/usr/bin/env python3
"""
Echtzeit-Übersicht über den Orchestrierungs-Zustand im PWBS.

Usage:
    python tools/orchestration/status.py                     # Alle Streams
    python tools/orchestration/status.py --stream STREAM-CONNECTORS
    python tools/orchestration/status.py --stale             # Nur stale Tasks anzeigen
    python tools/orchestration/status.py --in-progress       # Nur aktive Claims
    python tools/orchestration/status.py --blocked           # Nur blockierte Tasks
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_STATE_PATH = REPO_ROOT / "docs" / "orchestration" / "task-state.json"

STALE_THRESHOLD_HOURS = 4

# ANSI-Farben (funktionieren in Windows Terminal und VS Code)
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


def read_state() -> dict:
    with open(TASK_STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


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


def ago(iso_str: str | None) -> str:
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        if hours >= 24:
            return f"{hours // 24}d {hours % 24}h ago"
        elif hours > 0:
            return f"{hours}h {minutes}m ago"
        else:
            return f"{minutes}m ago"
    except (ValueError, TypeError):
        return iso_str or ""


def status_icon(status: str, task: dict) -> str:
    if is_stale(task):
        return f"{RED}⚠ stale {RESET}"
    icons = {
        "open": f"{GRAY}○ open   {RESET}",
        "ready": f"{CYAN}◎ ready  {RESET}",
        "in_progress": f"{YELLOW}● running{RESET}",
        "done": f"{GREEN}✓ done   {RESET}",
        "blocked": f"{RED}✗ blocked{RESET}",
        "skipped": f"{GRAY}– skipped{RESET}",
    }
    return icons.get(status, status)


def print_stream_summary(stream_name: str, tasks: list[tuple[str, dict]]) -> None:
    total = len(tasks)
    done = sum(1 for _, t in tasks if t["status"] == "done")
    ip = sum(1 for _, t in tasks if t["status"] == "in_progress")
    blocked = sum(1 for _, t in tasks if t["status"] == "blocked")
    open_ = sum(1 for _, t in tasks if t["status"] in ("open", "ready"))
    stale = sum(1 for _, t in tasks if is_stale(t))

    pct = int(done / total * 100) if total else 0
    bar_width = 20
    filled = int(bar_width * done / total) if total else 0
    bar = GREEN + "█" * filled + GRAY + "░" * (bar_width - filled) + RESET

    stale_flag = f" {RED}⚠ {stale} stale{RESET}" if stale else ""
    print(
        f"{BOLD}{stream_name:<28}{RESET}  {bar}  "
        f"{pct:3}%  done={done}/{total}  "
        f"run={ip}  blocked={blocked}  open={open_}"
        f"{stale_flag}"
    )


def print_task_detail(tid: str, task: dict) -> None:
    stale = is_stale(task)
    icon = status_icon(task["status"], task)
    cb = task.get("claimed_by", "")
    claimed_info = f" [{cb} · {ago(task.get('claimed_at'))}]" if cb else ""
    stale_warn = f" {RED}[STALE >{STALE_THRESHOLD_HOURS}h]{RESET}" if stale else ""
    print(f"  {icon}  {tid}  {task.get('title', '')[:60]}{claimed_info}{stale_warn}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PWBS Orchestrierungs-Statusübersicht",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--stream", metavar="STREAM", help="Nur diesen Stream anzeigen")
    parser.add_argument(
        "--stale", action="store_true", help="Nur stale in_progress Tasks"
    )
    parser.add_argument(
        "--in-progress",
        dest="in_progress",
        action="store_true",
        help="Nur aktive Claims",
    )
    parser.add_argument("--blocked", action="store_true", help="Nur blockierte Tasks")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Alle Tasks auflisten"
    )
    args = parser.parse_args()

    state = read_state()
    tasks_all = state["tasks"]
    streams = state.get("streams", {})

    # ── Filterung ─────────────────────────────────────────────────────────────
    if args.stale:
        stale_tasks = [(tid, t) for tid, t in tasks_all.items() if is_stale(t)]
        if not stale_tasks:
            print(
                f"{GREEN}✓ Keine stale Tasks (< {STALE_THRESHOLD_HOURS}h in_progress){RESET}"
            )
            return
        print(f"{RED}{BOLD}Stale Tasks (>{STALE_THRESHOLD_HOURS}h in_progress):{RESET}")
        for tid, t in sorted(stale_tasks, key=lambda x: x[1].get("claimed_at", "")):
            print_task_detail(tid, t)
        return

    if args.in_progress:
        ip_tasks = [
            (tid, t) for tid, t in tasks_all.items() if t["status"] == "in_progress"
        ]
        if not ip_tasks:
            print(f"{GRAY}Kein Task aktiv.{RESET}")
            return
        print(f"{YELLOW}{BOLD}Aktive Claims:{RESET}")
        for tid, t in sorted(ip_tasks, key=lambda x: x[0]):
            print_task_detail(tid, t)
        return

    if args.blocked:
        blocked_tasks = [
            (tid, t) for tid, t in tasks_all.items() if t["status"] == "blocked"
        ]
        if not blocked_tasks:
            print(f"{GREEN}✓ Keine blockierten Tasks{RESET}")
            return
        print(f"{RED}{BOLD}Blockierte Tasks:{RESET}")
        for tid, t in sorted(blocked_tasks, key=lambda x: x[0]):
            notes = t.get("notes", "")
            print_task_detail(tid, t)
            if notes:
                print(f"          {GRAY}Notiz: {notes}{RESET}")
        return

    # ── Stream-Zusammenfassung ─────────────────────────────────────────────────
    filter_stream = args.stream

    print(
        f"\n{BOLD}PWBS Orchestrierungs-Status – {datetime.now().strftime('%Y-%m-%d %H:%M')}{RESET}\n"
    )

    for stream_id, stream_info in streams.items():
        if filter_stream and stream_id != filter_stream:
            continue

        stream_tasks = [
            (tid, t) for tid, t in tasks_all.items() if t.get("stream") == stream_id
        ]
        stream_tasks.sort(key=lambda x: x[0])

        orch_slot = stream_info.get("orchestrator_slot", "?")
        print_stream_summary(f"{stream_id} ({orch_slot})", stream_tasks)

        if args.verbose or filter_stream:
            for tid, t in stream_tasks:
                if not args.verbose and t["status"] == "done":
                    continue
                print_task_detail(tid, t)
                if t.get("notes") and t["status"] in ("blocked", "in_progress"):
                    print(f"          {GRAY}{t['notes']}{RESET}")
            if filter_stream:
                print()

    # ── Gesamt-Footer ──────────────────────────────────────────────────────────
    if not filter_stream:
        total = len(tasks_all)
        done_count = sum(1 for t in tasks_all.values() if t["status"] == "done")
        ip_count = sum(1 for t in tasks_all.values() if t["status"] == "in_progress")
        blocked_count = sum(1 for t in tasks_all.values() if t["status"] == "blocked")
        stale_count = sum(1 for t in tasks_all.values() if is_stale(t))
        open_count = sum(
            1 for t in tasks_all.values() if t["status"] in ("open", "ready")
        )

        print(
            f"\n{BOLD}Gesamt:{RESET} {done_count}/{total} done  "
            f"| {ip_count} aktiv  | {blocked_count} blockiert  | {open_count} offen",
            end="",
        )
        if stale_count > 0:
            print(f"  | {RED}{stale_count} STALE{RESET}", end="")
        print()
        print()


if __name__ == "__main__":
    main()
