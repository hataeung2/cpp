# Plan: 070-18 essentials `thread_and_log` 보강

- Spec: [/docs/specs/070_18_thread_and_log_lesson.md](/docs/specs/070_18_thread_and_log_lesson.md) (approved 2026-11-10)
- Branch: `feature/070-18-thread-and-log-lesson` (from `main` at `c8d88e0`)

## Model assignment
Default split ([delegation.md](/.agent/rules/delegation.md) §1). The two C++ units touch thread lifetime, atomics and stop tokens: risky, so agy `flash` writes them (implementer chain §6.1) and codex `luna --effort high` reviews them (other family). The lesson manifest and tag lines are one-line changes (`lead (small)`). README, evolution pages, `exercises.toml` and the index lines are doc units written by the lead; one fresh reviewer (`cpp-reviewer`) checks the README and evolution pairs against spec §2.2/§3/AC-4.

## Design

### Files
- [NEW] `lessons/tracks/01_essentials/11_thread_and_log/legacy_worker.hpp`
- [MODIFY] `lessons/tracks/01_essentials/11_thread_and_log/main.cpp`, `lesson.toml`, `README.md`, `README.en.md`
- [NEW] `lessons/tracks/01_essentials/11_thread_and_log/exercises.toml`
- [NEW] `docs/cpp_evolution/jthread_stop_token.md`, `jthread_stop_token.en.md`
- [MODIFY] `docs/cpp_evolution.md`, `docs/cpp_evolution.en.md`, `docs/lesson_candidates.md`, `lessons/tags.toml`, `lessons/units/jthread_worker/README.md`, `README.en.md` (one line, only if it reads better)

C++20/23 features applied: `std::jthread`, `std::stop_token`, `std::stop_source`, `std::stop_callback` (CTAD), `condition_variable_any::wait_for(lock, token, …)` (already in the unit). Pre-C++20 pattern replaced: `std::thread` + `std::atomic<bool>` + `sleep_for` → evolution pair `jthread_stop_token.md` + `.en.md` (impl.md §6).

### `legacy_worker.hpp` (spec Assumption 2, §2.2, §4; AC-1, AC-3)
`namespace thread_and_log_lesson`, `class LegacyWorker`, header-only (members defined in the class: implicitly inline).
- `explicit LegacyWorker(std::chrono::milliseconds period)`: starts the thread in the member-initializer list; the thread function is a lambda capturing `this` that calls a private `run()`.
- `~LegacyWorker()`: `requestStop();` then `join()` when `thread_.joinable()`. No public `join()` (the end of the scope is the join: the lesson and exercise 6 depend on it).
- `void requestStop()`: `stop_.store(true)` (default `seq_cst`). Callable more than once.
- Copy and move deleted (a comment says why: moving a `std::thread` over a `joinable` one also calls `std::terminate`, and the thread function holds `this`).
- `run()`: `while (!stop_.load()) { std::this_thread::sleep_for(period_); }` with a comment where the periodic work would go. The flag is read only after the sleep ends, so a stop request is seen up to one period late.
- Members, in this order: `period_` (`std::chrono::milliseconds`), `stop_` (`std::atomic<bool>`, initial false), `thread_` (`std::thread`, **last**).
- Bilingual comments (Korean line, English line below): why at most one period late; a `std::thread` that is still `joinable()` when destroyed calls `std::terminate` (so the destructor joins); `thread_` is declared last because members are constructed in declaration order and the thread function reads `period_` and `stop_` at once, so both must exist before the thread starts (the destructor body joins before any member is destroyed, so destruction order is not the issue here, unlike `PeriodicWorker` where the `std::jthread` joins in its own destructor).
- Includes only what it uses: `<atomic> <chrono> <thread>`.

### `main.cpp` (spec Assumptions 2, 4, 5, 6, §4; AC-1, AC-2, AC-3)
Four steps, each starting with its header line on `std::cout`. Steps 1–3 use `std::cout` only and run before any `Logger` of the lesson exists, so no asynchronous Logger line can mix into them.
- Anonymous namespace constants `kPeriod{100}` (`std::chrono::milliseconds`) and `kHeadStart{15}` (the main thread waits this long so that the worker is already inside its first wait). No other `milliseconds(10)`, `(50)`, `{10}`, `{50}` and no `500` anywhere in the file (exercises 1 and 5 look for them).
- Helper `elapsedMs(t0, t1)`: `steady_clock` points → `std::chrono::round<std::chrono::milliseconds>(t1 - t0).count()`.
- Step 1 `== Step 1: std::thread with a stop flag (the old way) ==`: a block holds a `LegacyWorker{kPeriod}`; after `kHeadStart` take `t0`, call `requestStop()`; the end of the block runs `~LegacyWorker` (join); `t1` is taken after the block. Prints `legacy stop took <n> ms (period <kPeriod> ms)`.
- Step 2 `== Step 2: std::jthread with a stop_token ==`: a quiet `Logger` (`Logger::Config{.enableCrashDump = false}`, `liveOutput` null) declared before the worker; a block holds `PeriodicWorker{"StopTimer", kPeriod, {} (empty task), quiet_logger}`; after `kHeadStart` take `t0`, `requestStop()`, `join()`; `t1` after the block. Prints `jthread stop took <n> ms`.
- Step 3 `== Step 3: std::stop_callback ==`: a `std::stop_source`; a `std::stop_callback` (CTAD) registered **before** the request stores `std::this_thread::get_id()` of the thread that runs it; a `std::thread` stores its own id and calls `request_stop()`; `join()`. Prints `callback ran on the requesting thread: <bool>` and `callback ran on the main thread: <bool>` (true / false). Then, with the stop already requested, a second `std::stop_callback` registered on the same source sets a `bool` in its callback; prints `registered after the request, callback ran at once: <bool>` (true; the constructor runs the callback before it returns). Nothing else writes to `std::cout` while the callback runs (the main thread is in `join()`).
- Step 4 `== Step 4: workers with one Logger per feature ==`: the **existing** body of `main` unchanged in behaviour (log_config, three Loggers, "lesson start" line, `worker_fast` 20 ms and `worker_slow` 30 ms, 200 ms wait, requestStop/join, ticks, result line, `flush()`, the two `total ticks` lines), its header printed with `std::cout` before the Loggers are created.
- Comments: Korean line plus English line; `[학습]` / `[Learn]` blocks for the three new ideas. Program output is English. Steps 1–3 are small functions in the anonymous namespace (`stepLegacyStop`, `stepJthreadStop`, `stepStopCallback`), Step 4 stays in `main`.
- Time: step 1 ≈ `kPeriod - kHeadStart`, step 2 ≈ `kHeadStart`, step 4 ≈ 250 ms: well under 1 s.

