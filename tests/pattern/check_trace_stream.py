#!/usr/bin/env python3
"""End-to-end check of the ATUGCC_TRACE_OUT JSON Lines stream (spec 020-05 AC-2, AC-4, AC-5;
spec 020-06 AC-3, AC-8 for span lines, ATUGCC_SPAN_METER and ATUGCC_TRACE_FLUSH_MS).

Usage: check_trace_stream.py -- <command that runs trace_stream_probe> [args...]

The command runs three times: without the variable, with it pointing at a file, and with it
pointing into a missing directory; then with ATUGCC_SPAN_METER=cpu, with an unknown meter name,
and with ATUGCC_TRACE_FLUSH_MS=100. stdout must be identical each time (the probe prints its
expectations), every stream line must be valid JSON matching the v1 schema, and the stream must
hold exactly the recorded events and spans plus the Mermaid diagram parts the probe reported.
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
METER_ENV = "ATUGCC_SPAN_METER"
FLUSH_ENV = "ATUGCC_TRACE_FLUSH_MS"
META_KEYS = {"file", "line", "func", "tUs"}
EVENT_KEYS = {
    "message": {"v", "kind", "seq", "tracer", "from", "to", "action"} | META_KEYS,
    "transition": {"v", "kind", "seq", "tracer", "old", "new", "trigger"} | META_KEYS,
    "node": {"v", "kind", "seq", "tracer", "parent", "child", "relation"} | META_KEYS,
}
SPAN_KEYS = {"v", "kind", "seq", "tracer", "label", "meter", "durNs", "thread"} | META_KEYS
DIAGRAM_KEYS = {"v", "kind", "tracer", "part", "parts", "diagram", "backend", "title", "overBudget", "source"}
# The probe records exactly these labels. They are written out here, not reported by the probe,
# so a wrong escape in the library cannot cancel itself out on both sides.
EXPECTED_LABELS = [
    'Quote"Back\\slash',
    "Tab\tNew\nline\rCR",
    "bs\bff\fctl\x01f\x1fend",
    "한글 라벨",
]
# Spans the probe times with the Tracer's meter, and the one it records as an outside measurement.
SCOPED_SPAN_LABELS = ["probe scope", '구간 "quoted"']
PERF_SPAN = {"label": "external", "meter": "perf", "durNs": 250_000}

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def run(command: list[str], trace_out: str | None, extra: dict[str, str] | None = None) -> tuple[bytes, str]:
    """Runs the probe; returns (stdout, stderr text)."""
    env = dict(os.environ)
    for name in (ENV, METER_ENV, FLUSH_ENV):
        env.pop(name, None)
    if trace_out is not None:
        env[ENV] = trace_out
    env.update(extra or {})
    result = subprocess.run(command, env=env, capture_output=True, timeout=120)
    if result.returncode != 0:
        sys.exit(f"check_trace_stream: {ENV}={trace_out!r}: exit {result.returncode}\n"
                 f"{result.stderr.decode('utf-8', 'replace')}")
    return result.stdout, result.stderr.decode("utf-8", "replace")


def check_stream(lines: list[str], summary: dict, meter: str = "wall") -> None:
    records = []
    for number, line in enumerate(lines, 1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            failures.append(f"line {number} is not JSON ({error}): {line[:120]}")
    if failures:
        return

    events = [r for r in records if r.get("kind") in EVENT_KEYS]
    spans = [r for r in records if r.get("kind") == "span"]
    diagrams = [r for r in records if r.get("kind") == "diagram"]
    check(len(events) + len(spans) + len(diagrams) == len(records), "stream holds a record of an unknown kind")
    check(all(r.get("v") == 1 for r in records), "a record without \"v\":1")

    check(len(events) == summary["events"], f"{len(events)} event lines, probe recorded {summary['events']}")
    for event in events:
        check(set(event) == EVENT_KEYS[event["kind"]], f"{event['kind']} keys {sorted(event)}")
        check(event["file"].endswith("trace_stream_probe.cpp"), f"file {event['file']!r}")
        check(isinstance(event["line"], int) and event["line"] > 0, f"line {event['line']!r}")
    seqs = [record["seq"] for record in events + spans]
    check(len(set(seqs)) == len(seqs), "duplicate seq values")
    check(all(isinstance(s, int) and s > 0 for s in seqs), "seq must be a positive integer")

    actions = {event["action"] for event in events if event["kind"] == "message"}
    for label in EXPECTED_LABELS:
        check(label in actions, f"label {label!r} did not round-trip")

    check(len(spans) == summary["spans"], f"{len(spans)} span lines, probe recorded {summary['spans']}")
    for span in spans:
        check(set(span) == SPAN_KEYS, f"span keys {sorted(span)}")
        check(span["file"].endswith("trace_stream_probe.cpp"), f"span file {span['file']!r}")
        check(isinstance(span["line"], int) and span["line"] > 0, f"span line {span['line']!r}")
        check(isinstance(span["durNs"], int) and span["durNs"] >= 0, f"span durNs {span['durNs']!r}")
        check(isinstance(span["thread"], int) and span["thread"] > 0, f"span thread {span['thread']!r}")
    scoped = [(s["label"], s["meter"]) for s in spans if s["label"] != PERF_SPAN["label"]]
    check(scoped == [(label, meter) for label in SCOPED_SPAN_LABELS],
          f"scoped spans {scoped}, expected labels {SCOPED_SPAN_LABELS} on meter {meter!r}")
    perf = [s for s in spans if s["label"] == PERF_SPAN["label"]]
    check(len(perf) == 1 and all(perf[0][k] == v for k, v in PERF_SPAN.items()), f"perf span {perf}")

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
        plain, plain_err = run(command, None)
        streamed, _ = run(command, str(trace))
        unopenable, _ = run(command, str(Path(tmp) / "missing_dir" / "trace.jsonl"))
        cpu_trace = Path(tmp) / "trace_cpu.jsonl"
        cpu, _ = run(command, str(cpu_trace), {METER_ENV: "cpu"})
        bogus_trace = Path(tmp) / "trace_bogus.jsonl"
        bogus, bogus_err = run(command, str(bogus_trace), {METER_ENV: "no-such-meter"})
        flush_trace = Path(tmp) / "trace_flush.jsonl"
        flushed, flushed_err = run(command, str(flush_trace), {FLUSH_ENV: "100"})
        bad_flush_trace = Path(tmp) / "trace_bad_flush.jsonl"
        bad_flush, bad_flush_err = run(command, str(bad_flush_trace), {FLUSH_ENV: "100ms"})

        check(plain == streamed, "stdout changes when the variable is set")
        check(plain == unopenable, "stdout changes when the trace file cannot be opened")
        for name, other in (("cpu", cpu), ("unknown meter", bogus), ("flush interval", flushed),
                            ("invalid flush interval", bad_flush)):
            check(plain == other, f"stdout changes with the {name} run")
        # The variables are read: a bad value is reported once on stderr, a good one silently.
        check("atugcc:" not in plain_err, f"unexpected stderr: {plain_err!r}")
        check(bogus_err.count("unknown ATUGCC_SPAN_METER 'no-such-meter'") == 1, f"unknown-meter stderr: {bogus_err!r}")
        check("atugcc:" not in flushed_err, f"unexpected stderr with {FLUSH_ENV}=100: {flushed_err!r}")
        check(bad_flush_err.count("invalid ATUGCC_TRACE_FLUSH_MS '100ms'") == 1, f"bad-flush stderr: {bad_flush_err!r}")
        check(not (Path(tmp) / "missing_dir").exists(), "a missing directory was created")
        check(trace.is_file(), "trace file was not written")

        summary = json.loads(plain.decode("utf-8"))
        if trace.is_file():
            lines = trace.read_text(encoding="utf-8").splitlines()
            check_stream(lines, summary)
            for path, meter in ((cpu_trace, "cpu"), (bogus_trace, "wall"), (flush_trace, "wall"),
                                (bad_flush_trace, "wall")):
                check(path.is_file(), f"{path.name} was not written")
                if path.is_file():
                    other = path.read_text(encoding="utf-8").splitlines()
                    check(len(other) == len(lines), f"{path.name}: {len(other)} lines, default run {len(lines)}")
                    check_stream(other, summary, meter)

    if failures:
        print("check_trace_stream: FAILED")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"check_trace_stream: OK ({summary['events']} events, {summary['spans']} spans, "
          f"{sum(n for kinds in summary['tracers'].values() for n in kinds.values())} diagram parts)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
