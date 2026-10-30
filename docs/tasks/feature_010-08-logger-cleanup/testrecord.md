# Test Record: 010-08 Logger 정비

- Spec: [/docs/specs/010_08_logger_cleanup.md](/docs/specs/010_08_logger_cleanup.md)
- Plan: [plan.md](/docs/tasks/feature_010-08-logger-cleanup/plan.md)
- Date: 2026-10-30; host Windows 11 (MSVC 19.51, VS 2026), WSL Ubuntu 24.04 (GCC 13), 12 hardware threads

## Runs
| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | U1 only: `build.py --preset linux-x64-debug --target atugcc_tests --gtest-filter "RingBufferTest.*:LoggerTest.*:PosixDumpTest.*"` | pass | 16 tests pass | Pass |
| R2 | first full runs after U2, U3: `build.py --preset windows-x64-debug --test` | pass | build failed in the new test: MSVC C4996 on `sscanf` (`/WX`) → replaced by `std::from_chars` | Fail → fixed |
| R3 | rerun R2 | pass | 12/13; `AllTests` failed: `RingBufferTest.NoAutoFlushByDefault` expected `dropCount() == 0`, got 45. The test was wrong: `dropCount()` also counts evicted blocks (300 written, 255 kept) → expectation 45 | Fail → test fixed |
| R4 | `build.py --preset linux-x64-debug --test` (binary built before the R3 fix) | — | same single failure as R3, 110 other gtests pass on GCC | Info |
| R5 | after the U2 fix round: `windows-x64-debug --test` | pass | build failed: `logger_contention_probe.cpp(135)` C2589 on `std::min`: `<Windows.h>` macros reach `logger.hpp` users once U2 no longer defines `NOMINMAX` (KI-027) → probe uses `(std::min)` | Fail → fixed |
| R6 | `build.py --preset windows-x64-debug --test` | pass | 13/13 (gtest 110 pass, 1 POSIX skip) | Pass |
| R7 | `build.py --preset linux-x64-debug --test` | pass | 14/14 (includes `PlaygroundServer`) | Pass |
| R8 | after the doc and probe review fixes: `windows-x64-debug --test` | pass | gtest 110 pass, 1 skip; `logger_contention_probe 2000 1` exit 0 | Pass |
| R9 | `build.py --preset linux-x64-asan --test` | pass | 14/14 | Pass |
| R10 | `build.py --preset linux-x64-tsan --test` | pass | 14/14 | Pass |
| R11 | mutant M1: live output without `osyncstream` (`<< line << '\n'; flush()`), TSan, `--gtest_filter=LoggerTest.LiveOutputLinesDoNotInterleave` (run with `setarch -R`, KI-012) | killed | `WARNING: ThreadSanitizer: data race`, exit 66; header restored (`cmp` identical) | Pass |
| R12 | mutant M2: history write without `mutex_`, TSan, `--gtest_filter=LoggerTest.SharedAcrossThreads` | killed | ThreadSanitizer data race, exit 134; header restored | Pass |
| R13 | AC-2: temporary `l.log(Level::Info, "two {} {}", 1)` appended to `test_logger.cpp`, build `atugcc_tests` on `windows-x64-debug` and `linux-x64-debug` | compile error | MSVC C7595 (`_You_see_this_error_because_arg_id_is_out_of_range`), GCC `__invalid_arg_id_in_format_string`; file restored | Pass |
| R14 | AC-7: `lesson_device_state_machine.exe`, `lesson_thread_and_log.exe` (Windows Debug) run in an empty scratch directory | no `log/` | exit 0, no `log/` created; lines show the caller (`main.cpp:60 int __cdecl main(void)`) | Pass |
| R15 | AC-10 Linux: `build.py --preset linux-x64-release --target logger_contention_probe`, run with defaults (100000 lines × 3 runs), nothing else running | table, exit 0 | below | Pass |
| R16 | AC-10 Windows: same on `windows-x64-release` | table, exit 0 | below | Pass |
| R17 | `lint_docs.py`, `naming_check.py` | exit 0 | 0 errors, 0 warnings; 0 | Pass |

## AC-10 measurement (Release, live output off)
Latency in ns per call, best of 3 runs; "wall" is wall time / total lines.

| Host | Mode | Threads | wall ns/line | p50 | p99 | lines/s |
|---|---|---|---|---|---|---|
| Linux GCC 13 | A shared | 4 | 321.7 | 571 | 17,051 | 3.11 M |
| | B per-thread | 4 | 121.8 | 381 | 707 | 8.21 M |
| | C DbgBuf only | 4 | 123.3 | 313 | 679 | 8.11 M |
| | A shared | 8 | 391.5 | 1,132 | 35,129 | 2.55 M |
| | B per-thread | 8 | 102.5 | 720 | 946 | 9.76 M |
| | C DbgBuf only | 8 | 78.5 | 552 | 710 | 12.73 M |
| Windows MSVC | A shared | 4 | 367.6 | 900 | 7,600 | 2.72 M |
| | B per-thread | 4 | 275.4 | 700 | 1,400 | 3.63 M |
| | C DbgBuf only | 4 | 170.8 | 600 | 700 | 5.85 M |
| | A shared | 8 | 358.5 | 1,400 | 19,100 | 2.79 M |
| | B per-thread | 8 | 168.7 | 1,300 | 1,500 | 5.93 M |
| | C DbgBuf only | 8 | 130.1 | 1,000 | 1,100 | 7.68 M |

