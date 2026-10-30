# Plan: 010-08 Logger 정비

- Spec: [/docs/specs/010_08_logger_cleanup.md](/docs/specs/010_08_logger_cleanup.md) (approved 2026-10-30)
- Branch: `feature/010-08-logger-cleanup` (from `main` at `3a860c2`)

## Files
- [MODIFY] `include/atugcc/core/ring_buffer.hpp`, `include/atugcc/core/log_queue.hpp` (comments)
- [MODIFY] `include/atugcc/core/memory_dump.hpp`
- [MODIFY] `include/atugcc/core/logger.hpp`, `src/core/logger.cpp`
- [MODIFY] `tests/core/test_logger.cpp`, `tests/core/test_ring_buffer.cpp`, `tests/CMakeLists.txt`
- [NEW] `tests/core/dump_prepare_probe.cpp` (AC-5, AC-6, AC-7: a fresh process per check, because the dump target is process-wide and `atugcc_tests` already prepares one)
- [NEW] `tests/core/logger_contention_probe.cpp` (AC-10)
- [NEW] `docs/cpp_evolution/source_location.md`
- [MODIFY] lesson `02_thread_and_log` README and comments, unit `jthread_worker` README and comment, `docs/known_issues.md`, `docs/tasks/lesson_candidates.md`, `docs/tasks/agent_todo.md`

## C++20/23 features
`std::source_location` as a default argument of a `consteval` constructor, `std::type_identity_t` to keep the wrapper out of deduction, `std::osyncstream`, `std::call_once`. Evolution page: `docs/cpp_evolution/source_location.md`.

## Design decisions (fixed here, not left to the units)
- D1 `kNoAutoFlush = 2.0f`; `kDefaultFlushThreshold = kNoAutoFlush`.
- D2 `MemoryDump` keeps its header-only form. Process-wide prepare state lives in one inline function's static local (ODR-safe: one instance per program). `ensurePrepared(dir)`: `std::call_once`; registers the handler, creates `dir`, opens `dir/crash_dump_<time>.log`, stores fd/HANDLE in the existing statics and the path for `preparedPath()`. A function-local static guard object's destructor (normal exit) closes the auto-prepared fd/HANDLE and removes the file when its size is 0. `prepareDumpFile`/`prepareDumpFileWin` close the previous fd/HANDLE before storing the new one; when the previous one was the auto-prepared file, the guard forgets it and removes it if empty. The constructor `MemoryDump()` calls `ensurePrepared("log")` and keeps the Linux exe-path / module-base recording (done once, inside the once-block).
- D3 `Logger` history: `std::vector<std::string>` of size `bufferCapacity` plus `head_` and `count_`; `snapshot()` copies oldest first. Live output: build `line + '\n'` once, write it through `std::osyncstream`, then flush the underlying stream.
- D4 `Logger` constructor calls `ensurePrepared(cfg_.dumpDir)` only when `enableCrashDump`; the result is ignored at construction (spec §2.2) and is visible through `preparedPath()`.

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `ring_buffer.hpp`, `log_queue.hpp` | D1 + header comments (AC-8) | `grep -c kNoAutoFlush` = 4; R1; R6–R10 | yes (public header) | lead (spec-fixed constant) | codex luna (high, with U3): comments → fixed | 131k / 4k (review) | done |
| U2 | `memory_dump.hpp` | D2 (AC-5, AC-6, AC-7) | R6–R10, `DumpPrepare_*`, `PosixDumpTest.*`, `DumpHandleTest.*` | yes (platform branches, static state, crash handler) | agy flash (+ 1 fix round, `--resume`) | codex luna (high): 4 findings → fixed, round 2: none; 1 pre-existing → KI-026 | 451k / 157k (author), 266k / 11k (review) | done |
| U3 | `logger.hpp`, `logger.cpp` | `FormatWithLocation`, `log` overloads, D3, D4, remove `m_buffer` (AC-1, AC-2, AC-3, AC-4, AC-9) | R6–R13 | yes (public API, templates, locks) | agy flash | codex luna (high, with U1): none for U3 | 115k / 37k (author) | done |
| U4 | `test_logger.cpp`, `test_ring_buffer.cpp` | tests for AC-1, AC-3, AC-4, AC-8, AC-9 | R6–R12 | no (test) | lead | `cpp-reviewer`: AC-9 test cannot fail on old code → documented; mutants M1, M2 run | 85k (reviewer, U4–U7) | done |
| U5 | `dump_prepare_probe.cpp`, `tests/CMakeLists.txt` | modes `off`, `once`, `replace`, `cleanup` + `check-removed` (CTest fixture) (AC-5, AC-6, AC-7) | `DumpPrepare_*` in R6–R10 | no (test) | lead | `cpp-reviewer`: none | (see U4) | done |
| U6 | `logger_contention_probe.cpp`, `tests/CMakeLists.txt` | (A)(B)(C) × 1/2/4/8 threads × live off/on (AC-10) | `LoggerContention`; R15, R16 | no (test) | lead | `cpp-reviewer`: completeness only on live-on runs, merged lines not detected → whole-line check | (see U4) | done |
| U7 | §8 documents | contract, comments, evolution page, lessons, KIs (AC-11) | R17 | no (doc) | lead | `cpp-reviewer`: level setting claimed, crash-dump wording, `consteval` wording → fixed | (see U4) | done |
