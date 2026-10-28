# Plan: 070-01 레슨 구조

- Spec: [/docs/specs/070_01_lesson_structure.md](/docs/specs/070_01_lesson_structure.md) (approved 2026-10-28)
- Branch: `feature/070-01-lesson-structure` (from `main` at `6506596`, after 020-05)

## Design (fixed by the lead; units implement exactly this)

### D1. `tools/lessons.py` (Python 3.11+ stdlib, importable)
- Repo root = `Path(__file__).resolve().parent.parent`; every function takes `root` so tests can use a temporary tree.
- Model (dataclasses): `Track(id, title, summary, path)`, `Lesson(id, title, summary, sources, uses, tags, profile, timeout, path, track)`, `Unit(id, title, summary, files, uses, path)`, `Catalog(tracks, lessons, units)`. `id` of a track = its folder name; order = folder-name sort (numeric prefix).
- `load(root) -> (Catalog, Report)`: reads `lessons/tracks/*/track.toml`, `lessons/tracks/*/*/lesson.toml`, `lessons/units/*/unit.toml`.
- Schema (`check`):
  | file | required | optional |
  |---|---|---|
  | `track.toml` | `title` (str) | `summary` |
  | `lesson.toml` | `id`, `title` (str), `sources` (non-empty list of str) | `summary`, `uses` (list of str), `tags` (list of str), `[run] profile` (`quick`/`long`, default `quick`), `[run] timeout` (int 1–1800, default 300) |
  | `unit.toml` | `id`, `title`, `files` (non-empty list of str) | `summary`, `uses` |
  - `id` matches `^[a-z0-9_]+$`; unique among lessons and unique among units (a lesson and a unit may share an id: the seed has both `lambda_capture`).
  - `sources` / `files`: relative, no `..`, the file exists in the lesson/unit folder.
  - `uses` items: `unit:<id>` (unit exists) or `lib:<path>` (`include/<path>` exists); anything else is an error.
  - Cycles among units through `uses` → error naming the cycle.
  - CMake reads three keys with regexes (D3), so `sources = [...]` must be on one line, and `profile` / `timeout`, when present, on one line each → error otherwise.
  - `timeout` set while the profile is `quick` → WARN (ignored).
  - Includes (WARN): for each lesson source and unit file, every `#include "units/<id>/..."` must name a unit, and every `#include "units/..."` or `#include "atugcc/..."` must be in the file owner's **transitive** `uses` closure.
  - TOML syntax error → ERROR with the file and the line when known.
- Findings print as `ERROR|WARN <repo-relative path>[:line]: message`; `check` exits 1 if any ERROR.
- `index(catalog) -> dict` (JSON, `"version": 1`):
  ```json
  {"version":1,
   "tracks":[{"id","title","summary","path","lessons":[
      {"id","title","summary","path","target":"lesson_<id>","entry","sources":[…],"readme":"…|null",
       "uses":["unit:…","lib:…"],"files":[…],"tags":[…],"run":{"profile","timeout"}}]}],
   "units":[{"id","title","summary","path","files":[…],"readme","uses":[…],"usedBy":["<lesson id>", …]}]}
  ```
  All paths repo-relative with `/`. `files` = transitive resolution of `uses` in order, without duplicates: for a unit its folder files (`files`, then `README.md` if present) then its own uses; for a lib its `include/<path>`. `usedBy` = lessons whose transitive closure contains the unit.
- CLI: `py -3 tools/lessons.py check [--root R]`, `py -3 tools/lessons.py index [--root R] [--out out/lessons/index.json]` (`-` = stdout).

### D2. `tools/test_lessons.py` (unittest, stdlib)
Builds temporary trees (no committed fixtures): one valid tree, then one broken tree per AC-3 case: duplicate id, missing `uses` target, unit cycle, missing source, TOML syntax error, include missing from `uses` (WARN), bad `profile`, out-of-range `timeout`, multi-line `sources`. Plus the real repo: `check` has no ERROR, and `index` gives `jthread_worker.usedBy` = the two seed lessons from two tracks (AC-4).

### D3. CMake
- Root `CMakeLists.txt`:
  - `option(ATUGCC_BUILD_LESSONS "Build lessons (lessons/)" ON)` next to the other options.
  - The TSan test launcher moves from `tests/CMakeLists.txt` to the root as `ATUGCC_TEST_LAUNCHER` (same logic: `setarch <arch> -R` when UNIX and `thread` in `ATUGCC_SANITIZERS`), so lesson smoke tests use it too. `tests/CMakeLists.txt` uses `${ATUGCC_TEST_LAUNCHER}` instead of its local variable.
  - After the tests block: `if (ATUGCC_BUILD_LESSONS) add_subdirectory(lessons) endif()`.
- `lessons/CMakeLists.txt`: `file(GLOB … CONFIGURE_DEPENDS tracks/*/*/lesson.toml)`; for each manifest read with `file(READ)` and regexes anchored at line start: `id = "…"`, `sources = [ "a", "b" ]` (one line), optional `profile = "quick|long"`, optional `timeout = N`. Missing id or sources → `FATAL_ERROR` naming the manifest and `tools/lessons.py check`.
  - `add_executable(lesson_<id> <dir>/<sources>)`, include dir `lessons/`, link `atugcc_core`, `RUNTIME_OUTPUT_DIRECTORY ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/lessons`.
  - When `ATUGCC_BUILD_TESTS`: `add_test(NAME lesson.<id> COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:lesson_<id>>)`, quick: `TIMEOUT 10`, `LABELS lesson`; long: `TIMEOUT <timeout>`, `LABELS lesson;long`.

