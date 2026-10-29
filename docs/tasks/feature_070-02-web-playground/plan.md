# Plan: 070-02 로컬 웹 플레이그라운드

- Spec: [/docs/specs/070_02_web_playground.md](/docs/specs/070_02_web_playground.md) (approved 2026-10-28)
- Branch: `feature/070-02-web-playground` (from `main` at `eb86fd1`, after 020-05 and 070-01)

## Design (fixed by the lead; units implement exactly this)

### D1. Preset `linux-x64-playground`
Configure preset inherits `linux-x64-debug` and sets `ATUGCC_BUILD_TESTS=OFF`, `ATUGCC_BUILD_SAMPLES=OFF`, `ATUGCC_BUILD_LESSONS=ON`; a build preset with the same name. Own build directory `out/build/linux-x64-playground`, so a playground build never holds the ninja lock of `linux-x64-debug`.

### D2. `web/server/files.py` — repository file access (AC-3, AC-4)
- `RepoFiles(root)`. Paths come in as repo-relative strings with `/`.
- `resolve(path)` raises `PathError(status, message)`:
  - 400: empty path, NUL byte, backslash, absolute path (`/x`, `C:x`, `//host`), a `..` or `.` component, a component starting with `.` (`.git`, `.env`), or a resolved path outside the root (symlink escape: `Path.resolve()` then `relative_to(root.resolve())`);
  - 404: not a regular file (read).
- `read(path) -> {path, content, sha, eol, writable}`: `sha` = SHA-256 hex of the bytes on disk; `eol` = `"crlf"` when the file contains `\r\n`, else `"lf"`; `content` is the text decoded as UTF-8 (replacement chars on bad bytes) with CRLF folded to LF, so the editor always works on LF.
- `writable(path)`: inside `lessons/` and either an existing regular file, or a new file whose suffix is `.cpp`, `.hpp`, `.md` or `.toml`. Anything else → 403.
- `write(path, content, base_sha) -> {sha}`:
  - existing file: `base_sha` must equal the disk sha, else `Conflict(content, sha)` (→ 409 with the disk content); the text is written with the file's own `eol`;
  - new file: `base_sha` must be `null` (a file that appeared meanwhile is a conflict); parent folders under `lessons/` are created; LF;
  - written as UTF-8 to a temporary file in the same folder, then `os.replace` (the editor or a build never sees half a file).

### D3. `web/server/runner.py` — build, run, stream (AC-5, AC-11, AC-12)
- `PROFILES = {"quick": Limits(build_sec=120, run_sec=10, output_bytes=1 MiB)}` — the one table 070-06 extends. A `long` lesson runs with `quick` limits and its `phase` event carries `requested: "long"` so the page can show the 070-06 note.
- `Job`: id (uuid4 hex), lesson id, list of `(event, data)` kept for the whole job (a late or reconnecting stream starts from the first event), `threading.Condition`, `state` (`queued`/`running`/`done`), `stop_requested`.
- `RunManager(root, preset, launcher=None)`: one worker thread takes jobs from a FIFO queue, so builds and runs are serialized; `create(lesson) -> Job`, `get(id)`, `stop(id)`; keeps the last 20 finished jobs.
- Steps of one job (all children in their own session, `start_new_session=True`, killed with `os.killpg(pgid, SIGKILL)`):
  1. configure when `build_dir/build.ninja` is missing or `CMakePresets.json` is newer than the cache: `cmake --preset linux-x64-playground` (phase `configure`, output as `build` events);
  2. `cmake --build --preset linux-x64-playground --target lesson_<id>` (phase `build`); limit `build_sec` → killed, `build.ok=false`. Build failure never runs a previous binary.
  3. run `stdbuf -oL -eL <bin>/lessons/lesson_<id>` (phase `run`) with `cwd` = the lesson folder, `ATUGCC_TRACE_OUT=<per-job temp file>`, `DISPLAY`/`WAYLAND_DISPLAY` removed (no desktop console window), stdin `/dev/null`.
