#!/usr/bin/env python3
"""Tests for the web playground server (spec 070-02 AC-3, AC-4, AC-5, AC-9, AC-11, AC-12;
spec 070-06 AC-1, AC-2, AC-3, AC-4, AC-7, AC-9, AC-10).

    python3 web/server/test_server.py [--fixture <playground_fixture binary>] [unittest args] [-- <launcher prefix...>]

File and request-guard tests run on any host. Run tests need Linux and the fixture program
(tests/playground/playground_fixture.cpp); CTest passes it (test PlaygroundServer):
    py -3 .agent/scripts/build.py --preset linux-x64-debug --test
Without --fixture those tests are skipped and the summary says so.
"""
from __future__ import annotations

import argparse
import glob
import http.client
import json
import os
import random
import shutil
import subprocess
import socket
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import runner  # noqa: E402
import server  # noqa: E402
from files import Conflict, PathError, RepoFiles  # noqa: E402
from spans import SpanAggregator  # noqa: E402

FIXTURE: str | None = None
LAUNCHER: list[str] = []  # setarch -R under TSan (ATUGCC_TEST_LAUNCHER)
POSIX = os.name == "posix"


def needs_fixture(cls):
    """Skip the class unless main() got --fixture (checked when a test starts, after parsing)."""
    original = cls.setUp

    def setUp(self) -> None:
        if not (FIXTURE and POSIX):
            self.skipTest("needs Linux and --fixture <playground_fixture>")
        original(self)
    cls.setUp = setUp
    return cls


def processes_matching(text: str) -> list[int]:
    """Pids whose command line contains `text` (Linux /proc)."""
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if text in cmdline:
            found.append(int(entry.name))
    return found


def make_tree(root: Path) -> None:
    (root / "lessons" / "a").mkdir(parents=True)
    (root / "lessons" / "a" / "main.cpp").write_bytes(b"int main() {}\n")
    (root / "lessons" / "a" / "crlf.cpp").write_bytes(b"// one\r\n// two\r\nint x;\r\n")
    (root / "include").mkdir()
    (root / "include" / "x.hpp").write_bytes(b"#pragma once\n")
    (root / "src").mkdir()
    (root / "src" / "y.cpp").write_bytes(b"\n")
    (root / "README.md").write_bytes(b"# r\n")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_bytes(b"[core]\n")


# --- files (AC-3, AC-4) ----------------------------------------------------------------------
class FilesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "repo"
        self.root.mkdir()
        make_tree(self.root)
        (self.tmp / "outside.txt").write_bytes(b"secret\n")
        self.files = RepoFiles(self.root)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def assertStatus(self, status: int, call, *args) -> None:
        with self.assertRaises(PathError) as ctx:
            call(*args)
        self.assertEqual(ctx.exception.status, status, ctx.exception.message)

    def test_escapes_are_rejected(self) -> None:
        for path in ("../outside.txt", "lessons/../../outside.txt", "/etc/passwd",
                     "C:Windows/win.ini", "lessons\\a\\main.cpp", "//server/share/x",
                     ".git/config", "lessons/a/./main.cpp", "lessons/a/main.cpp\x00.md", ""):
            with self.subTest(path=path):
                self.assertStatus(400, self.files.read, path)
                self.assertStatus(400, self.files.write, path, "x", None)

    @unittest.skipUnless(POSIX, "symlinks need POSIX here")
    def test_symlink_out_of_the_repository_is_rejected(self) -> None:
        link = self.root / "lessons" / "a" / "link.cpp"
        link.symlink_to(self.tmp / "outside.txt")
        self.assertStatus(400, self.files.read, "lessons/a/link.cpp")
        self.assertStatus(400, self.files.write, "lessons/a/link.cpp", "x", None)
        self.assertEqual((self.tmp / "outside.txt").read_bytes(), b"secret\n")

    @unittest.skipUnless(POSIX, "symlinks need POSIX here")
    def test_symlinked_folder_cannot_lead_writes_out_of_lessons(self) -> None:
        (self.root / "lessons" / "inc").symlink_to(self.root / "include", target_is_directory=True)
        (self.root / "lessons" / "git").symlink_to(self.root / ".git", target_is_directory=True)
        self.assertStatus(403, self.files.write, "lessons/inc/new.hpp", "x", None)
        self.assertStatus(403, self.files.write, "lessons/inc/x.hpp", "x", self.files.read("include/x.hpp")["sha"])
        self.assertFalse((self.root / "include" / "new.hpp").exists())
        self.assertFalse(self.files.read("lessons/inc/x.hpp")["writable"])
        self.assertStatus(400, self.files.read, "lessons/git/config")

    def test_writes_outside_lessons_are_forbidden(self) -> None:
        for path in ("include/x.hpp", "src/y.cpp", "README.md", "include/new.hpp",
                     "lessons/a/tool.sh", "lessons/a/new.exe", "lessons"):
            with self.subTest(path=path):
                target = self.root / path
                sha = self.files.read(path)["sha"] if target.is_file() else None  # a valid save otherwise
                self.assertStatus(403, self.files.write, path, "x", sha)
        self.assertEqual((self.root / "include" / "x.hpp").read_bytes(), b"#pragma once\n")
        self.assertFalse(self.files.read("include/x.hpp")["writable"])
        self.assertTrue(self.files.read("lessons/a/main.cpp")["writable"])

    def test_missing_file_is_404(self) -> None:
        self.assertStatus(404, self.files.read, "lessons/a/none.cpp")

    def test_stale_base_sha_is_a_conflict_with_the_disk_content(self) -> None:
        opened = self.files.read("lessons/a/main.cpp")
        (self.root / "lessons" / "a" / "main.cpp").write_bytes(b"int main() { return 1; }\n")
        with self.assertRaises(Conflict) as ctx:
            self.files.write("lessons/a/main.cpp", "int main() { return 2; }\n", opened["sha"])
        self.assertEqual(ctx.exception.content, "int main() { return 1; }\n")
        self.assertEqual(ctx.exception.sha, self.files.read("lessons/a/main.cpp")["sha"])
        self.assertEqual((self.root / "lessons" / "a" / "main.cpp").read_bytes(), b"int main() { return 1; }\n")

    def test_save_with_current_sha_writes_and_returns_the_new_sha(self) -> None:
        opened = self.files.read("lessons/a/main.cpp")
        result = self.files.write("lessons/a/main.cpp", "int main() { return 3; }\n", opened["sha"])
        self.assertEqual((self.root / "lessons" / "a" / "main.cpp").read_bytes(), b"int main() { return 3; }\n")
        self.assertEqual(result["sha"], self.files.read("lessons/a/main.cpp")["sha"])
        self.assertNotEqual(result["sha"], opened["sha"])

    def test_crlf_file_stays_crlf(self) -> None:
        opened = self.files.read("lessons/a/crlf.cpp")
        self.assertEqual(opened["eol"], "crlf")
        self.assertNotIn("\r", opened["content"])
        self.files.write("lessons/a/crlf.cpp", opened["content"] + "int y;\n", opened["sha"])
        data = (self.root / "lessons" / "a" / "crlf.cpp").read_bytes()
        self.assertEqual(data, b"// one\r\n// two\r\nint x;\r\nint y;\r\n")
        self.assertEqual(self.files.read("lessons/a/main.cpp")["eol"], "lf")

    def test_new_file_is_created_as_lf_and_only_once(self) -> None:
        self.files.write("lessons/b/c/new.hpp", "#pragma once\r\nint z;\n", None)
        self.assertEqual((self.root / "lessons" / "b" / "c" / "new.hpp").read_bytes(), b"#pragma once\nint z;\n")
        with self.assertRaises(Conflict):
            self.files.write("lessons/b/c/new.hpp", "again\n", None)
        with self.assertRaises(Conflict):  # opened, then removed on disk
            self.files.write("lessons/b/c/gone.md", "x\n", "0" * 64)

    def test_no_temporary_files_are_left(self) -> None:
        opened = self.files.read("lessons/a/main.cpp")
        self.files.write("lessons/a/main.cpp", "x\n", opened["sha"])
        self.assertEqual(sorted(p.name for p in (self.root / "lessons" / "a").iterdir()), ["crlf.cpp", "main.cpp"])

    @unittest.skipUnless(POSIX, "file modes are POSIX")
    def test_file_mode_is_kept(self) -> None:
        target = self.root / "lessons" / "a" / "main.cpp"
        target.chmod(0o640)
        self.files.write("lessons/a/main.cpp", "x\n", self.files.read("lessons/a/main.cpp")["sha"])
        self.assertEqual(target.stat().st_mode & 0o777, 0o640)


