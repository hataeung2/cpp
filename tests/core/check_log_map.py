#!/usr/bin/env python3
"""Drives log_map_probe and verifies memory-mapped log buffers and recovery (spec 010-10, plan D5).

Usage:
  check_log_map.py --probe <log_map_probe> --work <dir> [--no-crash] [-- launcher...]

Cases:
  killmap    AC-1/AC-2/AC-10: killed after READY; copies .logmap to <work>/killmap.logmap.copy;
             runs read_dump.py; startrecover recovers undelivered lines;
             verifies line union, bidirectional delivered check, ordering, labels, counts
  live       AC-3: active process is skipped by recover (unchanged name, size, hash);
             after killing it, recover recovers it
  normal     AC-4: clean exit by normal return requires MAP <path>, leaves no .logmap and nothing to recover
  exit       AC-4: clean exit by std::exit requires MAP <path>, leaves no .logmap and nothing to recover
  quickexit  AC-4: clean exit by std::quick_exit requires MAP <path>, leaves no .logmap and nothing to recover
  abort      AC-5: abort() requires MAP <path>, leaves dump; recover flags crash 1; recovered header has crash handler: yes
  segv       AC-5: SIGSEGV requires MAP <path>, leaves dump; recover flags crash 1; recovered header has crash handler: yes
  config     AC-7: configuration error paths, re-entry, and inactive checks
  env        AC-7: ATUGCC_LOG_MAP_DIR starts mapped logging in new process
  full       AC-8: arena exhaustion spills cleanly to heap without loss; exactly one stderr warning
  threads    AC-11: thread churn (50 rounds x 8 threads x 100 lines) preserves all lines, leaves no .logmap

Exit 0 only when all cases pass.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BODY_RE = re.compile(r"^(\S+Z) T(\d+) \[(undelivered|delivered)\] (\S+) (.*)$")
PRODUCER_LINE_RE = re.compile(r"P(\d+) L(\d+)$")
PID_RE = re.compile(r"^# pid (\d+),")
CRASH_RE = re.compile(r"^# ended without a clean exit; crash handler: (yes|no)$")
COUNTS_RE = re.compile(r"^# (\d+) undelivered lines.*, (\d+) delivered lines.*, (\d+) skipped buffers")


def fail(case: str, msg: str) -> bool:
    print(f"FAIL {case}: {msg}")
    return False


def prepare_dir(path: Path) -> Path:
    if path.exists():
        for attempt in range(5):
            try:
                shutil.rmtree(path)
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(0.05)
    path.mkdir(parents=True, exist_ok=True)
    return path


def wait_for_ready(proc: subprocess.Popen[str], timeout: float = 60.0) -> tuple[bool, str]:
    ready_line: list[str] = []
    exc: list[Exception] = []

    def reader() -> None:
        try:
            assert proc.stdout is not None
            line = proc.stdout.readline()
            ready_line.append(line)
        except Exception as e:
            exc.append(e)

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        return False, "timed out waiting for READY"
    if exc:
        return False, f"error reading stdout: {exc[0]}"
    if not ready_line or ready_line[0].strip() != "READY":
        got = ready_line[0] if ready_line else "<EOF>"
        return False, f"expected 'READY', got {got!r}"
    return True, ready_line[0]


def kill_process(proc: subprocess.Popen[str], timeout: float = 60.0) -> None:
    if proc.poll() is None:
        try:
            proc.kill()
            proc.wait(timeout=timeout)
        except Exception:
            pass


def read_bytes_shared(path: Path) -> bytes:
    if sys.platform == "win32":
        import ctypes
        import msvcrt

        k32 = ctypes.windll.kernel32
        GENERIC_READ = 0x80000000
        FILE_SHARE_READ = 1
        FILE_SHARE_WRITE = 2
        FILE_SHARE_DELETE = 4
        OPEN_EXISTING = 3
        handle = k32.CreateFileW(
            str(path),
            GENERIC_READ,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        if handle == -1 or handle == 0xFFFFFFFFFFFFFFFF:
            raise OSError(f"CreateFileW failed for {path} with error {k32.GetLastError()}")
        try:
            fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | getattr(os, "O_BINARY", 0))
            with open(fd, "rb", closefd=True) as f:
                return f.read()
        except Exception:
            k32.CloseHandle(handle)
            raise
    else:
        with open(path, "rb") as f:
            return f.read()


def sha256_shared(path: Path) -> str:
    return hashlib.sha256(read_bytes_shared(path)).hexdigest()


def parse_recovered_probe_output(stdout: str) -> list[tuple[str, int, int, int, int, int]]:
    entries = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("RECOVERED "):
            rest = line.removeprefix("RECOVERED ").strip()
            parts = rest.rsplit(maxsplit=5)
            if len(parts) == 6:
                entries.append(
                    (
                        parts[0],
                        int(parts[1]),
                        int(parts[2]),
                        int(parts[3]),
                        int(parts[4]),
                        int(parts[5]),
                    )
                )
    return entries


@dataclass
class RecoveredRecord:
    timestamp: str
    thread_no: int
    status: str
    label: str
    text: str


@dataclass
class RecoveredData:
    pid: int | None
    crash_handler: str | None
    header_undelivered: int
    header_delivered: int
    header_skipped: int
    records: list[RecoveredRecord]


def parse_recovered_file(path: Path) -> RecoveredData:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    pid = None
    crash_handler = None
    header_undelivered = 0
    header_delivered = 0
    header_skipped = 0
    records: list[RecoveredRecord] = []

    for line in lines:
        if line.startswith("#"):
            m_pid = PID_RE.match(line)
            if m_pid:
                pid = int(m_pid.group(1))
            m_crash = CRASH_RE.match(line)
            if m_crash:
                crash_handler = m_crash.group(1)
            m_cnt = COUNTS_RE.match(line)
            if m_cnt:
                header_undelivered = int(m_cnt.group(1))
                header_delivered = int(m_cnt.group(2))
                header_skipped = int(m_cnt.group(3))
        else:
            m_body = BODY_RE.match(line)
            if m_body:
                records.append(
                    RecoveredRecord(
                        timestamp=m_body.group(1),
                        thread_no=int(m_body.group(2)),
                        status=m_body.group(3),
                        label=m_body.group(4),
                        text=m_body.group(5),
                    )
                )
            elif line.strip():
                raise ValueError(f"malformed body line: {line[:100]}")

    return RecoveredData(
        pid=pid,
        crash_handler=crash_handler,
        header_undelivered=header_undelivered,
        header_delivered=header_delivered,
        header_skipped=header_skipped,
        records=records,
    )


def run_case_killmap(probe: str, work: Path, launcher: list[str]) -> bool:
    case_dir = prepare_dir(work / "killmap")
    cmd = [*launcher, probe, "killmap", str(case_dir)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        ok, line = wait_for_ready(proc, timeout=60.0)
        if not ok:
            return fail("killmap", f"failed waiting for READY: {line!r}")
        kill_process(proc, timeout=60.0)
    finally:
        kill_process(proc, timeout=5.0)

    # 1. Locate .logmap and extract killed pid
    logmaps = list(case_dir.glob("*.logmap"))
    if len(logmaps) != 1:
        return fail("killmap", f"expected exactly 1 .logmap before recovery, found {len(logmaps)}")
    logmap_path = logmaps[0]
    m_pid = re.search(r"atugcc-(\d+)-", logmap_path.name)
    if not m_pid:
        return fail("killmap", f"cannot extract pid from .logmap filename: {logmap_path.name}")
    killed_pid = m_pid.group(1)

    # 2. Copy the .logmap to <work>/killmap.logmap.copy BEFORE running startrecover (for AC-10)
    copy_dest = work / "killmap.logmap.copy"
    shutil.copy2(logmap_path, copy_dest)
    if not copy_dest.exists() or copy_dest.stat().st_size == 0:
        return fail("killmap", f"failed to copy .logmap to {copy_dest}")

    # AC-10: run tools/read_dump.py <copy> --undelivered
    read_dump_script = ROOT / "tools" / "read_dump.py"
    cmd_dump = [sys.executable, str(read_dump_script), str(copy_dest), "--undelivered"]
    dump_res = subprocess.run(cmd_dump, capture_output=True, text=True, timeout=60.0)
    if dump_res.returncode != 0:
        return fail("killmap", f"read_dump.py failed with exit code {dump_res.returncode}: {dump_res.stderr}")
    dump_producer_lines = [
        m.group(0)
        for line in dump_res.stdout.splitlines()
        if (m := PRODUCER_LINE_RE.search(line))
    ]

    # 3. Run startrecover
    cmd_rec = [*launcher, probe, "startrecover", str(case_dir)]
    rec_res = subprocess.run(cmd_rec, capture_output=True, text=True, timeout=60.0)
    if rec_res.returncode != 0:
        return fail("killmap", f"startrecover failed with code {rec_res.returncode}: {rec_res.stderr}")
    if "recovered " not in rec_res.stderr:
        return fail("killmap", f"startrecover stderr does not contain 'recovered ': {rec_res.stderr}")

    # 4. Check no "*.logmap" left whose name contains f"atugcc-{killed_pid}-"
    target_prefix = f"atugcc-{killed_pid}-"
    rem_maps = list(case_dir.glob("*.logmap"))
    for p in rem_maps:
        if target_prefix in p.name:
            return fail("killmap", f"remaining .logmap matches killed pid pattern {target_prefix}: {p.name}")

    # 5. Check recovered files and parse
    rec_files = list(case_dir.glob("recovered_*.log"))
    if len(rec_files) != 1:
        return fail("killmap", f"expected 1 recovered file, found {len(rec_files)}")
    rec_data = parse_recovered_file(rec_files[0])

    # AC-10: assert read_dump.py producer lines equal recovered file's [undelivered] producer lines
    rec_undelivered_lines = [
        m.group(0)
        for r in rec_data.records
        if r.status == "undelivered" and (m := PRODUCER_LINE_RE.search(r.text))
    ]
    if dump_producer_lines != rec_undelivered_lines:
        return fail(
            "killmap",
            f"read_dump undelivered producer lines != recovered file undelivered producer lines: "
            f"dump count {len(dump_producer_lines)} vs rec count {len(rec_undelivered_lines)}",
        )

    # 6. Header counts == body counts
    body_undelivered = sum(1 for r in rec_data.records if r.status == "undelivered")
    body_delivered = sum(1 for r in rec_data.records if r.status == "delivered")
    if rec_data.header_undelivered != body_undelivered:
        return fail("killmap", f"header undelivered {rec_data.header_undelivered} != body {body_undelivered}")
    if rec_data.header_delivered != body_delivered:
        return fail("killmap", f"header delivered {rec_data.header_delivered} != body {body_delivered}")

    # 7. >= 1 undelivered
    if body_undelivered < 1:
        return fail("killmap", f"expected >= 1 undelivered line, got {body_undelivered}")

    # 8. Body time order non-decreasing (compare the timestamp strings)
    for idx in range(1, len(rec_data.records)):
        prev_ts = rec_data.records[idx - 1].timestamp
        cur_ts = rec_data.records[idx].timestamp
        if cur_ts < prev_ts:
            return fail("killmap", f"time order inversion: {cur_ts} < {prev_ts} at record {idx}")

    # 9. Label "app.log" on producer lines
    for r in rec_data.records:
        if PRODUCER_LINE_RE.search(r.text):
            if r.label != "app.log":
                return fail("killmap", f"producer line has label {r.label!r}, expected 'app.log'")

    # 10. Union check over 4 producers x 1000 lines & lines missing from app.log must be [undelivered]
    # & reverse direction: every recovered [delivered] producer line must also be in app.log
    app_log_path = case_dir / "app.log"
    if not app_log_path.exists():
        return fail("killmap", "app.log not found")
    app_lines = app_log_path.read_text(encoding="utf-8", errors="replace").splitlines()

    app_pairs: set[tuple[int, int]] = set()
    for line in app_lines:
        m = PRODUCER_LINE_RE.search(line)
        if m:
            app_pairs.add((int(m.group(1)), int(m.group(2))))

    undelivered_pairs: set[tuple[int, int]] = set()
    delivered_pairs: set[tuple[int, int]] = set()
    for r in rec_data.records:
        m = PRODUCER_LINE_RE.search(r.text)
        if m:
            pair = (int(m.group(1)), int(m.group(2)))
            if r.status == "undelivered":
                undelivered_pairs.add(pair)
            elif r.status == "delivered":
                delivered_pairs.add(pair)

    # Reverse direction: every recovered [delivered] producer line must also be in app.log
    for pair in delivered_pairs:
        if pair not in app_pairs:
            return fail("killmap", f"recovered [delivered] line P{pair[0]} L{pair[1]} missing from app.log")

    all_expected = {(p, i) for p in range(4) for i in range(1000)}

    missing_from_app = all_expected - app_pairs
    for pair in missing_from_app:
        if pair not in undelivered_pairs:
            return fail("killmap", f"line P{pair[0]} L{pair[1]} missing from app.log and not in undelivered")

    union_pairs = app_pairs | undelivered_pairs
    missing_from_union = all_expected - union_pairs
    if missing_from_union:
        return fail(
            "killmap",
            f"{len(missing_from_union)} lines missing from union of app.log and undelivered: "
            f"{sorted(list(missing_from_union))[:5]}",
        )

    return True


def run_case_live(probe: str, work: Path, launcher: list[str]) -> bool:
    case_dir = prepare_dir(work / "live")
    cmd = [*launcher, probe, "live", str(case_dir)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        ok, line = wait_for_ready(proc, timeout=60.0)
        if not ok:
            return fail("live", f"failed waiting for READY: {line!r}")
        if proc.poll() is not None:
            return fail("live", f"live probe exited prematurely with {proc.returncode}")

        # Ensure background drain of P0 L0 completes before recording initial state
        app_log = case_dir / "app.log"
        for _ in range(50):
            if app_log.exists() and "P0 L0" in app_log.read_text(encoding="utf-8", errors="replace"):
                break
            time.sleep(0.02)
        time.sleep(0.05)

        # Check .logmap exists while live probe is running
        logmaps = list(case_dir.glob("*.logmap"))
        if len(logmaps) != 1:
            return fail("live", f"expected exactly 1 .logmap file while live probe is running, found {len(logmaps)}")
        logmap_path = logmaps[0]

        # Record A's map file name, size and sha256 (read-only open)
        map_name = logmap_path.name
        map_size = logmap_path.stat().st_size
        map_hash = sha256_shared(logmap_path)

        # Run recover while live probe is running (process B)
        cmd_rec = [*launcher, probe, "recover", str(case_dir)]
        rec_res = subprocess.run(cmd_rec, capture_output=True, text=True, timeout=60.0)
        if rec_res.returncode != 0:
            return fail("live", f"recover while live failed: {rec_res.stderr}")
        entries = parse_recovered_probe_output(rec_res.stdout)
        if entries:
            return fail("live", f"recover listed live process file: {rec_res.stdout}")

        # Assert the same name, size and hash
        if not logmap_path.exists():
            return fail("live", ".logmap was removed while live process was running")
        if logmap_path.name != map_name:
            return fail("live", f".logmap name changed: {logmap_path.name} != {map_name}")
        if logmap_path.stat().st_size != map_size:
            return fail("live", f".logmap size changed: {logmap_path.stat().st_size} != {map_size}")
        after_hash = sha256_shared(logmap_path)
        if after_hash != map_hash:
            return fail("live", ".logmap sha256 changed after recover attempt while live")

        # Assert no recovered_*.log and no *.corrupt appeared
        rec_logs = list(case_dir.glob("recovered_*.log"))
        if rec_logs:
            return fail("live", f"recovered log appeared while live process was running: {[p.name for p in rec_logs]}")
        corrupts = list(case_dir.glob("*.corrupt"))
        if corrupts:
            return fail("live", f".corrupt file appeared while live process was running: {[p.name for p in corrupts]}")
    finally:
        kill_process(proc, timeout=60.0)

    # After live is killed, recover should list it
    cmd_rec2 = [*launcher, probe, "recover", str(case_dir)]
    rec_res2 = subprocess.run(cmd_rec2, capture_output=True, text=True, timeout=60.0)
    if rec_res2.returncode != 0:
        return fail("live", f"recover after kill failed: {rec_res2.stderr}")
    entries2 = parse_recovered_probe_output(rec_res2.stdout)
    if not entries2:
        return fail("live", f"recover did not list the killed live process: {rec_res2.stdout}")

    if not list(case_dir.glob("recovered_*.log")):
        return fail("live", "no recovered_*.log file created after recovering killed live process")
    if list(case_dir.glob("*.logmap")):
        return fail("live", ".logmap remains after recovery")

    return True


def run_case_clean_exit(probe: str, work: Path, launcher: list[str], mode: str) -> bool:
    case_dir = prepare_dir(work / mode)
    cmd = [*launcher, probe, mode, str(case_dir)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60.0)
    if res.returncode != 0:
        return fail(mode, f"probe {mode} failed with code {res.returncode}: {res.stderr}")

    # Require MAP <path> line
    map_lines = [line.strip() for line in res.stdout.splitlines() if line.startswith("MAP ")]
    if not map_lines:
        return fail(mode, f"probe did not print 'MAP <path>':\nstdout: {res.stdout}")
    map_path = Path(map_lines[0].removeprefix("MAP ").strip())
    if map_path.exists():
        return fail(mode, f"mapped file {map_path} still exists after clean {mode}")

    # No .logmap remains
    logmaps = list(case_dir.glob("*.logmap"))
    if logmaps:
        return fail(mode, f".logmap remains after {mode}: {[p.name for p in logmaps]}")

    # Recover lists nothing
    cmd_rec = [*launcher, probe, "recover", str(case_dir)]
    rec_res = subprocess.run(cmd_rec, capture_output=True, text=True, timeout=60.0)
    if rec_res.returncode != 0:
        return fail(mode, f"recover after {mode} failed: {rec_res.stderr}")
    entries = parse_recovered_probe_output(rec_res.stdout)
    if entries:
        return fail(mode, f"recover listed entries after clean {mode}: {rec_res.stdout}")

    # Verify app.log has 100 producer lines
    app_log = case_dir / "app.log"
    if not app_log.exists():
        return fail(mode, f"app.log missing after {mode}")
    app_lines = app_log.read_text(encoding="utf-8", errors="replace").splitlines()
    seen = [line for line in app_lines if "P0 L" in line]
    if len(seen) != 100:
        return fail(mode, f"expected 100 producer lines in app.log, found {len(seen)}")

    return True


def run_case_crash(probe: str, work: Path, launcher: list[str], mode: str) -> bool:
    case_dir = prepare_dir(work / mode)
    cmd = [*launcher, probe, mode, str(case_dir)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60.0)
    if res.returncode == 0:
        return fail(mode, "probe did not crash (exit code 0)")

    # Require MAP <path> line
    map_lines = [line.strip() for line in res.stdout.splitlines() if line.startswith("MAP ")]
    if not map_lines:
        return fail(mode, f"probe did not print 'MAP <path>':\nstdout: {res.stdout}\nstderr: {res.stderr}")
    map_path = Path(map_lines[0].removeprefix("MAP ").strip())
    if not map_path.exists():
        return fail(mode, f"mapped file {map_path} reported by MAP does not exist after crash")

    # Crash dump exists
    dumps = list(case_dir.glob("crash_dump_*.log"))
    if not dumps:
        return fail(mode, "no crash_dump_*.log found")
    if dumps[0].stat().st_size == 0:
        return fail(mode, "crash dump file is empty")

    # Recover shows crash 1
    cmd_rec = [*launcher, probe, "recover", str(case_dir)]
    rec_res = subprocess.run(cmd_rec, capture_output=True, text=True, timeout=60.0)
    if rec_res.returncode != 0:
        return fail(mode, f"recover failed: {rec_res.stderr}")

    entries = parse_recovered_probe_output(rec_res.stdout)
    if not entries:
        return fail(mode, f"no RECOVERED line in recover output: {rec_res.stdout}")
    if entries[0][5] != 1:
        return fail(mode, f"recover showed crash {entries[0][5]}, expected 1")

    # Recovered header says "crash handler: yes"
    rec_files = list(case_dir.glob("recovered_*.log"))
    if not rec_files:
        return fail(mode, "no recovered_*.log file found")
    content = rec_files[0].read_text(encoding="utf-8", errors="replace")
    if "# ended without a clean exit; crash handler: yes" not in content:
        return fail(mode, f"recovered file header lacks 'crash handler: yes':\n{content[:400]}")

    if list(case_dir.glob("*.logmap")):
        return fail(mode, ".logmap remains after recovery")

    return True


def run_case_config(probe: str, work: Path, launcher: list[str]) -> bool:
    case_dir = prepare_dir(work / "config")
    cmd = [*launcher, probe, "config", str(case_dir)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60.0)
    if res.returncode != 0:
        return fail("config", f"probe exit code {res.returncode}: {res.stderr}\nstdout: {res.stdout}")

    expected_steps = [
        "OK mappedBytes",
        "OK fileIOFailure",
        "OK dirA",
        "OK dirB",
        "OK dirAAgain",
        "OK empty",
        "OK logMapActive",
    ]
    for step in expected_steps:
        if step not in res.stdout:
            return fail("config", f"missing '{step}' in stdout:\n{res.stdout}")
    if "FAIL" in res.stdout:
        return fail("config", f"found FAIL in stdout:\n{res.stdout}")

    return True


def run_case_env(probe: str, work: Path, launcher: list[str]) -> bool:
    case_dir = prepare_dir(work / "env")
    cmd = [*launcher, probe, "env", str(case_dir)]
    env = dict(os.environ)
    env["ATUGCC_LOG_MAP_DIR"] = str(case_dir)
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60.0, env=env)
    if res.returncode != 0:
        return fail("env", f"probe exit code {res.returncode}: {res.stderr}\nstdout: {res.stdout}")
    if "MAPPED 1" not in res.stdout:
        return fail("env", f"expected 'MAPPED 1' in stdout, got:\n{res.stdout}")

    return True


def run_case_full(probe: str, work: Path, launcher: list[str]) -> bool:
    case_dir = prepare_dir(work / "full")
    cmd = [*launcher, probe, "full", str(case_dir)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60.0)
    if res.returncode != 0:
        return fail("full", f"probe exit code {res.returncode}: {res.stderr}\nstdout: {res.stdout}")
    if "MAPPED 7 HEAP 5" not in res.stdout:
        return fail("full", f"expected 'MAPPED 7 HEAP 5' in stdout, got: {res.stdout}")

    full_lines = [line for line in res.stderr.splitlines() if "log map full" in line]
    if len(full_lines) != 1:
        return fail("full", f"expected exactly 1 'log map full' line on stderr, found {len(full_lines)}: {res.stderr}")

    app_log = case_dir / "app.log"
    if not app_log.exists():
        return fail("full", "app.log missing")
    app_lines = app_log.read_text(encoding="utf-8", errors="replace").splitlines()
    seen: set[tuple[int, int]] = set()
    for line in app_lines:
        m = PRODUCER_LINE_RE.search(line)
        if m:
            seen.add((int(m.group(1)), int(m.group(2))))

    expected_all = {(p, i) for p in range(12) for i in range(1000)}
    missing = expected_all - seen
    if missing:
        return fail("full", f"{len(missing)} producer lines missing from app.log: {sorted(list(missing))[:5]}")
    if len(seen) != 12000:
        return fail("full", f"expected 12,000 unique producer lines in app.log, found {len(seen)}")

    return True


def run_case_threads(probe: str, work: Path, launcher: list[str]) -> bool:
    case_dir = prepare_dir(work / "threads")
    cmd = [*launcher, probe, "threads", str(case_dir)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=60.0)
    if res.returncode != 0:
        return fail("threads", f"probe exit code {res.returncode}: {res.stderr}\nstdout: {res.stdout}")

    logmaps = list(case_dir.glob("*.logmap"))
    if logmaps:
        return fail("threads", f".logmap remaining after threads: {[p.name for p in logmaps]}")

    app_log = case_dir / "app.log"
    if not app_log.exists():
        return fail("threads", "app.log missing")
    app_lines = app_log.read_text(encoding="utf-8", errors="replace").splitlines()

    counts: dict[tuple[int, int], int] = {}
    total_producer_lines = 0
    for line in app_lines:
        m = PRODUCER_LINE_RE.search(line)
        if m:
            pair = (int(m.group(1)), int(m.group(2)))
            counts[pair] = counts.get(pair, 0) + 1
            total_producer_lines += 1

    if total_producer_lines != 40000:
        return fail("threads", f"expected 40,000 producer lines in app.log, got {total_producer_lines}")

    for p in range(8):
        for i in range(100):
            c = counts.get((p, i), 0)
            if c != 50:
                return fail("threads", f"P{p} L{i} appeared {c} times (expected 50)")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Check log map mapped buffers and recovery (spec 010-10)")
    parser.add_argument("--probe", required=True, help="Path to log_map_probe executable")
    parser.add_argument("--work", required=True, type=Path, help="Working directory for test cases")
    parser.add_argument("--no-crash", action="store_true", help="Skip crash cases (sanitizer presets)")
    parser.add_argument("launcher", nargs="*", help="Optional launcher command (e.g. setarch -R)")
    args = parser.parse_args()

    args.work.mkdir(parents=True, exist_ok=True)

    cases = [
        ("killmap", lambda: run_case_killmap(args.probe, args.work, args.launcher)),
        ("live", lambda: run_case_live(args.probe, args.work, args.launcher)),
        ("normal", lambda: run_case_clean_exit(args.probe, args.work, args.launcher, "normal")),
        ("exit", lambda: run_case_clean_exit(args.probe, args.work, args.launcher, "exit")),
        ("quickexit", lambda: run_case_clean_exit(args.probe, args.work, args.launcher, "quickexit")),
    ]
    if not args.no_crash:
        cases.append(("abort", lambda: run_case_crash(args.probe, args.work, args.launcher, "abort")))
        cases.append(("segv", lambda: run_case_crash(args.probe, args.work, args.launcher, "segv")))
    cases.extend([
        ("config", lambda: run_case_config(args.probe, args.work, args.launcher)),
        ("env", lambda: run_case_env(args.probe, args.work, args.launcher)),
        ("full", lambda: run_case_full(args.probe, args.work, args.launcher)),
        ("threads", lambda: run_case_threads(args.probe, args.work, args.launcher)),
    ])

    all_ok = True
    for case_name, case_fn in cases:
        try:
            if case_fn():
                print(f"PASS {case_name}")
            else:
                all_ok = False
        except Exception as e:
            fail(case_name, f"unhandled exception: {e}")
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
