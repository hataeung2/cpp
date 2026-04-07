# Plan: ErrorCode / std::expected Module

Task: Implement `atugcc::core` unified error-handling using `std::expected`.
Spec: docs/specs/09_error_expected.md
Branch: feature/error-expected

## Summary
- Introduce a small, focused error module that standardizes error values across core components using C++23 `std::expected`.
- Apply to two quick wins: add `include/atugcc/core/error.hpp` and update `MemoryDump::dump()` + add `makeRingBuffer()` factory returning Expected<RingBuffer>.

## Files to create / modify
- [NEW] include/atugcc/core/error.hpp
- [MODIFY] include/atugcc/core/memory_dump.hpp (change dump signature to Result)
- [MODIFY] src/core/memory_dump.cpp (adjust implementation, propagate errors)
- [MODIFY] include/atugcc/core/ring_buffer.hpp (add forward declaration for factory)
- [MODIFY] src/core/ring_buffer.cpp (add makeRingBuffer factory function)
- [NEW] tests/error_expected_tests.cpp (GTest) — exercise Expected chaining and failure paths
- [MODIFY] CMakeLists.txt / tests/CMakeLists.txt — add new test target and include directories if needed
- [NEW] docs/tasks/feature_error-expected/walkthrough.md (created after implementation)
- [NEW] docs/tasks/feature_error-expected/testrecord.md (test logs)

## C++ Features / Style
- Target: C++23 (use std::expected, std::format where useful)
- Use [[nodiscard]] on Expected/Result aliases and to_string
- Use concepts/strong typing where applicable; follow .agent/rules/impl.md

## Implementation Steps
1. Add header `include/atugcc/core/error.hpp` with CoreError enum, to_string, Expected<T>, Result typedefs.
2. Update MemoryDump API and implementation to return Result, convert file I/O failures into CoreError::FileIOFailure.
3. Add makeRingBuffer() factory that validates capacity and returns Expected<RingBuffer> with CoreError::InvalidArgument on bad input.
4. Add unit tests covering success and failure paths and monadic chaining using .and_then/.or_else.
5. Update CMake to compile tests and link GTest.
6. Build and run tests; record results in testrecord.md.

## Risks & Questions
- Do we want a richer error payload (e.g., string message) in CoreError, or keep it an enum-only for now? Enum keeps ABI small; we can add a lightweight message wrapper later.
- Ensure public headers do NOT expose third-party headers (impl rule).

## Next Action
- Implement step 1: create `include/atugcc/core/error.hpp` and run a build to ensure header compiles.


---
Plan created by agent (Astra) on branch feature/error-expected
