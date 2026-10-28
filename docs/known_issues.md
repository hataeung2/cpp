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
| KI-005 | CLOSED | pattern visualizer (all diagram backends) | 090-01 | closed by 020-04 |
| KI-006 | OPEN | docs diagrams | 090-01 | first task that adds a Mermaid block to `docs/` |
| KI-007 | CLOSED | Windows build / Boost | 090-01 | closed by 090-03 |
| KI-008 | OPEN | `.claude/hooks/guard.py` | 090-01 | — |
| KI-009 | OPEN | CMakeLists.txt (PQXX option) | 090-01 | 030-02 |
| KI-010 | OPEN | `formatDiagram` (Mermaid titles) | 020-04 | web playground task |
| KI-011 | OPEN | example output on Windows consoles | 020-04 | — |
| KI-012 | OPEN | `.agent/scripts/build.py` (`--gtest-filter` on TSan) | 020-05 | — |

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
**Closed** by 020-04: sequences keep every message in order and merge only consecutive repeats (`label ×N`); identical state edges merge into one with a count; long traces split into budgeted parts (`diagramParts`). Output is byte-identical to before for traces within every budget, without repeats, with labels not longer than `labelWrap` and (Mermaid) without `;` in labels (golden test `AC7_OutputUnchangedFromBeforeSplitting`); longer labels are now wrapped, Mermaid `;` is escaped, and a state machine over `maxStates` gets an `over budget` note.

## KI-006 — No size check for hand-written docs diagrams
[diagrams.md](/.agent/rules/diagrams.md) §4 limits `docs/` diagrams to 1000 × 1400 px, but nothing measures them. `docs/` has no Mermaid block today, so the check has nothing to do yet.
**Next**: the first task that adds a Mermaid block to `docs/` ports the ai_sec measuring script (vendored Mermaid in headless Chrome, sizes recorded and read by the docs lint).

## KI-007 — Windows build has no Boost on this machine
`windows-x64-debug` configures MSVC 19.51 but stops at `find_package(Boost)`: no standalone vcpkg exists on this machine, and the VS developer environment points `VCPKG_ROOT` at Visual Studio's bundled vcpkg, which supports manifest mode only and has no Boost. This is most likely why the README once said the env var "was not recognized" on Windows. Linux presets (debug, asan, tsan) build and pass in WSL with the system Boost 1.83.
**Options** (user decision): (a) add a `vcpkg.json` manifest with `boost-lockfree` (+ a `builtin-baseline`) so the bundled vcpkg installs it per build directory; (b) install a standalone vcpkg with Boost and set `ATUGCC_VCPKG_ROOT`; (c) keep Boost a system prerequisite and document it.
**Closed** by 090-03 (option a, user decision 2026-10-28), with a git registry in `vcpkg-configuration.json` instead of `builtin-baseline` (the bundled vcpkg has no built-in ports): `vcpkg.json` + `vcpkg-configuration.json` (baseline = release 2026.07.29). `windows-x64-debug` now configures with the bundled vcpkg and no env var set, builds warning-free under `/W4 /WX`, and passes the suite.

## KI-008 — Command hook matches text inside quoted strings
`guard.py` checks the whole command line, so a command that only *mentions* an ad-hoc configure (a heredoc writing test data, a `grep` for the pattern) is refused. Seen once in 090-01 while adding the hook's own tests.
**Workaround**: put such text in a file and run the file. A fix would strip quoted strings and heredoc bodies before matching.

## KI-009 — PostgreSQL include path in `CMakeLists.txt`
With `ATUGCC_ENABLE_PQXX=ON` on Windows, `CMakeLists.txt` sets `PostgreSQL_INCLUDE_DIR` to one machine's install directory. The option is off by default, so no preset is affected.
**Next**: 030-02 (pqxx adapter) moves it to a cache variable or `find_package(PostgreSQL)`.

## KI-010 — Mermaid part titles sit outside the code fence
`formatDiagram(DiagramBackend::Mermaid)` writes a split part's title as `%% Sequence (k/n)` before the part's ```` ```mermaid ```` fence (plan D3), so in Markdown it renders as plain text rather than a Mermaid comment. The structured API is unaffected: `diagramParts()` returns the title as its own field, which is what a web viewer uses (diagrams.md §3).
**Next**: decide in the web playground task whether string output for Mermaid should put the title inside the fence or as a Markdown heading.

## KI-011 — `×` may print garbled on non-UTF-8 Windows consoles
Counts use the UTF-8 sign `×` (`C3 97`). `atugcc_pattern_example` does not switch the Windows console to UTF-8, so a cp949 console can show mojibake. Library output (strings) is correct UTF-8.
**Next**: set the console output code page in the example (next to the existing ANSI setup), or document `chcp 65001`.

## KI-012 — `build.py --gtest-filter` fails silently on the TSan preset
`build.py --preset linux-x64-tsan --target atugcc_tests --gtest-filter <f>` runs the test binary directly. GCC 13's ThreadSanitizer aborts under the ASLR entropy of WSL2 / Ubuntu 24.04 kernels, so the run exits 66 with no output. `ctest` is not affected: `tests/CMakeLists.txt` adds a `setarch <arch> -R` launcher for TSan builds, and `--test` goes through ctest.
**Workaround**: `setarch $(uname -m) -R out/build/linux-x64-tsan/bin/atugcc_tests --gtest_filter=<f>` in WSL, or `--test`.
**Next**: `build.py` prefixes the same launcher when the preset's `ATUGCC_SANITIZERS` contains `thread`.
