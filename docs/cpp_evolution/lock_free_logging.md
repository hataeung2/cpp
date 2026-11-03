# C++ Evolution: From a Locked Logger to Per-Thread Buffers

## Why
In 010-08, `atugcc::core::Logger` became safe to share by holding one mutex around its history. Measured on Release builds with 8 threads and no live output, the shared Logger's p99 call latency was 37× (Linux) and 12.7× (Windows) that of one Logger per thread, at 26 % and 47 % of the throughput ([010-08 testrecord](/docs/tasks/feature_010-08-logger-cleanup/testrecord.md)). With live output on, the stream write itself (5–9 µs a line, p99 in the hundreds of µs) ran on every logging thread. And the crash dump held only the crashing thread's lines. Task 010-09 moves the shared state off the hot path.

## C++11/17 (Legacy): one lock, one stream
```cpp
class Logger {
  std::mutex m_;
  std::ofstream out_;
public:
  void log(const std::string& line) {
    std::lock_guard lock(m_);   // every thread waits here
    out_ << line << '\n';       // and pays for the write
  }                             // a crash loses what is still in out_'s buffer
};
```
A background thread with a `std::queue` + `std::condition_variable` takes the write off the caller, but the queue's mutex is still one shared point, and the queue is gone when the process crashes.

## C++20: per-thread SPSC buffers and one consumer
```cpp
// producer: the calling thread, its own buffer, no lock
auto& buf = detail::threadBuffer();                     // thread_local handle, buffer from a registry
buf.tryWrite(now, seq, loggerId, level, line);          // fill slots, then
                                                        // writePos.store(w + n, std::memory_order_release)
// consumer: one log thread for all buffers
const auto w = buf.writePos();                          // acquire: sees the filled slots
/* read slots [readPos, w), sort by time, write to sinks */
buf.advanceRead(w);                                     // release: slots may be reused
```
- **Single producer, single consumer per buffer**: two atomics (`writePos` written only by the owning thread, `readPos` only by the log thread) replace the mutex. Each thread touches only its own cache lines.
- **No shared counter**: lines are ordered by `steady_clock` time plus a per-thread number. A global `fetch_add` sequence would be the same shared cache line the change removes.
- **Order without a counter (010-09-01)**: the consumer holds back records younger than 1 ms so that slower threads can catch up, but takes a half-full buffer at once so that a busy thread is not slowed down. Done per buffer, that let a thread started after `join()` be delivered before the last lines of the thread it waited for. The drain therefore runs in two passes. The first pass reads each such buffer's `writePos` (acquire) and the time of its last record, and the newest of these times becomes the cutoff. The second pass takes records from every buffer up to the cutoff (or the 1 ms limit, whichever is later). If call a happens before call b, a was published before b's time stamp was taken. If b is taken because of the cutoff, b's time stamp is no later than the cutoff record's, which was published before the first pass read it; if b is taken because it is older than the 1 ms limit, a was published before that moment too. Either way the second pass, which reads a's buffer after both, sees a, and no record ahead of a in its buffer can be newer than the bound (each was published before a). So a is taken with b. The promise is the happens-before order of one Logger's lines (same thread, `join`, mutex, release/acquire), except two calls on different threads that read the same clock tick: equal times are sorted by thread number, which does not follow the happens-before order. Threads with no such order are only sorted by time.
- **Waking without a lost-wakeup bug**: the consumer waits on a condition variable with a timeout (the drain interval, 5 ms by default), and a producer notifies it early for `Warn` and above or a half-full buffer; a missed notification costs at most one interval. A producer facing a full buffer backs off (`yield`, then `sleep_for(50us)`) until its deadline instead of blocking on a lock.
- **`std::jthread` + `std::stop_token`** give the consumer a clean stop; `std::atexit` / `std::at_quick_exit` drain before the process ends.

