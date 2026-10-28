---
trigger: model_decision
description: When configuring, building, testing or packaging the project
---

# Agent Rule: Configure, Build, Test, Package (atugcc)

`CMakePresets.json` is the only source of configure and build settings. Never configure ad hoc (`cmake -S . -B build`): a missing configuration becomes a preset. A `.claude` hook refuses ad-hoc configure commands.

## 1. The one command
```text
py -3 .agent/scripts/build.py [--preset auto|<name>] [--target <t>] [--test] [--gtest-filter <f>] [--fresh] [--dry-run]
```
(Linux host: `python3`.) [`build.py`](/.agent/scripts/build.py) does the mechanical part:
- `auto` picks `<host>-x64-debug`; user presets from the untracked `CMakeUserPresets.json` are accepted too (name them `windows-…` / `linux-…`).
- **Windows presets** run inside the MSVC developer environment: `VsDevCmd.bat` from `VSDEVCMD`, else found with `vswhere`.
- **Linux presets on a Windows host** run in WSL (`ATUGCC_WSL_DISTRO`, else the default distribution).
- Configure runs when needed: no cache, an interrupted configure, `--fresh`, or a build directory created at another location (a copied checkout: the directory is removed first, because FetchContent sub-builds keep their own caches).
- The exit code is the first failing step's; `--dry-run` prints the steps.

## 2. Presets
| Preset | Use |
|---|---|
| `windows-x64-debug` / `linux-x64-debug` | default build and unit check |
| `*-release`, `*-relwithdebinfo` | release builds; RelWithDebInfo for crash-dump symbolization |
| `linux-x64-asan` | ASan + UBSan; required for lifetime, cast and memory-layout units |
| `linux-x64-tsan` | TSan; required for concurrency units (tests run under `setarch -R`) |

All presets build with `ATUGCC_WARNINGS_AS_ERRORS=ON`. Sanitizers come from `ATUGCC_SANITIZERS` (MSVC: `address` only).

## 3. Environment
- **vcpkg / Boost**: dependencies live in the manifest ([`vcpkg.json`](/vcpkg.json); registry and baseline in [`vcpkg-configuration.json`](/vcpkg-configuration.json)). [`CMakeLists.txt`](/CMakeLists.txt) picks the toolchain from `-DCMAKE_TOOLCHAIN_FILE`, then `ATUGCC_VCPKG_ROOT`, then `VCPKG_ROOT` (each only if `<root>/scripts/buildsystems/vcpkg.cmake` exists); with a toolchain, vcpkg installs the manifest into `out/build/<preset>/vcpkg_installed` on configure. Without one, system packages are used (WSL/Ubuntu). On Windows the VS developer environment sets `VCPKG_ROOT` to the bundled vcpkg, so no setup is needed.
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
| A variable removed from a preset still has an effect | A plain configure re-applies preset values but never deletes cache entries: `build.py --preset <p> --fresh` |