### `lesson.toml` (Assumption 1)
`sources = ["main.cpp", "legacy_worker.hpp"]`; `summary` and `summary_en` mention the comparison and `stop_callback`; `title`, `tags`, `uses` unchanged.

### `lessons/tags.toml` (Assumption 9)
`[thread]` aliases add `stop_token`, `std::stop_callback`, `stop_callback` (`jthread`, `std::thread`, `std::stop_token` are already there). Check that none of the new words is an alias of another tag.

### README (spec §2.2; AC-4)
`README.md` and `README.en.md` in the format of `09_chrono_time`: lead paragraph, `## 예전 방식과 C++20` (table: lifetime, stop, waking a wait, what to do at stop), `## 실행`, `## 볼 것` (one bullet per step 1–4; the Logger notes of the old README go to step 4), `## 연습` with six numbered items (the old four keep their text and order; 5 and 6 are new). Paths `out/build/<preset>/bin/lessons/`. Same number of sections, exercises and code blocks in both languages.

### `exercises.toml` (Assumption 8, spec 070-17 §2.1)
| # | id | kind | rules |
|---|---|---|---|
| 1 | `change_periods` | auto | `source` `main.cpp` has `milliseconds\s*[({]\s*10\s*[)}]` and `…50…` |
| 2 | `early_stop` | observation | — |
| 3 | `warn_every_third` | auto | `source` has `tick\s*%\s*3\s*==\s*0` and `Level::Warn`; `expect` a `[WARN]` line (format checked in DEV) |
| 4 | `shared_logger` | observation | — |
| 5 | `legacy_period` | auto | `expect = ['^legacy stop took \d+ ms \(period 500 ms\)']`, `source` has `\b500\b` |
| 6 | `remove_join` | observation | — (the program ends with `std::terminate`) |

### Verification plan
Windows: `build.py --preset windows-x64-debug --test`; WSL: `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan` with `ctest -R lesson.thread_and_log`; ten runs of the lesson for AC-2; each auto exercise solved on a practice copy (Clang/WSL and MSVC) for AC-5; `lessons.py check`, `lint_docs.py`.

## Units

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `legacy_worker.hpp` | `LegacyWorker` (Assumption 2, §2.2; AC-1, AC-3) | `grep -c "class LegacyWorker"` = 1; `thread_` is the last member; no `join()` public | yes | agy flash | codex luna (high) | | |
| U2 | `main.cpp` | four steps (Assumptions 2, 4, 5; AC-1, AC-2, AC-3) | `grep -c "== Step"` = 4; no `500`, no `milliseconds(10\|50)`; build `lesson_thread_and_log` on `windows-x64-debug`; run prints the 7 expected lines | yes | agy flash | codex luna (high) | | |
| U3 | `lesson.toml`, `lessons/tags.toml` | sources, summaries, tag aliases (Assumptions 1, 9) | `lessons.py check` 0 errors | no | lead (small) | lead check | — | |
| U4 | run records | Windows, WSL debug / asan / tsan, ten runs (AC-1, AC-2, AC-3) | testrecord | — | lead | — | — | |
| U5 | `README.md`, `README.en.md` | new format, six exercises (§2.2; AC-4) | `lessons.py check`; section / exercise / code-block counts equal | no | lead | cpp-reviewer (with U6) | | |
| U6 | `docs/cpp_evolution/jthread_stop_token.md`, `.en.md` | old and new code, stop time, three tools, member order (§2.2; AC-6) | `lint_docs.py` (pair shape) | no | lead | cpp-reviewer (with U5) | | |
| U7 | `exercises.toml` | six exercises (Assumption 8; AC-5) | `lessons.py check` 0 / 0; `exercises.py verify thread_and_log`; each auto one solved by its answer | no | lead | — (solved on both compilers, testrecord AC-5) | — | |
| U8 | `docs/cpp_evolution.md`, `.en.md`, `lesson_candidates.md`, `jthread_worker/README*.md` | index lines, E3 `레슨 있음` (§8; AC-6) | `lint_docs.py` 0 | no | lead | | — | |
| U9 | `docs/agent_todo.md` | states | lint | no | lead | — | — | |
