#!/usr/bin/env python3
"""End-to-end check of the ATUGCC_TRACE_OUT JSON Lines stream (spec 020-05 AC-2, AC-4, AC-5).

Usage: check_trace_stream.py -- <command that runs trace_stream_probe> [args...]

The command runs three times: without the variable, with it pointing at a file, and with it
pointing into a missing directory. stdout must be identical each time (the probe prints its
expectations), every stream line must be valid JSON matching the v1 schema, and the stream must
hold exactly the recorded events plus the Mermaid diagram parts the probe reported.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ENV = "ATUGCC_TRACE_OUT"
META_KEYS = {"file", "line", "func", "tUs"}
EVENT_KEYS = {
    "message": {"v", "kind", "seq", "tracer", "from", "to", "action"} | META_KEYS,
    "transition": {"v", "kind", "seq", "tracer", "old", "new", "trigger"} | META_KEYS,
    "node": {"v", "kind", "seq", "tracer", "parent", "child", "relation"} | META_KEYS,
}
DIAGRAM_KEYS = {"v", "kind", "tracer", "part", "parts", "diagram", "backend", "title", "overBudget", "source"}
# The probe records exactly these labels. They are written out here, not reported by the probe,
# so a wrong escape in the library cannot cancel itself out on both sides.
EXPECTED_LABELS = [
    'Quote"Back\\slash',
    "Tab\tNew\nline\rCR",
    "bs\bff\fctl\x01f\x1fend",
    "한글 라벨",
]

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def run(command: list[str], trace_out: str | None) -> bytes:
    env = dict(os.environ)
    env.pop(ENV, None)
    if trace_out is not None:
        env[ENV] = trace_out
    result = subprocess.run(command, env=env, capture_output=True, timeout=120)
    if result.returncode != 0:
        sys.exit(f"check_trace_stream: {ENV}={trace_out!r}: exit {result.returncode}\n"
                 f"{result.stderr.decode('utf-8', 'replace')}")
    return result.stdout


def check_stream(lines: list[str], summary: dict) -> None:
    records = []
    for number, line in enumerate(lines, 1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            failures.append(f"line {number} is not JSON ({error}): {line[:120]}")
    if failures:
        return

    events = [r for r in records if r.get("kind") in EVENT_KEYS]
    diagrams = [r for r in records if r.get("kind") == "diagram"]
    check(len(events) + len(diagrams) == len(records), "stream holds a record of an unknown kind")
    check(all(r.get("v") == 1 for r in records), "a record without \"v\":1")

    check(len(events) == summary["events"], f"{len(events)} event lines, probe recorded {summary['events']}")
    for event in events:
        check(set(event) == EVENT_KEYS[event["kind"]], f"{event['kind']} keys {sorted(event)}")
        check(event["file"].endswith("trace_stream_probe.cpp"), f"file {event['file']!r}")
        check(isinstance(event["line"], int) and event["line"] > 0, f"line {event['line']!r}")
    seqs = [event["seq"] for event in events]
    check(len(set(seqs)) == len(seqs), "duplicate seq values")
    check(all(isinstance(s, int) and s > 0 for s in seqs), "seq must be a positive integer")

    actions = {event["action"] for event in events if event["kind"] == "message"}
    for label in EXPECTED_LABELS:
        check(label in actions, f"label {label!r} did not round-trip")

    for diagram in diagrams:
        check(set(diagram) == DIAGRAM_KEYS, f"diagram keys {sorted(diagram)}")
        check(diagram["backend"] == "mermaid", f"backend {diagram['backend']!r}")
    counts = Counter((str(d["tracer"]), d["diagram"]) for d in diagrams)
    expected = {(tracer, kind): n for tracer, kinds in summary["tracers"].items() for kind, n in kinds.items() if n}
    check(dict(counts) == expected, f"diagram parts {dict(counts)} != probe {expected}")
    for (tracer, kind), n in expected.items():
        mine = [d for d in diagrams if str(d["tracer"]) == tracer and d["diagram"] == kind]
        check(sorted(d["part"] for d in mine) == list(range(n)), f"part indices of {tracer}/{kind}")
        check(all(d["parts"] == n for d in mine), f"parts count of {tracer}/{kind}")


def main(argv: list[str]) -> int:
    if "--" not in argv or argv.index("--") == len(argv) - 1:
        sys.exit(__doc__)
    command = argv[argv.index("--") + 1:]

    with tempfile.TemporaryDirectory() as tmp:
        trace = Path(tmp) / "trace.jsonl"
        plain = run(command, None)
        streamed = run(command, str(trace))
        unopenable = run(command, str(Path(tmp) / "missing_dir" / "trace.jsonl"))

        check(plain == streamed, "stdout changes when the variable is set")
        check(plain == unopenable, "stdout changes when the trace file cannot be opened")
        check(not (Path(tmp) / "missing_dir").exists(), "a missing directory was created")
        check(trace.is_file(), "trace file was not written")

        summary = json.loads(plain.decode("utf-8"))
        if trace.is_file():
            check_stream(trace.read_text(encoding="utf-8").splitlines(), summary)

    if failures:
        print("check_trace_stream: FAILED")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"check_trace_stream: OK ({summary['events']} events, "
          f"{sum(n for kinds in summary['tracers'].values() for n in kinds.values())} diagram parts)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
