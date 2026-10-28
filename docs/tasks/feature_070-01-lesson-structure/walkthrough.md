# Walkthrough: 070-01 레슨 구조

- Spec: [/docs/specs/070_01_lesson_structure.md](/docs/specs/070_01_lesson_structure.md)
- Evidence: [testrecord.md](/docs/tasks/feature_070-01-lesson-structure/testrecord.md) (AC-1–AC-6 all Pass)
- Branch: `feature/070-01-lesson-structure`, merged into `main` by fast-forward

## Result
- `lessons/` holds tracks, lessons and reusable units ([lessons/README.md](/lessons/README.md)). Units are referenced across tracks (`jthread_worker` is used by `thread_and_log` in essentials and `device_state_machine` in patterns); library headers are referenced with `lib:`, never copied.
- Every `lessons/tracks/*/*/lesson.toml` becomes `lesson_<id>` (`bin/lessons/`) and a smoke test `lesson.<id>` (quick: 10 s; long: its `timeout`, label `long`) without touching CMake files; editing a manifest reconfigures. `ATUGCC_BUILD_LESSONS=OFF` turns it all off. The TSan launcher moved to the root as `ATUGCC_TEST_LAUNCHER` and serves tests and lessons.
- [tools/lessons.py](/tools/lessons.py) `check` validates the schema, ids, `uses`, unit cycles and `#include` coverage, and reads each manifest with the same regexes as CMake so both always agree; `index` writes `out/lessons/index.json` for the web playground (070-02). `lint_docs.py` runs the check.
- Seed: units `lambda_capture`, `jthread_worker`; lessons `lambda_capture`, `thread_and_log`, `device_state_machine`. All build warning-free on MSVC and GCC and run clean under ASan/UBSan and TSan.

## Notes
- Review found that `thread_and_log` shared one `Logger` between two threads although `Logger::log` writes a single-thread-only ring buffer outside its lock; TSan missed it because `std::cout` ordered the threads. The lesson now uses one `Logger` per worker and teaches why (KI-014).
- `PeriodicWorker` has a `join()` the plan did not list; it lets a lesson read results before the worker is destroyed (recorded in plan D4).

## Follow-ups
- KI-013: `Logger::log(Level, …)` reports `logger.hpp` instead of the caller's location.
- KI-014: `Logger` thread-safety contract (shared use races on the ring buffer).
- Curriculum: 070-03 (essentials), 070-04 (patterns, moving `main.cpp` samples and `example_visualizer.cpp`).
- No `lead (fallback)` units.
