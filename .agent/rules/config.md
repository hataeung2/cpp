---
trigger: model_decision
description: When configuring, building, testing or packaging the project
---

# Agent Rule: Configure, Build, Test, Package (atugcc)

`CMakePresets.json` is the only source of configure and build settings. Never configure ad hoc (`cmake -S . -B build`): a missing configuration becomes a preset. A `.claude` hook refuses ad-hoc configure commands; it judges what would run (the program position, also inside `bash -c`, `cmd /c`, substitutions and text fed to a shell), not text that only mentions it; a command it cannot split is checked against the old pattern.

## 1. The one command
```text
py -3 .agent/scripts/build.py [--preset auto|<name>] [--target <t>] [--test] [--label <L>] [--gtest-filter <f>] [--report [DIR]] [--fresh] [--dry-run]
```
(Linux host: `python3`.) [`build.py`](/.agent/scripts/build.py) does the mechanical part:
- `auto` picks `<host>-x64-debug`; user presets from the untracked `CMakeUserPresets.json` are accepted too (name them `windows-…` / `linux-…`).
- **Windows presets** run inside the MSVC developer environment: `VsDevCmd.bat` from `VSDEVCMD`, else found with `vswhere`.
- **Linux presets on a Windows host** run in WSL (`ATUGCC_WSL_DISTRO`, else the default distribution).
- Configure runs when needed: no cache, an interrupted configure, `--fresh`, or a build directory created at another location (a copied checkout: the directory is removed first, because FetchContent sub-builds keep their own caches).
- GoogleTest comes from FetchContent in [`cmake/atugcc_googletest.cmake`](/cmake/atugcc_googletest.cmake), included by `tests/` and by `lessons/` when a lesson has `gtest = true` (spec 070-15). Every preset that builds tests or lessons, the playground presets included, downloads it into its build directory's `_deps` on the first configure, so that configure needs the network.
- `--gtest-filter <f>` runs `ctest --preset <p> -R ^AllTests$ --verbose` with `GTEST_FILTER=<f>`, so the filtered run gets the same launcher and environment as the full suite (`setarch -R` and `TSAN_OPTIONS` on `linux-x64-tsan`). A filter containing `%`, `"` or a line break is refused (exit 2).
- `--label <L>` runs `ctest --preset <p> -L <L> --no-tests=error` instead of the full run of `--test`: `unit`, `scenario`, `probe`, `lesson` ([test.md](/.agent/rules/test.md) §2). A label that matches no test fails. Same refused characters as `--gtest-filter`.
- `--report [DIR]` (with `--test`, `--label` or `--gtest-filter`) writes a test report to `DIR`, default `out/test-reports/<preset>/<YYYYMMDD-HHMMSS>/`: `run.json` (steps and exit codes), `tests.json` (`ctest --show-only=json-v1`), `ctest-<n>.junit.xml` per ctest step, `gtest/*.json` per GoogleTest program and the summary `report.md` ([`test_report.py`](/.agent/scripts/test_report.py)). Written even when a test fails; the exit code is unchanged. `DIR` must be relative to the repository root (it is passed on to WSL unchanged).
- The exit code is the first failing step's; `--dry-run` prints the steps.

## 2. Presets
| Preset | Use |
|---|---|
| `windows-x64-debug` / `linux-x64-debug` | default build and unit check |
| `*-release`, `*-relwithdebinfo` | release builds; RelWithDebInfo for crash-dump symbolization |
| `linux-x64-asan` | ASan + UBSan; required for lifetime, cast and memory-layout units |
| `linux-x64-tsan` | TSan; required for concurrency units (tests run under `setarch -R`) |
| `linux-x64-playground` | web playground only (spec 070-02): Debug, lessons only (no tests, no samples), own build directory so a web run never waits for the `linux-x64-debug` ninja lock. Built by `web/server/runner.py`, not a verification preset |
| `linux-x64-playground-release` | web playground's long profile (spec 070-06): the same as `linux-x64-playground` with RelWithDebInfo, own build directory. Built by `web/server/runner.py`, not a verification preset |

