# Test record: 070-13 C++20 modules on Windows and Linux (Clang 20, CMake 4)

- Spec: [/docs/specs/070_13_modules_clang_toolchain.md](/docs/specs/070_13_modules_clang_toolchain.md)
- Plan: [plan.md](/docs/tasks/feature_070-13-modules-clang-toolchain/plan.md)
- Branch: `feature/070-13-modules-clang-toolchain`
- Hosts: Windows 11 (MSVC 19.51.36260, VS 2026, CMake 4.3.1-msvc1), WSL2 Ubuntu 24.04 (Clang 20.1.2, libstdc++ 14.2, CMake 4.4.5 from Kitware APT, Ninja 1.11.1)

## Runs

| # | Command | Result |
|---|---|---|
| R0 | baseline before any change: `linux-x64-debug` from an empty build directory, GCC 13.3, scanning off | build 110 s, exit 0 |
| R1 | `linux-x64-debug` from an empty build directory after U1–U5 (Clang 20, scanning on) | configure: `The CXX compiler identification is Clang 20.1.2`; build 120 s, exit 0, no warning (+9 % against R0) |
| R2 | `build.py --preset windows-x64-debug --fresh` after U1–U5 | compile OK, links of 4 executables fail with `LNK1000: Internal error during IncrBuildImage.Pass1`; again on a plain retry, plus `Access violation`. The failing links are the executables that had `.exe`/`.ilk` from the previous build; `--fresh` does not remove them |
| R2b | `out/build/windows-x64-debug` removed, `build.py --preset windows-x64-debug` | exit 0, no warning (155 steps). Cause: stale incremental-link files; added to `config.md` §5 |
| R3 | `build.py --preset <p> --target atugcc_tests --gtest-filter "CoreModule*"` on `linux-x64-debug` and `windows-x64-debug` (after U6 and its review fixes) | `[  PASSED  ] 6 tests.` on both (`CoreModule.{LoggerSnapshot, RingBufferRoundTrip, ExpectedError, TimeStampOptions}`, `CoreModuleMixed.{SameEntities, SameFunctionAcrossTranslationUnits}`) |
| R4 | `build.py --preset linux-x64-playground`, `linux-x64-playground-release` (empty build directories) | exit 0 both, 0 warning/error lines, `CMAKE_CXX_COMPILER=/usr/bin/clang++-20` |
| R5 | `build.py --preset windows-x64-debug --test` | build without warnings; `100% tests passed, 0 tests failed out of 21` |
| R6 | `build.py --preset linux-x64-debug --test` | build without warnings; `100% tests passed out of 21` (incl. `PlaygroundServer`) |
| R7 | `build.py --preset linux-x64-asan --test` (empty build directory) | build without warnings; `100% tests passed out of 21` |
| R8 | `build.py --preset linux-x64-tsan --test` (empty build directory) | build without warnings; `95% tests passed, 1 tests failed out of 21`: `PlaygroundServer` `LongRunTest.test_span_flood_keeps_memory_flat`, `(exitCode, traceLimit)` = `(None, False)`. The test skips itself when `playground_fixture build_info` prints `sanitized`; the fixture checked `__SANITIZE_ADDRESS__`/`__SANITIZE_THREAD__`, which Clang 20 does not define (it answers `__has_feature(address_sanitizer)`/`(thread_sanitizer)` only, checked with `clang++-20 -fsanitize=… -E`). So the TSan fixture ran the 3,000,000-span flood and hit the time limit. Under ASan (R7) the flood is fast enough to pass by chance. The same macros guarded `SpanLifetimeDeathTest`, which therefore ran under both sanitizers → U9 (spec Assumption 19) |
| R9 | after U9: `build.py --preset linux-x64-tsan --test`, `--preset linux-x64-asan --test` | build without warnings; `100% tests passed out of 21` on both |
| R10 | `playground_fixture build_info` per build | `linux-x64-debug`: `plain`; `linux-x64-asan`: `sanitized`; `linux-x64-tsan`: `sanitized` |
| R11 | temporary untracked user preset `linux-ac8-scan-off` (inherits `linux-x64-debug`, `CMAKE_CXX_SCAN_FOR_MODULES=OFF`, own build directory), `cmake --preset linux-ac8-scan-off`; preset and directory removed afterwards | exit 1, `CMake Error at CMakeLists.txt:37 (message): atugcc always builds with C++20 modules: configure through a preset of CMakePresets.json (base sets CMAKE_CXX_SCAN_FOR_MODULES=ON)` |
| R12 | `cmake --install out/build/linux-x64-debug` | exit 0; `out/install/linux-x64-debug/include/atugcc/core.cppm`; `lib/cmake/atugcc/atugccTargets.cmake` has `FILE_SET "CXX_MODULES"`, `FILES "${_IMPORT_PREFIX}/include/atugcc/core.cppm"` and includes `cxx-modules/cxx-modules-atugccTargets.cmake`; `cxx-modules/` holds `cxx-modules-atugccTargets.cmake`, `-Debug.cmake`, `target-atugcc__core-Debug.cmake` |
| R13 | `cmake --install out/build/windows-x64-debug` (CMake 4.3.1-msvc1) | exit 0; `out\install\windows-x64-debug\include\atugcc\core.cppm`; the same `FILES` line and `cxx-modules` include |
| R14 | configure of `linux-x64-release`, `linux-x64-relwithdebinfo` (empty build directories); compiler, version and scanning from every Linux build directory and from `windows-x64-debug` | all 7 Linux presets: `/usr/bin/clang++-20`, 20.1.2, `CMAKE_CXX_SCAN_FOR_MODULES=ON`; `windows-x64-debug`: `cl.exe` 19.51.36260.0, `ON` |
| R15 | `py -3 .agent/scripts/naming_check.py` | first run: `try_lock_for -> tryLockFor: src/core/log_service.cpp:256` (a std member). `try_lock_for` added to the std-member list next to `try_lock_until`; then `0 snake_case function name(s)`; `test_agent_scripts.py` OK |
| R16 | `py -3 tools/lessons.py check`; `py -3 .agent/scripts/lint_docs.py` | `0 error(s), 0 warning(s); 2 track(s), 8 lesson(s), 2 unit(s)`; `0 error(s), 0 warning(s)` |
| R17 | `grep -c '#include "atugcc' tests/modules/test_core_module.cpp`; `git ls-files src/core/alog.cppm modules/sample_module.cppm`; `grep -rn "alog.cppm\|sample_module"` outside `docs/specs`, `docs/tasks/feature_*`, `docs/known_issues.md` | `0`; empty; only the untracked clangd index under `.cache/` (not repository content) |
| R18 | trial before the spec (2026-11-03, recorded in spec §10) | scratch module project, the old `sample_module`/`alog` with Clang 20, full repository with Clang 20 under `-Werror` (3 warnings → Assumption 12), ASan, TSan (`<mutex>` error → Assumption 18), C++23 probes (Assumption 17) |

