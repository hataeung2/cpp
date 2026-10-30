# Plan: 010-09 Logger 스레드별 버퍼와 소비자 스레드

- Spec: [/docs/specs/010_09_logger_thread_buffers.md](/docs/specs/010_09_logger_thread_buffers.md) (approved 2026-10-30)
- Branch: `feature/010-09-logger-thread-buffers` (from `main` at `0ab027b`)

## Design decisions (fixed here; units implement them, they do not decide them)

### D1 Thread log buffer (`include/atugcc/core/detail/thread_log_buffer.hpp`, `src/core/thread_log_buffer.cpp`)
One contiguous, pointer-free, little-endian block per buffer, so 010-10 can place the same block in a mapped file:
```text
BufferHeader (64 bytes, alignas(64))
  char     magic[8]      "ATGLBUF1"
  uint32   slotCount     power of two
  uint32   slotBytes     256
  uint32   threadNo      process-unique number of the thread that owns it now (1, 2, ...)
  uint32   flags         bit0 = retired (owning thread ended)
  atomic<uint64> writePos  producer only; monotonic (never reset, also not on reuse)
  atomic<uint64> readPos   consumer only; monotonic
  uint64   reserved[3]
Slot[slotCount] (256 bytes each)
  SlotHeader (24 bytes)
    uint64 timeNs      steady_clock nanoseconds since its epoch, same for every slot of a record
    uint32 threadSeq   record number within the owning thread (0, 1, ...)
    uint16 loggerId    0 = DbgBuf (no sink), else a registered Logger
    uint8  level       atugcc::core::Level
    uint8  flags       bit0 = first slot of the record, bit1 = last slot
    uint16 len         payload bytes in this slot (0..232)
    uint16 reserved0
    uint32 reserved1
  uint8 payload[232]
```
- `static_assert(std::atomic<std::uint64_t>::is_always_lock_free && sizeof(std::atomic<std::uint64_t>) == 8)`.
- Producer `write(timeNs, threadSeq, loggerId, level, text)`: slots needed `n = max(1, ceil(len / 232))`; a record longer than `slotCount / 2` slots is cut to that many slots and its last slot ends with `…(truncated N bytes)`. Space exists while `writePos + n - readPos <= slotCount` (undelivered slots are never overwritten; delivered ones are). Fill the slots at `writePos .. writePos+n-1` (index `pos & (slotCount-1)`), then `writePos.store(writePos + n, release)`. Returns `false` when there is no space (no partial write).
- Consumer: `readPos` load (relaxed, own), `writePos` load (acquire); read slots; `readPos.store(new, release)`.
- Crash reader: valid positions are `[max(readPos_lower_bound, writePos - slotCount + 1), writePos)` where the lower bound is 0; it never trusts the slot at `writePos & mask` (may be mid-write). Slots `< readPos` are "delivered".
- `rawBytes()` / `rawSize()`: the whole block, for the crash dump (signal-safe: pointer + size, no allocation).
- Memory is allocated with `::operator new(size, std::align_val_t{64})` and never freed.

### D2 Registry (`detail/log_registry.hpp`, `src/core/log_registry.cpp`, `src/core/thread_crash_prep.cpp`)
- Lock-free singly linked list: `struct Node { ThreadLogBuffer* buffer; std::atomic<bool> inUse; Node* next; void* altStack; }`; `std::atomic<Node*> head`; push by CAS only; nodes and buffers are never freed.
- `ThreadLogBuffer& threadBuffer()`: a `thread_local` handle acquires on first use: reuse a node with `!inUse`, `buffer->readPos == buffer->writePos` and the currently configured `slotCount` (CAS `inUse` false → true), else create node + buffer and push. On acquire: new `threadNo` (global `std::atomic<uint32_t>` counter, only touched on acquire), clear the retired flag, `threadSeq` restarts at 0 (kept in the handle), call `prepareThreadForCrash(node.altStack)`.
- Handle destructor (thread exit): set the retired flag, then `inUse.store(false, release)`. A `log()` from a later-destroyed `thread_local` of the same thread after the handle died re-acquires (a thread-local "dead" flag makes `threadBuffer()` return a fresh node in that case) — no use of a dead handle.
- `template <class F> void forEachBuffer(F&& f)`: walks the list with acquire loads, no allocation; signal-safe when `f` is.
- `configureLogBuffers(LogBufferConfig)`: validates (power of two, 64..65536; `drainInterval` 1..1000 ms), stores in atomics; affects buffers created afterwards. First use reads `ATUGCC_LOG_SLOTS` once.
- `prepareThreadForCrash(void*& altStack)`: Linux: allocate once per node (`64 KiB`, kept in the node for reuse) and `sigaltstack` it for the calling thread; Windows: `SetThreadStackGuarantee` with 64 KiB. In `src/core/thread_crash_prep.cpp`, the only file of this unit with `#ifdef`.

