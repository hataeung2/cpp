# Implementation Plan: 01_project_restructure

## Files to Create/Modify
- `[NEW]` `include/atugcc/` hierarchy (core, pattern, adapter, libs)
- `[NEW]` `src/` hierarchy (core, pattern, adapters, libs)
- `[MODIFY]` `CMakeLists.txt` (Root)
- `[MODIFY]` `libs/CMakeLists.txt`
- `[MODIFY]` `tests/CMakeLists.txt`
- `[MODIFY]` All `#include` paths in existing source files.

## Actions
1. **Directory restructure**
   - Move `modules/log/` content to `include/atugcc/core/` (.hpp/.h) and `src/core/` (.cpp/.cppm).
   - Move `sample/design_pattern/` content to `include/atugcc/pattern/`.
   - Move `libs/libsample/` content to `include/atugcc/libs/` and `src/libs/`.
2. **CMake Modernization**
   - Update `CMakeLists.txt` `PROJECT_NAME` to `atugcc`.
   - Update `CMAKE_CXX_STANDARD` to `23`.
   - Add `option(ATUGCC_ENABLE_PQXX "Enable PostgreSQL support" OFF)` and make pqxx FetchContent conditional.
   - Separate targets (e.g., `atugcc_core`, `atugcc_libs`, `atugcc_sample`).
3. **Include Paths Update**
   - Update `#include "ring_buffer.h"` to `#include "atugcc/core/ring_buffer.hpp"`, etc.

## C++20/23 Features Applied
- Not primarily a code logic change phase, but enables `cxx_std_23` in CMake.
