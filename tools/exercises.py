#!/usr/bin/env python3
"""Exercise check: declarative verification of practice exercises (spec 070-17).

Exercises are defined in `exercises.toml` within a lesson folder. Practice runs are
verified automatically against declared rules (build, exit code, output, source).
Progress is persisted in `practice/progress.json`.

Usage:
    py -3 tools/exercises.py list <lesson>
    py -3 tools/exercises.py check <lesson> --preset <preset>
    py -3 tools/exercises.py verify <lesson> (--preset <preset> | --exe <command...>)

exercises.toml keys:
    [[exercise]]
    id = "remove_mutable"                       # [a-z0-9_], unique in lesson
    title = "mutable을 지우고 오류 읽기"
    title_en = "Remove mutable and read the error"
    build = "ok" | "fail"                       # default "ok"
    build_expect = ["regex"...]                 # requires build = "fail"
    exit = 0 | "nonzero" | "any"                # default 0
    expect = ["regex"...]                       # stdout line match
    forbid = ["regex"...]                       # stdout line must not match
    source = [{ file = "main.cpp", has = ["regex"...], lacks = ["regex"...] }]
    fail_hint = "..."
    fail_hint_en = "..."
    hint = "..."
    hint_en = "..."
    answer = "..."
    answer_en = "..."

practice/progress.json shape:
    {
      "version": 1,
      "lessons": {
        "<lesson_id>": {
          "<exercise_id>": {
            "passed": "<ISO timestamp>",
            "how": "auto" | "self"
          }
        }
      }
    }
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import threading
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent
FILE = "exercises.toml"
PROGRESS_FILE = "practice/progress.json"
KEYS = (
    "id",
    "title",
    "title_en",
    "build",
    "build_expect",
    "exit",
    "expect",
    "forbid",
    "source",
    "fail_hint",
    "fail_hint_en",
    "hint",
    "hint_en",
    "answer",
    "answer_en",
)
RULE_KEYS = ("build", "build_expect", "exit", "expect", "forbid", "source")

MESSAGES: dict[str, str] = {
    "unmodified": "Workspace copy has not been modified.",
    "not_finished": "Run was stopped or timed out before completion.",
    "build_fail": "Build was expected to fail, but succeeded.",
    "build_expect": "Build log did not match expected pattern: {pattern}",
    "build_ok": "Build failed.",
    "not_run": "Program was not run.",
    "exit": "Exit code was {actual}, expected {expected}.",
    "expect": "Output did not match expected pattern: {pattern}",
    "forbid": "Output contained forbidden line matching {pattern}: {line}",
    "truncated": "Output was truncated; output rules were not checked.",
    "missing_file": "Source file '{file}' is missing.",
    "has": "File '{file}' did not match pattern: {pattern}",
    "lacks": "File '{file}' contained forbidden line matching {pattern}: {line}",
}

_LOCK = threading.Lock()


@dataclass(frozen=True)
class Source:
    file: str
    has: tuple[str, ...] = ()
    lacks: tuple[str, ...] = ()


@dataclass(frozen=True)
class Exercise:
    id: str
    title: str
    title_en: str = ""
    build: str = "ok"
    build_expect: tuple[str, ...] = ()
    exit: int | str = 0
    expect: tuple[str, ...] = ()
    forbid: tuple[str, ...] = ()
    source: tuple[Source, ...] = ()
    fail_hint: str = ""
    fail_hint_en: str = ""
    hint: str = ""
    hint_en: str = ""
    answer: str = ""
    answer_en: str = ""
    line: int = 1
    rules_written: bool = False

    @property
    def kind(self) -> str:
        return "auto" if self.rules_written else "self"


@dataclass(frozen=True)
class Problem:
    level: str  # "ERROR" | "WARN"
    message: str
    line: int | None = None


@dataclass(frozen=True)
class RunResult:
    build_ok: bool
    build_log: str = ""
    ran: bool = False
    exit_code: int | None = None
    signal: str | None = None
    stopped: bool = False
    truncated: bool = False
    stdout: str = ""


def _split_lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _find_exercise_blocks(text: str) -> list[tuple[int, int, str]]:
    """Returns (1-based start_line, 1-based end_line, block_text) for each [[exercise]]."""
    lines = text.splitlines(keepends=True)
    header_indices = []
    for idx, line in enumerate(lines):
        if re.match(r"^[ \t]*\[\[[ \t]*exercise[ \t]*\]\]", line):
            header_indices.append(idx)
    blocks = []
    for i, start_idx in enumerate(header_indices):
        end_idx = header_indices[i + 1] if i + 1 < len(header_indices) else len(lines)
        block_text = "".join(lines[start_idx:end_idx])
        blocks.append((start_idx + 1, end_idx, block_text))
    return blocks


def _line_of_key_in_block(block_text: str, key: str, base_line: int) -> int:
    match = re.search(rf"^[ \t]*{re.escape(key)}[ \t]*=", block_text, re.M)
    if match:
        return base_line + block_text.count("\n", 0, match.start())
    return base_line


def _line_of(text: str, key: str) -> int | None:
    match = re.search(rf"^[ \t]*{re.escape(key)}[ \t]*=", text, re.M)
    return text.count("\n", 0, match.start()) + 1 if match else None


def readme_items(text: str) -> int | None:
    """Count lines matching `^\\d+\\.\\s` between `## 연습` and the next `## `."""
    lines = _split_lines(text)
    found = False
    count = 0
    for line in lines:
        if not found:
            if line == "## 연습" or line.rstrip() == "## 연습":
                found = True
        else:
            if line.startswith("## "):
                break
            if re.match(r"^\d+\.\s", line):
                count += 1
    return count if found else None


def exercise_groups(exercises: Sequence[Exercise]) -> int:
    """Number of distinct ids after removing one trailing `_<single lowercase letter>`."""
    groups = {re.sub(r"_[a-z]$", "", ex.id) for ex in exercises}
    return len(groups)


def load(
    path: Path,
    files: Mapping[str, str | None] | None = None,
    readme: str | None = None,
) -> tuple[list[Exercise], list[Problem]]:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as err:
        return [], [Problem("ERROR", f"not UTF-8: {err}", line=None)]
    except OSError as err:
        return [], [Problem("ERROR", f"cannot read file: {err}", line=None)]

    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as err:
        line = getattr(err, "lineno", None)
        if line is None:
            match = re.search(r"line (\d+)", str(err))
            line = int(match.group(1)) if match else None
        return [], [Problem("ERROR", f"TOML syntax error: {err}", line=line)]

    problems: list[Problem] = []

    if not isinstance(data, dict):
        return [], [Problem("ERROR", "TOML root must be a table", line=1)]

    for key in data:
        if key != "exercise":
            problems.append(Problem("ERROR", f"unknown top-level key '{key}'", line=_line_of(text, key)))

    exercise_items = data.get("exercise")
    if exercise_items is None:
        exercise_items = []
    elif not isinstance(exercise_items, list):
        problems.append(Problem("ERROR", "'exercise' must be an array of tables", line=_line_of(text, "exercise")))
        return [], problems

    blocks = _find_exercise_blocks(text)
    seen_ids: set[str] = set()
    exercises: list[Exercise] = []

    for idx, item in enumerate(exercise_items):
        start_line = blocks[idx][0] if idx < len(blocks) else 1
        block_text = blocks[idx][2] if idx < len(blocks) else ""

        if not isinstance(item, dict):
            problems.append(Problem("ERROR", "exercise entry must be a table", line=start_line))
            continue

        ex_has_error = False
        item_id = item.get("id")
        id_line = _line_of_key_in_block(block_text, "id", start_line) if "id" in item else start_line

        # Check unknown keys
        for key in item:
            if key not in KEYS:
                k_line = _line_of_key_in_block(block_text, key, start_line)
                problems.append(Problem("ERROR", f"unknown key '{key}' in exercise", line=k_line))
                ex_has_error = True

        # Required key: id
        if "id" not in item:
            problems.append(Problem("ERROR", "missing required key 'id'", line=start_line))
            ex_has_error = True
        elif not isinstance(item["id"], str):
            problems.append(Problem("ERROR", "'id' must be a string", line=id_line))
            ex_has_error = True
        elif not re.match(r"^[a-z0-9_]+$", item["id"]):
            problems.append(Problem("ERROR", f"invalid exercise id '{item['id']}': must match [a-z0-9_]+", line=id_line))
            ex_has_error = True
        elif item["id"] in seen_ids:
            problems.append(Problem("ERROR", f"duplicate exercise id '{item['id']}'", line=id_line))
            ex_has_error = True
        else:
            seen_ids.add(item["id"])

        # Required key: title
        if "title" not in item:
            problems.append(Problem("ERROR", "missing required key 'title'", line=start_line))
            ex_has_error = True
        elif not isinstance(item["title"], str):
            title_line = _line_of_key_in_block(block_text, "title", start_line)
            problems.append(Problem("ERROR", "'title' must be a string", line=title_line))
            ex_has_error = True

        # Optional string keys
        for str_key in ("title_en", "fail_hint", "fail_hint_en", "hint", "hint_en", "answer", "answer_en"):
            if str_key in item and not isinstance(item[str_key], str):
                sk_line = _line_of_key_in_block(block_text, str_key, start_line)
                problems.append(Problem("ERROR", f"'{str_key}' must be a string", line=sk_line))
                ex_has_error = True

        # build
        if "build" in item:
            build_val = item["build"]
            build_line = _line_of_key_in_block(block_text, "build", start_line)
            if not isinstance(build_val, str) or build_val not in ("ok", "fail"):
                problems.append(Problem("ERROR", f"'build' must be 'ok' or 'fail', got {build_val!r}", line=build_line))
                ex_has_error = True

        # exit
        if "exit" in item:
            exit_val = item["exit"]
            exit_line = _line_of_key_in_block(block_text, "exit", start_line)
            if isinstance(exit_val, bool) or not (isinstance(exit_val, int) or exit_val in ("nonzero", "any")):
                problems.append(Problem("ERROR", f"'exit' must be an integer, 'nonzero', or 'any', got {exit_val!r}", line=exit_line))
                ex_has_error = True

        # list of regex string keys: build_expect, expect, forbid
        for list_key in ("build_expect", "expect", "forbid"):
            if list_key in item:
                val = item[list_key]
                lk_line = _line_of_key_in_block(block_text, list_key, start_line)
                if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                    problems.append(Problem("ERROR", f"'{list_key}' must be a list of strings", line=lk_line))
                    ex_has_error = True
                else:
                    for pat in val:
                        try:
                            re.compile(pat)
                        except re.error as err:
                            problems.append(Problem("ERROR", f"invalid regex in '{list_key}' ({pat!r}): {err}", line=lk_line))
                            ex_has_error = True

        # Combination rules for build
        if item.get("build") == "fail":
            for forbidden_key in ("exit", "expect", "forbid"):
                if forbidden_key in item:
                    fk_line = _line_of_key_in_block(block_text, forbidden_key, start_line)
                    problems.append(
                        Problem("ERROR", f"'build = \"fail\"' cannot be combined with '{forbidden_key}'", line=fk_line)
                    )
                    ex_has_error = True

        if "build_expect" in item and item.get("build") != "fail":
            be_line = _line_of_key_in_block(block_text, "build_expect", start_line)
            problems.append(Problem("ERROR", "'build_expect' requires 'build = \"fail\"'", line=be_line))
            ex_has_error = True

        # source
        if "source" in item:
            src_val = item["source"]
            src_line = _line_of_key_in_block(block_text, "source", start_line)
            if not isinstance(src_val, list) or not all(isinstance(x, dict) for x in src_val):
                problems.append(Problem("ERROR", "'source' must be a list of tables", line=src_line))
                ex_has_error = True
            else:
                for s in src_val:
                    for sk in s:
                        if sk not in ("file", "has", "lacks"):
                            problems.append(Problem("ERROR", f"unknown key '{sk}' in source table", line=src_line))
                            ex_has_error = True
                    if "file" not in s or not isinstance(s["file"], str):
                        problems.append(Problem("ERROR", "source table must have a 'file' string", line=src_line))
                        ex_has_error = True
                    else:
                        s_file = s["file"]
                        if files is not None:
                            if s_file not in files:
                                problems.append(
                                    Problem(
                                        "ERROR",
                                        f"source file '{s_file}' is not a source of the lesson or a file of a unit it uses",
                                        line=src_line,
                                    )
                                )
                                ex_has_error = True
                            elif files[s_file] is None:
                                problems.append(
                                    Problem(
                                        "ERROR",
                                        f"ambiguous: a lesson source and a unit file have this name: '{s_file}'",
                                        line=src_line,
                                    )
                                )
                                ex_has_error = True
                    for sub_list_key in ("has", "lacks"):
                        if sub_list_key in s:
                            sub_val = s[sub_list_key]
                            if not isinstance(sub_val, list) or not all(isinstance(x, str) for x in sub_val):
                                problems.append(Problem("ERROR", f"'{sub_list_key}' in source must be a list of strings", line=src_line))
                                ex_has_error = True
                            else:
                                for pat in sub_val:
                                    try:
                                        re.compile(pat)
                                    except re.error as err:
                                        problems.append(
                                            Problem("ERROR", f"invalid regex in source '{sub_list_key}' ({pat!r}): {err}", line=src_line)
                                        )
                                        ex_has_error = True

        # WARN checks
        ex_label = f"exercise '{item_id}'" if isinstance(item_id, str) else "exercise"
        if "title_en" not in item or not item["title_en"]:
            problems.append(Problem("WARN", f"{ex_label}: missing 'title_en'", line=id_line))
        if item.get("hint") and not item.get("hint_en"):
            problems.append(Problem("WARN", f"{ex_label}: 'hint' given without 'hint_en'", line=id_line))
        if item.get("answer") and not item.get("answer_en"):
            problems.append(Problem("WARN", f"{ex_label}: 'answer' given without 'answer_en'", line=id_line))
        if item.get("fail_hint") and not item.get("fail_hint_en"):
            problems.append(Problem("WARN", f"{ex_label}: 'fail_hint' given without 'fail_hint_en'", line=id_line))

        # Check patterns matching empty string
        for empty_key in ("build_expect", "expect"):
            if empty_key in item and isinstance(item[empty_key], list):
                for pat in item[empty_key]:
                    if isinstance(pat, str):
                        try:
                            if re.search(pat, ""):
                                problems.append(
                                    Problem("WARN", f"{ex_label}: pattern in '{empty_key}' matches empty string: {pat!r}", line=id_line)
                                )
                        except re.error:
                            pass

        if "source" in item and isinstance(item["source"], list):
            for s in item["source"]:
                if isinstance(s, dict) and "has" in s and isinstance(s["has"], list):
                    for pat in s["has"]:
                        if isinstance(pat, str):
                            try:
                                if re.search(pat, ""):
                                    problems.append(
                                        Problem("WARN", f"{ex_label}: pattern in source 'has' matches empty string: {pat!r}", line=id_line)
                                    )
                            except re.error:
                                pass

        if ex_has_error:
            continue

        sources = tuple(
            Source(
                file=s["file"],
                has=tuple(s.get("has", ())),
                lacks=tuple(s.get("lacks", ())),
            )
            for s in item.get("source", [])
        )

        exercises.append(
            Exercise(
                id=item["id"],
                title=item["title"],
                title_en=item.get("title_en", ""),
                build=item.get("build", "ok"),
                build_expect=tuple(item.get("build_expect", ())),
                exit=item.get("exit", 0),
                expect=tuple(item.get("expect", ())),
                forbid=tuple(item.get("forbid", ())),
                source=sources,
                fail_hint=item.get("fail_hint", ""),
                fail_hint_en=item.get("fail_hint_en", ""),
                hint=item.get("hint", ""),
                hint_en=item.get("hint_en", ""),
                answer=item.get("answer", ""),
                answer_en=item.get("answer_en", ""),
                line=id_line,
                rules_written=any(k in item for k in RULE_KEYS),
            )
        )

    if readme is not None:
        count = readme_items(readme)
        if count is not None:
            groups = exercise_groups(exercises)
            if count != groups:
                problems.append(Problem("WARN", f"README has {count} exercise item(s), but exercises.toml has {groups} group(s)", line=None))

    return exercises, problems


def evaluate(
    exercises: Sequence[Exercise],
    run: RunResult,
    files: Mapping[str, str | None],
    modified: bool,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for ex in exercises:
        if ex.kind != "auto":
            continue

        failures: list[dict[str, Any]] = []
        checked = True

        # Rule 1: unmodified
        if not modified:
            failures.append({"rule": "unmodified"})

        # Rule 2: stopped
        if run.stopped:
            failures.append({"rule": "not_finished"})
        else:
            # Rule 3: build = "fail"
            if ex.build == "fail":
                if run.build_ok:
                    failures.append({"rule": "build_fail"})
                else:
                    log_lines = _split_lines(run.build_log)
                    for pat in ex.build_expect:
                        if not any(re.search(pat, line) for line in log_lines):
                            failures.append({"rule": "build_expect", "pattern": pat})
            # Rule 4: build = "ok"
            elif ex.build == "ok":
                if not run.build_ok:
                    failures.append({"rule": "build_ok"})
                elif not run.ran:
                    failures.append({"rule": "not_run"})
                else:
                    # Check exit
                    actual: Any = run.signal if run.signal is not None else run.exit_code
                    exit_passed = False
                    if ex.exit == "any":
                        exit_passed = True
                    elif ex.exit == "nonzero":
                        if run.signal is not None:
                            exit_passed = True
                        elif run.exit_code is not None and run.exit_code != 0:
                            exit_passed = True
                    elif isinstance(ex.exit, int):
                        if run.signal is None and run.exit_code == ex.exit:
                            exit_passed = True

                    if not exit_passed:
                        failures.append({"rule": "exit", "expected": ex.exit, "actual": actual})

                    # Output rules
                    if run.truncated and (ex.expect or ex.forbid):
                        checked = False
                        failures.append({"rule": "truncated"})
                    else:
                        out_lines = _split_lines(run.stdout)
                        for pat in ex.expect:
                            if not any(re.search(pat, line) for line in out_lines):
                                failures.append({"rule": "expect", "pattern": pat})
                        for pat in ex.forbid:
                            matching_line = next((line for line in out_lines if re.search(pat, line)), None)
                            if matching_line is not None:
                                failures.append({"rule": "forbid", "pattern": pat, "line": matching_line})

        # Rule 5: Source rules
        for src in ex.source:
            text = files.get(src.file)
            if text is None:
                failures.append({"rule": "missing_file", "file": src.file})
            else:
                file_lines = _split_lines(text)
                for pat in src.has:
                    if not any(re.search(pat, line) for line in file_lines):
                        failures.append({"rule": "has", "file": src.file, "pattern": pat})
                for pat in src.lacks:
                    matching_line = next((line for line in file_lines if re.search(pat, line)), None)
                    if matching_line is not None:
                        failures.append({"rule": "lacks", "file": src.file, "pattern": pat, "line": matching_line})

        passed = len(failures) == 0 and checked
        results.append(
            {
                "id": ex.id,
                "passed": passed,
                "checked": checked,
                "failures": failures,
            }
        )

    return results


def message(failure: Mapping[str, Any]) -> str:
    rule = failure.get("rule", "")
    template = MESSAGES.get(rule)
    if template is not None:
        try:
            return template.format(**failure)
        except KeyError:
            return f"Rule '{rule}' failed."
    return f"Rule '{rule}' failed."


def public(exercise: Exercise) -> dict[str, Any]:
    return {
        "id": exercise.id,
        "title": exercise.title,
        "titleEn": exercise.title_en or None,
        "kind": exercise.kind,
        "hint": exercise.hint or None,
        "hintEn": exercise.hint_en or None,
        "answer": exercise.answer or None,
        "answerEn": exercise.answer_en or None,
        "failHint": exercise.fail_hint or None,
        "failHintEn": exercise.fail_hint_en or None,
    }


class Progress:
    def __init__(self, root: Path = ROOT) -> None:
        self.root = Path(root)
        self.path = self.root / PROGRESS_FILE

    def _read(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"version": 1, "lessons": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("version") == 1 and isinstance(data.get("lessons"), dict):
                valid = True
                for lid, ex_map in data["lessons"].items():
                    if not isinstance(lid, str) or not isinstance(ex_map, dict):
                        valid = False
                        break
                    for eid, entry in ex_map.items():
                        if not isinstance(eid, str) or not isinstance(entry, dict):
                            valid = False
                            break
                        if not isinstance(entry.get("passed"), str) or entry.get("how") not in ("auto", "self"):
                            valid = False
                            break
                    if not valid:
                        break
                if valid:
                    return data
        except (ValueError, KeyError, UnicodeDecodeError):
            pass

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        aside = self.path.with_name(f"progress.json.broken-{stamp}")
        n = 2
        while aside.exists():
            aside = self.path.with_name(f"progress.json.broken-{stamp}-{n}")
            n += 1
        try:
            os.replace(self.path, aside)
        except OSError:
            pass

        empty = {"version": 1, "lessons": {}}
        self._write(empty)
        return empty

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f"progress.json.tmp-{os.getpid()}")
        tmp.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    def lesson(self, lesson_id: str) -> dict[str, dict]:
        with _LOCK:
            data = self._read()
            return dict(data.get("lessons", {}).get(lesson_id, {}))

    def record(self, lesson_id: str, ids: Iterable[str], how: str = "auto") -> list[str]:
        with _LOCK:
            data = self._read()
            lessons = data.setdefault("lessons", {})
            lesson_dict = lessons.setdefault(lesson_id, {})
            new_ids: list[str] = []
            now = datetime.now().isoformat(timespec="seconds")
            for ex_id in ids:
                if ex_id not in lesson_dict:
                    lesson_dict[ex_id] = {"passed": now, "how": how}
                    new_ids.append(ex_id)
            if new_ids:
                self._write(data)
            return new_ids

    def set_self(self, lesson_id: str, ex_id: str, done: bool) -> None:
        with _LOCK:
            data = self._read()
            lessons = data.setdefault("lessons", {})
            lesson_dict = lessons.setdefault(lesson_id, {})
            changed = False
            if done:
                if ex_id not in lesson_dict:
                    now = datetime.now().isoformat(timespec="seconds")
                    lesson_dict[ex_id] = {"passed": now, "how": "self"}
                    changed = True
            else:
                if ex_id in lesson_dict and lesson_dict[ex_id].get("how") == "self":
                    del lesson_dict[ex_id]
                    changed = True
            if changed:
                self._write(data)

    def clear(self, lesson_id: str) -> None:
        with _LOCK:
            data = self._read()
            lessons = data.get("lessons", {})
            if lesson_id in lessons:
                del lessons[lesson_id]
                self._write(data)

    def passed_counts(self, defs_by_lesson: Mapping[str, list[str]]) -> dict[str, int]:
        with _LOCK:
            data = self._read()
            lessons = data.get("lessons", {})
            result: dict[str, int] = {}
            for lid, ex_ids in defs_by_lesson.items():
                lesson_passes = lessons.get(lid, {})
                result[lid] = sum(1 for eid in ex_ids if eid in lesson_passes)
            return result


def check_practice(
    root: Path,
    lesson_id: str,
    lesson_dir: Path,
    files: Mapping[str, str | None],
    run: RunResult,
) -> dict[str, Any]:
    root = Path(root)
    lesson_dir = Path(lesson_dir)
    toml_path = lesson_dir / FILE
    if not toml_path.is_file():
        return {}

    exercises, problems = load(toml_path, files=files)
    errors = [p for p in problems if p.level == "ERROR"]
    if errors:
        return {"exercisesError": errors[0].message}

    try:
        file_texts, modified = _practice_texts(root, files)
    except OSError as exc:
        return {"exercisesError": f"cannot read a practice copy: {exc}"}
    results = evaluate(exercises, run, files=file_texts, modified=modified)
    passed_ids = [r["id"] for r in results if r["passed"]]
    new_ids = set(Progress(root).record(lesson_id, passed_ids, how="auto"))
    return {"exercises": [{**r, "new": r["id"] in new_ids} for r in results]}


def _practice_texts(root: Path, files: Mapping[str, str | None]) -> tuple[dict[str, str | None], bool]:
    """Text of each practice copy (None when missing) and whether any copy differs from its origin."""
    texts: dict[str, str | None] = {}
    modified = False
    for name, origin in files.items():
        if origin is None:  # ambiguous name: `load` already refuses a rule that names it
            continue
        copy, source = root / "practice" / origin, root / origin
        if not copy.is_file():
            texts[name] = None
            continue
        data = copy.read_bytes()
        texts[name] = data.decode("utf-8", errors="replace")
        modified |= not source.is_file() or data != source.read_bytes()
    return texts, modified


def _tools():
    """lessons, practice and build.py for the CLI (the core above imports none of them)."""
    tools_dir = str(Path(__file__).resolve().parent)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import lessons  # noqa: E402
    import practice  # noqa: E402

    if "atugcc_build" not in sys.modules:
        spec = importlib.util.spec_from_file_location("atugcc_build", ROOT / ".agent" / "scripts" / "build.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["atugcc_build"] = module
        spec.loader.exec_module(module)
    return lessons, practice, sys.modules["atugcc_build"]


class _CliError(Exception):
    """Printed as `error: <message>`; exit 1."""


def _definitions(lessons, lesson_id: str):
    """(lesson, files map, exercises) of a lesson with a valid exercises.toml; None without the file."""
    catalog = lessons.load(ROOT)[0]
    lesson = next((l for l in catalog.lessons if l.id == lesson_id), None)
    if lesson is None:
        raise _CliError(f"unknown lesson: {lesson_id}")
    path = lesson.path / FILE
    if not path.is_file():
        return None
    files = lessons.exercise_files(catalog, lesson)
    exercises, problems = load(path, files)
    errors = [p for p in problems if p.level == "ERROR"]
    if errors:
        raise _CliError("\n".join(f"{lessons.rel(ROOT, path)}:{e.line or 1}: {e.message}" for e in errors))
    return lesson, files, exercises


def _build(build, preset: str, target: str) -> tuple[bool, str]:
    """Build one target through build.py; (ok, log). A preset of the other platform cannot run here."""
    if build.preset_platform(preset) != build.host_system():
        raise _CliError(f"preset {preset} builds for {build.preset_platform(preset)}; run this command there "
                        f"(WSL: python3 tools/exercises.py {' '.join(sys.argv[1:])})")
    proc = subprocess.run([sys.executable, str(ROOT / ".agent" / "scripts" / "build.py"), "--preset", preset,
                           "--target", target], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")


def _executable(preset: str, folder: str, target: str) -> list[str]:
    exe = ROOT / "out" / "build" / preset / "bin" / folder / (target + (".exe" if sys.platform == "win32" else ""))
    if not exe.is_file():
        raise _CliError(f"executable not found: {exe}")
    return [str(exe)]


def _run(command: list[str], cwd: Path, lesson, build_log: str) -> RunResult:
    """Run the built program in `cwd` with the lesson's time limit (quick 10 s, long its [run] timeout)."""
    limit = lesson.timeout if lesson.profile == "long" else 10
    try:
        proc = subprocess.run(command, cwd=cwd, capture_output=True, timeout=limit)
    except subprocess.TimeoutExpired as exc:
        return RunResult(build_ok=True, build_log=build_log, ran=True, stopped=True,
                         stdout=(exc.stdout or b"").decode("utf-8", errors="replace"))
    except OSError as exc:
        raise _CliError(f"cannot run {command[0]}: {exc}") from None
    code, name = proc.returncode, None
    if code < 0:  # POSIX: killed by a signal
        try:
            name = signal.Signals(-code).name
        except ValueError:
            name = str(-code)
        code = None
    return RunResult(build_ok=True, build_log=build_log, ran=True, exit_code=code, signal=name,
                     stdout=proc.stdout.decode("utf-8", errors="replace"))


