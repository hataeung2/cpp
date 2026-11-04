#!/usr/bin/env python3
"""Tests for tools/playground.py ports and the WSL reach check (specs 070-02-01, 070-02-02). Run: py -3 tools/test_playground.py

The launch tests start the real playground (the API server in WSL on Windows) with
--no-frontend-build; they are skipped when node_modules or dist/ is missing.
"""
from __future__ import annotations

import io
import json
import os
import queue
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.error
import urllib.request
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import playground  # noqa: E402

SCRIPT = playground.ROOT / "tools" / "playground.py"


def hold_port() -> socket.socket:
    """A listening socket on a free 127.0.0.1 port (close it when done)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    return sock


def can_run_server() -> bool:
    return shutil.which("wsl.exe") is not None if playground.on_windows() else shutil.which("python3") is not None


class FreePortTest(unittest.TestCase):
    def test_returns_the_first_port_when_free(self) -> None:
        with hold_port() as sock:
            port = sock.getsockname()[1]
        self.assertEqual(playground.free_port(port, 1), port)

    def test_skips_a_busy_port(self) -> None:
        with hold_port() as sock:
            port = sock.getsockname()[1]
            found = playground.free_port(port, 5)
            self.assertIsNotNone(found)
            self.assertGreater(found, port)

    def test_time_wait_counts_as_free(self) -> None:
        """A port the last run closed (TIME_WAIT) is free for Vite, so the page must not move off it.

        The listener sets SO_REUSEADDR on Linux as Node and server.py do; Linux reuses a TIME_WAIT
        port only when both the old and the new socket set it.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            if not playground.on_windows():
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            with socket.create_connection(("127.0.0.1", port)) as client:
                accepted, _ = listener.accept()
                accepted.close()  # the listening side closes first: its port is left in TIME_WAIT
                client.recv(1)
        self.assertEqual(playground.free_port(port, 1), port)

    def test_none_when_all_busy(self) -> None:
        with hold_port() as sock:
            self.assertIsNone(playground.free_port(sock.getsockname()[1], 1))


class LaunchPlanTest(unittest.TestCase):
    """AC-2, AC-3."""

    def test_serve_mode_leaves_the_port_to_the_server(self) -> None:
        self.assertEqual(playground.launch_plan(None, False), (playground.SERVER_PORT, [], None))
        self.assertEqual(playground.launch_plan(9000, False), (9000, [], None))

    def test_dev_mode_gives_the_port_to_vite_and_any_port_to_the_server(self) -> None:
        with hold_port() as sock:
            port = sock.getsockname()[1]
        server_port, extra, page = playground.launch_plan(port, True)
        self.assertEqual((server_port, page), (0, port))
        self.assertEqual(extra, ["--allow-origin", f"http://127.0.0.1:{port}", "--allow-origin", f"http://localhost:{port}"])

    def test_dev_mode_default_page_port(self) -> None:
        with mock.patch.object(playground, "free_port", side_effect=lambda first: first) as probe:
            self.assertEqual(playground.launch_plan(None, True)[2], playground.DEV_PORT)
        probe.assert_called_once_with(playground.DEV_PORT)

    def test_dev_mode_moves_off_a_busy_page_port(self) -> None:
        with hold_port() as sock:
            port = sock.getsockname()[1]
            _, extra, page = playground.launch_plan(port, True)
        self.assertNotEqual(page, port)
        self.assertIn(f"http://127.0.0.1:{page}", extra)

    def test_serve_mode_port_0_still_reaches_the_server(self) -> None:
        self.assertEqual(playground.launch_plan(0, False), (0, [], None))

    def test_port_out_of_range_is_a_usage_error(self) -> None:
        for args in (["--dev", "--port", "0"], ["--dev", "--port", "65536"], ["--port", "-1"], ["--port", "70000"]):
            with self.subTest(args=args), mock.patch("sys.stderr"), self.assertRaises(SystemExit) as raised, \
                 mock.patch.object(playground, "launch_plan", side_effect=AssertionError("went past the check")):
                playground.main([*args, "--no-frontend-build"])
            self.assertEqual(raised.exception.code, 2)

    def test_free_port_stops_at_65535(self) -> None:
        def busy(address: tuple[str, int]) -> None:  # the real bind raises OverflowError above 65535
            raise OverflowError("port must be 0-65535") if address[1] > 65535 else OSError("in use")

        with mock.patch("socket.socket.bind", side_effect=busy):
            self.assertIsNone(playground.free_port(65530, 20))

    def test_dev_mode_fails_when_all_busy(self) -> None:
        with mock.patch.object(playground, "free_port", return_value=None):
            with self.assertRaises(OSError):
                playground.launch_plan(9000, True)
        with mock.patch.object(playground, "free_port", return_value=None), mock.patch("sys.stderr"):
            self.assertEqual(playground.main(["--dev", "--port", "9000", "--no-frontend-build"]), 1)


