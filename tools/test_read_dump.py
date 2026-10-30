#!/usr/bin/env python3
"""Tests for tools/read_dump.py (spec 010-09 AC-12). Run: py -3 tools/test_read_dump.py

Dumps are built here byte by byte from the layout in plan D1 / D5, so the tests pin the
format the C++ writer must produce; the C++ side is checked against real dumps by
tests/core/check_crash_dump.py.
"""
from __future__ import annotations

import io
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import read_dump  # noqa: E402

SLOT_BYTES = 256
PAYLOAD = 232


def buffer_block(slot_count: int, thread_no: int, records: list[tuple[int, int, int, str]],
                 read_upto: int | None = None, retired: bool = False, start_pos: int = 0,
                 reserve_extra: int = 0) -> bytes:
    """records: (timeNs, threadSeq, level, text); written from start_pos like the producer would."""
    slots = bytearray(slot_count * SLOT_BYTES)
    pos = start_pos
    for time_ns, seq, level, text in records:
        data = text.encode("utf-8")
        chunks = [data[i:i + PAYLOAD] for i in range(0, len(data), PAYLOAD)] or [b""]
        for k, chunk in enumerate(chunks):
            flags = (1 if k == 0 else 0) | (2 if k == len(chunks) - 1 else 0)
            off = (pos & (slot_count - 1)) * SLOT_BYTES
            slots[off:off + 24] = struct.pack("<QIHBBHHI", time_ns, seq, 7, level, flags, len(chunk), 0, 0)
            slots[off + 24:off + 24 + len(chunk)] = chunk
            pos += 1
    read_pos = pos if read_upto is None else read_upto
    reserve = pos + reserve_extra
    header = struct.pack("<8sIIIIQQQ16x", b"ATGLBUF1", slot_count, SLOT_BYTES, thread_no, 1 if retired else 0,
                         pos, read_pos, reserve)
    return header + bytes(slots)


def dump_bytes(blocks: list[bytes], end: bool = True) -> bytes:
    head = (b"DUMP-V2\nPID: 42\nEvent-Type: signal\nEvent-Code: 11\nCrash-Thread: 2\n"
            b"Clock-Base: 1700000000000000000 1000\n"
            b"--CONTEXT-BINARY--\n" + struct.pack("<Q", 0x1234) +
            b"--MODULES--\n" + struct.pack("<Q", 0x1000) + b"/bin/app\n--THREADS--\n")
    body = b"".join(b"--THREAD--\n" + b for b in blocks)
    return head + body + (b"--END--\n" if end else b"")


class ReadDumpTest(unittest.TestCase):
    def test_merges_threads_by_time(self) -> None:
        a = buffer_block(64, 1, [(1000, 0, 1, "a0"), (3000, 1, 1, "a1")])
        b = buffer_block(64, 2, [(2000, 0, 3, "b0")])
        d = read_dump.parse(dump_bytes([a, b]))
        self.assertEqual([r.text for r in d.records], ["a0", "b0", "a1"])
        self.assertEqual(d.fields["Event-Code"], "11")
        self.assertFalse(d.truncated)

    def test_ties_break_by_thread_then_seq(self) -> None:
        a = buffer_block(64, 2, [(5, 0, 1, "t2")])
        b = buffer_block(64, 1, [(5, 0, 1, "t1")])
        d = read_dump.parse(dump_bytes([a, b]))
        self.assertEqual([r.text for r in d.records], ["t1", "t2"])

    def test_multi_slot_record_is_joined(self) -> None:
        long = "x" * 500 + "END"
        d = read_dump.parse(dump_bytes([buffer_block(64, 1, [(1, 0, 1, long)])]))
        self.assertEqual(len(d.records), 1)
        self.assertEqual(d.records[0].text, long)

    def test_delivered_flag_follows_read_pos(self) -> None:
        block = buffer_block(64, 1, [(1, 0, 1, "old"), (2, 1, 1, "new")], read_upto=1)
        d = read_dump.parse(dump_bytes([block]))
        self.assertEqual([(r.text, r.delivered) for r in d.records], [("old", True), ("new", False)])

    def test_wrapped_buffer_keeps_newest_and_skips_partial_record(self) -> None:
        # 64 slots, 70 single-slot records written, nothing in progress: the newest 64 positions.
        recs = [(i, i, 1, f"r{i}") for i in range(70)]
        d = read_dump.parse(dump_bytes([buffer_block(64, 1, recs)]))
        self.assertEqual(d.records[0].text, "r6")
        self.assertEqual(d.records[-1].text, "r69")
        self.assertEqual(len(d.records), 64)
        # a 3-slot record in progress (reservePos = writePos + 3) overwrites positions 6..8:
        # those are not trusted
        d3 = read_dump.parse(dump_bytes([buffer_block(64, 1, recs, reserve_extra=3)]))
        self.assertEqual(d3.records[0].text, "r9")
        self.assertEqual(len(d3.records), 61)
        # a record whose first slot fell out of the valid range is skipped, not shown half
        long = "y" * 300  # two slots
        recs2 = [(0, 0, 1, long)] + [(i, i, 1, f"s{i}") for i in range(1, 64)]
        d2 = read_dump.parse(dump_bytes([buffer_block(64, 1, recs2)]))
        self.assertNotIn(long, [r.text for r in d2.records])
        self.assertTrue(all(r.text.startswith("s") for r in d2.records))

    def test_retired_thread_and_truncated_dump(self) -> None:
        a = buffer_block(64, 1, [(1, 0, 1, "a")], retired=True)
        b = buffer_block(64, 2, [(2, 0, 1, "b")])
        data = dump_bytes([a, b], end=False)
        cut = data[: len(data) - 100]  # second block cut short
        d = read_dump.parse(cut)
        self.assertEqual(d.threads[0], (1, True))
        self.assertTrue(d.truncated)
        self.assertIn("a", [r.text for r in d.records])

    def test_render_marks_undelivered_and_wall_time(self) -> None:
        block = buffer_block(64, 3, [(1000, 0, 2, "seen"), (1000 + 1_500_000, 1, 3, "lost")], read_upto=1)
        d = read_dump.parse(dump_bytes([block]))
        lines = read_dump.render(d, undelivered_only=False)
        body = [line for line in lines if not line.startswith("#")]
        self.assertTrue(body[0].startswith("2023-11-14T22:13:20.000000Z T3 WARN  delivered"))
        self.assertTrue(body[1].endswith(" T3 ERROR UNDELIVERED lost"), body[1])
        only = [line for line in read_dump.render(d, undelivered_only=True) if not line.startswith("#")]
        self.assertEqual(len(only), 1)
        self.assertTrue(only[0].endswith("lost"))
        self.assertIn("2023-11-14T22:13:20.001500Z", only[0])

    def test_cli_rejects_other_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "x.log"
            bad.write_bytes(b"DUMP-V1\nnot this one\n")
            self.assertEqual(read_dump.main([str(bad)]), 2)
            good = Path(tmp) / "d.log"
            good.write_bytes(dump_bytes([buffer_block(64, 1, [(1, 0, 1, "hello")])]))
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(read_dump.main([str(good)]), 0)
            self.assertIn("hello", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
