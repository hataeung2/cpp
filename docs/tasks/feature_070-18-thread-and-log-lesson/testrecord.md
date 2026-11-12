# Test record: 070-18 essentials `thread_and_log` 보강

- Spec: [/docs/specs/070_18_thread_and_log_lesson.md](/docs/specs/070_18_thread_and_log_lesson.md)
- Plan: [plan.md](plan.md)
- Hosts: Windows 11 (MSVC, `windows-x64-debug`), WSL2 Ubuntu 24.04 (Clang 20, libstdc++ 14: `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan`). "Web" means the Clang/libstdc++ build, the web's compiler; the practice copy is solved with `tools/exercises.py check`, the same `check_practice` the server runs.

## Runs
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R1 | `build.py --preset windows-x64-debug --target lesson_thread_and_log` | builds, 0 warnings | built, no warning lines | Pass |
| R2 | one run of `lesson_thread_and_log.exe` | Step 1–4 headers, `legacy stop took … (period 100 ms)`, `jthread stop took …`, 3 `stop_callback` lines, tick lines | all present; `callback ran on the requesting thread: true`, `… main thread: false`, `registered after the request, callback ran at once: true`; 0.46 s | Pass |
| R3 | `build.py --preset linux-x64-{debug,asan,tsan} --target lesson_thread_and_log`, then `ctest --preset <p> -R lesson.thread_and_log` (WSL) | builds, passes | 3 × `lesson.thread_and_log` Passed (0.33 s, 0.36 s, 0.36 s); no TSan report | Pass |
| R4 | ten runs, `legacy stop` and `jthread stop` (table below) | legacy > jthread, legacy ≤ about one period | Linux: legacy 85–86 ms, jthread 0–1 ms. Windows: legacy 82–102 ms, jthread 0–1 ms | Pass, with the 102 ms note |
| R5 | `py -3 tools/lessons.py check` | 0 / 0 | 0 errors, 0 warnings (17 lessons) | Pass |
| R6 | `exercises.py verify thread_and_log --preset windows-x64-debug`; CTest `lesson.thread_and_log.exercises_verify` | no automatic exercise passes on the unchanged lesson | "no automatic exercise passes on the unchanged lesson"; CTest Passed on both presets (R9, R10) | Pass |
| R7 | every automatic exercise solved on the practice copy (table AC-5), `exercises.py check` on `windows-x64-debug` and (WSL) `linux-x64-debug`; copy reset between exercises | the solved one passes, the others fail with their reasons | see AC-5 | Pass |
| R8 | search of the real index (`tools/lessons.py index`) with the frontend's `lessonHaystack` and `matches` in a temporary vitest test (deleted afterwards): `jthread`, `stop_token`, `stop_callback`, `std::thread`, `jthread stop_callback`, `unit:jthread_worker` | each finds `thread_and_log` | the test passed (all six queries) | Pass |
| R9 | `build.py --preset windows-x64-debug --test` | all pass, 0 warnings | 39/39, 0 warning lines (incl. `lesson.thread_and_log`, `lesson.thread_and_log.exercises_verify`) | Pass |
| R10 | `build.py --preset linux-x64-debug --test` (WSL) | all pass | 39/39 (incl. `PlaygroundServer`, the 4 × `exercises_verify`) | Pass |
| R11 | `py -3 .agent/scripts/lint_docs.py` | exit 0 | 0 errors, 0 warnings (final run after the last edit, see below) | Pass |
| R12 | exercise 4 as the corrected text says (all `fast_logger`/`slow_logger` of Step 4 → `logger`) on the practice copy, `windows-x64-debug` | builds, runs, tick lines go through `logger` | exit 0, 12 `[DEBUG] … tick` lines through the one shared logger | Pass |

### R4: ten runs
| run | Windows legacy / jthread (ms) | Linux legacy / jthread (ms) |
|---|---|---|
| 1 | 83 / 0 | 86 / 0 |
| 2 | 99 / 1 | 86 / 1 |
| 3 | 86 / 1 | 85 / 0 |
| 4 | 83 / 0 | 86 / 0 |
| 5 | 84 / 1 | 86 / 0 |
| 6 | 82 / 1 | 85 / 0 |
| 7 | 98 / 1 | 86 / 0 |
| 8 | 84 / 1 | 85 / 0 |
| 9 | **102** / 0 | 85 / 0 |
| 10 | 84 / 1 | 86 / 0 |

