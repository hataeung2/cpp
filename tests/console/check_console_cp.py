#!/usr/bin/env python3
"""Checks that lessons switch a cp949 console to UTF-8 and restore it (spec 090-06 AC-8, AC-9).

Usage:
    check_console_cp.py --probe <console_cp_probe> --lesson <lesson_exe>
    check_console_cp.py --read-screen <out-file>  (internal mode called in hidden console)
    check_console_cp.py --report-cp <out-file>    (internal: writes GetConsoleOutputCP() of this console)

`chcp` without arguments is not used for the check after exit: it does not show the output code page
that the lesson changes, so a missing restore would pass (mutant M3, 090-06 testrecord).
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from pathlib import Path
import re
import subprocess
import sys
import tempfile

# A non-ASCII line of lesson_device_state_machine (Tracer heading, U+2550): a console that is not UTF-8 garbles it.
# The lesson output is English since 070-03, so the line is no longer the Korean heading of 090-06 AC-9.
EXPECTED_LINE = "══ State Transitions ══"
RUN_TIMEOUT_S = 60


def read_screen(out_file: Path) -> int:
    """Reads the current console screen buffer and dumps lines as UTF-8."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    generic_read = 0x80000000
    generic_write = 0x40000000
    file_share_read = 1
    file_share_write = 2
    open_existing = 3
    invalid_handle_value = ctypes.c_void_p(-1).value

    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE

    handle = kernel32.CreateFileW(
        "CONOUT$",
        generic_read | generic_write,
        file_share_read | file_share_write,
        None,
        open_existing,
        0,
        None,
    )
    if handle == invalid_handle_value or handle == 0 or handle is None:
        err = ctypes.get_last_error()
        out_file.write_text(f"ERROR: CreateFileW CONOUT$ failed: {err}\n", encoding="utf-8")
        return 1

    class COORD(ctypes.Structure):
        _fields_ = [
            ("X", wintypes.SHORT),
            ("Y", wintypes.SHORT),
        ]

    class SMALL_RECT(ctypes.Structure):
        _fields_ = [
            ("Left", wintypes.SHORT),
            ("Top", wintypes.SHORT),
            ("Right", wintypes.SHORT),
            ("Bottom", wintypes.SHORT),
        ]

    class CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [
            ("dwSize", COORD),
            ("dwCursorPosition", COORD),
            ("wAttributes", wintypes.WORD),
            ("srWindow", SMALL_RECT),
            ("dwMaximumWindowSize", COORD),
        ]

    kernel32.GetConsoleScreenBufferInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(CONSOLE_SCREEN_BUFFER_INFO),
    ]
    kernel32.GetConsoleScreenBufferInfo.restype = wintypes.BOOL

    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    if not kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(csbi)):
        err = ctypes.get_last_error()
        out_file.write_text(f"ERROR: GetConsoleScreenBufferInfo failed: {err}\n", encoding="utf-8")
        kernel32.CloseHandle(handle)
        return 1

    width = csbi.dwSize.X
    cursor_y = csbi.dwCursorPosition.Y
    if width <= 0 or cursor_y < 0:
        out_file.write_text(
            f"ERROR: invalid console dimensions: width={width}, cursor_y={cursor_y}\n",
            encoding="utf-8",
        )
        kernel32.CloseHandle(handle)
        return 1

    total_cells = width * (cursor_y + 1)
    buf = ctypes.create_unicode_buffer(total_cells)
    chars_read = wintypes.DWORD(0)

    kernel32.ReadConsoleOutputCharacterW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        COORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.ReadConsoleOutputCharacterW.restype = wintypes.BOOL

    if not kernel32.ReadConsoleOutputCharacterW(
        handle,
        buf,
        total_cells,
        COORD(0, 0),
        ctypes.byref(chars_read),
    ):
        err = ctypes.get_last_error()
        out_file.write_text(f"ERROR: ReadConsoleOutputCharacterW failed: {err}\n", encoding="utf-8")
        kernel32.CloseHandle(handle)
        return 1

    kernel32.CloseHandle(handle)

    # Not split into rows: a wide character (Korean) fills two cells but is returned once, so
    # cutting every `width` characters drifts after the first wide character.
    out_file.write_text(buf[: chars_read.value].replace("\x00", ""), encoding="utf-8")
    return 0


def report_cp(out_file: Path) -> int:
    """Writes the output code page of the console this process is attached to."""
    out_file.write_text(f"{ctypes.WinDLL('kernel32').GetConsoleOutputCP()}\n", encoding="utf-8")
    return 0


def read_cp(path: Path) -> int | None:
    """The code page written by --report-cp, or None when the file is missing or empty."""
    if not path.exists():
        return None
    m = re.search(r"(\d+)", path.read_text(encoding="utf-8", errors="replace"))
    return int(m.group(1)) if m else None


