# Known Issues & Follow-ups

Every follow-up or non-blocking finding gets a `KI-NNN` id here and is referred to by that id from walkthroughs, testrecords and specs.

- **Status**: `OPEN`, `PLANNED` (a task owns it), `CLOSED` (with the closing task or commit).
- New entries go at the bottom with the next free id. Closed entries stay as a record.

| ID | Status | Area | Found | Owner |
|---|---|---|---|---|
| KI-001 | PLANNED | docs/cpp_evolution | 090-01 | Phase 5 (050-xx) |
| KI-002 | OPEN | legacy spec links | 090-01 | — (sealed, informational) |
| KI-003 | CLOSED | git / main | 090-01 | closed 2026-10-28 (fast-forward, user decision) |
| KI-004 | CLOSED | CMakePresets.json | 090-01 | closed by 090-01 Step 5 |
| KI-005 | PLANNED | pattern visualizer (all diagram backends) | 090-01 | 020-04 |
| KI-006 | OPEN | docs diagrams | 090-01 | first task that adds a Mermaid block to `docs/` |
| KI-007 | OPEN | Windows build / Boost | 090-01 | user decision |
| KI-008 | OPEN | `.claude/hooks/guard.py` | 090-01 | — |
| KI-009 | OPEN | CMakeLists.txt (PQXX option) | 090-01 | 030-02 |

## KI-001 — `docs/cpp_evolution` pages referenced but missing
Specs reference six evolution pages that do not exist: `cmake_modernization.md` (spec 01), `concepts.md` (03), `filesystem_format.md` (05), `source_location.md` (06), `trace_console_toggle.md` (08_001), `tracer_benchmarking.md` (08_002). Spec 04 still marks `chrono_format.md` as "(예정)" although the page exists.
**Next**: write them under Phase 5, or in the task that next touches each module; a new spec lists the page under Documentation Updates.

## KI-002 — Stale links in legacy specs
Specs 03, 04 and 05 link `/include/atugcc/core/ring_buffer.h`, the header's name at the time; it is now `ring_buffer.hpp`. Legacy specs are records of their round and are not edited (spec.md §5). The docs lint reports these as information, not errors.

## KI-003 — `main` is behind the integrated work
`main` is 8 commits behind `feature/dedicated-console`. Every feature branch is already merged linearly into that tip, so `main` can be fast-forwarded. Until then, new branches cannot follow the "branch from `main`" rule; 090-01 branched from `feature/dedicated-console` (spec 090-01 Assumption 7).
**Closed** 2026-10-28: the user approved the merge; `main` was fast-forwarded to the end of 090-01 (local; not pushed).

## KI-004 — Machine-specific paths in `CMakePresets.json`
`windows-base` hard-coded the vcpkg toolchain path and the Visual Studio Ninja path of one machine, which broke Non-negotiable Rule 1 and other machines' builds; `.agent/rules/CMakePresets.example.json` repeated them. The README's `ctest --preset windows-x64-debug` failed because no `testPresets` existed.
**Closed** (090-01 Step 5): presets hold no machine paths; the toolchain is chosen in `CMakeLists.txt` (`-DCMAKE_TOOLCHAIN_FILE`, `ATUGCC_VCPKG_ROOT`, `VCPKG_ROOT`, else system packages); Ninja comes from the VS developer environment; `testPresets` added; the example file was removed. Remaining Windows dependency: KI-007.

## KI-005 — Diagram formatters drop repeated messages
The sequence output of all three backends (`mermaid_formatter.hpp`, `plantuml_formatter.hpp`, `d2_formatter.hpp`) skips any `(from, to, action)` already seen, so a repeated call (e.g., an Observer broadcasting twice) is drawn once and its order is lost. The state output does the opposite and draws duplicate edges. No output bounds the diagram's width, so wide traces shrink to unreadable text in a web view. (The class-tree output drops duplicate relations too; that is correct for structure and stays, spec 020-04 Assumption 3.)
**Next**: 020-04 (rules: `.agent/rules/diagrams.md`, 090-01 Step 4).

## KI-006 — No size check for hand-written docs diagrams
[diagrams.md](/.agent/rules/diagrams.md) §4 limits `docs/` diagrams to 1000 × 1400 px, but nothing measures them. `docs/` has no Mermaid block today, so the check has nothing to do yet.
**Next**: the first task that adds a Mermaid block to `docs/` ports the ai_sec measuring script (vendored Mermaid in headless Chrome, sizes recorded and read by the docs lint).

## KI-007 — Windows build has no Boost on this machine
`windows-x64-debug` configures MSVC 19.51 but stops at `find_package(Boost)`: no standalone vcpkg exists on this machine, and the VS developer environment points `VCPKG_ROOT` at Visual Studio's bundled vcpkg, which supports manifest mode only and has no Boost. This is most likely why the README once said the env var "was not recognized" on Windows. Linux presets (debug, asan, tsan) build and pass in WSL with the system Boost 1.83.
**Options** (user decision): (a) add a `vcpkg.json` manifest with `boost-lockfree` (+ a `builtin-baseline`) so the bundled vcpkg installs it per build directory; (b) install a standalone vcpkg with Boost and set `ATUGCC_VCPKG_ROOT`; (c) keep Boost a system prerequisite and document it.

## KI-008 — Command hook matches text inside quoted strings
`guard.py` checks the whole command line, so a command that only *mentions* an ad-hoc configure (a heredoc writing test data, a `grep` for the pattern) is refused. Seen once in 090-01 while adding the hook's own tests.
**Workaround**: put such text in a file and run the file. A fix would strip quoted strings and heredoc bodies before matching.

## KI-009 — PostgreSQL include path in `CMakeLists.txt`
With `ATUGCC_ENABLE_PQXX=ON` on Windows, `CMakeLists.txt` sets `PostgreSQL_INCLUDE_DIR` to one machine's install directory. The option is off by default, so no preset is affected.
**Next**: 030-02 (pqxx adapter) moves it to a cache variable or `find_package(PostgreSQL)`.
