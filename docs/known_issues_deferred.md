# Deferred Known Issues

Deferred known issues: revisit when the condition in the Owner column happens. `py -3 .agent/scripts/archive_docs.py` moves a KI here when its Status becomes DEFERRED; set the Status back to OPEN and run it again to move the KI to docs/known_issues.md.

| ID | Status | Area | Found | Owner |
|---|---|---|---|---|
| KI-006 | DEFERRED | docs diagrams | 090-01 | first task that adds a Mermaid block to `docs/` |
| KI-010 | DEFERRED | `formatDiagram` (Mermaid titles) | 020-04 | — (a Markdown output task; the web is not affected) |
| KI-016 | DEFERRED | `JsonLinesEventSink` flush interval (liveness) | 020-06 | — (accepted by 070-06; a revisit condition of 070-06 §2.4) |
| KI-018 | DEFERRED | `npm run dev` start stall (`DevLaunchTest`) | 070-02-01 | — (investigate on the next occurrence) |
| KI-020 | DEFERRED | `PlaygroundServer` span-flood pause under host load | 070-08 | — (investigate on the next occurrence) |
| KI-022 | DEFERRED | Tracer recording cost (messages, transitions, nodes) | 090-05 | — (when a lesson or feature needs the numbers) |
| KI-028 | DEFERRED | log consumer thread throughput ceiling | 010-09 | — (when a program needs more than ~0.5–0.8 M lines/s) |
| KI-029 | DEFERRED | log map arena has a fixed size | 010-10 | — (when a program has more live threads than `mappedBytes` holds) |
| KI-032 | DEFERRED | lesson colour output on consoles without VT processing | 090-06 (U3c) | — (when a lesson user runs lessons in a plain console host) |
| KI-033 | DEFERRED | C++23 features missing from the Linux toolchain (was: `std::print`, GCC 13) | 070-03 | — (when libstdc++ 15 reaches the Linux toolchain: range formatting, pipe `ranges::to`, `std::forward_like`) |
| KI-034 | DEFERRED | `lessons.py`: duplicate entries in `sources` / `files` | 070-03 (U1 review) | — (when a duplicate entry appears) |
| KI-036 | DEFERRED | `import std` / `import std.compat` | 070-13 (spec) | — (when the Linux standard library ships a `std` module and CMake's support is not experimental) |
| KI-037 | DEFERRED | clangd / IntelliSense with C++20 modules | 070-13 (spec) | — (when editor support for `import atugcc.core;` is needed) |
| KI-038 | DEFERRED | installed `atugcc.core` module not tested from a consumer project | 070-13 (spec) | — (with a packaging or CI task) |
| KI-039 | DEFERRED | lesson units cannot hold C++20 modules | 070-14 (spec) | — (when several lessons need to share one module) |
| KI-041 | DEFERRED | `build.py --report` (report folders accumulate, no history view) | 040-02 | — (when `out/test-reports/` grows large or runs need comparing) |
| KI-042 | DEFERRED | web playground (no per-case test view, no test report) | 070-15 (spec) | — (when lessons need more than failure markers on the editor lines) |
| KI-046 | DEFERRED | `lesson.testing` timed out once in a full Windows run | 040-01 | — (investigate on the next occurrence) |
| KI-047 | DEFERRED | `subagent_run.py` (no sub-agent preamble added by the runner) | 090-08 | — (when the runner moves into a shared kit with ai_sec) |

## KI-006 — No size check for hand-written docs diagrams
[diagrams.md](/.agent/rules/diagrams.md) §4 limits `docs/` diagrams to 1000 × 1400 px, but nothing measures them. `docs/` has no Mermaid block today, so the check has nothing to do yet.
**Next**: the first task that adds a Mermaid block to `docs/` ports the ai_sec measuring script (vendored Mermaid in headless Chrome, sizes recorded and read by the docs lint).

## KI-010 — Mermaid part titles sit outside the code fence
`formatDiagram(DiagramBackend::Mermaid)` writes a split part's title as `%% Sequence (k/n)` before the part's ```` ```mermaid ```` fence (plan D3), so in Markdown it renders as plain text rather than a Mermaid comment. The structured API is unaffected: `diagramParts()` returns the title as its own field, which is what a web viewer uses (diagrams.md §3).
**Next**: decide whether string output for Mermaid should put the title inside the fence or as a Markdown heading (a Markdown output task).
**Web (070-02)**: not affected. The playground reads `diagram` lines (020-05), which carry the title as a field and the part as a fenced block; the page strips the fence (`mermaidSource` in `web/frontend/src/diagrams.ts`) and shows the title as the card heading.

## KI-016 — With a flush interval, the last lines can stay buffered while the program is quiet
`JsonLinesEventSink` with a flush interval (`ATUGCC_TRACE_FLUSH_MS`, spec 020-06 Assumption 6) flushes only inside a write, when the interval has passed since the last flush. Lines written less than one interval after a flush stay in the stream buffer until a later write finds the interval passed, the stream buffer fills, or the sink is destroyed. A program that writes a burst and then goes quiet (or blocks) shows the burst's tail late; a crash loses it. Interval 0 (the default) is not affected.
**Next**: 070-06 accepts it and tells the user on screen (spec 070-06 §4, crash case). A record written more than one interval after the last flush is flushed at once; records that follow it within the interval wait for the next record after that (or for exit), and are lost on a crash or kill. Fixing it in C++ (a flush timer in the sink, or the C++ aggregate stream of spec 070-06 §2.4 option B) is a new task when one of the revisit conditions in 070-06 §2.4 appears.

## KI-018 — `npm run dev` sometimes printed nothing for 30 s under the launch test
During 070-02-01, `tools/test_playground.py` `DevLaunchTest` failed in four groups of consecutive runs (4, 5, 1, 1), each the first runs after `tools/playground.py` had been rewritten (an edit, a mutation-test restore, or `git switch` / merge): the launcher was alive and had printed `dev page:`, but `npm run dev` wrote not even its `> atugcc-playground@0.1.0 dev` banner within 30 s, so the page port refused connections. Between and after the groups, about 40 full runs passed (3–4 s each), `npm run dev` alone started 12/12 times in under 1 s, and the stall could not be brought back by rewriting `tools/playground.py` before a run. Cause unknown (candidates: console input shared by `wsl.exe` and `npm.cmd`, which both inherit the launcher's stdin; a host-side scan or lock). The test now fails at once when the launcher has ended and prints the launcher's whole output on failure.
**Next**: on the next occurrence, read that output; if `npm` is stuck before its banner, try `stdin=subprocess.DEVNULL` for the `wsl.exe` server (it never reads input) and see whether the stall goes away.
2026-11-04 (070-02-02): one failure in `tools/test_playground.py` (27 tests, 47.8 s instead of 9–14 s) on the first full run after a mutation restore rewrote `tools/playground.py`; the failing test's output was not kept. 7 later runs passed, 2 right after a rewrite.

## KI-020 — `test_span_flood_keeps_memory_flat` failed once under host load
During 070-08 the full `linux-x64-debug` suite ran while the same machine built the frontend (Vite), drove headless Edge and served a second playground. `PlaygroundServer` failed one check: longest pause between span updates 1.01 s (limit 0.5 s). Run alone right after, it passed twice (0.23 s, 0.21 s); 070-06 recorded 0.32 s. 070-08 changed no server code.
**Next**: if it fails again without other load on the host, look at the server's tick under load; otherwise consider measuring the pause in CPU time of the server or relaxing the limit for shared hosts.

## KI-022 — Tracer cost of messages, transitions and nodes is not measured
Cancelled task 020-03 ([spec](/docs/specs/08_002_benchmark.md)) planned to report the cost of repeated `recordMessage`, `recordTransition` and `pushNode`, and of dedicated console output on/off. 020-06 measures only span recording (`tests/pattern/span_cost_probe.cpp`, CTest `SpanCost`, 020-06 AC-6 and AC-8), which the user judged enough on 2026-10-29.
**Next**: when a lesson or feature needs these numbers, add the scenarios to `span_cost_probe.cpp` (report only, no pass/fail threshold, as 020-03 planned) rather than a separate benchmark target.

## KI-028 — One log consumer thread caps sustained Logger throughput at roughly 0.5–0.8 M lines/s
Since 010-09 every `Logger` line is delivered by one consumer thread. Release measurements (010-09 testrecord, AC-1, live output off): a shared `Logger` and a `Logger` per thread both reach about 0.8–0.87 M lines/s on Linux and 0.5–0.7 M lines/s on Windows, whatever the number of threads; the `DbgBuf` path, which the consumer only consumes, reaches 4–8 M lines/s. So the cost is the consumer's per-record work (assembling the text, sorting the batch, writing the history ring), about 1 µs a line. Below that rate the calling thread pays about 0.3–0.8 µs (p50) and the p99 stays near 1–4 µs, far below 010-08's shared Logger (17–35 µs at 4–8 threads). Above it, producers wait for space and, with the default `OverflowPolicy::BlockThenDrop`, drop after 100 ms (reported).
**Next**: when a program needs more: profile `drainLocked`; candidates are moving each record's text instead of copying it, merging per-buffer runs instead of sorting the whole batch, and skipping the history ring for Loggers that never call `snapshot()`.

## KI-029 — The log map's arena has a fixed size; threads beyond it are not recoverable
Since 010-10 the mapped file is sized once (`LogBufferConfig::mappedBytes`, default 8 MiB: about 60 thread buffers of the default 512 slots). Retired buffers are reused, so the limit is the number of threads alive at the same time. A thread that starts when the arena is full gets a heap buffer: its lines are delivered as usual but a SIGKILL loses its undelivered ones. This is reported once on stderr (`[atugcc] log map full ...`) and counted (`detail::mappedRefusals()`).
**Next**: when a program needs more: map additional segments (a second file or a second view of a larger file) instead of moving the first one; buffer addresses must never change (crash handler, 010-09 plan D2).

## KI-032 — Lessons print ANSI colour codes raw on a console without VT processing
`formatTerminal()` colours its output with ANSI escape sequences (`[1;36m` …). Windows Terminal interprets them, but a plain console host window (conhost, or the hidden console of the 090-06 `LessonConsoleCodePage` test) shows them as text (`[1m[1;36m══ Sequence Messages ══[0m`) unless the program turns on `ENABLE_VIRTUAL_TERMINAL_PROCESSING`. Lessons do not; only `atugcc_pattern_example` does, through `enableWindowsAnsi()` (KI-031). Seen in the screen buffer read by the 090-06 test; text and code page are correct.
**Next**: if lessons are used in a plain console host, the lesson console setup (`lessons/support/console_utf8.cpp`) can also turn on VT processing for a console stdout (and restore the mode on exit), or `formatTerminal` can skip colours when stdout is not a VT console.

## KI-033 — C++23 features missing from the Linux toolchain (was: lessons cannot use `std::print`, GCC 13)
Until 070-13 the web playground and the `linux-x64-*` presets built with GCC 13.3, which has no `<print>` (checked 2026-11-03 by compiling `#include <print>`); it arrives with GCC 14. Lessons must build on both presets, so the `format_text` lesson (070-03) uses `std::format` and mentions `std::print` only in its README and in exercise 3 (MSVC only). [`format.md`](/docs/cpp_evolution/format.md) said the same until 070-13.
**Next**: what remains is range formatting (`std::format("{}", vector)`), the pipe form of `std::ranges::to` and `std::forward_like`, all waiting for libstdc++ 15 on Linux. When the Linux toolchain has them, a task moves them from the essentials READMEs and MSVC-only exercises into lesson code.
**Update 2026-11-03 (070-13)**: the Linux presets now build with Clang 20 and libstdc++ 14. Checked by compiling and running on both: `<print>`, `std::chrono::parse`, `std::chrono::clock_cast`, deducing this (explicit object parameter) work. Still missing on Linux: **range formatting** (`std::format("{}", vector)`, libstdc++ 15) and the **pipe form of `std::ranges::to`** (`v | std::ranges::to<std::vector>()`, a Clang 20 + libstdc++ 14.2 `forward_like` error; the call form `std::ranges::to<std::vector>(v)` builds). Lessons keep those two in READMEs. The `std::print` step of `format_text` is task 070-14. The draft specs 070-11 and 070-12 are revised against this list before their approval.
**Update 2026-11-04 (070-11)**: `std::forward_like` itself fails too on Clang 20 + libstdc++ 14.2 ("function 'forward_like<…>' with deduced return type cannot be used before it is defined", also when called directly), so the missing list is range formatting, the pipe form of `ranges::to` and `std::forward_like`; the essentials lessons keep them in READMEs and MSVC-only exercises. Lesson code now uses what builds: deducing this with an `auto&` return (`const_correctness`) and the call form `std::ranges::to<std::vector>(view)` (`ranges_views`).
**Update 2026-11-04 (070-14)**: the `format_text` lesson now has a `std::print` / `std::println` step (step 7), and its exercise 3 no longer depends on the toolchain. What remains is range formatting, the pipe form of `ranges::to` and `std::forward_like` (libstdc++ 15).

## KI-034 — `lessons.py` accepts duplicate entries in `sources` / `files`
A file listed twice in one lesson's `sources` (or a unit's `files`), e.g. `["main.cpp", "main.cpp"]`, is scanned twice, so its `#include`-vs-`uses` WARNs and the Hangul-literal WARNs of 070-03 appear twice. `load()` does not reject the duplicate. No manifest has one (found by the 070-03 U1 review).
**Next**: make `load()` report a duplicate entry (WARN, or ERROR because CMake would add the source twice) and check each file once.

## KI-036 — `import std` is not used
070-13 makes named modules build on both hosts but leaves `import std;` / `import std.compat;` out (user decision 2026-11-03). MSVC supports it; on Linux, libstdc++ 14 (the standard library of the Clang 20 presets) has no `std` module (it arrives with GCC 15), and CMake 4 still gates `import std` behind an experimental UUID that changes between releases. Lessons and tests must build from one source on both hosts.
**Next**: when the Linux toolchain has a `std` module (libstdc++ 15+, or a decision for libc++) and CMake's `import std` is no longer experimental, a task turns it on in the presets and decides where `#include <…>` gives way to `import std;`.

## KI-037 — Editor support for C++20 modules
With modules on (070-13), clangd needs `--experimental-modules-support` and a `compile_commands.json` that the module build can serve, and VS Code IntelliSense often does not resolve `import atugcc.core;`. The build is not affected; only editor diagnostics and completion are.
**Next**: when editor support is needed, try clangd 20 with `--experimental-modules-support` on `out/build/linux-x64-debug/compile_commands.json` and document the setting (or record why not).

## KI-038 — Installed module not tested from a consumer project
070-13 installs `modules/atugcc/core.cppm` with the `CXX_MODULES` file set on both hosts and checks the install tree, but no project outside the repository runs `find_package(atugcc)` and `import atugcc.core;` against the installed package (the consumer rebuilds the BMI from the installed interface).
**Next**: with a packaging or CI task, add a small consumer project that configures against `out/install/<preset>` and imports the module on both hosts.

## KI-039 — Lesson units cannot hold C++20 modules
070-14 lets a lesson list `.cppm` interface and partition files in its `sources`; `lessons/CMakeLists.txt` adds them to that lesson's own executable as a `CXX_MODULES` file set. Units (`lessons/units/`) are header-only: a lesson includes a unit's header and no CMake target owns unit files, so a module in a unit has nowhere to be built. `tools/lessons.py check` reports a `.cppm` in a unit's `files` as an ERROR.
**Next**: when several lessons need to share one module, give each unit that has `.cppm` files its own library target (with the file set) and link it into the lessons whose `uses` name the unit.

## KI-041 — Test report folders accumulate and cannot be compared
`build.py --report` without `DIR` makes a new `out/test-reports/<preset>/<YYYYMMDD-HHMMSS>/` per run (spec 040-02 Assumption 13) and nothing removes old ones; a full run's folder is about 140 KB (JUnit with every test's output). There is also no view across runs (a test getting slower, a flaky test). Both were left out of 040-02 (§6).
**Next**: when the folder grows large or a comparison is needed, add a cleanup (keep the last N per preset) and/or a history summary that reads several `run.json` + JUnit files.

## KI-042 — The web playground shows no per-case test results or test report
A GoogleTest lesson (spec 070-15) runs in the playground as one program without CTest (`linux-x64-playground` has `ATUGCC_BUILD_TESTS=OFF`), so there is no `build.py --report` and no `report.md`. The playground shows GoogleTest's console output and marks each `<file>:<line>: Failure` on the editor line (070-15 Assumption 10); a table of cases (passed, failed, time, message) is not shown. Reading a report is practised locally (`build.py --label lesson --report`).
**Next**: when a lesson needs it, add a Tests tab that reads a GoogleTest JSON of the run (the runner would set `GTEST_OUTPUT` to a temp file; today it removes every `GTEST_*` variable), one row per case, failures linking to the source line.

## KI-046 — `lesson.testing` timed out once in a full Windows run
During 040-01 the first full `windows-x64-debug` run (`build.py --test --report`, right after the build) reported `lesson.testing` as `***Timeout 13.07 sec` (limit 10 s; it normally takes 0.05 s). The report's failure block was empty and no `lesson_testing.json` was written to the run's `gtest/` folder, so the GoogleTest program stalled before it finished, or before it started. The host was busy: in the same run `CrashDump` took 121.7 s and `lesson.span_timing` 20.3 s. Five later runs passed: `--label lesson` twice without `--report`, once with `--report`, and the final full run with `--report` (13 cases in `lesson_testing.json`), plus the Linux full runs. 040-01 changed no lesson or test code (`lesson.testing` does not link `shape` or `sound`).
**Next**: on the next occurrence, see whether it is again the first run of a freshly linked lesson binary (a host-side scan of a new `.exe`, as KI-018 suspects for `npm`); if so, consider a longer timeout for lessons with `gtest = true`, or one warm-up run before timing.

## KI-047 — The runner does not tell a sub-agent to skip the boot sequence
Sub-agents run in the repo root, where `AGENTS.md` (codex) and the Antigravity rules point to the boot sequence. Since 090-08 the lead writes "You are a sub-agent ... do not run the repository's boot sequence" as the first line of every prompt ([delegation.md](/.agent/rules/delegation.md) §4). `subagent_run.py` could add that line itself, but it must stay identical to the ai_sec copy (its docstring).
**Next**: when the runner moves into a shared kit, add the line in the runner and drop it from the prompt rule.
