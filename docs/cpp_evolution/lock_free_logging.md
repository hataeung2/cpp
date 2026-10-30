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
- **Waking without a lost-wakeup bug**: the consumer waits on a condition variable with a timeout (the drain interval, 5 ms by default), and a producer notifies it early for `Warn` and above or a half-full buffer; a missed notification costs at most one interval. A producer facing a full buffer backs off (`yield`, then `sleep_for(50us)`) until its deadline instead of blocking on a lock.
- **`std::jthread` + `std::stop_token`** give the consumer a clean stop; `std::atexit` / `std::at_quick_exit` drain before the process ends.

## The part that keeps logs after a crash
- Buffers are one contiguous, pointer-free block each and are **never freed**, so a signal handler can walk the registry (`forEachBuffer`, acquire loads only) and `write(2)` every block to a file opened in advance. Consumed slots stay in place until the producer needs them, so the dump holds the newest records of every thread, delivered or not.
- A record being overwritten is excluded by a third position, `reservePos`, published before the slots are touched (`std::atomic_thread_fence(std::memory_order_seq_cst)` orders it before the plain stores).
- The handler path uses only `write`, `sigaction`, `raise`, atomics and a hand-written integer formatter: no `snprintf`, no `std::string`, no allocation, no lock (async-signal-safety). An alternate signal stack per thread (`sigaltstack`; Windows `SetThreadStackGuarantee`) lets it run after a stack overflow.
- `tools/read_dump.py` turns the raw blocks back into time-ordered text and marks the records the log thread had not delivered yet.

## C++23 (Current, atugcc)
- [`logger.hpp`](/include/atugcc/core/logger.hpp): `Delivery::Async` / `Sync`, `OverflowPolicy::BlockThenDrop` / `Block`, `Durability::Process` / `System`, `flush()`, `droppedCount()`.
- [`detail/thread_log_buffer.hpp`](/include/atugcc/core/detail/thread_log_buffer.hpp), [`detail/log_registry.hpp`](/include/atugcc/core/detail/log_registry.hpp), [`detail/log_service.hpp`](/include/atugcc/core/detail/log_service.hpp).
- Failures are values (`std::expected` through `atugcc::core::Result`): an invalid `configureLogBuffers` value, a log file that cannot be opened.
- Measured result: [010-09 testrecord](/docs/tasks/feature_010-09-logger-thread-buffers/testrecord.md) (AC-1).
