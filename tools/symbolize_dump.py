#!/usr/bin/env python3
"""Cross-platform symbolizer for the project's crash dump format.

Usage: tools/symbolize_dump.py <dump-file> <exe-path>

On Linux/macOS this uses `addr2line` (binutils) to map recorded IP → symbol
and source line. On Windows it uses DbgHelp via ctypes to load the module
and resolve symbols (PDB required on the same machine).

The dump format (written by the crash handler) includes markers:
  --CONTEXT-BINARY--\n  (followed by an 8-byte little-endian IP)
  --MODULES--\n        (followed by an 8-byte module base, then exe path + '\n')
"""

from __future__ import annotations
import argparse
import subprocess
from pathlib import Path
import sys
import platform

CTX_MARKER = b"--CONTEXT-BINARY--\n"
MOD_MARKER = b"--MODULES--\n"


def read_u64_le(b: bytes) -> int:
    return int.from_bytes(b, "little")


def symbolize_unix(dump_path: Path, exe_path: Path) -> int:
    data = dump_path.read_bytes()
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
    exe = str(exe_path)
    if mod_idx != -1:
        mb_off = mod_idx + len(MOD_MARKER)
        if mb_off + 8 <= len(data):
            module_base = read_u64_le(data[mb_off:mb_off+8])
            name_off = mb_off + 8
            nl = data.find(b"\n", name_off)
            if nl != -1:
                exe = data[name_off:nl].decode("utf-8", errors="replace")

    print(f"Context IP: 0x{ip:016x}")
    if module_base:
        print(f"Recorded module base: 0x{module_base:016x}")
    print(f"Using exe: {exe}")

    rel = ip
    if module_base:
        rel = ip - module_base
        print(f"Relative address: 0x{rel:016x}")

    try:
        cmd = ["addr2line", "-e", exe, "-f", "-C", f"0x{rel:x}"]
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


