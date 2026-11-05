# atugcc

A C++20/23 framework library intended to explore and utilize modern C++ features.
This project has been restructured to separate public APIs from internal implementations and fully supports modern CMake (Presets, `FetchContent`, target-based configurations).

## Project Structure

```text
atugcc/
├── CMakeLists.txt        # Root CMake configuration (CMake 4.0+, target-based, C++20 modules always on)
├── CMakePresets.json     # CMake configuration presets for MSVC (Windows) / Clang 20 (Linux)
├── modules/atugcc/       # C++20 module interface units (`import atugcc.core;`)
├── main.cpp              # Sample application entry point
├── include/
│   └── atugcc/           # Public API headers representing the logical structure
│       ├── core/         # Core utilities (RingBuffer, TimeStamp, logging, etc.)
│       ├── pattern/      # Modern design pattern templates
│       └── backend/      # (planned, Phase 3) Interfaces for external dependencies
├── src/                  # Internal implementation files (.cpp, .cppm)
│   ├── core/             # Implementations for core utilities
│   ├── pattern/          # Implementations for design patterns
│   └── backends/         # (planned, Phase 3) Backend implementations (e.g., PostgreSQL)
├── libs/                 # General-purpose framework libraries, one folder each: libs/<name>/ (candidates: docs/lib_candidates.md)
├── sample/               # Various implementation examples and legacy samples; sample/libs/: static (shape) and shared (sound) library build examples
├── tests/                # GoogleTest unit and scenario tests, probe tests (tests/README.md)
├── lessons/              # Lessons for learning and practice: tracks, lessons, reusable units (lessons/README.md)
├── tools/                # Developer tools (lessons.py: lesson check and index, playground.py, symbolize_dump.py)
├── web/                  # Local web playground: Python server (web/server) + Vite/TypeScript page (web/frontend)
└── docs/                 # Documentation directory
    ├── agent_start_prompt.md  # Boot sequence for AI agents (see below)
    ├── agent_todo.md     # Task list: IDs, states and the order of open tasks
    ├── known_issues.md   # Follow-ups and non-blocking findings (KI-NNN)
    ├── lesson_candidates.md   # Lesson topics for the playground and their state
    ├── lib_candidates.md # Library candidates for libs/ and the layering core → libs → engine (Korean)
    ├── cpp_evolution.md  # Study index: legacy C++ → C++20/23, one row per page (Korean; English: cpp_evolution.en.md)
    ├── cpp_evolution/    # One page per topic, <topic>.md (Korean) + <topic>.en.md (English)
    ├── guides/           # Project blueprint, Linux build setup
    ├── specs/            # Technical specifications and design documents
    └── tasks/            # One record folder per task: plan.md, testrecord.md, walkthrough.md
```

## Features

