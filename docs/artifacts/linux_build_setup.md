# Linux/WSL2 Build Environment Setup

This document outlines the required tools and libraries to build and test the `atugcc` project on a Linux (Ubuntu/Debian-based) or WSL2 environment.

## Prerequisites

The Linux presets build with **Clang 20** and the **libstdc++ 14** standard library, with **CMake 4.0 or later** and **Ninja**. C++20 modules are always on, so CMake needs Clang's dependency scanner (`clang-scan-deps-20`). Spec: [070-13](/docs/specs/070_13_modules_clang_toolchain.md). Tried on Ubuntu 24.04 (WSL2): Clang 20.1.2, libstdc++ 14.2, CMake 4.4.5, Ninja 1.11.1.

### 1. Install the compiler and the standard library
From the Ubuntu 24.04 archive (universe):
```bash
sudo apt-get update
sudo apt-get install -y clang-20 clang-tools-20 libstdc++-14-dev ninja-build gdb
```
- `clang-tools-20` provides `clang-scan-deps-20`, which CMake uses to scan modules.
- `libstdc++-14-dev` adds the GCC 14 standard library headers; Clang picks the newest one it finds (`clang++-20 -v` prints `Selected GCC installation: .../14`). `g++` itself is not needed.
- The presets call the compiler `clang++-20`. On a distribution that names it differently, set `CMAKE_CXX_COMPILER` in your own untracked `CMakeUserPresets.json`.

### 2. Install CMake 4 (Kitware APT repository)
Ubuntu 24.04 ships CMake 3.28; the presets need 4.0 or later:
```bash
sudo apt-get install -y ca-certificates gpg wget
wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | gpg --dearmor - | sudo tee /usr/share/keyrings/kitware-archive-keyring.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ noble main' | sudo tee /etc/apt/sources.list.d/kitware.list >/dev/null
sudo apt-get update
sudo apt-get install -y kitware-archive-keyring cmake
```

### 3. Install project dependencies
Boost (header-only libraries used in `atugcc_headers`) comes from the system package manager unless a vcpkg root is set (see the root README):
```bash
sudo apt-get install -y libboost-dev
```

### 4. (Optional) PostgreSQL dependency
If you use the PQXX target (`ATUGCC_ENABLE_PQXX=ON`), you may also need development headers for PostgreSQL:
```bash
sudo apt-get install -y libpq-dev
```

### 5. Check the versions
```bash
cmake --version            # 4.0 or later
clang++-20 --version       # 20.x
clang-scan-deps-20 --version
ninja --version            # 1.11 or later
```

## Building the Project

Configure, build and test through the presets of `CMakePresets.json` (one command: `python3 .agent/scripts/build.py --preset linux-x64-debug --test`).

### Configure
```bash
cmake --preset linux-x64-debug
```
*(Build directory: `out/build/linux-x64-debug`)*

### Build
```bash
cmake --build --preset linux-x64-debug
```

### Run Tests
```bash
ctest --preset linux-x64-debug
# Or the test executable directly:
# ./out/build/linux-x64-debug/bin/atugcc_tests
```

After a compiler change (for example from an older GCC build directory), configure with `--fresh` or remove the build directory: module interfaces (BMIs) and object files of another compiler cannot be reused.