def symbolize_windows(dump_path: Path, exe_path: Path) -> int:
    import ctypes
    from ctypes import wintypes

    data = dump_path.read_bytes()
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
    exe = str(exe_path)
    if mod_idx != -1:
        mb_off = mod_idx + len(MOD_MARKER)
        if mb_off + 8 <= len(data):
            module_base = read_u64_le(data[mb_off:mb_off+8])
            name_off = mb_off + 8
            nl = data.find(b"\n", name_off)
            if nl != -1:
                exe = data[name_off:nl].decode("utf-8", errors="replace")

    print(f"Context IP: 0x{ip:016x}")
    if module_base:
        print(f"Recorded module base: 0x{module_base:016x}")
    print(f"Using exe: {exe}")

    # Load dbghelp and prepare symbol API bindings
    dbghelp = ctypes.WinDLL("DbgHelp.dll")
    kernel32 = ctypes.WinDLL("Kernel32.dll")
    hProc = kernel32.GetCurrentProcess()

    # Setup prototypes
    SymInitialize = dbghelp.SymInitializeW
    SymInitialize.argtypes = [wintypes.HANDLE, ctypes.c_wchar_p, wintypes.BOOL]
    SymInitialize.restype = wintypes.BOOL

    SymSetOptions = dbghelp.SymSetOptions
    SymSetOptions.argtypes = [wintypes.DWORD]
    SymSetOptions.restype = wintypes.DWORD

    SymLoadModuleExW = dbghelp.SymLoadModuleExW
    SymLoadModuleExW.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_ulonglong, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    SymLoadModuleExW.restype = ctypes.c_ulonglong

    SymFromAddr = dbghelp.SymFromAddr
    SymFromAddr.argtypes = [wintypes.HANDLE, ctypes.c_ulonglong, ctypes.POINTER(ctypes.c_ulonglong), ctypes.c_void_p]
    SymFromAddr.restype = wintypes.BOOL

    SymGetLineFromAddr64 = dbghelp.SymGetLineFromAddr64
    SymGetLineFromAddr64.argtypes = [wintypes.HANDLE, ctypes.c_ulonglong, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    SymGetLineFromAddr64.restype = wintypes.BOOL

    SymCleanup = dbghelp.SymCleanup
    SymCleanup.argtypes = [wintypes.HANDLE]
    SymCleanup.restype = wintypes.BOOL

    # Initialize symbol handler
    ok = SymInitialize(hProc, None, True)
    if not ok:
        err = kernel32.GetLastError()
        print(f"SymInitialize failed: {err}")

    SYMOPT_LOAD_LINES = 0x00000010
    SYMOPT_UNDNAME = 0x00000002
    SymSetOptions(SYMOPT_LOAD_LINES | SYMOPT_UNDNAME)

    load_base = ctypes.c_ulonglong(module_base if module_base else 0)
    try:
        base = SymLoadModuleExW(hProc, None, exe, None, load_base.value, 0, None, 0)
    except Exception as e:
        base = 0
        print(f"SymLoadModuleExW exception: {e}")

    print(f"SymLoadModuleEx returned base: {hex(base) if base else 0}")

    # SYMBOL_INFO (variable size) — allocate buffer
    class SYMBOL_INFO(ctypes.Structure):
        _fields_ = [
            ("SizeOfStruct", ctypes.c_ulong),
            ("TypeIndex", ctypes.c_ulong),
            ("Reserved", ctypes.c_ulonglong * 2),
            ("Index", ctypes.c_ulong),
            ("Size", ctypes.c_ulong),
            ("ModBase", ctypes.c_ulonglong),
            ("Flags", ctypes.c_ulong),
            ("Value", ctypes.c_ulonglong),
            ("Address", ctypes.c_ulonglong),
            ("Register", ctypes.c_ulong),
            ("Scope", ctypes.c_ulong),
            ("Tag", ctypes.c_ulong),
            ("NameLen", ctypes.c_ulong),
            ("MaxNameLen", ctypes.c_ulong),
            ("Name", ctypes.c_char * 1),
        ]

    MAX_NAME = 1024
    buf_size = ctypes.sizeof(SYMBOL_INFO) + MAX_NAME
    sym_buf = ctypes.create_string_buffer(buf_size)
    pSym = ctypes.cast(sym_buf, ctypes.POINTER(SYMBOL_INFO))
    pSym.contents.SizeOfStruct = ctypes.sizeof(SYMBOL_INFO)
    pSym.contents.MaxNameLen = MAX_NAME

    displacement = ctypes.c_ulonglong(0)
    success = SymFromAddr(hProc, ctypes.c_ulonglong(ip), ctypes.byref(displacement), ctypes.byref(pSym.contents))
    if success:
        # extract name from buffer after the fixed struct
        raw = sym_buf.raw
        name_bytes = raw[ctypes.sizeof(SYMBOL_INFO):].split(b"\x00", 1)[0]
        try:
            name = name_bytes.decode("utf-8", errors="replace")
        except Exception:
            name = str(name_bytes)
        print(f"Symbol: {name} + 0x{displacement.value:x}")
    else:
        err = kernel32.GetLastError()
        print(f"SymFromAddr failed: {err}")

    # Try to get source line
    class IMAGEHLP_LINE64(ctypes.Structure):
        _fields_ = [
            ("SizeOfStruct", ctypes.c_ulong),
            ("Key", ctypes.c_void_p),
            ("LineNumber", ctypes.c_ulong),
            ("FileName", ctypes.c_char_p),
            ("Address", ctypes.c_ulonglong),
        ]

    line = IMAGEHLP_LINE64()
    line.SizeOfStruct = ctypes.sizeof(IMAGEHLP_LINE64)
    dwDisp = wintypes.DWORD(0)
    gotline = SymGetLineFromAddr64(hProc, ctypes.c_ulonglong(ip), ctypes.byref(dwDisp), ctypes.byref(line))
    if gotline:
        fname = line.FileName.decode("utf-8", errors="replace") if line.FileName else ""
        print(f"Source: {fname}:{line.LineNumber}")
    else:
        err = kernel32.GetLastError()
        print(f"SymGetLineFromAddr64 failed: {err}")

    SymCleanup(hProc)
    return 0


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("dump", type=Path)
    p.add_argument("exe", type=Path)
    args = p.parse_args(argv)

    if not args.dump.exists():
        print(f"Dump file not found: {args.dump}")
        return 2

    system = platform.system()
    if system == "Windows":
        return symbolize_windows(args.dump, args.exe)
    else:
        return symbolize_unix(args.dump, args.exe)


if __name__ == '__main__':
    raise SystemExit(main())
