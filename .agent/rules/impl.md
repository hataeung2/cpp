---
trigger: model_decision
description: When composing the code
---

# Implementation & Development Rules (C++ Library/Framework — atugcc)

These rules must be strictly followed by the AI Agent during the "Planning & Execution" phase of any task.

## 1. Code Quality & Style
* **C++ Standard**: Target **C++23** (`cxx_std_23`), with **C++20** as the minimum compatibility baseline.
* **Strong Typing**: 
  * Avoid `void*`, raw C-style casts, and unconstrained templates.
  * Use `static_cast`, `dynamic_cast`, `std::bit_cast` over C-style casts.
  * Prefer `concept`/`requires` constraints over SFINAE (`enable_if`).
* **`using namespace std;` is FORBIDDEN** at file/namespace scope. Use explicit `std::` or scoped `using` inside function bodies only.
* **Header Guards**: Use `#pragma once`. Do NOT use legacy `#ifndef __NAME__` guards (double-underscore identifiers are reserved).
* **Macro Minimization**: Avoid preprocessor macros where `constexpr`, `inline`, `concept`, or template solutions exist. Document any remaining macros with `// MACRO:` justification.
* **Modularity & DRY**: Keep each file focused on a single responsibility. Extract reusable logic when code exceeds ~150 lines. Prevent duplication.
* **Descriptive Naming**:
  * Classes/Structs: `PascalCase` (e.g., `RingBuffer`)
  * Functions/Methods: `camelCase` (e.g., `addEntry`)
  * Member Variables: `snake_case_` with trailing underscore (e.g., `ring_size_`)
  * Constants/Constexpr: `kPascalCase` (e.g., `kDefaultBufferSize`)
  * Namespaces: `lowercase` (e.g., `atugcc::core`)
* **No Unused Code**: Remove unreferenced variables, includes, and commented-out dead code. Clean up after implementation.
* **Modern C++ Attributes**: Use `[[nodiscard]]`, `[[maybe_unused]]`, `[[deprecated]]` where appropriate.

## 2. Cross-Platform Compatibility
* **Primary Targets**: Windows (MSVC — Visual Studio 2026) + Linux (GCC latest stable).
* **Minimize `#ifdef` Branching**: Use platform abstraction layers or CMake-based conditional compilation instead of scattering `#ifdef _WIN32` throughout source files.
* **`std::format`**: Use `std::format` (C++20 standard). Do NOT depend on `fmt` library for new code. The build system should provide `fmt` as a fallback only if compiler's `<format>` is incomplete.

## 3. Agent Behavior & Scoping
* **Strict Scope Containment**: Only modify files and logic directly related to the current task. Do not perform arbitrary refactoring outside the task scope without explicit user permission.
* **Verify Before Completing**: Always self-verify syntax and build correctness before reporting completion (ensure no missing includes, proper namespace usage, etc.).
* **Ask Before Guessing**: If requirements are ambiguous, architecture decisions are unclear, or breaking changes may occur, STOP and ASK the user for clarification.

## 4. Error Handling & Stability
* **Never Swallow Errors**: Empty `catch(...) {}` blocks are forbidden. Caught exceptions must be meaningfully logged, rethrown, or converted to `std::expected`/`std::optional` return values.
* **Prefer Value-Based Error Handling**: Use `std::expected<T,E>` (C++23) or `std::optional<T>` over throwing exceptions for expected failure paths. Reserve exceptions for truly exceptional situations.

## 5. Dependency & Adapter Pattern
* **All external dependencies** (pqxx, database drivers, network libs, etc.) MUST be wrapped behind an **adapter/interface** so they can be swapped.
* **Pattern**: Define a pure abstract interface in `include/atugcc/`, provide a concrete adapter implementation in `src/adapters/`.
* **Never** expose third-party headers in public `include/` headers.

## 6. C++ Standard Version Documentation
* When introducing a C++20/23 feature that replaces a pre-C++20 pattern:
  * **Main code**: Uses the latest standard (C++20/23).
  * **Reference docs**: Where noted in the spec, provide a `docs/cpp_evolution/` file showing pre-C++17 → C++20 → C++23 progression for educational purposes.
  * Format: `docs/cpp_evolution/<feature_name>.md` with side-by-side comparisons.

## 7. Build & Configuration
* **CMake Targets Only**: Use `target_compile_options`, `target_include_directories`, `target_link_libraries`. Do NOT set global `CMAKE_CXX_FLAGS` directly.
* **No Hardcoded Paths**: Database connection strings, file paths, API keys in source code are forbidden. Use CMake options, environment variables, or config files.
* **Relative Paths ONLY**: All documentation links and internal project references must be relative from the project root. NEVER use absolute paths like `C:/` or `Z:/`.
