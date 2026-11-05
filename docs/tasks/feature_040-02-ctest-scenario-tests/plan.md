# Plan: 040-02 CTest 시나리오 테스트와 테스트 리포트

- Spec: [/docs/specs/040_02_ctest_scenario_tests.md](/docs/specs/040_02_ctest_scenario_tests.md) (approved 2026-11-04)
- Branch: `feature/040-02-ctest-scenario-tests` (from `main` at `36066ac`)

## Model assignment
Default [delegation.md](/.agent/rules/delegation.md) §1: agy `flash` writes code, test and tool units; `cpp-reviewer` reviews ordinary units; risky units get codex `luna` first. The lead writes doc units and `lead (small)` changes.

## Design

### Files
- [NEW] `tests/scenario/scenario.hpp`, `tests/scenario/test_scenario_step.cpp` (in `atugcc_tests`)
- [NEW] `tests/scenario/scenario_traced_state_machine.cpp`, `tests/scenario/scenario_logged_error_flow.cpp` (in `atugcc_scenarios`)
- [MODIFY] `tests/CMakeLists.txt`
- [MODIFY] `.agent/scripts/build.py`, `.agent/scripts/test_agent_scripts.py`; [NEW] `.agent/scripts/test_report.py`
- [NEW] `tests/README.md`; [MODIFY] `.agent/rules/test.md`, `.agent/rules/config.md`, `docs/agent_start_prompt.md`, `docs/specs/00_template.md`, `README.md`, `docs/tasks/agent_todo.md`

### `scenario.hpp` (spec §2.1, §2.2; Assumptions 5, 6)
- `#pragma once`; includes `<gtest/gtest.h>`, `<concepts>`, `<cstddef>`, `<filesystem>`, `<iostream>`, `<string>`, `<string_view>`, `<utility>`.
- `namespace atugcc::test { class Scenario { ... }; }`, all members defined in the class.
- Work root: macro `ATUGCC_SCENARIO_WORK_ROOT` (string literal, set by CMake on both targets). If undefined: `#error`.
- Constructor: name = `<test_suite_name>.<name>` of `::testing::UnitTest::GetInstance()->current_test_info()` with `/` → `_`; `workDir_ = path(ATUGCC_SCENARIO_WORK_ROOT) / name`; `remove_all` then `create_directories` (error_code overloads; failure → `ADD_FAILURE()` with the path and message).
- `step(name, fn)`: `++index_`. If `stopped_`: print `[skip <n>] <name>` to `std::cout`, return false. Else print `[step <n>] <name>`, `{ SCOPED_TRACE(std::format("step {}: {}", n, name)); std::forward<F>(fn)(); }`, then `if (::testing::Test::HasFatalFailure()) { stopped_ = true; return false; } return true;`.
  - Note: `HasFatalFailure()` is true after any earlier fatal failure in the test, so a fatal failure *before* the first step also stops every step. That is intended.
- No static state, not copyable (`= delete`), not movable.

### `ScenarioStepTest` (AC-3) in `test_scenario_step.cpp`
gtest-spi `EXPECT_FATAL_FAILURE` / `EXPECT_NONFATAL_FAILURE` take a statement that cannot use locals → statements call file-static helper functions that run a whole `Scenario` and record into file-static counters.
- (a) failure message contains `step 2: second` (`EXPECT_NONFATAL_FAILURE(..., "step 2: second")`).
- (b) cannot be checked in process: inside `EXPECT_FATAL_FAILURE` the failure goes to gtest-spi's fake reporter, not to the test result, so `HasFatalFailure()` is false and the helper does not stop (found while planning). Instead: `TEST(ScenarioStepSelfRun, DISABLED_FatalStopsLaterSteps)` (step 1 `FAIL() << "planned"`, step 2 prints `BODY2_RAN`; after both, prints `returns=<r1>,<r2>`), run by its own CTest test `ScenarioStepFatalStops` = `atugcc_tests --gtest_also_run_disabled_tests --gtest_filter=ScenarioStepSelfRun.DISABLED_FatalStopsLaterSteps` with `PASS_REGULAR_EXPRESSION` `step 1: first.*\[skip 2\] second.*returns=false,false` and `FAIL_REGULAR_EXPRESSION` `BODY2_RAN`, label `unit`. Also a fatal failure before the first step (the helper's pre-check): `DISABLED_FatalBeforeFirstStep`, CTest `ScenarioStepFatalBefore`, pass regex `\[skip 1\] first`, fail regex `BODY1_RAN`.
- (c) moved out of process too (cpp-reviewer: inside `EXPECT_NONFATAL_FAILURE` `HasFailure()` is also blind, so the in-process test could not fail): `DISABLED_NonFatalDoesNotStopLaterSteps`, CTest `ScenarioStepNonFatalContinues`, pass regex `step 1: first.*\[step 2\] second.*BODY2_RAN.*returns=true,true`, fail regex `\[skip`.
- (d) success → `step` returns true; output `[step 1] first`.
- (e) a file put in `workDir()` by one `Scenario` is gone after constructing another `Scenario` in the same test (same name → same dir); the dir exists and is empty.

