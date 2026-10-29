"""Build and run lessons for the web playground, streaming what happens (spec 070-02 §2.2, 070-06).

One worker thread runs the jobs in order (build and run are serialized). A job builds the
lesson target with the `linux-x64-playground` preset (Debug) or `linux-x64-playground-release`
(RelWithDebInfo, the long profile's default), runs the binary under `stdbuf -oL -eL` and
records every event (`phase`, `build`, `stdout`, `stderr`, `trace`, `done`) in order, so a
stream that connects late still gets the whole run from the first event.

Span lines of the trace file are the exception (070-06 §2.4): they go to a per-key aggregate
(`spans.py`) that the job keeps beside its event list, so memory depends on the number of span
keys, not on the number of spans. Streams get the changed keys (`spans` events).

Every child runs in its own session and is killed as a process group: on Stop, on the time
limit, on the trace-file budget, and after the main process exits, so its children end with it
(a child that detaches into a new session with setsid() escapes: KI-015).
"""
from __future__ import annotations

import codecs
import importlib.util
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from spans import SpanAggregator

ROOT = Path(__file__).resolve().parents[2]
PRESET = "linux-x64-playground"
RELEASE_PRESET = "linux-x64-playground-release"
BUILD_TYPES = {"debug": "Debug", "release": "RelWithDebInfo"}
FLUSH_SEC = 0.1
KEEP_FINISHED = 20
MAX_DIAGNOSTICS = 200
TRACE_READ_BYTES = 4 << 20   # per read of the trace file (070-06 Assumption 10)
TRACE_TICK_SEC = 0.25        # while behind, one tick keeps reading pieces for at most this long
TRACE_FLUSH_MS = "100"       # ATUGCC_TRACE_FLUSH_MS for every run (070-06 Assumption 4)
SPAN_METERS = ("wall", "cpu")


@dataclass(frozen=True)
class Limits:
    build_sec: float
    run_sec: float | None    # None: the lesson's [run] timeout
    output_bytes: int
    trace_bytes: int         # trace file budget; over it the run is stopped (070-06 Assumption 9)
    combined_output: bool    # output_bytes covers stdout and stderr together


# One row per run profile.
PROFILES: dict[str, Limits] = {
    "quick": Limits(build_sec=120, run_sec=10, output_bytes=1 << 20, trace_bytes=1 << 30, combined_output=False),
    "long": Limits(build_sec=180, run_sec=None, output_bytes=8 << 20, trace_bytes=1 << 30, combined_output=True),
}

DIAGNOSTIC_RE = re.compile(
    r"^(?P<file>[^:\n]+):(?P<line>\d+):(?P<col>\d+): (?P<sev>fatal error|error|warning|note): (?P<msg>.*)$",
    re.M)


