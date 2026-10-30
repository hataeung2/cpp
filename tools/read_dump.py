#!/usr/bin/env python3
"""Turn an atugcc crash dump (DUMP-V2, spec 010-09) into time-ordered text.

Usage: py -3 tools/read_dump.py <dump-file> [--undelivered]

Every thread's buffer in the dump is decoded, the records are merged by their
steady-clock time (then thread number, then the thread's record number) and printed as

    2026-10-30T12:00:00.123456Z T3 INFO  delivered    [INFO] [main.cpp:12 main] text

"delivered" means the log thread had already passed the record to the Logger's sinks
(history, live output, file) before the crash; "UNDELIVERED" records may exist only in
the dump. `--undelivered` prints only those. Exit 0 on success, 2 when the file is not a
DUMP-V2 dump. A dump cut short by a crash inside the handler is read as far as it goes.

Layout: plan D1 and D5 of task 010-09 (docs/tasks/feature_010-09-logger-thread-buffers/plan.md).
"""
from __future__ import annotations

import argparse
import datetime as dt
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"DUMP-V2\n"
THREADS = b"--THREADS--\n"
THREAD = b"--THREAD--\n"
END = b"--END--\n"
BUFFER_MAGIC = b"ATGLBUF1"
BUFFER_HEADER = struct.Struct("<8sIIIIQQ24x")   # 64 bytes
SLOT_HEADER = struct.Struct("<QIHBBHHI")        # 24 bytes
FLAG_FIRST = 0x1
FLAG_LAST = 0x2
FLAG_RETIRED = 0x1
LEVELS = {0: "DEBUG", 1: "INFO", 2: "WARN", 3: "ERROR"}


@dataclass
class Record:
    time_ns: int
    thread_no: int
    thread_seq: int
    logger_id: int
    level: int
    delivered: bool
    text: str


@dataclass
class Dump:
    fields: dict[str, str]
    records: list[Record]
    threads: list[tuple[int, bool]]  # (threadNo, retired)
    truncated: bool


class NotADump(ValueError):
    pass


def parse_fields(data: bytes, end: int) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw in data[len(MAGIC):end].split(b"\n"):
        line = raw.decode("utf-8", errors="replace")
        if line.startswith("--"):
            break
        if ": " in line:
            key, value = line.split(": ", 1)
            fields[key] = value
    return fields


def decode_buffer(block: bytes) -> tuple[int, bool, list[Record], bool]:
    """Records of one raw buffer block. Returns (threadNo, retired, records, complete)."""
    magic, slot_count, slot_bytes, thread_no, flags, write_pos, read_pos = BUFFER_HEADER.unpack_from(block, 0)
    if magic != BUFFER_MAGIC or slot_count == 0 or slot_count & (slot_count - 1) or slot_bytes < SLOT_HEADER.size:
        raise NotADump("bad thread buffer header")
    slots_available = (len(block) - BUFFER_HEADER.size) // slot_bytes
    complete = slots_available >= slot_count
    records: list[Record] = []
    parts: list[bytes] = []
    head: tuple[int, int, int, int] | None = None  # time, seq, logger, level
    for pos in range(max(0, write_pos - slot_count + 1), write_pos):
        index = pos & (slot_count - 1)
        if index >= slots_available:
            continue
        offset = BUFFER_HEADER.size + index * slot_bytes
        time_ns, seq, logger_id, level, slot_flags, length, _r0, _r1 = SLOT_HEADER.unpack_from(block, offset)
        payload = block[offset + SLOT_HEADER.size: offset + SLOT_HEADER.size + length]
        if slot_flags & FLAG_FIRST:
            parts = [payload]
            head = (time_ns, seq, logger_id, level)
        elif head is not None:
            parts.append(payload)
        else:
            continue  # continuation whose first slot was already overwritten
        if slot_flags & FLAG_LAST and head is not None:
            records.append(Record(head[0], thread_no, head[1], head[2], head[3], pos < read_pos,
                                  b"".join(parts).decode("utf-8", errors="replace")))
            head = None
            parts = []
    return thread_no, bool(flags & FLAG_RETIRED), records, complete


def parse(data: bytes) -> Dump:
    if not data.startswith(MAGIC):
        raise NotADump("not a DUMP-V2 file")
    start = data.find(THREADS)
    fields = parse_fields(data, start if start != -1 else len(data))
    records: list[Record] = []
    threads: list[tuple[int, bool]] = []
    truncated = start == -1
    pos = start + len(THREADS) if start != -1 else len(data)
    while pos < len(data):
        if data.startswith(END, pos):
            break
        if not data.startswith(THREAD, pos):
            truncated = True
            break
        pos += len(THREAD)
        if pos + BUFFER_HEADER.size > len(data):
            truncated = True
            break
        _magic, slot_count, slot_bytes, *_rest = BUFFER_HEADER.unpack_from(data, pos)
        size = BUFFER_HEADER.size + slot_count * slot_bytes
        block = data[pos: pos + size]
        thread_no, retired, recs, complete = decode_buffer(block)
        threads.append((thread_no, retired))
        records.extend(recs)
        if not complete:
            truncated = True
            break
        pos += size
    else:
        truncated = truncated or start != -1
    records.sort(key=lambda r: (r.time_ns, r.thread_no, r.thread_seq))
    return Dump(fields, records, threads, truncated)


def wall_time(fields: dict[str, str], time_ns: int) -> str:
    try:
        system_ns, steady_ns = (int(x) for x in fields["Clock-Base"].split())
    except (KeyError, ValueError):
        return f"steady+{time_ns}ns"
    ns = system_ns + (time_ns - steady_ns)
    stamp = dt.datetime.fromtimestamp(ns // 1_000_000_000, tz=dt.timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S") + f".{(ns % 1_000_000_000) // 1000:06d}Z"


def render(dump: Dump, undelivered_only: bool) -> list[str]:
    out = [f"# {key}: {dump.fields[key]}" for key in ("Event-Type", "Event-Code", "Crash-Thread", "PID")
           if key in dump.fields]
    out.append("# threads: " + ", ".join(f"T{n}{' (ended)' if retired else ''}" for n, retired in dump.threads))
    if dump.truncated:
        out.append("# warning: the dump ends early; later threads are missing")
    for r in dump.records:
        if undelivered_only and r.delivered:
            continue
        state = "delivered  " if r.delivered else "UNDELIVERED"
        out.append(f"{wall_time(dump.fields, r.time_ns)} T{r.thread_no} {LEVELS.get(r.level, '?'):5} {state} {r.text}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dump", type=Path)
    parser.add_argument("--undelivered", action="store_true", help="only records the sinks may not have")
    args = parser.parse_args(argv)
    try:
        dump = parse(args.dump.read_bytes())
    except NotADump as exc:
        print(f"read_dump: {args.dump}: {exc}", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(render(dump, args.undelivered)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
