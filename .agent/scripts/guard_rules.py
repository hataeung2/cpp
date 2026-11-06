#!/usr/bin/env python3
"""Tool-independent guard rules: enforces machine-checkable non-negotiable rules
(docs/agent_start_prompt.md) before actions take effect.

Rule numbers:
- Rule 1: No machine-specific paths in repo files.
  Judged by check_added_lines() = is_checked_file() + machine_path_reason(): files outside
  the repo and ignored files (CMakeUserPresets.json, out/) are not checked. An adapter that
  must read a file to know the added lines calls is_checked_file() first, so it never
  opens a file the rule does not apply to.
- Rule 2: No ad-hoc CMake configure.
  Judged by check_command(): inspects the command for ad-hoc configure invocations
  using shell_commands / agent_common.is_adhoc_cmake.
- Rule 4: No commit on protected branches (main, master).
  Judged by check_command(): inspects the command for git commit invocations using
  agent_common.is_git_commit and checks the active branch.

Adapters (.claude/hooks/guard.py, .codex/hooks/guard.py, .agent/scripts/git_precommit.py)
only translate their tool's specific input and output formats, delegating all rule
judgments and reason sentences to this module.
"""
from __future__ import annotations

from pathlib import Path

import agent_common

PROTECTED_BRANCHES = {"main", "master"}


def inside_repo(path: Path, root: Path = agent_common.REPO_ROOT) -> bool:
    root_str = str(root.resolve()).replace("\\", "/").lower().rstrip("/") + "/"
    return str(path.resolve()).replace("\\", "/").lower().startswith(root_str)


def check_command(command: str, shell: str = "bash", root: Path = agent_common.REPO_ROOT) -> str | None:
    if agent_common.is_adhoc_cmake(command, shell):
        return ("Ad-hoc CMake configure is not allowed (non-negotiable rule 2). "
                "Use `py -3 .agent/scripts/build.py --preset <name>` or `cmake --preset <name>`; "
                "add a preset to CMakePresets.json if none fits.")
    if agent_common.is_git_commit(command, shell):
        branch = agent_common.git("rev-parse", "--abbrev-ref", "HEAD", root=root).stdout.strip()
        return protected_branch_reason(branch)
    return None


def protected_branch_reason(branch: str) -> str | None:
    """Rule 4: the reason when `branch` may not receive commits, else None."""
    if branch in PROTECTED_BRANCHES:
        return (f"Committing on {branch} is not allowed (non-negotiable rule 4). "
                "Create the task branch feature/NNN-SS-<slug> first.")
    return None


def is_checked_file(path: Path, root: Path = agent_common.REPO_ROOT) -> bool:
    """Rule 1 applies to files inside the repo that git does not ignore (CMakeUserPresets.json, out/ are ignored)."""
    return inside_repo(path, root=root) and not agent_common.is_ignored(path, root=root)


def machine_path_reason(added_lines: list[str]) -> str | None:
    """The rule 1 reason for lines about to be added to a checked file, or None."""
    hits = [hit for line in added_lines for hit in agent_common.machine_paths(line)]
    if not hits:
        return None
    shown = ", ".join(sorted(set(hits))[:3])
    return (f"Machine-specific path ({shown}) in a repo file is not allowed (non-negotiable rule 1). "
            "Use a project-relative path, an env var (VCPKG_ROOT, VSDEVCMD) or a <placeholder>; "
            "machine-only settings belong in the untracked CMakeUserPresets.json.")


def check_added_lines(path: Path, added_lines: list[str], root: Path = agent_common.REPO_ROOT) -> str | None:
    """Rule 1 for one file: None when the file is not checked or the lines are clean."""
    if not is_checked_file(path, root=root):
        return None
    return machine_path_reason(added_lines)