def load_module(name: str, path: Path):
    """Import a repository script (tools/lessons.py, .agent/scripts/build.py) by path."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lessons = load_module("lessons", ROOT / "tools" / "lessons.py")
build_script = load_module("atugcc_build", ROOT / ".agent" / "scripts" / "build.py")


@dataclass(frozen=True)
class LessonInfo:
    id: str
    path: Path               # working directory of the run
    profile: str             # profile the manifest asks for
    timeout: int = 300       # [run] timeout (seconds, long profile)
    build: str | None = None  # [run] build as written; None = the profile's default


def repo_relative(root: Path, base: Path, name: str) -> str:
    """`name` (absolute, or relative to `base`) as a repo-relative path; unchanged outside the root."""
    path = Path(name) if os.path.isabs(name) else base / name
    try:
        return Path(os.path.normpath(path)).relative_to(root).as_posix()
    except ValueError:
        return name


def parse_diagnostics(text: str, root: Path, build_dir: Path) -> list[dict]:
    out = []
    for m in DIAGNOSTIC_RE.finditer(text):
        sev = "error" if m["sev"] == "fatal error" else m["sev"]
        out.append({"file": repo_relative(root, build_dir, m["file"]), "line": int(m["line"]),
                    "col": int(m["col"]), "severity": sev, "message": m["msg"]})
        if len(out) == MAX_DIAGNOSTICS:
            break
    return out


class Job:
    def __init__(self, lesson: LessonInfo, profile_override: str | None = None,
                 span_meter: str | None = None) -> None:
        self.id = uuid.uuid4().hex
        self.lesson = lesson
        self.profile_override = profile_override
        self.span_meter = span_meter
        self.events: list[tuple[str, dict]] = []
        self.cond = threading.Condition()
        self.state = "queued"           # queued -> running -> done
        self.stop_requested = False
        # Span aggregate (070-06 §2.2): latest row per key with the version that changed it.
        self.span_rows: dict[tuple, tuple[int, dict]] = {}
        self.span_info = {"spanLines": 0, "lagBytes": 0}
        self.span_version = 0

    def publish_spans(self, rows: list[dict], lines: int, lag_bytes: int) -> None:
        with self.cond:
            self.span_version += 1
            for row in rows:
                key = (row["file"], row["line"], row["label"], row["meter"])
                self.span_rows[key] = (self.span_version, row)
            self.span_info = {"spanLines": lines, "lagBytes": lag_bytes}
            self.cond.notify_all()

    def emit(self, event: str, data: dict) -> None:
        with self.cond:
            self.events.append((event, data))
            if event == "done":
                self.state = "done"
            self.cond.notify_all()

    def start(self) -> bool:
        with self.cond:
            if self.state != "queued":
                return False
            self.state = "running"
            return True

    def request_stop(self) -> None:
        with self.cond:
            self.stop_requested = True
            self.cond.notify_all()

    def sleep(self, seconds: float) -> None:
        """Wait up to `seconds`; returns early when a stop is requested."""
        with self.cond:
            if not self.stop_requested:
                self.cond.wait(seconds)

    def events_from(self, index: int, timeout: float) -> tuple[list[tuple[str, dict]], bool]:
        """Events after `index` (waits up to `timeout` for new ones) and whether the job is done."""
        with self.cond:
            if len(self.events) <= index and self.state != "done":
                self.cond.wait(timeout)
            return self.events[index:], self.state == "done"

    def updates_from(self, index: int, seen: int, timeout: float
                     ) -> tuple[list[tuple[str, dict]], bool, dict | None, int]:
        """Like events_from, plus the span payload for a reader that has span version `seen`.

        The payload holds the rows changed since `seen` (`full: false`). In the batch that ends
        with `done` it holds every row (`full: true`), so a stream always ends on the complete
        aggregate, and one that connects after the run gets it in one piece. None: nothing to send.
        Returns (events, done, payload, the version the reader has now).
        """
        with self.cond:
            if len(self.events) <= index and self.span_version <= seen and self.state != "done":
                self.cond.wait(timeout)
            events = self.events[index:]
            ends = any(name == "done" for name, _ in events)
            payload = None
            if ends and self.span_rows:
                payload = {"full": True, "rows": [row for _, (_, row) in sorted(self.span_rows.items())],
                           **self.span_info}
            elif not ends and self.span_version > seen:
                payload = {"full": False,
                           "rows": [row for _, (v, row) in sorted(self.span_rows.items()) if v > seen],
                           **self.span_info}
            return events, self.state == "done", payload, self.span_version


@dataclass
class Outcome:
    exit_code: int | None = None
    signal: str | None = None
    timed_out: bool = False
    stopped: bool = False
    trace_limit: bool = False
    truncated: bool = False
    ms: int = 0
    spawn_error: bool = False
    log: str = ""

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not (self.timed_out or self.stopped or self.trace_limit or self.spawn_error)


class TraceTail:
    """New complete lines of the ATUGCC_TRACE_OUT file since the last read, at most `limit` bytes a read."""

    def __init__(self, path: Path, limit: int = TRACE_READ_BYTES) -> None:
        self.path = path
        self.limit = limit
        self.offset = 0
        self.partial = b""
        self.at_end = True     # the last read reached the end of the file
        self.skipping = False  # inside a line longer than `limit`: dropped up to its newline
        self.oversized = 0     # lines dropped that way, not yet reported

    def read(self, final: bool = False) -> list[str]:
        """`final`: the writer has exited, so a last line without '\\n' counts once the end is reached.

        The unfinished last line is kept for the next read only up to `limit` bytes; a longer line
        is dropped (counted in `oversized`), so memory stays bounded whatever the program writes.
        """
        try:
            with self.path.open("rb") as f:
                f.seek(self.offset)
                data = f.read(self.limit)
        except OSError:
            data = b""
        self.offset += len(data)
        self.at_end = len(data) < self.limit
        lines = (self.partial + data).split(b"\n")
        if self.skipping:
            if len(lines) == 1:  # still inside the dropped line
                self.skipping = not (final and self.at_end)
                self.partial = b""
                return []
            lines = lines[1:]    # its end
            self.skipping = False
        rest = b"" if final and self.at_end else lines.pop()
        if len(rest) > self.limit:
            self.oversized += 1
            self.skipping = True
            rest = b""
        self.partial = rest
        return [line.decode("utf-8", errors="replace") for line in lines if line.strip()]

    def take_oversized(self) -> int:
        count, self.oversized = self.oversized, 0
        return count

    def size(self) -> int:
        try:
            return self.path.stat().st_size
        except OSError:
            return self.offset


@dataclass
class _TraceState:
    """What one run's trace reading keeps between reads."""
    build_dir: Path
    limit_bytes: int
    spans: SpanAggregator = field(default_factory=SpanAggregator)
    diagrams: list[dict] = field(default_factory=list)
    skipped: int = 0
    lag: int = 0
    files: dict[str, str] = field(default_factory=dict)  # repo_relative() per file name: once, not per line