- Collection: one reader thread per pipe (`os.read` chunks, incremental UTF-8 decoder); a 100 ms flush loop sends the accumulated `stdout`/`stderr`/`build` text and the trace lines completed since the last flush. Each of stdout and stderr keeps at most `output_bytes`; the rest is dropped and `truncated=true`.
- Time limit and Stop: the flush loop checks the deadline and `stop_requested`; either kills the process group. After the main process exits the group is killed too, so no grandchild survives. Stop on a queued job ends it at once with `done{stopped:true}`.
- Trace: `file` becomes repo-relative (absolute, or relative to the build directory → resolved → relative to the root; outside the root it stays as is); `diagram` lines go to `done.diagrams[]` instead of `trace`; a line that is not JSON or has no `kind` counts in `skippedTraceLines`.
- Diagnostics: `^(?P<file>[^:\n]+):(?P<line>\d+):(?P<col>\d+): (?P<sev>error|warning|note): (?P<msg>.*)$` over the build log, file made repo-relative the same way, at most 200.
- `done`: `{build:{ok, ms, diagnostics}, run:{exitCode, signal, timedOut, stopped, ms, truncated} | null, diagrams, skippedTraceLines}`; `signal` is the signal name when the process died by a signal.
- `RunManager` takes an optional `executable(lesson) -> argv` override and a `build` switch so tests can run a fixture binary without building a lesson.

### D4. `web/server/server.py` — HTTP API (AC-9, AC-11, AC-12)
- `ThreadingHTTPServer` bound to `127.0.0.1` only (no option to change it); `--port` (default 8765), on `EADDRINUSE` the next of 20 ports; prints `atugcc playground: http://127.0.0.1:<port>/`.
- Request guard (local server that runs code): `Host` must be `127.0.0.1:<port>` or `localhost:<port>` (DNS rebinding); a request with an `Origin` header must come from the same host (another site cannot drive the API); `PUT`/`POST` need `Content-Type: application/json` (no simple cross-site form posts). Violations → 403.
- Routes as spec §2.2. `/api/lessons` = `lessons.index()` plus `problems` (ERROR findings of `lessons.check`, as strings). `/api/health` = `{version: 1, preset, compiler}` (`CMAKE_CXX_COMPILER_ID`/`_VERSION` from the playground cache, else `g++ --version`).
- SSE: sends every event of the job from the start, then waits on the job's condition; while idle it writes a `: ping` comment every 250 ms, so a closed tab is detected within about 0.5 s and the job is stopped (spec: stream closed → stop).
- Static: `web/frontend/dist`, `/` → `index.html`; paths are resolved inside `dist` only. Missing `dist` → a short page that names `py -3 tools/playground.py`.

### D5. `tools/playground.py` — launcher
- `--port`, `--dev` (Vite dev server with `/api` proxy, plus the API server), `--no-frontend-build`.
- Frontend build (host Node): `npm ci` when `node_modules` is missing or older than `package-lock.json`; `npm run build` when `dist/index.html` is older than any file in `src/`, `index.html`, `package.json` or `vite.config.ts`.
- Windows host: then `wsl.exe [-d $ATUGCC_WSL_DISTRO] --cd <repo> --exec python3 web/server/server.py --port N`; Linux: the same command directly.
- `.vscode/tasks.json`: `Playground: start` and `Playground: start (dev)`, `windows.command` = `py -3`, others `python3`; background tasks.

### D6. Frontend (`web/frontend`, Vite + TypeScript)
- Pinned versions in `package.json` (exact, no `^`), `package-lock.json` committed. `node_modules/` and `dist/` ignored.
- Monaco: `monaco-editor/esm/vs/editor/editor.api` + C++/Markdown/INI(toml) basic languages; only the editor worker.
- Modules: `api.ts` (fetch + EventSource wrapper), `lessonTree.ts`, `editor.ts` (tabs, models keyed by path, dirty ●, read-only lock, Ctrl+S, conflict dialog, focus refresh, markers, line highlight), `diagnostics.ts` (pure: diagnostics → markers per file), `output.ts`, `ansi.ts` (stateful SGR parser → spans with token classes, HTML escaped, sequences split across chunks), `diagrams.ts` (Mermaid per part; `fitScale(natural, available) = clamp(available/natural, 0.8, 1)`; error box with the source; full-size view in a dialog), `events.ts` (sorted by seq, click → open file and highlight line), `readme.ts` (marked + DOMPurify; relative `.md` links open in the README tab, other repo files in the editor), `main.ts`, `theme.css` (tokens for light/dark).
- Tests (vitest, jsdom): `ansi.test.ts`, `diagnostics.test.ts`, `mermaidParse.test.ts` (fixture: Mermaid parts captured from the seed lessons by `web/server/capture_diagrams.py`), plus `diagrams.test.ts` for `fitScale`.