### D3 Log service (`detail/log_service.hpp`, `src/core/log_service.cpp`)
- `LogService& LogService::instance()`: function-local static in the `.cpp`; starts the consumer `std::jthread` on construction; registers `std::atexit` and `std::at_quick_exit` handlers that call `shutdown()`; installs a `std::set_terminate` handler (chains the previous one): `emergencyFlush(200ms)`, then `alog::MemoryDump::writeDumpNow("terminate", 0)` when a dump target is prepared, then the previous handler or `std::abort()`.
- Loggers: `std::uint16_t registerLogger(LoggerSinks*)` / `unregisterLogger(id)` under the service mutex; ids 1..65535, reused. `LoggerSinks` holds the history ring (+ its mutex), `liveOutput`, the file (`LogFile`), durability, `std::atomic<uint64_t> dropped`, `uint64_t droppedReported`.
- `submit(loggerId, level, text, Delivery, OverflowPolicy, wait)` on the caller thread: `timeNs` = steady now; write into `threadBuffer()`; full → wake the consumer, then retry with backoff (`yield`, then `sleep_for(50us)`) until written or, for `BlockThenDrop`, until `wait` elapsed → `dropped.fetch_add(1)`, return. After writing: wake the consumer if `level >= Warn` or buffer more than half used. `Sync`: wait until this thread's buffer `readPos >= ` the end position of the record (cv wait with 1 ms timeout loop); from the consumer thread itself, never wait. When the service is stopped (after `shutdown()`): deliver inline (caller takes the service mutex and runs one drain itself).
- Consumer loop: `cv.wait_for(drainInterval)` or wake; drain: walk buffers, collect complete records (first..last slots) that are undelivered, keep only those with `timeNs <= now - 1 ms` (holdback) unless a flush or shutdown is pending; sort by `(timeNs, threadNo, threadSeq)`; under the service mutex dispatch each to its Logger's sinks (unknown id or 0 → none); before a Logger's first record of the batch, if `dropped > droppedReported`, emit `[atugcc] dropped N lines`; write file and live output once per batch per Logger; then advance each buffer's `readPos` past what was taken; notify waiters.
- Sink line formats: history = the line as today (`[LEVEL] [file:line func] payload`); live output = `HH:MM:SS.uuuuuu ` + line; file = `YYYY-MM-DDTHH:MM:SS.uuuuuuZ T<threadNo> ` + line. Wall time = `system_clock` base + (`timeNs` − steady base), bases taken once at service start.
- `flush()`: snapshot every buffer's `writePos`, mark flush pending, wake, wait until each `readPos` reaches its snapshot (returns at once on the consumer thread). `emergencyFlush(timeout)`: same with a deadline, never blocks longer.
- `shutdown()`: flush, stop and join the consumer, mark stopped. Idempotent.
- Time order across batches: a record whose producer stalled more than the 1 ms holdback between reading the clock and publishing can land after a later-timestamped one; per-thread order is always exact (`threadSeq`). The AC-2 check reports cross-thread inversions and requires 0 per-thread inversions (spec §4 clarification, History).

### D4 File sink (`src/core/log_file.hpp`, `src/core/log_file.cpp`)
`LogFile::open(path)` (creates parent directories, opens for append: POSIX `open(O_WRONLY|O_CREAT|O_APPEND|O_CLOEXEC, 0644)`, Windows `CreateFileW(FILE_APPEND_DATA, FILE_SHARE_READ|FILE_SHARE_WRITE, OPEN_ALWAYS)`), `write(std::string_view)` (loops until all written), `sync()` (`fsync` / `FlushFileBuffers`), closes in the destructor. Errors are returned as `Result` and counted; the service keeps running.

### D5 Crash dump (`include/atugcc/core/memory_dump.hpp`, `src/core/memory_dump.cpp`, `src/core/crash_handler_posix.cpp`, `src/core/crash_handler_win.cpp`)
- `memory_dump.hpp` keeps only declarations and includes neither `<Windows.h>` nor POSIX headers (KI-027). Public: `MemoryDump()` (calls `ensurePrepared("log")`), `ensurePrepared`, `preparedPath`, `getDumpFd`, `getDumpHandle`, `getModuleBase`, `getExePath` (now `const char*`), `prepareDumpFile`, `prepareDumpFileWin`, `dump(dir)`, new `static void writeDumpNow(const char* eventType, std::uint64_t eventCode) noexcept` (signal-safe; writes to the prepared target). `ignoreResult` stays. The 010-08 behaviour of `ensurePrepared` (once, first dir wins, empty file removed at exit, explicit prepare closes the previous) is kept, with its state moved into `memory_dump.cpp`.
- Dump format `DUMP-V2` (all text lines end with `\n`):
  ```text
  DUMP-V2
  PID: <n>
  Event-Type: <signal|exception|terminate|manual>
  Event-Code: <n>
  Crash-Thread: <threadNo or 0>
  Clock-Base: <system_clock ns> <steady_clock ns>
  --CONTEXT-BINARY--      (Linux: 8-byte IP; Windows: CONTEXT struct, as today)
  --MODULES--             (as today: 8-byte base, exe path, '\n')
  --THREADS--
  --THREAD--              then the raw buffer block (D1), once per registered buffer
  --END--
  ```
  Numbers are written with a signal-safe decimal formatter (no `snprintf`, KI-026). The exe path lives in a fixed `char[4096]` filled at preparation.
