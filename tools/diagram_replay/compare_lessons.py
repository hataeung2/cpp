#!/usr/bin/env python3
"""Spec 070-07 AC-1: replaying a run's events to the last seq gives the diagram its Tracers wrote.

    py -3 tools/diagram_replay/compare_lessons.py [--preset windows-x64-debug] [--lesson ID ...]

For every lesson executable that is built (out/build/<preset>/bin/lessons), run it with
ATUGCC_TRACE_OUT, take the `diagram` lines each Tracer wrote when it was destroyed, run
`atugcc_diagram_replay --tracer <id> --until <last seq>` on the same trace file, and compare the two
sets of lines byte for byte. Build first: build.py --preset <p> --target atugcc_diagram_replay (and the
lessons). A lesson without a Tracer shows "no tracer". Exit 0: all equal; 1: a difference; 2: setup problem.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import lessons  # noqa: E402

EXE = ".exe" if os.name == "nt" else ""
RUN_TIMEOUT_SEC = 120


def default_preset() -> str:
    return "windows-x64-debug" if os.name == "nt" else "linux-x64-debug"


def trace_lines(path: Path) -> list[str]:
    return [line.rstrip("\r") for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def compare_lesson(lesson, bin_dir: Path, tool: Path) -> tuple[str, bool]:
    exe = bin_dir / "lessons" / f"lesson_{lesson.id}{EXE}"
    if not exe.is_file():
        return "not built", True
    with tempfile.TemporaryDirectory(prefix="atugcc_replay_") as tmp:
        trace = Path(tmp) / "trace.jsonl"
        env = dict(os.environ, ATUGCC_TRACE_OUT=str(trace))
        try:
            subprocess.run([str(exe)], cwd=lesson.path, env=env, capture_output=True,
                           timeout=RUN_TIMEOUT_SEC, check=False)
        except subprocess.TimeoutExpired:
            return f"run timed out ({RUN_TIMEOUT_SEC} s)", False
        if not trace.is_file():
            return "no trace file", True
        lines = trace_lines(trace)
        objs = []
        for line in lines:
            try:
                objs.append((line, json.loads(line)))
            except ValueError:
                return f"unreadable trace line: {line[:60]}", False
        expected: dict[int, list[str]] = {}
        last_seq: dict[int, int] = {}
        for line, obj in objs:
            tracer = obj.get("tracer")
            if not isinstance(tracer, int):
                continue
            if obj.get("kind") == "diagram":
                expected.setdefault(tracer, []).append(line)
            elif obj.get("kind") in ("message", "transition", "node"):
                last_seq[tracer] = max(last_seq.get(tracer, 0), obj["seq"])
        if not expected:
            return "no tracer", True
        compared = 0
        for tracer, want in sorted(expected.items()):
            done = subprocess.run([str(tool), "--tracer", str(tracer), "--until", str(last_seq.get(tracer, 0))],
                                  input="\n".join(lines) + "\n", capture_output=True, text=True,
                                  encoding="utf-8", timeout=RUN_TIMEOUT_SEC, check=False)
            got = [line.rstrip("\r") for line in done.stdout.splitlines()]
            if done.returncode != 0 or got != want:
                return f"tracer {tracer}: {len(want)} diagram lines written, replay gave {len(got)}", False
            compared += len(want)
        return f"{len(expected)} tracer(s), {compared} diagram line(s) equal", True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--preset", default=default_preset())
    parser.add_argument("--lesson", action="append", default=[], help="only this lesson id (repeatable)")
    args = parser.parse_args(argv)

    bin_dir = ROOT / "out" / "build" / args.preset / "bin"
    tool = bin_dir / "tools" / f"atugcc_diagram_replay{EXE}"
    if not tool.is_file():
        print(f"error: {tool.relative_to(ROOT).as_posix()} is not built", file=sys.stderr)
        return 2
    catalog, _ = lessons.load(ROOT)
    failed = False
    for lesson in catalog.lessons:
        if args.lesson and lesson.id not in args.lesson:
            continue
        message, ok = compare_lesson(lesson, bin_dir, tool)
        failed |= not ok
        print(f"{'OK  ' if ok else 'FAIL'} {lesson.id}: {message}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
