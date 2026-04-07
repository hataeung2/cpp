# Plan: ErrorCode / std::expected Module

Task: Implement `atugcc::core` unified error-handling using `std::expected`.
Spec: docs/specs/09_error_expected.md
Branch: feature/error-expected

## Summary
- Introduce a focused, unified core error layer with C++23 `std::expected`.
- Complete integration by adding `makeRingBuffer()` factory and converting `MemoryDump::dump()` to value-based error returns.

## Files to create / modify
- [MODIFY] include/atugcc/core/error.hpp
- [MODIFY] include/atugcc/core/memory_dump.hpp
- [MODIFY] include/atugcc/core/ring_buffer.hpp
- [MODIFY] src/core/ring_buffer.cpp
- [NEW] tests/core/test_error_expected.cpp
- [MODIFY] tests/CMakeLists.txt
- [MODIFY] main.cpp
- [NEW] docs/cpp_evolution/error_expected.md
- [MODIFY] docs/tasks/feature_error-expected/testrecord.md
- [MODIFY] docs/tasks/feature_error-expected/walkthrough.md
- [MODIFY] docs/tasks/agent_todo.md

## C++ Features / Style
- Target: C++23 (use std::expected, std::format where useful)
- Use [[nodiscard]] on Expected/Result aliases and to_string
- Use concepts/strong typing where applicable; follow .agent/rules/impl.md

## Implementation Steps
1. Confirm `error.hpp` baseline API exists.
2. Add `makeRingBuffer(std::size_t)` declaration/definition with `CoreError::InvalidArgument` validation.
3. Convert `MemoryDump::dump(...)` to return `atugcc::core::Result` and map I/O failures to `CoreError::FileIOFailure`.
4. Add GTest coverage for `to_string`, monadic `Expected` flow, ring buffer factory validation, and memory dump result path.
5. Build and run tests via CMake Tools.
6. Update task artifacts and checklist.

## Risks & Questions
- Do we want a richer error payload (e.g., string message) in CoreError, or keep it an enum-only for now? Enum keeps ABI small; we can add a lightweight message wrapper later.
- Ensure public headers do NOT expose third-party headers (impl rule).

## Next Action
- Implementation completed and validated; prepare commit.


---
Plan updated by agent on branch feature/error-expected
