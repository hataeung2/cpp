# Test record: 070-14 essentials modules 레슨과 `format_text`의 `std::print` 단계

- Spec: [/docs/specs/070_14_essentials_modules_lesson.md](/docs/specs/070_14_essentials_modules_lesson.md)
- Plan: [plan.md](/docs/tasks/feature_070-14-essentials-modules-lesson/plan.md)
- Hosts: Windows 11, MSVC 19.51 (VS 2026); WSL Ubuntu 24.04, Clang 20.1.2 + libstdc++ 14.2, CMake 4

## Scripts (lead's scratch area, not committed)
Output capture and diff: each lesson binary run on both hosts, `diff` after stripping `\r`. Comment pairs and Hangul output: an inline Python check (every comment line with Hangul is followed by a comment line without Hangul; no Hangul in captured stdout). AC-4: append a comment line to one source, rebuild `lesson_modules`, keep the Ninja `Building`/`Linking` lines, restore the file from a copy and rebuild. AC-5: scratch copies outside the repository compiled against the existing BMIs with the preset flags (agy opus during review U2). AC-7: `ac7.mjs` (agy flash) drives the installed Edge headless (`playwright-core`) against `tools/playground.py --port 18783`.

## Runs
| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | `build.py --preset windows-x64-debug --target lesson_modules` (agy output) | 0 warnings | clean; output as plan | Pass |
| R2 | `build.py --preset linux-x64-debug --target lesson_modules` | 0 warnings | `geometry.cpp:44: error: no member named 'unexpected' in namespace 'std'`: `import atugcc.core;` exports no `std::` names (MSVC had accepted it) | Fail |
| R3 | after lead (small): `module;` + `#include <expected>` in `geometry.cpp`; both hosts, run, diff | AC-2 | 0 warnings both; outputs identical | Pass |
| R4 | `lesson_format_text` both hosts, diff | AC-8 | 0 warnings; only step 6's `format_error` text differs (library message, README says so); step 7 `println` and `cout` rows identical | Pass |
| R5 | AC-4 probe, both hosts | see AC-4 | see AC-4 | Pass |
| R6 | `build.py --preset windows-x64-debug --test` | all pass | first run: link of `lesson_device_state_machine.exe` and `lesson_modules.exe` failed with "The process cannot access the file because it is being used by another process" (file lock, other jobs running); rerun: 29/29 | Pass |
| R7 | `build.py --preset linux-x64-debug --test` | all pass | 29/29 (`PlaygroundServer` included) | Pass |
| R8 | `build.py --preset linux-x64-asan --test`, `linux-x64-tsan --test` | all pass | 29/29, 29/29 | Pass |
| R9 | `build.py --preset linux-x64-playground`, `linux-x64-playground-release` | build all lessons | exit 0, exit 0 | Pass |
| R10 | `py -3 tools/test_lessons.py`; `py -3 tools/lessons.py check` | pass; 0/0 | 79 tests OK (71 + 8 new); 0 errors, 0 warnings (16 lessons) | Pass |
| R11 | `py -3 web/server/test_server.py -k module` | pass | 1 test OK | Pass |
| R12 | `npm --prefix web/frontend test` | pass | 7 files, 63 tests | Pass |
| R13 | comment pairs on the 4 `15_modules` sources and `format_text/main.cpp`; Hangul in the 4 captured outputs | OK | all pairs OK; no Hangul | Pass |
| R14 | `node ac7.mjs` | AC-7 | 6 checks OK; screenshots in [`screenshots/`](/docs/tasks/feature_070-14-essentials-modules-lesson/screenshots/); `geometry.cppm` byte-identical afterwards (`cmp` with the lead's copy), no `probe.cppm` left | Pass |
| R15 | `lint_docs.py` | exit 0 | 0 errors, 0 warnings | Pass |

## AC evidence
| AC | Criterion (short) | Evidence | Result |
|---|---|---|---|
| AC-1 | `modules` last in essentials; `.cppm` sources; `mod:` → `modules/atugcc/core.cppm` | `lessons.py index`: `…, lock_free_buffer, span_timing, modules`; `sources` = `main.cpp`, `geometry.cppm`, `geometry_rect.cppm`, `geometry.cpp`; `files` = `modules/atugcc/core.cppm`, `include/atugcc/core/error.hpp` | Pass |
| AC-2 | builds clean on both, 4 steps, same output | R3 | Pass |
| AC-3 | `.cppm` in the `CXX_MODULES` file set, no `#include "atugcc` in `main.cpp` | Ninja builds `geometry.cppm.obj`/`.o` and `geometry_rect.cppm.obj`/`.o` as module units; BMIs `modules.geometry` and `modules.geometry-rect` (`.ifc` / `.pcm`, agy opus review); `grep -c '#include "atugcc' main.cpp` = 0 | Pass |
| AC-4 | exercise 2 rebuild scope | both hosts: edit `geometry.cpp` → `geometry.cpp` compiled, link; edit `geometry.cppm` → `geometry.cppm`, `geometry.cpp`, `main.cpp` compiled, link. Files restored (byte compare empty) | Pass |
| AC-5 | exercises 1 and 3 (3a on Clang, spec History) | exercise 1: MSVC `error C2039: 'clampSide': is not a member of 'modules::geometry::detail'`, Clang `declaration of 'clampSide' must be imported from module 'modules.geometry' before it is required`; 3a: Clang `error: missing '#include'; 'to_string' must be declared before it is used`, MSVC builds (non-conformance, user decision); 3b: `export import atugcc.core;` → `main.cpp` without its import builds on both | Pass |
| AC-6 | new `lessons.py` rules | R10; tests `test_entry_source_cannot_be_cppm`, `test_unit_files_cannot_contain_cppm`, `test_lesson_sources_rejected_module_extension`, `test_uses_mod_path_validation`, `test_module_name_prefix`, `test_import_atugcc_requires_mod_in_uses`, `test_cppm_source_hangul_literal_warns`, `test_index_includes_mod_files_and_cppm_sources` | Pass |
| AC-7 | web | R14: Run of `modules` exit 0 with the 4 headings and the macro line (`ac7-run-modules.png`); `geometry.cppm` tab tokenized as C++ (`ac7-cppm-highlight.png`); related tab `🔒 core.cppm` read-only; `PUT /api/files` of a new `probe.cppm` → 200, then removed; `int broken(` in `geometry.cppm` → `빌드 실패 · 오류 3개`, error squiggles on `geometry.cppm` lines 14, 28, 32 (`ac7-diagnostic.png`; the first error is reported where the unterminated declaration ends); searches `.cppm`, `import`, `모듈` → `modules` (`레슨 1`) | Pass |
| AC-8 | `format_text` step 7, README | R4; both READMEs: "아직 쓰지 않습니다" gone, exercise 3 no longer toolchain-specific | Pass |
| AC-9 | README pairs, no Hangul output, comment pairs | `15_modules` and `02_format_text` README pairs: same headings (6/6, 5/5), exercises (3/3, 3/3), code blocks (0/0); R13; codex luna doc review (translation question): none | Pass |
| AC-10 | suites, sanitizers, playground builds, tool tests | R6–R12 | Pass |
| AC-11 | §8 docs, lint | R15 | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1, U2, U6 | agy opus (read-only) | spec §2.2/§2.3, AC-2/3/5/7; module rules; exercises 1 and 3 on both compilers | must fix: exercise 3a does not fail on MSVC 19.51 (checked with scratch copies). optional: plan line for `geometry.cpp` stale; comment on why core names are visible in `geometry.cpp`; quote real messages in the README; step 1 wording vs spec | user decision: keep exercise, 3a on Clang (spec Assumption 11, AC-5, History); optional items fixed by lead (small) and in U7 |
| U3, U4, U5 | codex luna (medium) | spec §2.3/§2.4, regex edge cases, trivially passing tests | none | — (agy opus was out of quota; codex is the cross-family reviewer for flash's code) |
| U4 | lead | per-unit diff | unit self-coverage key changed from folder name to unit id (behaviour change) | restored `manifest.parent.name`, lead (small) |
| U7, U8 | codex luna (medium) | claims vs code, KO/EN parity | none (short answer, 36 s) | — |
| U7 | lead | README vs AC-4 measurement | exercise 2 said only `main.cpp` is recompiled after an interface edit; `geometry.cpp` is too | fixed both languages, lead (small) |
| U8 | lead | agy opus's own notes | lesson links use `README.md` where the pages use `README.en.md`; stale "empty numbers" sentence in `lessons/README.md` | fixed, lead (small) |

## Notes
- agy opus hit its quota (HTTP 429, "Individual quota reached", resets in about 5 h) after U8 and review U1/U2/U6; U7 moved to agy argon, the remaining reviews to codex luna.
- MSVC 19.51 accepted two things Clang 20 rejects: `std::unexpected` through `import atugcc.core;` (R2) and names of a non-exported import in an importer (AC-5 3a). The Linux preset is the stricter check for module code.
