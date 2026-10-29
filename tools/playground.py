#!/usr/bin/env python3
"""Start the local web playground (spec 070-02).

Usage:
    py -3 tools/playground.py [--port 8765] [--open] [--dev] [--no-frontend-build]   (Linux: python3)

- Builds the frontend with the host's Node when needed (`npm ci` when node_modules is missing
  or older than package-lock.json, `npm run build` when dist/ is older than its sources).
- Starts web/server/server.py: in WSL on a Windows host (distribution: ATUGCC_WSL_DISTRO, else
  the default, as in .agent/scripts/build.py), directly on Linux. The server listens on
  127.0.0.1 only; WSL2 forwards localhost, so the Windows browser reaches it.
- --dev: also starts the Vite dev server (hot reload) on 127.0.0.1:5173, proxying /api.
- --open: opens the page in the default browser once the server is up.
Ctrl+C stops everything.
"""
from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "web" / "frontend"
DEV_PORT = 5173
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
    parser.add_argument("--port", type=int, default=8765, help="first port to try (the next free one is used)")
    parser.add_argument("--open", action="store_true", help="open the page in the default browser")
    parser.add_argument("--dev", action="store_true", help="Vite dev server with hot reload on port 5173")
    parser.add_argument("--no-frontend-build", action="store_true", help="skip npm ci / npm run build")
    args = parser.parse_args(argv)

    if not args.no_frontend_build:
        code = build_frontend(args.dev)
        if code != 0:
            return code

    extra = []
    if args.dev:
        extra = ["--allow-origin", f"http://127.0.0.1:{DEV_PORT}", "--allow-origin", f"http://localhost:{DEV_PORT}"]
    procs: list[subprocess.Popen] = []
    try:
        server, url = start_server(args.port, extra, procs)
        if not url:
            return server.wait() or 1
        if args.dev:
            tool = npm()
            if tool is None:
                print("error: npm not found", file=sys.stderr)
                return 2
            api_port = READY_RE.search(f"atugcc playground: {url}").group(2)
            procs.append(subprocess.Popen([tool, "run", "dev"], cwd=FRONTEND,
                                          env={**os.environ, "ATUGCC_API_PORT": api_port}))
            url = f"http://127.0.0.1:{DEV_PORT}/"
            print(f"dev page: {url}", flush=True)
        if args.open:
            webbrowser.open(url)
        return server.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        for proc in procs:
            stop(proc)


if __name__ == "__main__":
    sys.exit(main())
