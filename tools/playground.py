#!/usr/bin/env python3
"""Start the local web playground (specs 070-02, 070-02-01).

Usage:
    py -3 tools/playground.py [--port N] [--open] [--dev] [--no-frontend-build]   (Linux: python3)

- Builds the frontend with the host's Node when needed (`npm ci` when node_modules is missing
  or older than package-lock.json, `npm run build` when dist/ is older than its sources).
- Starts web/server/server.py: in WSL on a Windows host (distribution: ATUGCC_WSL_DISTRO, else
  the default, as in .agent/scripts/build.py), directly on Linux. The server listens on
  127.0.0.1 only; WSL2 forwards localhost, so the Windows browser reaches it.
- --port: the page's port (default 8765, with --dev 5173); a busy port moves on to the next
  free one of 20.
- --dev: the page comes from the Vite dev server (hot reload) on that port, which proxies /api
  to the API server; the API server then takes any free port.
- --open: opens the page in the default browser once the server is up.
Ctrl+C stops everything.
"""
from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "web" / "frontend"
SERVER_PORT = 8765
DEV_PORT = 5173
PORT_TRIES = 20  # as web/server/server.py
READY_RE = re.compile(r"atugcc playground: (http://127\.0\.0\.1:(\d+)/)")
FRONTEND_INPUTS = ("index.html", "package.json", "package-lock.json", "vite.config.ts", "tsconfig.json")


def on_windows() -> bool:
    return platform.system() == "Windows"


def newest_mtime(paths: list[Path]) -> float:
    times = [p.stat().st_mtime for p in paths if p.is_file()]
    return max(times) if times else 0.0


def needs_install(frontend: Path = FRONTEND) -> bool:
    marker = frontend / "node_modules" / ".package-lock.json"  # written by npm ci / install
    return not marker.is_file() or marker.stat().st_mtime < (frontend / "package-lock.json").stat().st_mtime


def needs_build(frontend: Path = FRONTEND) -> bool:
    built = frontend / "dist" / "index.html"
    if not built.is_file():
        return True
    inputs = [frontend / name for name in FRONTEND_INPUTS] + list((frontend / "src").rglob("*"))
    return newest_mtime(inputs) > built.stat().st_mtime


def npm() -> str | None:
    return shutil.which("npm.cmd" if on_windows() else "npm") or shutil.which("npm")


def build_frontend(dev: bool) -> int:
    tool = npm()
    if tool is None:
        print("error: npm not found; install Node.js 20+ (spec 070-02 §7)", file=sys.stderr)
        return 2
    steps = []
    if needs_install():
        steps.append([tool, "ci", "--no-audit", "--no-fund"])
    if not dev and needs_build():
        steps.append([tool, "run", "build"])
    for step in steps:
        print("+ npm " + " ".join(step[1:]), flush=True)
        code = subprocess.run(step, cwd=FRONTEND).returncode
        if code != 0:
            return code
    return 0


