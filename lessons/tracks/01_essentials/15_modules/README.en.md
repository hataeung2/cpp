# Lesson: C++20 modules — interfaces, partitions, implementation units, and `import atugcc.core` (`modules`)

`#include` re-parses a header's text in every source that includes it and leaks its macros and private helpers; a C++20 named module compiles its interface once and exposes only what it marks `export`. This lesson splits its own module `modules.geometry` across three files (a primary interface, a partition, and an implementation unit), uses the library only through `import atugcc.core;` with no library `#include` ([`core.cppm`](/modules/atugcc/core.cppm) and [`error.hpp`](/include/atugcc/core/error.hpp) in the `uses` tab), and prints four steps showing implementation-unit separation, partition re-export, macro isolation, and non-transitive `import`. Background: [modules.en.md](/docs/cpp_evolution/modules.en.md).

## `#include` and named modules
| | `#include` (headers) | Named module (C++20) |
|---|---|---|
| How often parsed | every translation unit re-parses the header and everything it includes | the interface compiles once into a binary module interface (BMI) read by `import` |
| Macros | `#define`s in a header leak into every includer | macros never cross `import`; include the defining header when a macro is needed |
| Include order | macros or declarations from an earlier header can change what a later header means | each module is self-contained; `import` order does not change meaning |
| What can be hidden | a `detail::` namespace is still visible to name lookup in every includer | non-exported declarations (`detail::clampSide`) are not visible outside the module |
| Rebuilds | editing an inline body or helper in a header recompiles every includer | editing an implementation unit (`.cpp`) recompiles only that file and relinks; importers recompile only when the interface (`.cppm`) changes |

## Unit layout and build
- **Primary module interface unit (`geometry.cppm`, `export module modules.geometry;`)**: re-exports the partition with `export import :rect;`, imports `atugcc.core` without `export`, and declares the exported functions `area` and `makeRect` alongside non-exported `detail::clampSide`. Because it `#include`s no headers at all, it has no global module fragment (`module;`).
- **Module partition interface unit (`geometry_rect.cppm`, `export module modules.geometry:rect;`)**: includes `<format>` and `<string>` in its `module;` fragment, exports `Rect` and the inline `describe(const Rect&)`, and is re-exported by `geometry.cppm` through `export import :rect;`. `Rect` and `describe` live together in the partition because a partition cannot `import` its own primary interface (`modules.geometry`, which would form a cycle).
- **Module implementation unit (`geometry.cpp`, `module modules.geometry;` without `export`)**: inherits all declarations and imports of the primary interface and defines `area`, `makeRect`, and `detail::clampSide`. It has a global module fragment (`module;` + `#include <expected>`) for `std::unexpected`: an `import` brings in no unexported `std::` names, and `import atugcc.core;` exports none.
- **Build**: `.cppm` files listed in `sources` of `lesson.toml` go into a CMake `CXX_MODULES` file set automatically ([`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt)), while the first source stays the `.cpp` entry point (`main.cpp`). If you rename a module or delete an `export module` line, CMake re-scans on the next build; scanner errors may appear only in the build log rather than as `file:line:col` editor markers.
- **Every `#include` before every `import`**: within one file, keep every `#include` before every `import` ([`impl.md`](/.agent/rules/impl.md) §2a), because including a standard header after an `import` whose module already included it can clash with the module's declarations.
- **`import std;` and editors**: `import std;` (C++23) is not used yet ([KI-036](/docs/known_issues.md)), so standard headers are included with `#include`. A local editor may underline `import` lines ([KI-037](/docs/known_issues.md)); the build works normally.

## Run
- Web playground: select it in the lesson tree, then Run
- Local: `cmake --build --preset <preset> --target lesson_modules`, then `bin/lessons/lesson_modules`, or `ctest --preset <preset> -R lesson.modules`

## What to look for
- Step 1: `main.cpp` imports `modules.geometry` and calls `makeRect(3.0, 4.0)` and `area(rect)` to get area `12`. Both functions are defined in the implementation unit `geometry.cpp`, not in a header.
- Step 2: `describe(rect)` returns `Rect 3 x 4`. `Rect` and `describe` live in the `:rect` partition, and `main.cpp` gets them from `import modules.geometry;` because the primary interface writes `export import :rect;` (partitions are never imported directly from outside their module).
- Step 3: `geometry.cppm` defines `#define GEOMETRY_UNIT_CM 1`, yet `#ifdef GEOMETRY_UNIT_CM` in `main.cpp` takes the `#else` branch (`GEOMETRY_UNIT_CM is not defined in main.cpp`). Macros do not cross `import`.
- Step 4: the failure from `makeRect(-1.0, 2.0)` is printed with `atugcc::core::to_string` ([04_error_expected](../04_error_expected/README.en.md)). Because `geometry.cppm` writes `import atugcc.core;` without `export`, that import is not transitive: `main.cpp` can receive the returned value through `auto` (the type is *reachable*), but to spell names such as `to_string` or `CoreError` (*visible*), `main.cpp` imports `atugcc.core` itself.

## Exercises
1. Call `modules::geometry::detail::clampSide(5.0)` from `main.cpp`: both compilers reject it. The gist is MSVC `error C2039: 'clampSide': is not a member of 'modules::geometry::detail'` and Clang `declaration of 'clampSide' must be imported from module 'modules.geometry' before it is required`. Because `clampSide` is declared in `geometry.cppm` (the interface) without `export`, it is reachable, but not visible to name lookup outside the module. Undo it afterwards.
2. Edit only `geometry.cpp` (for example change `kMaxSide`) and rebuild: in the build log (the web build output or Ninja lines locally), only `geometry.cpp` is recompiled and the binary is relinked. Next, edit `geometry.cppm` and rebuild: because the interface BMI changed, its importer `main.cpp` and the implementation unit `geometry.cpp` are recompiled too. Undo it afterwards.
3. Remove `import atugcc.core;` from `main.cpp` and build. On Clang (the Linux preset and the web playground), the build fails at `atugcc::core::to_string` / `CoreError` — note that Clang's wording says `"missing '#include'"` although the fix is an `import`. MSVC 19.51 builds it anyway: it lets names of `geometry.cppm`'s non-exported import leak into importers, which the standard does not allow, so try this first part on Clang. Then change `geometry.cppm` to `export import atugcc.core;`: `main.cpp` now builds without its own import on both compilers; the cost is that every importer of `modules.geometry` now sees the core names too. Undo it afterwards.
