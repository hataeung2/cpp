---
trigger: model_decision
description: When composing the code
---

# Implementation & Development Rules (C++ Library/Framework — atugcc)

## Core
Every agent follows this section: the lead (`lint_docs.py --boot` prints it) and every sub-agent (`subagent_run.py` attaches it).
- C++23 (`cxx_std_23`), C++20 minimum. Code builds without warnings on MSVC and Clang 20.
- C++ names: types `PascalCase`; functions and methods `camelCase` (`addEntry`; exceptions: `naming_check.py`); members `snake_case_`; constants `kPascalCase`; namespaces `lowercase`. Python scripts use `snake_case`.
- Use: `#pragma once`; `static_cast` / `std::bit_cast`; `concept` / `requires`; `std::format`; `std::expected` / `std::optional` for expected failures.
- Never: `using namespace std;` at file or namespace scope; C casts or `void*`; SFINAE where a concept fits; `fmt` in new code; an empty `catch`; `#ifdef _WIN32` scattered through sources; a third-party header in `include/`; an external library outside a backend interface; a macro without a `// MACRO:` reason; dead or commented-out code.
- Paths: project-relative only in committed files, never `C:/`, `Z:/` or a user home. No secrets or connection strings in code; do not open `.env` or credential files.
- Build and test only through `py -3 .agent/scripts/build.py --preset <p>` (Linux `python3`), never an ad-hoc `cmake`.
- Change only what the task names. Unclear: ask, do not guess.
- Read more when you touch: C++ modules → §2a; a backend → §5; `docs/cpp_evolution/` → §6; tests → [test.md](/.agent/rules/test.md) §2; lessons → [lessons/README.md](/lessons/README.md).

## 1. Code Quality & Style
* **Strong typing**: no unconstrained templates; prefer `concept`/`requires` constraints over `enable_if`.
* **Macros**: use `constexpr`, `inline`, `concept` or templates where they can replace a macro.
* **Modularity & DRY**: Keep each file focused on a single responsibility. Extract reusable logic when code exceeds ~150 lines. Prevent duplication.
* **Naming**: Core. Function names: user decision 2026-10-28, applies to every public and internal function, concept requirements included (`onEvent`). Check: `py -3 .agent/scripts/naming_check.py` exits 0.
* **No unused code**: remove unreferenced variables and includes after implementation.
* **Modern C++ Attributes**: Use `[[nodiscard]]`, `[[maybe_unused]]`, `[[deprecated]]` where appropriate.

## 2. Cross-Platform Compatibility
* **Primary Targets**: Windows (MSVC — Visual Studio 2026) + Linux (Clang 20 with libstdc++ 14, spec 070-13).
* **Platform branches**: use platform abstraction layers or CMake-based conditional compilation.
* **`std::format`**: the build system provides `fmt` as a fallback only if the compiler's `<format>` is incomplete.

## 2a. C++20 Modules (spec 070-13)
* **Always on**: every preset scans for modules (`CMAKE_CXX_SCAN_FOR_MODULES=ON`); `CMakeLists.txt` refuses a configure with scanning off. Any source may `import`.
* **Names and files**: module `atugcc.<area>` (dotted), partitions for sub-parts (`atugcc.core:log`); public interface units in `modules/atugcc/<area>.cppm`, added to the area's library target as `FILE_SET CXX_MODULES` (`BASE_DIRS modules`).
* **Wrapper first**: a module's global module fragment includes the area's public headers and exports their public names with `using` declarations ([`core.cppm`](/modules/atugcc/core.cppm)). The headers stay the source of truth; a new public name in a header is added to the module's export list in the same change. Free operators and functions found only by ADL are exported by name.
* **Includes before imports**: in one source file every `#include` comes before every `import`.
* **No macros through modules**: a module cannot export a macro; code that needs one includes the header that defines it.
* **Lesson modules** (spec 070-14): a lesson may list `.cppm` interface or partition units in its `sources` (the entry point, the first source, stays a `.cpp`); its module names are `<lesson id>` or start with `<lesson id>.` (`modules.geometry`); [`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt) puts the `.cppm` files into the lesson target's `CXX_MODULES` file set. Units (`lessons/units/`) cannot hold modules (KI-039).
* Header units (`import "x.hpp";`) and `import std;` are not used (CMake does not support header units; `import std` is KI-036).

## 3. Agent Behavior & Scoping
* **Scope**: no refactoring outside the task scope without the user's permission (Core).
* **Verify Before Completing**: Always self-verify syntax and build correctness before reporting completion (ensure no missing includes, proper namespace usage, etc.).
* **Ask before guessing**: when requirements are ambiguous, an architecture decision is unclear or a breaking change may occur, STOP and ASK the user.

## 4. Error Handling & Stability
* **Errors**: a caught exception is logged, rethrown, or converted to a `std::expected`/`std::optional` return value (Core forbids the empty `catch`).
* **Exceptions**: reserved for truly exceptional situations; expected failure paths return `std::expected<T,E>` or `std::optional<T>`.

## 5. Dependencies & Pluggable Backends
* **All external dependencies** (pqxx, database drivers, network libs, GLFW, graphics APIs, etc.) MUST be wrapped behind an interface, a **pluggable backend**, so they can be swapped.
* **Pattern**: Define a concept or pure abstract interface in `include/atugcc/` (`include/atugcc/backend/` for Phase 3), and the concrete backend in `src/backends/` (engine backends: `src/engine/backends/`).
* **Naming**: the word *adapter* is reserved for the GoF Adapter pattern (task 022-02). Do not name a backend layer, namespace or directory "adapter" (user decision 2026-10-29).

## 6. C++ Standard Version Documentation
* When introducing a C++20/23 feature that replaces a pre-C++20 pattern:
  * **Main code**: Uses the latest standard (C++20/23).
  * **Reference docs**: Where noted in the spec, provide a `docs/cpp_evolution/` file showing pre-C++17 → C++20 → C++23 progression for educational purposes.
  * Format: `docs/cpp_evolution/<feature_name>.md` (Korean) and `docs/cpp_evolution/<feature_name>.en.md` (English) with side-by-side comparisons, plus a row in both index pages `docs/cpp_evolution.md` and `docs/cpp_evolution.en.md` (spec 090-07). The two files have the same headings and code blocks; each links to lessons and pages in its own language (`README.md` / `README.en.md`). `lint_docs.py` warns about a missing or differently shaped pair.

## 7. Build & Configuration
* **CMake Targets Only**: Use `target_compile_options`, `target_include_directories`, `target_link_libraries`. Do NOT set global `CMAKE_CXX_FLAGS` directly.
* **Configuration values**: database connection strings, file paths and API keys come from CMake options, environment variables or config files.
* **Links**: documentation links and internal project references are relative from the project root (Core).
