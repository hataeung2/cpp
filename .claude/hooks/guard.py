#!/usr/bin/env python3
"""PreToolUse guard: enforces the machine-checkable non-negotiable rules
(docs/agent_start_prompt.md) before a tool runs.

- Bash / PowerShell: no ad-hoc CMake configure (rule 2), no commit on main (rule 4).
- Write / Edit: no machine-specific paths in repo files (rule 1); ignored files
  (CMakeUserPresets.json, out/) and files outside the repo are not checked.

A denial is returned as PreToolUse JSON with the reason. Any internal error lets the
tool run (fail open): a broken guard must not stop work; the docs lint still checks.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agent" / "scripts"))

try:
    import agent_common as ac  # noqa: E402
except Exception as _import_error:  # fail open: a broken guard must not stop work
    ac = None
    _IMPORT_ERROR = _import_error

GIT_COMMIT_RE = re.compile(r"\bgit\b[^|;&\n]*\scommit\b")
PROTECTED_BRANCHES = {"main", "master"}


def check_command(command: str) -> str | None:
    if ac.is_adhoc_cmake(command):
        return ("Ad-hoc CMake configure is not allowed (non-negotiable rule 2). "
                "Use `py -3 .agent/scripts/build.py --preset <name>` or `cmake --preset <name>`; "
                "add a preset to CMakePresets.json if none fits.")
    if GIT_COMMIT_RE.search(command):
        branch = ac.git("rev-parse", "--abbrev-ref", "HEAD", root=ROOT).stdout.strip()
        if branch in PROTECTED_BRANCHES:
            return (f"Committing on {branch} is not allowed (non-negotiable rule 4). "
                    "Create the task branch feature/NNN-SS-<slug> first.")
    return None


def written_lines(tool: str, path: Path, tool_input: dict) -> list[str]:
    """Lines the tool call would add to the file.

    Write: the whole content. Edit / MultiEdit: the edits are applied to the current file
    and the lines that did not exist before are returned, so a path assembled across the
    edit boundary (old text + new text) is seen too. Without a readable file or a matching
    old_string, the new_string text itself is checked.
    """
    if tool == "Write":
        return str(tool_input.get("content", "")).splitlines()
    edits = tool_input.get("edits") if tool == "MultiEdit" else [tool_input]
    edits = [e for e in (edits or []) if isinstance(e, dict)]
    try:
        before = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return [line for e in edits for line in str(e.get("new_string", "")).splitlines()]
    after, unmatched = before, []
    for e in edits:
        old, new = str(e.get("old_string", "")), str(e.get("new_string", ""))
        if old and old in after:
            after = after.replace(old, new) if e.get("replace_all") else after.replace(old, new, 1)
        else:
            unmatched += new.splitlines()
    # Count lines, not just their presence: copying an existing line adds one more copy.
    remaining = Counter(before.splitlines())
    added = []
    for line in after.splitlines():
        if remaining[line] > 0:
            remaining[line] -= 1
        else:
            added.append(line)
    return added + unmatched


def inside_repo(path: Path) -> bool:
    root = str(ROOT.resolve()).replace("\\", "/").lower().rstrip("/") + "/"
    return str(path.resolve()).replace("\\", "/").lower().startswith(root)


def check_write(tool: str, tool_input: dict) -> str | None:
    raw = tool_input.get("file_path")
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    if not inside_repo(path) or ac.is_ignored(path, root=ROOT):
        return None
    hits = [hit for line in written_lines(tool, path, tool_input) for hit in ac.machine_paths(line)]
    if not hits:
        return None
    shown = ", ".join(sorted(set(hits))[:3])
    return (f"Machine-specific path ({shown}) in a repo file is not allowed (non-negotiable rule 1). "
            "Use a project-relative path, an env var (VCPKG_ROOT, VSDEVCMD) or a <placeholder>; "
            "machine-only settings belong in the untracked CMakeUserPresets.json.")


def decide(event: dict) -> str | None:
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    if tool in ("Bash", "PowerShell"):
        return check_command(str(tool_input.get("command", "")))
    if tool in ("Write", "Edit", "MultiEdit"):
        return check_write(tool, tool_input)
    return None


def main() -> int:
    if ac is None:
        print(f"guard.py skipped: cannot import agent_common: {_IMPORT_ERROR}", file=sys.stderr)
        return 0
    try:
        # Claude Code sends UTF-8; do not depend on the console code page.
        reason = decide(json.loads(sys.stdin.buffer.read().decode("utf-8")))
    except Exception as exc:  # fail open, but say why
        print(f"guard.py skipped: {exc}", file=sys.stderr)
        return 0
    if reason:
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
