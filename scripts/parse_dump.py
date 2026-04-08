#!/usr/bin/env python3
"""Simple parser for the project's crash dump format.

Usage: scripts/parse_dump.py <dump-file> [--block-size N] [--show N]

Parses the UTF-8 header (Key: Value lines) and then splits the remainder
into fixed-size binary blocks (default 128 bytes). For each sample block
it prints the embedded ring-buffer header (level/cont/len) and a payload
preview.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Tuple


def parse_header_and_split(data: bytes) -> Tuple[str, bytes]:
    # Accept either CRLF or LF header terminator.
    sep = b"\r\n\r\n"
    idx = data.find(sep)
    if idx == -1:
        sep = b"\n\n"
        idx = data.find(sep)
    if idx == -1:
        raise ValueError("Could not find header/body separator (empty line)")
    header = data[:idx].decode("utf-8", errors="replace")
    body = data[idx + len(sep):]
    return header, body


def strip_marker(body: bytes) -> bytes:
    marker = b"--BINARY-BLOCKS--"
    if body.startswith(marker):
        # skip marker line and following newline(s)
        rest = body[len(marker):]
        if rest.startswith(b"\r\n"):
            return rest[2:]
        if rest.startswith(b"\n"):
            return rest[1:]
        return rest
    return body


def is_printable(bs: bytes) -> bool:
    try:
        s = bs.decode("utf-8")
    except Exception:
        return False
    return all((0x20 <= ord(c) <= 0x7E) or c in "\t\n\r" for c in s)


def inspect_block(block: bytes) -> Tuple[int, bool, int, bytes]:
    # Block layout: first 2 bytes = header (uint16 little-endian)
    if len(block) < 2:
        return (0, False, 0, b"")
    hdr = int.from_bytes(block[0:2], "little")
    level = (hdr & 0xC000) >> 14
    cont = bool(hdr & 0x2000)
    length = hdr & 0x1FFF
    payload = block[2:2+length]
    return level, cont, length, payload


def main(argv=None):
    p = argparse.ArgumentParser(prog="parse_dump.py")
    p.add_argument("file", type=Path)
    p.add_argument("--block-size", type=int, default=128)
    p.add_argument("--show", type=int, default=5, help="how many blocks to show samples for")
    args = p.parse_args(argv)

    if not args.file.exists():
        print(f"File not found: {args.file}")
        return 2

    data = args.file.read_bytes()
    try:
        header_text, body = parse_header_and_split(data)
    except ValueError as e:
        print(f"Error parsing header: {e}")
        return 3

    print("--- Header ---")
    print(header_text)
    print("--- End Header ---\n")

    body = strip_marker(body)

    bs = args.block_size
    if bs <= 0:
        print("Invalid block size")
        return 4

    full_blocks = len(body) // bs
    rem = len(body) % bs
    print(f"Binary section: {len(body)} bytes, block size={bs}, full_blocks={full_blocks}, remainder={rem}")

    if full_blocks == 0:
        print("No blocks found")
        return 0

    to_show = min(args.show, full_blocks)
    print(f"Showing first {to_show} blocks:\n")
    for i in range(to_show):
        block = body[i*bs:(i+1)*bs]
        level, cont, length, payload = inspect_block(block)
        print(f"Block {i}: level={level} cont={cont} len={length}")
        if length == 0:
            print("  (empty payload)")
            continue
        if is_printable(payload):
            txt = payload.decode("utf-8", errors="replace")
            print(f"  payload(text): {txt!r}")
        else:
            # show up to 32 bytes hex
            sample = payload[:32]
            print(f"  payload(hex, first {len(sample)} bytes): {sample.hex()}\n")

    if rem:
        print(f"Warning: {rem} trailing bytes ignored (not a full block)")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
