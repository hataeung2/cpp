#!/usr/bin/env python3
"""Sync agent skills from .agent/skills/ to .claude/skills/ and .agents/skills/.

Usage:
    py -3 .agent/scripts/sync_skills.py             (Windows; Linux: python3)
    py -3 .agent/scripts/sync_skills.py --check     (verify target copies are in sync; exit 1 on diff)

Rules: docs/agent_start_prompt.md, docs/specs/090_10_portable_skills.md.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_common  # noqa: E402

SOURCE = Path(".agent/skills")
TARGETS = (Path(".claude/skills"), Path(".agents/skills"))
MARKER = "<!-- generated from .agent/skills/{name}/SKILL.md by .agent/scripts/sync_skills.py; edit the source -->"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DESCRIPTION_LIMIT = 1024
BODY_LIMIT = 4096
ALLOWED_KEYS = ("name", "description")

__all__ = [
    "SOURCE",
    "TARGETS",
    "MARKER",
    "NAME_RE",
    "DESCRIPTION_LIMIT",
    "BODY_LIMIT",
    "ALLOWED_KEYS",
    "Finding",
    "validate",
    "expected",
    "check",
    "sync",
    "main",
]


@dataclass
class Finding:
    level: str
    path: str
    line: int
    message: str


def _insert_marker(text: str, skill_name: str) -> str:
    marker_line = MARKER.format(name=skill_name)
    lines = text.splitlines(keepends=True)
    found_first = False
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if not found_first:
                found_first = True
            else:
                closing = line
                if not closing.endswith("\n"):
                    closing += "\n"
                lines[i] = closing + marker_line + "\n"
                return "".join(lines)
    return marker_line + "\n" + text


def validate(root: Path = agent_common.REPO_ROOT) -> list[Finding]:
    root = Path(root)
    src_dir = root / SOURCE
    if not src_dir.is_dir():
        return []

    findings: list[Finding] = []

    for entry in sorted(src_dir.iterdir()):
        if not entry.is_dir():
            continue

        skill_file = entry / "SKILL.md"
        skill_rel = (SOURCE / entry.name / "SKILL.md").as_posix()

        # Check all files under entry for UTF-8
        bad_utf8_files: set[Path] = set()
        for p in sorted(entry.rglob("*")):
            if not p.is_file():
                continue
            try:
                p.read_bytes().decode("utf-8")
            except (UnicodeDecodeError, OSError) as exc:
                bad_utf8_files.add(p)
                p_rel = p.relative_to(root).as_posix()
                findings.append(Finding("ERROR", p_rel, 1, f"file is not valid UTF-8: {exc}"))

        if not skill_file.is_file():
            findings.append(Finding("ERROR", skill_rel, 1, "missing SKILL.md in skill folder"))
            continue

        if skill_file in bad_utf8_files:
            continue

        text = skill_file.read_bytes().decode("utf-8").lstrip("\ufeff")
        fm = agent_common.read_frontmatter(text)
        if fm is None:
            findings.append(Finding("ERROR", skill_rel, 1, "missing or invalid frontmatter"))
            continue

        lines = text.splitlines()

        def find_key_line(k: str) -> int:
            for idx, l in enumerate(lines, start=1):
                if idx > 1 and l.strip() == "---":
                    break
                if l.strip().startswith(f"{k}:") or l.strip().startswith(f"{k} :"):
                    return idx
            return 1

        for k in sorted(fm.keys()):
            if k not in ALLOWED_KEYS:
                findings.append(
                    Finding(
                        "ERROR",
                        skill_rel,
                        find_key_line(k),
                        f"disallowed frontmatter key '{k}': only {ALLOWED_KEYS} are allowed",
                    )
                )

        if "name" not in fm:
            findings.append(Finding("ERROR", skill_rel, 1, "missing 'name' in frontmatter"))
        else:
            name_val = fm["name"]
            name_line = find_key_line("name")
            if not name_val:
                findings.append(Finding("ERROR", skill_rel, name_line, "skill name is empty"))
            else:
                if not NAME_RE.fullmatch(name_val):
                    findings.append(
                        Finding(
                            "ERROR",
                            skill_rel,
                            name_line,
                            f"skill name '{name_val}' does not match pattern {NAME_RE.pattern} (lowercase alphanumeric and hyphens only)",
                        )
                    )
                if len(name_val) > 64:
                    findings.append(
                        Finding(
                            "ERROR",
                            skill_rel,
                            name_line,
                            f"skill name '{name_val}' exceeds 64 characters ({len(name_val)} > 64)",
                        )
                    )
                if name_val != entry.name:
                    findings.append(
                        Finding(
                            "ERROR",
                            skill_rel,
                            name_line,
                            f"skill name '{name_val}' does not match folder name '{entry.name}'",
                        )
                    )

        if "description" not in fm:
            findings.append(Finding("ERROR", skill_rel, 1, "missing 'description' in frontmatter"))
        else:
            desc_line = find_key_line("description")
            # Empty: judged on the read_frontmatter value, so a comment-only value is empty.
            # Length: judged on the raw line value, so a '#' inside the text ("C# ...") is counted.
            stripped_desc = fm["description"].strip()
            desc_val = lines[desc_line - 1].partition(":")[2].strip()

            if not stripped_desc:
                findings.append(Finding("ERROR", skill_rel, desc_line, "description is empty in frontmatter"))
            elif len(desc_val) > DESCRIPTION_LIMIT:
                findings.append(
                    Finding(
                        "ERROR",
                        skill_rel,
                        desc_line,
                        f"description length ({len(desc_val)}) exceeds limit of {DESCRIPTION_LIMIT} characters",
                    )
                )

        # Body UTF-8 byte limit check
        lines_raw = text.splitlines(keepends=True)
        closing_idx = -1
        found_first = False
        for i, line in enumerate(lines_raw):
            if line.strip() == "---":
                if not found_first:
                    found_first = True
                else:
                    closing_idx = i
                    break

        if closing_idx != -1:
            body = "".join(lines_raw[closing_idx + 1:])
            body_bytes = len(body.replace("\r\n", "\n").encode("utf-8"))
            if body_bytes > BODY_LIMIT:
                findings.append(
                    Finding(
                        "WARN",
                        skill_rel,
                        closing_idx + 2,
                        f"skill body size ({body_bytes} bytes) exceeds limit of {BODY_LIMIT} bytes",
                    )
                )

    return findings


def expected(root: Path = agent_common.REPO_ROOT) -> dict[Path, str]:
    root = Path(root)
    exp: dict[Path, str] = {}
    src_dir = root / SOURCE
    if not src_dir.is_dir():
        return exp

    for entry in sorted(src_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_name = entry.name
        for file_path in sorted(entry.rglob("*")):
            if not file_path.is_file():
                continue
            subpath = file_path.relative_to(entry)
            try:
                raw_bytes = file_path.read_bytes()
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = raw_bytes.decode("utf-8", errors="replace")
            except OSError:
                text = ""

            norm_text = text.replace("\r\n", "\n")
            if subpath == Path("SKILL.md"):
                norm_text = norm_text.lstrip("﻿")  # as validate reads it; a BOM would hide the opening ---
                content = _insert_marker(norm_text, skill_name)
            else:
                content = norm_text

            for target in TARGETS:
                dest_path = target / skill_name / subpath
                exp[dest_path] = content

    return exp


def check(root: Path = agent_common.REPO_ROOT) -> list[Finding]:
    root = Path(root)
    findings: list[Finding] = list(validate(root))
    exp_map = expected(root)

    for target in TARGETS:
        target_dir = root / target
        # A missing target folder still means missing copies (plan Design `check`).
        for dest_rel, exp_content in exp_map.items():
            if not dest_rel.is_relative_to(target):
                continue
            actual_path = root / dest_rel
            src_subpath = dest_rel.relative_to(target)
            src_posix = (SOURCE / src_subpath).as_posix()

            if not actual_path.is_file():
                findings.append(
                    Finding(
                        level="ERROR",
                        path=dest_rel.as_posix(),
                        line=1,
                        message=f"out of date with {src_posix}: run py -3 .agent/scripts/sync_skills.py",
                    )
                )
            else:
                try:
                    actual_bytes = actual_path.read_bytes()
                    actual_text = actual_bytes.decode("utf-8")
                    is_diff = actual_text.replace("\r\n", "\n") != exp_content
                except (UnicodeDecodeError, OSError):
                    is_diff = True

                if is_diff:
                    findings.append(
                        Finding(
                            level="ERROR",
                            path=dest_rel.as_posix(),
                            line=1,
                            message=f"out of date with {src_posix}: run py -3 .agent/scripts/sync_skills.py",
                        )
                    )

        for p in sorted(target_dir.rglob("*")) if target_dir.is_dir() else []:
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            if rel not in exp_map:
                findings.append(
                    Finding(
                        level="ERROR",
                        path=rel.as_posix(),
                        line=1,
                        message=f"no source in {SOURCE.as_posix()} (generated folder): run py -3 .agent/scripts/sync_skills.py",
                    )
                )

    return findings


def sync(root: Path = agent_common.REPO_ROOT) -> list[str]:
    root = Path(root)
    val_findings = validate(root)
    errors = [f for f in val_findings if f.level == "ERROR"]
    if errors:
        msgs = "\n".join(f"{f.path}:{f.line}: {f.message}" for f in errors)
        raise ValueError(f"validation failed:\n{msgs}")
    if not (root / SOURCE).is_dir() and any((root / t).is_dir() for t in TARGETS):
        # Removing every generated copy because the source folder is missing (a wrong --root,
        # an old checkout) is never what was meant: refuse and say so.
        raise ValueError(f"{SOURCE.as_posix()} not found: refusing to remove the generated copies")

    exp_map = expected(root)
    to_write: dict[Path, str] = {}
    for dest_rel, exp_content in exp_map.items():
        actual_path = root / dest_rel
        if not actual_path.is_file():
            to_write[dest_rel] = exp_content
        else:
            try:
                actual_bytes = actual_path.read_bytes()
                actual_text = actual_bytes.decode("utf-8")
                if actual_text.replace("\r\n", "\n") != exp_content:
                    to_write[dest_rel] = exp_content
            except (UnicodeDecodeError, OSError):
                to_write[dest_rel] = exp_content

    to_remove: list[Path] = []
    for target in TARGETS:
        target_dir = root / target
        if not target_dir.exists():
            continue
        for p in sorted(target_dir.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root)
            if rel not in exp_map:
                to_remove.append(rel)

    changed: list[str] = []

    for dest_rel, content in to_write.items():
        actual_path = root / dest_rel
        actual_path.parent.mkdir(parents=True, exist_ok=True)
        actual_path.write_text(content, encoding="utf-8", newline="\n")
        changed.append(dest_rel.as_posix())

    for rem_rel in to_remove:
        actual_path = root / rem_rel
        if actual_path.is_file():
            actual_path.unlink()
        changed.append(rem_rel.as_posix())

    for target in TARGETS:
        target_dir = root / target
        if not target_dir.exists():
            continue
        for dirpath_str, dirnames, filenames in os.walk(str(target_dir), topdown=False):
            d = Path(dirpath_str)
            if d == target_dir:
                continue
            try:
                if not any(d.iterdir()):
                    d.rmdir()
            except OSError:
                pass

    return sorted(changed)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=agent_common.REPO_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--check", action="store_true", help="check that target skill copies are up to date")
    args = parser.parse_args(argv)
    root = Path(args.root)

    if args.check:
        findings = check(root)
        order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        for f in sorted(findings, key=lambda x: (order.get(x.level, 99), x.path, x.line)):
            print(f"{f.level} {f.path}:{f.line}: {f.message}")
        has_error = any(f.level == "ERROR" for f in findings)
        return 1 if has_error else 0

    try:
        changed = sync(root)
    except (ValueError, OSError) as exc:  # OSError: e.g. a file where a folder is needed
        print(f"sync_skills: {exc}", file=sys.stderr)
        return 1

    if not changed:
        print("skills up to date")
    else:
        for rel_posix in changed:
            p = root / rel_posix
            if p.exists():
                print(f"wrote {rel_posix}")
            else:
                print(f"removed {rel_posix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
