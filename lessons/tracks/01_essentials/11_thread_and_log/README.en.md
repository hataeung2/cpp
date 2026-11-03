# Lesson: std::jthread workers with the logger (`thread_and_log`)

This lesson uses the `jthread_worker` unit (`PeriodicWorker`) and `atugcc::core::Logger` to run two background threads periodically and to stop them safely.

## 1. What the lesson does

The lesson covers:
- It creates two `PeriodicWorker` instances with different periods (20ms, 30ms) and runs them at the same time.
- **One Logger per feature**: a single `Logger` is safe to share between threads. Still, this lesson gives each worker its own Logger (`fast_logger`, `slow_logger`). This is the recommended use: it lets each feature have its own settings, such as the output target (`liveOutput`) or the history size (`bufferCapacity`).
- The main thread waits about 200ms, then asks both worker threads to stop (`requestStop`) and joins them (`join`).
- It prints the total number of ticks of each thread, so you can see the effect of the periods (20ms vs 30ms).
- The whole run ends quickly, within a second (about 200–250ms).

## 2. Key concepts

### `std::thread` vs `std::jthread` (C++20)
- **Auto-join**: when a `std::thread` object is destroyed while still `joinable()`, it calls `std::terminate()` and the program ends abnormally. A `std::jthread` requests a stop and calls `join()` in its destructor.
- **Cooperative cancellation**: a `std::jthread` holds a `std::stop_source` and can pass a `std::stop_token` to the thread function. When `request_stop()` is called from outside, `stop_token.stop_requested()` becomes true and the loop can exit safely.

### `std::condition_variable_any::wait_for` with `std::stop_token`
- A plain `sleep_for()` does not notice a stop request while it sleeps. The `wait_for(lock, stop_token, period, pred)` overload of `std::condition_variable_any` stops waiting and returns as soon as a stop is requested on the `stop_token`.

### The Logger's thread-safety contract
- Every public function of `atugcc::core::Logger` is safe to call from several threads at once, and `log()` takes no lock. Each thread puts its lines into its own buffer, and one log thread writes them to the history (`snapshot()`), the live output and the file (spec 010-09).
- So delivery is **asynchronous**. Before printing to `std::cout` directly, wait with `logger.flush()` until every earlier log line is out (end of `main.cpp`; `flush()` waits for every line written before the call, through any Logger). If a call must return only after its line is written, use `Config::delivery = Delivery::Sync` (returns after writing to the OS; with `Durability::System`, to the disk).
- Only the log thread writes the live output and the file, so several Loggers can share one `std::cout` without mixing lines.
- With crash dumps on (`enableCrashDump = true`, the default; this lesson turns it off), a crash leaves the recent records of **every thread** (including threads that already ended) in the crash dump. Read it with `py -3 tools/read_dump.py log/crash_dump_<time>.log`. The table in the root README says what each kind of ending leaves.
- **So when do you split?** By feature, not by number of threads (output target, history size, the directory for a manual `dump()`). There is one crash dump target per process, and the first Logger that prepares it chooses the directory. There is no level filter yet. You can measure the performance difference between a shared Logger and per-thread Loggers with `logger_contention_probe` (spec 010-08).

## 3. How to run

### Through ctest (smoke test)
```bash
ctest -R lesson.thread_and_log --output-on-failure
```

### Running the executable directly
```bash
# Windows
bin\lessons\lesson_thread_and_log.exe
# or, with a Debug configuration
bin\Debug\lessons\lesson_thread_and_log.exe

# Linux
bin/lessons/lesson_thread_and_log
```

## 4. Exercises

1. **Change the periods**: set the two workers' periods to 10ms and 50ms. Check that over the 200ms run the tick counts are roughly 5:1.
2. **Early stop**: call `worker_fast.requestStop()` after `std::this_thread::sleep_for(100ms)`, then wait another 100ms. Watch `worker_fast` stop at once at 100ms while only `worker_slow` keeps going until 200ms.
3. **Change the log level and log per tick**: in the worker's `task` lambda, log a warning with `logger.log(atugcc::core::Level::Warn, ...)` on certain ticks (for example `tick % 3 == 0`).
4. **Shared Logger vs one Logger per feature**: make both workers share `logger` (pass `logger` instead of `fast_logger`, `slow_logger`). Check that the output lines do not mix and that `snapshot()` holds the lines of both workers together in time order. Also delete `logger.flush()` and see how the order of the last `std::cout` lines and the log lines changes. Then think of a situation that needs per-feature settings, such as "send only the slow worker's log to a file" (try passing a `std::ofstream` as `liveOutput`), and explain why one Logger per feature is still useful.
