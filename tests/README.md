# tests/ — running tests and reading test reports

This page is for people who run the tests by hand: which tests exist, how to run one kind, how to add a scenario, and how to get and read a test report. The rules agents follow are in [`.agent/rules/test.md`](../.agent/rules/test.md); the design is spec [040-02](../docs/specs/040_02_ctest_scenario_tests.md).

All commands run from the repository root. On Linux write `python3` instead of `py -3`. `build.py` builds first, so every command below also works after a code change. On a Windows host, Linux presets (`linux-x64-*`) run in WSL by themselves.

## 1. Three kinds of tests

| Kind (CTest label) | What it checks | Where | Name in CTest |
|---|---|---|---|
| `unit` | one component, one behaviour | `tests/<module>/test_<name>.cpp` → program `atugcc_tests` | `AllTests` (every unit test in one process), plus `ScenarioStepFatalStops`, `ScenarioStepNonFatalContinues`, `ScenarioStepFatalBefore` (the step helper's own failure checks, each in its own process) |
| `scenario` | one flow a library user goes through, in named steps, with public headers only | `tests/scenario/scenario_<flow>.cpp` → program `atugcc_scenarios` | `scenario.<Suite>.<Name>`, **one process per scenario** |
| `probe` | something that needs a process to crash, be killed, start again or get a special environment | a probe program plus a checking script (`tests/core/check_crash_dump.py` …) | its own name: `CrashDump`, `LogMap`, `TraceStream`, `DumpPrepare_*` … |

Lessons add their own tests: `lesson.<id>` with label `lesson` (and `long` for long-running ones).

Why scenarios get a process each: some library settings are made once per process (`configureLogBuffers`, the `ATUGCC_TRACE_OUT` sink, the crash dump target). A fresh process lets every scenario set them up from the start, and lets scenarios run in parallel.

## 2. Running tests

| I want to run | Command |
|---|---|
| everything (the task gate) | `py -3 .agent/scripts/build.py --preset <p> --test` |
| one kind | `py -3 .agent/scripts/build.py --preset <p> --label unit` (or `scenario`, `probe`, `lesson`) |
| two kinds | `py -3 .agent/scripts/build.py --preset <p> --label "unit\|scenario"` (the label is a regular expression) |
| some unit tests | `py -3 .agent/scripts/build.py --preset <p> --gtest-filter "Tracer*"` (GoogleTest filter, runs inside `AllTests`) |
| one scenario | `ctest --preset <p> -R "^scenario.LoggedErrorFlow"` (in a VS Developer prompt on Windows; inside WSL for Linux presets) |

`<p>` is a preset: `windows-x64-debug`, `linux-x64-debug`, `linux-x64-asan`, `linux-x64-tsan`, … (`auto` = this host's debug preset). The `ctest` lines work too once the preset is built: `ctest --preset <p> -L scenario`, `ctest --preset <p> -N -L probe` (list only).

A label that matches no test fails with `--label` (`No tests were found!!!`), so a typo does not look like a pass.

Do not start `out/build/<p>/bin/atugcc_scenarios` by hand without `--gtest_filter`: all scenarios would then share one process, which is the situation scenarios are meant to avoid.

## 3. Adding a scenario

1. Create `tests/scenario/scenario_<flow>.cpp`:
   ```cpp
   #include "scenario.hpp"

   #include <gtest/gtest.h>

   #include <memory>

   #include "atugcc/core/logger.hpp"   // public headers only

   TEST(MyFlow, WhatTheUserSees) {
       atugcc::test::Scenario s;
       std::unique_ptr<atugcc::core::Logger> logger;   // state shared by steps lives outside them

       s.step("open a logger that writes a file", [&] {
           atugcc::core::Logger::Config cfg;
           cfg.filePath = s.workDir() / "app.log";
           logger = std::make_unique<atugcc::core::Logger>(cfg);
       });
       s.step("the file has the line", [&] {
           ASSERT_NE(logger, nullptr);
           // ... read s.workDir() / "app.log", EXPECT_...
       });
   }
   ```
2. Add the file to the `atugcc_scenarios` list in [`tests/CMakeLists.txt`](CMakeLists.txt).
3. Build and run: `py -3 .agent/scripts/build.py --preset <p> --label scenario`. The new test appears as `scenario.MyFlow.WhatTheUserSees`.

What the step helper (`atugcc::test::Scenario`, [`scenario.hpp`](scenario/scenario.hpp)) does:
- prints `[step n] <name>` before each step; a failure inside a step carries `step n: <name>` in its message;
- after a fatal failure (`ASSERT_*`, `FAIL()`) the remaining steps print `[skip n] <name>` and do not run; `EXPECT_*` failures do not stop them;
- `step()` returns whether the step ended without a fatal failure;
- `s.workDir()` is `out/build/<p>/tests/scenario_work/<Suite>.<Name>/`, emptied when the scenario starts and **kept** afterwards, so after a failure you can look at the files the scenario wrote.

Threads: `ASSERT_*` on another thread does not stop the steps (GoogleTest tracks fatal failures per thread). Start and join threads inside one step, collect results into variables, and assert after the join. [`scenario_logged_error_flow.cpp`](scenario/scenario_logged_error_flow.cpp) shows the pattern.

## 4. Test reports

Add `--report` to any run that tests (`--test`, `--label` or `--gtest-filter`):

```text
py -3 .agent/scripts/build.py --preset linux-x64-debug --test --report
py -3 .agent/scripts/build.py --preset windows-x64-debug --label scenario --report
py -3 .agent/scripts/build.py --preset linux-x64-tsan --label unit --report out/test-reports/tsan-check
```

The last line names the folder: `report: out/test-reports/<preset>/<YYYYMMDD-HHMMSS>/report.md`. Without `DIR` a new folder is made per run; with `DIR` (relative to the repository root only) that folder is emptied and reused. The report is written **even when tests fail**, and the exit code is the same as without `--report`. If the build itself fails, no test ran and no report is written (the output says so).

Reports live under `out/` and are not committed. For a task's evidence, copy the command and the numbers and failures from `report.md` into the task's `testrecord.md`.

### 4.1 What is in the folder

| File | What | Use it for |
|---|---|---|
| `report.md` | the summary below | read this first |
| `run.json` | preset, command, start time, every step with its exit code (`null` = did not run) | which step failed |
| `tests.json` | `ctest --show-only=json-v1`: every registered test with its labels and command | how a test is started |
| `ctest-<n>.junit.xml` | one per ctest step (JUnit XML): every CTest test with status, time and its full output | a test's whole output |
| `gtest/*.json` | one per GoogleTest process (`atugcc_tests.json`, `atugcc_scenarios.json`, `atugcc_scenarios_1.json` …): every test case with its failure messages | which `Suite.Name` failed and why |

### 4.2 Reading `report.md`

A real report of `py -3 .agent/scripts/build.py --preset windows-x64-debug --test --report` (shortened):

````markdown
# Test report: windows-x64-debug

| | |
|---|---|
| Date | 2026-11-04T16:22:16 |
| Commit | 36066ac (uncommitted changes) |
| Compiler | MSVC 19.51.36260.0 |
| Command | `py -3 .agent/scripts/build.py --preset windows-x64-debug --test --report` |

## Steps
| # | Command | Exit code |
|---|---|---|
| 1 | `cmake --build --preset windows-x64-debug` | 0 |
| 2 | `ctest --preset windows-x64-debug --show-only=json-v1` | 0 |
| 3 | `ctest --preset windows-x64-debug --output-junit out/test-reports/windows-x64-debug/20261104-162216/ctest-1.junit.xml` | 0 |

## Results by label
| Label | Tests | Passed | Failed | Not run | Time (s) |
|---|---|---|---|---|---|
| unit | 4 | 4 | 0 | 0 | 26.71 |
| scenario | 2 | 2 | 0 | 0 | 0.10 |
| probe | 12 | 12 | 0 | 0 | 142.22 |
| lesson | 16 | 16 | 0 | 0 | 18.07 |
| long | 2 | 2 | 0 | 0 | 16.88 |
| **All** | 34 | 34 | 0 | 0 | 187.10 |

## Failures
(none)

## Slowest tests
| Test | Time (s) |
|---|---|
| CrashDump | 118.72 |
| AllTests | 26.63 |
| ...

## GoogleTest cases
| Program | Cases | Failed | Disabled |
|---|---|---|---|
| atugcc_scenarios.json | 1 | 0 | 0 |
| atugcc_scenarios_1.json | 1 | 0 | 0 |
| atugcc_tests.json | 140 | 0 | 3 |
| **All** | 142 | 0 | 3 |

## Inputs
- out/test-reports/windows-x64-debug/20261104-162216/run.json
- ...
````

Part by part:
1. **Header**: which preset, when, which commit (`uncommitted changes` = the working tree differs from that commit), which compiler, and the command to run it again.
2. **Steps**: every step `build.py` ran, with its exit code. `not run` means an earlier step failed (on a build error the test steps are `not run` and no report is written). Step 2 only lists the tests (for the labels).
3. **Results by label**: counts per kind. A test with two labels (`lesson` and `long`) counts in both rows, so **All** counts each test once and can be less than the sum. *Not run* = disabled or skipped by CTest. Time is the sum of the tests' times.
4. **Failures**: one section per failed CTest test. For a GoogleTest test it names the failing case and quotes its message; a scenario's message ends with the step (`Google Test trace: … step 4: the stream has the run in order`). For anything else (a probe, a crash, a timeout) it shows the last 30 lines of the test's output. Example from a run with a broken scenario:
   ````markdown
   ### scenario.TracedStateMachine.EventsReachStreamInOrder
   - `TracedStateMachine.EventsReachStreamInOrder`:
   ```
   tests/scenario/scenario_traced_state_machine.cpp:115
   Failed
   Value of: result
     Actual: false
   Expected: true
   Google Test trace:
   tests/scenario/scenario.hpp:73: step 4: the stream has the run in order
   ```
   ````
5. **Slowest tests**: the five longest CTest tests: where the suite's time goes.
6. **GoogleTest cases**: one row per GoogleTest process: `atugcc_tests.json` is `AllTests` (the same count as `atugcc_tests --gtest_list_tests`), each `atugcc_scenarios*.json` one scenario. *Disabled* counts `DISABLED_` tests (the step helper's self-checks, run separately).
7. **Inputs**: the files the summary was made from; `could not read: <file>` marks a broken one (for example a process that crashed while writing its JSON).

Paths in `report.md` are relative to the repository root; a path outside the repository (a system header, a temp file) is shortened to `<abs>/<file name>`. The XML and JSON files keep the absolute paths the tools wrote.

### 4.3 When something failed

1. **Failures** in `report.md`: the CTest test, and for GoogleTest the failing `Suite.Name` with its message. A scenario's message names the step (`step 4: the stream has the run in order`), and the steps after it show as `[skip n]`.
2. No GoogleTest message (the process crashed or timed out, or it is a probe): `report.md` shows the last 30 lines of the test's output; the whole output is in `ctest-<n>.junit.xml` (`<system-out>` of that `<testcase>`).
3. A scenario: look at its files in `out/build/<p>/tests/scenario_work/<Suite>.<Name>/`.
4. Run it alone again: `ctest --preset <p> -R "^scenario.<Suite>.<Name>$" --output-on-failure`, or for a unit test `py -3 .agent/scripts/build.py --preset <p> --gtest-filter "<Suite>.<Name>"`.

### 4.4 A report for a run made without build.py

`test_report.py` only reads files, so it can summarise any run that wrote the same files:

```text
cd out/build/linux-x64-debug
mkdir -p ../../test-reports/manual
ctest --show-only=json-v1 > ../../test-reports/manual/tests.json
GTEST_OUTPUT=json:$PWD/../../test-reports/manual/gtest/ ctest -L scenario --output-junit $PWD/../../test-reports/manual/ctest-1.junit.xml
cd ../../..
py -3 .agent/scripts/test_report.py out/test-reports/manual
```

Without `run.json` the header and the Steps table say `unknown`, and Inputs lists `could not read: run.json`. At least one `ctest-*.junit.xml` must be there.

## 5. Common surprises

| What you see | Why |
|---|---|
| `No tests were found!!!` and exit 8 with `--label` | the label matches no test (typo, or the preset does not build that kind: `linux-x64-playground` builds no tests) |
| `--report needs --test, --label or --gtest-filter` | `--report` only reports test runs |
| `--report takes a path relative to the repository root` | `DIR` was absolute; it must also work inside WSL |
| `--report <DIR> exists and is not an earlier test report` | `DIR` is emptied before the run, so only an empty folder or an earlier report (it has `run.json`) is reused; the repository itself, folders outside it, `.git`, links and paths with `%` or `"` are refused |
| test commands on `linux-x64-tsan` start with `setarch … -R` | ThreadSanitizer needs ASLR off on current kernels; CMake adds it to every test, scenarios included |
| GoogleTest totals in `report.md` count more cases than `AllTests` alone | scenario processes and lessons add their own; the three step-helper self-checks write no JSON on purpose (their failures are planned) |
