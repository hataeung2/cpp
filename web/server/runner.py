"""Build and run lessons for the web playground, streaming what happens (spec 070-02 §2.2).

One worker thread runs the jobs in order (build and run are serialized). A job builds the
lesson target with the `linux-x64-playground` preset, runs the binary under `stdbuf -oL -eL`
and records every event (`phase`, `build`, `stdout`, `stderr`, `trace`, `done`) in order, so a
stream that connects late still gets the whole run from the first event.

Every child runs in its own session and is killed as a process group: on Stop, on the time
limit, and after the main process exits, so its children end with it (a child that detaches
into a new session with setsid() escapes: KI-015).
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

ROOT = Path(__file__).resolve().parents[2]
PRESET = "linux-x64-playground"
FLUSH_SEC = 0.1
KEEP_FINISHED = 20
MAX_DIAGNOSTICS = 200


@dataclass(frozen=True)
class Limits:
    build_sec: float
    run_sec: float
    output_bytes: int


# One row per run profile. 070-06 adds "long".
PROFILES: dict[str, Limits] = {
    "quick": Limits(build_sec=120, run_sec=10, output_bytes=1 << 20),
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
    path: Path      # working directory of the run
    profile: str    # profile the manifest asks for


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
    def __init__(self, lesson: LessonInfo) -> None:
        self.id = uuid.uuid4().hex
        self.lesson = lesson
        self.events: list[tuple[str, dict]] = []
        self.cond = threading.Condition()
        self.state = "queued"           # queued -> running -> done
        self.stop_requested = False

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


@dataclass
class Outcome:
    exit_code: int | None = None
    signal: str | None = None
    timed_out: bool = False
    stopped: bool = False
    truncated: bool = False
    ms: int = 0
    spawn_error: bool = False
    log: str = ""

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not (self.timed_out or self.stopped or self.spawn_error)


class TraceTail:
    """New complete lines of the ATUGCC_TRACE_OUT file since the last read."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.offset = 0
        self.partial = b""

    def read(self, final: bool = False) -> list[str]:
        try:
            with self.path.open("rb") as f:
                f.seek(self.offset)
                data = f.read()
        except OSError:
            data = b""
        self.offset += len(data)
        data = self.partial + data
        lines = data.split(b"\n")
        self.partial = b"" if final else lines.pop()
        return [line.decode("utf-8", errors="replace") for line in lines if line.strip()]