# --- runner helpers ---------------------------------------------------------------------------
def collect(job: runner.Job, timeout: float) -> list[tuple[str, dict, float]]:
    """Every event of `job` with its arrival time, until done or `timeout`."""
    out: list[tuple[str, dict, float]] = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        events, done = job.events_from(len(out), 0.05)
        now = time.monotonic()
        out += [(name, data, now) for name, data in events]
        if done:
            return out
    raise AssertionError(f"job not done after {timeout}s; events: {[e[0] for e in out]}")


def done_of(events: list[tuple[str, dict, float]]) -> dict:
    name, data, _ = events[-1]
    assert name == "done", name
    return data


def text(events, name: str) -> str:
    return "".join(d["text"] for n, d, _ in events if n == name)


def collect_updates(job: runner.Job, timeout: float, on_poll=None
                    ) -> tuple[list[tuple[str, dict, float]], list[tuple[dict, float]]]:
    """Events and span payloads of `job` with arrival times, read like a stream (updates_from).

    `on_poll()` runs after every poll (about every 50 ms), e.g. to sample memory during the run.
    """
    events: list[tuple[str, dict, float]] = []
    spans: list[tuple[dict, float]] = []
    seen = 0
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        new, done, payload, seen = job.updates_from(len(events), seen, 0.05)
        now = time.monotonic()
        if payload is not None:
            spans.append((payload, now))
        events += [(name, data, now) for name, data in new]
        if on_poll is not None:
            on_poll()
        if done:
            return events, spans
    raise AssertionError(f"job not done after {timeout}s; events: {[e[0] for e in events]}")


def stats_lines(stdout: str) -> list[dict]:
    """The fixture's `STATS {json}` lines (span_tick prints spanStats() this way)."""
    return [json.loads(line[6:]) for line in stdout.splitlines() if line.startswith("STATS ")]


def rss_bytes() -> int:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    raise AssertionError("no VmRSS")


def fixture_manager(tmp: Path, profile: str = "quick", timeout: int = 300, build: str | None = None,
                    profiles: dict[str, runner.Limits] | None = None,
                    seen_dirs: list[Path] | None = None) -> runner.RunManager:
    def executable(info: runner.LessonInfo, build_dir: Path) -> list[str]:
        if seen_dirs is not None:
            seen_dirs.append(build_dir)
        return [*LAUNCHER, FIXTURE, info.id]
    return runner.RunManager(
        runner.ROOT, build=False, profiles=profiles,
        lesson_info=lambda lesson_id: runner.LessonInfo(lesson_id, tmp, profile, timeout, build),
        executable=executable)


