#!/usr/bin/env python3
"""Docs lint: links, machine paths, todo grammar, spec approval state, KI ids.

Usage:
    py -3 .agent/scripts/lint_docs.py            (Windows; Linux: python3)
    py -3 .agent/scripts/lint_docs.py --status   (task states and the next approved task)

Exit 0 = no ERROR, 1 = at least one ERROR. Sealed records report INFO instead of ERROR:
legacy specs (no frontmatter, task line marked `legacy`, DONE) and artifact directories of
DONE tasks (named `feature_NNN-SS-<slug>`, or `feature_<branch>` for a legacy task's branch).
Rules: docs/agent_start_prompt.md, .agent/rules/spec.md, docs/tasks/agent_todo.md (Grammar).
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_common as ac  # noqa: E402

TODO = Path("docs/tasks/agent_todo.md")
KNOWN_ISSUES = Path("docs/known_issues.md")
KI_REF_RE = re.compile(r"\bKI-\d{3}\b")
PATH_CHECKED_SUFFIXES = {".md", ".json"}
DOC_DIRS = ("docs", ".agent", ".claude")
TASK_DIR_RE = re.compile(rf"^feature_(?P<id>{ac.TASK_ID})-")
BRANCH_RE = re.compile(r"`feature/([^`]+)`")
LEGACY_RE = re.compile(r"\blegacy\b")
LEGACY_SPEC_NAME_RE = re.compile(r"^\d{2}_")  # spec.md §5: names before 090-01 (01_, 08_001_, ...)


def is_legacy_task(task: ac.TaskLine) -> bool:
    """DONE and marked `legacy` in the note after the title (` — legacy ...`), not in the title."""
    note = task.rest.split(" — ", 1)[1] if " — " in task.rest else ""
    return task.state == "DONE" and bool(LEGACY_RE.search(note))
STATES_NEEDING_APPROVAL = {"APPROVED", "DEV", "TEST", "DONE"}


@dataclass
class Report:
    root: Path
    findings: list[tuple[str, str, int, str]] = field(default_factory=list)

    def add(self, level: str, path: Path, line: int, message: str) -> None:
        rel = path.relative_to(self.root).as_posix() if path.is_absolute() else path.as_posix()
        self.findings.append((level, rel, line, message))

    def count(self, level: str) -> int:
        return sum(1 for f in self.findings if f[0] == level)


def read(path: Path, report: Report) -> str | None:
    """UTF-8 text (a BOM is accepted); a file in another encoding is an ERROR, not a crash."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        report.add("ERROR", path, 0, f"not UTF-8 ({exc.reason} at byte {exc.start})")
        return None


def is_date(value: str) -> bool:
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))


def parse_todo(root: Path, report: Report) -> list[ac.TaskLine]:
    path = root / TODO
    if not path.is_file():
        report.add("ERROR", path, 0, "task list not found")
        return []
    text = read(path, report)
    if text is None:
        return []
    tasks: list[ac.TaskLine] = []
    group = ""
    last_original = ""  # the task the next patch line belongs to
    in_tasks = False
    groups: dict[str, tuple[int, int, int]] = {}  # heading -> (line, done, total) as declared

    for lineno, line in enumerate(text.splitlines(), 1):
        if not in_tasks:
            in_tasks = line.strip() == "---"
            continue
        if not line.strip():
            continue
        if line.startswith("## "):
            group = line
            m = ac.GROUP_HEADING_RE.match(line)
            if m:
                groups[group] = (lineno, int(m.group("done")), int(m.group("total")))
            else:
                report.add("ERROR", path, lineno, "group heading must end with '(k/n DONE)'")
            continue
        m = ac.TASK_LINE_RE.match(line)
        if not m:
            report.add("ERROR", path, lineno, "line in the task section does not follow '- !STATE | NNN-SS | Title'")
            continue
        if m.group("state") not in ac.STATES:
            report.add("ERROR", path, lineno, f"unknown state {m.group('state')}")
        task_id = m.group("id")
        is_patch = task_id.count("-") == 2
        if is_patch:
            parent = task_id.rsplit("-", 1)[0]
            if not m.group("indent"):
                report.add("ERROR", path, lineno, f"patch {task_id} must be indented under {parent}")
            if parent != last_original:
                report.add("ERROR", path, lineno, f"patch {task_id} must follow its task {parent} (spec.md §4)")
        else:
            if m.group("indent"):
                report.add("ERROR", path, lineno, f"only patches (NNN-SS-PP) are indented; {task_id} is not one")
            last_original = task_id
        tasks.append(ac.TaskLine(lineno, m.group("state"), task_id, m.group("rest"), group))

    if not in_tasks:
        report.add("ERROR", path, 0, "no '---' line: the task section was not found")
    elif not tasks:
        report.add("ERROR", path, 0, "no task lines found")

    for task_id, n in Counter(t.task_id for t in tasks).items():
        if n > 1:
            report.add("ERROR", path, 0, f"task id {task_id} used {n} times")

    for heading, (lineno, done, total) in groups.items():
        members = [t for t in tasks if t.group == heading]
        real_done = sum(1 for t in members if t.state == "DONE")
        if (done, total) != (real_done, len(members)):
            report.add("ERROR", path, lineno, f"heading says ({done}/{total} DONE), lines say ({real_done}/{len(members)} DONE)")
    return tasks


