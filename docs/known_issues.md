# Known Issues & Follow-ups

Every follow-up or non-blocking finding gets a `KI-NNN` id here and is referred to by that id from walkthroughs, testrecords and specs.

- **Status**: `OPEN`, `PLANNED` (a task owns it), `CLOSED` (with the closing task or commit).
- New entries go at the bottom with the next free id. Closed entries stay as a record.

| ID | Status | Area | Found | Owner |
|---|---|---|---|---|
| KI-001 | PLANNED | docs/cpp_evolution | 090-01 | lesson candidates (070-03, 070-04); `source_location.md` written by 010-08 |
| KI-002 | OPEN | legacy spec links | 090-01 | — (sealed, informational) |
| KI-003 | CLOSED | git / main | 090-01 | closed 2026-10-28 (fast-forward, user decision) |
| KI-004 | CLOSED | CMakePresets.json | 090-01 | closed by 090-01 Step 5 |
| KI-005 | CLOSED | pattern visualizer (all diagram backends) | 090-01 | closed by 020-04 |
| KI-006 | OPEN | docs diagrams | 090-01 | first task that adds a Mermaid block to `docs/` |
| KI-007 | CLOSED | Windows build / Boost | 090-01 | closed by 090-03 |
| KI-008 | PLANNED | `.claude/hooks/guard.py` | 090-01 | 090-06 |
| KI-009 | PLANNED | CMakeLists.txt (PQXX option) | 090-01 | 030-02 |
| KI-010 | OPEN | `formatDiagram` (Mermaid titles) | 020-04 | — (a Markdown output task; the web is not affected) |
| KI-011 | PLANNED | example output on Windows consoles | 020-04 | 090-06 |
| KI-012 | PLANNED | `.agent/scripts/build.py` (`--gtest-filter` on TSan) | 020-05 | 090-06 |
| KI-013 | CLOSED | `core::Logger` (source location) | 070-01 | closed by 010-08 |
| KI-014 | CLOSED | `core::Logger` (thread safety) | 070-01 | closed by 010-08 (shared-safe contract) |
| KI-015 | PLANNED | web playground runner (process tracking) | 070-02 | 070-05 (public use, user decision) |
| KI-016 | OPEN | `JsonLinesEventSink` flush interval (liveness) | 020-06 | — (accepted by 070-06; a revisit condition of 070-06 §2.4) |
| KI-017 | CLOSED | `tools/playground.py` (`--port` with `--dev`) | 070-02 | closed by 070-02-01 |
| KI-018 | OPEN | `npm run dev` start stall (`DevLaunchTest`) | 070-02-01 | — (investigate on the next occurrence) |
| KI-019 | CLOSED | links in `lessons/**/*.md` unchecked | 070-08 | closed by 090-04 |
| KI-020 | OPEN | `PlaygroundServer` span-flood pause under host load | 070-08 | — (investigate on the next occurrence) |
| KI-021 | CLOSED | `core::Logger` / `MemoryDump` (dump target per instance) | 090-05 | closed by 010-08 |
| KI-022 | OPEN | Tracer recording cost (messages, transitions, nodes) | 090-05 | — (when a lesson or feature needs the numbers) |
| KI-023 | PLANNED | legacy pattern headers (namespaces, non-inline definitions) | 090-05 | 021-01, 022-01, 023-03, 023-05, 024-01; 070-04 |
| KI-024 | OPEN | no CI | 090-05 | — (user decision) |
| KI-025 | CLOSED | `RingBuffer::flushToQueue` / `LogQueue` (many producers, no consumer) | 010-08 (review) | closed by 010-08 (auto-flush off; consumer: 010-09) |
| KI-026 | OPEN | Linux crash signal handler (async-signal-safety) | 010-08 (review) | 010-09 |
| KI-027 | OPEN | `<Windows.h>` reaches every user of `logger.hpp` | 010-08 | 010-09 |

