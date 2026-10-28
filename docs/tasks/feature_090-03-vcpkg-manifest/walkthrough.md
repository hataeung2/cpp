# Walkthrough: 090-03 vcpkg manifest로 Boost 자동 공급

- Spec: [/docs/specs/090_03_vcpkg_manifest.md](/docs/specs/090_03_vcpkg_manifest.md) · Plan: [plan.md](./plan.md) · Tests: [testrecord.md](./testrecord.md)

## Result
Boost.Lockfree is declared in `vcpkg.json`; `vcpkg-configuration.json` pins the microsoft/vcpkg git registry to release 2026.07.29. With any vcpkg toolchain (the VS-bundled one through VsDevCmd, or a standalone one), the first configure installs Boost into the build directory; without vcpkg (WSL/Ubuntu) the system Boost is used. The same `CMakePresets.json` works on every machine.

- Windows (`windows-x64-debug`, no env var set): configure, build with `/W4 /WX` (0 warnings), all tests pass. First time this project is verified warning-free on MSVC.
- Linux (`linux-x64-debug`, WSL, no vcpkg): unchanged, all tests pass.
- Review: `cpp-reviewer`, no mismatches; two wording fixes applied.

## Follow-ups
- KI-007 closed.
- Raising the baseline (newer Boost) is a separate task (spec Out of Scope).