### D7. Test fixture binary (tests/)
AC-5/11/12 need C++ programs that loop forever, print 2 MiB, or print one line per second (the C++ stdout buffering is what `stdbuf` fixes, so a shell script would not test it). They are not lessons (they must not appear in the lesson tree), so they are one test-only target `playground_fixture` in `tests/` (mode argument `loop | flood | tick | crash | spawn`). On Linux, CTest runs `python3 web/server/test_server.py --fixture $<TARGET_FILE:playground_fixture>` as `PlaygroundServer`. Spec §9 says "no C++ change": this adds a test program only (no library or lesson change); recorded in the spec History.

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `CMakePresets.json` | preset `linux-x64-playground` (D1) | WSL: `cmake --build --preset linux-x64-playground --target lesson_lambda_capture` | no | lead | cpp-reviewer: none | – | done |
| U2 | `web/server/files.py` | D2 | `test_server.py` FilesTest | no | lead | cpp-reviewer: symlinked folder write, save race → fixed; re-review: fixed | – | done |
| U3 | `web/server/runner.py` | D3 | `test_server.py` RunnerTest | no (Python; delegation §3 lists C++ risks) — gets a cross-family review anyway for its threads and process groups | lead | codex luna: build limit +1 s (fixed), setsid escape (KI-015) | 135k / 4k (with U5) | done |
| U4 | `tests/playground_fixture.cpp`, `tests/CMakeLists.txt` | D7 | both presets build; `ctest -R PlaygroundServer` | no | lead | cpp-reviewer: TSan launcher missing → fixed (`--` prefix); re-review: fixed | – | done |
| U5 | `web/server/server.py` | D4 | `test_server.py` ServerTest | no | lead | codex luna (with U3): guard and SSE none | (with U3) | done |
| U6 | `web/server/test_server.py` | tests for AC-3,4,5,9,11,12 + guard | runs green; each test fails against a mutated implementation | no | lead | cpp-reviewer: 3 weak tests → fixed; re-review: fixed | – | done |
| U7 | `tools/playground.py`, `.vscode/tasks.json`, `.gitignore` | D5 | `--help`; start on Windows, `/api/health` 200 | no | lead | cpp-reviewer: process cleanup → fixed; re-review: fixed | – | done |
| U8 | `web/frontend/*` scaffold, `api.ts`, `main.ts`, `lessonTree.ts`, `editor.ts`, `theme.css` | D6 | `npm run build` | no | lead | cpp-reviewer: data-loss races, stuck buttons → fixed; re-review: 2 residuals fixed by the lead (testrecord) | – | done |
| U9 | `ansi.ts`, `output.ts`, `diagrams.ts`, `events.ts`, `readme.ts`, `diagnostics.ts` | D6 | `npm run build` | no | lead | cpp-reviewer: fit padding, draw overlap, retry loop → fixed; re-review: fixed | – | done |
| U10 | `web/frontend/test/*`, `web/server/capture_diagrams.py` | AC-6, AC-8 tests | `npm test` | no | lead | cpp-reviewer: fixture check too strict → fixed; config test added | – | done |
| U11 | docs (spec §8 list) | README, web/README, lessons/README, agent_start_prompt, known_issues KI-010, config.md | `lint_docs.py` | no | lead | lead (Tester read against code) | – | done |

Manual ACs (1, 2, 6, 7, 8) are driven with a browser automation script kept outside the repo (installed Edge via `playwright-core`), with screenshots and assertions recorded in `testrecord.md`.