class FakeProc:
    """`poll()` gives None until `ends_after` calls, then `code`."""

    def __init__(self, ends_after: int | None, code: int = 0) -> None:
        self.ends_after, self.code, self.polls = ends_after, code, 0

    def poll(self) -> int | None:
        self.polls += 1
        return self.code if self.ends_after is not None and self.polls > self.ends_after else None

    @property
    def returncode(self) -> int | None:
        return self.code if self.ends_after is not None and self.polls > self.ends_after else None


@mock.patch.object(playground.time, "sleep", lambda _: None)
class WaitAnyTest(unittest.TestCase):
    """The launcher ends when either child ends (a Vite that cannot keep its port must not leave it waiting)."""

    def test_server_end_returns_its_code(self) -> None:
        self.assertEqual(playground.wait_any([FakeProc(2, 3), FakeProc(None)]), 3)

    def test_vite_end_is_an_error(self) -> None:
        with mock.patch("sys.stderr"):
            self.assertEqual(playground.wait_any([FakeProc(None), FakeProc(2, 0)]), 1)
            self.assertEqual(playground.wait_any([FakeProc(None), FakeProc(0, 7)]), 7)

    def test_main_stops_both_children_when_vite_ends(self) -> None:
        server, vite = FakeProc(None), FakeProc(1, 1)

        def start_server(port, extra, procs):
            self.assertEqual(port, 0)
            procs.append(server)
            return server, "http://127.0.0.1:40000/"

        with (mock.patch.object(playground, "start_server", start_server),
              mock.patch.object(playground, "reachable", return_value=True),
              mock.patch.object(playground, "free_port", side_effect=lambda first: first),
              mock.patch.object(playground, "npm", return_value="npm"),
              mock.patch.object(playground.subprocess, "Popen", return_value=vite) as popen,
              mock.patch.object(playground, "stop") as stop, mock.patch("sys.stdout"), mock.patch("sys.stderr")):
            self.assertEqual(playground.main(["--dev", "--port", "9000", "--no-frontend-build"]), 1)
        self.assertEqual(popen.call_args.args[0], ["npm", "run", "dev", "--", "--port", "9000"])
        self.assertEqual(popen.call_args.kwargs["env"]["ATUGCC_API_PORT"], "40000")
        self.assertEqual([c.args[0] for c in stop.call_args_list], [server, vite])


class StatusHandler(BaseHTTPRequestHandler):
    status = 200

    def do_GET(self) -> None:
        self.send_response(self.status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args) -> None:
        pass