### Scenarios (spec §2.2; AC-5, AC-6)
- S1 `TracedStateMachine.EventsReachStreamInOrder`: local `viz::Tracer` (not the global one) with `setEventSink(JsonLinesEventSink::open(workDir()/"trace.jsonl"))`; `state::Machine m(tracer)`; target order IDLE → STANDBY → RUN → STANDBY → ABORT → IDLE (all allowed), each `transition` inside a `viz::ScopedSpan` (label `transition <to>`), `ASSERT_TRUE(result)`. Tracer in its own scope so the destructor emits the diagram parts. Step 4 reads lines and checks: the transition lines' from/to equal the list in order; `seq` strictly increasing over all lines that carry it; span lines = 5; the last line is a diagram part. Exact JSON keys from `event_stream.hpp` (`toJsonLine`), parsed with string search (no JSON library in tests).
- S2 `LoggedErrorFlow.ErrorFromTwoThreadsReachesFile`: `configureLogBuffers({.mappedDir = workDir()/"map"})` must succeed; `Logger` with `filePath = workDir()/"app.log"`, `enableCrashDump = false`, `dumpDir = workDir()/"dump"`; a file-local function `openConfig()` returning `core::Expected<int>` = `std::unexpected(CoreError::FileIOFailure)`; two `std::jthread`s line up on a `std::latch`, each calls it and logs `"thread {} failed: {}"` with `core::to_string(error)`; join inside step 3; `flush()`; the log file has exactly two lines with `FileIOFailure`, each with `scenario_logged_error_flow.cpp` and the line number of the `log` call (captured with `std::source_location::current().line()` next to the call). Risky: threads (§3).

### `tests/CMakeLists.txt` (spec §2.2; AC-1, AC-2, AC-7)
- `test_scenario_step.cpp` into `TEST_SOURCES`; `ATUGCC_SCENARIO_WORK_ROOT` on `atugcc_tests` and `atugcc_scenarios`.
- `atugcc_scenarios` block per spec §2.2; `include(GoogleTest)`.
- Labels per Assumption 4.

### build.py (spec §2.1, §2.2; AC-8, AC-12, AC-13)
- `--label <L>`: refused characters as `--gtest-filter` (`bad_value(name, value)`); `build_steps(..., label)`: the label step replaces the `--test` step; forwarded to WSL.
- `--report [DIR]`: `nargs="?"`, const = default; default dir `out/test-reports/<preset>/<YYYYMMDD-HHMMSS>` computed once in the outer process and forwarded as a relative path; absolute → exit 2; no ctest step → exit 2. Steps get `--output-junit <abs>/ctest-<n>.junit.xml` and env `GTEST_OUTPUT=json:<abs>/gtest/`; a `ctest --preset p --show-only=json-v1` step whose stdout goes to `tests.json` (a step kind with an output file: Linux/WSL path in Python; on Windows a batch redirection `> "<file>"`). The directory is emptied first. After `run`/batch (any exit code): if any ctest step ran → `test_report.write_report(...)`, print `report: <rel>/report.md`; else print that no report was written. Exit code unchanged.
- `test_report.py`: `write_report(report_dir, *, preset, command, step_codes, build_dir, repo_root) -> Path`; CLI `test_report.py <DIR>` (reads `tests.json`, `ctest-*.junit.xml`, `gtest/*.json`; preset and command from a small `run.json` that build.py writes before the steps).

## Units
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `tests/scenario/scenario.hpp` | step helper (§2.1; AC-3) | builds with U2; `grep -c "HasFatalFailure"` = 3 | no | lead (small) | cpp-reviewer: none | — | done |
| U2 | `tests/scenario/test_scenario_step.cpp` (+ `TEST_SOURCES` line, lead) | `ScenarioStepTest` + `ScenarioStepSelfRun` (AC-3) | `ctest -L unit` both presets; mutation run (testrecord run 4) | no | agy flash | cpp-reviewer: (c) could not fail → moved out of process, lead (small) | 84k / 21k | done |
| U3 | `tests/scenario/scenario_traced_state_machine.cpp` | S1 (AC-5) | passes both presets, tsan, asan; broken copy fails in step 4 | no | agy flash | cpp-reviewer: none; repeated transition blocks → loop, lead (small) | 113k / 23k | done |
| U4 | `tests/CMakeLists.txt` | scenarios exe, discovery, launcher, env, labels, step self-checks (AC-1, AC-2, AC-7) | `ctest -N -L scenario/unit/probe`; label script | no | lead (small) | cpp-reviewer: labels vs AC-2 wording → spec History | — | done |
| U5 | `tests/scenario/scenario_logged_error_flow.cpp` (+ list line, lead) | S2 (AC-6) | passes both presets, tsan, asan | yes (threads) | agy flash | codex luna (high): substring thread checks → review fixes lead (small); re-check codex luna: none | 176k / 34k (review 175k / 4k, 59k / 1k) | done |
| U6 | `.agent/scripts/build.py` | `--label` (AC-8) | `--dry-run`; `--label nosuchlabel` exit 8 | no | lead (small) | cpp-reviewer (with U8): none | — | done |
| U7 | `.agent/scripts/test_report.py` | report writer (§2.1; AC-13) | real report dirs, 0 absolute paths | no | agy flash | cpp-reviewer: 9 findings → agy flash `--resume`; round 2 → review fixes lead (small) | 221k / 62k (+ 305k / 101k) | done |
| U8 | `.agent/scripts/build.py` | `--report` (§2.2; AC-11–AC-13) | `--dry-run`; real runs both presets | no | agy flash | cpp-reviewer: safety, exit code, dead code → review fixes lead (small) (`report_dir_problem`, `read_step_codes`, `finish_report`) | 228k / 75k | done |
| U9 | `.agent/scripts/test_agent_scripts.py` | tests for `--label`, `--report`, `test_report.py` (AC-8, AC-13) | 70 tests OK | no | agy flash | lead read the tests; `test_main` extended, lead (small) | 154k / 43k | done |
| U10 | §8 documents + `naming_check.py` `ALLOWED` | docs (AC-14) | `lint_docs.py` 0; README followed (testrecord run 14) | no | lead | lead (following the README) | — | done |
| U11 | `agent_todo.md` | states | lint | no | lead | — | — | |

## Verification (spec §12)
See spec §12; evidence goes to `testrecord.md`.