- Handlers, installed by `ensurePrepared` only (010-08 AC-5 stays true): Linux `SIGSEGV, SIGBUS, SIGFPE, SIGILL, SIGABRT` with `SA_SIGINFO | SA_ONSTACK`, previous actions saved; Windows `SetUnhandledExceptionFilter` (previous saved) and `signal(SIGABRT)`. An atomic flag makes the dump happen once; then the handler restores the previous action (or the default) and re-raises (Linux) / returns `EXCEPTION_CONTINUE_SEARCH` or calls the previous filter (Windows). Nothing on this path allocates, locks, or calls `snprintf`.

### D6 `RingBuffer`, `DbgBuf`, queue
Remove `log_queue.hpp`, `log_queue.cpp`, `RingBuffer::flushToQueue`, its specialization, `kNoAutoFlush` and the threshold constructor parameter; `RingBuffer` stays a plain container. `DbgBuf::log` writes a record with `loggerId 0` into `threadBuffer()`; `DbgBuf::instance()` returns `ThreadLogBuffer&`; `DbgBuf::dump()` returns the calling thread's retained records as text; `dumpToFd` / `dumpToHandle` write the calling thread's raw block. Boost stays a build dependency (user 2026-10-30) but no logging file includes it.

### D7 Logger (`logger.hpp`, `logger.cpp`)
`Logger` owns a `LoggerSinks` (D3), registers in the constructor, unregisters in the destructor after `flush()`. `log()` formats the line (as in 010-08, outside any lock) and calls `LogService::submit`. `snapshot()` = `flush()` + copy of the history. `dump()` as today. `droppedCount()` reads the sink counter. `logger.hpp` includes only `detail/log_service.hpp`-level declarations (no `memory_dump.hpp`).

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `ring_buffer.hpp`, `ring_buffer.cpp`, `log_queue.*`, `CMakeLists.txt`, `test_ring_buffer.cpp` | D6 queue removal (AC-11) | `grep -c "LogQueue\|flushToQueue"` = 0 in `include`, `src`; build | yes (public header) | lead (deletion fixed by the spec) | codex luna | | |
| U2 | `detail/thread_log_buffer.hpp`, `thread_log_buffer.cpp` | D1 | build; unit tests in U7 | yes (atomics, layout) | agy flash | codex luna (high) | | |
| U3 | `detail/log_registry.hpp`, `log_registry.cpp`, `thread_crash_prep.cpp` | D2, `configureLogBuffers` (AC-6b) | build; U7 tests; TSan | yes (lock-free list, thread_local lifetime, platform) | agy flash | codex luna (high) | | |
| U4 | `detail/log_service.hpp`, `log_service.cpp`, `log_file.hpp`/`.cpp` | D3, D4 | build; U7 tests; TSan | yes (threads, lifetime, platform I/O) | agy flash | codex luna (high) | | |
| U5a | `memory_dump.hpp`, `memory_dump.cpp` | D5 common part, `writeDumpNow`, DUMP-V2 writer (KI-026, KI-027) | build; `DumpPrepare_*`; dump tests | yes (signal-safety, static state) | agy flash | codex luna (high) | | |
| U5b | `crash_handler_posix.cpp`, `crash_handler_win.cpp` | D5 handlers | build both; U8 crash probes | yes (signal handlers, platform) | agy flash | codex luna (high) | | |
| U6 | `logger.hpp`, `logger.cpp`, `ring_buffer.cpp` (`DbgBuf`) | D7, D6 `DbgBuf` | build both; existing `LoggerTest.*` | yes (public API) | agy flash | codex luna (high) | | |
| U7 | `tests/core/test_log_buffers.cpp` (new), `test_logger.cpp`, `test_dump_handle.cpp`, `test_posix_dump.cpp`, `tests/CMakeLists.txt` | AC-6, AC-6b, AC-7, AC-8, buffer/registry tests | four presets | no (test) | lead | `cpp-reviewer` | | |
| U8 | `tests/core/crash_probe.cpp`, `tests/core/check_crash_dump.py`, `tests/CMakeLists.txt` | AC-2 … AC-5, AC-10 | `ctest -R Crash` debug presets | no (test) | lead | `cpp-reviewer` | | |
| U9 | `tools/read_dump.py`, `tools/test_read_dump.py` | AC-12 | unittest | no (tool) | lead | `cpp-reviewer` | | |
| U10 | §8 documents | AC-12b, lessons, evolution page, KIs | `lint_docs.py` | no (doc) | lead | `cpp-reviewer` | | |
