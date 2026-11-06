#!/usr/bin/env python3
"""Codex PreToolUse adapter for the project guard.

The rules and their reason sentences live in .agent/scripts/guard_rules.py (spec 090-11);
this file only turns a Codex event into a call of those rules and the answer back into
Codex's PreToolUse JSON. The same rules run for Claude Code (.claude/hooks/guard.py) and
before every commit (.githooks/pre-commit -> .agent/scripts/git_precommit.py).

Event (Codex docs, 2026-11): `tool_name` is "Bash" for shell commands and "apply_patch" for
file edits; both carry `tool_input.command`. `.codex/hooks.json` matches exactly these two.
- Bash: rule 2 (ad-hoc CMake configure) and rule 4 (commit on main). A command given as a
  list of arguments is joined with shell quoting, so `["bash", "-lc", "git commit"]` keeps
  its script as one argument.
- apply_patch: rule 1 (machine paths) on the `+` lines of each Add File / Update File block,
  judged at its path (or its `*** Move to:` path) relative to the event's `cwd`, else the
  repo root. Delete File blocks add nothing and are not judged.

Codex must trust the project hook in /hooks before it runs (and again after it changes).
Codex does not document what a failing hook does, so this adapter fails open like the
Claude one: an import or input error lets the tool run and says why on stderr.
"""
from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".agent" / "scripts"))

try:
    import guard_rules as gr  # noqa: E402
except Exception as _import_error:  # fail open: a broken guard must not stop work
    gr = None
    _IMPORT_ERROR = _import_error

_LEAD = chr(0xFEFF) + " \t"  # a BOM, spaces and tabs before `*** Begin Patch`
_HEADERS = {"*** Add File:": "add", "*** Update File:": "update", "*** Delete File:": "delete"}


def check_command(command: str) -> str | None:
    return gr.check_command(command, "bash", root=ROOT)


def patch_blocks(patch_text: str) -> list[tuple[str, str, list[str]]]:
    """(kind, path, added lines) per file block of an apply_patch body; [] if it is not one."""
    # Split on '\n' only: str.splitlines() would also cut a '+' line at a form feed or U+2028.
    lines = [line.removesuffix("\r") for line in patch_text.split("\n")]
    # Text before the patch (a BOM, blank lines, a wrapper) is skipped up to `*** Begin Patch`.
    start = next((i for i, line in enumerate(lines) if line.lstrip(_LEAD).rstrip() == "*** Begin Patch"), None)
    if start is None:
        return []
    blocks: list[tuple[str, str, list[str]]] = []
    for line in lines[start + 1:]:
        # Headers start in column 0; a line starting with a space is context, even " *** End Patch".
        head = line.rstrip()
        if head == "*** End Patch":
            break
        prefix = next((p for p in _HEADERS if head.startswith(p)), None)
        if prefix is not None:
            blocks.append((_HEADERS[prefix], head[len(prefix):].strip(), []))
        elif head.startswith("*** Move to:") and blocks and blocks[-1][0] == "update":
            kind, _old, added = blocks[-1]
            blocks[-1] = (kind, head[len("*** Move to:"):].strip(), added)
        elif blocks and line.startswith("+"):
            blocks[-1][2].append(line[1:])
    return blocks


def check_patch(patch_text: str, cwd: str | None = None) -> str | None:
    base = Path(cwd) if cwd else ROOT
    for kind, raw_path, added in patch_blocks(patch_text):
        if kind == "delete":
            continue
        target = Path(raw_path)
        path = (target if target.is_absolute() else base / target).resolve()
        reason = gr.check_added_lines(path, added, root=ROOT)
        if reason:
            return reason
    return None


def decide(event: dict) -> str | None:
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    command = tool_input.get("command", "")
    if tool == "Bash":
        if isinstance(command, list):
            command = shlex.join(str(part) for part in command)
        return check_command(str(command))
    if tool == "apply_patch" and isinstance(command, str):
        return check_patch(command, cwd=event.get("cwd"))
    return None


def main() -> int:
    if gr is None:
        print(f"guard.py skipped: cannot import the guard rules: {_IMPORT_ERROR}", file=sys.stderr)
        return 0
    try:
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
