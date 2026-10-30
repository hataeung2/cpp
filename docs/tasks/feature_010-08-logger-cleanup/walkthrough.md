# Walkthrough: 010-08 Logger 정비

- Spec: [/docs/specs/010_08_logger_cleanup.md](/docs/specs/010_08_logger_cleanup.md) (approved 2026-10-30)
- Evidence: [testrecord.md](/docs/tasks/feature_010-08-logger-cleanup/testrecord.md) (AC-1 … AC-12 Pass)
- Branch: `feature/010-08-logger-cleanup`, merged into `main` by fast-forward

## Result
- **Caller location**: `logger.log(Level::Info, "x {}", v)` records the caller's file and line (`FormatWithLocation`, a `consteval` wrapper around the format string). Call sites are unchanged; a wrong argument count is still a compile error.
- **One Logger may be shared**: every public member of `Logger` is safe from several threads. The history is a fixed ring under the mutex, crash-dump lines go to the calling thread's `DbgBuf`, live output goes through `std::osyncstream` so Loggers sharing a stream never mix lines. The Logger's own duplicate ring buffer is gone.
- **Crash dump follows the config**: `MemoryDump::ensurePrepared(dir)` prepares the handler and file once per process; `enableCrashDump = false` touches nothing; an empty dump file is removed at normal exit; explicit prepares close the previous descriptor.
- **No implicit pushes into the single-producer queue**: `RingBuffer` auto-flush is off by default, so the crash buffer always holds the newest blocks.
- **Measurement**: `logger_contention_probe` compares a shared Logger, a Logger per thread and `DbgBuf` alone. Release, live output off, 8 threads: shared p99 is 37× (Linux) and 12.7× (Windows) the per-thread p99, throughput 26% and 47%. With live output on, the shared stream dominates and sharing makes no difference. Both hosts pass the Assumption 9 threshold, so 010-09 is proposed as per-thread buffers plus a consumer thread that also owns output.
- Docs: lesson `02_thread_and_log` and unit `jthread_worker` explain the shared-safe contract and why per-feature Loggers are still useful; new [source_location.md](/docs/cpp_evolution/source_location.md).
- `.agent/scripts/naming_check.py`: twelve standard-library names used by the new tests added to the allowed list.

## Follow-ups
- KI-013, KI-014, KI-021, KI-025: closed.
- KI-026 (signal handler not async-signal-safe, pre-existing) and KI-027 (`<Windows.h>` reaches `logger.hpp` users, pre-existing): new, owned by 010-09.
- 010-09 scope: the user's decision, with the numbers above.
