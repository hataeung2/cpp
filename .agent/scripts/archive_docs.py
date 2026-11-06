#!/usr/bin/env python3
"""Archive docs: move closed known issues and completed tasks to archive files.

Usage:
    py -3 .agent/scripts/archive_docs.py            (Windows; Linux: python3)
    py -3 .agent/scripts/archive_docs.py --dry-run  (show planned moves without writing)

Locations are decided by status:
- Known issues: OPEN, PLANNED in docs/known_issues.md; DEFERRED in docs/known_issues_deferred.md;
  CLOSED in docs/archive/known_issues_closed.md.
- Tasks: top-level DONE tasks whose patch lines are all DONE move to docs/archive/agent_todo_done.md.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_common as ac  # noqa: E402

TODO = Path("docs/agent_todo.md")
TODO_DONE = Path("docs/archive/agent_todo_done.md")
KNOWN_ISSUES = Path("docs/known_issues.md")
KI_DEFERRED = Path("docs/known_issues_deferred.md")
KI_CLOSED = Path("docs/archive/known_issues_closed.md")
KI_FILES = (KNOWN_ISSUES, KI_DEFERRED, KI_CLOSED)

KI_HOME: dict[str, Path] = {
    "OPEN": KNOWN_ISSUES,
    "PLANNED": KNOWN_ISSUES,
    "DEFERRED": KI_DEFERRED,
    "CLOSED": KI_CLOSED,
}

KI_CLOSED_INITIAL = """\
# Closed Known Issues

Closed known issues. `py -3 .agent/scripts/archive_docs.py` moves a KI here when its Status becomes CLOSED, from docs/known_issues.md or docs/known_issues_deferred.md. A sealed record: do not edit entries.

| ID | Status | Area | Found | Owner |
|---|---|---|---|---|
"""

KI_DEFERRED_INITIAL = """\
# Deferred Known Issues

Deferred known issues: revisit when the condition in the Owner column happens. `py -3 .agent/scripts/archive_docs.py` moves a KI here when its Status becomes DEFERRED; set the Status back to OPEN and run it again to move the KI to docs/known_issues.md.

| ID | Status | Area | Found | Owner |
|---|---|---|---|---|
"""

KNOWN_ISSUES_INITIAL = """\
# Known Issues & Follow-ups

| ID | Status | Area | Found | Owner |
|---|---|---|---|---|
"""

TODO_DONE_INITIAL = """\
# Tasks (Archive)

DONE tasks. `py -3 .agent/scripts/archive_docs.py` moves a task here from docs/agent_todo.md when it and all its patch lines are DONE (workflow step 6). Group counts in agent_todo.md include these lines. A sealed record: do not edit entries.

