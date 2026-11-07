#!/usr/bin/env python3
"""Docs lint: links, machine paths, todo grammar, spec approval state, KI ids, lesson manifests, evolution page pairs, archive docs, rule frontmatter, trigger table, skill copies.

Usage:
    py -3 .agent/scripts/lint_docs.py                       (Windows; Linux: python3)
    py -3 .agent/scripts/lint_docs.py --status              (task states and the next approved task)
    py -3 .agent/scripts/lint_docs.py --boot                (boot text: todo header, status, open/planned KI table)
    py -3 .agent/scripts/lint_docs.py --ki ID [ID ...]      (print sections for KI ids from any KI file)
    py -3 .agent/scripts/lint_docs.py --deferred            (print deferred KI table)

Exit 0 = no ERROR, 1 = at least one ERROR. Sealed records report INFO instead of ERROR:
legacy specs (no frontmatter, task line marked `legacy`, DONE) and artifact directories of
DONE tasks (named `feature_NNN-SS-<slug>`, or `feature_<branch>` for a legacy task's branch).
Archive files (docs/archive/agent_todo_done.md, docs/archive/known_issues_closed.md,
docs/known_issues_deferred.md) are read alongside current docs.
Rules: docs/agent_start_prompt.md, .agent/rules/spec.md, docs/agent_todo.md (Grammar).
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import re
import sys
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_common as ac  # noqa: E402
import archive_docs  # noqa: E402
import setup_hooks  # noqa: E402
import subagent_run  # noqa: E402
import sync_skills  # noqa: E402

TODO = archive_docs.TODO
TODO_DONE = archive_docs.TODO_DONE
KNOWN_ISSUES = archive_docs.KNOWN_ISSUES
BUDGET = {
    "open_ki": 20,
    "deferred_ki": 30,
    "header_bytes": 5120,
    "boot_bytes": 16384,
}
EVOLUTION_DIR = Path("docs/cpp_evolution")
EVOLUTION_INDEX = Path("docs/cpp_evolution.md")
RULES_DIR = Path(".agent/rules")
BOOT_PROMPT = Path("docs/agent_start_prompt.md")
RULE_TRIGGERS = ("always_on", "model_decision", "glob", "manual")
ALWAYS_ON_BODY_LIMIT = 1024
RUNNER = Path(".agent/scripts/subagent_run.py")
# impl.md `## Core` (090-12-01): the first section of every kind in subagent_run.RULE_SECTIONS.
CORE_RULES = Path(subagent_run.RULE_SECTIONS["code"][0][0])
CORE_HEADING = subagent_run.RULE_SECTIONS["code"][0][1]
CORE_LIMIT = 1536  # bytes of the Core section
RULE_BUNDLE_LIMIT = 8192  # bytes of one kind's `## Project rules` block
HEADING_RE = re.compile(r"^(#{1,6}) ", re.MULTILINE)
KI_REF_RE = re.compile(r"\bKI-\d{3}\b")
PATH_CHECKED_SUFFIXES = {".md", ".json"}
DOC_DIRS = ("docs", ".agent", ".claude", ".codex", "lessons")  # lessons/: READMEs and intro.md (KI-019)
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

    all_headings: list[str] = []  # every todo group heading, also one without a valid count
    try:
        movable_ids = set(archive_docs.movable_task_ids(text))
    except ValueError as exc:  # archive_docs.py would refuse this todo: say why
        movable_ids = set()
        report.add("ERROR", path, 0, f"archive_docs.py cannot read this file: {exc}")

    for lineno, line in enumerate(text.splitlines(), 1):
        if not in_tasks:
            in_tasks = line.strip() == "---"
            continue
        if not line.strip():
            continue
        if line.startswith("## "):
            group = line
            all_headings.append(line)
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
            if task_id in movable_ids:
                report.add("WARN", path, lineno, f"{task_id} is DONE: run py -3 .agent/scripts/archive_docs.py")
        tasks.append(ac.TaskLine(lineno, m.group("state"), task_id, m.group("rest"), group))

    if not in_tasks:
        report.add("ERROR", path, 0, "no '---' line: the task section was not found")
    elif not tasks:
        report.add("ERROR", path, 0, "no task lines found")

    done_path = root / TODO_DONE
    if done_path.is_file():
        done_text = read(done_path, report)
        if done_text is not None:
            done_group = ""
            done_last_original = ""
            in_done_tasks = False
            todo_archive_headings = {archive_docs.archive_heading(h) for h in all_headings}

            for lineno, line in enumerate(done_text.splitlines(), 1):
                if not in_done_tasks:
                    in_done_tasks = line.strip() == "---"
                    continue
                if not line.strip():
                    continue
                if line.startswith("## "):
                    if archive_docs.COUNT_SUFFIX_RE.search(line):
                        report.add("ERROR", done_path, lineno, "archive group heading must not include '(k/n DONE)'")
                    done_group = archive_docs.archive_heading(line.strip())
                    if done_group not in todo_archive_headings:
                        report.add("ERROR", done_path, lineno, f"archive group heading {line.strip()!r} has no matching group in {TODO.as_posix()}")
                    done_last_original = ""
                    continue
                m = ac.TASK_LINE_RE.match(line)
                if not m:
                    report.add("ERROR", done_path, lineno, "line in the task section does not follow '- !STATE | NNN-SS | Title'")
                    continue
                if not done_group:
                    report.add("ERROR", done_path, lineno, "task line before the first '## ' group heading")
                state = m.group("state")
                task_id = m.group("id")
                if state != "DONE":
                    report.add("ERROR", done_path, lineno, f"task {task_id} in {TODO_DONE.as_posix()} is {state}, must be DONE")
                is_patch = task_id.count("-") == 2
                if is_patch:
                    parent = task_id.rsplit("-", 1)[0]
                    if not m.group("indent"):
                        report.add("ERROR", done_path, lineno, f"patch {task_id} must be indented under {parent}")
                    if parent != done_last_original:
                        report.add("ERROR", done_path, lineno, f"patch {task_id} must follow its task {parent} (spec.md §4)")
                else:
                    if m.group("indent"):
                        report.add("ERROR", done_path, lineno, f"only patches (NNN-SS-PP) are indented; {task_id} is not one")
                    done_last_original = task_id
                tasks.append(ac.TaskLine(lineno, state, task_id, m.group("rest"), done_group, path=TODO_DONE))

            if not in_done_tasks:
                report.add("ERROR", done_path, 0, "no '---' line: the task section was not found")

    for task_id, n in Counter(t.task_id for t in tasks).items():
        if n > 1:
            report.add("ERROR", path, 0, f"task id {task_id} used {n} times")

    for heading, (lineno, done, total) in groups.items():
        arch_h = archive_docs.archive_heading(heading)
        members = [t for t in tasks if (t.path is None and t.group == heading) or (t.path is not None and t.group == arch_h)]
        real_done = sum(1 for t in members if t.state == "DONE")
        if (done, total) != (real_done, len(members)):
            report.add("ERROR", path, lineno, f"heading says ({done}/{total} DONE), lines say ({real_done}/{len(members)} DONE)")
    return tasks


def check_specs(root: Path, tasks: list[ac.TaskLine], report: Report) -> set[Path]:
    """Spec frontmatter against todo states. Returns the legacy (sealed) spec files."""
    legacy: set[Path] = set()
    linked: set[Path] = set()
    for task in tasks:
        link = task.spec_link
        task_file = root / (task.path or TODO)
        if link is None:
            if task.state not in ("BACKLOG", "BLOCKED"):
                report.add("ERROR", task_file, task.lineno, f"{task.task_id} is {task.state} without a spec link")
            continue
        spec = root / urllib.parse.unquote(link.lstrip("/").split("#", 1)[0])
        linked.add(spec)
        if not spec.is_file():
            report.add("ERROR", task_file, task.lineno, f"{task.task_id}: spec {link} not found")
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
            report.add("ERROR", task_file, task.lineno, f"{task.task_id} is {task.state} but its spec has approved: null")
        if task.state == "SPEC_DRAFT" and is_date(approved):
            report.add("WARN", task_file, task.lineno, f"{task.task_id} spec is approved but the state is still SPEC_DRAFT")
        if task.state == "BACKLOG":
            report.add("WARN", task_file, task.lineno, f"{task.task_id} has a spec but is BACKLOG (expected SPEC_DRAFT or later)")

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
    main_ki_path = root / KNOWN_ISSUES
    if not main_ki_path.is_file():
        report.add("ERROR", main_ki_path, 0, "known issues file not found")
        return

    all_table_ids: set[str] = set()
    ki_to_file: dict[str, Path] = {}
    existing_files: list[Path] = []

    for rel_path in archive_docs.KI_FILES:
        file_path = root / rel_path
        if not file_path.is_file():
            continue
        existing_files.append(rel_path)
        text = read(file_path, report)
        if text is None:
            continue
        try:
            doc = archive_docs.parse_ki(text)
        except ValueError as exc:
            report.add("ERROR", file_path, 0, str(exc))
            continue

        table_ids = set(doc.rows.keys())
        section_ids = set(doc.sections.keys())
        for ki in sorted(table_ids - section_ids):
            report.add("ERROR", file_path, 0, f"{ki} is in the table but has no '## {ki}' section")
        for ki in sorted(section_ids - table_ids):
            report.add("ERROR", file_path, 0, f"{ki} has a section but no table row")

        line_map: dict[str, int] = {}
        for lineno, line in enumerate(text.splitlines(), 1):
            m = archive_docs.KI_ROW_RE.match(line)
            if m:
                line_map[m.group("id")] = lineno

        for ki_id, status in doc.statuses.items():
            lineno = line_map.get(ki_id, 0)
            if status not in archive_docs.KI_HOME:
                report.add("ERROR", file_path, lineno, f"unknown KI status {status!r} for {ki_id}")
            else:
                expected_home = archive_docs.KI_HOME[status]
                if rel_path != expected_home:
                    report.add("WARN", file_path, lineno, f"{ki_id} is {status} but in {rel_path.as_posix()}: run py -3 .agent/scripts/archive_docs.py")

            if ki_id in ki_to_file:
                report.add("ERROR", file_path, lineno, f"duplicate KI id {ki_id}: already in {ki_to_file[ki_id].as_posix()}")
            else:
                ki_to_file[ki_id] = rel_path
            all_table_ids.add(ki_id)

            if status == "DEFERRED":
                row_line = doc.rows.get(ki_id, "")
                parts = [p.strip() for p in row_line.split("|")]
                if parts and parts[0] == "":
                    parts.pop(0)
                if parts and parts[-1] == "":
                    parts.pop()
                owner = parts[-1] if len(parts) >= 5 else ""
                if not owner or owner == "—":
                    report.add("ERROR", file_path, lineno, f"{ki_id} is DEFERRED but has no revisit condition in Owner column")

    if len(existing_files) == 1 and existing_files[0] == KNOWN_ISSUES:
        ki_file_str = KNOWN_ISSUES.as_posix()
    else:
        ki_file_str = ", ".join(p.as_posix() for p in archive_docs.KI_FILES)

    for ki, refs in sorted(ki_refs.items()):
        if ki not in all_table_ids:
            for ref_path, lineno, sealed in refs:
                report.add("INFO" if sealed else "ERROR", ref_path, lineno, f"{ki} is not defined in {ki_file_str}")


def check_rule_frontmatter(root: Path, report: Report) -> list[Path]:
    """Frontmatter in .agent/rules/*.md: valid trigger, required keys, single always_on, body limit."""
    rules_dir = root / RULES_DIR
    if not rules_dir.is_dir():
        return []
    first_always_on: Path | None = None
    model_decision_rules: list[Path] = []
    for rule_path in sorted(rules_dir.glob("*.md")):
        if not rule_path.is_file():
            continue
        text = read(rule_path, report)
        if text is None:
            continue
        fm = ac.read_frontmatter(text)
        if fm is None:
            report.add("ERROR", rule_path, 1, "rule has no frontmatter")
            continue
        trigger = fm.get("trigger")
        if not trigger or trigger not in RULE_TRIGGERS:
            report.add("ERROR", rule_path, 1, f"trigger must be one of {', '.join(RULE_TRIGGERS)}")
            continue
        if trigger == "always_on":
            if first_always_on is None:
                first_always_on = rule_path
            else:
                report.add("ERROR", rule_path, 1, f"only one always_on rule (first: {first_always_on.name})")
            lines = text.lstrip("\ufeff").splitlines(keepends=True)
            closing_idx = -1
            for i, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    closing_idx = i
                    break
            if closing_idx != -1:
                body = "".join(lines[closing_idx + 1:])
                body_bytes = len(body.encode("utf-8"))
                if body_bytes > ALWAYS_ON_BODY_LIMIT:
                    report.add(
                        "WARN",
                        rule_path,
                        1,
                        f"always_on body is {body_bytes} bytes (limit {ALWAYS_ON_BODY_LIMIT}): every Antigravity conversation loads it",
                    )
        elif trigger == "model_decision":
            model_decision_rules.append(rule_path)
            if not fm.get("description", "").strip():
                report.add("ERROR", rule_path, 1, "model_decision rule requires description")
        elif trigger == "glob":
            if not fm.get("globs", "").strip():
                report.add("ERROR", rule_path, 1, "glob rule requires globs")
    return model_decision_rules


def check_rule_table(root: Path, report: Report, model_decision_rules: list[Path] | None = None) -> None:
    """Every model_decision rule is linked from the trigger table in docs/agent_start_prompt.md."""
    rules_dir = root / RULES_DIR
    if not rules_dir.is_dir():
        return

    if model_decision_rules is None:
        model_decision_rules = []
        for rule_path in sorted(rules_dir.glob("*.md")):
            if not rule_path.is_file():
                continue
            text = read(rule_path, report)
            if text is None:
                continue
            fm = ac.read_frontmatter(text)
            if fm and fm.get("trigger") == "model_decision":
                model_decision_rules.append(rule_path)

    if not model_decision_rules:
        return

    boot_path = root / BOOT_PROMPT
    if not boot_path.is_file():
        report.add("ERROR", boot_path, 0, f"boot prompt not found: {BOOT_PROMPT.as_posix()}")
        return

    boot_text = read(boot_path, report)
    if boot_text is None:
        return

    stripped = ac.strip_code(boot_text)
    table_rules: set[str] = set()
    for m in ac.LINK_RE.finditer(stripped):
        target = m.group("target").split("#", 1)[0]
        if target.startswith("/.agent/rules/") and target.endswith(".md"):
            name = target.removeprefix("/.agent/rules/")
            if "/" not in name:
                table_rules.add(name)

    for rule_path in sorted(model_decision_rules):
        if rule_path.name not in table_rules:
            report.add(
                "ERROR",
                rule_path,
                1,
                "not linked from the trigger table in docs/agent_start_prompt.md",
            )


def check_skills(root: Path, report: Report) -> None:
    """Skill sources and their generated copies through sync_skills.check (spec 090-10), same levels."""
    for finding in sync_skills.check(root):
        report.add(finding.level, root / finding.path, finding.line, f"skills: {finding.message}")


def check_lessons(root: Path, report: Report) -> None:
    """Lesson manifests through tools/lessons.py check (spec 070-01 AC-6), same levels."""
    module_path = root / "tools" / "lessons.py"
    if not module_path.is_file() or not (root / "lessons").is_dir():
        return
    spec = importlib.util.spec_from_file_location("atugcc_lessons", module_path)
    if spec is None or spec.loader is None:
        report.add("ERROR", module_path, 1, "cannot load tools/lessons.py")
        return
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module   # dataclasses look the module up while the class is created
    spec.loader.exec_module(module)
    for finding in module.run_check(root).findings:
        report.add(finding.level, Path(finding.path), finding.line or 1, f"lessons: {finding.message}")


def page_shape(text: str) -> tuple[list[int], int]:
    """Heading levels in order (outside code) and the number of fenced code blocks."""
    levels = [len(m.group(1)) for m in HEADING_RE.finditer(ac.strip_code(text))]
    fences = sum(1 for line in text.splitlines() if line.lstrip().startswith("```"))
    return levels, fences // 2


def check_evolution_pairs(root: Path, report: Report) -> None:
    """Every evolution page is a pair <x>.md (Korean) + <x>.en.md (English) of the same shape (spec 090-07)."""
    pages = sorted(p for p in (root / EVOLUTION_DIR).glob("*.md") if p.is_file()) if (root / EVOLUTION_DIR).is_dir() else []
    pages += [p for p in (root / EVOLUTION_INDEX, (root / EVOLUTION_INDEX).with_suffix(".en.md")) if p.is_file()]
    for page in [p for p in pages if not p.name.endswith(".en.md")]:
        english = page.with_name(page.stem + ".en.md")
        if not english.is_file():
            report.add("WARN", page, 1, f"no English page {english.name}")
            continue
        try:   # a file that is not UTF-8 is already an ERROR of check_file
            ko_text, en_text = page.read_text(encoding="utf-8-sig"), english.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        (ko_levels, ko_blocks), (en_levels, en_blocks) = page_shape(ko_text), page_shape(en_text)
        if ko_levels != en_levels:
            report.add("WARN", page, 1, f"headings differ from {english.name}: levels {ko_levels} vs {en_levels}")
        if ko_blocks != en_blocks:
            report.add("WARN", page, 1, f"code blocks differ from {english.name}: {ko_blocks} vs {en_blocks}")
    for english in [p for p in pages if p.name.endswith(".en.md")]:
        if not english.with_name(english.name[: -len(".en.md")] + ".md").is_file():
            report.add("WARN", english, 1, "no Korean page " + english.name[: -len(".en.md")] + ".md")


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
    model_decision_rules = check_rule_frontmatter(root, report)
    check_rule_table(root, report, model_decision_rules)
    check_lessons(root, report)
    check_skills(root, report)
    check_evolution_pairs(root, report)
    check_rule_bundles(root, report)
    return report


def check_rule_bundles(root: Path, report: Report) -> None:
    """Every kind's sub-agent rule block builds from existing sections and stays in its limit (090-12-01).

    Skipped when the root has no .agent/scripts/subagent_run.py (trees without the runner, such as test fixtures)."""
    if not (root / RUNNER).is_file():
        return
    core_path = root / CORE_RULES
    core = None
    if core_path.is_file():
        core = subagent_run.extract_section(core_path.read_text(encoding="utf-8-sig"), CORE_HEADING)
    if core is not None and len(core.encode("utf-8")) > CORE_LIMIT:
        report.add("ERROR", core_path, 1, f"'{CORE_HEADING}' is {len(core.encode('utf-8'))} bytes (limit {CORE_LIMIT}): every sub-agent prompt carries it")
    reported: set[tuple[str, str]] = set()
    for kind in subagent_run.KINDS:
        broken = False
        for rel, heading in subagent_run.rule_sections(kind):
            path = root / rel
            text = path.read_text(encoding="utf-8-sig") if path.is_file() else None
            if text is not None and subagent_run.extract_section(text, heading) is not None:
                continue
            broken = True
            if (rel, heading) not in reported:
                reported.add((rel, heading))
                what = "file not found" if text is None else f"no '{heading}' section"
                report.add("ERROR", path, 1, f"{what}: subagent_run.py RULE_SECTIONS attaches it to sub-agent prompts (kind {kind})")
        if broken:
            continue
        size = len(subagent_run.rule_bundle(kind, root).encode("utf-8"))
        if size > RULE_BUNDLE_LIMIT:
            report.add("ERROR", root / subagent_run.rule_sections(kind)[-1][0], 1,
                       f"sub-agent rules for kind {kind} are {size} bytes (limit {RULE_BUNDLE_LIMIT})")


def status_lines(root: Path | str = ac.REPO_ROOT) -> list[str]:
    root_path = Path(root).resolve()
    report = Report(root_path)
    tasks = parse_todo(root_path, report)
    counts = Counter(t.state for t in tasks)
    lines = ["states: " + ", ".join(f"{s} {counts.get(s, 0)}" for s in ac.STATES)]
    for t in tasks:
        if t.state not in ("BACKLOG", "DONE"):
            lines.append(f"  {t.state:<10} {t.task_id}  {ac.LINK_RE.sub(lambda m: m.group('text'), t.rest)}")
    ready = next((t for t in tasks if t.state == "APPROVED"), None)
    lines.append(f"next approved task: {ready.task_id if ready else 'none'}")
    if setup_hooks.hooks_installed(root_path) is False:
        lines.append("git hooks: not installed (py -3 .agent/scripts/setup_hooks.py; the user decides per clone)")
    return lines


def print_status(root: Path | str = ac.REPO_ROOT) -> int:
    root_path = Path(root).resolve()
    for line in status_lines(root_path):
        print(line)
    return 0


def _build_boot_data(root: Path) -> tuple[str, list[str]]:
    # 1. Todo header
    todo_path = root / TODO
    header_raw = ""
    todo_part = ""
    header_bytes = 0
    finished_in_header = False

    if todo_path.is_file():
        try:
            todo_text = todo_path.read_text(encoding="utf-8-sig")
            todo_lines = todo_text.splitlines()
            # The same boundary as parse_todo: the first line that is '---' after stripping.
            sep = next((i for i, line in enumerate(todo_lines) if line.strip() == "---"), None)
            if sep is not None:
                header_raw = "\n".join(todo_lines[:sep]) + "\n"
                header_bytes = len(header_raw.encode("utf-8"))
                todo_part = header_raw.strip()
            else:  # no header to measure; parse_todo reports the missing '---' as an ERROR
                header_raw = ""
                todo_part = f"NOTE: no '---' in {TODO.as_posix()}; printed the whole file\n{todo_text.strip()}"
            finished_in_header = bool(re.search(r"~~[^~]+~~\s*\(DONE", header_raw))
        except Exception as exc:
            todo_part = f"NOTE: {TODO.as_posix()} unparsable: {exc}"
    else:
        todo_part = f"NOTE: {TODO.as_posix()} not found"

    # 2. Status lines
    stat_lines = status_lines(root)
    status_part = "\n".join(stat_lines)

    # 3. Known issues
    ki_path = root / KNOWN_ISSUES
    ki_part = ""
    ki_docs: dict[Path, archive_docs.KiDoc] = {}
    ki_errors: dict[Path, str] = {}

    for rel_path in archive_docs.KI_FILES:
        full_path = root / rel_path
        if full_path.is_file():
            try:
                text = full_path.read_text(encoding="utf-8-sig")
                ki_docs[rel_path] = archive_docs.parse_ki(text)
            except Exception as exc:
                ki_errors[rel_path] = str(exc)

    if not ki_path.is_file():
        ki_part = f"NOTE: {KNOWN_ISSUES.as_posix()} not found"
    elif KNOWN_ISSUES in ki_errors:
        ki_part = f"NOTE: {KNOWN_ISSUES.as_posix()} unparsable: {ki_errors[KNOWN_ISSUES]}"
    else:
        doc = ki_docs[KNOWN_ISSUES]
        try:
            text = ki_path.read_text(encoding="utf-8-sig")
            lines = text.splitlines()
            header_idx = -1
            for idx, line in enumerate(lines):
                if re.search(r"^\|\s*ID\s*\|\s*Status\s*\|", line, re.IGNORECASE):
                    if idx + 1 < len(lines) and lines[idx + 1].strip().startswith("|") and "---" in lines[idx + 1]:
                        header_idx = idx
                        break
            if header_idx != -1:
                table_lines = [lines[header_idx], lines[header_idx + 1]]
                for ki_id, row in doc.rows.items():
                    if doc.statuses.get(ki_id) not in ("CLOSED", "DEFERRED"):  # an unknown status stays visible
                        table_lines.append(row)
                ki_part = "\n".join(table_lines)
            else:
                ki_part = f"NOTE: {KNOWN_ISSUES.as_posix()} table not found"
        except Exception as exc:
            ki_part = f"NOTE: {KNOWN_ISSUES.as_posix()} unparsable: {exc}"

    # 4. DEFERRED summary
    open_ki_count = sum(1 for d in ki_docs.values() for st in d.statuses.values() if st in ("OPEN", "PLANNED"))
    deferred_ki_count = sum(1 for d in ki_docs.values() for st in d.statuses.values() if st == "DEFERRED")

    if archive_docs.KI_DEFERRED in ki_errors:
        deferred_part = f"NOTE: {archive_docs.KI_DEFERRED.as_posix()} unparsable: {ki_errors[archive_docs.KI_DEFERRED]}"
    else:
        deferred_part = f"DEFERRED: {deferred_ki_count} in {archive_docs.KI_DEFERRED.as_posix()} (check its Area column for the area you change)"
    if archive_docs.KI_CLOSED in ki_errors:  # its rows drop out of the counts: say so
        deferred_part += f"\nNOTE: {archive_docs.KI_CLOSED.as_posix()} unparsable: {ki_errors[archive_docs.KI_CLOSED]}"

    # 5. Core rules for every agent (090-12-01); absent in trees without the agent rules
    core_part = ""
    core_path = root / CORE_RULES
    if core_path.is_file():
        try:
            core_part = subagent_run.extract_section(core_path.read_text(encoding="utf-8-sig"), CORE_HEADING) or ""
        except Exception as exc:
            core_part = f"NOTE: {CORE_RULES.as_posix()} unparsable: {exc}"
        if not core_part:
            core_part = f"NOTE: no '{CORE_HEADING}' in {CORE_RULES.as_posix()}"

    body = f"{todo_part}\n\n" + (f"{core_part}\n\n" if core_part else "") + f"{status_part}\n\n{ki_part}\n\n{deferred_part}"
    boot_bytes = len(body.encode("utf-8"))

    items: list[str] = []
    if open_ki_count > BUDGET["open_ki"]:
        items.append(f"open KI {open_ki_count}/{BUDGET['open_ki']}")
    if deferred_ki_count > BUDGET["deferred_ki"]:
        items.append(f"DEFERRED {deferred_ki_count}/{BUDGET['deferred_ki']}")
    if header_bytes > BUDGET["header_bytes"]:
        items.append(f"todo header {header_bytes}/{BUDGET['header_bytes']} bytes")
    if finished_in_header:
        items.append("finished items in the todo header (~~…~~ (DONE …))")
    if boot_bytes > BUDGET["boot_bytes"]:
        items.append(f"boot output {boot_bytes}/{BUDGET['boot_bytes']} bytes")

    return body, items


def boot_text(root: Path | str = ac.REPO_ROOT) -> str:
    root_path = Path(root).resolve()
    body, items = _build_boot_data(root_path)
    if items:
        budget_line = f"BUDGET: {'; '.join(items)}: triage before the next task"
        if body.startswith("NOTE: no '---'"):  # spec §2.2: that NOTE stays the first line
            note, _, rest = body.partition("\n")
            return f"{note}\n{budget_line}\n{rest}"
        return f"{budget_line}\n{body}"
    return body


def read_ki_docs_noted(root: Path) -> tuple[dict[Path, archive_docs.KiDoc], list[str]]:
    """The KI files that parse, and a NOTE line for each that does not (the boot views never raise)."""
    docs: dict[Path, archive_docs.KiDoc] = {}
    notes: list[str] = []
    for rel_path in archive_docs.KI_FILES:
        full_path = root / rel_path
        if not full_path.is_file():
            continue
        try:
            docs[rel_path] = archive_docs.parse_ki(full_path.read_text(encoding="utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as exc:
            notes.append(f"NOTE: {rel_path.as_posix()} unparsable: {exc}")
    return docs, notes


def budget_items(root: Path | str = ac.REPO_ROOT) -> list[str]:
    root_path = Path(root).resolve()
    _body, items = _build_boot_data(root_path)
    return items


def print_ki_sections(root: Path | str, ki_ids: list[str]) -> int:
    root_path = Path(root).resolve()
    docs, notes = read_ki_docs_noted(root_path)
    for note in notes:
        print(note, file=sys.stderr)
    all_sections: dict[str, str] = {}
    for doc in docs.values():
        all_sections.update(doc.sections)

    seen: set[str] = set()
    unique_ids: list[str] = []
    for ki_id in ki_ids:
        if ki_id not in seen:
            seen.add(ki_id)
            unique_ids.append(ki_id)

    found_sections: list[str] = []
    missing_ids: list[str] = []
    for ki_id in unique_ids:
        if ki_id in all_sections:
            found_sections.append(all_sections[ki_id])
        else:
            missing_ids.append(ki_id)

    if found_sections:
        print("\n\n".join(found_sections))
    for missing_id in missing_ids:
        print(f"{missing_id} not found", file=sys.stderr)

    return 1 if missing_ids else 0


def print_deferred(root: Path | str = ac.REPO_ROOT) -> int:
    root_path = Path(root).resolve()
    def_path = root_path / archive_docs.KI_DEFERRED
    if not def_path.is_file():
        print("no deferred KIs")
        return 0
    try:
        text = def_path.read_text(encoding="utf-8-sig")
        doc = archive_docs.parse_ki(text)
    except (ValueError, UnicodeDecodeError) as exc:  # a broken file is not "no deferred KIs"
        print(f"NOTE: {archive_docs.KI_DEFERRED.as_posix()} unparsable: {exc}", file=sys.stderr)
        return 1
    if not doc.rows:
        print("no deferred KIs")
        return 0
    lines = text.splitlines()
    header_idx = -1
    for idx, line in enumerate(lines):
        if re.search(r"^\|\s*ID\s*\|\s*Status\s*\|", line, re.IGNORECASE):
            if idx + 1 < len(lines) and lines[idx + 1].strip().startswith("|") and "---" in lines[idx + 1]:
                header_idx = idx
                break
    if header_idx == -1:
        print("no deferred KIs")
        return 0
    table_lines = [lines[header_idx], lines[header_idx + 1]]
    table_lines.extend(doc.rows.values())
    for line in table_lines:
        print(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ac.REPO_ROOT, help=argparse.SUPPRESS)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--status", action="store_true", help="print task states and exit")
    group.add_argument("--boot", action="store_true", help="print boot text and exit")
    group.add_argument("--ki", nargs="+", metavar="ID", help="print sections for KI ids and exit")
    group.add_argument("--deferred", action="store_true", help="print deferred table and exit")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.status:
        return print_status(root)
    if args.boot:
        print(boot_text(root))
        return 0
    if args.ki:
        return print_ki_sections(root, args.ki)
    if args.deferred:
        return print_deferred(root)
    report = lint(root)
    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    for level, rel, line, message in sorted(report.findings, key=lambda f: (order[f[0]], f[1], f[2])):
        print(f"{level} {rel}:{line}: {message}")
    print(f"lint_docs: {report.count('ERROR')} error(s), {report.count('WARN')} warning(s), {report.count('INFO')} info")
    return 1 if report.count("ERROR") else 0


if __name__ == "__main__":
    sys.exit(main())
