# Web Playground (local)

The browser side of the lessons in [`lessons/`](../lessons/README.md): pick a lesson, edit its files, Run, and watch the build log, the program's output, the Tracer events, the code-range timings and the Mermaid diagrams arrive while it runs. Specs: [070-02](../docs/specs/070_02_web_playground.md) (page, server), [070-06](../docs/specs/070_06_long_run_timings.md) (long runs, Timings).

The page edits the **repository's own files** and builds with a **preset**, so the same lesson can be worked on in VS Code and in the browser, and git keeps the history.

> **Local only.** The server builds and runs whatever the lessons contain. It listens on `127.0.0.1` only, checks `Host` and `Origin`, and accepts request bodies only as `application/json`, so other web sites cannot drive it. Do not put it behind a proxy or bind it to another interface (public use: task 070-05).

## Start
| What | Command |
|---|---|
| Start and open the page | `py -3 tools/playground.py --open` (Linux: `python3`), or VS Code task **Playground: start** |
| Frontend with hot reload | `py -3 tools/playground.py --dev --open` (task **Playground: start (dev)**): the page comes from Vite on `127.0.0.1:5173`, which proxies `/api` to the API server on any free port |
| Another port | `--port 9000`: the page's port in both modes (default 8765, with `--dev` 5173); a busy port moves on to the next of 20 |

`tools/playground.py` runs `npm ci` with the host's Node when `node_modules` is missing or older than `package-lock.json`, and `npm run build` when `web/frontend/dist` is missing or older than its sources, then starts `web/server/server.py`: through `wsl.exe` on Windows (distribution: `ATUGCC_WSL_DISTRO`, else the default), directly on Linux. WSL2 forwards `localhost`, so the Windows browser reaches the server.

Requirements: WSL (Windows) or Linux with CMake, Ninja, GCC and Python 3.11+ (the same as the `linux-x64-*` presets); Node.js 20+ on the host for the frontend build. The first Run configures the `linux-x64-playground` preset (about a minute), the first long-profile Run `linux-x64-playground-release`; later Runs rebuild only the lesson.

## Structure
```text
web/
  server/                 Python 3.11+ standard library only
    server.py             HTTP API, SSE, static files (127.0.0.1)
    runner.py             one job at a time: preset build → run → stream; limits; Stop
    spans.py              span aggregates per (file, line, label, meter): count/total/min/max, sample, p50/p95
    files.py              path checks, read/write, sha conflict detection, line endings
    capture_diagrams.py   regenerates the Mermaid fixture from the seed lessons
    test_server.py        unittest (CTest: PlaygroundServer)
  frontend/               Vite + TypeScript (versions pinned in package.json / package-lock.json)
    src/  main.ts (wiring), api.ts, editor.ts (Monaco tabs, inline span times), lessonTree.ts,
          output.ts + ansi.ts, diagrams.ts, events.ts, timings.ts, readme.ts, diagnostics.ts, theme.css
    test/ vitest (jsdom)
```
The test fixture program for the runner is `tests/playground/playground_fixture.cpp` (a test target, not a lesson).

## API
| Method | Path | Result |
|---|---|---|
| GET | `/api/health` | `{version, preset, releasePreset, compiler}` |
| GET | `/api/lessons` | lesson index of [`tools/lessons.py`](../tools/lessons.py) (`tracks`, `units`) + `problems` (manifest errors) |
| GET | `/api/files?path=<repo-relative>` | `{path, content, sha, eol, writable}`: `content` always uses LF; `sha` = SHA-256 of the bytes on disk |
| PUT | `/api/files?path=…` `{content, baseSha}` | `{sha}`; 409 `{content, sha}` when the file changed since `baseSha` (`null` = create a new file); 403 outside `lessons/` |
| POST | `/api/runs` `{lesson, profileOverride?, spanMeter?}` | 202 `{runId}`; runs are queued and executed one at a time. `profileOverride`: `quick` or `long`, this run only; `spanMeter`: `wall` or `cpu` (→ `ATUGCC_SPAN_METER`); another value is 400 |
| GET | `/api/runs/<id>/stream` | Server-Sent Events from the first event of the run (`id:` = event index; `Last-Event-ID` resumes) |
| POST | `/api/runs/<id>/stop` | kills the run's process group; the stream ends with `done{stopped:true}` |

Path rules: repo-relative with `/`; no `..`, `.`, hidden components (`.git`), absolute or drive paths, backslashes, NUL, or symlinks leading out of the repository (400). Writes: existing files under `lessons/`, or new `.cpp`/`.hpp`/`.md`/`.toml` files there (403 otherwise). A saved file keeps its line ending (CRLF stays CRLF); new files are LF.