## KI-001 — `docs/cpp_evolution` pages referenced but missing
Specs reference six evolution pages that do not exist: `cmake_modernization.md` (spec 01), `concepts.md` (03), `filesystem_format.md` (05), `source_location.md` (06), `trace_console_toggle.md` (08_001), `tracer_benchmarking.md` (08_002). Spec 04 still marks `chrono_format.md` as "(예정)" although the page exists.
**Next**: write them under Phase 5, or in the task that next touches each module; a new spec lists the page under Documentation Updates.
**Update (090-05)**: Phase 5 is now the [lesson candidate list](/docs/tasks/lesson_candidates.md); each page there is written as a lesson (070-03, 070-04) or with the task that next touches the module. `tracer_benchmarking.md` is no longer needed: 020-03 was cancelled (KI-022 keeps what it would have measured).
**Update (010-08)**: [`source_location.md`](/docs/cpp_evolution/source_location.md) is written.

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
**Next**: decide whether string output for Mermaid should put the title inside the fence or as a Markdown heading (a Markdown output task).
**Web (070-02)**: not affected. The playground reads `diagram` lines (020-05), which carry the title as a field and the part as a fenced block; the page strips the fence (`mermaidSource` in `web/frontend/src/diagrams.ts`) and shows the title as the card heading.

## KI-011 — `×` may print garbled on non-UTF-8 Windows consoles
Counts use the UTF-8 sign `×` (`C3 97`). `atugcc_pattern_example` does not switch the Windows console to UTF-8, so a cp949 console can show mojibake. Library output (strings) is correct UTF-8.
**Next**: set the console output code page in the example (next to the existing ANSI setup), or document `chcp 65001`.
Span output (020-06) has the same problem: the live line starts with `⏱` (U+23F1, `E2 8F B1`), and durations in the live line and the `formatTimings()` table use `µs` (U+00B5, `C2 B5`). Spec 020-06 §2.5 leaves a `[t]` fallback option to this item.

## KI-012 — `build.py --gtest-filter` fails silently on the TSan preset
`build.py --preset linux-x64-tsan --target atugcc_tests --gtest-filter <f>` runs the test binary directly. GCC 13's ThreadSanitizer aborts under the ASLR entropy of WSL2 / Ubuntu 24.04 kernels, so the run exits 66 with no output. `ctest` is not affected: `tests/CMakeLists.txt` adds a `setarch <arch> -R` launcher for TSan builds, and `--test` goes through ctest.
**Workaround**: `setarch $(uname -m) -R out/build/linux-x64-tsan/bin/atugcc_tests --gtest_filter=<f>` in WSL, or `--test`.
**Next**: `build.py` prefixes the same launcher when the preset's `ATUGCC_SANITIZERS` contains `thread`.

## KI-013 — `Logger::log(Level, ...)` records its own location, not the caller's
The overloads `log(fmt, args...)` and `log(Level, fmt, args...)` in `include/atugcc/core/logger.hpp` call `std::source_location::current()` inside their own body, so every line they write shows `logger.hpp:41` instead of the caller. Seen in the 070-01 lesson output. Only the overload that takes a `source_location` first reports the caller.
**Next**: take `std::source_location loc = std::source_location::current()` as a defaulted parameter (a format-string wrapper struct that captures the location is the usual way with a variadic `std::format_string`).
**Closed** by 010-08: `FormatWithLocation`, a `consteval` wrapper that takes the format string and the caller's `source_location`; call sites unchanged; `LoggerTest.RecordsCallerLocation` passes on MSVC and GCC.

## KI-014 — One `Logger` must not be used by two threads at once
`Logger::log` locks its mutex only around `history_`; `m_buffer.write(...)` (a `RingBuffer`, documented single-thread only) and the live-output write run outside it. Two threads logging through one `Logger` race on the ring buffer. ThreadSanitizer did not report it in 070-01 because the following `std::cout` write happened to order the threads. Found by codex review of 070-01 U4b; the lesson `thread_and_log` now gives each worker its own `Logger` and explains why.
**Next**: decide whether `Logger` is meant to be shared (then hold the lock across the ring-buffer write, or use a per-thread buffer) and state the contract in the header.
**Closed** by 010-08 (user decision 2026-10-30: one Logger may be shared): the Logger's own ring buffer is gone, the history is under the mutex, crash-dump lines go to the calling thread's `DbgBuf`, live output goes through `std::osyncstream`. TSan tests `SharedAcrossThreads` and `LiveOutputLinesDoNotInterleave` (mutants killed). The measured cost of sharing is in the 010-08 testrecord; per-thread buffers inside the shared Logger are 010-09.

