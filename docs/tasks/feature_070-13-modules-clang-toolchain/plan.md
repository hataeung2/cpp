# Plan: 070-13 C++20 modules on Windows and Linux (Clang 20, CMake 4)

- Spec: [/docs/specs/070_13_modules_clang_toolchain.md](/docs/specs/070_13_modules_clang_toolchain.md) (approved 2026-11-03)
- Branch: `feature/070-13-modules-clang-toolchain` (from `main` at `b5c0782`)

## Design

### Files
- [MODIFY] `CMakePresets.json` — `cmakeMinimumRequired` 4.0; `base`: `CMAKE_CXX_SCAN_FOR_MODULES` `ON`; `linux-base`: `CMAKE_CXX_COMPILER` `clang++-20`, description with the packages (§2.2)
- [NEW] `modules/atugcc/core.cppm` — module `atugcc.core`, the export list of §2.1
- [MODIFY] `CMakeLists.txt` — `cmake_minimum_required(VERSION 4.0)`; scan guard; `FILE_SET CXX_MODULES` with `BASE_DIRS modules` on every host; one `install(TARGETS …)` with the file set; `install(EXPORT … CXX_MODULES_DIRECTORY cxx-modules)`; TSan launcher comment (§2.2, Assumptions 4, 5, 13, 14)
- [DELETE] `src/core/alog.cppm`, `modules/sample_module.cppm`; [MODIFY] `main.cpp` — the `_WIN32` import and the commented `sample_module::name()` call (Assumption 9)
- [MODIFY] `include/atugcc/pattern/factory.hpp` (`ACarFactory`), `include/atugcc/pattern/iterator_concept.hpp` (`Impl`) — `virtual ~X() = default;` (Assumption 12)
- [MODIFY] `src/core/log_service.cpp` — `tryLockService(deadline)`: `try_lock_for(deadline - steady_clock::now())` with the reason in a comment (Assumption 18)
- [NEW] `tests/modules/test_core_module.cpp`, `tests/modules/test_core_module_mixed.cpp`; [MODIFY] `tests/CMakeLists.txt` (Assumption 10, AC-3, AC-4)
- [MODIFY] `web/server/runner.py` — `compiler_version()` fallback `clang++-20`
- Docs: every row of spec §8; [NEW] `docs/cpp_evolution/modules.md`

### C++20/23 features
- Named modules, global module fragment, exported `using` declarations (C++20). Evolution page: `docs/cpp_evolution/modules.md` (new).

### Scan guard (Assumption 5)
After `project()`:
```cmake
if(NOT CMAKE_CXX_SCAN_FOR_MODULES)
  message(FATAL_ERROR "atugcc always builds with C++20 modules: configure through a preset of CMakePresets.json (base sets CMAKE_CXX_SCAN_FOR_MODULES=ON)")
endif()
```
It reads the value; the presets stay the only place that sets it.

### Tests (Assumption 10)
- `test_core_module.cpp`: includes only `<gtest/gtest.h>` and standard headers, then `import atugcc.core;`. Suite `CoreModule`:
  - `LoggerSnapshot`: a `Logger` with `Config{.bufferCapacity = …}` defaults (no live output, no file, crash dump off if the config has such a flag), `log`/`info` one line with `Delivery::Sync` or `flush()`, `snapshot()` contains the text.
  - `RingBufferRoundTrip`: `RingBuffer<>` `write("abc", Level::Info)`, `read()` returns the text and level.
  - `ExpectedError`: a local function returning `core::Expected<int>` → `std::unexpected(CoreError::InvalidArgument)`; `to_string(CoreError::InvalidArgument)` non-empty.
  - `TimeStampOptions`: `TimeStamp::Option` values combined with `operator|` give the bitwise OR of their underlying values; `TimeStamp::str(flags)` non-empty.