---
"""

KI_ROW_RE = re.compile(
    r"^\|\s*(?P<id>KI-\d+)\s*\|\s*(?P<status>[A-Z_]+)\s*\|(?P<rest>.*)$"
)
SECTION_HEADER_RE = re.compile(r"^##\s+(?P<id>KI-\d+)\b")
COUNT_SUFFIX_RE = re.compile(r"\s*\(\d+/\d+\s+DONE\)\s*$")


@dataclass
class KiDoc:
    preamble: str
    rows: dict[str, str]
    statuses: dict[str, str]
    sections: dict[str, str]


@dataclass
class TodoTaskBlock:
    task_id: str
    lines: list[str]


def ki_sort_key(ki_id: str) -> tuple[int, str]:
    m = re.search(r"\d+", ki_id)
    return (int(m.group(0)) if m else 0, ki_id)


def parse_ki(text: str) -> KiDoc:
    """Parse a known issues markdown document into a KiDoc model.

    Raises ValueError if table header or separator line is missing, if a non-blank line
    appears between the table rows and the first ## KI- section, or if duplicate KI ids
    appear among the rows or sections.
    """
    normalized = text.replace("\r\n", "\n")
    lines = normalized.splitlines()

    header_idx = -1
    for idx, line in enumerate(lines):
        if re.search(r"^\|\s*ID\s*\|\s*Status\s*\|", line, re.IGNORECASE):
            if idx + 1 < len(lines):
                sep = lines[idx + 1].strip()
                if sep.startswith("|") and "---" in sep:
                    header_idx = idx
                    break

    if header_idx == -1:
        raise ValueError("missing table header '| ID | Status |' and separator line")

    preamble = "\n".join(lines[: header_idx + 2]) + "\n"

    rows: dict[str, str] = {}
    statuses: dict[str, str] = {}
    cur = header_idx + 2
    while cur < len(lines):
        line = lines[cur]
        m = KI_ROW_RE.match(line)
        if m:
            ki_id = m.group("id")
            if ki_id in rows:
                raise ValueError(f"duplicate KI id {ki_id} in table rows")
            rows[ki_id] = line
            statuses[ki_id] = m.group("status")
            cur += 1
        else:
            break

    while cur < len(lines) and not lines[cur].strip():
        cur += 1

    if cur < len(lines) and not SECTION_HEADER_RE.match(lines[cur]):
        raise ValueError(f"non-blank line between table and sections: {lines[cur]!r}")

    sections: dict[str, str] = {}
    while cur < len(lines):
        m = SECTION_HEADER_RE.match(lines[cur])
        if not m:
            if not lines[cur].strip():
                cur += 1
                continue
            raise ValueError(f"unexpected line in sections: {lines[cur]!r}")
        ki_id = m.group("id")
        if ki_id in sections:
            raise ValueError(f"duplicate KI id {ki_id} in sections")
        sec_lines = [lines[cur]]
        cur += 1
        while cur < len(lines) and not SECTION_HEADER_RE.match(lines[cur]):
            sec_lines.append(lines[cur])
            cur += 1
        while sec_lines and not sec_lines[-1].strip():
            sec_lines.pop()
        sections[ki_id] = "\n".join(sec_lines)

    return KiDoc(preamble=preamble, rows=rows, statuses=statuses, sections=sections)


def render_ki(doc: KiDoc) -> str:
    """Render a KiDoc into a Markdown string."""
    preamble = doc.preamble if doc.preamble.endswith("\n") else doc.preamble + "\n"
    parts: list[str] = [preamble]

    if doc.rows:
        sorted_row_ids = sorted(doc.rows.keys(), key=ki_sort_key)
        rows_str = "\n".join(doc.rows[k] for k in sorted_row_ids) + "\n"
        parts.append(rows_str)
        if doc.sections:
            parts.append("\n")
            sorted_sec_ids = sorted(doc.sections.keys(), key=ki_sort_key)
            sections_str = "\n\n".join(doc.sections[k] for k in sorted_sec_ids) + "\n"
            parts.append(sections_str)
    elif doc.sections:
        parts.append("\n")
        sorted_sec_ids = sorted(doc.sections.keys(), key=ki_sort_key)
        sections_str = "\n\n".join(doc.sections[k] for k in sorted_sec_ids) + "\n"
        parts.append(sections_str)

    return "".join(parts)


def read_ki_docs(root: Path) -> dict[Path, KiDoc]:
    """Read existing KI files under root into a map of relative Path -> KiDoc."""
    docs: dict[Path, KiDoc] = {}
    for rel_path in KI_FILES:
        full_path = root / rel_path
        if full_path.is_file():
            text = full_path.read_text(encoding="utf-8")
            docs[rel_path] = parse_ki(text)
    return docs


def archive_heading(heading: str) -> str:
    """Drop a trailing ` (k/n DONE)` from a group heading."""
    return COUNT_SUFFIX_RE.sub("", heading.rstrip("\r\n"))


def is_block_movable(block: TodoTaskBlock) -> bool:
    """A block is movable when its top-level task and all its patch lines are DONE."""
    top_m = ac.TASK_LINE_RE.match(block.lines[0])
    if not top_m or top_m.group("state") != "DONE":
        return False
    for patch_line in block.lines[1:]:
        patch_m = ac.TASK_LINE_RE.match(patch_line)
        if not patch_m or patch_m.group("state") != "DONE":
            return False
    return True


def parse_todo_body(
    body_lines: list[str],
    filename: Path | str,
) -> tuple[list[tuple[str, Any]], list[str], dict[str, list[TodoTaskBlock]]]:
    """Parse body lines of a todo or archive_todo document.

    Validates that:
    - Any non-blank line is either a '## ' heading, a top-level task line, or an indented
      task line directly following a task line (with no blank line between).
    - Task lines must not appear before the first '## ' heading.
    """
    items: list[tuple[str, Any]] = []
    group_order: list[str] = []
    blocks_by_group: dict[str, list[TodoTaskBlock]] = {}

    current_group: str | None = None
    last_was_task_line: bool = False
    current_block: TodoTaskBlock | None = None

    for line in body_lines:
        if not line.strip():
            last_was_task_line = False
            current_block = None
            items.append(("blank", line))
            continue

        if line.startswith("## "):
            last_was_task_line = False
            current_block = None
            current_group = archive_heading(line)
            if current_group not in group_order:
                group_order.append(current_group)
            items.append(("heading", line, current_group))
            continue

        m = ac.TASK_LINE_RE.match(line)
        if m:
            if not m.group("indent"):
                # Top-level task line
                if current_group is None:
                    raise ValueError(f"{filename}: task line before first '## ' heading: {line!r}")
                current_block = TodoTaskBlock(task_id=m.group("id"), lines=[line])
                blocks_by_group.setdefault(current_group, []).append(current_block)
                items.append(("block", current_block, current_group))
                last_was_task_line = True
            else:
                # Indented task line (patch) directly under a task
                if not last_was_task_line or current_block is None:
                    raise ValueError(f"{filename}: indented task line not directly under a task: {line!r}")
                current_block.lines.append(line)
                last_was_task_line = True
            continue

        raise ValueError(f"{filename}: unexpected line: {line!r}")

    return items, group_order, blocks_by_group


def movable_task_ids(todo_text: str) -> list[str]:
    """Top-level DONE task IDs whose indented patch lines are all DONE."""
    lines = todo_text.replace("\r\n", "\n").splitlines()
    sep_idx = -1
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            sep_idx = idx
            break
    if sep_idx == -1:
        return []

    body_lines = lines[sep_idx + 1:]
    items, _, _ = parse_todo_body(body_lines, TODO)
    movable: list[str] = []
    for item in items:
        if item[0] == "block":
            block: TodoTaskBlock = item[1]
            if is_block_movable(block):
                movable.append(block.task_id)
    return movable


def initial_ki_template(path: Path) -> str:
    if path == KI_CLOSED:
        return KI_CLOSED_INITIAL
    elif path == KI_DEFERRED:
        return KI_DEFERRED_INITIAL
    return KNOWN_ISSUES_INITIAL


def plan_moves(root: Path) -> list[tuple[str, Path, Path]]:
    """Plan moves of KIs and completed tasks without writing any files."""
    moves: list[tuple[str, Path, Path]] = []

    # 1. KI duplicate check across files and plan KI moves
    ki_docs = read_ki_docs(root)
    seen_ki_ids: dict[str, Path] = {}
    for path in KI_FILES:
        doc = ki_docs.get(path)
        if not doc:
            continue
        file_ids = set(doc.rows.keys()) | set(doc.sections.keys())
        for ki_id in file_ids:
            if ki_id in seen_ki_ids:
                raise ValueError(f"KI id {ki_id} present in multiple files: {seen_ki_ids[ki_id]} and {path}")
            seen_ki_ids[ki_id] = path

        for ki_id in sorted(doc.statuses.keys(), key=ki_sort_key):
            status = doc.statuses[ki_id]
            target_path = KI_HOME.get(status)
            if target_path and target_path != path:
                if ki_id not in doc.sections:  # checked here so that --dry-run refuses too
                    raise ValueError(f"KI section for {ki_id} missing in {path}")
                moves.append((ki_id, path, target_path))

    # 2. Todo duplicate checks and plan todo moves
    todo_done_file = root / TODO_DONE
    done_task_ids: set[str] = set()
    if todo_done_file.is_file():
        done_text = todo_done_file.read_text(encoding="utf-8")
        lines = done_text.replace("\r\n", "\n").splitlines()
        sep_idx = -1
        for idx, line in enumerate(lines):
            if line.strip() == "---":
                sep_idx = idx
                break
        if sep_idx == -1:
            raise ValueError(f"{TODO_DONE}: missing '---' separator line")
        _, _, done_blocks = parse_todo_body(lines[sep_idx + 1:], TODO_DONE)
        for blocks in done_blocks.values():
            for b in blocks:
                for line in b.lines:
                    m = ac.TASK_LINE_RE.match(line)
                    if m:
                        tid = m.group("id")
                        if tid in done_task_ids:
                            raise ValueError(f"duplicate task id in {TODO_DONE}: {tid}")
                        done_task_ids.add(tid)

    todo_path = root / TODO
    if todo_path.is_file():
        todo_text = todo_path.read_text(encoding="utf-8")
        lines = todo_text.replace("\r\n", "\n").splitlines()
        sep_idx = -1
        for idx, line in enumerate(lines):
            if line.strip() == "---":
                sep_idx = idx
                break
        if sep_idx != -1:
            _, _, todo_blocks = parse_todo_body(lines[sep_idx + 1:], TODO)
            seen_todo_ids: set[str] = set()
            for blocks in todo_blocks.values():
                for b in blocks:
                    for line in b.lines:
                        m = ac.TASK_LINE_RE.match(line)
                        if m:
                            tid = m.group("id")
                            if tid in seen_todo_ids:
                                raise ValueError(f"task id appears twice in todo: {tid}")
                            seen_todo_ids.add(tid)
                            if tid in done_task_ids:
                                raise ValueError(f"task id in todo already in {TODO_DONE}: {tid}")

        movable = movable_task_ids(todo_text)
        for task_id in movable:
            moves.append((task_id, TODO, TODO_DONE))

    return moves


def update_todo(
    todo_text: str,
    movable_ids: set[str] | None = None,
) -> tuple[str, dict[str, list[TodoTaskBlock]], list[str]]:
    lines = todo_text.replace("\r\n", "\n").splitlines()
    sep_idx = -1
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            sep_idx = idx
            break

    if sep_idx == -1:
        return todo_text, {}, []

    preamble_lines = lines[: sep_idx + 1]
    body_lines = lines[sep_idx + 1:]
    items, todo_group_order, _ = parse_todo_body(body_lines, TODO)

    moved_tasks_by_group: dict[str, list[TodoTaskBlock]] = {}
    retained_body_lines: list[str] = []

    for item in items:
        kind = item[0]
        if kind == "heading":
            retained_body_lines.append(item[1])
        elif kind == "blank":
            retained_body_lines.append(item[1])
        elif kind == "block":
            block: TodoTaskBlock = item[1]
            group: str = item[2]
            should_move = (
                is_block_movable(block)
                if movable_ids is None
                else (block.task_id in movable_ids and is_block_movable(block))
            )
            if should_move:
                moved_tasks_by_group.setdefault(group, []).append(block)
            else:
                retained_body_lines.extend(block.lines)

    while retained_body_lines and not retained_body_lines[-1].strip():
        retained_body_lines.pop()

    all_lines = preamble_lines + retained_body_lines
    new_todo_content = "\n".join(all_lines) + "\n"
    return new_todo_content, moved_tasks_by_group, todo_group_order


def update_todo_done(
    done_text: str | None,
    moved_tasks_by_group: dict[str, list[TodoTaskBlock]],
    todo_group_order: list[str],
) -> str:
    if done_text is not None:
        lines = done_text.replace("\r\n", "\n").splitlines()
        sep_idx = -1
        for idx, line in enumerate(lines):
            if line.strip() == "---":
                sep_idx = idx
                break
        if sep_idx == -1:
            raise ValueError(f"{TODO_DONE}: missing '---' separator line")
        done_preamble = "\n".join(lines[: sep_idx + 1]) + "\n"
        done_body = lines[sep_idx + 1:]
    else:
        done_preamble = TODO_DONE_INITIAL.rstrip("\n") + "\n"
        done_body = []

    _, existing_group_order, existing_groups = parse_todo_body(done_body, TODO_DONE)

    all_groups: dict[str, list[TodoTaskBlock]] = {}
    for g, blocks in existing_groups.items():
        all_groups[g] = list(blocks)
    for g, blocks in moved_tasks_by_group.items():
        all_groups.setdefault(g, []).extend(blocks)

    def task_sort_key(block: TodoTaskBlock) -> tuple[int, ...]:
        parts = re.findall(r"\d+", block.task_id)
        return tuple(int(p) for p in parts)

    for g in all_groups:
        all_groups[g].sort(key=task_sort_key)

    ordered_groups: list[str] = []
    for g in todo_group_order:
        if g in all_groups and all_groups[g] and g not in ordered_groups:
            ordered_groups.append(g)
    for g in existing_group_order:
        if g in all_groups and all_groups[g] and g not in ordered_groups:
            ordered_groups.append(g)
    for g in all_groups:
        if all_groups[g] and g not in ordered_groups:
            ordered_groups.append(g)

    rendered_groups: list[str] = []
    for g in ordered_groups:
        blocks = all_groups[g]
        heading_line = g if g.startswith("## ") else f"## {g}"
        group_lines = [heading_line]
        for b in blocks:
            group_lines.extend(b.lines)
        rendered_groups.append("\n".join(group_lines))

    if rendered_groups:
        return done_preamble.rstrip("\n") + "\n\n" + "\n\n".join(rendered_groups) + "\n"
    return done_preamble.rstrip("\n") + "\n"


def apply(root: Path) -> list[tuple[str, Path, Path]]:
    """Apply planned moves, writing only modified files."""
    moves = plan_moves(root)
    if not moves:
        return []

    ki_moves = [m for m in moves if m[1] in KI_FILES]
    todo_moves = [m for m in moves if m[1] == TODO]

    new_contents: dict[Path, str] = {}

    if ki_moves:
        ki_docs = read_ki_docs(root)
        for _, _, dst in ki_moves:
            if dst not in ki_docs:
                ki_docs[dst] = parse_ki(initial_ki_template(dst))

        # Check presence before popping any move (Finding 6)
        for ki_id, src, dst in ki_moves:
            src_doc = ki_docs[src]
            if ki_id not in src_doc.rows:
                raise ValueError(f"KI row for {ki_id} missing in {src}")
            if ki_id not in src_doc.sections:
                raise ValueError(f"KI section for {ki_id} missing in {src}")

        # Pop and move
        touched_ki_files: set[Path] = set()
        for ki_id, src, dst in ki_moves:
            touched_ki_files.add(src)
            touched_ki_files.add(dst)
            src_doc = ki_docs[src]
            dst_doc = ki_docs[dst]

            row = src_doc.rows.pop(ki_id)
            status = src_doc.statuses.pop(ki_id)
            section = src_doc.sections.pop(ki_id)

            dst_doc.rows[ki_id] = row
            dst_doc.statuses[ki_id] = status
            dst_doc.sections[ki_id] = section

        # Re-render ONLY touched KI files (Finding 5)
        for path in touched_ki_files:
            new_contents[path] = render_ki(ki_docs[path])

    if todo_moves:
        todo_file = root / TODO
        todo_text = todo_file.read_text(encoding="utf-8")
        planned_todo_ids = {m[0] for m in todo_moves}
        new_todo_content, moved_groups, todo_group_order = update_todo(todo_text, planned_todo_ids)
        moved_ids = {b.task_id for blocks in moved_groups.values() for b in blocks}
        if moved_ids != planned_todo_ids:
            raise ValueError(f"todo move mismatch: planned {planned_todo_ids} != applied {moved_ids}")

        new_contents[TODO] = new_todo_content

        done_file = root / TODO_DONE
        done_text = done_file.read_text(encoding="utf-8") if done_file.is_file() else None
        new_done_content = update_todo_done(
            done_text,
            moved_tasks_by_group=moved_groups,
            todo_group_order=todo_group_order,
        )
        new_contents[TODO_DONE] = new_done_content

    for path, content in new_contents.items():
        file_path = root / path
        existing_content = file_path.read_text(encoding="utf-8") if file_path.is_file() else None
        if existing_content != content:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8", newline="\n")

    return moves


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--root", type=Path, default=ac.REPO_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true", help="show planned moves without writing files")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    try:
        if args.dry_run:
            moves = plan_moves(root)
        else:
            moves = apply(root)
    except ValueError as e:
        sys.stderr.write(f"archive_docs: {e}\n")
        return 1

    if not moves:
        print("nothing to move")
    else:
        for item_id, _src, dst in moves:
            print(f"moved {item_id} -> {dst.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
