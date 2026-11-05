# C++ Evolution: Index

An index of the pages on the C++ features learned while building `atugcc`, centred on how each moved from the older style (C++11/14/17) to C++20/23. The same material can be run hands-on as playground lessons.

- The pages live in [`docs/cpp_evolution/`](/docs/cpp_evolution/), two per topic: `<topic>.md` (Korean) and `<topic>.en.md` (English). 한국어: [cpp_evolution.md](/docs/cpp_evolution.md).
- Most pages follow the order **Why → legacy → C++20 → C++23 → in atugcc**.
- Overall structure and direction of the project: [project_blueprint.md](/docs/guides/project_blueprint.md) (in Korean). Lesson topics still to come: [lesson_candidates.md](/docs/lesson_candidates.md) (in Korean).

## 1. In the order of the essentials track
Read in lesson order (`lessons/tracks/01_essentials/`), the material goes from syntax → core features (time, files) → threads and logs → modules → tests. For a lesson without a page, its README carries the explanation.

| # | Lesson | Legacy → current | Background page | atugcc code |
|---|---|---|---|---|
| 01 | [`lambda_capture`](/lessons/tracks/01_essentials/01_lambda_capture/README.en.md) | function objects → lambdas, capture modes | — | unit `lambda_capture` |
| 02 | [`format_text`](/lessons/tracks/01_essentials/02_format_text/README.en.md) | `printf`/`iostream` → `std::format` (C++20), `std::print` (C++23) | [format.en.md](/docs/cpp_evolution/format.en.md) | `std::format_string` in `Logger::log` |
| 03 | [`const_correctness`](/lessons/tracks/01_essentials/03_const_correctness/README.en.md) | `const` on a return type vs a `const` member function, deducing this (C++23) | [const_return_type.en.md](/docs/cpp_evolution/const_return_type.en.md) | — |
| 04 | [`error_expected`](/lessons/tracks/01_essentials/04_error_expected/README.en.md) | exceptions and silent failures → `std::optional` → `std::expected` (C++23) | [error_expected.en.md](/docs/cpp_evolution/error_expected.en.md) | `core/error.hpp` |
| 05 | [`source_location`](/lessons/tracks/01_essentials/05_source_location/README.en.md) | `__FILE__`/`__LINE__` macros → `std::source_location`, `std::osyncstream` | [source_location.en.md](/docs/cpp_evolution/source_location.en.md) | `FormatWithLocation` (`logger.hpp`) |
| 06 | [`concepts`](/lessons/tracks/01_essentials/06_concepts/README.en.md) | SFINAE (`enable_if`) → concepts, `requires` | [concepts.en.md](/docs/cpp_evolution/concepts.en.md) | `observer.hpp`, `ring_buffer.hpp` |
| 07 | [`ranges_views`](/lessons/tracks/01_essentials/07_ranges_views/README.en.md) | raw loops and iterators → `std::ranges`, view pipelines | — | — |
| 08 | [`variant_visit`](/lessons/tracks/01_essentials/08_variant_visit/README.en.md) | virtual functions → `std::variant` + `std::visit` | — | `state.hpp` |
| 09 | [`chrono_time`](/lessons/tracks/01_essentials/09_chrono_time/README.en.md) | `time_t`/`struct tm` → `std::chrono` calendar and time zones + `std::format` | [chrono_format.en.md](/docs/cpp_evolution/chrono_format.en.md) | `TimeStamp` |
| 10 | [`filesystem_paths`](/lessons/tracks/01_essentials/10_filesystem_paths/README.en.md) | strings and platform APIs → `std::filesystem`, `clock_cast` (C++20) | [filesystem.en.md](/docs/cpp_evolution/filesystem.en.md) | `MemoryDump::ensurePrepared` |
| 11 | [`thread_and_log`](/lessons/tracks/01_essentials/11_thread_and_log/README.en.md) | `std::thread` → `std::jthread` + `std::stop_token` | — | unit `jthread_worker` |
| 12 | [`log_recovery`](/lessons/tracks/01_essentials/12_log_recovery/README.en.md) | logs lost on an unclean exit → memory-mapped buffers and recovery | [lock_free_logging.en.md](/docs/cpp_evolution/lock_free_logging.en.md) §memory-mapped | `configureLogBuffers`, `recoverLogMaps` |
| 13 | [`lock_free_buffer`](/lessons/tracks/01_essentials/13_lock_free_buffer/README.en.md) | a Logger with one lock → per-thread SPSC buffers + one consumer | [lock_free_logging.en.md](/docs/cpp_evolution/lock_free_logging.en.md), old design [modern_ring_buffer_architecture.en.md](/docs/cpp_evolution/modern_ring_buffer_architecture.en.md) | `detail::ThreadLogBuffer` |
| 14 | [`span_timing`](/lessons/tracks/01_essentials/14_span_timing/README.en.md) | timing by hand → Tracer spans and aggregates | — | `ScopedSpan` (`visualizer.hpp`) |
| 15 | [`modules`](/lessons/tracks/01_essentials/15_modules/README.en.md) | `#include` → C++20 named modules, `import std` (C++23) | [modules.en.md](/docs/cpp_evolution/modules.en.md) | `modules/atugcc/core.cppm` |
| 16 | [`testing`](/lessons/tracks/01_essentials/16_testing/README.en.md) | GoogleTest unit tests, step scenarios, CTest, test reports | end of [source_location.en.md](/docs/cpp_evolution/source_location.en.md) (test macros) | `tests/`, `atugcc::test::Scenario` |

## 2. Pages without a lesson yet
| Page | Legacy → current | atugcc code |
|---|---|---|
| [designated_initializers.en.md](/docs/cpp_evolution/designated_initializers.en.md) | positional aggregate initialization and builders → designated initializers (C++20) | `DiagramBudget` (`visualizer.hpp`). Lesson candidate: 021-02 Builder |

## 3. Records of old designs
| Page | Content |
|---|---|
| [modern_ring_buffer_architecture.en.md](/docs/cpp_evolution/modern_ring_buffer_architecture.en.md) | The Logger before 010-09: a per-thread `RingBuffer` of fixed 128-byte blocks and a global `boost::lockfree::spsc_queue`. Current design: [lock_free_logging.en.md](/docs/cpp_evolution/lock_free_logging.en.md) |

## 4. Adding or changing a page
- A task that replaces an older pattern with C++20/23 writes or updates a page in `docs/cpp_evolution/` ([impl.md](/.agent/rules/impl.md) §6 Reference docs). It writes both languages and adds a row to this index and to [`cpp_evolution.md`](/docs/cpp_evolution.md).
- The two versions have the same heading structure and the same number of code blocks. The docs gate (`lint_docs.py`) warns when a page has no pair or the shapes differ.
- The Korean version links to Korean lesson READMEs and Korean pages; the English version links to `README.en.md` and `.en.md`.
