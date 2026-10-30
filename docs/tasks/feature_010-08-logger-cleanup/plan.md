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
| U1 | `ring_buffer.hpp`, `log_queue.hpp` | D1 + header comments (AC-8) | `grep -c kNoAutoFlush` ≥ 2; build `atugcc_tests` both presets; `RingBufferTest.*` | yes (public header) | lead (spec-fixed constant) | codex luna (medium) | | |
| U2 | `memory_dump.hpp` | D2 (AC-5, AC-6, AC-7) | build both presets; `PosixDumpTest.*`, `DumpHandleTest.*` | yes (platform branches, static state, crash handler) | agy flash | codex luna (high) | | |
| U3 | `logger.hpp`, `logger.cpp` | `FormatWithLocation`, `log` overloads, D3, D4, remove `m_buffer` (AC-1, AC-2, AC-3, AC-4, AC-9) | build both presets; `LoggerTest.*`; lessons build | yes (public API, templates, locks) | agy flash | codex luna (high) | | |
| U4 | `test_logger.cpp`, `test_ring_buffer.cpp` | tests for AC-1, AC-3, AC-4, AC-8, AC-9 | both presets; TSan for AC-3, AC-4 | no (test) | lead | `cpp-reviewer` | | |
| U5 | `dump_prepare_probe.cpp`, `tests/CMakeLists.txt` | modes `off`, `once`, `cleanup` + `check-removed` (CTest fixture) (AC-5, AC-6, AC-7) | `ctest -R DumpPrepare` both presets | no (test) | lead | `cpp-reviewer` | | |
| U6 | `logger_contention_probe.cpp`, `tests/CMakeLists.txt` | (A)(B)(C) × 1/2/4/8 threads × live off/on (AC-10) | `ctest -R LoggerContention`; Release runs | no (test) | lead | `cpp-reviewer` | | |
| U7 | §8 documents | contract, comments, evolution page, lessons, KIs (AC-11) | `lint_docs.py` | no (doc) | lead | `cpp-reviewer` | | |