@dataclass
class _Collector:
    """Reads a child's pipes on threads; the job loop drains what arrived every FLUSH_SEC."""
    cap: int
    keep_log: bool = False
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
                room = self.cap - self.sizes.get(name, 0)
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

    def __init__(self, root: Path = ROOT, preset: str = PRESET, *, build: bool = True,
                 lesson_info: Callable[[str], LessonInfo] | None = None,
                 executable: Callable[[LessonInfo], list[str]] | None = None,
                 profiles: dict[str, Limits] | None = None) -> None:
        self.root = root.resolve()
        self.preset = preset
        self.build_dir = self.root / "out" / "build" / preset
        self.build_enabled = build
        self.lesson_info = lesson_info or self._catalog_lesson
        self.executable = executable or (lambda info: [str(self.build_dir / "bin" / "lessons" / f"lesson_{info.id}")])
        self.profiles = profiles or PROFILES
        self.jobs: dict[str, Job] = {}
        self.finished: list[str] = []
        self.lock = threading.Lock()
        self.queue: queue.Queue[Job] = queue.Queue()
        threading.Thread(target=self._worker, name="playground-runner", daemon=True).start()

    def _catalog_lesson(self, lesson_id: str) -> LessonInfo:
        catalog, _ = lessons.load(self.root)
        for lesson in catalog.lessons:
            if lesson.id == lesson_id:
                return LessonInfo(lesson.id, lesson.path, lesson.profile)
        raise KeyError(lesson_id)

    def create(self, lesson_id: str) -> Job:
        """Queue a run of `lesson_id`; KeyError when there is no such lesson."""
        job = Job(self.lesson_info(lesson_id))
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
        profile = "quick" if job.lesson.profile not in self.profiles else job.lesson.profile
        limits = self.profiles[profile]
        phase_extra = {"profile": profile, "requested": job.lesson.profile}

        build = {"ok": True, "ms": 0, "diagnostics": [], "timedOut": False}
        if job.stop_requested:
            job.emit("done", self._done_data(None, None, [], 0, stopped=True))
            return
        if self.build_enabled:
            build = self._build(job, limits, phase_extra)
        if not build["ok"] or job.stop_requested:
            job.emit("done", self._done_data(build, None, [], 0, stopped=job.stop_requested))
            return

        job.emit("phase", {"phase": "run", "limitSec": limits.run_sec, **phase_extra})
        fd, trace_name = tempfile.mkstemp(prefix="atugcc_trace_", suffix=".jsonl")
        os.close(fd)
        trace_path = Path(trace_name)
        state = {"diagrams": [], "skipped": 0}
        tail = TraceTail(trace_path)
        env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
        env["ATUGCC_TRACE_OUT"] = str(trace_path)
        # stdbuf works through LD_PRELOAD; an ASan-built program refuses to start unless told
        # that its runtime need not come first (sanitizer presets, test fixture)
        asan = env.get("ASAN_OPTIONS", "")
        env["ASAN_OPTIONS"] = f"{asan}:verify_asan_link_order=0" if asan else "verify_asan_link_order=0"
        argv = ["stdbuf", "-oL", "-eL", *self.executable(job.lesson)]
        try:
            outcome = self._stream(job, argv, job.lesson.path, env, limits.run_sec, limits.output_bytes,
                                   ("stdout", "stderr"), lambda final: self._trace(job, tail, state, final))
        finally:
            trace_path.unlink(missing_ok=True)
        run = {"exitCode": outcome.exit_code, "signal": outcome.signal, "timedOut": outcome.timed_out,
               "stopped": outcome.stopped, "ms": outcome.ms, "truncated": outcome.truncated}
        job.emit("done", self._done_data(build, run, state["diagrams"], state["skipped"], outcome.stopped))

    def _build(self, job: Job, limits: Limits, phase_extra: dict) -> dict:
        start = time.monotonic()
        preset_files = (self.root / "CMakePresets.json", self.root / "CMakeUserPresets.json")
        mode = build_script.configure_mode(self.build_dir, self.root.as_posix(), False, preset_files)
        log: list[str] = []
        outcome = Outcome(exit_code=0)
        if mode is not None:
            job.emit("phase", {"phase": "configure", "limitSec": limits.build_sec, **phase_extra})
            if mode == "stale":
                shutil.rmtree(self.build_dir, ignore_errors=True)
            argv = ["cmake", "--preset", self.preset] + (["--fresh"] if mode in ("fresh", "stale") else [])
            outcome = self._stream(job, argv, self.root, dict(os.environ), limits.build_sec,
                                   limits.output_bytes, ("build", "build"), keep_log=True)
            log.append(outcome.log)
        remaining = limits.build_sec - (time.monotonic() - start)  # configure and build share the limit
        if outcome.ok and remaining <= 0:
            job.emit("build", {"text": f"build time limit ({limits.build_sec:g} s) used up by configure\n"})
            outcome = Outcome(timed_out=True)
        elif outcome.ok:
            job.emit("phase", {"phase": "build", "limitSec": limits.build_sec, **phase_extra})
            argv = ["cmake", "--build", "--preset", self.preset, "--target", f"lesson_{job.lesson.id}"]
            outcome = self._stream(job, argv, self.root, dict(os.environ), remaining,
                                   limits.output_bytes, ("build", "build"), keep_log=True)
            log.append(outcome.log)
        return {"ok": outcome.ok, "ms": int((time.monotonic() - start) * 1000),
                "diagnostics": parse_diagnostics("".join(log), self.root, self.build_dir),
                "timedOut": outcome.timed_out}

    def _trace(self, job: Job, tail: TraceTail, state: dict, final: bool) -> None:
        events = []
        for line in tail.read(final):
            try:
                obj = json.loads(line)
            except ValueError:
                obj = None
            if not isinstance(obj, dict) or "kind" not in obj:
                state["skipped"] += 1
                continue
            if obj["kind"] == "diagram":
                state["diagrams"].append(obj)
                continue
            if isinstance(obj.get("file"), str):
                obj["file"] = repo_relative(self.root, self.build_dir, obj["file"])
            events.append(obj)
        if events:
            job.emit("trace", {"events": events})

    def _stream(self, job: Job, argv: list[str], cwd: Path, env: dict, limit_sec: float, cap: int,
                names: tuple[str, str], trace: Callable[[bool], None] | None = None,
                keep_log: bool = False) -> Outcome:
        """Run `argv` in its own session, emitting its output every FLUSH_SEC until it ends."""
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

        collector = _Collector(cap, keep_log)
        readers = [threading.Thread(target=collector.reader, args=(proc.stdout, names[0]), daemon=True)]
        if not merged:
            readers.append(threading.Thread(target=collector.reader, args=(proc.stderr, names[1]), daemon=True))
        for reader in readers:
            reader.start()

        outcome = Outcome()

        def flush(final: bool = False) -> None:
            for name, text in collector.drain():
                job.emit(name, {"text": text})
            if trace is not None:
                trace(final)

        while True:
            if proc.poll() is not None:
                _kill_group(proc)  # anything the program left behind in its group
                for reader in readers:
                    reader.join(timeout=2)
                flush(final=True)
                break
            if job.stop_requested and not outcome.stopped:
                outcome.stopped = True
                _kill_group(proc)
            elif not outcome.stopped and not outcome.timed_out and time.monotonic() - start > limit_sec:
                outcome.timed_out = True
                _kill_group(proc)
            flush()
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
