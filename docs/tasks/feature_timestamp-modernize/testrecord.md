# Test Record: TimeStamp Modernization

## Test Environment
- **OS**: Linux (WSL2 / Ubuntu 24.04)
- **Compiler**: GCC 13.3.0
- **Build Type**: Debug
- **Date**: 2026-03-30

## Test Results (GoogleTest)
Filtered tests for `TimeStampTest.*`:

```
[==========] Running 5 tests from 1 test suite.
[----------] Global test environment set-up.
[----------] 5 tests from TimeStampTest
[ RUN      ] TimeStampTest.FormatWithFmt
[       OK ] TimeStampTest.FormatWithFmt (6 ms)
[ RUN      ] TimeStampTest.FormatNone
[       OK ] TimeStampTest.FormatNone (0 ms)
[ RUN      ] TimeStampTest.TimePointOverload
[       OK ] TimeStampTest.TimePointOverload (0 ms)
[ RUN      ] TimeStampTest.NoInstantiation
[       OK ] TimeStampTest.NoInstantiation (0 ms)
[ RUN      ] TimeStampTest.BitwiseOperators
[       OK ] TimeStampTest.BitwiseOperators (0 ms)
[----------] 5 tests from TimeStampTest (7 ms total)

[----------] Global test environment tear-down
[==========] 5 tests from 1 test suite ran. (7 ms total)
[  PASSED  ] 5 tests.
```

## Verification Details
- **FormatWithFmt**: Verified string matches `YYYY-MM-DD HH:MM:SS.mmm ` pattern.
- **FormatNone**: Verified string matches `YYYYMMDDHHMMSSmmm` pattern.
- **TimePointOverload**: Verified that the component handles specific `time_point` inputs correctly across different formats.
- **NoInstantiation**: Confirmed `TimeStamp` is a static-only utility class (non-instantiable).
- **BitwiseOperators**: Confirmed enum class bitwise OR support.

## Issue Notes
- Initial `std::format` output included too much nanosecond precision when using `zoned_time::get_local_time()`. Fixed by using `std::chrono::floor<std::chrono::seconds>(local)` before formatting and manually appending milliseconds.