def check_specs(root: Path, tasks: list[ac.TaskLine], report: Report) -> set[Path]:
    """Spec frontmatter against todo states. Returns the legacy (sealed) spec files."""
    todo = root / TODO
    legacy: set[Path] = set()
    linked: set[Path] = set()
    for task in tasks:
        link = task.spec_link
        if link is None:
            if task.state not in ("BACKLOG", "BLOCKED"):
                report.add("ERROR", todo, task.lineno, f"{task.task_id} is {task.state} without a spec link")
            continue
        spec = root / urllib.parse.unquote(link.lstrip("/").split("#", 1)[0])
        linked.add(spec)
        if not spec.is_file():
            report.add("ERROR", todo, task.lineno, f"{task.task_id}: spec {link} not found")
            continue
        text = read(spec, report)
        if text is None:
            continue
        fm = ac.read_frontmatter(text)
        if fm is None:
            if is_legacy_task(task) and LEGACY_SPEC_NAME_RE.match(spec.name):
                legacy.add(spec)
            else:
                report.add("ERROR", spec, 1, f"{task.task_id} spec has no frontmatter (only DONE tasks marked 'legacy' with a pre-090-01 spec name may omit it)")
            continue
        if fm.get("id") != task.task_id:
            report.add("ERROR", spec, 1, f"frontmatter id {fm.get('id')!r} != todo id {task.task_id}")
        approved = fm.get("approved", "")
        if approved != "null" and not is_date(approved):
            report.add("ERROR", spec, 1, f"approved must be null or a real YYYY-MM-DD date, got {approved!r}")
        if task.state in STATES_NEEDING_APPROVAL and approved == "null":
            report.add("ERROR", todo, task.lineno, f"{task.task_id} is {task.state} but its spec has approved: null")
        if task.state == "SPEC_DRAFT" and is_date(approved):
            report.add("WARN", todo, task.lineno, f"{task.task_id} spec is approved but the state is still SPEC_DRAFT")
        if task.state == "BACKLOG":
            report.add("WARN", todo, task.lineno, f"{task.task_id} has a spec but is BACKLOG (expected SPEC_DRAFT or later)")

    for spec in sorted((root / "docs/specs").glob("[0-9][0-9][0-9]_[0-9][0-9]*.md")):
        m = re.match(r"^(\d{3})_(\d{2})(?:_(\d{2}))?_", spec.name)
        if not m:
            continue
        file_id = "-".join(g for g in m.groups() if g)
        text = read(spec, report)
        fm = ac.read_frontmatter(text) if text is not None else None
        if fm is None:
            report.add("ERROR", spec, 1, "NNN_SS spec without frontmatter")
        elif fm.get("id") != file_id:
            report.add("ERROR", spec, 1, f"file name id {file_id} != frontmatter id {fm.get('id')!r}")
        if spec not in linked:
            report.add("WARN", spec, 1, "spec is not linked from agent_todo.md")
    return legacy


def sealed_task_dirs(root: Path, tasks: list[ac.TaskLine], report: Report) -> set[Path]:
    states = {t.task_id: t.state for t in tasks}
    legacy_dirs = {f"feature_{b}" for t in tasks if is_legacy_task(t) for b in BRANCH_RE.findall(t.rest)}
    sealed: set[Path] = set()
    tasks_dir = root / "docs/tasks"
    if not tasks_dir.is_dir():
        return sealed
    for d in sorted(tasks_dir.iterdir()):
        if not d.is_dir() or not d.name.startswith("feature_"):
            continue
        m = TASK_DIR_RE.match(d.name)
        if m is not None:
            if states.get(m.group("id")) == "DONE":
                sealed.add(d)
        elif d.name in legacy_dirs:
            sealed.add(d)
        else:
            report.add("ERROR", d, 0, "artifact directory must be named feature_NNN-SS-<slug> (or match a legacy task's branch)")
    return sealed


