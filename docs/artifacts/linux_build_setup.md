# Linux/WSL2 Build Environment Setup

This document outlines the required tools and libraries to build and test the `atugcc` project on a Linux (Ubuntu/Debian-based) or WSL2 environment.

## Prerequisites

To build the project natively on Linux, you need a C++ compiler supporting C++23 features, a build system generator like CMake, and a build tool like Ninja. We also need Boost for `lockfree` components.

### 1. Install Build Tools and Compiler
Install `cmake`, `ninja-build`, and the GNU compiler collection (`g++`):
```bash
sudo apt update
sudo apt install -y cmake ninja-build g++ gdb libboost-dev libfmt-dev
```

### 2. Install Project Dependencies
The project relies on Boost (specifically header-only libraries used in `atugcc_headers`), which should be installed via the system package manager on Linux:
```bash
sudo apt install -y libboost-dev
```

### 3. (Optional) Install PostgreSQL dependency
If you use the PQXX target (`ATUGCC_ENABLE_PQXX=ON`), you may also need development headers for PostgreSQL:
```bash
sudo apt install -y libpq-dev
```

## Building the Project

The existing `CMakePresets.json` file provides templates to easily configure and build the project.

### Configure
```bash
cmake --preset linux-x64-debug
```
*(This sets the build directory to `out/linux/x64/debug` and enables standard Debug flags)*

### Build
```bash
cmake --build --preset linux-x64-debug
# Alternatively, using Ninja directly:
# ninja -C out/linux/x64/debug
```

### Run Tests
```bash
ctest --test-dir out/linux/x64/debug --output-on-failure
# Or manually running the test executable:
# ./out/linux/x64/debug/tests/atugcc_tests
```