- `test_core_module_mixed.cpp`: `<gtest/gtest.h>`, `<expected>`, `<string>` and the core headers, then `import atugcc.core;`. Suite `CoreModuleMixed`: `SameEntities` makes a `Logger`, an `Expected<int>` and a `CoreError` with header names and passes them to `atugcc_test::moduleSideAccepts`, defined in `test_core_module.cpp` with module names (parameter types are part of the symbol: distinct entities would not link), then checks the line it logged; `SameFunctionAcrossTranslationUnits` compares `&configureLogBuffers` with `coreModuleConfigureAddress()` from the import-only TU. (Revised after the cpp-reviewer review: the first draft's `std::is_same_v` checks compared a name with itself and could not fail.)
- Exact Logger API (constructor, config fields, log call) is read from `logger.hpp` by the author.

## Units

Code units first, then tests, then docs. U1–U5 cannot build apart: the first configure needs the presets (U1), the module file (U2) and the new `CMakeLists.txt` (U3); `atugcc_sample` fails under Clang `-Werror` without U4, and the TSan build fails without U5. Their per-unit checks are greps; the build check runs once on all five.

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `CMakePresets.json` | min 4.0, scan ON, `clang++-20` (AC-1) | `grep -c` for `"major": 4`, `"CMAKE_CXX_SCAN_FOR_MODULES": "ON"`, `clang++-20` = 1 each; `json.load` ok | no | lead (small) | codex luna (with U3, U4): none | 131k / 1k (shared) | done |
| U2 | `modules/atugcc/core.cppm` | module `atugcc.core` (§2.1) | 20 `using ::atugcc::core::` lines (18 + 2 after review); build U1–U5 | yes (ODR, templates) | lead (from spec §2.1) | codex luna: `DbgBuf`, `makeRingBuffer` missing → review fixes lead (small), spec §2.1 amended | 100k / 1k | done |
| U3 | `CMakeLists.txt`, delete `src/core/alog.cppm` + `modules/sample_module.cppm`, `main.cpp` | §2.2 (AC-8, AC-9) | `grep -c "CMAKE_CXX_SCAN_FOR_MODULES"` = 3 (comment, `if`, message: all the guard); no `alog.cppm`/`sample_module` outside docs; build U1–U5 | yes (platform branches, several files) | lead (small) | codex luna: install path doubled (`include/atugcc/modules/atugcc/`) → `DESTINATION include`; KI-035 text names old files → accepted (closed record), AC-8 grep excludes `known_issues.md` | (shared with U1) | done |
| U4 | `factory.hpp`, `iterator_concept.hpp` | virtual destructors (Assumption 12, AC-2) | `grep -c "virtual ~ACarFactory\|virtual ~Impl()"` = 1 each; build | yes (public header ABI) | lead (small) | codex luna (with U1, U3): none | (shared with U1) | done |
| U5 | `src/core/log_service.cpp` | `try_lock_for` (Assumption 18, AC-6) | `grep -c try_lock_until` = 0 in code (1 in the comment); TSan build | yes (locks) | lead (small) | codex luna high: a future deadline can end later by the time between `now()` and the call → accepted (ns against ms deadlines), comment and Assumption 18 say so | 99k / 3k | done (`naming_check.py`: `try_lock_for` added to the std-member list) |
| B1 | — | build U1–U5 | `linux-x64-debug` (fresh): exit 0, no warning, 120 s (GCC baseline 110 s); `windows-x64-debug`: LNK1000 / access violation twice on incremental links against the old `.ilk` files, exit 0 after removing `out/build/windows-x64-debug` | — | lead | — | — | done |
| U6 | `tests/modules/test_core_module.cpp`, `test_core_module_mixed.cpp`, `tests/CMakeLists.txt` | AC-3, AC-4 (U7 merged: the cross-TU check needs both files) | `grep -c '#include "atugcc' tests/modules/test_core_module.cpp` = 0; `--gtest-filter "CoreModule*"`: 6 passed on both hosts | no | agy flash | cpp-reviewer: `is_same_v` checks tautological, `TimeStampOptions` copies `operator|`, `<string>` missing → review fixes lead (small), re-check: fixed, spec AC-4 / §4 and plan text stale → updated | 103k / 15k (agy) | done |
| U7 | (merged into U6) | | | | | | | — |
| U8 | `web/server/runner.py` | `clang++-20` fallback | `grep -c clang++-20` = 2; `PlaygroundServer` ctest (R6) | no | lead (small) | cpp-reviewer (with U9): none | — | done |
| U9 | `tests/CMakeLists.txt`, `tests/playground/playground_fixture.cpp`, `tests/pattern/test_span_timing.cpp` | `ATUGCC_SANITIZED_BUILD` from `ATUGCC_SANITIZERS` (Assumption 19, AC-6; found by the first full TSan run: `PlaygroundServer` failed, `test_span_flood_keeps_memory_flat` exitCode None after the time limit) | no `__SANITIZE_` left in sources; `playground_fixture build_info` = `sanitized` on asan/tsan, `plain` on debug; full asan/tsan suites | no | lead (small) | cpp-reviewer (with U8): none (observation: any non-empty `ATUGCC_SANITIZERS` counts, no UBSan-only preset) | — | done |
| D1 | docs of spec §8, `modules.md`, KI-033/035/024/036–038 | AC-10 | `lint_docs.py`, `lessons.py check` exit 0 | no | lead | cpp-reviewer: VS 2022 note, scanner names, KI-033 wording → fixed, re-checked | — | done |
