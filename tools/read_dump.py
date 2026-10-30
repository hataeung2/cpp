#!/usr/bin/env python3
"""Turn an atugcc crash dump (DUMP-V2, spec 010-09) or log map (ATGLMAP1, spec 010-10) into time-ordered text.

Usage: py -3 tools/read_dump.py <dump-or-map-file> [--undelivered]

Every thread's buffer in the dump or log map arena is decoded, the records are merged by their
steady-clock time (then thread number, then the thread's record number) and printed as

    2026-10-30T12:00:00.123456Z T3 INFO  delivered    [INFO] [main.cpp:12 main] text

"delivered" means the log thread had already passed the record to the Logger's sinks
(history, live output, file) before the crash; "UNDELIVERED" records may exist only in
the dump or map. `--undelivered` prints only those, for either format. Exit 0 on success,
2 when the file is not a DUMP-V2 dump or ATGLMAP1 log map (or fails header validation).
A dump cut short by a crash inside the handler is read as far as it goes; a corrupt map
buffer skips to the next 64-byte aligned valid buffer.

Layout: plan D1 and D5 of task 010-09 (docs/tasks/feature_010-09-logger-thread-buffers/plan.md)
and plan D2 and D7 of task 010-10 (docs/tasks/feature_010-10-logger-mapped-buffers/plan.md).
"""
from __future__ import annotations

import argparse
import datetime as dt
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

MAGIC = b"DUMP-V2\n"
THREADS = b"--THREADS--\n"
THREAD = b"--THREAD--\n"
END = b"--END--\n"
BUFFER_MAGIC = b"ATGLBUF1"
BUFFER_HEADER = struct.Struct("<8sIIIIQQQ16x")  # 64 bytes
SLOT_HEADER = struct.Struct("<QIHBBHHI")        # 24 bytes
FLAG_FIRST = 0x1
FLAG_LAST = 0x2
FLAG_RETIRED = 0x1
LEVELS = {0: "DEBUG", 1: "INFO", 2: "WARN", 3: "ERROR"}

MAP_MAGIC = b"ATGLMAP1"
MAP_VERSION = 1
ARENA_OFFSET = 36864
LABEL_TABLE_OFFSET = 4096
LABEL_COUNT = 256
LABEL_BYTES = 128
LABEL_TEXT_BYTES = 124
PAYLOAD_BYTES = 232
FLAG_MAP_CRASH = 0x1
FLAG_MAP_CLEAN_EXIT = 0x2
MAP_HEADER = struct.Struct("<8sIIQIIQQqQII56x")  # 128 bytes
LABEL_ENTRY = struct.Struct("<HH124s")           # 128 bytes


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
    labels: list[str] = field(default_factory=list)


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
    magic, slot_count, slot_bytes, thread_no, flags, write_pos, read_pos, reserve_pos = BUFFER_HEADER.unpack_from(block, 0)
    if magic != BUFFER_MAGIC or slot_count == 0 or slot_count & (slot_count - 1) or slot_bytes < SLOT_HEADER.size:
        raise NotADump("bad thread buffer header")
    slots_available = (len(block) - BUFFER_HEADER.size) // slot_bytes
    complete = slots_available >= slot_count
    records: list[Record] = []
    parts: list[bytes] = []
    head: tuple[int, int, int, int] | None = None  # time, seq, logger, level
    # slots below reservePos - slotCount may be mid-overwrite by the record in progress (plan D1)
    for pos in range(max(0, max(reserve_pos, write_pos) - slot_count), write_pos):
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


def parse_dump(data: bytes) -> Dump:
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


def parse_labels(data: bytes) -> list[str]:
    labels = ["dbgbuf"]
    for i in range(1, LABEL_COUNT):
        offset = LABEL_TABLE_OFFSET + i * LABEL_BYTES
        entry_id, length, raw_text = LABEL_ENTRY.unpack_from(data, offset)
        if entry_id == i and 0 < length <= LABEL_TEXT_BYTES:
            labels.append(raw_text[:length].decode("utf-8", errors="replace"))
        else:
            labels.append(f"logger#{i}")
    return labels


def is_valid_buffer_header(data: bytes, offset: int, end: int, file_size: int) -> tuple[bool, int, tuple]:
    if offset + BUFFER_HEADER.size > end or offset + BUFFER_HEADER.size > file_size:
        return False, 0, ()
    unpacked = BUFFER_HEADER.unpack_from(data, offset)
    magic, slot_count, slot_bytes, thread_no, flags, write_pos, read_pos, reserve_pos = unpacked
    if magic != BUFFER_MAGIC:
        return False, 0, ()
    if slot_bytes != 256:
        return False, 0, ()
    if slot_count < 64 or slot_count > 65536 or (slot_count & (slot_count - 1)) != 0:
        return False, 0, ()
    block_size = BUFFER_HEADER.size + slot_count * slot_bytes
    if offset + block_size > end or offset + block_size > file_size:
        return False, 0, ()
    if read_pos > write_pos or write_pos > reserve_pos:
        return False, 0, ()
    if write_pos - read_pos > slot_count:
        return False, 0, ()
    return True, block_size, unpacked


