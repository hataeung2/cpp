#!/usr/bin/env python3
"""Local web playground server (spec 070-02): lesson API, file API, runs as SSE, static frontend.

Usage (normally started by tools/playground.py):
    python3 web/server/server.py [--port 8765] [--dist web/frontend/dist] [--allow-origin URL ...]

The server runs code from the repository, so it listens on 127.0.0.1 only and refuses requests
that do not come from its own page: the Host header must name 127.0.0.1 or localhost with this
port (DNS rebinding), an Origin header must be this server or an --allow-origin (another site
cannot drive the API), and PUT/POST bodies must be application/json (no plain form posts).
"""
from __future__ import annotations

import argparse
import errno
import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import runner  # noqa: E402
from files import Conflict, PathError, RepoFiles  # noqa: E402

API_VERSION = 1
BIND_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PORT_TRIES = 20
PING_SEC = 0.25
MAX_BODY = 4 << 20
DEFAULT_DIST = runner.ROOT / "web" / "frontend" / "dist"


class PlaygroundServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, root: Path, dist: Path, runs: runner.RunManager,
                 allowed_origins: tuple[str, ...] = ()) -> None:
        super().__init__((BIND_HOST, port), Handler)
        self.root = root.resolve()
        self.dist = dist.resolve()
        self.files = RepoFiles(self.root)
        self.runs = runs
        port = self.server_address[1]
        self.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        self.allowed_origins = {f"http://{h}" for h in self.allowed_hosts} | set(allowed_origins)


