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
    ├── artifacts/        # Project architecture and design blueprint (project_blueprint.md)
    ├── learning/         # C++ evolution and implementation details (cpp_evolution.md)
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

## Environment-Specific Configuration

`CMakePresets.json` 파일에는 현재 PC 환경에 맞춘 절대 경로(vcpkg, Ninja 컴파일러 등)가 포함되어 있습니다. 다른 PC에서 작업하시거나 환경이 변경되는 경우, `CMakePresets.json` 안의 `base` preset 부분에서 아래 항목들을 본인의 환경에 맞게 수정해 주셔야 합니다.

1. **`toolchainFile`**: `vcpkg.cmake` 파일의 경로를 지정합니다.
   * 기본값: `"C:/vcpkg/scripts/buildsystems/vcpkg.cmake"`
   * *Tip: 시스템 환경 변수 `VCPKG_ROOT`가 설정되어 있다면 `"$env{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"` 와 같이 변경하여 경로 의존성을 없앨 수 있습니다.*
   * Note: 
      - Windows에서는 환경변수를 사용하는 경우 인식이 안되는 경우가 있음. 그냥 절대경로 사용하여 해결.
      - Linux(Ubuntu)에서는 ~/.bashrc에 아래의 내용 추가저장 하고, source ~/.bashrc 해서 적용.
         export VCPKG_ROOT=$HOME/vcpkg
         export PATH=$VCPKG_ROOT:$PATH
2. **`CMAKE_MAKE_PROGRAM`**: `ninja.exe` 빌드 프로그램의 경로를 지정합니다.
   * 기본값: `"C:/Program Files (x86)/Microsoft Visual Studio/18/BuildTools/.../Ninja/ninja.exe"`
   * *Tip: 이 경로는 VS Code의 CMake 확장 기능을 사용하시거나 Visual Studio Developer Command Prompt 환경에서 빌드하시는 경우, 시스템 환경에서 자동으로 인식되므로 해당 줄 자체를 삭제하셔도 무방합니다.*

## Phase Roadmaps

Check `docs/tasks/agent_todo.md` for current progress. The development is organized into several phases:
- **Phase 0:** Project Base Setup & Modernization (Completed)
- **Phase 1:** Core Module Conversion (`atugcc::core`)
- **Phase 2:** Design Pattern Modernization (`atugcc::pattern`)
- **Phase 3:** Adapter Layer (`atugcc::adapter`)
- **Phase 4:** Samples & Tests Modernization
- **Phase 5:** C++ Evolution Documentation

