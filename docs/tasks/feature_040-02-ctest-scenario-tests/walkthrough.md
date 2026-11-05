# Walkthrough: 040-02 CTest 시나리오 테스트와 테스트 리포트

- Spec: [/docs/specs/040_02_ctest_scenario_tests.md](/docs/specs/040_02_ctest_scenario_tests.md) (approved 2026-11-04, amendments in its History)
- Evidence: [testrecord.md](testrecord.md) (every AC with its run or test, reviews)
- Branch: `feature/040-02-ctest-scenario-tests`

## Result
- **Scenario tests**: `tests/scenario/scenario_<flow>.cpp` build into `atugcc_scenarios`; `gtest_discover_tests` registers one CTest test and one process per scenario, `scenario.<Suite>.<Name>`, label `scenario`, with the TSan launcher and suppressions. First scenarios: `TracedStateMachine.EventsReachStreamInOrder` (State pattern + Tracer + spans + JSON Lines) and `LoggedErrorFlow.ErrorFromTwoThreadsReachesFile` (`Expected` error + `Logger` + process-wide `configureLogBuffers`, two threads).
- **Step helper** `atugcc::test::Scenario` ([`scenario.hpp`](/tests/scenario/scenario.hpp)): `[step n]` / `[skip n]` lines, `step n: <name>` in failure messages, stop after a fatal failure, fresh `workDir()` per scenario. What a failure does to later steps is checked out of process (`ScenarioStepFatalStops`, `ScenarioStepNonFatalContinues`, `ScenarioStepFatalBefore`), because gtest-spi hides the failure from `HasFatalFailure()` / `HasFailure()`.
- **Test kinds**: every test in `tests/` has `unit`, `scenario` or `probe`; lessons keep `lesson` / `long`.
- **`build.py --label <L>`** runs one kind (`--no-tests=error`), **`build.py --report [DIR]`** writes `out/test-reports/<preset>/<time>/` (JUnit, gtest JSON, `tests.json`, `run.json`, `report.md` by [`test_report.py`](/.agent/scripts/test_report.py)) even when tests fail. DIR is checked before it is emptied (inside the repository, not `.git`, not a link, empty or an earlier report).
- **Docs**: [`tests/README.md`](/tests/README.md) (how to run, add a scenario, read a report), [test.md](/.agent/rules/test.md) §2 and §6, [config.md](/.agent/rules/config.md) §1, README, quick reference, spec template; `agent_todo.md` common principle: pattern and engine tasks add a scenario.
- Full suites: 34/34 on `windows-x64-debug` and `linux-x64-debug`; unit + scenario 6/6 on `linux-x64-tsan` and `linux-x64-asan`.

## Changes against the approved spec (spec History, 2026-11-04 DEV)
- AC-3 (b), (c): verified by deliberately failing `DISABLED_` tests run by CTest, not in process; these self-checks carry `unit`, so `-L unit` is `AllTests` plus the three.
- Report: compiler read from `CMakeFiles/<version>/CMakeCXXCompiler.cmake`; DIR safety rules; GoogleTest table per program; paths outside the repository shortened to `<abs>/<name>`; `test_report.py <DIR>` needs a JUnit file, `run.json` is optional.

## Follow-ups
- [KI-041](/docs/known_issues.md): report folders accumulate; no cross-run view.
- 070-15 (BACKLOG): a lesson on writing tests and reading reports.

## Notes
- No `lead (fallback)` units. Review fixes by the lead are listed in the plan's unit table.
- During the safety check a command ran with the not-yet-fixed build.py and created `a%b/` in the repository root (removed; see testrecord "Failures and retries").