All presets build with `ATUGCC_WARNINGS_AS_ERRORS=ON` and with C++20 module scanning on (`CMAKE_CXX_SCAN_FOR_MODULES=ON` in `base`; `CMakeLists.txt` stops a configure with it off). Windows presets use MSVC, Linux presets Clang 20 (`clang++-20`, libstdc++ 14). CMake 4.0 or later on both hosts (`cmakeMinimumRequired`). Sanitizers come from `ATUGCC_SANITIZERS` (MSVC: `address` only).

## 3. Environment
- **vcpkg / Boost**: dependencies live in the manifest ([`vcpkg.json`](/vcpkg.json); registry and baseline in [`vcpkg-configuration.json`](/vcpkg-configuration.json)). [`CMakeLists.txt`](/CMakeLists.txt) picks the toolchain from `-DCMAKE_TOOLCHAIN_FILE`, then `ATUGCC_VCPKG_ROOT`, then `VCPKG_ROOT` (each only if `<root>/scripts/buildsystems/vcpkg.cmake` exists); with a toolchain, vcpkg installs the manifest into `out/build/<preset>/vcpkg_installed` on configure. Without one, system packages are used (WSL/Ubuntu). On Windows the VS developer environment sets `VCPKG_ROOT` to the bundled vcpkg, so no setup is needed.
- **Linux toolchain**: `clang-20`, `clang-tools-20` (`clang-scan-deps-20` for module scanning), `libstdc++-14-dev`, `ninja-build`, and CMake 4 from the Kitware APT repository: [`linux_build_setup.md`](/docs/guides/linux_build_setup.md). Windows uses the CMake of VS 2026.
- A new dependency is added to `vcpkg.json` (never installed by hand); a baseline change is its own task.
- Machine-specific values (toolchain paths, compilers) go into `CMakeUserPresets.json` or environment variables, never into `CMakePresets.json` (non-negotiable rule 1).

## 4. Test and package
- Tests: [test.md](/.agent/rules/test.md).
- Install into the preset's install directory: `cmake --install out/build/<preset>` (`installDir` is `out/install/<preset>`).
- Archive (optional): `Compress-Archive -Path out/install/<preset>/* -DestinationPath artifacts/atugcc-<preset>.zip` (Windows) or `cd out/install/<preset> && zip -r ../../../artifacts/atugcc-<preset>.zip .` (Linux).

## 5. Common failures
| Symptom | Cause and fix |
|---|---|
| `Could not find ... "Boost"` | No vcpkg toolchain and no system Boost: build inside the VS developer environment (Windows), set `VCPKG_ROOT`, or install `libboost-dev` (Linux) |
| vcpkg fails on the first configure | No network for the registry/sources, or a vcpkg tool older than the baseline needs: check the vcpkg output in the configure log |
| Cannot find standard headers (`<atomic>`), x86/x64 link errors | MSVC environment missing or wrong: use `build.py`, which calls `VsDevCmd -arch=x64 -host_arch=x64` |
| `CMakeCache.txt directory ... is different` | Build directory copied from another checkout: `build.py` removes and rebuilds it |
| `ThreadSanitizer: unexpected memory mapping` | High ASLR entropy; the TSan preset's tests already run under `setarch -R` |
| `ctest` finds no tests | Wrong preset or not built: `build.py --preset <p> --test` |
| `atugcc always builds with C++20 modules` at configure | `CMAKE_CXX_SCAN_FOR_MODULES` is off (an ad-hoc configure or a user preset that turns it off): configure through a preset |
| CMake cannot find `clang-scan-deps` | `clang-tools-20` is not installed (Linux) |
| `LNK1000: Internal error during IncrBuildImage` or `Access violation` while linking (Windows) | Incremental-link files (`.ilk`) from an older build of the same directory; seen once when modules were turned on (070-13). `--fresh` does not remove them: delete `out/build/<preset>` and build again |
| Errors about a module or BMI after changing the compiler | Object files and BMIs of the old compiler: `build.py --preset <p> --fresh`, or delete the build directory |
| A variable removed from a preset still has an effect | A plain configure re-applies preset values but never deletes cache entries: `build.py --preset <p> --fresh` |
