# Lesson: std::jthread worker threads with the logger — the old way that stops late, and cooperative stop (`thread_and_log`)

To stop a worker thread, the thread has to notice the request "please stop", and then you have to `join` it. This lesson shows it in four steps. (1) It times how **late** an old-style worker made of `std::thread` + a `std::atomic<bool>` flag + `sleep_for` stops after the request. (2) It times how long the `std::jthread` + `stop_token` worker (`PeriodicWorker` of the `jthread_worker` unit) takes with the same period. (3) It shows `std::stop_callback`, a function called once when a stop is requested. (4) It runs periodic work on two `PeriodicWorker` threads with one `Logger` per feature. The whole run takes under a second. Background: [jthread_stop_token.en.md](/docs/cpp_evolution/jthread_stop_token.en.md).

## The old way and C++20
| | `std::thread` + a flag (C++11) | `std::jthread` + `stop_token` (C++20) |
|---|---|---|
| Lifetime | destroying it while `joinable()` calls `std::terminate`; you need a class whose destructor calls `join()` yourself | the destructor calls `request_stop()`, then `join()` |
| Asking to stop | you make a `std::atomic<bool>` flag and the thread function reads it yourself | a `stop_source` asks, the thread function receives a `stop_token` |
| Waking a wait | impossible: the flag is seen only when `sleep_for` ends, so the stop is up to **one period** late | `condition_variable_any::wait_for(lock, token, …)` wakes at once on the stop request |
| What to do at stop | the requester calls it directly | register a `std::stop_callback` |

The old-style code is in [legacy_worker.hpp](legacy_worker.hpp) and [jthread_stop_token.en.md](/docs/cpp_evolution/jthread_stop_token.en.md). Ending the program without joining a `std::thread` ends it with `std::terminate`, and the later steps could not run, so the lesson does not run that; it is left to exercise 6.

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `py -3 .agent/scripts/build.py --preset <preset> --target lesson_thread_and_log`, then `out/build/<preset>/bin/lessons/lesson_thread_and_log` (`.exe` on Windows), or `ctest --preset <preset> -R lesson.thread_and_log`

## What to look for
Sample output (the numbers differ from run to run; the lesson only prints the values and does not judge them):
```text
== Step 1: std::thread with a stop flag (the old way) ==
legacy stop took 83 ms (period 100 ms)
== Step 2: std::jthread with a stop_token ==
jthread stop took 0 ms
== Step 3: std::stop_callback ==
callback ran on the requesting thread: true
callback ran on the main thread: false
registered after the request, callback ran at once: true
```
- Step 1: it creates a `LegacyWorker` (period 100 ms) and calls `requestStop()` 15 ms later. The thread is inside `sleep_for` then, so it cannot see the flag; it sees it only after the sleep ends, and stops. The end of the block runs `~LegacyWorker`, which `join`s, so the measured time is about `100 - 15 = 85 ms`. The stop is **up to one period** late.
- Step 2: the `PeriodicWorker` with the same period waits with `condition_variable_any::wait_for(lock, stop_token, …)`, so `requestStop()` wakes the wait at once. The measured time is usually 0 to a few ms. The difference between the two times is the point of this lesson.
- Step 3: a `stop_callback`'s callback runs at once on the **thread that calls** `request_stop()` (`true` for the requesting thread, `false` for main). If you register it after the request, the callback runs at the place of registration (inside the constructor).
- Step 4: this part was here before. Two workers with periods of 20 ms and 30 ms run for about 200 ms and print their tick counts. A `Logger` is safe to share between threads, `log()` takes no lock, and one log thread writes the lines to the history, the live output and the file (spec 010-09). So three `Logger`s can share one `std::cout` without mixing lines. Delivery is **asynchronous**, so before printing to `std::cout` directly you wait with `logger.flush()` until every earlier log line is out (`flush()` waits for every line written before the call through any `Logger`). If the call must return after the line is recorded, use `Config::delivery = Delivery::Sync`. With the crash dump on (`enableCrashDump = true`, the default; this lesson turns it off), the latest records of **all threads** (finished ones included) are kept at a crash, and you read them with `py -3 tools/read_dump.py log/crash_dump_<time>.log`.
- Split `Logger`s by **feature**, not by thread count (output target, history size, the directory for a manual `dump()`). The crash dump target is one per process, and the first `Logger` prepared decides the directory. You can measure the speed difference between a shared `Logger` and one `Logger` per thread with `logger_contention_probe` (spec 010-08).
- Waiting precision differs by OS. On Windows `sleep_for` and condition-variable waits move in steps of about 16 ms, so the Step 1 value can go a little over the period of 100 ms (once in ten runs it was 102 ms), and in Step 4 the tick counts of the 20 ms and 30 ms workers can come out equal.

## Exercises
1. **Change the periods**: change the periods of the two Step 4 workers to 10 ms and 50 ms. Check that the tick counts over the total run time (about 200 ms) are roughly 5:1 (on Windows the ratio can be smaller because of the waiting precision).
2. **Early stop**: in Step 4, call `worker_fast.requestStop()` at the 100 ms point of `std::this_thread::sleep_for(100ms)` and then wait another 100 ms. Watch that `worker_fast` stops at once at 100 ms and only `worker_slow` keeps running until 200 ms.
3. **Log level and a condition per tick**: inside a worker's `task` lambda, change the code so that on a certain tick (for example `tick % 3 == 0`) it writes a warning with `fast_logger.log(atugcc::core::Level::Warn, ...)`.
4. **Shared Logger versus one Logger per feature**: make the two workers share `logger` (change `fast_logger` and `slow_logger` to `logger` in the constructor arguments and in the lambdas). Check that the output lines do not mix, and that `snapshot()` holds the lines of both workers in time order. Also see what happens to the order of the last `std::cout` lines and the log lines when you remove `logger.flush()`. Then think of a case that needs per-feature settings, such as "send only the slow worker's log to a file" (pass a `std::ofstream` as `liveOutput`), and explain why one `Logger` per feature is still useful.
5. **Grow the old worker's period**: change `kPeriod` in `main.cpp` to 500 ms and run it. How large is `legacy stop took … ms (period 500 ms)`, and what happens to `jthread stop took … ms`? What does the lateness of the stop depend on?
6. **Remove `join()`**: remove the `join()` call from `~LegacyWorker` in `legacy_worker.hpp` and run it. How does the program end? Why can this not happen with `std::jthread`? Reset the file when you are done.
