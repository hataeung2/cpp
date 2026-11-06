# Known Issues & Follow-ups

Every follow-up or non-blocking finding gets a `KI-NNN` id here and is referred to by that id from walkthroughs, testrecords and specs.

- **Status**: `OPEN`, `PLANNED` (a task owns it), `DEFERRED` (revisit when the condition in the Owner column happens), `CLOSED` (with the closing task or commit, or `dropped: <reason>`).
- **The status decides the file**: OPEN and PLANNED stay here; DEFERRED lives in [known_issues_deferred.md](/docs/known_issues_deferred.md); CLOSED in [archive/known_issues_closed.md](/docs/archive/known_issues_closed.md), a sealed record. Change the Status cell, then run `py -3 .agent/scripts/archive_docs.py` to move the row and section. Nothing is deleted.
- New entries go at the bottom with the next free id across all three files (the highest id in any of them + 1).
- At boot, `py -3 .agent/scripts/lint_docs.py --boot` shows only this file's table; `--ki KI-NNN` prints one entry from any of the three files.

| ID | Status | Area | Found | Owner |
|---|---|---|---|---|
| KI-001 | PLANNED | docs/cpp_evolution | 090-01 | lesson candidates (070-04); `source_location.md` written by 010-08, `format.md` by 070-03, `concepts.md` by 070-11, `filesystem.md` by 070-12 |
| KI-009 | PLANNED | CMakeLists.txt (PQXX option) | 090-01 | 030-02 |
| KI-015 | PLANNED | web playground runner (process tracking) | 070-02 | 070-05 (public use, user decision) |
| KI-023 | PLANNED | legacy pattern headers (namespaces, non-inline definitions) | 090-05 | 021-01, 022-01, 023-03, 023-05, 024-01; 070-04 |
| KI-024 | OPEN | no CI | 090-05 | — (user decision) |

## KI-001 — `docs/cpp_evolution` pages referenced but missing
Specs reference six evolution pages that do not exist: `cmake_modernization.md` (spec 01), `concepts.md` (03), `filesystem_format.md` (05), `source_location.md` (06), `trace_console_toggle.md` (08_001), `tracer_benchmarking.md` (08_002). Spec 04 still marks `chrono_format.md` as "(예정)" although the page exists.
**Next**: write them under Phase 5, or in the task that next touches each module; a new spec lists the page under Documentation Updates.
**Update (090-05)**: Phase 5 is now the [lesson candidate list](/docs/lesson_candidates.md); each page there is written as a lesson (070-03, 070-04) or with the task that next touches the module. `tracer_benchmarking.md` is no longer needed: 020-03 was cancelled (KI-022 keeps what it would have measured).
**Update (010-08)**: [`source_location.md`](/docs/cpp_evolution/source_location.md) is written.
**Update (070-03)**: `filesystem_format.md` is split. The format half is [`format.md`](/docs/cpp_evolution/format.md) (lesson `format_text`); the filesystem half is left to 070-12 (candidate E9). `concepts.md` is left to 070-11 (E1).
**Update (070-11)**: [`concepts.md`](/docs/cpp_evolution/concepts.md) is written (lesson `concepts`).
**Update (070-12)**: [`filesystem.md`](/docs/cpp_evolution/filesystem.md) is written (lesson `filesystem_paths`), the filesystem half of `filesystem_format.md`. Still open: the pages of 070-04 and keeping the existing pages true to the code.

## KI-009 — PostgreSQL include path in `CMakeLists.txt`
With `ATUGCC_ENABLE_PQXX=ON` on Windows, `CMakeLists.txt` sets `PostgreSQL_INCLUDE_DIR` to one machine's install directory. The option is off by default, so no preset is affected.
**Next**: 030-02 (pqxx adapter) moves it to a cache variable or `find_package(PostgreSQL)`.

## KI-015 — A lesson can leave a process the playground does not track
`web/server/runner.py` runs every build and lesson in its own session and kills the process group on Stop, on the time limit and after the program exits. A descendant that calls `setsid()` (or double-forks into a new session) leaves that group and survives the run; if it keeps the output pipe open, a reader thread stays blocked (a daemon thread, so the server still exits). Spec 070-02 accepts this: the playground is local and runs the user's own lessons. Found by codex review of 070-02 U3.
Such a descendant also delays the end of a run: after the main process exits, the runner waits up to 2 s per output reader for the pipe to close, so `done` can come later than the 1 s that Stop promises (codex review of 070-06 U4; unchanged by 070-06).
**Next**: a public playground (070-05) needs real isolation (cgroup or container per run), which also bounds memory and CPU.

## KI-023 — Legacy pattern headers: global namespaces and non-inline definitions in headers
`factory.hpp`, `decorator.hpp`, `command.hpp`, `iterator_concept.hpp` and `injection.hpp` under `include/atugcc/pattern/` put their code in top-level namespaces (`factory`, `decorator`, …) instead of `atugcc::pattern::*`, and define functions in the header without `inline` (`factorySample()` and the like; `injection.hpp` has three). A program that includes one of them from two translation units fails to link (multiple definition), so a lesson cannot share them with a unit or a second file. None has a test or Tracer calls; only `main.cpp` uses them, with every sample commented out except `iteratorSample()`. On 2026-10-29 the five samples built on `linux-x64-debug` (`-Wall -Wextra -Werror`) and ran to exit 0 (090-05 testrecord R1). `main.cpp` also keeps commented calls `astate::stateChangeSample()` and `observer::observerSample()` that no longer exist: 020-01 moved State and Observer to `atugcc::pattern::state` / `::observer`.
**Next**: each pattern task (021-01, 022-01, 023-03, 023-05, 024-01) fixes its own header; 070-04 removes the dead calls when it moves the `main.cpp` samples. Closed with the last of them.
**Includes KI-031 (2026-11-06)**: when `terminal_formatter.hpp` moves, restore the console code pages that `detail::enableWindowsAnsi()` changes (as `lessons/support/console_utf8.cpp` does), or move the console setup out of the library header.

## KI-024 — No CI: every check runs on one machine
The repository has no `.github/` workflow. Builds, tests and the docs gate run only locally (`build.py`, `lint_docs.py`), and at the 090-05 check the local `main` was 7 commits ahead of `origin/main`. A regression on another compiler or OS, or a skipped gate, shows only when someone runs it by hand.
**Next**: user decision: push, and add a CI workflow (Linux Clang 20 presets and the docs gate first; Windows MSVC needs a runner with Visual Studio). It publishes to an outside service, so it is not done without that decision.
