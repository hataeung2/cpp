#!/usr/bin/env python3
"""Shared helpers for the agent scripts (lint_docs.py, build.py, .claude/hooks/guard.py).

Stdlib only. Rules: docs/agent_start_prompt.md (non-negotiable rules), .agent/rules/spec.md.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# A machine-specific path: drive letter path (also JSON-escaped, drive + two backslashes),
# file URL, or a home directory. The look-behind keeps URL schemes ("https://") from
# matching as a drive letter. The pattern is assembled from pieces so that this source
# line does not itself look like a machine path to the guard hook.
_FILE_URL = "file:" + "///"
_HOME = "/" + "home/"
_USERS = "Us" + "ers"
MACHINE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]"
    + "|" + re.escape(_FILE_URL)
    + "|" + re.escape(_HOME) + r"[a-z_][a-z0-9_-]*/"
    + "|" + r"\\{1,2}" + _USERS + r"\\{1,2}[^\\\s]+\\"
    + "|/" + _USERS + r"/[^/\s]+/"
)

# A prohibition may quote the forbidden example in a code span ("NEVER use `<drive>/`").
# Only hits inside a code span on such a line are exempt.
PROHIBITION_RE = re.compile(r"\b(never|do not|don't|no|not)\b|forbidden", re.IGNORECASE)
CODE_SPAN_RE = re.compile(r"`[^`]*`")

# Ad-hoc CMake configure (rule 2): `cmake -S`, `cmake -B`, `cmake ..`.
ADHOC_CMAKE_RE = re.compile(r"\bcmake(?:\.exe)?\s+(?:[^|;&\n]*\s)?(?:-S|-B)\s*\S|\bcmake(?:\.exe)?\s+\.\.(?:\s|$)")

TASK_ID = r"\d{3}-\d{2}(?:-\d{2})?"
STATES = ("BACKLOG", "SPEC_DRAFT", "APPROVED", "DEV", "TEST", "DONE", "BLOCKED")
TASK_LINE_RE = re.compile(
    rf"^(?P<indent>\s*)- !(?P<state>[A-Z_]+) \| (?P<id>{TASK_ID}) \| (?P<rest>.+)$"
)
LINK_RE = re.compile(r"\[(?P<text>(?:[^\[\]]|\[[^\]]*\])*)\]\((?P<target>[^)\s]+)\)")
GROUP_HEADING_RE = re.compile(r"^## .*\((?P<done>\d+)/(?P<total>\d+) DONE\)\s*$")


def machine_paths(line: str) -> list[str]:
    """Machine-specific paths in a line, except a bare example quoted in a prohibition.

    Exempt only when the line forbids something and the hit is a whole code span by
    itself (a span holding just the drive or prefix); a span with a usable path or a
    command in it (`VAR=<drive>/x`) is still reported.
    """
    bare_spans: list[tuple[int, int]] = []
    if PROHIBITION_RE.search(line):
        bare_spans = [m.span(1) for m in re.finditer(r"`([^`]*)`", line)
                      if MACHINE_PATH_RE.fullmatch(m.group(1))]
    return [m.group(0) for m in MACHINE_PATH_RE.finditer(line) if m.span() not in bare_spans]


def is_adhoc_cmake(command: str) -> bool:
    return bool(ADHOC_CMAKE_RE.search(command))


def git(*args: str, root: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    """Run git in the repo; safe.directory avoids the dubious-ownership refusal."""
    return subprocess.run(
        ["git", "-c", f"safe.directory={root.as_posix()}", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def repo_files(root: Path = REPO_ROOT) -> list[Path]:
    """Tracked files plus untracked files that are not ignored."""
    # core.quotepath=off: non-ASCII (e.g. Korean) names come back unquoted and usable.
    result = git("-c", "core.quotepath=off", "ls-files", "--cached", "--others", "--exclude-standard", root=root)
    if result.returncode != 0:
        return [p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts]
    return sorted({root / line for line in result.stdout.splitlines() if line})


def is_ignored(path: Path, root: Path = REPO_ROOT) -> bool:
    return git("check-ignore", "-q", str(path), root=root).returncode == 0


def read_frontmatter(text: str) -> dict[str, str] | None:
    """Flat `key: value` frontmatter between leading `---` lines; comments stripped."""
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    data: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        if ":" in line:
            key, _, value = line.partition(":")
            data[key.strip()] = value.split("#", 1)[0].strip()
    return None


@dataclass
class TaskLine:
    lineno: int
    state: str
    task_id: str
    rest: str
    group: str

    @property
    def spec_link(self) -> str | None:
        for m in LINK_RE.finditer(self.rest):
            if m.group("target").startswith("/docs/specs/"):
                return m.group("target")
        return None


def strip_code(text: str) -> str:
    """Blank out fenced blocks and inline code spans, keeping line numbers."""
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else re.sub(r"`[^`]*`", "", line))
    return "\n".join(out)