def decode_map_buffer(data: bytes, buf_offset: int, slot_count: int, slot_bytes: int,
                      thread_no: int, flags: int, write_pos: int, read_pos: int,
                      reserve_pos: int) -> tuple[int, bool, list[Record]]:
    file_size = len(data)
    max_reserve_write = max(reserve_pos, write_pos)
    start_pos = max(0, max_reserve_write - slot_count)
    end_pos = write_pos
    if start_pos >= end_pos:
        return thread_no, bool(flags & FLAG_RETIRED), []

    mask = slot_count - 1
    max_slots_per_record = slot_count // 2
    records: list[Record] = []

    pos = start_pos
    while pos < end_pos:
        first_idx = pos & mask
        first_slot_offset = buf_offset + BUFFER_HEADER.size + first_idx * slot_bytes
        if first_slot_offset + slot_bytes > file_size:
            pos += 1
            continue

        f_time_ns, f_seq, f_logger_id, f_level, f_flags, f_len, _, _ = SLOT_HEADER.unpack_from(data, first_slot_offset)
        if not (f_flags & FLAG_FIRST) or f_len > PAYLOAD_BYTES:
            pos += 1
            continue

        complete = False
        record_end = pos
        max_check_end = min(end_pos, pos + max_slots_per_record)

        for cur in range(pos, max_check_end):
            cur_idx = cur & mask
            cur_slot_offset = buf_offset + BUFFER_HEADER.size + cur_idx * slot_bytes
            if cur_slot_offset + slot_bytes > file_size:
                break
            c_time_ns, c_seq, c_logger_id, c_level, c_flags, c_len, _, _ = SLOT_HEADER.unpack_from(data, cur_slot_offset)
            if c_len > PAYLOAD_BYTES:
                break
            if cur > pos:
                if (c_flags & FLAG_FIRST) or c_time_ns != f_time_ns or c_seq != f_seq or c_logger_id != f_logger_id:
                    break
            if c_flags & FLAG_LAST:
                complete = True
                record_end = cur
                break

        if not complete:
            pos += 1
            continue

        parts: list[bytes] = []
        for cur in range(pos, record_end + 1):
            cur_idx = cur & mask
            cur_slot_offset = buf_offset + BUFFER_HEADER.size + cur_idx * slot_bytes
            _, _, _, _, _, c_len, _, _ = SLOT_HEADER.unpack_from(data, cur_slot_offset)
            chunk_len = min(c_len, PAYLOAD_BYTES)
            payload_offset = cur_slot_offset + SLOT_HEADER.size
            if chunk_len > 0 and payload_offset + chunk_len <= file_size:
                parts.append(data[payload_offset:payload_offset + chunk_len])

        raw_text = b"".join(parts).decode("utf-8", errors="replace")
        clean_text = raw_text.replace("\r", " ").replace("\n", " ")
        delivered = (record_end < read_pos)
        records.append(Record(
            time_ns=f_time_ns,
            thread_no=thread_no,
            thread_seq=f_seq,
            logger_id=f_logger_id,
            level=f_level,
            delivered=delivered,
            text=clean_text
        ))
        pos = record_end + 1

    return thread_no, bool(flags & FLAG_RETIRED), records


def parse_map(data: bytes) -> Dump:
    if len(data) < ARENA_OFFSET:
        raise NotADump("file too small for log map header")
    magic, version, arena_offset, file_bytes, pid, flags, start_system_ns, steady_base_ns, system_base_ns, arena_used, label_count, label_bytes = MAP_HEADER.unpack_from(data, 0)
    if magic != MAP_MAGIC:
        raise NotADump("bad log map magic")
    if version != MAP_VERSION:
        raise NotADump(f"unsupported log map version {version}")
    if arena_offset != ARENA_OFFSET:
        raise NotADump(f"unexpected arena offset {arena_offset}")
    if file_bytes != len(data):
        raise NotADump(f"log map fileBytes {file_bytes} != size {len(data)}")
    if label_count != LABEL_COUNT:
        raise NotADump(f"unexpected label count {label_count}")
    if label_bytes != LABEL_BYTES:
        raise NotADump(f"unexpected label bytes {label_bytes}")

    labels = parse_labels(data)

    file_size = len(data)
    end = arena_used if (ARENA_OFFSET <= arena_used <= file_size) else file_size
    offset = ARENA_OFFSET
    skipped_buffers = 0
    records: list[Record] = []
    threads: list[tuple[int, bool]] = []

    while offset < end:
        valid, block_size, hdr = is_valid_buffer_header(data, offset, end, file_size)
        if valid:
            _b_magic, slot_count, slot_bytes, thread_no, b_flags, write_pos, read_pos, reserve_pos = hdr
            t_no, retired, recs = decode_map_buffer(data, offset, slot_count, slot_bytes,
                                                    thread_no, b_flags, write_pos, read_pos, reserve_pos)
            threads.append((t_no, retired))
            records.extend(recs)
            offset += block_size
        else:
            skipped_buffers += 1
            offset += 64
            while offset < end:
                valid_next, _, _ = is_valid_buffer_header(data, offset, end, file_size)
                if valid_next:
                    break
                offset += 64

    records.sort(key=lambda r: (r.time_ns, r.thread_no, r.thread_seq))
    fields: dict[str, str] = {
        "Clock-Base": f"{system_base_ns} {steady_base_ns}",
    }
    if pid != 0:
        fields["PID"] = str(pid)

    truncated = bool(skipped_buffers)
    return Dump(fields=fields, records=records, threads=threads, truncated=truncated, labels=labels)


def parse(data: bytes) -> Dump:
    if data.startswith(MAGIC):
        return parse_dump(data)
    if data.startswith(MAP_MAGIC):
        return parse_map(data)
    raise NotADump("not a DUMP-V2 file or log map")


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
    try:
        print("\n".join(render(dump, args.undelivered)))
        sys.stdout.flush()
    except BrokenPipeError:  # e.g. `| head`: the reader stopped, which is not an error
        sys.stdout = None  # type: ignore[assignment]  # no flush at interpreter exit
    return 0


if __name__ == "__main__":
    sys.exit(main())
