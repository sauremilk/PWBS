"""Fix B904 (raise-without-from-inside-except) using ruff's JSON output.

Strategy: For each reported line, find the raise statement and the enclosing
except clause. If the except has `as <var>`, append `from <var>`. If no
variable, append `from None`.

The fix handles:
- Single-line raise: `raise HTTPException(...)` → `raise HTTPException(...) from err`
- Raise with type:ignore comment: keeps comment at end
- Multi-line raise (parenthesized): appends to the closing-paren line
- Celery self.retry: `raise self.retry(exc=exc)` → `raise self.retry(exc=exc) from exc`
"""

import json
import re
import subprocess
from pathlib import Path


def find_except_var(lines: list[str], raise_row: int) -> str | None:
    """Walk backwards from raise_row to find except ... as <var>:"""
    for i in range(raise_row - 1, max(raise_row - 50, -1), -1):
        line = lines[i]
        stripped = line.lstrip()
        if not stripped:
            continue
        # Found an except clause?
        m = re.match(r"except\s+[\w.,\s|()]+\s+as\s+(\w+)\s*:", stripped)
        if m:
            return m.group(1)
        m2 = re.match(r"except\s*:", stripped)
        if m2:
            return None
        m3 = re.match(r"except\s+[\w.,\s|()]+\s*:", stripped)
        if m3:
            return None
    return None


def find_raise_end(lines: list[str], start_row: int) -> int:
    """Find the line where the raise statement ends (handles multi-line parens)."""
    paren_depth = 0
    for i in range(start_row, min(start_row + 30, len(lines))):
        line = lines[i]
        # Strip strings and comments for paren counting
        code = re.sub(r"#.*$", "", line)
        code = re.sub(r'"[^"]*"', "", code)
        code = re.sub(r"'[^']*'", "", code)
        paren_depth += code.count("(") - code.count(")")
        if paren_depth <= 0:
            return i
    return start_row


def fix_b904():
    result = subprocess.run(
        ["ruff", "check", "backend/", "--select", "B904", "--output-format", "json"],
        capture_output=True,
        text=True,
    )
    errors = json.loads(result.stdout)
    print(f"B904 errors to fix: {len(errors)}")

    by_file: dict[str, list[int]] = {}
    for e in errors:
        by_file.setdefault(e["filename"], []).append(
            e["location"]["row"] - 1
        )  # 0-indexed

    for fn, rows in by_file.items():
        path = Path(fn)
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

        # Process from bottom to top to avoid line offset issues
        for raise_row in sorted(set(rows), reverse=True):
            if raise_row >= len(lines):
                continue

            line = lines[raise_row]

            # Already has 'from' in the actual code (not in comment)?
            code_part = line.split("#")[0] if "#" in line else line
            if " from " in code_part and "raise" in code_part:
                continue

            exc_var = find_except_var(lines, raise_row)
            from_clause = f" from {exc_var}" if exc_var else " from None"

            # Find where the raise statement ends (multi-line)
            end_row = find_raise_end(lines, raise_row)
            end_line = lines[end_row]

            # Split into code and comment
            # Handle type: ignore comments
            comment_match = re.search(r"\s*(#.*)$", end_line.rstrip("\n"))
            if comment_match:
                comment = comment_match.group(1)
                code = end_line[: comment_match.start(1)].rstrip()
                lines[end_row] = f"{code}{from_clause}  {comment}\n"
            else:
                code = end_line.rstrip("\n").rstrip()
                lines[end_row] = f"{code}{from_clause}\n"

        path.write_text("".join(lines), encoding="utf-8")
        print(f"  Fixed: {fn} ({len(rows)} errors)")

    print("Done!")


if __name__ == "__main__":
    fix_b904()