- **Modern C++ Standard:** Targets C++23 as the baseline and leverages modern C++20/23 features (e.g., Concepts, Ranges, `std::expected`, `std::variant/visit`).
- **Modern CMake:** Employs target-centric modern CMake structure (CMake 4.0+).
- **C++20 modules:** every target that links `atugcc_core` can `import atugcc.core;` instead of including the core headers; both forms can be mixed (includes first). Module scanning is always on. See [`docs/cpp_evolution/modules.en.md`](docs/cpp_evolution/modules.en.md) (spec [070-13](docs/specs/070_13_modules_clang_toolchain.md)).
- **Platform Agnostic:** Built with MSVC (VS 2026) on Windows and Clang 20 with libstdc++ 14 on Linux, through one `CMakePresets.json`.
- **FetchContent:** Seamlessly integrates external dependencies (like `pqxx` for PostgreSQL or `gtest`) using CMake's `FetchContent`.
- **Test-Driven:** Test setups included using GoogleTest (`tests/`).
- **Pattern Tracer event stream:** set `ATUGCC_TRACE_OUT=<file>` and every `atugcc::pattern::viz::Tracer` writes its events (with source location and a process-wide `seq`) and its Mermaid diagram parts as JSON Lines, without code changes. Schema: [spec 020-05](docs/specs/020_05_tracer_event_stream.md) §2.2.
- **Logging that survives crashes:** `atugcc::core::Logger` can be shared by any number of threads without a lock on the hot path: each thread writes into its own buffer and one log thread delivers to the history, the live output and an optional file (`Config::filePath`). `Delivery::Sync` returns once the line is written, `flush()` waits for every earlier line. Every way a line can be lost is in the table below (spec [010-09](docs/specs/010_09_logger_thread_buffers.md) §2.4); at run time, dropped lines and log file errors are reported. Read a crash dump with `py -3 tools/read_dump.py log/crash_dump_<time>.log` (`--undelivered`: only lines that may be missing from the file).

  **Surviving SIGKILL** (spec [010-10](docs/specs/010_10_logger_mapped_buffers.md)): call `configureLogBuffers({.mappedDir = "log"})` as the first line of `main` (or set `ATUGCC_LOG_MAP_DIR=log`). The thread buffers then live in a memory-mapped file `log/atugcc-<pid>-<time>.logmap` that the OS keeps when the process is killed. The next run that turns mapping on (or calls `recoverLogMaps("log")`) writes what was in it to `log/recovered_<time>_<pid>.log`: every line that never reached a sink (`[undelivered]`) plus each thread's newest delivered lines for context; the log file itself is never changed. A clean exit removes the map file. `py -3 tools/read_dump.py <file>.logmap` reads a map file without recovering it. Off by default: buffers made before it is turned on, and buffers beyond `mappedBytes` (8 MiB by default, about 60 threads), stay in memory and are not recoverable.

  | When the program ends by | Log file (`Config::filePath`) | Crash dump (`log/crash_dump_*.log`) | Notes |
  |---|---|---|---|
  | `main` returning, `std::exit`, `std::quick_exit` | every line | — (an empty dump file is removed) | drained at exit; with `mappedDir`: map file removed, nothing recovered |
  | a thread ending | every line | its buffer is kept (retired) until reused | |
  | a `Logger` being destroyed | every line of that Logger | — | the destructor waits |
  | an unhandled C++ exception (`std::terminate`) | lines delivered within 200 ms | every thread's newest records (512 per thread by default) | then `abort` ; with `mappedDir`: the next run also writes a recovered file (`crash handler: yes`), which can overlap the dump |
  | `abort`, `assert`, SIGSEGV / SIGBUS / SIGFPE / SIGILL, a Windows exception, a stack overflow | lines written before the crash | every thread's newest records | signal-safe path only ; with `mappedDir`: the next run also writes a recovered file (`crash handler: yes`), which can overlap the dump |
  | a full buffer with `OverflowPolicy::BlockThenDrop` (default: after 100 ms) | a `[atugcc] dropped N lines` line | — | `Logger::droppedCount()`; `OverflowPolicy::Block` never drops, except a line logged from inside a sink (on the log thread) whose own buffer is full |
  | a log file that cannot be opened or written | the file misses lines | — | one `[atugcc] log file error` line on stderr per Logger |
  | SIGKILL, `TerminateProcess`, the OOM killer | lines already written (the last drain interval, 5 ms + 1 ms holdback + write time, can be lost) | none | with `mappedDir`: the next run writes every undelivered line of the mapped buffers to `recovered_<time>_<pid>.log` |
  | an OS crash or power loss | with `Durability::System`: lines already written; otherwise what the OS had not written to disk is lost | none | the map file is not flushed to disk: not covered |
  | `_exit`, a `fork()` child | not covered | not covered | |

- **Span timing:** `auto span = tracer.timeScope("parse");` times a code range (wall clock by default, thread CPU time with `ATUGCC_SPAN_METER=cpu`, or any `SpanMeter`), aggregates per source line, label and meter (`spanStats()`, `formatTimings()`), prints a `⏱` line when live output is on, and adds `span` lines to the event stream. `ATUGCC_TRACE_FLUSH_MS` sets the stream's flush interval for hot loops. Spec: [020-06](docs/specs/020_06_tracer_span_timing.md).

## How to Build

We recommend using CMake Presets.

### Using Visual Studio
Open the folder in Visual Studio 2026, and it should automatically read `CMakePresets.json` (the presets need CMake 4.0 or later, which VS 2026 bundles). Simply select a preset (e.g., `windows-x64-debug`) and build.

### Using CLI
```bash
# One command on any host: picks <host>-x64-debug, sets up MSVC (VsDevCmd) on Windows,
# runs Linux presets in WSL when called from Windows, then builds and tests.
py -3 .agent/scripts/build.py --test                       # Windows (Linux: python3)
py -3 .agent/scripts/build.py --preset linux-x64-asan --test
py -3 .agent/scripts/build.py --gtest-filter "Tracer*"     # one test suite
py -3 .agent/scripts/build.py --label scenario            # one kind: unit, scenario, probe, lesson
py -3 .agent/scripts/build.py --test --report             # + a test report in out/test-reports/
py -3 .agent/scripts/build.py --target lesson_lambda_capture   # one lesson (bin/lessons/)

# Plain CMake (Windows: inside a VS Developer prompt)
cmake --preset windows-x64-debug
cmake --build --preset windows-x64-debug
ctest --preset windows-x64-debug
ctest --preset windows-x64-debug -L scenario   # -L unit / scenario / probe / lesson
```

Test kinds, adding a scenario and reading a test report: [tests/README.md](tests/README.md).

