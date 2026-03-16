"""
Interner pytest-Runner fuer t.ps1.

Aufruf:
    python _pytest_run.py <test_path> <tb_mode> <out_file> [--no-cache]

Gibt den vollstaendigen pytest-Output nach stdout (fuer t.ps1-Filter) UND
in <out_file> aus. Exit-Code entspricht dem pytest-Exit-Code.
"""

import re
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: _pytest_run.py <test_path> <tb_mode> <out_file>", file=sys.stderr)
        return 2

    test_path = sys.argv[1]
    tb_mode = sys.argv[2]
    out_file = sys.argv[3]

    script_dir = Path(__file__).resolve().parent

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        test_path,
        f"--tb={tb_mode}",
        "-p",
        "no:cacheprovider",
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(script_dir),
    )

    stdout_data = ""
    stderr_data = ""
    exit_code = 1

    try:
        stdout_data, stderr_data = proc.communicate(timeout=600)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout_data, stderr_data = proc.communicate()
        stderr_data = "TIMEOUT (600s)\n" + stderr_data
    except KeyboardInterrupt:
        proc.terminate()
        try:
            stdout_data, stderr_data = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
        stderr_data = "INTERRUPTED\n" + stderr_data

    combined = stdout_data
    if stderr_data.strip():
        combined += "\n--- STDERR ---\n" + stderr_data

    Path(out_file).write_text(combined, encoding="utf-8")

    # Gefilterte Zusammenfassung nach stdout schreiben (wird von t.ps1 gelesen)
    lines = combined.splitlines()
    in_summary = False
    printed: list[str] = []

    for line in lines:
        if re.match(r"^=+ short test summary", line):
            in_summary = True
            continue
        if re.match(r"^=+\s+\d+ (passed|failed|error)", line):
            in_summary = False
            printed.append(line)
            continue
        if in_summary or re.match(r"^(FAILED|ERROR)\s", line):
            printed.append(line)

    if not printed:
        # Fallback: letzte nicht-leere Zusammenfassungszeile
        for line in reversed(lines):
            if line.strip() and re.search(r"\d+ (passed|failed|error)", line):
                printed.append(line)
                break

    for line in dict.fromkeys(printed):  # Reihenfolge beibehalten, Duplikate entfernen
        print(line)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