### D4. Seed content (`lessons/`)
Namespace `atugcc::lessons::<unit_id>` for unit headers; every function `inline`; lesson programs print to stdout and finish in well under 1 s.
- `units/lambda_capture/` — `unit.toml`, `README.md`, `lambda_capture.hpp`: `makeCounterByValue(int start)` (`[count = start]() mutable`), `makeAdderByReference(int& total)` (`[&total]`), `makeGreeter(std::string name)` (init capture by move, returns `std::format`), `makeOwner(std::unique_ptr<int>)` (move-only lambda).
- `units/jthread_worker/` — `unit.toml` (uses `lib:atugcc/core/logger.hpp`), `README.md`, `jthread_worker.hpp`: class `PeriodicWorker(std::string name, std::chrono::milliseconds period, std::function<void(std::size_t tick)> task, atugcc::core::Logger& logger)`: runs `task(tick)` every `period` on a `std::jthread` until stop; waits with `std::condition_variable_any::wait_for(lock, stop_token, period, pred)` so a stop wakes it at once; logs start and stop through the logger; `requestStop()`, `join()` (added by the author so a lesson can read results before destruction; joining twice is safe through `joinable()`), `ticks()` (atomic); not copyable or movable; the `std::jthread` is the **last** member (destroyed first: stop + join before the other members go). Destructor default.
- `tracks/01_essentials/track.toml` (title "Essentials: 어느 시스템에나 필요한 것"), `tracks/02_patterns/track.toml` (title "Patterns: 상황에 맞게 적용하고 바꾸기").
- `tracks/01_essentials/01_lambda_capture/` — lesson `lambda_capture`, uses `unit:lambda_capture`; prints each capture kind's result; README: what each capture copies or references, 3 exercises.
- `tracks/01_essentials/02_thread_and_log/` — lesson `thread_and_log`, uses `unit:jthread_worker`, `lib:atugcc/core/logger.hpp`; a `Logger` with `Config{ .liveOutput = &std::cout, .enableCrashDump = false }`, two workers (20 ms, 30 ms) for about 200 ms, then stop; prints the tick counts. README: jthread vs thread, stop_token, exercises.
- `tracks/02_patterns/01_device_state_machine/` — lesson `device_state_machine`, uses `unit:jthread_worker`, `lib:atugcc/pattern/state.hpp`, `lib:atugcc/pattern/visualizer.hpp`; one worker drives a `state::Machine` (own `viz::Tracer`) IDLE→STANDBY→RUN with `schedule()` each tick; after the worker stops, prints `formatTerminal()` and `formatDiagram(DiagramBackend::Mermaid)`. The Machine is touched only by the worker thread until it is stopped and joined. README: State pattern with `std::variant`, how to change the transition rules, exercises.

### D5. Docs and lint
- `lint_docs.py` runs the `check` of `tools/lessons.py` (import, not subprocess) and reports its findings with the same levels; `test_agent_scripts.py` passes.
- `lessons/README.md` (new): structure, manifest schema, adding a lesson, run profiles, `ctest -L lesson`, `ctest -LE long`.
- `README.md`: Project Structure (`lessons/`, `tools/`), How to Build (`ATUGCC_BUILD_LESSONS`, running a lesson).
- `docs/agent_start_prompt.md` Quick reference: `py -3 tools/lessons.py check`.
- `.gitignore`: `out/` already ignored → no change (verify).

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `tools/lessons.py` (new) | D1 (+ CMake-view comparison, folder = unit id, absolute lib, non-UTF-8 after review) | `lessons.py check` 0 errors | no | lead | `cpp-reviewer`: check/CMake disagreements and 4 more → fixed | — | done |
| U2 | `tools/test_lessons.py` (new) | D2 (AC-3, AC-4), 27 tests after review | `py -3 tools/test_lessons.py` | no (test) | lead | `cpp-reviewer`: missing cases → added | — | done |
| U3 | `CMakeLists.txt`, `lessons/CMakeLists.txt` (new), `tests/CMakeLists.txt` (launcher only) | D3 (AC-2, AC-5) + `CMAKE_CONFIGURE_DEPENDS` per manifest | both presets build; R7–R9 | no | lead | `cpp-reviewer`: manifest edits did not reconfigure → fixed | — | done |
| U4a | `lessons/units/lambda_capture/*`, `lessons/tracks/*/track.toml`, `lessons/tracks/01_essentials/01_lambda_capture/*` | D4 | build + run both presets | no | lead | `cpp-reviewer`: exercise 2 (ASan needs a run) → fixed | — | done |
| U4b | `lessons/units/jthread_worker/*`, `lessons/tracks/01_essentials/02_thread_and_log/*`, `lessons/tracks/02_patterns/01_device_state_machine/*` | D4 (AC-1) | build + `ctest -L lesson` on both presets and TSan; direct TSan runs | yes (thread lifetime, stop token) | agy flash (2 attempts: shared Logger fixed via `--resume`) | codex luna (high): shared `Logger` race → fixed; 2nd review: resolved, one doc wording (lead) | 131k / 34k + 161k / 42k; reviews 230k / 3k, 103k / 3k | done |
| U5 | `.agent/scripts/lint_docs.py`, `.agent/scripts/test_agent_scripts.py` | D5 lint hook (AC-6) | `lint_docs.py` exit 0; `test_agent_scripts.py` 50 OK | no | lead | `cpp-reviewer`: none | — | done |
| U6 | `lessons/README.md`, `README.md`, `docs/agent_start_prompt.md` | D5 docs | `lint_docs.py` | no (doc) | lead | `cpp-reviewer`: one cosmetic (missing `py -3`) → fixed | — | done |
