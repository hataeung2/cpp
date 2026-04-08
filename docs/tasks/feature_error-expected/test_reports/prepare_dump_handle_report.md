# prepareDumpFileWin — Change & Test Report

- Date: 2026-04-08
- Change: MemoryDump::prepareDumpFileWin now opens pre-created dump HANDLE with
  `SECURITY_ATTRIBUTES` (non-inheritable) and `FILE_FLAG_WRITE_THROUGH`.

## Summary

- Status: Code updated in `include/atugcc/core/memory_dump.hpp`.
- Test run: Executed locally in this environment after initializing the Visual Studio developer command environment. Build and `DumpHandleTest` executed successfully.

Build snapshot:

```
[vcvarsall.bat] Environment initialized for: 'x64'
[1/21] Scanning Z:\cpp\src\core\alog.cppm for CXX dependencies
[10/17] Building CXX object CMakeFiles\atugcc_core.dir\src\core\alog.cppm.obj
[17/17] Linking CXX executable bin\atugcc_tests.exe
```

## What I changed

- In the `MemoryDump` constructor, replaced `CreateFileA` path with `CreateFileW` and
  use `SECURITY_ATTRIBUTES` with `bInheritHandle = FALSE` and `FILE_FLAG_WRITE_THROUGH`.
- In `prepareDumpFileWin`, use `CreateFileW` with the same `SECURITY_ATTRIBUTES` and
  `FILE_FLAG_WRITE_THROUGH` to create the handle with conservative write semantics.

## How to validate locally

Run the following commands on a Windows dev machine with CMake installed from the repository root:

```powershell
cmake -S . -B out/windows/x64/debug -DCMAKE_BUILD_TYPE=Debug
cmake --build out/windows/x64/debug --target atugcc_tests -- -j 4
& "out\windows\x64\debug\bin\atugcc_tests.exe" --gtest_filter=DumpHandleTest.*
```

Then inspect `docs/tasks/feature_error-expected/test_reports/dump_handle_report.md` for the dump test output from the prior run, and run the test again to capture updated output.

## Notes

- Build and `DumpHandleTest` were then executed successfully in this environment; see `dump_handle_report.md` for test output and verification details.
- I extended `tests/core/test_dump_handle.cpp` to also invoke `crashHdler(nullptr)` (best-effort) and validate the presence of the `DUMP-V1` header in the prepared dump file; that test executed as part of the run.
