# Modern C++23 RingBuffer Architecture & implementation Study

> **A record of the old design.** The design this page describes, many threads sharing one global `boost::lockfree::spsc_queue`, was removed by 010-09 (why many producers must not share one SPSC queue: [KI-025](/docs/known_issues.md)). The current design is per-thread SPSC buffers and one consumer thread: [lock_free_logging.en.md](/docs/cpp_evolution/lock_free_logging.en.md), [010-09 spec](/docs/specs/010_09_logger_thread_buffers.md) (in Korean), lesson [`lock_free_buffer`](/lessons/tracks/01_essentials/13_lock_free_buffer/README.en.md).

This page analyses the core structure and the modern C++ syntax of the high-performance logging system implemented in commit `f8c62cf949757af763a328427e0213b170b7799c`.

---

## 1. Architecture

### 1-1. Fixed-block memory layout
Instead of the earlier dynamic memory allocation based on `std::string`, it uses **fixed 128-byte blocks**.
- **Benefit**: no heap allocation (malloc/new) happens, so run-time performance is very consistent (deterministic) and cache efficiency is maximized.
- **Block layout**: `[2B Header][125B Payload][1B Sentinel]`
  - **Header (16-bit)**:
    - `bit[15:14]`: log level (Debug, Info, Warn, Error)
    - `bit[13]`: continuation flag (whether the message continues in the next block)
    - `bit[12:0]`: length of the actual data (max 125)

### 1-2. Thread-local isolation (no-lock write)
The biggest performance gain comes from isolating writes completely with the **`thread_local`** keyword.
- Each thread has its own `RingBuffer` instance (`DbgBuf::instance()`).
- Writes never contend with other threads, so **no mutex (lock) is needed at all.**

### 1-3. A global SPSC (single-producer single-consumer) queue
When a thread's local buffer is filled beyond a set amount (50 %), it hands the data over to a shared global queue.
- **`boost::lockfree::spsc_queue`**: the producer is the thread that writes the log; the consumer is a dedicated logger thread that saves the log to a file or prints it.
- With this design, logging is fully separated from the time spent waiting on actual I/O (file writes).

---

## 2. Modern C++ syntax used (key features)

### 2-1. `concepts` & `requires` (C++20)
The template arguments are checked strictly at compile time.
```cpp
template <std::size_t BlockSize, std::size_t BlockCount>
    requires (BlockCount > 1 && (BlockCount & (BlockCount - 1)) == 0) // power-of-two check
          && (BlockSize >= 4)
class RingBuffer { ... };
```
- The bit operation (`BC & (BC-1)`) guarantees that the ring buffer size is a power of two, so the remainder operation can be replaced by `& mask` (faster).

### 2-2. `std::atomic` & memory order (memory model)
When indices are shared between threads, the memory barriers are controlled precisely for performance.
- **`memory_order_release`**: when the index is updated after writing the data, it guarantees that "the data I wrote is surely visible to the other thread".
- **`memory_order_acquire`**: when the index is read, it makes "the latest data for that index" observable.
- **`std::memory_order_relaxed`**: index reads and writes used only within the thread use relaxed, which has no overhead.

### 2-3. `alignas(64)` (preventing false sharing)
The cache line size of modern CPUs (one unit of the CPU cache) is usually 64 bytes.
```cpp
alignas(64) std::atomic<uint32_t> write_idx_{0};
alignas(64) uint32_t read_idx_{0};
```
- If the two indices are on the same cache line, every update by one thread invalidates the other thread's cache and performance drops: this is **false sharing**. `alignas(64)` separates them physically.

### 2-4. `thread_local` singleton
```cpp
RingBuffer<>& DbgBuf::instance() noexcept {
    thread_local RingBuffer<> buf;
    return buf;
}
```
- An elegant modern pattern that solves the weakness of a global singleton, "every thread shares it", while managing a separate store for each thread automatically.

---

## 3. Algorithm: newest-wins eviction

When a ring buffer is full, the traditional response is to return an error or wait, but a logging system needs to **keep the newest logs**.
- `evictIfNeeded`: when `(write_idx + 1) == read_idx`, it drops the oldest unread log (`read_idx`) outright and moves one slot forward.
- This way the buffer keeps cycling and always holds exactly the newest N logs.

## 4. Tip: physically separating the template implementation
- **Problem**: putting a template's implementation in a `.cpp` causes a link error (`LNK2019`) when another file uses it.
- **Solution**: most of the implementation moves to the bottom of the `.hpp`, while methods with heavy dependencies (`boost` and so on), such as `flushToQueue`, are defined in the `.cpp` through `template<>` specialization, separating build time and dependencies.
