# DumpHandleTest — Report

- Date: 2026-04-08
- Test binary: `out/windows/x64/debug/bin/atugcc_tests.exe`
- Test filter: `DumpHandleTest.*`

## Summary

Result: PASSED (1 test executed). Build and test run completed locally using the Visual Studio developer environment.

## Command

Initialize MSVC env then run tests:

```
cmd /c "call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe" --build "Z:/cpp/out/windows/x64/debug" --target atugcc_tests -- -j 4"
& "Z:\cpp\out\windows\x64\debug\bin\atugcc_tests.exe" --gtest_filter=DumpHandleTest.*
```

## Raw Output

Note: captured from the local run after initializing the Visual Studio dev environment.

```
Note: Google Test filter = DumpHandleTest.*
[==========] Running 1 test from 1 test suite.
[----------] Global test environment set-up.
[----------] 1 test from DumpHandleTest
[ RUN      ] DumpHandleTest.WriteToHandle
program crashed!
[       OK ] DumpHandleTest.WriteToHandle (10 ms)
[----------] 1 test from DumpHandleTest (10 ms total)

[----------] Global test environment tear-down
[==========] 1 test from 1 test suite ran. (12 ms total)
```

## Notes

- The test calls `alog::MemoryDump::prepareDumpFileWin(path)`, writes a sample log via `DbgBuf::log(...)`, then calls `DbgBuf::dumpToHandle(getDumpHandle())` and verifies the prepared file exists and is non-empty.
- `crashHdler(nullptr)` is also invoked by the test to exercise the SEH crash path; it writes a minimal structured header and a small CONTEXT block (best-effort) followed by non-consuming per-block `WriteFile` of ring buffer contents. The presence of `program crashed!` in the output indicates the handler's safe_write executed.
- After the change `DbgBuf::dumpToHandle` delegates to `RingBuffer::rawDumpToHandle`, which performs a non-consuming, per-block `WriteFile` of the ring buffer contents. The test passed, indicating the new non-consuming path is exercising the prepared handle write.
- Both dump files are created under the repository `log/` directory: `log/test_dump_handle.bin` and `log/test_dump_handle_crash.bin`.
