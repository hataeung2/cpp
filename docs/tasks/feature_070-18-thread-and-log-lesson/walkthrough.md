# Walkthrough: 070-18 essentials `thread_and_log` 보강

## Result
The lesson `thread_and_log` now has the "old way → C++20" comparison the other essentials lessons have:
- `legacy_worker.hpp`: `LegacyWorker` (`std::thread` + `std::atomic<bool>` + `sleep_for`, the destructor joins). Step 1 of `main.cpp` times how late it stops after `requestStop()` (about `period - 15 ms`, always under about one period), Step 2 times the `PeriodicWorker` (`std::jthread` + `condition_variable_any::wait_for(lock, token, …)`): 0 to 1 ms. Step 3 prints the two behaviours of `std::stop_callback` (it runs on the thread that calls `request_stop()`; registered after the request it runs inside the constructor). Step 4 is the earlier content (one `Logger` per feature, `flush()`, tick counts) unchanged in behaviour. The whole run takes under half a second.
- README in Korean and English in the format of `chrono_time` (comparison table, run, what to look for, six exercises). The Logger notes of the old README moved into the Step 4 bullet.
- `exercises.toml`: six exercises, three automatic (`change_periods`, `warn_every_third`, `legacy_period`), three observation (`early_stop`, `shared_logger`, `remove_join`). `remove_join` is the `std::terminate` of a joinable `std::thread`, done on a practice copy instead of in a lesson step.
- `docs/cpp_evolution/jthread_stop_token.md` and `.en.md` (old code, new code, the three `stop_token` tools, member order), index lines in both evolution tables, candidate E3 `레슨 있음`, tag aliases `stop_token`, `stop_callback`, `std::stop_callback`.

Evidence: [testrecord.md](testrecord.md) (both full suites 39/39 with 0 warnings, asan and tsan runs, ten timing runs per OS, every automatic exercise solved on MSVC and Clang).

## Notes
- No `lead (fallback)` unit. The two C++ units were written by agy `flash` and reviewed by codex `luna` (high effort): none. The doc units were reviewed by `cpp-reviewer`; its two findings (exercise 4 wording, a libstdc++-only message text) are fixed.
- The first drafts of three answers guessed numbers (Windows tick ratio 3:1, early-stop ticks); they were replaced with the measured values (4:1, 4 ticks).
- A Windows run of Step 1 once read 102 ms for a 100 ms period (timer granularity of about 16 ms). The lesson prints values and judges nothing; the README says so.
- The unit README of `jthread_worker` was not changed (spec §8 "if needed": it has no section for the lessons that use it).
- The `practice/` folder is untracked; the progress record my checks wrote was removed, the reset backups remain.

## Follow-ups
- None new. On `windows-x64-debug` exercise `remove_join` would show the `abort()` dialog the same way as `error_expected` `remove_catch` (KI-050); it is an observation exercise, so nothing waits on it.
- The remaining lessons' exercise definitions are 070-20.