## KI-015 — A lesson can leave a process the playground does not track
`web/server/runner.py` runs every build and lesson in its own session and kills the process group on Stop, on the time limit and after the program exits. A descendant that calls `setsid()` (or double-forks into a new session) leaves that group and survives the run; if it keeps the output pipe open, a reader thread stays blocked (a daemon thread, so the server still exits). Spec 070-02 accepts this: the playground is local and runs the user's own lessons. Found by codex review of 070-02 U3.
Such a descendant also delays the end of a run: after the main process exits, the runner waits up to 2 s per output reader for the pipe to close, so `done` can come later than the 1 s that Stop promises (codex review of 070-06 U4; unchanged by 070-06).
**Next**: a public playground (070-05) needs real isolation (cgroup or container per run), which also bounds memory and CPU.

## KI-016 — With a flush interval, the last lines can stay buffered while the program is quiet
`JsonLinesEventSink` with a flush interval (`ATUGCC_TRACE_FLUSH_MS`, spec 020-06 Assumption 6) flushes only inside a write, when the interval has passed since the last flush. Lines written less than one interval after a flush stay in the stream buffer until a later write finds the interval passed, the stream buffer fills, or the sink is destroyed. A program that writes a burst and then goes quiet (or blocks) shows the burst's tail late; a crash loses it. Interval 0 (the default) is not affected.
**Next**: 070-06 accepts it and tells the user on screen (spec 070-06 §4, crash case). A record written more than one interval after the last flush is flushed at once; records that follow it within the interval wait for the next record after that (or for exit), and are lost on a crash or kill. Fixing it in C++ (a flush timer in the sink, or the C++ aggregate stream of spec 070-06 §2.4 option B) is a new task when one of the revisit conditions in 070-06 §2.4 appears.

