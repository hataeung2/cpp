#!/usr/bin/env python3
"""Linux symbolizer for the project's crash dump format.

Usage: tools/symbolize_dump.py <dump-file> <exe-path>

Reads the dump produced by the Linux crash handler and runs `addr2line`
against the recorded instruction pointer. It expects the dump to contain
markers written by the handler:
  --CONTEXT-BINARY--\n  (followed by a 8-byte little-endian RIP)
  --MODULES--\n        (followed by 8-byte module base, then exe path + '\n')

This script prints the recorded IP, module base, and the addr2line output.
"""

from __future__ import annotations
import argparse
import subprocess
from pathlib import Path
import sys

CTX_MARKER = b"--CONTEXT-BINARY--\n"
MOD_MARKER = b"--MODULES--\n"


def read_u64_le(b: bytes) -> int:
    return int.from_bytes(b, "little")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("dump", type=Path)
    p.add_argument("exe", type=Path)
    args = p.parse_args(argv)

    if not args.dump.exists():
        print(f"Dump file not found: {args.dump}")
        return 2
    data = args.dump.read_bytes()

    ctx_idx = data.find(CTX_MARKER)
    if ctx_idx == -1:
        print("No context marker found in dump")
        return 3
    ip_off = ctx_idx + len(CTX_MARKER)
    if ip_off + 8 > len(data):
        print("Dump too short to contain IP")
        return 4
    ip = read_u64_le(data[ip_off:ip_off+8])

    mod_idx = data.find(MOD_MARKER)
    module_base = 0
    exe_path = str(args.exe)
    if mod_idx != -1:
        mb_off = mod_idx + len(MOD_MARKER)
        if mb_off + 8 <= len(data):
            module_base = read_u64_le(data[mb_off:mb_off+8])
            # exe path follows the 8 bytes and ends at newline
            name_off = mb_off + 8
            nl = data.find(b"\n", name_off)
            if nl != -1:
                exe_path = data[name_off:nl].decode("utf-8", errors="replace")

    print(f"Context IP: 0x{ip:016x}")
    if module_base:
        print(f"Recorded module base: 0x{module_base:016x}")
    print(f"Using exe: {exe_path}")

    # Compute relative address for PIE executables if module_base is present
    rel = ip
    if module_base:
        rel = ip - module_base
        print(f"Relative address: 0x{rel:016x}")

    # Call addr2line
    try:
        cmd = ["addr2line", "-e", exe_path, "-f", "-C", f"0x{rel:x}"]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        if out:
            print("Addr2line output:")
            print(out)
        if err:
            print("Addr2line stderr:")
            print(err)
    except FileNotFoundError:
        print("addr2line not found; install binutils and retry")
        return 5

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
