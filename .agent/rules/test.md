---
trigger: model_decision
description: When testing the code or verifying changes
---

# Agent Rule: Testing Guide (atugcc — C++ Library/Framework)

## 1. When to Test
You MUST run the tests below before reporting a task as complete and before writing `walkthrough.md`.

## 2. C++ Testing (GoogleTest)
- **Framework**: GoogleTest (GTest) + Google Mock (GMock).
- **Location**: `/tests/`, organized by module:
  - `tests/core/`: core module tests (ring_buffer, timestamp, memory_dump, logger, error)
  - `tests/pattern/`: design pattern and visualizer tests
  - `tests/adapter/`: adapter/interface tests
- **File naming**: `test_<module_name>.cpp` (e.g., `test_ring_buffer.cpp`). New files are picked up by [`tests/CMakeLists.txt`](/tests/CMakeLists.txt).
- **Execution**: always through a preset ([config.md](/.agent/rules/config.md)). All tests build into one executable, `atugcc_tests`, registered in CTest as `AllTests`.
  ```text
  cmake --build --preset <preset> --target atugcc_tests        # narrow build
  out/build/<preset>/bin/atugcc_tests --gtest_filter=<Suite>.*    # narrow run (one unit's check)
  ctest --test-dir out/build/<preset> --output-on-failure          # full suite (task gate)
  ```
  On Windows, run the build inside the MSVC environment ([config.md](/.agent/rules/config.md) §2).
- **Guidelines**:
  - Test both happy path and edge cases (nullptr, overflow, concurrency, empty containers).
  - Use `EXPECT_*` for non-fatal assertions, `ASSERT_*` only when continuation is meaningless.
  - Test thread safety where applicable (`std::latch`/`std::barrier` to line up threads in setup).
  - A test that mirrors the implementation or cannot fail does not count as evidence.

## 3. Build Verification
- Build with a preset before testing. Never configure ad hoc (`cmake -S . -B build`): add a preset instead ([config.md](/.agent/rules/config.md)).
- **Zero Warnings Policy**: the build completes with 0 warnings at the project's levels (`/W4` on MSVC, `-Wall -Wextra` on GCC, set in [`CMakeLists.txt`](/CMakeLists.txt)). Any warning is fixed before the task is complete.

## 4. Compiler Compatibility Check
Verify every code change on both target compilers:
- **MSVC** (Visual Studio 2026): `windows-x64-debug`.
- **GCC** (latest stable): `linux-x64-debug` (WSL or a Linux host).
- If one compiler is not reachable in the session, say so in `testrecord.md` and register the gap in [`docs/known_issues.md`](/docs/known_issues.md).

## 5. Acceptance Criteria Evidence
- Expected results come from the spec's **Acceptance Criteria** table, not from the tests written alongside the code.
- `testrecord.md` holds one row per `AC-n`: criterion, evidence (test name, command, or manual check), result.
- An AC with no evidence blocks completion.

## 6. Post-Test Actions
- **`testrecord.md`** (`/docs/tasks/feature_NNN-SS-<slug>/testrecord.md`), for each test run:
  - Test name / description
  - Expected result
  - Actual result
  - Status (Pass / Fail)
  - Error output and retry attempts if it failed
  - The AC evidence table (§5)
- **`walkthrough.md`**: the final outcome only, referring to `testrecord.md` for details.
- **On failure**: diagnose, fix, re-run, and log the retry in `testrecord.md`. Do not complete the task until tests pass.
- **Non-blocking findings**: register them in [`docs/known_issues.md`](/docs/known_issues.md) and refer to them by `KI-` id.
- **On success**: only then move the task state in `agent_todo.md`.
