#!/usr/bin/env python3
"""Runs tests/core/crash_probe and checks what each way of ending leaves behind (spec 010-09).

Usage: check_crash_dump.py --probe <crash_probe> --work <dir> [--modes m1,m2,...] [--lines N] [-- launcher...]

  normal, exit, quickexit
                 AC-2, §2.4 row 1: app.log has every "P<k> L<i>" exactly once, in order within
                 each producer (destructor / atexit / at_quick_exit drain); cross-thread time
                 inversions are counted and printed
  segv, abort, terminate, stackoverflow
                 AC-3: the dump (read with tools/read_dump.py) has CRASH-MARKER, for every
                 producer a line at or after the one named in it, and the ended thread's last
                 line from a retired buffer;
                 AC-4: sync.log has "SYNC before crash"; terminate: app.log has CRASH-MARKER
  killme         AC-5: after READY the process is killed (SIGKILL / TerminateProcess); app.log
                 has "BEFORE KILL"

Exit 0 when every requested mode passes, 1 otherwise.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import read_dump  # noqa: E402

LINE_RE = re.compile(r"P([0-9]+) L([0-9]+)$")
# "YYYY-MM-DDTHH:MM:SS.uuuuuuZ T<n> " (file sink prefix, plan D3)
STAMP_RE = re.compile(r"^([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}[:][0-9]{2}[:][0-9]{2}[.][0-9]{6})Z T([0-9]+) ")
CRASH_MODES = ("segv", "abort", "terminate", "stackoverflow")


def fail(mode: str, msg: str) -> bool:
    print(f"FAIL {mode}: {msg}")
    return False


def check_normal(work: Path, lines: int, mode: str = "normal") -> bool:
    text = (work / "app.log").read_text(encoding="utf-8", errors="replace").splitlines()
    seen: dict[int, list[int]] = {}
    inversions = 0
    last_stamp = ""
    for line in text:
        m = STAMP_RE.match(line)
        if not m:
            return fail(mode, f"line without time prefix: {line[:80]}")
        if m.group(1) < last_stamp:
            inversions += 1
        last_stamp = max(last_stamp, m.group(1))
        p = LINE_RE.search(line)
        if p:
            seen.setdefault(int(p.group(1)), []).append(int(p.group(2)))
    for producer in range(8):
        got = seen.get(producer, [])
        if got != list(range(lines)):
            missing = sorted(set(range(lines)) - set(got))[:5]
            dup = len(got) - len(set(got))
            return fail(mode, f"P{producer}: {len(got)} lines, missing {missing}, duplicates {dup}, "
                                  f"in order {got == sorted(got)}")
    if not any(line.endswith(f"DONE {lines}") for line in text):
        return fail(mode, "DONE line missing")
    print(f"ok   {mode}: {8 * lines} lines once each, in producer order; cross-thread time inversions: {inversions}")
    return True


def dump_file(work: Path) -> Path | None:
    dumps = sorted(work.glob("crash_dump_*.log"))
    return dumps[-1] if dumps else None


def check_crash(work: Path, mode: str) -> bool:
    path = dump_file(work)
    if path is None or path.stat().st_size == 0:
        return fail(mode, "no crash dump written")
    dump = read_dump.parse(path.read_bytes())
    texts = [r.text for r in dump.records]
    marker = next((t for t in texts if "CRASH-MARKER" in t), None)
    if marker is None:
        return fail(mode, f"CRASH-MARKER not in the dump ({len(texts)} records)")
    for producer, last in re.findall(r" P([0-9]+)=([0-9]+)", marker):
        # Producers keep logging until the dump is written (the terminate handler first delivers
        # for up to 200 ms) and may overwrite delivered slots: a line of that producer at or after
        # the one named in CRASH-MARKER must be in the dump, which only a dump of that producer's
        # buffer can have.
        if not any(m and int(m.group(1)) == int(producer) and int(m.group(2)) >= int(last)
                   for m in (LINE_RE.search(t) for t in texts)):
            return fail(mode, f"no line P{producer} L>={last} (named in CRASH-MARKER) in the dump")
    retired_threads = {n for n, retired in dump.threads if retired}
    p9 = [r for r in dump.records if r.text.endswith("P9 L9")]
    if not p9:
        return fail(mode, "the ended thread's last line P9 L9 is not in the dump")
    if not any(r.thread_no in retired_threads for r in p9):
        return fail(mode, "P9 L9 is not from a retired (ended-thread) buffer")
    expected_types = ("terminate",) if mode == "terminate" else ("signal", "exception")
    if dump.fields.get("Event-Type") not in expected_types:
        return fail(mode, f"Event-Type {dump.fields.get('Event-Type')!r}, expected {expected_types}")
    sync = (work / "sync.log").read_text(encoding="utf-8", errors="replace") if (work / "sync.log").exists() else ""
    if "SYNC before crash" not in sync:
        return fail(mode, "sync.log lacks the Delivery::Sync line (AC-4)")
    if mode == "terminate":
        app = (work / "app.log").read_text(encoding="utf-8", errors="replace")
        if "CRASH-MARKER" not in app:
            return fail(mode, "terminate: CRASH-MARKER was not delivered to app.log within the emergency flush")
    undelivered = sum(1 for r in dump.records if not r.delivered)
    retired = len(retired_threads)
    print(f"ok   {mode}: dump has {len(texts)} records from {len(dump.threads)} buffers "
          f"({retired} retired, {undelivered} undelivered), Event-Type {dump.fields.get('Event-Type')}")
    return True


def run_killme(cmd: list[str], work: Path) -> bool:
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert proc.stdout is not None
        line = proc.stdout.readline()
        if line.strip() != "READY":
            proc.kill()
            return fail("killme", f"no READY line (got {line!r})")
        proc.kill()  # SIGKILL on POSIX, TerminateProcess on Windows
        proc.wait(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
    app = (work / "app.log").read_text(encoding="utf-8", errors="replace") if (work / "app.log").exists() else ""
    if "BEFORE KILL" not in app:
        return fail("killme", "BEFORE KILL (logged 50 ms before the kill) is not in app.log")
    print("ok   killme: the line logged 50 ms before the kill is in app.log")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", required=True)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--modes", default="normal,exit,quickexit," + ",".join(CRASH_MODES) + ",killme")
    parser.add_argument("--lines", type=int, default=100000)  # AC-2: 8 producers x 100,000
    parser.add_argument("launcher", nargs="*")
    args = parser.parse_args()
    ok = True
    for mode in [m for m in args.modes.split(",") if m]:
        work = args.work / mode
        cmd = [*args.launcher, args.probe, mode, str(work), str(args.lines)]
        if mode == "killme":
            ok = run_killme(cmd, work) and ok
            continue
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if mode in ("normal", "exit", "quickexit"):
            if proc.returncode != 0:
                ok = fail(mode, f"exit {proc.returncode}: {proc.stderr[-400:]}")
                continue
            ok = check_normal(work, args.lines, mode) and ok
        else:
            if proc.returncode == 0:
                ok = fail(mode, "the probe did not crash")
                continue
            ok = check_crash(work, mode) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