The legacy stop is always far above the jthread stop. On Windows run 9 went 2 ms over the period (100 ms) because `sleep_for` has a granularity of about 16 ms; the README says so. A run with period 500 on Windows read 500 ms (R7 below), the same cause.

## AC-5: automatic exercises solved by their answers
| Exercise | Change in the practice copy | Clang 20 (web compiler) | MSVC `windows-x64-debug` |
|---|---|---|---|
| `change_periods` | `main.cpp`: periods 20 → 10, 30 → 50 | pass (ticks 19 / 3) | pass (ticks 12 / 3) |
| `warn_every_third` | `main.cpp`: `if (tick % 3 == 0)` with `Level::Warn` in the `worker_fast` lambda | pass (`[WARN]` at ticks 0, 3, 6) | pass (`[WARN]` at ticks 0, 3) |
| `legacy_period` | `main.cpp`: `kPeriod{500}` | pass (`legacy stop took 485 ms (period 500 ms)`) | pass (`legacy stop took 500 ms (period 500 ms)`) |
| `early_stop`, `shared_logger`, `remove_join` | observation | early_stop: ticks 4 / 6 (Windows 3 / 6); remove_join: `terminate called without an active exception`, exit 134 (`-6` in Python) | not run on MSVC Debug (the `abort()` dialog waits for a click, KI-050); shared_logger: R12 |

In every run the other automatic exercises of the lesson failed with their own reasons. The answers' numbers were checked against these runs and corrected where the first draft guessed (Windows 4:1, not 3:1; early stop 4 ticks).

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 `legacy_worker.hpp`, U2 `main.cpp` | codex `luna` (`--effort high`) | match plan design and spec §4; data races, member order, join, callback captures, forbidden literals | VERDICT none | — |
| U1 | lead (small) | redundant `stop_{ false }` in the constructor's initializer list | — | removed (the member has a default initializer) |
| U5 README, U6 evolution pair, U7 `exercises.toml` | `cpp-reviewer` | README vs code, KO vs EN, exercise order and text, C++20 statements, evolution pair shape | exercise 4 text (README and `exercises.toml`) changed only the constructor arguments although the lambdas capture `fast_logger` / `slow_logger`; `terminate called without an active exception` is libstdc++'s text and reads as platform-neutral | both fixed by the lead (small); R12 checks the corrected exercise 4; the reviewer could not confirm measured numbers, R4 and AC-5 do |

## Acceptance criteria
| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | R1–R3, R9, R10: builds without warnings on both presets, `lesson.thread_and_log` passes, output has the step headers, both stop lines, the three `stop_callback` lines and the tick lines (R2) | Pass |
| AC-2 | R4: ten runs on each OS; legacy > jthread in all, legacy ≤ period except one Windows run (102 ms, timer granularity) | Pass (recorded; the lesson does not judge) |
| AC-3 | R3: `lesson.thread_and_log` passes on `linux-x64-asan` and `linux-x64-tsan` | Pass |
| AC-4 | `lessons.py check` 0 / 0 (R5); the reviewer compared the pair: same four `##` sections, 6 exercises, 1 code block; paths are `out/build/<preset>/bin/lessons/` | Pass |
| AC-5 | `lessons.py check` 0 / 0 (R5); table above (R7); `exercises_verify` (R6, R9, R10) | Pass |
| AC-6 | `jthread_stop_token.md` and `.en.md` exist, index lines in `docs/cpp_evolution.md` and `.en.md`, E3 row `레슨 있음`; `lint_docs.py` pair-shape rule passes (R11); search R8 | Pass |
| AC-7 | R9, R10, R11 | Pass |

## Notes
- Spec §8 lists `lessons/units/jthread_worker/README.md` and `.en.md` "if needed": the unit README has no "lessons that use it" section, so a line there would add a section for nothing. Not changed.
