# Plan — Logger Facade

## Target Task
- Logger 통합 퍼사드 (RingBuffer + dlog + MemoryDump)
- Spec: /docs/specs/10_logger_facade.md

## File Change Plan
- [NEW] /include/atugcc/core/logger.hpp
- [NEW] /src/core/logger.cpp
- [NEW] /tests/core/test_logger.cpp
- [MODIFY] /include/atugcc/core/alog.h
- [MODIFY] /src/core/alog.cppm
- [MODIFY] /CMakeLists.txt
- [MODIFY] /tests/CMakeLists.txt
- [MODIFY] /docs/tasks/agent_todo.md
- [NEW] /docs/tasks/feature_logger-facade/testrecord.md
- [NEW] /docs/tasks/feature_logger-facade/walkthrough.md

## C++20/23 Features
- C++20 `std::source_location` for call-site metadata
- C++20 `std::format` / `std::format_string` for type-safe formatting
- C++20 designated initializer style support in `Logger::Config`
- C++23 `[[nodiscard]]` and value-based `Result` (`std::expected<void, CoreError>`)

## Legacy to Modern Evolution Note
- This task replaces macro-oriented/manual composition with a single facade API.
- Existing evolution docs already cover related modules; this change is integration-focused.
