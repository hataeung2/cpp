# Test Record: feature/error-expected-dump-impl

Date: 2026-04-08

Summary of test runs performed while implementing this feature branch.

1) Initial build and tests (Linux)
- Command: `cmake -S . -B out/linux/x64/debug -DCMAKE_BUILD_TYPE=Debug && cmake --build out/linux/x64/debug -j`
- Result: Build succeeded.
- Tests: `ctest` run in build dir — All tests passed (1/1 at the time).

2) Added POSIX integration test `tests/core/test_posix_dump.cpp`
- Purpose: exercise `MemoryDump::prepareDumpFile` + `DbgBuf::dumpToFd` without triggering a crash.
- Result: built and ran; test passed.

3) Parser validation
- Created `scripts/parse_dump.py` and produced a local sample `test_sample_dump.bin` with three blocks.
- Ran parser: output correctly showed header and three blocks payloads (`hello`, `world`, `foo`).

4) Windows validation (performed by developer)
- Developer reported Windows `dumpToHandle` implementation compiled and was manually tested locally on Windows.

Artifacts
- `tests/core/test_posix_dump.cpp`
- `scripts/parse_dump.py`
- `docs/tasks/feature_error-expected/*` (this folder)

# Test Record — feature/error-expected

Date: 2026-04-07
Branch: feature/error-expected

## Build
Command: Build_CMakeTools (default debug preset)
Result: First run failed due to access control in `memory_dump.hpp` (`dumpToFile` protected). Updated visibility and rebuilt.

Command: Build_CMakeTools (retry)
Result: Build succeeded.
Built targets: `atugcc_core`, `atugcc_sample`, `atugcc_tests`.

## Tests
Command: RunCtest_CMakeTools
Result: All tests passed (1/1). No failures.

Logs:
```
100% tests passed, 0 tests failed out of 1
```

Test additions validated:
- `tests/core/test_error_expected.cpp`
	- `to_string(CoreError)` mapping
	- `Expected<int>` monadic flow (`and_then`, `transform`, `or_else`)
	- `makeRingBuffer()` invalid/success path
	- `MemoryDump::dump()` `Result` success path