def run_hidden(inner: str) -> bool:
    """Runs `chcp 949 >nul & <inner>` in a new hidden console; False if it timed out.

    No stdin/stdout/stderr arguments on purpose: with any of them Python passes the driver's own
    handles (pipes under ctest), and the programs would no longer write to the hidden console.
    The command line is one string: as a list, its inner quotes would be escaped and cmd would fail.
    """
    try:
        subprocess.run(f'cmd.exe /d /s /c "chcp 949 >nul & {inner}"',
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=RUN_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        print(f"FAIL: timed out after {RUN_TIMEOUT_S} s: {inner}")
        return False
    return True


def parse_probe_file(path: Path) -> dict[str, int]:
    """Parses run=<cp> and dtor=<cp> lines from probe output."""
    res: dict[str, int] = {}
    if not path.exists():
        return res
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if "=" in line:
            k, v = line.split("=", 1)
            try:
                res[k.strip()] = int(v.strip())
            except ValueError:
                pass
    return res


def screen_contains_expected(screen_text: str, expected: str) -> bool:
    """True if the screen text (all cells, unsplit) contains the expected line."""
    return expected in screen_text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify lesson console UTF-8 switching and restoration (spec 090-06 AC-8, AC-9)."
    )
    parser.add_argument("--probe", type=Path, help="Path to console_cp_probe executable")
    parser.add_argument("--lesson", type=Path, help="Path to lesson executable")
    parser.add_argument("--report-cp", type=Path, dest="report_cp_path",
                        help="Internal child: write this console's output code page to a file")
    parser.add_argument(
        "--read-screen",
        type=Path,
        dest="read_screen_path",
        help="Internal reader child: dump screen buffer to file",
    )
    args = parser.parse_args()

    if args.read_screen_path is not None:
        return read_screen(args.read_screen_path.resolve())
    if args.report_cp_path is not None:
        return report_cp(args.report_cp_path.resolve())

    if not args.probe or not args.lesson:
        parser.error("Both --probe and --lesson are required when not using --read-screen")

    probe_exe = args.probe.resolve()
    lesson_exe = args.lesson.resolve()
    this_script = Path(__file__).resolve()
    python_exe = Path(sys.executable).resolve()

    if not probe_exe.is_file():
        print(f"FAIL: probe executable not found: {probe_exe}")
        return 1
    if not lesson_exe.is_file():
        print(f"FAIL: lesson executable not found: {lesson_exe}")
        return 1

    all_passed = True
    report = f'"{python_exe}" -I "{this_script}" --report-cp'

    # ignore_cleanup_errors: after a timeout a grandchild in the hidden console may still hold a file.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        work_dir = Path(td)

        # Check 1 (AC-8): probe with console stdout. Expect run=65001, dtor=65001, 949 after exit.
        probe_out_1, after_out_1 = work_dir / "probe1.txt", work_dir / "after1.txt"
        ran = run_hidden(f'"{probe_exe}" "{probe_out_1}" & {report} "{after_out_1}"')
        res1, cp1 = parse_probe_file(probe_out_1), read_cp(after_out_1)
        run1, dtor1 = res1.get("run"), res1.get("dtor")
        ok1 = ran and run1 == 65001 and dtor1 == 65001 and cp1 == 949
        all_passed &= ok1
        print(f"check 1 (probe console): run={run1} dtor={dtor1} after={cp1} "
              f"(expected run=65001, dtor=65001, after=949) -> {'PASS' if ok1 else 'FAIL'}")

        # Check 2 (AC-8): probe with stdout to a pipe. Expect the code page untouched: run=949, after=949.
        probe_out_2, after_out_2 = work_dir / "probe2.txt", work_dir / "after2.txt"
        ran = run_hidden(f'"{probe_exe}" "{probe_out_2}" | more >nul & {report} "{after_out_2}"')
        run2, cp2 = parse_probe_file(probe_out_2).get("run"), read_cp(after_out_2)
        ok2 = ran and run2 == 949 and cp2 == 949
        all_passed &= ok2
        print(f"check 2 (probe pipe): run={run2} after={cp2} "
              f"(expected run=949, after=949) -> {'PASS' if ok2 else 'FAIL'}")

        # Check 3 (AC-9): the real lesson, then a reader in the same console reads the screen.
        screen_out_3, after_out_3 = work_dir / "screen3.txt", work_dir / "after3.txt"
        ran = run_hidden(f'"{lesson_exe}" & "{python_exe}" -I "{this_script}" --read-screen "{screen_out_3}"'
                         f' & {report} "{after_out_3}"')
        screen_text = screen_out_3.read_text(encoding="utf-8", errors="replace") if screen_out_3.exists() else ""
        cp3 = read_cp(after_out_3)
        found3 = screen_contains_expected(screen_text, EXPECTED_LINE)
        ok3 = ran and found3 and cp3 == 949
        all_passed &= ok3
        print(f"check 3 (lesson console screen): found={found3} after={cp3} "
              f"(expected line found and after=949) -> {'PASS' if ok3 else 'FAIL'}")
        if not found3:
            print(f"  screen (first 300 characters): {' '.join(screen_text.split())[:300]!r}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
