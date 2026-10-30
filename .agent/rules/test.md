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
  - `tests/backend/`: backend/interface tests ([impl.md](/.agent/rules/impl.md) §5)
- **File naming**: `test_<module_name>.cpp` (e.g., `test_ring_buffer.cpp`). New files are picked up by [`tests/CMakeLists.txt`](/tests/CMakeLists.txt).
- **Execution**: always through a preset ([config.md](/.agent/rules/config.md)). All tests build into one executable, `atugcc_tests`, registered in CTest as `AllTests`.
  ```text
  py -3 .agent/scripts/build.py --preset <preset> --target atugcc_tests --gtest-filter "<Suite>.*"   # one unit's check
  py -3 .agent/scripts/build.py --preset <preset> --test                                             # full suite (task gate)
  ```
  `build.py` sets up MSVC on Windows and runs Linux presets in WSL ([config.md](/.agent/rules/config.md) §1).
- **Guidelines**:
  - Test both happy path and edge cases (nullptr, overflow, concurrency, empty containers).
  - Use `EXPECT_*` for non-fatal assertions, `ASSERT_*` only when continuation is meaningless.
  - Test thread safety where applicable (`std::latch`/`std::barrier` to line up threads in setup).
  - A test that mirrors the implementation or cannot fail does not count as evidence.

## 3. Build Verification
- Build with a preset before testing. Never configure ad hoc (`cmake -S . -B build`): add a preset instead ([config.md](/.agent/rules/config.md)).
- **Zero Warnings Policy**: enforced by the build: every preset sets `ATUGCC_WARNINGS_AS_ERRORS=ON` on top of `/W4` (MSVC) and `-Wall -Wextra` (GCC) from [`CMakeLists.txt`](/CMakeLists.txt). A warning fails the build.

## 4. Compiler and Sanitizer Matrix
Every code change passes the full suite on:
- **MSVC** (Visual Studio 2026): `windows-x64-debug`.
- **GCC** (latest stable): `linux-x64-debug` (WSL or a Linux host).

Risky units ([delegation.md](/.agent/rules/delegation.md) §3) add sanitizer runs:
- lifetime, casts, memory layout, signal handlers: `linux-x64-asan` (ASan + UBSan);
- atomics, locks, threads: `linux-x64-tsan`.

If a configuration is not reachable in the session, say so in `testrecord.md` and register the gap in [`docs/known_issues.md`](/docs/known_issues.md).

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
- **Docs gate**: `py -3 .agent/scripts/lint_docs.py` exits 0 (links, machine paths, todo grammar, spec approval state, KI ids, lesson manifests). Links and machine paths are checked in top-level files and under `docs/`, `.agent/`, `.claude/` and `lessons/`. Changes to `.agent/scripts/` or `.claude/hooks/` also pass `py -3 .agent/scripts/test_agent_scripts.py`.
- **Naming gate**: `py -3 .agent/scripts/naming_check.py` exits 0 (no snake_case function names, impl.md §1).
- **On success**: only then move the task state in `agent_todo.md`.
