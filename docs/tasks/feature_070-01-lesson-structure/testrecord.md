# Test Record: 070-01 레슨 구조

- Spec: [/docs/specs/070_01_lesson_structure.md](/docs/specs/070_01_lesson_structure.md)
- Plan: [plan.md](/docs/tasks/feature_070-01-lesson-structure/plan.md)
- Date: 2026-10-28
- Hosts: Windows 11 (MSVC 19.51, Python 3.15), WSL Ubuntu 24.04 (GCC 13.3, CMake, Python 3.12)

## Runs

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R1 | `py -3 tools/test_lessons.py` before U4b existed | all but the repo test pass | 14/15; `jthread_worker` not found (U4b still being written) | Expected |
| R2 | `py -3 tools/lessons.py check` after U4b | 0 errors | `0 error(s), 0 warning(s); 2 track(s), 3 lesson(s), 2 unit(s)` | Pass |
| R3 | `build.py --preset linux-x64-debug --test` | AllTests, TraceStream, 3 lesson tests pass | 5/5 passed | Pass |
| R4 | `build.py --preset windows-x64-debug --test` (`/W4 /WX`) | 5/5 | 5/5 passed | Pass |
| R5 | `build.py --preset linux-x64-tsan --test`, plus each thread lesson run directly under `setarch -R` | no TSan report | 5/5 passed; `thread_and_log` and `device_state_machine` exit 0, 0 warnings | Pass |
| R6 | lesson output (linux-x64-debug) | values as the READMEs say | `lambda_capture`: `11, 12 / 11`, `total = 7`, `Hello, atugcc!`, `42`; `device_state_machine`: IDLE→STANDBY→RUN, Mermaid sequence with `run_cycle() ×2`; `thread_and_log`: 9 / 6 ticks | Pass |
| R7 | `cmake --preset linux-x64-debug -DATUGCC_BUILD_LESSONS=OFF`, `ctest -N`, `ninja -t targets all \| grep -c ^lesson_`; then `=ON` again | no lesson targets or tests; other tests remain | 0 lesson targets; tests: AllTests, TraceStream; back to 5 tests after `=ON` | Pass |
| R8 | copy `01_lambda_capture` to `99_tmp_probe` (id `tmp_probe`), build + ctest without touching CMake files | new target and test | `Re-running CMake`, `lesson_tmp_probe` built, `lesson.tmp_probe` passed (6/6) | Pass |
| R9 | append `[run] profile = "long"`, `timeout = 42` to that manifest, build | reconfigure; test gets `long` label and TIMEOUT 42 | `Re-running CMake`; `ctest -N -L long` lists it; properties `LABELS ['lesson','long']`, `TIMEOUT 42`; folder removed, back to 5/5 | Pass |
| R10 | `py -3 .agent/scripts/test_agent_scripts.py` | pass | 50 tests OK (with `test_lessons_are_checked`) | Pass |
| R11 | `lint_docs.py` while U4b was half written (manifest present, `main.cpp` not yet) | lint reports the lesson error | `ERROR …/01_device_state_machine/lesson.toml:4: lessons: 'sources' entry 'main.cpp' does not exist` | Pass |

## Revision 1 — 2026-10-28
Reviews of the first versions (see Reviews) led to one rework round:
- U4b (agy, resumed): `thread_and_log` gave both workers one `Logger`, whose ring-buffer write is single-thread only (KI-014). Each worker now has its own `Logger`; README and unit docs state the contract.
- U1/U2/U3/U6 (lead): `check()` now reads every `lesson.toml` with the same regexes as `lessons/CMakeLists.txt` and reports any difference from the TOML values (inline `run = {…}`, keys outside `[run]`, single quotes, indented keys); `id` uses `fullmatch`; a unit's folder name must equal its id; absolute `lib:` paths are rejected; a non-UTF-8 manifest is an ERROR, not a crash. CMake adds every manifest to `CMAKE_CONFIGURE_DEPENDS`. Lambda README exercise 2 now says to run (not only build) under ASan with `detect_stack_use_after_return=1`.

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| R12 | `py -3 tools/test_lessons.py` | all pass | 27 tests OK (added: duplicate unit id, lesson/unit shared id, unit include WARN, missing unit WARN, timeout 0, absolute lib, 5 CMake-agreement cases, CLI exit codes, index file) | Pass |
| R13 | `build.py --test` on `windows-x64-debug`, `linux-x64-asan`, `linux-x64-tsan` after the rework; thread lessons under `setarch -R` | all pass, no sanitizer report | 5/5 each; thread lessons exit 0, 0 TSan warnings | Pass |
| R14 | `lessons.py check`, `test_agent_scripts.py`, `naming_check.py`, `lint_docs.py` | exit 0 | 0 errors; 50 OK; 0 snake_case; 0 errors, 0 warnings | Pass |

## Acceptance Criteria Evidence

| AC | Criterion (short) | Evidence | Result |
|---|---|---|---|
| AC-1 | 3 seed lessons build warning-free and pass smoke tests on `windows-x64-debug`, `linux-x64-debug`, `linux-x64-tsan` | R3, R4, R5, R13 | Pass |
| AC-2 | a copied lesson folder becomes a target and test without CMake edits | R8 (and R9: a manifest edit reconfigures) | Pass |
| AC-3 | `check` exits 0 on the seed; each broken fixture gives its finding | R2; `BrokenTreeTest` (id duplicate, missing uses, cycle, missing source, TOML syntax with line, include not in uses, bad profile, timeout range) and `CMakeAgreementTest` (multi-line sources) in R12; `CommandLineTest.test_check_exit_code` | Pass |
| AC-4 | `jthread_worker` is used by 2 lessons in 2 tracks | `RepositoryTest.test_jthread_worker_is_used_by_lessons_in_two_tracks` (R12) | Pass |
| AC-5 | `ATUGCC_BUILD_LESSONS=OFF`: no lesson targets, rest unchanged | R7 | Pass |
| AC-6 | `lint_docs.py` runs `lessons.py check`, exit 0 | R11 (finding surfaces through lint), R10 (`test_lessons_are_checked`), R14 | Pass |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U4b | codex luna (high) | D4 match; concurrency and lifetime of `PeriodicWorker` and both lessons | `thread_and_log`: two threads share one `Logger` whose ring-buffer write is single-thread only | fixed by the author (agy, `--resume`); KI-014 for the library |
| U4b rework | codex luna (high) | finding resolved, nothing new | resolved; exercise 4 wording missed the worker's own start/stop logs | wording fixed by the lead (doc only) |
| U1–U3, U4a, U5, U6 | `cpp-reviewer` | D1 match and check/CMake agreement; trivial tests; CMake per profile; docs vs code | check and CMake could read a manifest differently (inline `run`, top-level keys, quotes, indent); `id` `$` accepts trailing newline; unit folder ≠ id not checked; absolute `lib:`; non-UTF-8 crash; manifest edits did not reconfigure; missing tests (CLI exit code, duplicate unit id, unit-include WARNs, timeout 0); lambda exercise 2 said "build" for a run-time ASan finding; two cosmetic doc points | all fixed in Revision 1; `load()` returns `(Catalog, Report)` — plan D1 wording updated instead of the code |
| Tester | lead | unit diffs against D1–D5; tests against ACs | no further findings | — |

Cross-family review: risky unit U4b written by agy, reviewed by codex. Ordinary units written by the lead, reviewed by `cpp-reviewer` (same family, as delegation.md §1 allows for ordinary units).
