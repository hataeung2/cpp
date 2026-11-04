# C++ Evolution: Modules

## Why
`#include` pastes a header's text into every source that includes it. Each source re-parses the same standard and library headers, every macro and private helper of a header leaks into the includer, and the order of includes can change meaning. Precompiled headers save time but not the leaks. C++20 named modules compile an interface once into a binary module interface (BMI), and `import` brings in only what the module exports: no macros, no private helpers, independent of import order. atugcc builds with modules always on (spec [070-13](/docs/specs/070_13_modules_clang_toolchain.md)); `import atugcc.core;` is the module form of the core headers.

Lesson: none yet (task 070-14).

## C++98/17 (Legacy): headers
```cpp
// widget.hpp
#pragma once                       // or an include guard
#include <string>
#define WIDGET_MAX 16              // leaks into every includer
namespace lib {
namespace detail { inline int helper() { return 1; } }   // visible to every includer
inline std::string name() { return "widget"; }
}

// user.cpp
#include "widget.hpp"              // re-parsed in every source; <string> too
int n = lib::detail::helper() + WIDGET_MAX;   // nothing stops this
```
- Compile time grows with the number of sources times the size of the headers they include.
- Everything in a header is part of its interface, whether meant or not.

## C++20: named modules
```cpp
// widget.cppm (module interface unit)
module;                            // global module fragment: only preprocessor directives
#include <string>
export module lib.widget;          // the module's name
namespace lib {
namespace detail { int helper() { return 1; } }   // not exported: invisible to importers
export std::string name() { return "widget"; }
}

// user.cpp
import lib.widget;
std::string s = lib::name();       // ok
// lib::detail::helper();          // error: not exported
```
- The build system scans every source for `import` / `export module` (P1689) and builds interfaces before their importers. CMake does this with `FILE_SET CXX_MODULES` and `CMAKE_CXX_SCAN_FOR_MODULES` (Ninja generator); the scanner is `cl /scanDependencies` on MSVC and `clang-scan-deps` on Clang (package `clang-tools-20` on Ubuntu).
- BMIs are compiler- and flag-specific (MSVC `.ifc`, Clang `.pcm`). They are not installed or shared: a consumer builds its own from the installed `.cppm`.
- **Partitions** split one module: `export module lib.widget:text;` in one file, `export import :text;` in the primary interface.
- **Implementation units** (`module lib.widget;` without `export`) keep definitions out of the interface, so editing them does not rebuild importers.
- Macros never cross `import`. Code that needs a macro includes the header that defines it.
- Header units (`import "widget.hpp";`) are standard too, but CMake does not support them; atugcc does not use them.

## C++23: `import std`
```cpp
import std;                        // the whole standard library, as one module (P2465)
```
MSVC has it; libstdc++ gets a `std` module with GCC 15, and CMake still keeps `import std` experimental. atugcc does not use it yet: [KI-036](/docs/known_issues.md).

## C++20 (Current, atugcc)
[`modules/atugcc/core.cppm`](/modules/atugcc/core.cppm) is a **wrapper module**: its global module fragment includes the public core headers, and the module exports their public names with `using` declarations.
```cpp
module;
#include "atugcc/core/logger.hpp"   // ... and the other public core headers
export module atugcc.core;
export namespace atugcc::core {
using ::atugcc::core::Logger;
using ::atugcc::core::operator|;   // ADL-only operators are exported by name
// ...
}
```
- The headers stay the source of truth, so header users and module users share one build. Declarations in the global module fragment belong to the global module, so a source that includes `logger.hpp` **and** imports `atugcc.core` sees one `Logger`, not two ([`test_core_module_mixed.cpp`](/tests/modules/test_core_module_mixed.cpp)).
- In such a source, every `#include` comes before every `import` (MSVC and Clang have both failed on a standard header included after an import whose module had already included it).
- [`test_core_module.cpp`](/tests/modules/test_core_module.cpp) uses the library only through `import atugcc.core;`.
- Rules for new modules (names `atugcc.<area>`, files `modules/atugcc/<area>.cppm`, a new public header name goes into the export list in the same change): [`impl.md`](/.agent/rules/impl.md) §2a.
- Toolchains: MSVC (VS 2026) on Windows, Clang 20 with libstdc++ 14 on Linux, CMake 4.0 or later, Ninja.
