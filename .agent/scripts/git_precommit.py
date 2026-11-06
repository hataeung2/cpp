#!/usr/bin/env python3
"""Git pre-commit guard: enforces non-negotiable rules on staged changes before commit.

Usage:
    py -3 .agent/scripts/git_precommit.py          (invoked by .githooks/pre-commit)
    py -3 .agent/scripts/git_precommit.py --root . (manual invocation / tests)

Rules: docs/agent_start_prompt.md (rules 1 and 4), docs/specs/090_11_portable_hooks.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_common  # noqa: E402
import guard_rules  # noqa: E402


def current_branch(root: Path = agent_common.REPO_ROOT) -> str:
    """Return the active branch name, or '' if detached HEAD. Fail closed if not a git repo."""
    res = agent_common.git("rev-parse", "--git-dir", root=root)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or f"not a git repository: {root}")
    res = agent_common.git("symbolic-ref", "--short", "-q", "HEAD", root=root)
    if res.returncode == 0:
        return res.stdout.strip()
    if res.returncode == 1:  # HEAD is not a symbolic ref: detached
        return ""
    raise RuntimeError(res.stderr.strip() or "git symbolic-ref failed")


# Fixed diff form, whatever the user's diff config says (prefixes, textconv, external diff, colour).
_DIFF = ("diff", "--cached", "--no-color", "--no-ext-diff", "--no-textconv", "-U0",
         "--src-prefix=a/", "--dst-prefix=b/")


def staged_paths(root: Path = agent_common.REPO_ROOT) -> list[str]:
    """Staged paths that add content (Added, Copied, Modified, Renamed), NUL-separated so any name works."""
    res = agent_common.git("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR", root=root)
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip() or "git diff --name-only failed")
    return [p for p in res.stdout.split("\0") if p]


def staged_added_lines(root: Path = agent_common.REPO_ROOT) -> dict[str, list[str]]:
    """Added lines per staged path. One diff per path: its header ends at the first hunk, so
    an added line that looks like a header ('+++ x') is still content. Binary files have no
    hunk and no lines. Lines are split on '\\n' only (not on form feeds or U+2028)."""
    added: dict[str, list[str]] = {}
    for path in staged_paths(root):
        res = agent_common.git("--literal-pathspecs", *_DIFF, "--", path, root=root)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or f"git diff failed for {path}")
        lines: list[str] = []
        in_hunks = False
        for line in res.stdout.split("\n"):
            if line.startswith("@@"):
                in_hunks = True
            elif in_hunks and line.startswith("+"):
                lines.append(line[1:])
        added[path] = lines
    return added


def check(root: Path = agent_common.REPO_ROOT) -> list[str]:
    """Check staged changes against non-negotiable rules. Return list of rejection reasons."""
    reasons: list[str] = []
    branch = current_branch(root)
    branch_reason = guard_rules.protected_branch_reason(branch)
    if branch_reason:
        reasons.append(branch_reason)
    for rel_path, lines in staged_added_lines(root).items():
        reason = guard_rules.check_added_lines(root / rel_path, lines, root=root)
        if reason and reason not in reasons:
            reasons.append(reason)
    return reasons


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=agent_common.REPO_ROOT, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        root = Path(args.root).resolve()
        reasons = check(root)
    except Exception as exc:
        print(f"pre-commit: guard failed: {exc}", file=sys.stderr)
        return 1

    if reasons:
        for reason in reasons:
            print(f"pre-commit: {reason}", file=sys.stderr)
        print("pre-commit: commit refused (a person may bypass with git commit --no-verify; agents never do)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
