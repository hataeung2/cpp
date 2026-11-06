#!/usr/bin/env python3
"""Claude Code PreToolUse adapter for the project guard.

The rules and their reason sentences live in .agent/scripts/guard_rules.py (spec 090-11);
this file only turns a Claude event into a call of those rules and the answer back into
Claude's PreToolUse JSON. The same rules run for Codex (.codex/hooks/guard.py) and before
every commit (.githooks/pre-commit -> .agent/scripts/git_precommit.py).

- Bash / PowerShell: no ad-hoc CMake configure (rule 2), no commit on main (rule 4).
  Commands are judged by what runs (.agent/scripts/shell_commands.py, spec 090-06): the
  program position; shell strings, substitutions and text fed to a shell are judged
  inside. Text that is only data — quoted arguments, quoted-delimiter heredoc bodies,
  `@'…'@` here-strings, comments — is not; substitutions inside an unquoted heredoc or
  `@"…"@` are. A command that cannot be split (or that the splitter fails on) is judged
  by the old regex on the whole text, which leans towards refusing.
- Write / Edit / MultiEdit: no machine-specific paths in repo files (rule 1); ignored files
  (CMakeUserPresets.json, out/) and files outside the repo are not checked (and not read).

A denial is returned as PreToolUse JSON with the reason. An error in the guard itself
(import, bad input) lets the tool run (fail open): a broken guard must not stop work;
the docs lint still checks.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agent" / "scripts"))

try:
    import agent_common as ac  # noqa: E402  (tests patch ac.git / ac.is_ignored here; guard_rules uses the same module)
    import guard_rules as gr  # noqa: E402
except Exception as _import_error:  # fail open: a broken guard must not stop work
    ac = gr = None
    _IMPORT_ERROR = _import_error


def check_command(command: str, shell: str = "bash") -> str | None:
    return gr.check_command(command, shell, root=ROOT)


def inside_repo(path: Path) -> bool:
    return gr.inside_repo(path, root=ROOT)


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


def check_write(tool: str, tool_input: dict) -> str | None:
    raw = tool_input.get("file_path")
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw)
    # Decide whether the rule applies before reading the file (as before 090-11). This is
    # guard_rules.is_checked_file spelled out through this module's inside_repo and ac, the
    # names the hook tests patch; keep the two in step.
    if not inside_repo(path) or ac.is_ignored(path, root=ROOT):
        return None
    return gr.machine_path_reason(written_lines(tool, path, tool_input))


def decide(event: dict) -> str | None:
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    if tool in ("Bash", "PowerShell"):
        shell = "powershell" if tool == "PowerShell" else "bash"
        return check_command(str(tool_input.get("command", "")), shell)
    if tool in ("Write", "Edit", "MultiEdit"):
        return check_write(tool, tool_input)
    return None


def main() -> int:
    if gr is None:
        print(f"guard.py skipped: cannot import the guard rules: {_IMPORT_ERROR}", file=sys.stderr)
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