- One thread: A, B and C are within 15% of each other on both hosts (Linux 378 / 431 / 375 ns, Windows 765 / 730 / 605 ns): the lock costs nothing without contention.
- **Live output on**: A and B are the same on both hosts (Linux about 5 µs per line from 2 threads up, p99 76–230 µs; Windows 4.5–9 µs, p99 up to 445 µs). The shared stream itself is the bottleneck, whichever Logger writes to it.
- Windows `steady_clock` steps by 100 ns, so its p50 values are coarse.

### Assumption 9 (proposed threshold: p99 A/B ≥ 3× or throughput A/B ≤ 50%, at 4 and 8 threads, live off)
| Host | 4 threads p99 A/B | 4 threads throughput A/B | 8 threads p99 A/B | 8 threads throughput A/B |
|---|---|---|---|---|
| Linux | 24.1× | 38% | 37.1× | 26% |
| Windows | 5.4× | 75% | 12.7× | 47% |

**Proposal for 010-09** (AC-11; the decision is the user's): the threshold is met on both hosts, so 010-09 changes the shared `Logger` to per-thread buffers drained by one consumer thread. The consumer also owns live output, which takes the 5–9 µs stream write (and its p99 of hundreds of µs) off the logging threads; that is the larger cost whenever live output is on. Together with the crash dump of every thread's buffer (spec §6), KI-026 and KI-027.

## Acceptance Criteria
| AC | Evidence | Status |
|---|---|---|
| AC-1 | `LoggerTest.RecordsCallerLocation` passes on MSVC (R6, R8) and GCC (R7, R9, R10); R14 shows the caller in a real lesson | Pass |
| AC-2 | R13 (both compilers); every existing caller (tests, the two lessons, unit `jthread_worker`) builds unchanged in R6–R10 | Pass |
| AC-3 | `LoggerTest.SharedAcrossThreads` on `linux-x64-tsan` (R10); mutant M2 killed (R12) | Pass |
| AC-4 | `LoggerTest.LiveOutputLinesDoNotInterleave` (R6–R10); mutant M1 killed under TSan (R11) | Pass |
| AC-5 | CTest `DumpPrepare_off`: no `log/`, no `dumpDir`, empty `preparedPath()`, crash handler unchanged from startup (R6–R10) | Pass |
| AC-6 | CTest `DumpPrepare_once`: one file in the first `dumpDir`, none elsewhere, one new descriptor for three Loggers and a `MemoryDump` (Linux `/proc/self/fd`); `DumpPrepare_replace`: an explicit prepare closes the auto-prepared descriptor and removes the empty file (R6–R10) | Pass |
| AC-7 | normal exit: CTest fixture `DumpPrepare_cleanup` → `DumpPrepare_check-removed` (R6–R10) and R14; crash path: existing `PosixDumpTest.*`, `DumpHandleTest.*` (crash handler writes to the prepared target) pass on both compilers | Pass |
| AC-8 | `RingBufferTest.NoAutoFlushByDefault`; existing `RingBufferTest.*` with explicit thresholds unchanged (R6–R10) | Pass |
| AC-9 | code review: `logger.hpp` has no `m_buffer` / `m_dump` (`grep -c` = 0, codex review U3: none); `LoggerTest.OneDbgBufCopyPerLine` checks one `DbgBuf` copy (it would also pass on the old code, so the removal itself rests on review) | Pass |
| AC-10 | CTest `LoggerContention` (Debug smoke, R6–R10); R15, R16 tables; live-on runs check that every line arrived whole | Pass |
| AC-11 | proposal above; `agent_todo.md` 010-09 note | Pass |
| AC-12 | R6–R10: `windows-x64-debug` (`/W4 /WX`), `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan` all pass | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U2 | codex luna (high), round 1 | matches spec / D2, list defects | (1) descriptor leak if the once-block throws after opening; (2) `preparedPath()` races the first prepare; (3) `NOMINMAX` in a public header; (4) `std::call_once` may throw out of `noexcept`; (5) `signalHandler` not async-signal-safe (unchanged code) | 1–4 sent back to agy flash (`--resume`), fixed; 5 → KI-026 |
| U2 | codex luna (high), round 2 | are 1–4 fixed, any new defect | all fixed, new defects: none (mutex not on the crash path; guard destroyed before the mutex) | — |
| U1, U3 | codex luna (high) | matches spec / D1, D3, D4, list defects | `log_queue.hpp` brief still named a consumer; "one thread at a time" weaker than SPSC needs; caller location on both compilers not provable from the diff | comments fixed by lead; location proven by AC-1 on both compilers |
| U4–U7 | `cpp-reviewer` | does each test check its AC, can it pass trivially; docs vs code | `OneDbgBufCopyPerLine` cannot fail on the old code; probe counted lines only for live-on runs and did not detect merged lines; docs claimed a per-Logger level setting and per-Logger crash dump choice, and implied other threads' buffers reach the dump; evolution page imprecise on `consteval` | test comment states AC-9 rests on review; probe checks every line is whole; README, `main.cpp`, `logger.hpp` comment and spec Assumption 1 wording fixed; evolution page fixed; AC-3/AC-4 strength proven by mutants M1, M2 |
