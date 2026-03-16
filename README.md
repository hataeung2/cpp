# atugcc

A C++20/23 framework library intended to explore and utilize modern C++ features.
This project has been restructured to separate public APIs from internal implementations and fully supports modern CMake (Presets, `FetchContent`, target-based configurations).

## Project Structure

```text
atugcc/
├── CMakeLists.txt        # Root CMake configuration (Modern CMake 3.26+, target-based)
├── CMakePresets.json     # CMake configuration presets for MSVC / GCC / Clang
├── main.cpp              # Sample application entry point
├── include/
│   └── atugcc/           # Public API headers representing the logical structure
│       ├── core/         # Core utilities (RingBuffer, TimeStamp, logging, etc.)
│       ├── pattern/      # Modern design pattern templates
│       ├── adapter/      # Interfaces for external dependencies
│       └── libs/         # Framework-provided library headers
├── src/                  # Internal implementation files (.cpp, .cppm)
│   ├── core/             # Implementations for core utilities
│   ├── pattern/          # Implementations for design patterns
│   └── adapters/         # Implementations for adapters (e.g., PostgreSQL adapter)
├── libs/                 # Independent internal or external sub-libraries (e.g., shape, sound)
├── sample/               # Various implementation examples and legacy samples
├── tests/                # Unit tests using GoogleTest
└── docs/                 # Documentation directory
    ├── specs/            # Technical specifications and design documents
    └── tasks/            # Task tracking and assignment logs (agent_todo.md)
```

## Features

- **Modern C++ Standard:** Targets C++23 as the baseline and leverages modern C++20/23 features (e.g., Concepts, Ranges, `std::expected`, `std::variant/visit`).
- **Modern CMake:** Employs target-centric modern CMake structure, supporting C++20 modules (`FILE_SET CXX_MODULES`).
- **Platform Agnostic:** Built to support both MSVC (VS 2026) and GCC/Clang with unified `CMakePresets.json`.
- **FetchContent:** Seamlessly integrates external dependencies (like `pqxx` for PostgreSQL or `gtest`) using CMake's `FetchContent`.
- **Test-Driven:** Test setups included using GoogleTest (`tests/`).

## How to Build

We recommend using CMake Presets.

### Using Visual Studio
Open the folder in Visual Studio 2022/2026, and it should automatically read `CMakePresets.json`. Simply select a preset (e.g., `windows-x64-debug`) and build.

### Using CLI
```bash
# Configuration
cmake --preset windows-x64-debug

# Build
cmake --build --preset windows-x64-debug

# Run Tests
ctest --preset windows-x64-debug
```

## Phase Roadmaps

Check `docs/tasks/agent_todo.md` for current progress. The development is organized into several phases:
- **Phase 0:** Project Base Setup & Modernization (Completed)
- **Phase 1:** Core Module Conversion (`atugcc::core`)
- **Phase 2:** Design Pattern Modernization (`atugcc::pattern`)
- **Phase 3:** Adapter Layer (`atugcc::adapter`)
- **Phase 4:** Samples & Tests Modernization
- **Phase 5:** C++ Evolution Documentation