### Lessons
Every `lessons/tracks/*/*/lesson.toml` builds into `bin/lessons/lesson_<id>` and a smoke test `lesson.<id>` (`ctest --preset <p> -L lesson`; `-LE long` skips long-running ones). Turn them off with `-DATUGCC_BUILD_LESSONS=OFF`. Check the manifests with `py -3 tools/lessons.py check`. See [lessons/README.md](lessons/README.md).

### Web Playground
Edit a lesson in the browser, build and run it, and watch its output, Tracer events and Mermaid diagrams stream in. The page works on the repository's own files and preset builds, so the same lesson can be worked on in VS Code and in the browser.

```bash
py -3 tools/playground.py --open     # or the VS Code task "Playground: start" (Linux: python3)
```
- Needs WSL with the Linux build tools (CMake 4, Ninja, Clang 20, Python 3.11+; [setup](docs/guides/linux_build_setup.md)) on Windows, and Node.js 20+ on the host for the first frontend build.
- Runs in the `linux-x64-playground` preset (long-profile lessons: `linux-x64-playground-release`); saves only under `lessons/` (`include/` and `src/` are read-only there).
- **ⓘ 소개** on the page (and its first screen) is [`lessons/intro.md`](lessons/intro.md): what the page is for and how the library and the lessons relate.
- **Local only.** The server runs whatever the lessons contain, so it listens on `127.0.0.1` and refuses requests from other sites. Do not expose it to a network.

Structure, API and tests: [web/README.md](web/README.md).

| Preset | Purpose |
|---|---|
| `windows-x64-{debug,release,relwithdebinfo}` | MSVC |
| `linux-x64-{debug,release,relwithdebinfo}` | Clang 20 (`clang++-20`, libstdc++ 14) |
| `linux-x64-asan` | Clang Debug + AddressSanitizer / UndefinedBehaviorSanitizer |
| `linux-x64-tsan` | Clang Debug + ThreadSanitizer (tests run without ASLR via `setarch -R`) |
| `linux-x64-playground` | Clang Debug, lessons only: the web playground's build |
| `linux-x64-playground-release` | Clang RelWithDebInfo, lessons only: the playground's long-profile build |

Every preset builds with warnings as errors (`ATUGCC_WARNINGS_AS_ERRORS=ON`) and with C++20 module scanning on (`CMAKE_CXX_SCAN_FOR_MODULES=ON`; configuring with it off fails).

## Workflow

### Where code goes
| You are writing | Put it in | Then |
|---|---|---|
| A library feature (logger, sink, pattern header) | `include/atugcc/` + `src/` (target `atugcc_core`), with a spec and tests | Show it in a lesson that references it with `uses = ["lib:atugcc/..."]`. Lessons link `atugcc_core` and include the headers in place, so a library change reaches every lesson at the next build. Nothing is copied. |
| Learning or practice code (syntax, a pattern variant) | `lessons/tracks/<track>/<NN_lesson>/`; code shared by several lessons in `lessons/units/<unit>/` | Build it with any preset, in VS Code or in the playground. |
| A rough experiment | `main.cpp` / `sample/` (target `atugcc_sample`) | Move it into a lesson once it runs cleanly. Every lesson is a smoke test (`lesson.<id>`: exit 0 within the time limit) and is checked by the docs gate, so a half-written lesson breaks both. |

### Adding a lesson
1. Copy a similar lesson folder to `lessons/tracks/<track>/<NN_name>/` (the number sets the order). If the code will be reused, also add `lessons/units/<unit>/` with `unit.toml`, `<unit>.hpp` and `README.md`.
2. Edit `lesson.toml`: `id`, `title`, `summary`, `sources`, `uses`. `uses` lists `"unit:<unit>"` and `"lib:atugcc/..."`; in the sources, include units as `"units/<unit>/<unit>.hpp"` and library headers as `"atugcc/..."`.
3. `py -3 tools/lessons.py check`
4. Build on Windows too: `py -3 .agent/scripts/build.py --target lesson_<id>`. The playground builds with Clang only, and lessons have to build warning-free with MSVC as well.
5. Open it in the playground (`py -3 tools/playground.py --open`, or ↻ if the page is already open) and Run.
6. Commit. There is no publish step: the playground reads the repository directly, and edits made in the browser are already in the working tree (`git diff`).