def free_port(first: int, tries: int = PORT_TRIES) -> int | None:
    """The first of `tries` ports from `first` that 127.0.0.1 can bind now, or None.

    Same socket options as Vite's own bind: on Linux libuv sets SO_REUSEADDR, so a port left in
    TIME_WAIT by the last run counts as free; Windows uses the defaults.
    """
    for port in range(first, min(first + tries, 65536)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if not on_windows():
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    return None


def launch_plan(port: int | None, dev: bool) -> tuple[int, list[str], int | None]:
    """(server port, extra server arguments, Vite port or None) for `--port` and `--dev`.

    Without --dev the server serves the page and finds a free port itself. With --dev the page
    is Vite's; the server takes any free port (port 0), reached only through the Vite proxy.
    """
    if not dev:
        return SERVER_PORT if port is None else port, [], None
    first = DEV_PORT if port is None else port
    page = free_port(first)
    if page is None:
        raise OSError(f"ports {first}..{first + PORT_TRIES - 1} are all in use")
    origins = [f"http://127.0.0.1:{page}", f"http://localhost:{page}"]
    return 0, [arg for origin in origins for arg in ("--allow-origin", origin)], page


def server_command(port: int, extra: list[str]) -> list[str]:
    args = ["web/server/server.py", "--port", str(port), *extra]
    if not on_windows():
        return [sys.executable, str(ROOT / args[0]), *args[1:]]
    cmd = ["wsl.exe"]
    distro = os.environ.get("ATUGCC_WSL_DISTRO")
    if distro:
        cmd += ["-d", distro]
    return cmd + ["--cd", str(PureWindowsPath(ROOT)), "--exec", "python3", *args]


def echo(stream) -> None:
    for line in stream:
        print(line, end="", flush=True)


def stop(proc: subprocess.Popen) -> None:
    """End a child and its children (npm.cmd starts node; ending wsl.exe ends the Linux server)."""
    if proc.poll() is not None:
        return
    if on_windows():
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.terminate()


def wait_any(procs: list[subprocess.Popen]) -> int:
    """Wait until a child ends: the server (`procs[0]`, its exit code) or Vite (an error, e.g. its port was taken)."""
    server, others = procs[0], procs[1:]
    while True:
        if server.poll() is not None:
            return server.returncode
        for proc in others:
            if proc.poll() is not None:
                print("error: the Vite dev server stopped", file=sys.stderr)
                return proc.returncode or 1
        time.sleep(0.2)


def start_server(port: int, extra: list[str], procs: list[subprocess.Popen]) -> tuple[subprocess.Popen, str]:
    """Start the API server (added to `procs` at once); returns it and its URL once it reports its port."""
    cmd = server_command(port, extra)
    print("+ " + " ".join(cmd), flush=True)
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    procs.append(proc)
    url = ""
    for line in proc.stdout:
        print(line, end="", flush=True)
        found = READY_RE.search(line)
        if found:
            url = found.group(1)
            break
    threading.Thread(target=echo, args=(proc.stdout,), daemon=True).start()
    return proc, url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, help=f"page port (default {SERVER_PORT}, with --dev {DEV_PORT}); "
                        f"a busy port moves on to the next free one of {PORT_TRIES}")
    parser.add_argument("--open", action="store_true", help="open the page in the default browser")
    parser.add_argument("--dev", action="store_true", help="page from the Vite dev server (hot reload)")
    parser.add_argument("--no-frontend-build", action="store_true", help="skip npm ci / npm run build")
    args = parser.parse_args(argv)
    if args.port is not None and not (1 if args.dev else 0) <= args.port <= 65535:
        # port 0 lets the server choose; Vite would choose a port this script does not know
        parser.error("--port must be 1..65535" if args.dev else "--port must be 0..65535 (0: any free port)")

    if not args.no_frontend_build:
        code = build_frontend(args.dev)
        if code != 0:
            return code

    try:
        server_port, extra, page_port = launch_plan(args.port, args.dev)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    procs: list[subprocess.Popen] = []
    try:
        server, url = start_server(server_port, extra, procs)
        if not url:
            return server.wait() or 1
        if args.dev:
            tool = npm()
            if tool is None:
                print("error: npm not found", file=sys.stderr)
                return 2
            api_port = READY_RE.search(f"atugcc playground: {url}").group(2)
            procs.append(subprocess.Popen([tool, "run", "dev", "--", "--port", str(page_port)], cwd=FRONTEND,
                                          env={**os.environ, "ATUGCC_API_PORT": api_port}))
            url = f"http://127.0.0.1:{page_port}/"
            print(f"dev page: {url}", flush=True)
        if args.open:
            webbrowser.open(url)
        return wait_any(procs)
    except KeyboardInterrupt:
        return 0
    finally:
        for proc in procs:
            stop(proc)


if __name__ == "__main__":
    sys.exit(main())