class ReachableTest(unittest.TestCase):
    """Spec 070-02-02 AC-1, AC-2: the launcher stops with a fix when Windows cannot reach the WSL server."""

    def serve(self, status: int) -> str:
        handler = type("Handler", (StatusHandler,), {"status": status})
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(httpd.shutdown)
        return f"http://127.0.0.1:{httpd.server_address[1]}/api/health"

    def test_any_response_is_reachable(self) -> None:
        for status in (200, 403):
            with self.subTest(status=status):
                self.assertTrue(playground.reachable(self.serve(status), FakeProc(None), wait=5))

    def test_system_proxy_is_not_used(self) -> None:
        with hold_port() as sock:
            dead = f"http://127.0.0.1:{sock.getsockname()[1]}"
        url = self.serve(200)
        with mock.patch.dict(os.environ, {"HTTP_PROXY": dead, "http_proxy": dead, "NO_PROXY": "", "no_proxy": ""}):
            self.assertTrue(playground.reachable(url, FakeProc(None), wait=5))

    def test_a_server_that_answers_late_is_reachable(self) -> None:
        """Forwarding that appears after the first failed attempts (spec 070-02-02 §4)."""
        with hold_port() as sock:
            port = sock.getsockname()[1]
        servers: list[ThreadingHTTPServer] = []

        def start_later() -> None:
            time.sleep(2.5)
            servers.append(ThreadingHTTPServer(("127.0.0.1", port), StatusHandler))
            servers[0].serve_forever()

        threading.Thread(target=start_later, daemon=True).start()
        self.addCleanup(lambda: servers and (servers[0].shutdown(), servers[0].server_close()))
        started = time.monotonic()
        self.assertTrue(playground.reachable(f"http://127.0.0.1:{port}/api/health", FakeProc(None), wait=10))
        self.assertGreaterEqual(time.monotonic() - started, 2.5)

    def test_closed_port_is_unreachable_after_the_wait(self) -> None:
        with hold_port() as sock:
            port = sock.getsockname()[1]
        for wait in (0.3, 3.0):
            with self.subTest(wait=wait):
                started = time.monotonic()
                self.assertFalse(playground.reachable(f"http://127.0.0.1:{port}/api/health", FakeProc(None), wait=wait))
                self.assertGreaterEqual(time.monotonic() - started, wait)
                self.assertLess(time.monotonic() - started, wait + 0.5)  # no attempt starts after the deadline

    def test_server_end_stops_the_wait(self) -> None:
        with hold_port() as sock:
            port = sock.getsockname()[1]
        started = time.monotonic()
        self.assertFalse(playground.reachable(f"http://127.0.0.1:{port}/api/health", FakeProc(0, 3), wait=30))
        self.assertLess(time.monotonic() - started, 5)

    def run_main(self, windows: bool, reach: bool, server: FakeProc,
                 mode: tuple[str, ...] = ("--dev",)) -> tuple[int, str, mock.Mock, mock.Mock, mock.Mock]:
        def start_server(port, extra, procs):
            procs.append(server)
            return server, "http://127.0.0.1:40000/"

        with (mock.patch.object(playground, "start_server", start_server),
              mock.patch.object(playground, "on_windows", return_value=windows),
              mock.patch.object(playground, "reachable", return_value=reach) as check,
              mock.patch.object(playground, "free_port", side_effect=lambda first: first),
              mock.patch.object(playground, "npm", return_value="npm"),
              mock.patch.object(playground.subprocess, "Popen", return_value=FakeProc(0, 0)) as popen,
              mock.patch.object(playground, "wait_any", return_value=0),
              mock.patch.object(playground, "stop") as stop, mock.patch("sys.stdout"),
              mock.patch("sys.stderr", new_callable=io.StringIO) as err):
            code = playground.main([*mode, "--port", "9000", "--no-frontend-build"])
        return code, err.getvalue(), check, popen, stop

    def test_serve_mode_is_checked_too(self) -> None:
        code, err, check, _, _ = self.run_main(True, False, FakeProc(None), mode=())
        self.assertEqual(code, 1)
        self.assertIn('Run "wsl --shutdown"', err)
        check.assert_called_once()

    def test_unreachable_on_windows_stops_before_vite(self) -> None:
        server = FakeProc(None)
        code, err, check, popen, stop = self.run_main(True, False, server)
        self.assertEqual(code, 1)
        self.assertIn("error: Windows cannot reach the API server in WSL at http://127.0.0.1:40000/", err)
        self.assertIn('Run "wsl --shutdown"', err)
        self.assertEqual(check.call_args.args[0], "http://127.0.0.1:40000/api/health")
        popen.assert_not_called()
        self.assertEqual([c.args[0] for c in stop.call_args_list], [server])

    def test_server_that_ended_during_the_check_gives_its_code(self) -> None:
        code, err, _, popen, _ = self.run_main(True, False, FakeProc(0, 5))
        self.assertEqual(code, 5)
        self.assertNotIn("wsl --shutdown", err)
        popen.assert_not_called()

    def test_reachable_on_windows_starts_vite(self) -> None:
        code, _, check, popen, _ = self.run_main(True, True, FakeProc(None))
        self.assertEqual(code, 0)
        check.assert_called_once()
        self.assertEqual(popen.call_args.args[0], ["npm", "run", "dev", "--", "--port", "9000"])

    def test_no_check_on_linux(self) -> None:
        code, _, check, popen, _ = self.run_main(False, False, FakeProc(None))
        self.assertEqual(code, 0)
        check.assert_not_called()
        popen.assert_called_once()