### How a lesson reaches the playground
```text
lesson.toml ──▶ CMake (line regexes: id, sources, profile, timeout) ──▶ target lesson_<id>, test lesson.<id>
            └─▶ tools/lessons.py (full TOML) ──▶ GET /api/lessons ──▶ tree, editor tabs (sources + files of uses)

browser ──▶ web/server/server.py (in WSL on Windows, Python on Linux; repository at /mnt/c/... under WSL)
              ├─ GET/PUT /api/files   read/write the repository's own files (writes only under lessons/)
              └─ POST /api/runs       cmake --build --preset linux-x64-playground[-release] --target lesson_<id>
                                      → run bin/lessons/lesson_<id> → stream output, Tracer events, spans
```
- CMake cannot parse TOML, so `id`, `sources`, `profile` and `timeout` stay on one line. `lessons.py check` reports any difference between the two readings.
- `uses` decides which files open as tabs. `#include` decides what gets compiled.
- On Windows only the launcher, the frontend build (`npm`) and the browser run on the host. The server, CMake, Clang and the lesson process run in WSL, with their own build directories (`out/build/linux-x64-playground*`).

## Environment-Specific Configuration

`CMakePresets.json` holds no machine-specific paths. Machine-specific settings come from the environment or from your own untracked `CMakeUserPresets.json`.

1. **vcpkg / Boost** (Boost.Lockfree is required by the build: `find_package(Boost REQUIRED)`; the logging code no longer uses it, spec 010-09). Dependencies are declared in the vcpkg manifest ([`vcpkg.json`](vcpkg.json), registry pinned in [`vcpkg-configuration.json`](vcpkg-configuration.json)); vcpkg installs them into the build directory on the first configure (network required once, then the vcpkg binary cache is reused). [`CMakeLists.txt`](CMakeLists.txt) picks the vcpkg toolchain in this order:
   1. `-DCMAKE_TOOLCHAIN_FILE=...` (or the `CMAKE_TOOLCHAIN_FILE` cache variable of a user preset),
   2. the environment variable `ATUGCC_VCPKG_ROOT` (optional: pick a particular vcpkg),
   3. the environment variable `VCPKG_ROOT`,
   4. otherwise no vcpkg: system packages (Ubuntu: `sudo apt install libboost-dev`).

   A variable is used only if `<root>/scripts/buildsystems/vcpkg.cmake` exists; otherwise the next option is tried.

   On Windows nothing needs to be set when building through the VS developer environment (`VsDevCmd`, which `build.py` calls): it sets `VCPKG_ROOT` to the vcpkg bundled with Visual Studio, and the manifest makes it install Boost. If your IDE starts CMake without that environment, set `VCPKG_ROOT` (or `ATUGCC_VCPKG_ROOT`) to any vcpkg; a standalone vcpkg works the same way.
2. **Ninja / MSVC**: run inside the VS developer environment. Visual Studio and VS Code (CMake Tools) do this themselves; on the command line `build.py` finds `VsDevCmd.bat` with `vswhere`, or set `VSDEVCMD`.
3. **Personal presets without env vars**: create `CMakeUserPresets.json` (ignored by git) and name presets after the platform so `build.py` knows where to run them:
   ```json
   {
     "version": 6,
     "configurePresets": [{
       "name": "windows-x64-debug-local",
       "inherits": "windows-x64-debug",
       "cacheVariables": { "CMAKE_TOOLCHAIN_FILE": "<your-vcpkg-root>/scripts/buildsystems/vcpkg.cmake" }
     }],
     "buildPresets": [{ "name": "windows-x64-debug-local", "configurePreset": "windows-x64-debug-local" }],
     "testPresets": [{ "name": "windows-x64-debug-local", "configurePreset": "windows-x64-debug-local", "output": { "outputOnFailure": true } }]
   }
   ```

## Working with AI Agents

`CLAUDE.md` (Claude Code), `AGENTS.md` (Codex and others) and `.agent/` (Antigravity) all point to one boot sequence, [`docs/agent_start_prompt.md`](docs/agent_start_prompt.md). Tasks carry IDs (`NNN-SS`) and states in `docs/agent_todo.md`; no implementation starts before its spec is approved.

## Phase Roadmaps

Check `docs/agent_todo.md` for current progress (task IDs and states). The development is organized into several phases:
- **Phase 0:** Project Base Setup & Modernization (Completed)
- **Phase 1:** Core Module Conversion (`atugcc::core`)
- **Phase 2:** Design Pattern Modernization (`atugcc::pattern`)
- **Phase 3:** Pluggable Backend Layer (`atugcc::backend`)
- **Phase 4:** Library Samples Modernization & CTest Scenario Tests
- **Phase 6:** Game Engine Core (`atugcc::engine`), every feature also playable in the web playground
- **Phase 7:** Local Web Playground and lessons (C++ evolution topics are lesson candidates: [`docs/lesson_candidates.md`](docs/lesson_candidates.md))
- **Phase 9:** Development Process & Maintenance

The order in which the open tasks are taken is at the top of `docs/agent_todo.md`.