def checked_files(root: Path) -> list[Path]:
    files = []
    for path in ac.repo_files(root):
        rel = path.relative_to(root)
        if path.suffix not in PATH_CHECKED_SUFFIXES or not path.is_file():
            continue
        if len(rel.parts) == 1 or rel.parts[0] in DOC_DIRS:
            files.append(path)
    return files


def check_file(path: Path, root: Path, sealed: bool, report: Report, ki_refs: dict[str, list[tuple[Path, int, bool]]]) -> None:
    text = read(path, report)
    if text is None:
        return
    level = "INFO" if sealed else "ERROR"
    for lineno, line in enumerate(text.splitlines(), 1):
        for found in ac.machine_paths(line):
            report.add(level, path, lineno, f"machine-specific path {found!r}")
    if path.suffix != ".md":
        return
    prose = ac.strip_code(text)
    for lineno, line in enumerate(prose.splitlines(), 1):
        for m in ac.LINK_RE.finditer(line):
            target = m.group("target")
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#") or target.startswith("<"):
                continue
            rel = urllib.parse.unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not rel:
                continue
            dest = root / rel.lstrip("/") if rel.startswith("/") else path.parent / rel
            if not dest.exists():
                report.add(level, path, lineno, f"broken link {target}")
        for ref in KI_REF_RE.findall(line):
            ki_refs.setdefault(ref, []).append((path, lineno, sealed))


def check_known_issues(root: Path, report: Report, ki_refs: dict[str, list[tuple[Path, int, bool]]]) -> None:
    path = root / KNOWN_ISSUES
    if not path.is_file():
        report.add("ERROR", path, 0, "known issues file not found")
        return
    text = read(path, report)
    if text is None:
        return
    table = set(re.findall(r"^\| (KI-\d{3}) \|", text, re.MULTILINE))
    sections = set(re.findall(r"^## (KI-\d{3})\b", text, re.MULTILINE))
    for ki in sorted(table - sections):
        report.add("ERROR", path, 0, f"{ki} is in the table but has no '## {ki}' section")
    for ki in sorted(sections - table):
        report.add("ERROR", path, 0, f"{ki} has a section but no table row")
    for ki, refs in sorted(ki_refs.items()):
        if ki not in table:
            for ref_path, lineno, sealed in refs:
                report.add("INFO" if sealed else "ERROR", ref_path, lineno, f"{ki} is not defined in {KNOWN_ISSUES.as_posix()}")


def lint(root: Path) -> Report:
    report = Report(root)
    tasks = parse_todo(root, report)
    legacy_specs = check_specs(root, tasks, report)
    sealed_dirs = sealed_task_dirs(root, tasks, report)
    ki_refs: dict[str, list[tuple[Path, int, bool]]] = {}
    for path in checked_files(root):
        sealed = path in legacy_specs or any(d in path.parents for d in sealed_dirs)
        check_file(path, root, sealed, report, ki_refs)
    check_known_issues(root, report, ki_refs)
    return report


def print_status(root: Path) -> int:
    report = Report(root)
    tasks = parse_todo(root, report)
    counts = Counter(t.state for t in tasks)
    print("states: " + ", ".join(f"{s} {counts.get(s, 0)}" for s in ac.STATES))
    for t in tasks:
        if t.state not in ("BACKLOG", "DONE"):
            print(f"  {t.state:<10} {t.task_id}  {ac.LINK_RE.sub(lambda m: m.group('text'), t.rest)}")
    ready = next((t for t in tasks if t.state == "APPROVED"), None)
    print(f"next approved task: {ready.task_id if ready else 'none'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ac.REPO_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--status", action="store_true", help="print task states and exit")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.status:
        return print_status(root)
    report = lint(root)
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    for level, rel, line, message in sorted(report.findings, key=lambda f: (order[f[0]], f[1], f[2])):
        print(f"{level} {rel}:{line}: {message}")
    print(f"lint_docs: {report.count('ERROR')} error(s), {report.count('WARN')} warning(s), {report.count('INFO')} info")
    return 1 if report.count("ERROR") else 0


if __name__ == "__main__":
    sys.exit(main())