`SpanLifetimeDeathTest` (R9): with `ATUGCC_SANITIZED_BUILD` defined it is compiled out on `linux-x64-asan` and `linux-x64-tsan` again, as before the compiler change; it still runs on `linux-x64-debug` (R6).

Whether Clang 20's TSan still needs the `setarch -R` launcher (spec Assumption 13) was not separated: the launcher stays, and every TSan run went through it.

## Acceptance criteria

| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | R14 (7 Linux presets Clang 20.1.2, `windows-x64-debug` MSVC 19.51), CMake 4.4.5 (Linux) and 4.3.1-msvc1 (Windows); `cmakeMinimumRequired` 4.0 in `CMakePresets.json`, `cmake_minimum_required(VERSION 4.0)` | Pass |
| AC-2 | R1, R2b, R5, R6 (no warning with warnings as errors) | Pass |
| AC-3 | R17 (0 atugcc includes), R3 (4 `CoreModule` tests on both hosts) | Pass |
| AC-4 | R3 (`CoreModuleMixed`: a `Logger`, `Expected<int>` and `CoreError` made with header names go to `moduleSideAccepts`, defined with module names in the import-only TU; the call links and returns true on Clang and MSVC; `configureLogBuffers` addresses equal) | Pass |
| AC-5 | R5, R6 | Pass |
| AC-6 | R7, R9 (ASan and TSan 21/21 after U9; R8 is the failing run that led to U9) | Pass |
| AC-7 | R4 (both playground presets build every lesson with Clang 20), R6 (`PlaygroundServer` on `linux-x64-debug`) | Pass |
| AC-8 | R17, R11; `CMakeLists.txt` has no `set(CMAKE_CXX_SCAN_FOR_MODULES …)` and no Windows-only module branch (`grep -c "CMAKE_CXX_SCAN_FOR_MODULES" CMakeLists.txt` = 3: the guard's comment, `if` and message) | Pass |
| AC-9 | R12, R13 | Pass |
| AC-10 | R16; D1 review (below) | Pass |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U5 `log_service.cpp` | codex luna (high) | equivalence of `try_lock_for(deadline - now())` with `try_lock_until(deadline)`, flag handling, conversions, comment | a future deadline can end later by the time between `now()` and the call | accepted (ns against the ms deadlines of the two callers); comment and Assumption 18 say so. Re-check: fixed |
| U2 `core.cppm` | codex luna (medium) | export list against the five headers, missing public names, structure, ADL companions | `DbgBuf`, `makeRingBuffer` (public in `ring_buffer.hpp`) missing | review fixes lead (small): both exported (20 names), spec §2.1 amended. Re-check: fixed |
| U1, U3, U4 presets, `CMakeLists.txt`, `main.cpp`, two headers | codex luna (medium) | §2.2, Assumptions 3–5, 9, 12–14, AC-8/9, scope | install path `include/atugcc/modules/atugcc/core.cppm` (doubled by `BASE_DIRS`); `docs/known_issues.md` KI-035 text names the deleted files | `DESTINATION include` → `include/atugcc/core.cppm`; KI text kept (closed record), AC-8 grep excludes `known_issues.md`. Re-check: fixed, no new defect |
| U6 tests | cpp-reviewer | does each test check its AC; can any pass trivially | `CoreModuleMixed.SameEntities` `std::is_same_v` checks compare a name with itself (cannot fail); `TimeStampOptions` rebuilds the expected mask with `operator|`'s own formula; `<string>` missing in the mixed file | review fixes lead (small): cross-TU `moduleSideAccepts(Logger&, const Expected<int>&, CoreError)` (parameter types are part of the symbol on Itanium and MSVC, so distinct entities would not link), literal `0x3u`, includes. Re-check: fixed; spec AC-4 / §4 and plan text stale → updated |
| U8 `runner.py`, U9 sanitizer flag | cpp-reviewer | §2.2 / Assumption 19; every `__SANITIZE_*` replaced; same polarity; plain builds unchanged; `// MACRO:` comments | none. Observation: the flag is set for any non-empty `ATUGCC_SANITIZERS`, so a UBSan-only build would now count as sanitized (no preset does that) | accepted |
| D1 docs | cpp-reviewer | spec §8 rows done; docs vs code; stale GCC / old module names; KI entries | README "Visual Studio 2022/2026" conflicts with CMake 4.0; `modules.md` does not name the scanners; KI-033 body still present tense with the old **Next**. Agreed: the dated GCC 13 measurement table in `lessons/README.md` stays | fixed by the lead (VS 2026 + CMake 4 note, `cl /scanDependencies` / `clang-scan-deps`, KI-033 past tense, Next → 070-14). Re-check: fixed; one more stale sentence ("`format.md` says the same") → "said the same until 070-13" |
