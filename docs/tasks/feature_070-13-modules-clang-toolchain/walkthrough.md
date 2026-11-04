# Walkthrough: 070-13 C++20 modules on Windows and Linux (Clang 20, CMake 4)

- Spec: [/docs/specs/070_13_modules_clang_toolchain.md](/docs/specs/070_13_modules_clang_toolchain.md) (approved 2026-11-03)
- Evidence: [testrecord.md](/docs/tasks/feature_070-13-modules-clang-toolchain/testrecord.md) (every AC passes), plan and unit table: [plan.md](/docs/tasks/feature_070-13-modules-clang-toolchain/plan.md)

## Result
- **Linux toolchain**: every `linux-x64-*` preset builds with Clang 20 (`clang++-20`, Ubuntu packages `clang-20 clang-tools-20`) and libstdc++ 14 (`libstdc++-14-dev`); GCC left the Linux presets (one compiler per host, user decision). Setup: [`linux_build_setup.md`](/docs/artifacts/linux_build_setup.md).
- **CMake 4.0 or later on both hosts**: `cmakeMinimumRequired` and `cmake_minimum_required` say 4.0; Linux takes CMake from the Kitware APT repository, Windows from VS 2026.
- **Modules always on**: the `base` preset sets `CMAKE_CXX_SCAN_FOR_MODULES=ON`, and `CMakeLists.txt` stops a configure that turns it off. There is no option to turn modules off (user decision).
- **`import atugcc.core;`**: [`modules/atugcc/core.cppm`](/modules/atugcc/core.cppm) wraps the five public core headers and exports their 20 public names; it belongs to `atugcc_core`, so every target that links the library can import it, and header and module users share one build. The install tree has `include/atugcc/core.cppm` and the `CXX_MODULES` file set on both hosts. The old `alog.cppm` and `sample_module.cppm` are gone.
- **Tests**: [`tests/modules/`](/tests/modules/test_core_module.cpp) — one file uses the library only through `import`; the other includes `logger.hpp` and imports the module, and passes header-named objects to a function defined with module names in the first file, which links only if both are the same entities.
- **Rules**: [`impl.md`](/.agent/rules/impl.md) §2a (module names, files, wrapper pattern, includes before imports, no macros through modules), test matrix and config rules for Clang; evolution page [`modules.md`](/docs/cpp_evolution/modules.md).
- **Build time**: `linux-x64-debug` full build 110 s (GCC 13, scanning off) → 120 s (Clang 20, scanning on).

## Changes found during the task (spec History has each)
- Three Clang warnings in `factory.hpp` / `iterator_concept.hpp` (deleting through a base without a virtual destructor) were real defects: fixed with virtual destructors (Assumption 12, found by the trial).
- libstdc++ 14.2's `<mutex>` does not compile `try_lock_until` with a `steady_clock` deadline under ThreadSanitizer; `LogService::tryLockService(deadline)` uses `try_lock_for` (Assumption 18). `naming_check.py` learned `try_lock_for` as a std member.
- Clang does not define `__SANITIZE_ADDRESS__` / `__SANITIZE_THREAD__`, so the playground fixture reported a TSan build as plain and a long test timed out; the tests now get `ATUGCC_SANITIZED_BUILD` from CMake (Assumption 19, found by the first full TSan run).
- The Windows build failed with `LNK1000` on incremental links against `.ilk` files of the pre-module build; a clean build directory fixed it (`config.md` §5 row).
- Reviews: `DbgBuf` and `makeRingBuffer` added to the export list; install destination fixed (`include/atugcc/core.cppm`); the first mixed test's `std::is_same_v` checks could not fail and became the cross-TU call.

## Units and authors
U6 (tests) was written by agy `flash`; U1–U5, U8, U9 and the docs by the lead (`lead (small)`, U2 from the code in spec §2.1). Risky units U2–U5 were reviewed by codex `luna`, ordinary units and docs by `cpp-reviewer`. Review fixes were applied by the lead as `review fixes lead (small)` and re-checked once by the same reviewer. No `lead (fallback)` unit.

## Follow-ups
- 070-14: essentials modules lesson (`.cppm` lesson sources) and the `std::print` step of `format_text` (KI-033).
- 070-11, 070-12: revise the draft specs against the Clang 20 toolchain (KI-033 list) before their approval.
- KI-033: range formatting and the pipe form of `ranges::to` wait for libstdc++ 15.
- KI-036 `import std`; KI-037 editor support for modules; KI-038 consumer-project test of the installed module.
