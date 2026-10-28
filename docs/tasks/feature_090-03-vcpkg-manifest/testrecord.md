# Test Record: 090-03 vcpkg manifest로 Boost 자동 공급

## Acceptance Criteria Evidence
| AC | Evidence | Result |
|---|---|---|
| AC-1 | `py -3 .agent/scripts/build.py --preset windows-x64-debug --test`, no env var set: `atugcc: vcpkg toolchain from VCPKG_ROOT` (VS bundled vcpkg 2026-07-27), registry fetched, 33 packages installed (boost-lockfree 1.91.0 and dependencies) into `out/build/windows-x64-debug/vcpkg_installed`; 61/61 targets with `/W4 /WX`, 0 `warning C`; `100% tests passed` | Pass |
| AC-2 | `py -3 .agent/scripts/build.py --preset linux-x64-debug --test` (WSL, no `VCPKG_ROOT`): no vcpkg toolchain, system Boost; `100% tests passed` | Pass |
| AC-3 | `py -3 .agent/scripts/lint_docs.py`: 0 errors (vcpkg files contain URLs and a commit id only) | Pass |
| AC-4 | README §Environment and config.md §3/§5 describe the manifest; KI-007 CLOSED | Pass |

## Runs
| Test | Expected | Actual | Status |
|---|---|---|---|
| Windows debug, fresh build directory | configure + build + test | as AC-1; first configure includes the vcpkg install (boost-lockfree 4.4 s, binary cache populated for later runs) | Pass |
| Linux debug (WSL) | unchanged behaviour | as AC-2 | Pass |
| Docs lint | exit 0 | `0 error(s), 0 warning(s), 19 info` | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1–U2 (manifest, README, config.md, KI-007) | `cpp-reviewer` (26k tokens, 1 min) | spec conformance; config form and pinned commit; docs vs `CMakeLists.txt` toolchain order; contradictions with Assumptions/Out of Scope; machine paths | VERDICT none. Wording: docs omitted that a root is used only if its `vcpkg.cmake` exists; KI-007 option text still named `builtin-baseline`. Not verified by the reviewer: baseline = tag commit, VS Code CMake Tools setting `VCPKG_ROOT` | Both wording points fixed. Baseline verified by the lead with `git ls-remote` (`refs/tags/2026.07.29^{}` = `9e593bb…`). README no longer claims the VS Code behaviour; it names the verified VsDevCmd path and the fallback (`VCPKG_ROOT`) |
