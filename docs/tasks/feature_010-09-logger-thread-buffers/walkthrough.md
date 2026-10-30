# Walkthrough: 010-09 Logger 스레드별 버퍼와 소비자 스레드

- Spec: [/docs/specs/010_09_logger_thread_buffers.md](/docs/specs/010_09_logger_thread_buffers.md) (approved 2026-10-30)
- Evidence: [testrecord.md](/docs/tasks/feature_010-09-logger-thread-buffers/testrecord.md) (AC-1 … AC-13 Pass; AC-1 with a note)
- Branch: `feature/010-09-logger-thread-buffers`, merged into `main` by fast-forward

## Result
- **No lock on the hot path**: each thread writes into its own pointer-free buffer (`detail::ThreadLogBuffer`, SPSC); one log thread delivers to the history, the live output and the new file sink (`Config::filePath`). `Delivery::Sync`, `flush()`, `OverflowPolicy::BlockThenDrop` (default, 100 ms) / `Block`, `Durability::Process` / `System`, `configureLogBuffers()` / `ATUGCC_LOG_SLOTS`.
- **Logs survive the ways a process can end inside itself**: normal exit, `std::exit`, `std::quick_exit`, thread exit, `std::terminate`, `abort`, SIGSEGV/SIGBUS/SIGFPE/SIGILL, Windows exceptions and stack overflow all leave every thread's newest records in a DUMP-V2 crash dump (`tools/read_dump.py` reads it), and the file has what was delivered. What can still be lost (SIGKILL, power loss, a full buffer with BlockThenDrop, file errors) is in the README table and, at run time, reported.
- **Measured**: the shared Logger's p99 at 4–8 threads is now 1.1–1.5 µs on Linux and 3.3–3.9 µs on Windows (010-08: 17–35 µs and 7.6–19 µs), equal to one Logger per thread. Sustained throughput is bounded by the one log thread at about 0.8 M lines/s (Linux) and 0.5–0.7 M (Windows): KI-028.
- KI-026 and KI-027 closed; the logging code no longer uses Boost (the dependency stays for other features).

## Lead (fallback) units
- U6 review fixes (Logger without an id, guarantee list, `peekThreadBuffer` in `dumpToFd`), the alternate-stack and fence fixes found by the sanitizers, the per-thread terminate handler for MSVC, and the log thread's own-buffer drop: small changes, each reviewed by codex (testrecord Reviews).

## Follow-ups
- KI-028: one log consumer caps sustained throughput.
- 010-10 (next, user decision 2026-10-30): memory-mapped buffers and recovery into a separate file for SIGKILL / forced termination.
