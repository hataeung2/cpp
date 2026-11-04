# Walkthrough: 070-12 essentials 3차 레슨 — 시간·파일·동시성

- Spec: [/docs/specs/070_12_essentials_time_file_lockfree.md](/docs/specs/070_12_essentials_time_file_lockfree.md)
- Evidence: [testrecord.md](/docs/tasks/feature_070-12-essentials-time-file-lockfree/testrecord.md)
- Branch: `feature/070-12-essentials-time-file-lockfree`

## Result
Three new essentials lessons fill the last empty slots; the essentials track now has all 14 lessons:
- [`09_chrono_time`](/lessons/tracks/01_essentials/09_chrono_time/README.md): duration conversions (`duration_cast`, `round`, `floor`), timing with `steady_clock`, calendar dates and repairing `2026-02-31`, one fixed instant in four time zones with `%z` and the zone name, a daylight-saving gap with `choose::earliest`, chrono formatting and `std::chrono::parse`.
- [`10_filesystem_paths`](/lessons/tracks/01_essentials/10_filesystem_paths/README.md): paths, a sandbox folder `fs_sandbox/` written in binary mode, sorted listings, exceptions vs `std::error_code` vs `core::Expected`, and the modification time through `clock_cast`.
- [`13_lock_free_buffer`](/lessons/tracks/01_essentials/13_lock_free_buffer/README.md) (`long`): a release/acquire `SpscRing` against a mutex queue for 300 ms per case, false sharing, and one ring per producer (the Logger's layout), each case verified for order and loss; clean under TSan, and a `relaxed` copy shows the data race.

All three build without warnings with MSVC and Clang 20; `chrono_time` and `filesystem_paths` print the same lines on both OSes apart from the lines the spec allows. Tags `chrono`, `filesystem`, `lock_free`; `.gitignore` has `fs_sandbox/`.

Documents: new [`filesystem.md`](/docs/cpp_evolution/filesystem.md); lesson links in [`chrono_format.md`](/docs/cpp_evolution/chrono_format.md) and [`lock_free_logging.md`](/docs/cpp_evolution/lock_free_logging.md); [`modern_ring_buffer_architecture.md`](/docs/learning/modern_ring_buffer_architecture.md) starts with a notice that it describes the structure 010-09 removed; the `current_zone()` comment in [`timestamp.cpp`](/src/core/timestamp.cpp) names the standard library instead of "GCC 14+"; KI-001 and [lesson_candidates.md](/docs/tasks/lesson_candidates.md) updated.

## Deviations from the spec (recorded in its History)
- No `file_clock::to_sys` comparison in `filesystem_paths`: MSVC's `file_clock` has only `to_utc` (the standard allows either pair). The lesson uses `clock_cast` and says why it is the portable form.

## Follow-ups
- None new. The throughput of the false-sharing case varies between runs (sometimes faster than the padded ring, because this simple ring reads the other index on every operation); both READMEs explain it, and the numbers are not an acceptance criterion.

All code units were written by agy and reviewed (`cpp-reviewer`; codex for the risky `lock_free_buffer`); no `lead (fallback)` units.
