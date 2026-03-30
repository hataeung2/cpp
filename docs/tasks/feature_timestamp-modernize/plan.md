# Implementation Plan: TimeStamp Modernization (atugcc::core)

## Overview
Migrate `alog::TimeStamp` to `atugcc::core::TimeStamp` using C++20 `<chrono>` (Calendar/TimeZone) and `<format>`. This eliminates platform-specific `localtime` branches.

## Files to Modify/Create
- [NEW] `include/atugcc/core/timestamp.hpp`: Public interface with `enum class Option`.
- [NEW] `src/core/timestamp.cpp`: Implementation using `std::chrono::zoned_time` and `std::format`.
- [MODIFY] `src/core/CMakeLists.txt`: Add `timestamp.cpp` to the `atugcc_core` target.
- [NEW] `tests/core/test_timestamp.cpp`: GoogleTest cases for various options.
- [MODIFY] `tests/CMakeLists.txt`: Register `test_timestamp.cpp`.
- [NEW] `docs/cpp_evolution/chrono_format.md`: Documentation of the evolution from C-style time to C++20 chrono/format.

## C++20/23 Features Applied
- `std::chrono::zoned_time` & `std::chrono::current_zone()`: Modern timezone-aware time handling.
- `std::format`: Type-safe, high-performance string formatting for dates.
- `enum class`: Scoped and strongly-typed enumerations.
- `[[nodiscard]]`: Ensure return values are not ignored.
- `consteval` / `constexpr`: For bitwise operations on `Option` flags.

## Evolutionary Changes
Replacing: `std::chrono::system_clock::to_time_t` + `localtime_r`/`_localtime64_s` + `std::put_time`.
New Pattern: `std::chrono::zoned_time` + `std::format`.
Reference: `/docs/cpp_evolution/chrono_format.md`

## Implementation Steps
1. **Header**: Define `atugcc::core::TimeStamp` in `include/atugcc/core/timestamp.hpp`.
2. **Source**: Implement logic in `src/core/timestamp.cpp`.
3. **CMake**: Update `src/core/CMakeLists.txt`.
4. **Tests**: Create `tests/core/test_timestamp.cpp`.
5. **Evolution Doc**: Write `/docs/cpp_evolution/chrono_format.md`.