## KI-017 — `--port` does not move the page in `--dev` mode
`tools/playground.py --port N` sets the first port the API server tries. Without `--dev` the API server also serves the page, so `--port` is the page port. With `--dev` the page comes from the Vite dev server, which is fixed at 5173 (`DEV_PORT`, `strictPort` in `web/frontend/vite.config.ts`), so `--dev --port 9000` moves only the API server and the page stays on 5173. The user read `--port` as the page port. Found by the user after 070-02.
**Next**: make `--port` the page port in both modes: in `--dev`, pass it to Vite (and to the API server's `--allow-origin` list) and let the API server pick any free port, since the page reaches it through the Vite proxy. Update the `--help` text, `web/README.md` and the VS Code tasks to match.
**Closed** by 070-02-01: `--port` is the page port in both modes; with `--dev` the API server takes any free port.

## KI-018 — `npm run dev` sometimes printed nothing for 30 s under the launch test
During 070-02-01, `tools/test_playground.py` `DevLaunchTest` failed in four groups of consecutive runs (4, 5, 1, 1), each the first runs after `tools/playground.py` had been rewritten (an edit, a mutation-test restore, or `git switch` / merge): the launcher was alive and had printed `dev page:`, but `npm run dev` wrote not even its `> atugcc-playground@0.1.0 dev` banner within 30 s, so the page port refused connections. Between and after the groups, about 40 full runs passed (3–4 s each), `npm run dev` alone started 12/12 times in under 1 s, and the stall could not be brought back by rewriting `tools/playground.py` before a run. Cause unknown (candidates: console input shared by `wsl.exe` and `npm.cmd`, which both inherit the launcher's stdin; a host-side scan or lock). The test now fails at once when the launcher has ended and prints the launcher's whole output on failure.
**Next**: on the next occurrence, read that output; if `npm` is stuck before its banner, try `stdin=subprocess.DEVNULL` for the `wsl.exe` server (it never reads input) and see whether the stall goes away.

## KI-019 — Links in `lessons/` Markdown are not checked
`lint_docs.py` checks links only in top-level files and under `docs/`, `.agent/`, `.claude/` (`DOC_DIRS`). Links in `lessons/intro.md` and the lesson and unit READMEs are checked by nothing, so renaming a lesson folder (070-03, 070-04) breaks them silently. 070-08 checked the intro's 7 links once with a scratch script (testrecord R3). The page resolves links the same way as `lint_docs.py` (relative, or `/` from the repository root).
**Next**: add `"lessons"` to `DOC_DIRS` in `.agent/scripts/lint_docs.py` and fix whatever it reports; that also covers every lesson README.
**Closed** by 090-04: `lessons/` is in `DOC_DIRS`; the 8 Markdown files there had no broken link.

## KI-020 — `test_span_flood_keeps_memory_flat` failed once under host load
During 070-08 the full `linux-x64-debug` suite ran while the same machine built the frontend (Vite), drove headless Edge and served a second playground. `PlaygroundServer` failed one check: longest pause between span updates 1.01 s (limit 0.5 s). Run alone right after, it passed twice (0.23 s, 0.21 s); 070-06 recorded 0.32 s. 070-08 changed no server code.
**Next**: if it fails again without other load on the host, look at the server's tick under load; otherwise consider measuring the pause in CPU time of the server or relaxing the limit for shared hosts.

## KI-021 — Every `Logger` registers the crash handler and creates an empty dump file, whatever its config
`Logger` holds an `alog::MemoryDump` member ([logger.hpp](/include/atugcc/core/logger.hpp), `m_dump`). The `MemoryDump` constructor ([memory_dump.hpp](/include/atugcc/core/memory_dump.hpp)) registers the process-wide crash handler (`sigaction(SIGSEGV)` / `SetUnhandledExceptionFilter`) and opens `log/crash_dump_<time>.log` under the current directory. So every `Logger`:
- creates that file even with `Config::enableCrashDump = false`, and always in `log/`: `Config::dumpDir` is used only by `dump()`;
- overwrites the static `dump_fd_` (`dump_handle_` on Windows) without closing the previous one (`~MemoryDump` is defaulted): one descriptor leaks per extra `Logger`, and a crash writes only into the newest file;
- registers the handler again.
Seen 2026-10-29: 0-byte files in `lessons/tracks/02_patterns/01_device_state_machine/log/` (six, one per run, although the lesson sets `enableCrashDump = false`) and `lessons/tracks/01_essentials/02_thread_and_log/log/` (three in the same millisecond: the lesson creates three `Logger`s because of KI-014). `.gitignore` hides `log/`, so nothing reported it.
**Next**: 010-08: prepare the dump target only when `enableCrashDump` is set, in `dumpDir`, once per process (or close the previous one), and decide which component owns the process-wide handler.
**Closed** by 010-08: `MemoryDump::ensurePrepared(dir)` registers the handler and opens the file once per process; `Logger` calls it only with `enableCrashDump`; explicit prepares close the previous descriptor; an empty auto-prepared file is removed at normal exit (CTest `DumpPrepare_*`).

## KI-022 — Tracer cost of messages, transitions and nodes is not measured
Cancelled task 020-03 ([spec](/docs/specs/08_002_benchmark.md)) planned to report the cost of repeated `recordMessage`, `recordTransition` and `pushNode`, and of dedicated console output on/off. 020-06 measures only span recording (`tests/pattern/span_cost_probe.cpp`, CTest `SpanCost`, 020-06 AC-6 and AC-8), which the user judged enough on 2026-10-29.
**Next**: when a lesson or feature needs these numbers, add the scenarios to `span_cost_probe.cpp` (report only, no pass/fail threshold, as 020-03 planned) rather than a separate benchmark target.

## KI-023 — Legacy pattern headers: global namespaces and non-inline definitions in headers
`factory.hpp`, `decorator.hpp`, `command.hpp`, `iterator_concept.hpp` and `injection.hpp` under `include/atugcc/pattern/` put their code in top-level namespaces (`factory`, `decorator`, …) instead of `atugcc::pattern::*`, and define functions in the header without `inline` (`factorySample()` and the like; `injection.hpp` has three). A program that includes one of them from two translation units fails to link (multiple definition), so a lesson cannot share them with a unit or a second file. None has a test or Tracer calls; only `main.cpp` uses them, with every sample commented out except `iteratorSample()`. On 2026-10-29 the five samples built on `linux-x64-debug` (`-Wall -Wextra -Werror`) and ran to exit 0 (090-05 testrecord R1). `main.cpp` also keeps commented calls `astate::stateChangeSample()` and `observer::observerSample()` that no longer exist: 020-01 moved State and Observer to `atugcc::pattern::state` / `::observer`.
**Next**: each pattern task (021-01, 022-01, 023-03, 023-05, 024-01) fixes its own header; 070-04 removes the dead calls when it moves the `main.cpp` samples. Closed with the last of them.

## KI-024 — No CI: every check runs on one machine
The repository has no `.github/` workflow. Builds, tests and the docs gate run only locally (`build.py`, `lint_docs.py`), and at the 090-05 check the local `main` was 7 commits ahead of `origin/main`. A regression on another compiler or OS, or a skipped gate, shows only when someone runs it by hand.
**Next**: user decision: push, and add a CI workflow (Linux GCC presets and the docs gate first; Windows MSVC needs a runner with Visual Studio). It publishes to an outside service, so it is not done without that decision.

## KI-025 — Every thread pushes into a single-producer queue that nobody drains
`RingBuffer::write` calls `flushToQueue()` once the buffer is more than half full (128 of 256 blocks by default), and `flushToQueue()` pushes into `globalLogQueue()`, a `boost::lockfree::spsc_queue` ([log_queue.hpp](/include/atugcc/core/log_queue.hpp)): one producer thread only. Each thread's `DbgBuf` buffer is a producer, and so is each `Logger`'s own `m_buffer`, so two threads that log enough push at the same time: a data race (undefined behaviour) even when every thread has its own `Logger`, so the KI-014 workaround does not avoid it. No code outside `tests/core/test_ring_buffer.cpp` consumes the queue, so after 4096 blocks every flush fails and only `drop_count_` grows. Each `Logger::log` line is also stored three times (`history_`, `m_buffer`, the thread's `DbgBuf`), and `history_` at capacity shifts the whole vector under the mutex for every new line (`erase(begin)`). Found while weighing the KI-014 contract for 010-08 (2026-10-30); not yet reproduced under TSan.
**Next**: 010-08: one producer per queue (a queue per thread drained by one consumer, or a multi-producer queue), a consumer that owns output, one copy per line.
**Closed** by 010-08: `RingBuffer` no longer flushes by default (`kNoAutoFlush`), so no thread pushes into the queue implicitly and the crash buffer keeps the newest blocks; the Logger's duplicate ring buffer and the vector shift are gone. Explicit `flushToQueue()` is documented as single-producer. A consumer thread is 010-09.

## KI-026 — The Linux crash signal handler calls functions that are not async-signal-safe
`signalHandler` in [memory_dump.hpp](/include/atugcc/core/memory_dump.hpp) formats its messages and the dump header with `std::snprintf`, which POSIX does not list as async-signal-safe, and reads the executable path through a `const std::string&` (`getExePath()`); it does write only with `::write` to the descriptor prepared before the crash. A crash inside `malloc` or inside stdio can therefore deadlock or corrupt the dump. Found by codex review of 010-08 U2 (2026-10-30); 010-08 does not change the handler.
**Next**: 010-09, which reworks the crash dump to cover every thread's buffer: format the numbers with a small signal-safe integer-to-text helper and keep the executable path in a fixed `char` buffer filled at preparation time.

## KI-027 — `logger.hpp` brings `<Windows.h>` (and its `min` / `max` macros) into every user
`include/atugcc/core/logger.hpp` includes `memory_dump.hpp`, which includes `<Windows.h>` on Windows. Every file that uses `Logger` therefore gets the Win32 macros, and `std::min(a, b)` / `std::max(a, b)` stop compiling there (`error C2589`). Seen in 010-08: `tests/core/logger_contention_probe.cpp` failed on `windows-x64-debug` once a `NOMINMAX` that U2 had added to the public header was removed again (defining it in a public header changes the macros for code that wants them). The probe now writes `(std::min)(...)`. This predates 010-08: `Logger` included `memory_dump.hpp` before too, and it is the kind of exposure [impl.md](/.agent/rules/impl.md) §5 forbids for third-party headers.
**Next**: 010-09: `logger.hpp` needs only `MemoryDump::ensurePrepared` and `dump`; declare what it needs in a small header and keep `memory_dump.hpp` (and `<Windows.h>`) to `src/` and the files that install handlers.
