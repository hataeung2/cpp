# Walkthrough: 01_project_restructure

## Overview
This task modernized the C++ project layout to fit the `atugcc` framework library standard and updated the CMake build system to target C++23 and use modern `target_*` commands.

## Changes Made
1. **Directory Restructuring**:
   - Headers moved to `include/atugcc/` (`core/`, `pattern/`, `adapter/`, `libs/`).
   - Implementations moved to `src/` (`core/`, `pattern/`, `adapters/`, `libs/`).
   - Legacy folders (`modules`, `includes`, `libs/libsample`) removed.
2. **CMake Modernization**:
   - **Root `CMakeLists.txt`**: Added `atugcc_headers` INTERFACE target to enforce C++23 across the project. Added `atugcc_core` and `atugcc_sample`. Wrapped `pqxx` fetching in an `option()` toggle (`ATUGCC_ENABLE_PQXX`).
   - **`libs/CMakeLists.txt`**: Simplified target linking for `shape` and `sound` libraries using `atugcc_headers`.
   - **`tests/CMakeLists.txt`**: Updated to fetch the latest GoogleTest and link against `atugcc_core`.
3. **Include Paths Update**:
   - Automatically replaced all cross-file includes in `.h`, `.hpp`, `.cpp`, and `.cppm` files to use the new `atugcc/...` paths (e.g., `#include "atugcc/core/ring_buffer.h"`).

## Testing & Validation
The restructuring rules and Python-based include rewrites were successfully executed. However, the automated CMake build test could not complete because the `cmake` executable is not in the current environment's PATH.

**Manual Verification Required**:
Please open your **Visual Studio 2026 Developer PowerShell** and run:
```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Debug
cd build && ctest --output-on-failure -C Debug
```

## Reference
- Detailed test logs: [testrecord.md](./testrecord.md)