Stream events:
| event | data |
|---|---|
| `phase` | `{phase: configure\|build\|run, profile, requested, limitSec, buildType}` (`profile` = this run's, `requested` = the manifest's; `buildType`: `Debug` or `RelWithDebInfo`) |
| `build` | `{text}` configure/build output |
| `stdout`, `stderr` | `{text}` program output, sent at most every 100 ms |
| `trace` | `{events: [...]}` new 020-05 event lines (message, transition, node); `file` made repo-relative. Span lines never appear here |
| `spans` | `{full, rows: [{file, line, label, meter, count, totalNs, minNs, maxNs, p50Ns, p95Ns, hist: {loNs, hiNs, bins[20]}}], spanLines, lagBytes}`: the span keys changed since this stream's last `spans` event, with cumulative values. The batch that ends with `done` carries every key (`full: true`). No `id:` (not part of the replayable event list); a stream that connects late gets every key in its first `spans` event (`full: true` only once the run is done) |
| `done` | `{build: {ok, ms, diagnostics[], timedOut}, run: {exitCode, signal, timedOut, stopped, traceLimit, ms, truncated} \| null, diagrams[], skippedTraceLines, stopped}` |

Limits (the `PROFILES` table in `runner.py`):

| Profile | Build | Run | Output | Trace file | Preset |
|---|---|---|---|---|---|
| `quick` | 120 s | 10 s | 1 MiB each for stdout and stderr | 1 GiB | `linux-x64-playground` (Debug); `[run] build = "release"` → `linux-x64-playground-release` |
| `long` | 180 s | the lesson's `[run] timeout` (300 s default, 1800 s max) | 8 MiB for stdout and stderr together; the page keeps the last 5,000 lines | 1 GiB | `linux-x64-playground-release` (RelWithDebInfo); `[run] build = "debug"` → Debug |

The profile is the manifest's unless the page's **길게 실행** toggle picks the other one for this run (`profileOverride`). Over the trace-file budget the run is stopped (`done.run.traceLimit`): the program keeps writing the file even when the server stops reading it. Closing the page while a lesson runs stops it.

Span timings (spec 070-06 §2.4 has the design record and the alternatives): span lines are not sent one by one. Every 100 ms the server reads the trace file in pieces of at most 4 MiB (more pieces, for up to 250 ms, while it is behind), adds each span to a per-key aggregate (exact count, total, min, max, and a uniform sample of 1,024 durations over the whole run for p50, p95 and the distribution bars) and sends the changed keys as `spans` events. Memory depends on the number of keys, not of spans. When the server falls behind, `lagBytes` says how far and the page shows "집계 지연". Every run gets `ATUGCC_TRACE_FLUSH_MS=100`, so the program flushes its trace at most every 100 ms: after a crash, or while a program that wrote within the last interval stays quiet, the last lines can be missing or late (KI-016).

How a run works: `cmake --preset <preset>` when `.agent/scripts/build.py` would configure (no build directory, an interrupted configure, a preset file newer than the cache, a directory made for another checkout), `cmake --build --preset <preset> --target lesson_<id>`, then `stdbuf -oL -eL out/build/<preset>/bin/lessons/lesson_<id>` in the lesson folder with `ATUGCC_TRACE_OUT` set to a temporary file (read every 100 ms), `ATUGCC_TRACE_FLUSH_MS=100` and, when chosen, `ATUGCC_SPAN_METER`. Every child runs in its own session and is killed as a group on Stop, on the time limit and after it exits, so what the program starts ends with the run, unless it detaches into a new session itself (`setsid`, KI-015). An ASan-built program gets `verify_asan_link_order=0` in `ASAN_OPTIONS`, since `stdbuf` works through `LD_PRELOAD`.

## Page
- Left: tracks and lessons; units with the lessons that use them. ↻ reloads the index (new lesson folders).
- Center: Monaco tabs for the lesson's sources and the files of its `uses`. 🔒 = read-only; ● = modified; Ctrl+S saves; Ctrl+Enter or Run saves every modified tab and runs. Compiler diagnostics become markers.
- When the window gets focus again, unmodified tabs reload from disk; a modified tab whose file changed is marked, and saving it asks: reload from disk / overwrite / cancel.
- Top: **길게 실행** (this run's profile; it starts at the manifest's), **측정기** (`wall` = elapsed time, `cpu` = thread CPU time), the phase with its build type and the time left.
- Right: **README** (sanitized Markdown, relative links open inside the page), **Output** (ANSI colors mapped to the page's tokens), **Diagrams** (Mermaid parts; never below 80 %, wide ones scroll; "전체 크기" opens the natural size), **Events** (seq order; click to highlight the source line), **Timings**.
- **Timings** (070-06): one row per (label, file:line, meter) with count, total, mean, p50, p95, min, max and the change of the mean against the previous run of the same lesson (kept in the browser's storage; "빌드 다름" when the build type differs; the column is empty when storage is blocked). It updates while the run goes and opens by itself at the first span of a run. Click a header to sort, a row to jump to its line, ▸ for the distribution bars. The editor shows `⏱ <mean> avg ×<count>` at the end of each span's start line (rows on one line merged), cleared at the next Run.

## Tests
| What | Command |
|---|---|
| Server (files, guard, runner, SSE) | CTest `PlaygroundServer` in `py -3 .agent/scripts/build.py --preset linux-x64-debug --test`; alone: `python3 web/server/test_server.py --fixture out/build/linux-x64-debug/bin/playground_fixture` (without `--fixture` only the file and request tests run) |
| Frontend | `npm --prefix web/frontend ci`, then `npm --prefix web/frontend run build` and `npm --prefix web/frontend test` (Timings helpers: `test/timings.test.ts`) |
| Mermaid fixture | `python3 web/server/capture_diagrams.py` (WSL), after changing a lesson or the diagram generator |
