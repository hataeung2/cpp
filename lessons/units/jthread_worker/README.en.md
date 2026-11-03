# Unit: jthread_worker

A background worker thread unit that uses `std::jthread` and `std::stop_token` to do periodic work, with safe cooperative cancellation and RAII destruction.

## 1. Overview and learning points

`std::jthread`, added in C++20, fixes several weak points of `std::thread`. This unit's `PeriodicWorker` follows these principles:

1. **RAII auto-join and cancellation (`std::jthread`)**
   - A `std::thread` that is destroyed without a call to `join()` or `detach()` (still `joinable()`) calls `std::terminate()` and ends the process, even if its thread function has already finished.
   - A `std::jthread` calls `request_stop()` and then `join()` in its destructor, so it cleans up without leaks or an abnormal end.

2. **`std::condition_variable_any` with `std::stop_token`**
   - If the periodic wait uses a plain `std::this_thread::sleep_for()`, a stop request that arrives during the wait is not noticed until the period is over.
   - With `cv_.wait_for(lock, stop_token, period, pred)`, the moment `request_stop()` is called the condition variable wakes at once through the `stop_token`'s callback, and the thread ends without delay.

3. **Member destruction order (reverse declaration order) and thread safety**
   - By the C++ standard, class members are destroyed in the **reverse order of their declaration**.
   - In `PeriodicWorker`, the `std::jthread thread_` member is **declared as the last member of the class**.
   - So when the destructor runs, `thread_` is destroyed first (stop request + join completed). Only after the thread loop function (`run()`) has fully ended are the other members (`logger_`, `task_`, `cv_mutex_`, `cv_`, ...) destroyed, which rules out dangling-reference / use-after-free bugs where the thread touches an already destroyed member.

4. **Lifetime of the injected Logger**
   - `PeriodicWorker` keeps the injected `atugcc::core::Logger&` as a reference. The Logger must outlive the worker.
   - A `Logger` is safe to share between threads (spec 010-08), so you may pass the same Logger to several workers. Give each worker its own Logger when you want separate settings per feature.

## 2. Interface

```cpp
namespace atugcc::lessons::jthread_worker {

class PeriodicWorker {
public:
    PeriodicWorker(std::string name,
                   std::chrono::milliseconds period,
                   std::function<void(std::size_t tick)> task,
                   atugcc::core::Logger& logger);

    ~PeriodicWorker() = default;

    // No copy, no move
    PeriodicWorker(const PeriodicWorker&) = delete;
    PeriodicWorker& operator=(const PeriodicWorker&) = delete;
    PeriodicWorker(PeriodicWorker&&) = delete;
    PeriodicWorker& operator=(PeriodicWorker&&) = delete;

    void requestStop();
    void join();
    [[nodiscard]] std::size_t ticks() const noexcept;
};

} // namespace atugcc::lessons::jthread_worker
```

## 3. Example

```cpp
#include "atugcc/core/logger.hpp"
#include "units/jthread_worker/jthread_worker.hpp"

// [Note] The Logger must outlive the worker (the worker keeps a reference). Several workers may share one Logger (spec 010-08).
atugcc::core::Logger worker_logger;

atugcc::lessons::jthread_worker::PeriodicWorker worker{
    "Worker1",
    std::chrono::milliseconds(50),
    [](std::size_t tick) {
        // Work called every 50ms (receives the tick number, starting at 0)
    },
    worker_logger
};

std::this_thread::sleep_for(std::chrono::milliseconds(200));
worker.requestStop();
worker.join();
```
