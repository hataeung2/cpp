#!/usr/bin/env python3
"""Set up git core.hooksPath to .githooks for this repository clone.

Usage:
    py -3 .agent/scripts/setup_hooks.py          (Windows; Linux: python3)
    py -3 .agent/scripts/setup_hooks.py --root . (manual invocation / tests)

Rules: docs/agent_start_prompt.md (git hooks), docs/specs/090_11_portable_hooks.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_common  # noqa: E402


def hooks_installed(root: Path | str = agent_common.REPO_ROOT) -> bool | None:
    """Return True if core.hooksPath is .githooks, False if not set or another value, None if not a git repo."""
    root_path = Path(root).resolve()
    res = agent_common.git("rev-parse", "--git-dir", root=root_path)
    if res.returncode != 0:
        return None
    res = agent_common.git("config", "--local", "--get", "core.hooksPath", root=root_path)
    if res.returncode == 0:
        return res.stdout.strip() == ".githooks"
    return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=agent_common.REPO_ROOT, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    installed = hooks_installed(root)
    if installed is None:
        print(f"setup_hooks: not a git repository: {root}", file=sys.stderr)
        return 1

    res = agent_common.git("config", "--local", "--get", "core.hooksPath", root=root)
    current_val = res.stdout.strip() if res.returncode == 0 else ""
    if not current_val:
        set_res = agent_common.git("config", "--local", "core.hooksPath", ".githooks", root=root)
        if set_res.returncode != 0:
            print(f"setup_hooks: failed to set core.hooksPath: {set_res.stderr.strip()}", file=sys.stderr)
            return 1
        print("installed: core.hooksPath=.githooks")
        return 0
    if current_val == ".githooks":
        print("already installed")
        return 0
    print(f"setup_hooks: core.hooksPath is already set to '{current_val}'; refusing to overwrite", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