@needs_fixture
class RunnerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.runs = fixture_manager(self.tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_endless_lesson_ends_at_the_time_limit_without_leftovers(self) -> None:  # AC-5
        start = time.monotonic()
        events = collect(self.runs.create("loop"), 30)
        elapsed = time.monotonic() - start
        run = done_of(events)["run"]
        self.assertTrue(run["timedOut"])
        self.assertFalse(run["stopped"])
        self.assertEqual(run["signal"], "SIGKILL")
        self.assertGreaterEqual(elapsed, 10.0)
        self.assertLess(elapsed, 12.0)
        self.assertEqual(processes_matching(f"{FIXTURE} loop"), [])

    def test_large_output_is_cut_at_one_mebibyte(self) -> None:  # AC-5
        events = collect(self.runs.create("flood"), 30)
        run = done_of(events)["run"]
        self.assertTrue(run["truncated"])
        self.assertEqual(run["exitCode"], 0)
        self.assertEqual(len(text(events, "stdout").encode()), 1 << 20)

    def test_output_streams_line_by_line(self) -> None:  # AC-11 (runner level)
        events = collect(self.runs.create("tick"), 30)
        done_at = events[-1][2]
        arrivals = [t for n, _, t in events if n == "stdout" and t < done_at]
        self.assertGreaterEqual(len(arrivals), 4)
        self.assertGreaterEqual(arrivals[3] - arrivals[0], 2.5)  # spread over seconds, not one burst
        self.assertEqual(text(events, "stdout"), "".join(f"tick {i}\n" for i in range(1, 6)))

    def test_stop_ends_the_run_within_a_second(self) -> None:  # AC-12
        job = self.runs.create("loop")
        deadline = time.monotonic() + 10
        while not any(n == "phase" for n, _ in job.events):
            self.assertLess(time.monotonic(), deadline, "no phase event")
            time.sleep(0.05)
        time.sleep(0.5)
        start = time.monotonic()
        self.assertTrue(self.runs.stop(job.id))
        events = collect(job, 5)
        self.assertLess(time.monotonic() - start, 1.0)
        done = done_of(events)
        self.assertTrue(done["stopped"])
        self.assertTrue(done["run"]["stopped"])
        self.assertFalse(done["run"]["timedOut"])
        self.assertEqual(processes_matching(f"{FIXTURE} loop"), [])

    def test_background_children_do_not_survive(self) -> None:
        events = collect(self.runs.create("spawn"), 30)
        self.assertEqual(done_of(events)["run"]["exitCode"], 0)
        time.sleep(0.2)
        self.assertEqual(processes_matching("sleep 987"), [])

    def test_crash_reports_the_signal(self) -> None:
        run = done_of(collect(self.runs.create("crash"), 30))["run"]
        self.assertIsNone(run["exitCode"])
        self.assertEqual(run["signal"], "SIGABRT")

    def test_trace_events_arrive_while_running_with_repo_paths(self) -> None:
        events = collect(self.runs.create("trace"), 30)
        done = done_of(events)
        traced = [e for n, d, _ in events if n == "trace" for e in d["events"]]
        self.assertEqual([e["new"] for e in traced], ["STANDBY", "RUN", "IDLE"])
        self.assertEqual({e["file"] for e in traced}, {"tests/playground/playground_fixture.cpp"})
        self.assertGreaterEqual(len([1 for n, _, _ in events if n == "trace"]), 2)  # not one batch at the end
        self.assertTrue(done["diagrams"])
        self.assertTrue(all(d["backend"] == "mermaid" for d in done["diagrams"]))
        self.assertEqual(done["skippedTraceLines"], 0)

    def test_jobs_run_one_at_a_time_in_order(self) -> None:
        first = self.runs.create("trace")  # about 0.6 s
        second = self.runs.create("crash")
        first_done = second_start = None
        deadline = time.monotonic() + 30
        while (first_done is None or second_start is None) and time.monotonic() < deadline:
            now = time.monotonic()  # both jobs watched side by side, not one after the other
            if first_done is None and first.state == "done":
                first_done = now
            if second_start is None and second.events:
                second_start = now
            time.sleep(0.01)
        self.assertIsNotNone(first_done)
        self.assertIsNotNone(second_start)
        self.assertGreaterEqual(second_start, first_done)

    def test_stop_while_queued_ends_the_job_without_running(self) -> None:
        first = self.runs.create("loop")
        second = self.runs.create("tick")
        self.runs.stop(second.id)
        events = collect(second, 5)
        self.assertEqual([n for n, _, _ in events], ["done"])
        self.assertTrue(events[0][1]["stopped"])
        self.runs.stop(first.id)
        collect(first, 5)

    def test_bad_run_options_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            self.runs.create("tick", profile_override="slow")
        with self.assertRaises(ValueError):
            self.runs.create("tick", span_meter="perf")


def phase_of(events, phase: str) -> dict:
    return next(d for n, d, _ in events if n == "phase" and d["phase"] == phase)


@needs_fixture
class LongRunTest(unittest.TestCase):
    """070-06: long profile, build kinds, span aggregation, trace budget."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_long_profile_uses_the_lesson_timeout(self) -> None:  # AC-1
        runs = fixture_manager(self.tmp, profile="long", timeout=30)
        start = time.monotonic()
        events = collect(runs.create("sleep25"), 60)
        elapsed = time.monotonic() - start
        run = done_of(events)["run"]
        self.assertEqual((run["exitCode"], run["timedOut"]), (0, False))
        self.assertGreaterEqual(elapsed, 25.0)
        self.assertEqual(text(events, "stdout"), "slept\n")
        self.assertEqual((phase_of(events, "run")["profile"], phase_of(events, "run")["limitSec"]), ("long", 30))

        start = time.monotonic()  # the same lesson with the quick toggle
        events = collect(runs.create("sleep25", profile_override="quick"), 30)
        elapsed = time.monotonic() - start
        self.assertTrue(done_of(events)["run"]["timedOut"])
        self.assertGreaterEqual(elapsed, 10.0)
        self.assertLess(elapsed, 12.0)
        run_phase = phase_of(events, "run")
        self.assertEqual((run_phase["profile"], run_phase["requested"], run_phase["limitSec"]), ("quick", "long", 10))

    def test_build_type_follows_profile_and_manifest(self) -> None:  # AC-2
        cases = [  # (manifest profile, [run] build, override) -> buildType, preset
            (("quick", None, None), ("Debug", runner.PRESET)),
            (("long", None, None), ("RelWithDebInfo", runner.RELEASE_PRESET)),
            (("long", "debug", None), ("Debug", runner.PRESET)),
            (("quick", None, "long"), ("RelWithDebInfo", runner.RELEASE_PRESET)),
            (("quick", "release", None), ("RelWithDebInfo", runner.RELEASE_PRESET)),
        ]
        for (profile, build, override), (build_type, preset) in cases:
            with self.subTest(profile=profile, build=build, override=override):
                dirs: list[Path] = []
                runs = fixture_manager(self.tmp, profile=profile, build=build, seen_dirs=dirs)
                events = collect(runs.create("crash", profile_override=override), 30)
                self.assertEqual(phase_of(events, "run")["buildType"], build_type)
                self.assertEqual(dirs, [runner.ROOT / "out" / "build" / preset])
        presets = json.loads((runner.ROOT / "CMakePresets.json").read_text(encoding="utf-8"))
        configure = {p["name"]: p for p in presets["configurePresets"]}
        self.assertEqual(configure[runner.RELEASE_PRESET]["inherits"], "linux-x64-relwithdebinfo")
        self.assertEqual(configure[runner.RELEASE_PRESET]["cacheVariables"], configure[runner.PRESET]["cacheVariables"])
        self.assertIn(runner.RELEASE_PRESET, {p["name"] for p in presets["buildPresets"]})

    def test_span_rows_arrive_while_running(self) -> None:  # AC-3
        runs = fixture_manager(self.tmp)
        events, spans = collect_updates(runs.create("span_tick"), 30)
        done_at = events[-1][2]
        increases = []  # arrival times at which the "tick" count went up, before done
        last = 0
        for payload, at in spans:
            for row in payload["rows"]:
                if row["label"] == "tick" and row["count"] > last and at < done_at:
                    increases.append(at)
                    last = row["count"]
        self.assertGreaterEqual(len(increases), 3)
        self.assertGreaterEqual(increases[2] - increases[0], 1.5)  # spread over seconds, not one burst
        self.assertFalse([e for n, d, _ in events if n == "trace" for e in d["events"]], "span lines leaked into trace")

    def test_final_snapshot_equals_span_stats(self) -> None:  # AC-4
        runs = fixture_manager(self.tmp)
        events, spans = collect_updates(runs.create("span_tick"), 30)
        self.assertEqual(done_of(events)["run"]["exitCode"], 0)
        final, _ = spans[-1]
        self.assertTrue(final["full"])
        expected = {(runner.repo_relative(runner.ROOT, runs.build_dir, s["file"]), s["line"], s["label"], s["meter"]):
                    (s["count"], s["totalNs"], s["minNs"], s["maxNs"]) for s in stats_lines(text(events, "stdout"))}
        got = {(r["file"], r["line"], r["label"], r["meter"]): (r["count"], r["totalNs"], r["minNs"], r["maxNs"])
               for r in final["rows"]}
        self.assertEqual(len(expected), 2)  # tick (wall) and io (perf)
        self.assertEqual(got, expected)
        self.assertEqual(final["spanLines"], 10)
        self.assertTrue(all(file == "tests/playground/playground_fixture.cpp" for file, _, _, _ in got))

    def test_span_meter_option_reaches_the_program(self) -> None:  # §2.1 spanMeter
        runs = fixture_manager(self.tmp)
        _, spans = collect_updates(runs.create("span_tick", span_meter="cpu"), 30)
        meters = {r["label"]: r["meter"] for r in spans[-1][0]["rows"]}
        self.assertEqual(meters, {"tick": "cpu", "io": "perf"})

    def test_span_flood_keeps_memory_flat(self) -> None:  # AC-7
        # AC-7 is about the server (memory, update gaps). A sanitizer-built fixture writes spans far
        # slower than 100,000/s and would only hit the time limit; the evidence is the plain build.
        info = subprocess.run([*LAUNCHER, FIXTURE, "build_info"], capture_output=True, text=True, timeout=30).stdout
        if info.strip() == "sanitized":
            self.skipTest("sanitizer-built fixture cannot reach 100,000 spans/s (AC-7 runs on linux-x64-debug)")
        runs = fixture_manager(self.tmp, profile="long", timeout=180)
        before = rss_bytes()
        peak = [before]
        job = runs.create("span_flood")
        events, spans = collect_updates(job, 240, lambda: peak.append(max(peak.pop(), rss_bytes())))
        after = peak[0]  # the highest RSS seen while the run went, not only at the end
        run = done_of(events)["run"]
        self.assertEqual((run["exitCode"], run["traceLimit"]), (0, False))
        flooded = int(text(events, "stdout").split()[-1])
        self.assertEqual(flooded, 3_000_000)
        final = spans[-1][0]
        self.assertTrue(final["full"])
        self.assertEqual([r["count"] for r in final["rows"]], [flooded])
        self.assertEqual(final["spanLines"], flooded)
        # the run's event list does not grow with the spans: phases, a few stdout chunks, done
        self.assertLess(len(job.events), 50, [n for n, _ in job.events])
        self.assertFalse([n for n, _ in job.events if n == "trace"])
        run_start = phase_of(events, "run")
        start_at = next(t for n, d, t in events if d is run_start)
        times = [start_at] + [t for _, t in spans if t < events[-1][2]]
        gaps = [b - a for a, b in zip(times, times[1:])]
        print(f"\n  AC-7: run {events[-1][2] - start_at:.1f} s, {len(spans)} span updates, longest pause "
              f"{max(gaps):.2f} s, RSS +{(after - before) / (1 << 20):.1f} MiB, events kept {len(job.events)}",
              file=sys.stderr)
        self.assertLessEqual(max(gaps), 0.5, f"longest pause between span updates {max(gaps):.2f} s")
        self.assertLess(after - before, 50 << 20, f"RSS grew by {(after - before) >> 20} MiB")

    def test_trace_budget_stops_the_run(self) -> None:  # AC-10
        small = {"quick": runner.Limits(build_sec=120, run_sec=10, output_bytes=1 << 20,
                                        trace_bytes=2 << 20, combined_output=False)}
        runs = fixture_manager(self.tmp, profiles=small)
        pattern = str(Path(tempfile.gettempdir()) / "atugcc_trace_*.jsonl")
        before = set(glob.glob(pattern))
        start = time.monotonic()
        events, spans = collect_updates(runs.create("span_flood"), 30)
        run = done_of(events)["run"]
        self.assertTrue(run["traceLimit"])
        self.assertFalse(run["timedOut"] or run["stopped"])
        self.assertEqual(run["signal"], "SIGKILL")
        self.assertLess(time.monotonic() - start, 8.0)
        self.assertTrue(spans and spans[-1][0]["full"] and spans[-1][0]["rows"][0]["count"] > 0)
        self.assertEqual(set(glob.glob(pattern)) - before, set())
        self.assertEqual(processes_matching(f"{FIXTURE} span_flood"), [])


class SpanAggregatorTest(unittest.TestCase):  # 070-06 AC-9
    @staticmethod
    def span(dur, label: str = "a", **extra) -> dict:
        return {"file": "f.cpp", "line": 3, "label": label, "meter": "wall", "durNs": dur, **extra}

    def test_exact_count_total_min_max(self) -> None:
        agg = SpanAggregator(seed=1)
        for dur in (5, 1, 9, 3):
            self.assertTrue(agg.add(self.span(dur)))
        (row,) = agg.snapshot()
        self.assertEqual((row["count"], row["totalNs"], row["minNs"], row["maxNs"]), (4, 18, 1, 9))
        self.assertEqual((row["file"], row["line"], row["label"], row["meter"]), ("f.cpp", 3, "a", "wall"))

    def test_percentiles_from_a_bounded_uniform_sample(self) -> None:
        # Fixed seed (spec AC-9). With 1024 samples the p50 sampling spread is about ±190 here, so
        # ±5 % of the median holds for most seeds but not all (testrecord); the bias test below
        # is what shows the sampler is uniform.
        values = list(range(1, 10001))
        random.Random(1).shuffle(values)
        agg = SpanAggregator(seed=3)
        for value in values:
            agg.add(self.span(value))
        self.assertEqual(len(agg.entries[("f.cpp", 3, "a", "wall")].sample), 1024)
        (row,) = agg.snapshot()
        self.assertAlmostEqual(row["p50Ns"], 5000, delta=250)
        self.assertAlmostEqual(row["p95Ns"], 9500, delta=475)
        self.assertEqual((row["count"], row["totalNs"], row["minNs"], row["maxNs"]), (10000, 50005000, 1, 10000))
        self.assertEqual(sum(row["hist"]["bins"]), 1024)
        self.assertEqual(len(row["hist"]["bins"]), 20)

    def test_reservoir_is_not_biased_toward_early_or_late_values(self) -> None:
        # In arrival order 1..2000 a sampler that keeps the first (or the last) 1024 values has a
        # mean near 512 (or 1489); a uniform one near 1000.5, sd of the average over 60 runs ≈ 1.6.
        means = []
        for seed in range(60):
            agg = SpanAggregator(seed=seed)
            for value in range(1, 2001):
                agg.add(self.span(value))
            sample = agg.entries[("f.cpp", 3, "a", "wall")].sample
            means.append(sum(sample) / len(sample))
        self.assertAlmostEqual(sum(means) / len(means), 1000.5, delta=10)

    def test_drain_returns_only_changed_keys(self) -> None:
        agg = SpanAggregator(seed=1)
        agg.add(self.span(1, "a"))
        agg.add(self.span(1, "b"))
        self.assertEqual([r["label"] for r in agg.drain()], ["a", "b"])
        agg.add(self.span(2, "a"))
        self.assertEqual([(r["label"], r["count"]) for r in agg.drain()], [("a", 2)])
        self.assertEqual(agg.drain(), [])
        self.assertEqual(len(agg.snapshot()), 2)

    def test_meter_is_part_of_the_key(self) -> None:
        agg = SpanAggregator(seed=1)
        agg.add(self.span(1))
        agg.add(self.span(1, meter="cpu"))
        agg.add(self.span(1, meter="hw-counter"))  # unknown meters are kept as they are
        self.assertEqual(sorted(r["meter"] for r in agg.snapshot()), ["cpu", "hw-counter", "wall"])

    def test_bad_lines_are_refused(self) -> None:
        agg = SpanAggregator(seed=1)
        for bad in ({"file": "f.cpp", "line": 3, "label": "a", "meter": "wall"},  # no durNs
                    self.span(-1), self.span(True), self.span(1.5), self.span("1"),
                    self.span(1, line=True), self.span(1, line=-1), self.span(1, label=None), self.span(1, file=7)):
            self.assertFalse(agg.add(bad), bad)
        self.assertEqual((agg.lines, agg.snapshot()), (0, []))

    def test_single_value_histogram(self) -> None:
        agg = SpanAggregator(seed=1)
        for _ in range(3):
            agg.add(self.span(0))
        (row,) = agg.snapshot()
        self.assertEqual(row["hist"], {"loNs": 0, "hiNs": 0, "bins": [3]})
        self.assertEqual((row["p50Ns"], row["p95Ns"]), (0, 0))


class TraceAndDiagnosticsTest(unittest.TestCase):
    @staticmethod
    def trace_runner() -> runner.RunManager:
        runs = runner.RunManager.__new__(runner.RunManager)  # only _trace's fields
        runs.root = Path("/x")
        return runs

    def test_bad_trace_lines_are_counted_and_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            path.write_text('{"v":1,"kind":"node","seq":1,"file":"/x/y.cpp"}\nnot json\n{"no":"kind"}\n'
                            '{"v":1,"kind":"diagram","source":"graph TD"}\n{"v":1,"kind":"mess', encoding="utf-8")
            runs = self.trace_runner()
            job = runner.Job(runner.LessonInfo("t", Path(tmp), "quick"))
            state, tail = runner._TraceState(build_dir=Path("/x/out"), limit_bytes=1 << 30), runner.TraceTail(path)
            self.assertFalse(runs._trace(job, tail, state, False))
            self.assertEqual(state.skipped, 2)  # the cut last line waits for more data
            self.assertEqual(job.events[0][1]["events"][0]["file"], "y.cpp")
            self.assertEqual(len(state.diagrams), 1)
            runs._trace(job, tail, state, True)
            self.assertEqual(state.skipped, 3)

    def test_span_lines_are_aggregated_not_sent(self) -> None:  # 070-06 §2.1
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            span = '{"v":1,"kind":"span","seq":%d,"tracer":1,"label":"s","meter":"wall","durNs":%d,"thread":1,"file":"/x/a.cpp","line":4,"func":"f","tUs":1}\n'
            path.write_text(span % (1, 10) + span % (2, 30) + '{"v":1,"kind":"span","label":"no file"}\n'
                            '{"v":1,"kind":"node","seq":3,"file":"/x/a.cpp"}\n', encoding="utf-8")
            runs = self.trace_runner()
            job = runner.Job(runner.LessonInfo("t", Path(tmp), "quick"))
            state = runner._TraceState(build_dir=Path("/x/out"), limit_bytes=1 << 30)
            runs._trace(job, runner.TraceTail(path), state, True)
            self.assertEqual([n for n, _ in job.events], ["trace"])
            self.assertEqual([e["kind"] for e in job.events[0][1]["events"]], ["node"])
            self.assertEqual(state.skipped, 1)
            _, _, payload, seen = job.updates_from(1, 0, 0)
            self.assertEqual(seen, 1)
            self.assertFalse(payload["full"])
            (row,) = payload["rows"]
            self.assertEqual((row["file"], row["line"], row["count"], row["totalNs"]), ("a.cpp", 4, 2, 40))
            self.assertEqual(payload["spanLines"], 2)
            self.assertEqual(job.updates_from(1, seen, 0)[2], None)  # nothing new for this reader
            job.emit("done", {})
            _, _, payload, _ = job.updates_from(1, seen, 0)
            self.assertTrue(payload["full"])  # the batch that ends the run carries every row

    def test_reads_are_bounded_and_the_budget_is_reported(self) -> None:  # 070-06 Assumptions 9, 10
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            path.write_text('{"v":1,"kind":"node","seq":1,"file":"/x/a.cpp"}\n' * 100, encoding="utf-8")
            size = path.stat().st_size
            runs = self.trace_runner()
            job = runner.Job(runner.LessonInfo("t", Path(tmp), "quick"))
            state = runner._TraceState(build_dir=Path("/x/out"), limit_bytes=size - 1)
            tail = runner.TraceTail(path, limit=size // 4)
            with unittest.mock.patch.object(runner, "TRACE_TICK_SEC", 0):  # no time left for a second piece
                self.assertTrue(runs._trace(job, tail, state, False))  # over the budget
            self.assertEqual(tail.offset, size // 4)  # pieces of at most `limit` bytes
            self.assertFalse(tail.at_end)
            runs._trace(job, tail, state, True)  # the final read drains the rest
            self.assertEqual(tail.offset, size)
            self.assertEqual(sum(len(d["events"]) for n, d in job.events if n == "trace"), 100)

            behind = runner.TraceTail(path, limit=size // 4)
            runs._trace(runner.Job(job.lesson), behind, runner._TraceState(build_dir=Path("/x/out"), limit_bytes=size),
                        False)
            self.assertEqual(behind.offset, size)  # with time left, a tick that is behind reads on

    def test_a_line_longer_than_a_read_is_dropped_not_kept(self) -> None:  # bounded memory (Assumption 5)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            node = '{"v":1,"kind":"node","seq":%d,"file":"/x/a.cpp"}\n'
            path.write_text(node % 1 + "x" * 1000 + "\n" + node % 2 + "y" * 300, encoding="utf-8")
            runs = self.trace_runner()
            job = runner.Job(runner.LessonInfo("t", Path(tmp), "quick"))
            state = runner._TraceState(build_dir=Path("/x/out"), limit_bytes=1 << 30)
            tail = runner.TraceTail(path, limit=100)
            while not tail.at_end or tail.offset == 0:
                runs._trace(job, tail, state, False)
                self.assertLessEqual(len(tail.partial), 100)
            runs._trace(job, tail, state, True)
            seqs = [e["seq"] for n, d in job.events if n == "trace" for e in d["events"]]
            self.assertEqual(seqs, [1, 2])  # the lines around the long one survive
            self.assertEqual(state.skipped, 2)  # the 1000-byte line and the 300-byte unfinished tail

    def test_gcc_diagnostics_become_repo_relative(self) -> None:
        root = Path("/repo")
        log = ("/repo/lessons/a/main.cpp: In function 'int main()':\n"
               "/repo/lessons/a/main.cpp:7:5: error: 'foo' was not declared in this scope\n"
               "../../../lessons/units/u/u.hpp:3:1: warning: unused [-Wunused]\n"
               "/usr/include/c++/13/bits/x.h:10:2: note: declared here\n"
               "lessons/a/main.cpp:1:10: fatal error: nope.hpp: No such file or directory\n")
        diags = runner.parse_diagnostics(log, root, root / "out" / "build" / "p")
        self.assertEqual([(d["file"], d["line"], d["col"], d["severity"]) for d in diags], [
            ("lessons/a/main.cpp", 7, 5, "error"),
            ("lessons/units/u/u.hpp", 3, 1, "warning"),
            ("/usr/include/c++/13/bits/x.h", 10, 2, "note"),
            ("out/build/p/lessons/a/main.cpp", 1, 10, "error"),
        ])
        self.assertEqual(diags[0]["message"], "'foo' was not declared in this scope")


# --- HTTP server (AC-3, AC-9, AC-11, AC-12) ------------------------------------------------------
class ServerCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "repo"
        self.root.mkdir()
        make_tree(self.root)
        (self.tmp / "dist").mkdir()
        (self.tmp / "dist" / "index.html").write_text("<!doctype html><title>t</title>", encoding="utf-8")
        runs = fixture_manager(self.tmp) if FIXTURE and POSIX else runner.RunManager(self.root, build=False)
        self.server = server.make_server(0, root=self.root, dist=self.tmp / "dist", runs=runs)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def request(self, method: str, path: str, body=None, headers: dict | None = None) -> tuple[int, dict | str]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = {"Host": f"127.0.0.1:{self.port}"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            hdrs["Content-Type"] = "application/json"
        hdrs.update(headers or {})
        conn.request(method, path, body=data, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read().decode()
        conn.close()
        try:
            return resp.status, json.loads(raw)
        except ValueError:
            return resp.status, raw


class ServerTest(ServerCase):
    def test_binds_loopback_only(self) -> None:  # AC-9
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("192.0.2.1", 9))  # no packet is sent; picks the outgoing interface
            other = probe.getsockname()[0]
        except OSError:
            other = None
        finally:
            probe.close()
        if not other or other.startswith("127."):
            self.skipTest("no non-loopback interface")
        with self.assertRaises(OSError):
            socket.create_connection((other, self.port), timeout=2).close()

    def test_encoded_and_plain_escapes_over_http(self) -> None:  # AC-3
        for query in ("%2e%2e/README.md", "%2E%2E%2Foutside.txt", "lessons%2F..%2F..%2Foutside.txt",
                      "%2Fetc%2Fpasswd", "lessons/a/main.cpp%00.md", ".git/config"):
            with self.subTest(query=query):
                status, _ = self.request("GET", f"/api/files?path={query}")
                self.assertEqual(status, 400)
        status, _ = self.request("PUT", "/api/files?path=include/x.hpp", {"content": "x", "baseSha": None})
        self.assertEqual(status, 403)
        status, _ = self.request("GET", "/%2e%2e/%2e%2e/etc/passwd")
        self.assertEqual(status, 400)

    def test_file_round_trip_and_conflict(self) -> None:  # AC-4 over HTTP
        status, opened = self.request("GET", "/api/files?path=lessons/a/crlf.cpp")
        self.assertEqual((status, opened["eol"], opened["writable"]), (200, "crlf", True))
        status, saved = self.request("PUT", "/api/files?path=lessons/a/crlf.cpp",
                                     {"content": opened["content"] + "int w;\n", "baseSha": opened["sha"]})
        self.assertEqual(status, 200)
        status, conflict = self.request("PUT", "/api/files?path=lessons/a/crlf.cpp",
                                        {"content": "lost\n", "baseSha": opened["sha"]})
        self.assertEqual(status, 409)
        self.assertEqual(conflict["sha"], saved["sha"])
        self.assertTrue(conflict["content"].endswith("int w;\n"))
        self.assertTrue((self.root / "lessons" / "a" / "crlf.cpp").read_bytes().endswith(b"int w;\r\n"))

    def test_requests_from_other_sites_are_refused(self) -> None:
        self.assertEqual(self.request("GET", "/api/health", headers={"Host": "evil.example:80"})[0], 403)
        self.assertEqual(self.request("POST", "/api/runs", {"lesson": "tick"},
                                      headers={"Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.request("PUT", "/api/files?path=lessons/a/main.cpp", None,
                                      headers={"Content-Type": "text/plain", "Content-Length": "0"})[0], 415)
        self.assertEqual(self.request("GET", "/api/health", headers={"Origin": f"http://localhost:{self.port}"})[0], 200)

    def test_bad_run_options_are_400(self) -> None:  # 070-06 §2.1
        for body in ({"lesson": "x", "profileOverride": "slow"}, {"lesson": "x", "spanMeter": "perf"},
                     {"lesson": "x", "profileOverride": 1}):
            status, data = self.request("POST", "/api/runs", body)
            self.assertEqual(status, 400, (body, data))
        self.assertEqual(self.request("GET", "/api/health")[1]["releasePreset"], runner.RELEASE_PRESET)

    def test_static_and_unknown_routes(self) -> None:
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("<title>t</title>", body)
        self.assertEqual(self.request("GET", "/api/nope")[0], 404)
        self.assertEqual(self.request("POST", "/api/runs", {"lesson": 3})[0], 400)


class LessonsApiTest(unittest.TestCase):
    def test_seed_lessons_and_units_are_listed(self) -> None:  # AC-1 (data side)
        srv = server.make_server(0, runs=runner.RunManager(runner.ROOT, build=False))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=30)
            conn.request("GET", "/api/lessons", headers={"Host": f"127.0.0.1:{srv.server_address[1]}"})
            data = json.loads(conn.getresponse().read())
            conn.close()
        finally:
            srv.shutdown()
            srv.server_close()
        lessons = [l["id"] for t in data["tracks"] for l in t["lessons"]]
        self.assertEqual(lessons, ["lambda_capture", "thread_and_log", "span_timing", "device_state_machine"])
        self.assertEqual([u["id"] for u in data["units"]], ["jthread_worker", "lambda_capture"])
        self.assertEqual(data["problems"], [])


@needs_fixture
class StreamTest(ServerCase):
    def start_run(self, lesson: str) -> str:
        status, body = self.request("POST", "/api/runs", {"lesson": lesson})
        self.assertEqual(status, 202, body)
        return body["runId"]

    def open_stream(self, run_id: str) -> tuple[http.client.HTTPConnection, http.client.HTTPResponse]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request("GET", f"/api/runs/{run_id}/stream", headers={"Host": f"127.0.0.1:{self.port}"})
        resp = conn.getresponse()
        self.assertEqual(resp.getheader("Content-Type"), "text/event-stream; charset=utf-8")
        return conn, resp

    @staticmethod
    def read_events(resp: http.client.HTTPResponse):
        """Yield (event, data, arrival time) as the SSE frames arrive."""
        name, data = None, None
        while True:
            line = resp.fp.readline()
            if not line:
                return
            line = line.decode().rstrip("\n")
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
            elif line == "" and name is not None:
                yield name, data, time.monotonic()
                name, data = None, None

    def test_lines_arrive_while_the_lesson_runs(self) -> None:  # AC-11
        conn, resp = self.open_stream(self.start_run("tick"))
        events = list(self.read_events(resp))
        conn.close()
        self.assertEqual(events[0][0], "phase")
        self.assertEqual(events[-1][0], "done")
        stdout_times = [t for n, _, t in events if n == "stdout"]
        self.assertGreaterEqual(len(stdout_times), 4)
        self.assertGreaterEqual(len({round(t, 1) for t in stdout_times}), 4)
        self.assertGreater(events[-1][2] - stdout_times[0], 3.0)

    def test_stop_over_http(self) -> None:  # AC-12
        run_id = self.start_run("loop")
        conn, resp = self.open_stream(run_id)
        stream = self.read_events(resp)
        self.assertEqual(next(stream)[0], "phase")
        time.sleep(0.5)
        start = time.monotonic()
        self.assertEqual(self.request("POST", f"/api/runs/{run_id}/stop", {})[0], 200)
        rest = list(stream)
        conn.close()
        self.assertLess(rest[-1][2] - start, 1.0)
        self.assertEqual(rest[-1][0], "done")
        self.assertTrue(rest[-1][1]["stopped"])
        self.assertEqual(processes_matching(f"{FIXTURE} loop"), [])

    def test_closing_the_stream_stops_the_run(self) -> None:  # AC-12
        run_id = self.start_run("loop")
        conn, resp = self.open_stream(run_id)
        next(self.read_events(resp))
        time.sleep(0.3)
        start = time.monotonic()
        resp.close()  # the response owns the socket of a Connection: close stream
        conn.close()
        events = collect(self.server.runs.get(run_id), 5)
        self.assertLess(time.monotonic() - start, 1.0)
        self.assertTrue(done_of(events)["stopped"])
        time.sleep(0.1)
        self.assertEqual(processes_matching(f"{FIXTURE} loop"), [])

    def test_spans_stream_ends_on_the_full_aggregate(self) -> None:  # 070-06 §2.2
        status, body = self.request("POST", "/api/runs", {"lesson": "span_tick", "spanMeter": "wall"})
        self.assertEqual(status, 202, body)
        conn, resp = self.open_stream(body["runId"])
        events = list(self.read_events(resp))
        conn.close()
        names = [n for n, _, _ in events]
        self.assertEqual(names[-1], "done")
        last = max(i for i, n in enumerate(names) if n == "spans")  # the final batch: spans, then its events
        self.assertTrue(events[last][1]["full"])
        self.assertNotIn("spans", names[last + 1:])
        self.assertEqual({r["label"] for r in events[last][1]["rows"]}, {"tick", "io"})
        partial = [d for n, d, t in events[:last] if n == "spans"]
        self.assertTrue(partial and not any(d["full"] for d in partial))
        self.assertEqual(phase_of(events, "run")["buildType"], "Debug")

    def test_late_stream_gets_every_event_from_the_start(self) -> None:
        run_id = self.start_run("trace")
        job = self.server.runs.get(run_id)
        collect(job, 30)
        conn, resp = self.open_stream(run_id)
        events = list(self.read_events(resp))
        conn.close()
        self.assertEqual([n for n, _, _ in events], [n for n, _ in job.events])


def main() -> int:
    global FIXTURE, LAUNCHER
    argv = sys.argv[1:]
    launcher: list[str] = []
    if "--" in argv:  # everything after -- prefixes the fixture (setarch x86_64 -R under TSan)
        launcher = argv[argv.index("--") + 1:]
        argv = argv[:argv.index("--")]
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--fixture")
    args, rest = parser.parse_known_args(argv)
    if args.fixture:
        FIXTURE = str(Path(args.fixture).resolve())
        LAUNCHER = launcher
    result = unittest.main(argv=[sys.argv[0], *rest], exit=False).result
    if not FIXTURE:
        print("note: run tests skipped (no --fixture); CTest test PlaygroundServer runs them", file=sys.stderr)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