def _table(rows: list[tuple[str, ...]]) -> None:
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]) - 1)]
    for row in rows:
        print("  ".join([c.ljust(w) for c, w in zip(row, widths)] + [row[-1]]).rstrip())


def _cmd_list(lesson_id: str) -> int:
    lessons, _, _ = _tools()
    found = _definitions(lessons, lesson_id)
    if found is None:
        raise _CliError(f"lesson {lesson_id} has no {FILE}")
    progress = Progress(ROOT).lesson(lesson_id)
    _table([("ID", "KIND", "DONE", "TITLE")] + [
        (e.id, e.kind, f"yes ({progress[e.id]['how']})" if e.id in progress else "-", e.title) for e in found[2]])
    return 0


def _cmd_check(lesson_id: str, preset: str) -> int:
    """Build and run the practice copy, check it as the page does, record the passes (Assumption 13)."""
    lessons, practice, build = _tools()
    found = _definitions(lessons, lesson_id)
    if found is None:
        raise _CliError(f"lesson {lesson_id} has no {FILE}")
    lesson, files, _ = found
    folder = ROOT / practice.Workspace(ROOT).start(lesson_id)["dir"]
    target = f"practice_{lesson_id}"
    ok, log = _build(build, preset, target)
    run = _run(_executable(preset, "practice", target), folder, lesson, log) if ok else RunResult(False, log)
    out = check_practice(ROOT, lesson_id, lesson.path, files, run)
    if "exercisesError" in out:
        raise _CliError(out["exercisesError"])
    rows = [("ID", "RESULT", "MESSAGE")]
    for r in out.get("exercises", []):
        if r["passed"]:
            rows.append((r["id"], "pass (new)" if r["new"] else "pass", ""))
        for f in r["failures"]:
            rows.append((r["id"], "fail" if r["checked"] else "unchecked", message(f)))
    _table(rows)
    return 0


