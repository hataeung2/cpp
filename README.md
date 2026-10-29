# atugcc

A C++20/23 framework library intended to explore and utilize modern C++ features.
This project has been restructured to separate public APIs from internal implementations and fully supports modern CMake (Presets, `FetchContent`, target-based configurations).

## Project Structure

```text
atugcc/
├── CMakeLists.txt        # Root CMake configuration (Modern CMake 3.26+, target-based)
├── CMakePresets.json     # CMake configuration presets for MSVC / GCC / Clang
├── main.cpp              # Sample application entry point
├── include/
│   └── atugcc/           # Public API headers representing the logical structure
│       ├── core/         # Core utilities (RingBuffer, TimeStamp, logging, etc.)
│       ├── pattern/      # Modern design pattern templates
│       ├── adapter/      # Interfaces for external dependencies
│       └── libs/         # Framework-provided library headers
├── src/                  # Internal implementation files (.cpp, .cppm)
│   ├── core/             # Implementations for core utilities
│   ├── pattern/          # Implementations for design patterns
│   └── adapters/         # Implementations for adapters (e.g., PostgreSQL adapter)
├── libs/                 # Independent internal or external sub-libraries (e.g., shape, sound)
├── sample/               # Various implementation examples and legacy samples
├── tests/                # Unit tests using GoogleTest
├── lessons/              # Lessons for learning and practice: tracks, lessons, reusable units (lessons/README.md)
├── tools/                # Developer tools (lessons.py: lesson check and index, playground.py, symbolize_dump.py)
├── web/                  # Local web playground: Python server (web/server) + Vite/TypeScript page (web/frontend)
└── docs/                 # Documentation directory
    ├── artifacts/        # Project architecture and design blueprint (project_blueprint.md)
    ├── learning/         # C++ evolution and implementation details (cpp_evolution.md)
    ├── specs/            # Technical specifications and design documents
    ├── tasks/            # Task tracking and assignment logs (agent_todo.md)
    ├── known_issues.md   # Follow-ups and non-blocking findings (KI-NNN)
    └── agent_start_prompt.md  # Boot sequence for AI agents (see below)
```

## Features

- **Modern C++ Standard:** Targets C++23 as the baseline and leverages modern C++20/23 features (e.g., Concepts, Ranges, `std::expected`, `std::variant/visit`).
- **Modern CMake:** Employs target-centric modern CMake structure, supporting C++20 modules (`FILE_SET CXX_MODULES`).
- **Platform Agnostic:** Built to support both MSVC (VS 2026) and GCC/Clang with unified `CMakePresets.json`.
- **FetchContent:** Seamlessly integrates external dependencies (like `pqxx` for PostgreSQL or `gtest`) using CMake's `FetchContent`.
- **Test-Driven:** Test setups included using GoogleTest (`tests/`).
- **Pattern Tracer event stream:** set `ATUGCC_TRACE_OUT=<file>` and every `atugcc::pattern::viz::Tracer` writes its events (with source location and a process-wide `seq`) and its Mermaid diagram parts as JSON Lines, without code changes. Schema: [spec 020-05](docs/specs/020_05_tracer_event_stream.md) §2.2.
- **Span timing:** `auto span = tracer.timeScope("parse");` times a code range (wall clock by default, thread CPU time with `ATUGCC_SPAN_METER=cpu`, or any `SpanMeter`), aggregates per source line, label and meter (`spanStats()`, `formatTimings()`), prints a `⏱` line when live output is on, and adds `span` lines to the event stream. `ATUGCC_TRACE_FLUSH_MS` sets the stream's flush interval for hot loops. Spec: [020-06](docs/specs/020_06_tracer_span_timing.md).

## How to Build

We recommend using CMake Presets.

### Using Visual Studio
Open the folder in Visual Studio 2022/2026, and it should automatically read `CMakePresets.json`. Simply select a preset (e.g., `windows-x64-debug`) and build.

