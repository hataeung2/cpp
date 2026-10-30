# Test Record: 010-09 Logger 스레드별 버퍼와 소비자 스레드

- Spec: [/docs/specs/010_09_logger_thread_buffers.md](/docs/specs/010_09_logger_thread_buffers.md)
- Plan: [plan.md](/docs/tasks/feature_010-09-logger-thread-buffers/plan.md)
- Date: 2026-10-30; host Windows 11 (MSVC 19.51, VS 2026), WSL Ubuntu 24.04 (GCC 13), 12 hardware threads

## Runs
| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | U1: `build.py --preset linux-x64-debug --gtest-filter "RingBufferTest.*"` | pass | 10 tests | Pass |
| R2 | `py -3 tools/test_read_dump.py` | pass | 8 tests (after fixing two of the test's own mistakes; again after the reservePos change) | Pass |
| R3 | first integration build, both presets | builds | include paths `"src/core/log_file.hpp"` (→ `"log_file.hpp"`), a private `lockService` used by the cpp's RAII helper (→ public internal section), `main.cpp` / `dump_prepare_probe.cpp` had reached `alog::MemoryDump` / Win32 through `logger.hpp` (KI-027 cut that: `adefine.hpp` includes `memory_dump.hpp`, the probe includes `<Windows.h>`), test compared `Level` with `uint8_t`, a probe line broken by a shell escape | Fail → fixed |
| R4 | first full suites | pass | Windows 3 and Linux 3 failures, all in the new tests: async output read without `flush()`; probe line check not aware of the `HH:MM:SS.uuuuuu ` prefix; the retired-buffer check was wrong (the crasher reused the ended thread's buffer) | Fail → tests fixed |
| R5 | `logger_contention_probe 2000 1` three times, Windows Debug | exit 0 | 1 of 3 runs missing lines: the probe used the default BlockThenDrop and the Debug sink is slow, so lines were dropped after 100 ms by design → probe uses `OverflowPolicy::Block` | Fail → probe fixed |
| R6 | crash checks, Linux Debug | pass | terminate: the named producer line was overwritten during the 200 ms emergency flush → check "a line ≥ the named one in the dump" (after the cpp-reviewer round: no file fallback) | Fail → check fixed |
| R7 | `linux-x64-asan --test` | pass | ASan could not unmap an alternate signal stack: `prepareThreadForCrash` had replaced ASan's own per-thread stack → keep an existing ≥ 32 KiB alternate stack; LeakSanitizer reported the four 64-slot buffers the unit tests create (never freed by design) → test keeps them reachable | Fail → fixed |
| R8 | `linux-x64-tsan` build | builds | GCC `-Wtsan`: `atomic_thread_fence` not modelled → pragma around that one fence (plan D1; producer/consumer sync is release/acquire on `writePos`) | Fail → fixed |
| R9 | `linux-x64-tsan --test` | pass | race between the crash-dump writers (`writeAll`, `DbgBuf::dumpToFd`, called directly by tests) and the consumer's `readPos` store: the deliberate racy snapshot of plan D1/D5 → `tests/tsan.supp` names those two functions only; then counting tests lost lines under TSan's slowness (default BlockThenDrop) → those tests use `Block` | Fail → fixed |
| R10 | crash checks, Windows Debug | pass | terminate dumped as `signal`: MSVC keeps the terminate handler per thread → `installTerminateHandlerForThisThread()` on every buffer acquisition, previous handler remembered per thread | Fail → fixed |
| R11 | `linux-x64-release` probe, first measurement | AC-1 | ratios met, but 85,000 lines/s for one thread (010-08: 2.6 M): a burst filled the buffer inside the 1 ms holdback and the consumer then waited the whole 5 ms interval → plan D3 "Sustained load" | Fail → fixed (agy) |
| R12 | `windows-x64-release` probe | AC-1 | 26,000 lines/s, 22 ms stalls: `sleep_for(50us)` rounds up to the ~15.6 ms Windows tick → producers wait on a "space" condition variable (plan D3 "Waiting for space") | Fail → fixed (agy) |
| R13 | codex review of the performance fixes | — | the log thread logging into its own full buffer would wait forever → it drops and counts (documented) | Fixed (lead) |
| R14 | final suites at `3b45b68`: `build.py --test` on `windows-x64-debug`, `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan` | pass, zero warnings | 15/15, 16/16, 16/16, 16/16 | Pass |
| R15 | Release measurement (below), nothing else running | AC-1 | see table | Pass (note) |
| R16 | mutant M1: `writePos.store(..., relaxed)` in `tryWrite`; TSan, `--gtest_filter="LoggerTest.SharedAcrossThreads:LoggerDeliveryTest.*"` | killed | 18 `ThreadSanitizer: data race` reports; file restored (`git checkout`, clean) | Pass |
| R17 | mutant M2: `writeDump` skips retired buffers; `check_crash_dump.py --modes segv,abort,terminate,stackoverflow` | killed | all four: "the ended thread's last line P9 L9 is not in the dump"; file restored | Pass |
| R18 | `symbolize_dump.py` on a DUMP-V2 segv dump (Linux Debug) | crash line | `tests/core/crash_probe.cpp:113` = `*p = 1;` | Pass |
| R19 | `lint_docs.py`, `naming_check.py`, `test_agent_scripts.py` | exit 0 | 0 errors, 0 warnings; 0; OK | Pass |

## AC-1 measurement (Release, best of 3 runs, 100,000 lines per thread)
| Host | Mode | Threads | live | p50 ns | p99 ns | lines/s |
|---|---|---|---|---|---|---|
| Linux GCC 13 | A shared | 4 | off | 380 | 1,484 | 857 k |
| | B per-thread | 4 | off | 377 | 1,098 | 868 k |
| | A shared | 8 | off | 761 | 1,146 | 801 k |
| | B per-thread | 8 | off | 747 | 1,253 | 867 k |
| | A shared | 4 / 8 | on | 385 / 748 | 1,079 / 1,257 | 799 k / 808 k |
| Windows MSVC | A shared | 4 | off | 800 | 3,300 | 643 k |
| | B per-thread | 4 | off | 800 | 3,300 | 705 k |
| | A shared | 8 | off | 1,300 | 3,900 | 489 k |
| | B per-thread | 8 | off | 1,200 | 6,900 | 657 k |
| | A shared | 4 / 8 | on | 800 / 1,200 | 4,200 / 4,200 | 521 k / 503 k |

| Criterion (AC-1) | Linux (2 runs) | Windows (3 runs) |
|---|---|---|
| 4 threads: p99 A/B ≤ 2×, throughput A/B ≥ 80 % | 1.35× · 99 %; 0.86× · 102 % | 1.00× · 91 %; 1.00× · 96 %; 1.00× · 96 % |
| 8 threads: same | 0.91× · 92 %; 0.97× · 103 % | 0.57× · **74 %**; 0.91× · 97 %; 0.59× · 87 % |
| live on: A's p99 ≤ 3× live off (4 and 8 threads) | 0.73×, 1.10× | 1.27×, 1.08× |

- **Note on AC-1**: one of three Windows runs had 74 % throughput at 8 threads. A and B are both bounded by the same single consumer thread (KI-028), so the throughput ratio measures run-to-run noise there; p99 never exceeded B's. Every other criterion passed in every run.
- Compared with 010-08: the shared Logger's p99 at 4 / 8 threads fell from 17,051 / 35,129 ns to 1,484 / 1,146 ns (Linux) and from 7,600 / 19,100 ns to 3,300 / 3,900 ns (Windows); with live output on, the caller no longer pays the stream write (010-08: p99 76–445 µs).
- **Limit (KI-028)**: sustained throughput is now the consumer's, about 0.8–0.87 M lines/s (Linux) and 0.5–0.7 M (Windows), lower than 010-08's per-thread Loggers (up to 9.8 M lines/s at 8 threads, each writing its own history on the calling thread). The `DbgBuf` path, which the consumer only consumes, reaches 4–8 M lines/s, so the cost is the consumer's per-record work.

## Crash checks (`check_crash_dump.py`, final code)
| Mode | Linux Debug | Windows Debug |
|---|---|---|
| normal / exit / quickexit, 8 × 100,000 lines | every line once, per-producer order; cross-thread time inversions 6–19 of 800,000 | same; 1,929–2,114 inversions (Block policy: a producer waiting for space publishes an older timestamp) |
| segv / abort / terminate / stackoverflow | dump: CRASH-MARKER, every producer at or after its named line, P9 L9 from a retired buffer; Event-Type `signal` / `terminate`; `sync.log` has the Sync line logged right before the crash; terminate: CRASH-MARKER in `app.log` | same; Event-Type `exception` for segv and stackoverflow |
| killme (SIGKILL / TerminateProcess 50 ms after the line) | line in `app.log` | line in `app.log` |

Sanitizer presets run normal, exit, quickexit and killme only (sanitizer runtimes own the crash signals; spec §12).

## Acceptance Criteria
| AC | Evidence | Status |
|---|---|---|
| AC-1 | R15 table | Pass (note: one Windows run 74 % at 8 threads, consumer-bound; KI-028). Accepted as Pass by the user 2026-10-30 |
| AC-2 | crash checks normal / exit / quickexit, 8 × 100,000 (CTest `CrashDump`); exit / quickexit cover the atexit / at_quick_exit drain | Pass |
| AC-3 | crash checks segv / abort / terminate / stackoverflow, both hosts; mutant M2 killed (R17) | Pass |
| AC-4 | same runs: `sync.log` line logged right before the crash; terminate delivers CRASH-MARKER to `app.log` | Pass |
| AC-5 | killme, both hosts | Pass |
| AC-6 | `LoggerOverflowTest.BlockThenDropReturnsAndReportsDrops`, `LoggerOverflowTest.BlockLosesNothing` | Pass |
| AC-6b | `LogBufferConfigTest.NewThreadsGetTheConfiguredSize` (error code `InvalidArgument`), CTest `LogSlotsFromEnvironment` (`ATUGCC_LOG_SLOTS=128`) | Pass |
| AC-7 | `LoggerDeliveryTest.SyncLineIsDeliveredWhenLogReturns`, `FlushDeliversEveryEarlierLine`; `snapshot()` right after `log()` in `LoggerTest.*` | Pass |
| AC-8 | `LoggerDeliveryTest.DestructorDeliversItsLines` (the stream is deleted right after the Logger; ASan clean, R14) | Pass |
| AC-9 | codex reviews of U5a, U5b (crash path: `write`, `sigaction`, `raise`, atomics, own decimal formatter; restore actions built at install); no `snprintf` / `std::string` on the handler path | Pass |
| AC-10 | `tests/core/crash_probe.cpp` includes only `logger.hpp` and calls `std::min` unparenthesised; builds on `windows-x64-debug` (R14) | Pass |
| AC-11 | `grep -rn "boost" include/atugcc/core src/core` = 0; `log_queue.hpp`, `flushToQueue` gone; `vcpkg.json` and `find_package(Boost)` unchanged | Pass |
| AC-12 | `tools/test_read_dump.py` (R2); crash checks read every dump with `read_dump.py`; R18 | Pass |
| AC-12b | §2.4 table in `logger.hpp` (class comment) and the root README (Features) | Pass |
| AC-13 | R14 | Pass |

## Reviews
| Unit | Reviewer | Findings | Resolution |
|---|---|---|---|
| U1 | lead (deletion fixed by the spec) | — | covered by later reviews of the files it touches |
| U2 | codex luna (high), 2 rounds | crash range could include slots being overwritten by a multi-slot write; little-endian not asserted; `retainedText` not documented as non-signal-safe; slot count narrowed before the truncation check | `reservePos` + fence (plan D1 amended), `static_assert`, doc, size_t; round 2: none |
| U3 | codex luna (high) | null dereference if the emergency buffer cannot be created; member naming; macros in the Windows include | emergency buffer in static storage (`createIn`); naming kept (public-field struct like `Config`, plan D2); macros stay in the `.cpp` |
| U4 | codex luna (high), plus two measured defects and a performance review | emergency buffer written without its try-lock; blocking lock after shutdown; blocking lock in `emergencyFlush`; exit callbacks could use a destroyed service; file errors discarded; (measured) holdback starved bursts; (measured) Windows sleep granularity; (review) log thread waiting on its own buffer | all fixed: try-lock, `try_lock`/`try_lock_until`, immortal service, `fileErrors` + stderr notice, plan D3 "Sustained load" and "Waiting for space", drop-and-count on the log thread |
| U5a | codex luna (high), 2 rounds | manual dump used up the one-time claim; handlers installed before the target opened; (round 2) a manual dump concurrent with a crash could interleave | fixed; the last documented as a limit of the diagnostic call |
| U5b | codex luna (high) | `sigemptyset` on the handler path; Windows IP not where `symbolize_dump.py` reads it | restore actions built at install; 8-byte IP before the `CONTEXT` |
| U6 | codex luna (high) | Logger with no id lost lines silently; guarantee list missing SIGBUS/SIGFPE/SIGILL; `dumpToFd` could allocate | lead (fallback): stderr notice + `droppedCount`, doc, `peekThreadBuffer()` |
| lead fixes | codex luna (high) | foreign alternate stack accepted at 16 KiB; one process-wide previous terminate handler on MSVC | 32 KiB threshold; per-thread previous handler |
| U7–U10 | `cpp-reviewer` | terminate check passable with a crash-thread-only dump; ended-thread buffer reused by the crasher; Sync line too early to prove Sync; atexit path untested; AC-2 line count; AC-8 stream outlived the Logger; error code unchecked; README / lesson / evolution page wording (missing rows, osyncstream, flush scope, Sync and disk, `atomic::wait`) | all fixed (crash probe reorganised, exit / quickexit modes, 100,000 lines, heap stream, docs) |