@dataclass
class _Collector:
    """Reads a child's pipes on threads; the job loop drains what arrived every FLUSH_SEC."""
    cap: int
    keep_log: bool = False
    combined: bool = False  # one `cap` for all streams together (long profile)
    lock: threading.Lock = field(default_factory=threading.Lock)
    pending: dict[str, list[str]] = field(default_factory=dict)
    sizes: dict[str, int] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)
    truncated: bool = False

    def reader(self, pipe, name: str) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        fd = pipe.fileno()
        while True:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            with self.lock:
                used = sum(self.sizes.values()) if self.combined else self.sizes.get(name, 0)
                room = self.cap - used
                if room <= 0:
                    self.truncated = True
                    continue  # keep draining so the child never blocks on a full pipe
                if len(chunk) > room:
                    chunk = chunk[:room]
                    self.truncated = True
                self.sizes[name] = self.sizes.get(name, 0) + len(chunk)
                self._add(name, decoder.decode(chunk))
        with self.lock:
            self._add(name, decoder.decode(b"", final=True))
        pipe.close()

    def _add(self, name: str, text: str) -> None:
        if text:
            self.pending.setdefault(name, []).append(text)
            if self.keep_log:
                self.log.append(text)

    def drain(self) -> list[tuple[str, str]]:
        with self.lock:
            out = [(name, "".join(parts)) for name, parts in self.pending.items() if parts]
            self.pending = {}
        return out


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