class LaunchTestBase(unittest.TestCase):
    """Start tools/playground.py, wait for the page URL, fetch from it, stop the whole tree."""

    proc: subprocess.Popen | None = None
    output: list[str]

    def launch(self, *args: str, url_prefix: str) -> str:
        if not can_run_server():
            self.skipTest("no WSL / python3 for the API server")
        kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if playground.on_windows() else {"start_new_session": True}
        self.proc = subprocess.Popen([sys.executable, str(SCRIPT), "--no-frontend-build", *args], cwd=playground.ROOT,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     encoding="utf-8", errors="replace", **kwargs)
        self.addCleanup(self.stop)
        self.output = []
        lines: queue.Queue[str] = queue.Queue()
        def read() -> None:
            for line in self.proc.stdout:
                self.output.append(line)
                lines.put(line)
        threading.Thread(target=read, daemon=True).start()
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                self.assertIsNone(self.proc.poll(), "playground.py ended before reporting its page")
                continue
            if line.startswith(url_prefix):
                return line[len(url_prefix):].split()[0]
        self.fail(f"no '{url_prefix}' line within 90 s")

    def stop(self) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is None:
            if playground.on_windows():
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True)
            else:
                os.killpg(self.proc.pid, signal.SIGTERM)
            self.proc.wait(timeout=30)
        self.proc.stdout.close()

    def fetch(self, url: str, wait: float = 30) -> str:
        """GET `url`, retrying while the server behind it is still starting."""
        deadline = time.monotonic() + wait
        while True:
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    return resp.read().decode("utf-8")
            except OSError as exc:
                if time.monotonic() > deadline or self.proc.poll() is not None:
                    self.fail(f"GET {url}: {exc}\nplayground.py output:\n{''.join(self.output)}")
                time.sleep(0.5)

    @staticmethod
    def status(url: str, origin: str) -> int:
        request = urllib.request.Request(url, headers={"Origin": origin})
        try:
            with urllib.request.urlopen(request, timeout=5) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code


class DevLaunchTest(LaunchTestBase):
    """AC-1: --dev --port N puts the hot-reload page on N and proxies /api from there."""

    def test_page_and_api_on_the_given_port(self) -> None:
        if not (playground.FRONTEND / "node_modules" / ".package-lock.json").is_file() or playground.npm() is None:
            self.skipTest("web/frontend/node_modules missing (npm ci)")
        node = shutil.which("node")
        version = subprocess.run([node, "--version"], capture_output=True, text=True).stdout if node else ""
        if not version.startswith("v") or int(version[1:].split(".")[0]) < 20:
            self.skipTest(f"Node.js 20+ needed for Vite (found {version.strip() or 'none'})")
        port = playground.free_port(19000)
        url = self.launch("--dev", "--port", str(port), url_prefix="dev page: ")
        self.assertEqual(url, f"http://127.0.0.1:{port}/")
        self.assertIn("/src/main.ts", self.fetch(url))  # Vite serves the sources, not dist/
        health = json.loads(self.fetch(url + "api/health"))
        self.assertEqual(health["preset"], "linux-x64-playground")
        # AC-2 through the real server: it took any free port and allows this page's origin only
        self.assertEqual(self.status(url + "api/health", f"http://127.0.0.1:{port}"), 200)
        self.assertEqual(self.status(url + "api/health", f"http://localhost:{port}"), 200)
        self.assertEqual(self.status(url + "api/health", "http://127.0.0.1:5173"), 403)
        started = next(line for line in self.output if line.startswith("+ ") and "server.py" in line)
        self.assertEqual(started.split("server.py")[1].split()[:2], ["--port", "0"])


class ServeLaunchTest(LaunchTestBase):
    """AC-4: without --dev, --port N is still the page and API port."""

    def test_page_and_api_on_the_given_port(self) -> None:
        if not (playground.FRONTEND / "dist" / "index.html").is_file():
            self.skipTest("web/frontend/dist missing (npm run build)")
        port = playground.free_port(19100)
        url = self.launch("--port", str(port), url_prefix="atugcc playground: ")
        self.assertEqual(url, f"http://127.0.0.1:{port}/")
        self.assertIn("<html", self.fetch(url).lower())
        self.assertEqual(json.loads(self.fetch(url + "api/health"))["preset"], "linux-x64-playground")


if __name__ == "__main__":
    unittest.main(verbosity=2)