### Using CLI
```bash
# One command on any host: picks <host>-x64-debug, sets up MSVC (VsDevCmd) on Windows,
# runs Linux presets in WSL when called from Windows, then builds and tests.
py -3 .agent/scripts/build.py --test                       # Windows (Linux: python3)
py -3 .agent/scripts/build.py --preset linux-x64-asan --test
py -3 .agent/scripts/build.py --gtest-filter "Tracer*"     # one test suite
py -3 .agent/scripts/build.py --target lesson_lambda_capture   # one lesson (bin/lessons/)

# Plain CMake (Windows: inside a VS Developer prompt)
cmake --preset windows-x64-debug
cmake --build --preset windows-x64-debug
ctest --preset windows-x64-debug
```

### Lessons
Every `lessons/tracks/*/*/lesson.toml` builds into `bin/lessons/lesson_<id>` and a smoke test `lesson.<id>` (`ctest --preset <p> -L lesson`; `-LE long` skips long-running ones). Turn them off with `-DATUGCC_BUILD_LESSONS=OFF`. Check the manifests with `py -3 tools/lessons.py check`. See [lessons/README.md](lessons/README.md).

### Web Playground
Edit a lesson in the browser, build and run it, and watch its output, Tracer events and Mermaid diagrams stream in. The page works on the repository's own files and preset builds, so the same lesson can be worked on in VS Code and in the browser.

```bash
py -3 tools/playground.py --open     # or the VS Code task "Playground: start" (Linux: python3)
```
- Needs WSL with the Linux build tools (CMake, Ninja, GCC, Python 3.11+) on Windows, and Node.js 20+ on the host for the first frontend build.
- Runs in the `linux-x64-playground` preset; saves only under `lessons/` (`include/` and `src/` are read-only there).
- **Local only.** The server runs whatever the lessons contain, so it listens on `127.0.0.1` and refuses requests from other sites. Do not expose it to a network.

Structure, API and tests: [web/README.md](web/README.md).

| Preset | Purpose |
|---|---|
| `windows-x64-{debug,release,relwithdebinfo}` | MSVC |
| `linux-x64-{debug,release,relwithdebinfo}` | GCC |
| `linux-x64-asan` | GCC Debug + AddressSanitizer / UndefinedBehaviorSanitizer |
| `linux-x64-tsan` | GCC Debug + ThreadSanitizer (tests run without ASLR via `setarch -R`) |
| `linux-x64-playground` | GCC Debug, lessons only: the web playground's build |

Every preset builds with warnings as errors (`ATUGCC_WARNINGS_AS_ERRORS=ON`).

## Environment-Specific Configuration

`CMakePresets.json` holds no machine-specific paths. Machine-specific settings come from the environment or from your own untracked `CMakeUserPresets.json`.

1. **vcpkg / Boost** (Boost.Lockfree is required). Dependencies are declared in the vcpkg manifest ([`vcpkg.json`](vcpkg.json), registry pinned in [`vcpkg-configuration.json`](vcpkg-configuration.json)); vcpkg installs them into the build directory on the first configure (network required once, then the vcpkg binary cache is reused). [`CMakeLists.txt`](CMakeLists.txt) picks the vcpkg toolchain in this order:
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

`CLAUDE.md` (Claude Code), `AGENTS.md` (Codex and others) and `.agent/` (Antigravity) all point to one boot sequence, [`docs/agent_start_prompt.md`](docs/agent_start_prompt.md). Tasks carry IDs (`NNN-SS`) and states in `docs/tasks/agent_todo.md`; no implementation starts before its spec is approved.

## Phase Roadmaps

Check `docs/tasks/agent_todo.md` for current progress (task IDs and states). The development is organized into several phases:
- **Phase 0:** Project Base Setup & Modernization (Completed)
- **Phase 1:** Core Module Conversion (`atugcc::core`)
- **Phase 2:** Design Pattern Modernization (`atugcc::pattern`)
- **Phase 3:** Adapter Layer (`atugcc::adapter`)
- **Phase 4:** Samples & Tests Modernization
- **Phase 5:** C++ Evolution Documentation