class Handler(BaseHTTPRequestHandler):
    server: PlaygroundServer
    protocol_version = "HTTP/1.1"
    server_version = "atugcc-playground"

    def log_message(self, format: str, *args) -> None:  # noqa: A002 (base class name)
        pass  # one person, local: the terminal stays for the server's own messages

    # --- responses -----------------------------------------------------------------------
    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, data) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self.close_connection = True  # a request body may be left unread
        self._json(status, {"error": message})

    def _guard(self) -> bool:
        if self.headers.get("Host", "") not in self.server.allowed_hosts:
            self._error(HTTPStatus.FORBIDDEN, "unexpected Host header")
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin not in self.server.allowed_origins:
            self._error(HTTPStatus.FORBIDDEN, "cross-origin request refused")
            return False
        if self.command in ("PUT", "POST") and not self.headers.get("Content-Type", "").startswith("application/json"):
            self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "body must be application/json")
            return False
        return True

    def _body(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, f"body must be 0..{MAX_BODY} bytes")
            return None
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            data = None
        if not isinstance(data, dict):
            self._error(HTTPStatus.BAD_REQUEST, "body must be a JSON object")
            return None
        return data

    # --- routing -------------------------------------------------------------------------
    def do_GET(self) -> None:
        if not self._guard():
            return
        url = urlsplit(self.path)
        parts = url.path.split("/")
        if url.path == "/api/health":
            self._json(200, {"version": API_VERSION, "preset": self.server.runs.preset,
                             "compiler": runner.compiler_version(self.server.root, self.server.runs.preset)})
        elif url.path == "/api/lessons":
            self._lessons()
        elif url.path == "/api/files":
            self._read_file(parse_qs(url.query).get("path", [""])[0])
        elif len(parts) == 5 and parts[:3] == ["", "api", "runs"] and parts[4] == "stream":
            self._stream(parts[3])
        elif url.path.startswith("/api/"):
            self._error(HTTPStatus.NOT_FOUND, "no such API")
        else:
            self._static(url.path)

    do_HEAD = do_GET

    def do_PUT(self) -> None:
        if not self._guard():
            return
        url = urlsplit(self.path)
        if url.path != "/api/files":
            self._error(HTTPStatus.NOT_FOUND, "no such API")
            return
        body = self._body()
        if body is None:
            return
        content, base_sha = body.get("content"), body.get("baseSha")
        if not isinstance(content, str) or not (base_sha is None or isinstance(base_sha, str)):
            self._error(HTTPStatus.BAD_REQUEST, "expected {content: string, baseSha: string|null}")
            return
        try:
            self._json(200, self.server.files.write(parse_qs(url.query).get("path", [""])[0], content, base_sha))
        except PathError as exc:
            self._error(exc.status, exc.message)
        except Conflict as exc:
            self._json(HTTPStatus.CONFLICT, {"error": "file changed on disk", "content": exc.content, "sha": exc.sha})

    def do_POST(self) -> None:
        if not self._guard():
            return
        parts = urlsplit(self.path).path.split("/")
        body = self._body()
        if body is None:
            return
        if parts == ["", "api", "runs"]:
            lesson = body.get("lesson")
            if not isinstance(lesson, str):
                self._error(HTTPStatus.BAD_REQUEST, "expected {lesson: string}")
                return
            try:
                job = self.server.runs.create(lesson)
            except KeyError:
                self._error(HTTPStatus.NOT_FOUND, f"no lesson {lesson!r}")
                return
            self._json(HTTPStatus.ACCEPTED, {"runId": job.id})
        elif len(parts) == 5 and parts[:3] == ["", "api", "runs"] and parts[4] == "stop":
            if self.server.runs.stop(parts[3]):
                self._json(200, {"stopping": True})
            else:
                self._error(HTTPStatus.NOT_FOUND, "no such run")
        else:
            self._error(HTTPStatus.NOT_FOUND, "no such API")

    # --- handlers ------------------------------------------------------------------------
    def _lessons(self) -> None:
        catalog, report = runner.lessons.load(self.server.root)
        runner.lessons.check(catalog, report)
        data = runner.lessons.index(catalog)
        data["problems"] = [str(f) for f in report.findings if f.level == "ERROR"]
        self._json(200, data)

    def _read_file(self, path: str) -> None:
        try:
            self._json(200, self.server.files.read(path))
        except PathError as exc:
            self._error(exc.status, exc.message)

    def _stream(self, run_id: str) -> None:
        job = self.server.runs.get(run_id)
        if job is None:
            self._error(HTTPStatus.NOT_FOUND, "no such run")
            return
        try:  # EventSource reconnects with the id of the last event it got
            index = int(self.headers.get("Last-Event-ID", "-1")) + 1
        except ValueError:
            index = 0
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        try:
            while True:
                events, done = job.events_from(index, PING_SEC)
                if events:
                    chunk = "".join(
                        f"id: {index + i}\nevent: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                        for i, (name, data) in enumerate(events))
                    index += len(events)
                    self.wfile.write(chunk.encode("utf-8"))
                else:
                    self.wfile.write(b": ping\n\n")  # a closed tab shows up as a failed write
                self.wfile.flush()
                if done:
                    return
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError):
            self.server.runs.stop(job.id)  # spec: closing the page ends the run

    def _static(self, path: str) -> None:
        dist = self.server.dist
        if not (dist / "index.html").is_file():
            self._send(200, ("<!doctype html><meta charset=utf-8><title>atugcc playground</title>"
                             "<p>Frontend not built. Run <code>py -3 tools/playground.py</code> "
                             "(Linux: <code>python3 tools/playground.py</code>).</p>").encode("utf-8"),
                       "text/html; charset=utf-8")
            return
        rel = unquote(path).lstrip("/") or "index.html"
        target = (dist / rel).resolve()
        try:
            target.relative_to(dist)
        except ValueError:
            self._error(HTTPStatus.BAD_REQUEST, "path leaves the frontend folder")
            return
        if not target.is_file():
            target = dist / "index.html"  # single page app
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self._send(200, target.read_bytes(), ctype)


def make_server(port: int, root: Path = runner.ROOT, dist: Path = DEFAULT_DIST,
               runs: runner.RunManager | None = None, allowed_origins: tuple[str, ...] = (),
               tries: int = PORT_TRIES) -> PlaygroundServer:
    """Bind to 127.0.0.1:`port`, or the next free one of `tries` ports (port 0: any free port)."""
    runs = runs or runner.RunManager(root)
    for candidate in range(port, port + tries) if port else [0]:
        try:
            return PlaygroundServer(candidate, root, dist, runs, allowed_origins)
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise
    raise OSError(errno.EADDRINUSE, f"ports {port}..{port + tries - 1} are all in use")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST, help="built frontend (npm run build)")
    parser.add_argument("--allow-origin", action="append", default=[],
                        help="extra page origin allowed to call the API (the Vite dev server)")
    args = parser.parse_args(argv)
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    try:
        server = make_server(args.port, dist=args.dist, allowed_origins=tuple(args.allow_origin))
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"atugcc playground: http://127.0.0.1:{server.server_address[1]}/  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
