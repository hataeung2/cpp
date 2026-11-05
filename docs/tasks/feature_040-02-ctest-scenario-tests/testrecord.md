# Test record: 040-02 CTest 시나리오 테스트와 테스트 리포트

- Spec: [/docs/specs/040_02_ctest_scenario_tests.md](/docs/specs/040_02_ctest_scenario_tests.md)
- Plan: [plan.md](plan.md)
- Hosts: Windows 11 (MSVC 19.51.36260, CMake of VS 2026), WSL Ubuntu (Clang 20.1.2, libstdc++ 14, CMake 4.4.5)
- Reports (`out/`, not committed) are quoted below; commands are given with each run.

## Runs

| # | Command | Expected | Actual | Status |
|---|---|---|---|---|
| 1 | `build.py --preset windows-x64-debug --label "unit\|scenario"` | builds 0 warnings; scenarios and unit pass | 5/5 passed (2 scenario, 3 unit) | Pass |
| 2 | `build.py --preset linux-x64-debug --label "unit\|scenario"` | same on Clang | 5/5 passed | Pass |
| 3 | after moving AC-3 (c) out of process: `ctest --preset linux-x64-debug -L "unit\|scenario"` | 6 tests pass | 6/6 passed (4 unit, 2 scenario) | Pass |
| 4 | mutation: `HasFatalFailure()` → `HasFailure()` in `scenario.hpp`, `ctest -R ScenarioStep` (restored after) | `ScenarioStepNonFatalContinues` fails | `Failed  Error regular expression found in output. Regex=[\[skip]`; the other two pass | Pass (the check can fail) |
| 5 | `build.py --preset windows-x64-debug --test --report` | full suite passes; report written | 34/34 passed (unit 4, scenario 2, probe 12, lesson 16, long 2); `report: out/test-reports/windows-x64-debug/20261104-162216/report.md` | Pass |
| 6 | `build.py --preset linux-x64-debug --test --report` | full suite passes; report written | 34/34 passed (unit 4, scenario 2, probe 12 incl. `PlaygroundServer`, lesson 16); `report: out/test-reports/linux-x64-debug/20261104-162650/report.md` | Pass |
| 7 | `build.py --preset linux-x64-tsan --label "unit\|scenario"` | pass under TSan | 6/6 passed | Pass |
| 8 | `build.py --preset linux-x64-asan --label "unit\|scenario"` | pass under ASan + UBSan | 6/6 passed | Pass |
| 9 | independence, `linux-x64-debug`: each scenario alone (`-R`), `-L scenario`, `-j 4`, `--schedule-random`, `--repeat until-fail:2` | all pass | all `100% tests passed` | Pass |
| 10 | S1 broken on purpose (targets Standby, Abort, Idle, Standby, Run; restored after): `build.py --preset linux-x64-debug --label scenario --report out/test-reports/ac12-broken-s1` | exit ≠ 0, report lists the failure with `step 4` | exit 8; report (below) | Pass |
| 11 | `build.py --preset windows-x64-debug --label nosuchlabel` | fails | `No tests were found!!!`, exit 8 | Pass |
| 12 | `py -3 .agent/scripts/test_agent_scripts.py` | all pass | 70 tests OK (after the last fixes) | Pass |
| 13 | `py -3 .agent/scripts/lint_docs.py`, `py -3 .agent/scripts/naming_check.py` | exit 0 | 0 errors; 0 snake_case (after adding GoogleTest's `current_test_info`, `test_suite_name` to `ALLOWED`) | Pass |
| 14 | tests/README.md followed (AC-14): §3 example scenario added as a temporary file + list line, `build.py --preset windows-x64-debug --label scenario`; §4.4 commands run as written in WSL (removed / restored after) | the example appears and passes; §4.4 makes a report | `scenario.MyFlow.WhatTheUserSees ... Passed` (3/3); §4.4 → `report: out/test-reports/manual/report.md` | Pass after two README fixes (below) |
| 15 | final: both full suites with `--report` on the committed tree | pass | see Final runs | |

### Failures and retries
- Run 14, first try: the README §3 example needed `#include <memory>` (added to the README); the §4.4 commands had no `mkdir` and `test_report.py` refused a folder without `run.json` although §4.4 said it works without one. Fixed: `mkdir -p` in the README; `test_report.py` needs at least one `ctest-*.junit.xml`, `run.json` is optional (`TestReportTest.test_main` checks both).
- Run 14, first §4.4 try also failed `scenario.TracedStateMachine` because the Linux build still held run 10's broken S1 binary (source already restored); after `cmake --build --preset linux-x64-debug` it passed.
- While checking the `--report DIR` refusal, a command meant for the fixed build.py ran with the old one (the fix script had stopped on an assertion) and created `a%b/` in the repository root with `run.json` and an empty `gtest/`; it was removed. The fixed build.py refuses `%` (exit 2, nothing created). A planned direct run with `--report .` was blocked by the auto-mode classifier; the safety checks were verified by calling `report_dir_problem` and by `BuildScriptTest.test_report_dir_problem` (temp directories) instead.

### Report excerpts
Run 5 (`windows-x64-debug`):
```
| unit | 4 | 4 | 0 | 0 | 26.71 |
| scenario | 2 | 2 | 0 | 0 | 0.10 |
| probe | 12 | 12 | 0 | 0 | 142.22 |
| lesson | 16 | 16 | 0 | 0 | 18.07 |
| long | 2 | 2 | 0 | 0 | 16.88 |
| **All** | 34 | 34 | 0 | 0 | 187.10 |
...
| atugcc_scenarios.json | 1 | 0 | 0 |
| atugcc_scenarios_1.json | 1 | 0 | 0 |
| atugcc_tests.json | 140 | 0 | 3 |
| **All** | 142 | 0 | 3 |
```
`out/build/windows-x64-debug/bin/atugcc_tests.exe --gtest_list_tests` → 140 cases; Linux report 141, `--gtest_list_tests` 141. ctest summary lines: `100% tests passed, 0 tests failed out of 34` on both. Absolute paths in both `report.md`: 0 (`grep -cE "[A-Za-z]:[\\/]|/mnt/|/home/|/usr/"`).

Run 10 (broken S1):
```
## Failures
### scenario.TracedStateMachine.EventsReachStreamInOrder
- `TracedStateMachine.EventsReachStreamInOrder`:
tests/scenario/scenario_traced_state_machine.cpp:146
Expected equality of these values:
  actualTransitions
    Which is: { ("IDLE", "STANDBY"), ("STANDBY", "ABORT"), ("ABORT", "IDLE"), ("IDLE", "STANDBY"), ("STANDBY", "RUN") }
  expectedTransitions
    Which is: { ("IDLE", "STANDBY"), ("STANDBY", "RUN"), ("RUN", "STANDBY"), ("STANDBY", "ABORT"), ("ABORT", "IDLE") }
Google Test trace:
tests/scenario/scenario.hpp:73: step 4: the stream has the run in order
```

Run 7 (TSan), `ctest -N -V -R "^scenario.LoggedErrorFlow"` in `out/build/linux-x64-tsan`:
```
Test command: /usr/bin/setarch "x86_64" "-R" ".../bin/atugcc_scenarios" "--gtest_filter=LoggedErrorFlow.ErrorFromTwoThreadsReachesFile" "--gtest_also_run_disabled_tests"
Environment variables:
 TSAN_OPTIONS=suppressions=.../tests/tsan.supp
```

Run 9 / AC-2, `ctest --show-only=json-v1` read by a short script (every test outside `lesson.*` must have exactly one of unit/scenario/probe):
```
bad: []
probe 12 ['TraceStream', 'SpanCost', 'DumpPrepare_off', 'DumpPrepare_once', 'DumpPrepare_replace', 'DumpPrepare_cleanup', 'DumpPrepare_check-removed', 'LogSlotsFromEnvironment', 'LoggerContention', 'CrashDump', 'LogMap', 'PlaygroundServer']
scenario 2 ['scenario.TracedStateMachine.EventsReachStreamInOrder', 'scenario.LoggedErrorFlow.ErrorFromTwoThreadsReachesFile']
unit 4 ['AllTests', 'ScenarioStepFatalStops', 'ScenarioStepFatalBefore', 'ScenarioStepNonFatalContinues']
```
(Linux. Windows has `LessonConsoleCodePage` instead of `PlaygroundServer`, also 12 probe.)

## AC evidence

| AC | Criterion (short) | Evidence | Result |
|---|---|---|---|
| AC-1 | `-L scenario` lists and passes exactly S1, S2 on both presets | runs 1, 2 (`scenario.TracedStateMachine.EventsReachStreamInOrder`, `scenario.LoggedErrorFlow.ErrorFromTwoThreadsReachesFile`), runs 5, 6 | Pass |
| AC-2 | every `tests/` test has exactly one kind label; `-L unit` = `AllTests` + the three step self-checks (History 2026-11-04 DEV); lesson labels unchanged | run 9 label script (`bad: []`); lesson rows 16 / long 2 as before in runs 5, 6 | Pass |
| AC-3 | step helper (a)–(e) | (a) `ScenarioStepTest.FailureMessageNamesTheStep`, (d) `SuccessfulStepsReturnTrueAndPrint`, (e) `WorkDirIsEmptiedWhenScenarioStarts`; (b) `ScenarioStepFatalStops`, (c) `ScenarioStepNonFatalContinues`, before-first-step `ScenarioStepFatalBefore`; run 4 shows the self-check can fail | Pass |
| AC-4 | scenarios independent (alone, together, `-j 4`, random order, twice) | run 9 | Pass |
| AC-5 | S1 checks transitions, seq, spans, diagram; a broken order fails in step 4 | runs 1, 2; run 10 (`step 4` in the message) | Pass |
| AC-6 | S2: `configureLogBuffers` succeeds, two lines with `FileIOFailure` and the call site | runs 1, 2, 7, 8; codex review (questions 3, 4) | Pass |
| AC-7 | TSan and ASan pass; TSan command has `setarch` and `TSAN_OPTIONS` | runs 7, 8 and the `ctest -N -V` excerpt | Pass |
| AC-8 | `--label`: dry-run shape, replaces `--test`, unknown label fails, refused characters, WSL forwarding, `^` reaches ctest | `BuildScriptTest.test_label`, `test_steps_and_batch`, `test_wsl_forwarding`, `test_batch_arguments_reach_the_program_unchanged`; run 11 | Pass |
| AC-9 | `--test` passes on both presets incl. scenarios; `--gtest-filter` unchanged | runs 5, 6; `BuildScriptTest.test_steps_and_batch` (filter step unchanged without `--report`) | Pass |
| AC-10 | docs and naming gates | run 13 | Pass |
| AC-11 | `--test --report` writes the folder; numbers match ctest; `AllTests` case count = `--gtest_list_tests`; label rows; no absolute paths | runs 5, 6 and the excerpts (34 = 34; 140 / 141 = list counts; 0 absolute paths) | Pass |
| AC-12 | a failing run still gets a report naming the scenario and `step 4`; no report when no test step ran | run 10; `BuildScriptTest.test_finish_report_no_test_step` | Pass |
| AC-13 | `test_report.py` on prepared samples (pass, gtest failure, crash without JSON, broken JSON); `--report` refusals; dry-run shows junit/`GTEST_OUTPUT` and creates nothing; WSL gets the same relative DIR | `TestReportTest.test_write_report`, `test_fallback_cmake_labels`, `test_main`; `BuildScriptTest.test_report_build_steps`, `test_report_show_and_batch`, `test_report_main_argument_errors`, `test_report_dir_problem`, `test_forwarded_args_report`, `test_batch_exit_codes` | Pass |
| AC-14 | `tests/README.md` can be followed as written | run 14 | Pass (after the README fixes in run 14) |

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1–U4 | cpp-reviewer | helper behaviour, trivially passing tests, S1 keys and lifetimes, labels / launcher / TSan env | (1) self-checks labelled `unit` contradict AC-2 wording; (2) AC-3 (c) in process cannot fail (`HasFailure()` is blind inside gtest-spi too); (3) spec AC-3 evidence not amended. S1, CMake escaping, launcher list, ODR: none | (2) moved out of process (`ScenarioStepNonFatalContinues`), lead (small); (1), (3) spec History 2026-11-04 (DEV); TSan env added to the self-checks |
| U5 | codex luna (high) | races, lifetime, worker-thread asserts, line drift, AC-6 checks, flush | no race / lifetime problem; thread labels checked by substring only; redundant file-name check; (note) latch would block if the second thread failed to start | step 4 checks each `thread N failed: FileIOFailure` exactly once, lead (small); re-check by codex luna (medium): none |
| U6–U8 | cpp-reviewer | report written when required, step codes, exit code, rmtree safety, report.md vs §2.1, dead code | build.py: run.json write outside try, `%` in DIR, wording, dead code, `.git`/link not refused; test_report.py: `AllTests` matched every gtest file, paths relative to build/report folder, all backslashes converted, other absolute paths kept, malformed input raised, compiler folder text-sorted, one gtest total, duplicated loop | build.py fixes lead (small); test_report.py back to the author (agy flash `--resume`) |
| U6–U8 (round 2) | cpp-reviewer | earlier findings resolved? new problems? | resolved except: self-check items given AllTests' gtest file; URL inside text masked; paths with spaces / more POSIX roots; malformed nested gtest JSON; `.GIT` case on drvfs; import under `python -I`; dead `PathCleaner` params, duplicated case walk | all fixed by the lead (small): `assign_gtest_files` (scenario by case, others the next file of their program, tests with `GTEST_OUTPUT` unset get none), path regex with left boundary and spaced segments, shape check at load, case-insensitive `.git`, explicit `sys.path`; one round only (§6.3), no further review |
| U9 | lead | tests check their AC, can any pass trivially | read every new test; `test_main` extended for the optional `run.json` | — |
| U10 | lead | docs vs final code | README §3/§4.4 corrected by following them (run 14) | — |

## Final runs
(filled after the commit)
