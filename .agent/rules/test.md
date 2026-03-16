---
trigger: model_decision
description: When testing the code or verifying changes
---

# Agent Rule: Testing Guide (atugcc — C++ Library/Framework)

## 1. When to Test
You MUST run appropriate tests before reporting a task as complete and creating the `walkthrough.md` artifact.

## 2. C++ Testing (GoogleTest)
- **Framework**: GoogleTest (GTest) + Google Mock (GMock)
- **Location**: Write tests in `/tests/` directory, organized by module:
  - `tests/core/` — core module tests (ring_buffer, timestamp, memory_dump)
  - `tests/pattern/` — design pattern tests
  - `tests/adapter/` — adapter/interface tests  
- **File Naming**: `test_<module_name>.cpp` (e.g., `test_ring_buffer.cpp`)
- **Execution**:
  // turbo
  ```powershell
  # Windows (MSVC 2026)
  cmake --build build --config Debug --target tests
  cd build && ctest --output-on-failure -C Debug
  ```
  ```bash
  # Linux (GCC)
  cmake --build build --config Debug --target tests
  cd build && ctest --output-on-failure -C Debug
  ```
- **Guidelines**:
  - Test both happy path and edge cases (nullptr, overflow, concurrency, empty containers).
  - Use `EXPECT_*` for non-fatal assertions, `ASSERT_*` only when continuation is meaningless.
  - Test thread safety where applicable (use `std::latch`/`std::barrier` for synchronization in test setup).

## 3. Build Verification (CMake)
Before testing, ALWAYS verify the build succeeds:
// turbo
```powershell
# Configure (first time or after CMakeLists.txt changes)
cmake -S . -B build -G "Visual Studio 17 2022" -A x64

# Build
cmake --build build --config Debug
```
- **Zero Warnings Policy**: Build must complete with 0 warnings at `/W3` (MSVC) or `-Wall` (GCC). Any warnings must be resolved before marking the task complete.

## 4. Compiler Compatibility Check
When implementing new features, verify compilation on both target compilers:
- **MSVC** (Visual Studio 2026): Primary development platform.
- **GCC** (latest stable): Ensure no MSVC-specific extensions are used unintentionally.
- If cross-compilation is not immediately testable, document any known portability concerns in the task walkthrough.

## 5. Post-Test Actions
- **Detailed Execution Log (`testrecord.md`)**: Document test execution in `/docs/tasks/feature_<task-name>/testrecord.md`. For each test:
  - Test Name / Description
  - Expected Result
  - Actual Result
  - Status (Pass / Fail)
  - Error logs or retry attempts if failed
- **Summarize Results (`walkthrough.md`)**: In `/docs/tasks/feature_<task-name>/walkthrough.md`, include final testing outcome and reference `testrecord.md`.
- **On Failure**: Diagnose and fix, re-run tests, log retry process. Do NOT proceed to completion until tests pass.
- **On Success**: Only when all tests pass should you update `agent_todo.md`.