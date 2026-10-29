#!/usr/bin/env python3
"""Tests for the web playground server (spec 070-02 AC-3, AC-4, AC-5, AC-9, AC-11, AC-12).

    python3 web/server/test_server.py [--fixture <playground_fixture binary>] [unittest args] [-- <launcher prefix...>]

File and request-guard tests run on any host. Run tests need Linux and the fixture program
(tests/playground/playground_fixture.cpp); CTest passes it (test PlaygroundServer):
    py -3 .agent/scripts/build.py --preset linux-x64-debug --test
Without --fixture those tests are skipped and the summary says so.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import runner  # noqa: E402
import server  # noqa: E402
from files import Conflict, PathError, RepoFiles  # noqa: E402

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


def fixture_manager(tmp: Path) -> runner.RunManager:
    return runner.RunManager(
        runner.ROOT, build=False,
        lesson_info=lambda lesson_id: runner.LessonInfo(lesson_id, tmp, "quick"),
        executable=lambda info: [*LAUNCHER, FIXTURE, info.id])


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


class TraceAndDiagnosticsTest(unittest.TestCase):
    def test_bad_trace_lines_are_counted_and_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            path.write_text('{"v":1,"kind":"node","seq":1,"file":"/x/y.cpp"}\nnot json\n{"no":"kind"}\n'
                            '{"v":1,"kind":"diagram","source":"graph TD"}\n{"v":1,"kind":"mess', encoding="utf-8")
            runs = runner.RunManager.__new__(runner.RunManager)  # only _trace's fields
            runs.root, runs.build_dir = Path("/x"), Path("/x/out")
            job = runner.Job(runner.LessonInfo("t", Path(tmp), "quick"))
            state, tail = {"diagrams": [], "skipped": 0}, runner.TraceTail(path)
            runs._trace(job, tail, state, False)
            self.assertEqual(state["skipped"], 2)  # the cut last line waits for more data
            self.assertEqual(job.events[0][1]["events"][0]["file"], "y.cpp")
            self.assertEqual(len(state["diagrams"]), 1)
            runs._trace(job, tail, state, True)
            self.assertEqual(state["skipped"], 3)

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
        self.assertEqual(lessons, ["lambda_capture", "thread_and_log", "device_state_machine"])
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