def _cmd_verify(lesson_id: str, preset: str | None, command: list[str] | None) -> int:
    """No automatic exercise may pass on the unchanged lesson (spec Assumption 5)."""
    lessons, _, build = _tools()
    found = _definitions(lessons, lesson_id)
    if found is None:
        return 0
    lesson, files, exercises = found
    if command:  # already built (CTest): a launcher may come before the path
        run = _run(command, lesson.path, lesson, "")
    else:
        if preset is None:
            raise _CliError("give --preset or --exe <command>")
        target = f"lesson_{lesson_id}"
        ok, log = _build(build, preset, target)
        run = _run(_executable(preset, "lessons", target), lesson.path, lesson, log) if ok else RunResult(False, log)
    texts = {name: (ROOT / origin).read_text(encoding="utf-8", errors="replace")
             if origin and (ROOT / origin).is_file() else None for name, origin in files.items()}
    passing = [r["id"] for r in evaluate(exercises, run, texts, modified=True) if r["passed"]]
    for ex_id in passing:
        print(f"error: exercise {ex_id!r} of lesson {lesson_id} passes on the unchanged lesson", file=sys.stderr)
    if not passing:
        print(f"{lesson_id}: no automatic exercise passes on the unchanged lesson")
    return 1 if passing else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="exercises.py", description="Exercise definitions and checks (spec 070-17).")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="the lesson's exercises and progress").add_argument("lesson")
    check = sub.add_parser("check", help="build and run the practice copy, check the exercises")
    check.add_argument("lesson")
    check.add_argument("--preset", required=True)
    verify = sub.add_parser("verify", help="the unchanged lesson must pass no automatic exercise")
    verify.add_argument("lesson")
    verify.add_argument("--preset")
    verify.add_argument("--exe", nargs=argparse.REMAINDER, metavar="COMMAND",
                        help="run this already built program (the rest of the line; a launcher may come first)")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            return _cmd_list(args.lesson)
        if args.command == "check":
            return _cmd_check(args.lesson, args.preset)
        return _cmd_verify(args.lesson, args.preset, args.exe)
    except (_CliError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