class RunManager:
    """Queue of jobs and the worker thread that runs them one at a time."""

    def __init__(self, root: Path = ROOT, preset: str = PRESET, *, release_preset: str = RELEASE_PRESET,
                 build: bool = True,
                 lesson_info: Callable[[str], LessonInfo] | None = None,
                 executable: Callable[[LessonInfo, Path], list[str]] | None = None,
                 profiles: dict[str, Limits] | None = None) -> None:
        self.root = root.resolve()
        self.preset = preset
        self.presets = {"debug": preset, "release": release_preset}
        self.build_dir = self.build_dir_of("debug")
        self.build_enabled = build
        self.lesson_info = lesson_info or self._catalog_lesson
        self.executable = executable or (lambda info, build_dir: [str(build_dir / "bin" / "lessons" / f"lesson_{info.id}")])
        self.profiles = profiles or PROFILES
        self.jobs: dict[str, Job] = {}
        self.finished: list[str] = []
        self.lock = threading.Lock()
        self.queue: queue.Queue[Job] = queue.Queue()
        threading.Thread(target=self._worker, name="playground-runner", daemon=True).start()

    def build_dir_of(self, kind: str) -> Path:
        return self.root / "out" / "build" / self.presets[kind]

    def _catalog_lesson(self, lesson_id: str) -> LessonInfo:
        catalog, _ = lessons.load(self.root)
        for lesson in catalog.lessons:
            if lesson.id == lesson_id:
                return LessonInfo(lesson.id, lesson.path, lesson.profile, lesson.timeout, lesson.build)
        raise KeyError(lesson_id)

    def create(self, lesson_id: str, profile_override: str | None = None, span_meter: str | None = None) -> Job:
        """Queue a run of `lesson_id`; KeyError when there is no such lesson, ValueError for a bad option."""
        if profile_override not in (None, *lessons.PROFILES):
            raise ValueError(f"profileOverride must be one of {', '.join(lessons.PROFILES)}")
        if span_meter not in (None, *SPAN_METERS):
            raise ValueError(f"spanMeter must be one of {', '.join(SPAN_METERS)}")
        job = Job(self.lesson_info(lesson_id), profile_override, span_meter)
        with self.lock:
            self.jobs[job.id] = job
        self.queue.put(job)
        return job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)

    def stop(self, job_id: str) -> bool:
        job = self.get(job_id)
        if job is None:
            return False
        job.request_stop()
        with job.cond:
            queued = job.state == "queued"
        if queued and job.start():  # still waiting in the queue: end it here
            job.emit("done", self._done_data(None, None, [], 0, stopped=True))
        return True

    def _worker(self) -> None:
        while True:
            job = self.queue.get()
            if not job.start():
                continue
            try:
                self._execute(job)
            except Exception as exc:  # report, never kill the worker
                job.emit("stderr", {"text": f"playground internal error: {exc!r}\n"})
                job.emit("done", self._done_data(None, None, [], 0, stopped=job.stop_requested))
            with self.lock:
                self.finished.append(job.id)
                while len(self.finished) > KEEP_FINISHED:
                    self.jobs.pop(self.finished.pop(0), None)

    @staticmethod
    def _done_data(build: dict | None, run: dict | None, diagrams: list, skipped: int, stopped: bool) -> dict:
        return {"build": build or {"ok": False, "ms": 0, "diagnostics": [], "timedOut": False},
                "run": run, "diagrams": diagrams, "skippedTraceLines": skipped, "stopped": stopped}

    # --- one job ---------------------------------------------------------------------------
    def _execute(self, job: Job) -> None:
        requested = job.lesson.profile
        profile = job.profile_override or requested
        if profile not in self.profiles:
            profile = "quick"
        limits = self.profiles[profile]
        kind = lessons.effective_build(profile, job.lesson.build)
        build_dir = self.build_dir_of(kind)
        run_sec = limits.run_sec if limits.run_sec is not None else job.lesson.timeout
        phase_extra = {"profile": profile, "requested": requested, "buildType": BUILD_TYPES[kind]}

        build = {"ok": True, "ms": 0, "diagnostics": [], "timedOut": False}
        if job.stop_requested:
            job.emit("done", self._done_data(None, None, [], 0, stopped=True))
            return
        if self.build_enabled:
            build = self._build(job, limits, phase_extra, self.presets[kind], build_dir)
        if not build["ok"] or job.stop_requested:
            job.emit("done", self._done_data(build, None, [], 0, stopped=job.stop_requested))
            return

        job.emit("phase", {"phase": "run", "limitSec": run_sec, **phase_extra})
        fd, trace_name = tempfile.mkstemp(prefix="atugcc_trace_", suffix=".jsonl")
        os.close(fd)
        trace_path = Path(trace_name)
        state = _TraceState(build_dir=build_dir, limit_bytes=limits.trace_bytes)
        tail = TraceTail(trace_path)
        env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
        env["ATUGCC_TRACE_OUT"] = str(trace_path)
        env["ATUGCC_TRACE_FLUSH_MS"] = TRACE_FLUSH_MS
        env.pop("ATUGCC_SPAN_METER", None)
        if job.span_meter:
            env["ATUGCC_SPAN_METER"] = job.span_meter
        # stdbuf works through LD_PRELOAD; an ASan-built program refuses to start unless told
        # that its runtime need not come first (sanitizer presets, test fixture)
        asan = env.get("ASAN_OPTIONS", "")
        env["ASAN_OPTIONS"] = f"{asan}:verify_asan_link_order=0" if asan else "verify_asan_link_order=0"
        argv = ["stdbuf", "-oL", "-eL", *self.executable(job.lesson, build_dir)]
        try:
            outcome = self._stream(job, argv, job.lesson.path, env, run_sec, limits.output_bytes,
                                   ("stdout", "stderr"), lambda final: self._trace(job, tail, state, final),
                                   combined=limits.combined_output)
        finally:
            trace_path.unlink(missing_ok=True)
        run = {"exitCode": outcome.exit_code, "signal": outcome.signal, "timedOut": outcome.timed_out,
               "stopped": outcome.stopped, "traceLimit": outcome.trace_limit, "ms": outcome.ms,
               "truncated": outcome.truncated}
        job.emit("done", self._done_data(build, run, state.diagrams, state.skipped, outcome.stopped))

    def _build(self, job: Job, limits: Limits, phase_extra: dict, preset: str, build_dir: Path) -> dict:
        start = time.monotonic()
        preset_files = (self.root / "CMakePresets.json", self.root / "CMakeUserPresets.json")
        mode = build_script.configure_mode(build_dir, self.root.as_posix(), False, preset_files)
        log: list[str] = []
        outcome = Outcome(exit_code=0)
        if mode is not None:
            job.emit("phase", {"phase": "configure", "limitSec": limits.build_sec, **phase_extra})
            if mode == "stale":
                shutil.rmtree(build_dir, ignore_errors=True)
            argv = ["cmake", "--preset", preset] + (["--fresh"] if mode in ("fresh", "stale") else [])
            outcome = self._stream(job, argv, self.root, dict(os.environ), limits.build_sec,
                                   limits.output_bytes, ("build", "build"), keep_log=True)
            log.append(outcome.log)
        remaining = limits.build_sec - (time.monotonic() - start)  # configure and build share the limit
        if outcome.ok and remaining <= 0:
            job.emit("build", {"text": f"build time limit ({limits.build_sec:g} s) used up by configure\n"})
            outcome = Outcome(timed_out=True)
        elif outcome.ok:
            job.emit("phase", {"phase": "build", "limitSec": round(remaining, 1), **phase_extra})
            argv = ["cmake", "--build", "--preset", preset, "--target", f"lesson_{job.lesson.id}"]
            outcome = self._stream(job, argv, self.root, dict(os.environ), remaining,
                                   limits.output_bytes, ("build", "build"), keep_log=True)
            log.append(outcome.log)
        return {"ok": outcome.ok, "ms": int((time.monotonic() - start) * 1000),
                "diagnostics": parse_diagnostics("".join(log), self.root, build_dir),
                "timedOut": outcome.timed_out}

    def _trace(self, job: Job, tail: TraceTail, state: _TraceState, final: bool) -> bool:
        """Read new trace lines; returns True when the trace file is over its budget.

        A tick reads one piece, more while it is behind (up to TRACE_TICK_SEC). `final` (the program
        has exited) reads to the end of the file, unless Stop was requested.
        """
        deadline = time.monotonic() + TRACE_TICK_SEC
        while True:
            self._trace_lines(job, tail.read(final), state)
            state.skipped += tail.take_oversized()
            size = tail.size()
            lag = max(0, size - tail.offset)
            rows = state.spans.drain()
            if rows or (state.spans.lines and lag != state.lag):  # per piece: a long drain keeps updating
                state.lag = lag
                job.publish_spans(rows, state.spans.lines, lag)
            if tail.at_end or job.stop_requested or (not final and time.monotonic() >= deadline):
                break
        return size > state.limit_bytes

    def _trace_lines(self, job: Job, lines: list[str], state: _TraceState) -> None:
        events = []
        for line in lines:
            try:
                obj = json.loads(line)
            except ValueError:
                obj = None
            if not isinstance(obj, dict) or "kind" not in obj:
                state.skipped += 1
                continue
            if obj["kind"] == "diagram":
                state.diagrams.append(obj)
                continue
            file = obj.get("file")
            if isinstance(file, str):
                relative = state.files.get(file)
                if relative is None:
                    relative = state.files[file] = repo_relative(self.root, state.build_dir, file)
                obj["file"] = relative
            if obj["kind"] == "span":  # aggregated, never sent or kept one by one (070-06 §2.4)
                if not state.spans.add(obj):
                    state.skipped += 1
                continue
            events.append(obj)
        if events:
            job.emit("trace", {"events": events})

    def _stream(self, job: Job, argv: list[str], cwd: Path, env: dict, limit_sec: float, cap: int,
                names: tuple[str, str], trace: Callable[[bool], bool] | None = None,
                keep_log: bool = False, combined: bool = False) -> Outcome:
        """Run `argv` in its own session, emitting its output every FLUSH_SEC until it ends.

        `trace(final)` reads the trace file; True means it is over budget and the run is stopped.
        """
        start = time.monotonic()
        merged = names[0] == names[1]
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT if merged else subprocess.PIPE,
                                    start_new_session=True)
        except OSError as exc:
            job.emit(names[1], {"text": f"{argv[0]}: {exc}\n"})
            return Outcome(spawn_error=True, log=f"{argv[0]}: {exc}\n")

        collector = _Collector(cap, keep_log, combined)
        readers = [threading.Thread(target=collector.reader, args=(proc.stdout, names[0]), daemon=True)]
        if not merged:
            readers.append(threading.Thread(target=collector.reader, args=(proc.stderr, names[1]), daemon=True))
        for reader in readers:
            reader.start()

        outcome = Outcome()

        def flush(final: bool = False) -> bool:
            for name, text in collector.drain():
                job.emit(name, {"text": text})
            return trace(final) if trace is not None else False

        while True:
            if proc.poll() is not None:
                _kill_group(proc)  # anything the program left behind in its group
                for reader in readers:
                    reader.join(timeout=2)
                flush(final=True)
                break
            ending = outcome.stopped or outcome.timed_out or outcome.trace_limit
            if job.stop_requested and not outcome.stopped:
                outcome.stopped = True
                _kill_group(proc)
            elif not ending and time.monotonic() - start > limit_sec:
                outcome.timed_out = True
                _kill_group(proc)
            if flush() and not (outcome.stopped or outcome.timed_out or outcome.trace_limit):
                outcome.trace_limit = True
                _kill_group(proc)
            job.sleep(FLUSH_SEC)

        outcome.ms = int((time.monotonic() - start) * 1000)
        code = proc.returncode
        if code is not None and code < 0:
            try:
                outcome.signal = signal.Signals(-code).name
            except ValueError:
                outcome.signal = str(-code)
        else:
            outcome.exit_code = code
        outcome.truncated = collector.truncated
        outcome.log = "".join(collector.log)
        return outcome


def compiler_version(root: Path = ROOT, preset: str = PRESET) -> str | None:
    """First line of `<compiler> --version` for the playground build (g++ before the first configure)."""
    cache = root / "out" / "build" / preset / "CMakeCache.txt"
    try:
        found = re.search(r"^CMAKE_CXX_COMPILER:\w+=(.+)$", cache.read_text(encoding="utf-8", errors="replace"), re.M)
    except OSError:
        found = None
    compiler = found[1].strip() if found else "g++"
    try:
        out = subprocess.run([compiler, "--version"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return out.splitlines()[0] if out else None