## The part that keeps logs after a crash
- Buffers are one contiguous, pointer-free block each and are **never freed**, so a signal handler can walk the registry (`forEachBuffer`, acquire loads only) and `write(2)` every block to a file opened in advance. Consumed slots stay in place until the producer needs them, so the dump holds the newest records of every thread, delivered or not.
- A record being overwritten is excluded by a third position, `reservePos`, published before the slots are touched (`std::atomic_thread_fence(std::memory_order_seq_cst)` orders it before the plain stores).
- The handler path uses only `write`, `sigaction`, `raise`, atomics and a hand-written integer formatter: no `snprintf`, no `std::string`, no allocation, no lock (async-signal-safety). An alternate signal stack per thread (`sigaltstack`; Windows `SetThreadStackGuarantee`) lets it run after a stack overflow.
- `tools/read_dump.py` turns the raw blocks back into time-ordered text and marks the records the log thread had not delivered yet.

## Buffers in a memory-mapped file (010-10)
A crash handler cannot run when the process is killed from outside (SIGKILL, `TerminateProcess`). If the buffers themselves live in a file mapping, the OS keeps their bytes in the file, and the next run can read them.

```cpp
// C++11/17: map the file and treat the bytes as a struct
auto* hdr = reinterpret_cast<Header*>(mmap(...));   // no object lives there: strictly UB
if (hdr->count > 0) { ... }                         // and a corrupt file is trusted as is
```
```cpp
// C++20 (atugcc): the writer starts each object's lifetime, the reader copies and checks
ThreadLogBuffer::createIn(base + offset, slots);   // placement new: std::atomic members are real objects
std::atomic_ref<std::uint64_t>(header.arenaUsed)    // plain header fields, updated atomically in place
    .compare_exchange_weak(used, used + need);
MapHeader h;  std::memcpy(&h, bytes, sizeof h);     // recovery: copy into a trivially copyable struct,
if (h.fileBytes != size || ...) { /* .corrupt */ }  // validate every size and position before use
```
- Copying bytes with `memcpy` into an existing trivially copyable struct has always been well defined; P0593 (C++20) adds that `memcpy`, `malloc` and similar operations implicitly create objects, while placement new on the writer side starts the lifetimes explicitly. `std::atomic_ref` (C++20) gives atomic access to a plain field without making the struct non-copyable.
- C++23's `std::start_lifetime_as<T>(p)` (P2590) states "these bytes are a `T`" directly; MSVC and GCC do not ship it yet, so atugcc keeps `memcpy`.
- Which records count as lost is decided by the same positions as the crash dump: the consumer moves `readPos` only after every sink has a record, so `[readPos, writePos)` holds every record no sink received; a record written to the file just before the kill (before `readPos` moved) can appear in both.
- [`detail/log_map.hpp`](/include/atugcc/core/detail/log_map.hpp) (format), `src/core/log_map_recover.cpp` (recovery), spec [010-10](/docs/specs/010_10_logger_mapped_buffers.md).

## C++23 (Current, atugcc)
- [`logger.hpp`](/include/atugcc/core/logger.hpp): `Delivery::Async` / `Sync`, `OverflowPolicy::BlockThenDrop` / `Block`, `Durability::Process` / `System`, `flush()`, `droppedCount()`.
- [`detail/thread_log_buffer.hpp`](/include/atugcc/core/detail/thread_log_buffer.hpp), [`detail/log_registry.hpp`](/include/atugcc/core/detail/log_registry.hpp), [`detail/log_service.hpp`](/include/atugcc/core/detail/log_service.hpp).
- Failures are values (`std::expected` through `atugcc::core::Result`): an invalid `configureLogBuffers` value, a log file that cannot be opened.
- Measured result: [010-09 testrecord](/docs/tasks/feature_010-09-logger-thread-buffers/testrecord.md) (AC-1).
- Lesson: [`log_recovery`](/lessons/tracks/01_essentials/12_log_recovery/README.en.md) (essentials track) ends a run without cleanup (`std::_Exit`) and shows the next run recovering the lines that never reached the screen.
