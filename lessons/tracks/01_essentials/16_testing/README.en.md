# Lesson: testing — GoogleTest unit tests, step scenarios, and reading a test report (`testing`)

This lesson is a tutorial to follow along. You write tests for a small version parser ([`version.hpp`](version.hpp)), break them on purpose, and read the failures in the console, in the editor and in a test report. By the end you can:

- Write unit tests with GoogleTest: `TEST`, `EXPECT`/`ASSERT`, fixtures (`TEST_F`), table tests (`TEST_P`), and showing values in failure messages (`PrintTo`).
- Write a scenario with this project's step helper: `[step n]`, `[skip n]`, `workDir()`.
- Pick and run tests of a test program with options: `--gtest_filter`, `--gtest_repeat`, `--gtest_shuffle`, `--gtest_output`.
- Use CTest to pick the project's tests, look at failures again, repeat them and run them side by side: `-N`, `-R`, `-L`, `--output-on-failure`, `--rerun-failed`, `--repeat`, `-j`.
- Find what broke and why in the `report.md` that `build.py --report` writes.

## Files and running
| File | What it does |
|---|---|
| [`version.hpp`](version.hpp) | the code under test: `Version`, `parseVersion`, `newestVersion`, `PrintTo` |
| [`test_version.cpp`](test_version.cpp) | unit tests (A1–A5) |
| [`scenario_version_file.cpp`](scenario_version_file.cpp) | scenario: version file → parse → `Logger` → log file (A6) |
| [`main.cpp`](main.cpp) | entry point: `InitGoogleTest` and `RUN_ALL_TESTS` (A1, A7) |

The one line `gtest = true` in `lesson.toml` links GoogleTest into this lesson and lets it use the step helper [`scenario.hpp`](/tests/scenario/scenario.hpp) from `tests/scenario/` ([`lessons/README.md`](/lessons/README.md)).

- 🌐 **Web playground**: pick `testing` in the lesson tree and Run. Run saves the files you changed and builds again. You cannot pass program arguments (A7 shows what to do instead).
- 💻 **Locally**: `py -3 .agent/scripts/build.py --preset <preset> --target lesson_testing` (Linux: `python3`), then run `out/build/<preset>/bin/lessons/lesson_testing` (Windows: `.exe`). `<preset>` is `windows-x64-debug` or `linux-x64-debug`. On a Windows host the `linux-x64-*` presets build inside WSL.

The output in this page comes from real runs; the repository location is shortened to `<repo>`. Times (`(0 ms)`) differ from run to run.

### `assert` and a test framework
| | `assert(x)` / a hand-written `if` | GoogleTest |
|---|---|---|
| On a failure | the program ends at the first one (`abort`) | records that check as failed and goes on to the next check and the next test |
| What broke | file, line, expression | test name, file, line, expression, **both values** |
| Release builds | gone under `NDEBUG` | runs in every build type |
| Running some | not possible | `--gtest_filter`, CTest `-R`/`-L` |
| Results a machine reads | exit code only | exit code + JSON/XML result files |

## A. GoogleTest

### A1. A first test and `main`
One test is one `TEST(Suite, Name)` block. The names show up as they are in results and filters, so name what the test checks (`ParseVersion.ReadsThreeNumbers`). GoogleTest asks for no underscores `_` in the names (they can clash with names it makes internally).

```cpp
TEST(ParseVersion, ReadsThreeNumbers) {
    const auto result = parseVersion("1.2.3");
    ASSERT_TRUE(result) << "error: " << core::to_string(result.error());
    EXPECT_EQ(result->major, 1u);
    EXPECT_EQ(result->minor, 2u);
    EXPECT_EQ(result->patch, 3u);
}
```

`main` has no list of tests. Global objects made by `TEST` register the tests before `main`, and `RUN_ALL_TESTS()` runs everything registered. It returns 0 when every test passed and 1 when any failed, and that value is the program's exit code. CTest and the web decide pass or fail by this exit code. Linking the `gtest_main` library writes this `main` for you (then one more line, `Running main() from …`, is printed).

```cpp
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
```

**Try it** 🌐💻: run it as it is.

**What you see**: `[ RUN ]`/`[ OK ]` per test, `[----------]` per suite, and a summary at the end. The `[step n]` lines of the scenario come from the step helper (A6).
```text
[==========] Running 13 tests from 6 test suites.
[----------] Global test environment set-up.
[----------] 1 test from ParseVersion
[ RUN      ] ParseVersion.ReadsThreeNumbers
[       OK ] ParseVersion.ReadsThreeNumbers (0 ms)
[----------] 1 test from ParseVersion (0 ms total)
...
[----------] 7 tests from Table/ParseVersionRejects
[ RUN      ] Table/ParseVersionRejects.BadText/0
[       OK ] Table/ParseVersionRejects.BadText/0 (0 ms)
...
[==========] 13 tests from 6 test suites ran. (16 ms total)
[  PASSED  ] 13 tests.
```

### A2. `EXPECT` and `ASSERT`
Every comparison comes in two forms.
- `EXPECT_*`: records the failure and **goes on**. Use it to check several values at once.
- `ASSERT_*`: records the failure and **returns from the test function at once**. Use it when later lines depend on the result. `ASSERT_TRUE(result)` above is the example: reading `result->major` after a failed parse is undefined behaviour.

The common ones:

| Macro (both `EXPECT_` and `ASSERT_` exist) | True when |
|---|---|
| `TRUE(c)`, `FALSE(c)` | `c` is true / false (works with `std::expected`, `std::optional`) |
| `EQ(a, b)`, `NE(a, b)` | `a == b` / `a != b` |
| `LT`, `LE`, `GT`, `GE` | `<`, `<=`, `>`, `>=` |
| `STREQ(a, b)` | the C strings have the same content (`EQ` on `const char*` compares addresses) |
| `DOUBLE_EQ(a, b)`, `NEAR(a, b, eps)` | floating point within 4 ULP / difference at most `eps` |
| `THROW(stmt, E)`, `NO_THROW(stmt)` | `stmt` throws `E` / throws nothing |

Any of them takes an explanation with `<<`, which is evaluated only on a failure (`ASSERT_TRUE(result) << "error: " << …`).

Why `1u`: the fields of `Version` are `unsigned`. `EXPECT_EQ(result->major, 1)` compares `unsigned` with `int` inside the GoogleTest template, which is a `-Wsign-compare` warning, and this project treats warnings as errors. Match the type of the expected value.

**Try it** 🌐💻: in `ReadsThreeNumbers` of [`test_version.cpp`](test_version.cpp), make two expected values wrong: `EXPECT_EQ(result->minor, 5u);`, `EXPECT_EQ(result->patch, 7u);`. Run, then change only the first line to `ASSERT_EQ(result->minor, 5u);` and run again.

**What you see**: with two `EXPECT`s there are **two** failures (lines 36 and 37); with an `ASSERT` first there is **one** (line 36). Line 37 was never checked because `ASSERT` returned. Both times there is a single `[  FAILED  ] ParseVersion.ReadsThreeNumbers` and exit code 1.
```text
<repo>\lessons\tracks\01_essentials\16_testing\test_version.cpp(36): error: Expected equality of these values:
  result->minor
    Which is: 2
  5u
    Which is: 5

<repo>\lessons\tracks\01_essentials\16_testing\test_version.cpp(37): error: Expected equality of these values:
  result->patch
    Which is: 3
  7u
    Which is: 7

[  FAILED  ] ParseVersion.ReadsThreeNumbers (0 ms)
```
In the web and on Linux (Clang) the same failure starts like this: `<repo>/lessons/tracks/01_essentials/16_testing/test_version.cpp:36: Failure`, then `Expected equality of these values:` on the next line.
In the web the failed lines (36, 37) get a red marker, and hovering shows the message. Undo the change before the next section.

### A3. Reading a failure message, `PrintTo`
A message always has the same shape: `file(line)` (MSVC) or `file:line: Failure` (Clang, GCC), then the **text of each expression** and **its value**.
```text
Expected equality of these values:
  *newer                 ← text of the first argument
    Which is: 1.10.0     ← its value
  (Version{1, 9, 0})     ← text of the second argument
    Which is: 1.9.0
```
GoogleTest finds the way to turn a value into text: `PrintTo(const T&, std::ostream*)` in the same namespace (ADL) if there is one, else `operator<<`. With both, `PrintTo` wins. With neither, it prints the object's bytes. The `PrintTo` in `version.hpp` makes a `Version` show as `1.10.0`. A type GoogleTest does not know, such as `Expected<Version>`, prints as bytes, so compare after taking the value out, as in `*newer`.

The parentheses in `(Version{1, 9, 0})`: the preprocessor splits macro arguments at commas inside `{}` too. Parentheses make it one argument.

Why a macro and not a function: the failure's place (file and line) can also come from C++20 `std::source_location` ([05_source_location](../05_source_location/README.en.md)), but only the preprocessor's `#` can make the text of an expression (`*newer`), and the "return from the test function" of `ASSERT` cannot be done by a function call.

**Try it** 🌐💻: in `VersionOrder.ComparesNumbersNotText`, change `EXPECT_EQ(*newer, (Version{1, 10, 0}));` to `(Version{1, 9, 0})` and run. Then delete the whole `PrintTo` function from `version.hpp` and run again.

**What you see**: with `PrintTo` it says `Which is: 1.10.0`; without it, a byte dump (`0A` is 10, `09` is 9).
```text
  *newer
    Which is: 12-byte object <01-00 00-00 0A-00 00-00 00-00 00-00>
  (Version{1, 9, 0})
    Which is: 12-byte object <01-00 00-00 09-00 00-00 00-00 00-00>
```
Undo the changes.

### A4. Fixtures: `TEST_F`
When several tests need the same setup, put it in a fixture class. Derive from `::testing::Test`, set up in `SetUp()`, clean up in `TearDown()` (not needed in this lesson), and write the tests as `TEST_F(Class, Name)` instead of `TEST(…)`. A test body uses the fixture's `protected` members directly.

```cpp
class ReleaseListTest : public ::testing::Test {
protected:
    void SetUp() override;           // puts "1.2.0", "1.10.0", "1.9.3" into releases_
    std::vector<Version> releases_;
};

TEST_F(ReleaseListTest, SortsAscending) {
    std::ranges::sort(releases_);
    ASSERT_EQ(releases_.size(), 3u);
    EXPECT_EQ(releases_.front(), (Version{1, 2, 0}));
    EXPECT_EQ(releases_.back(), (Version{1, 10, 0}));
}
```

- **A new fixture object for every test.** `SortsAscending` sorting `releases_` leaves `NewestIsHighest` with a fresh, unsorted list. This keeps tests from depending on their order (check it with `--gtest_shuffle` in A7).
- If `FAIL()` or an `ASSERT_*` fails in `SetUp`, the test body does not run.
- When to use a fixture: the same setup appears in two or more tests, or a cleanup (`TearDown`) must always run. Setup used by one test only stays in that test.

**Try it** 🌐💻: add one more text, `"2.0"`, to the list in `SetUp` (and make the array size 4) and run.

**What you see**: both tests of `ReleaseListTest` fail with `cannot parse 2.0`, and the checks in the bodies (`size() == 3` of `SortsAscending`) do not appear. Undo the change.

### A5. Table tests: `TEST_P`
Use it to run the same check with different inputs. Each row becomes one named test, so the result shows which input broke.

```cpp
class ParseVersionRejects : public ::testing::TestWithParam<std::string_view> {};

TEST_P(ParseVersionRejects, BadText) {
    const auto result = parseVersion(GetParam());
    ASSERT_FALSE(result) << "accepted: " << GetParam();
    EXPECT_EQ(result.error(), core::CoreError::InvalidArgument);
}

INSTANTIATE_TEST_SUITE_P(Table, ParseVersionRejects,
    ::testing::Values("", "1.2", "1.2.3.4", "1.x.3", "-1.2.3", "1..3", "99999999999.0.0"));
```

The names are `<INSTANTIATE name>/<class>.<test>/<row number>`: `Table/ParseVersionRejects.BadText/3` is the `"1.x.3"` row. `--gtest_list_tests` shows the value of each row (A7). Besides `::testing::Values`, the values can come from `ValuesIn(container)`, `Range` and `Combine`.

**Try it** 🌐💻: add `"1.2.3"` at the end of `Values(…)`. It is a valid version, so the "must be rejected" check has to fail.

**What you see**: only the new row `/7` fails, and the failure line carries its value. Undo the change.
```text
<repo>\lessons\tracks\01_essentials\16_testing\test_version.cpp(50): error: Value of: result
  Actual: true
Expected: false
accepted: 1.2.3

[  FAILED  ] Table/ParseVersionRejects.BadText/7, where GetParam() = "1.2.3" (0 ms)
```

### A6. Step scenarios
A unit test looks at one part; a scenario looks at **one flow** a user goes through. This project writes scenarios in named steps ([`tests/README.md`](/tests/README.md) §3, helper [`scenario.hpp`](/tests/scenario/scenario.hpp)). This lesson's [`scenario_version_file.cpp`](scenario_version_file.cpp):

```cpp
TEST(VersionFileFlow, BadVersionIsLogged) {
    atugcc::test::Scenario s;
    std::unique_ptr<core::Logger> logger;   // state the next step uses lives outside the steps

    s.step("write a version file with a bad line", [&] { /* "1.2" into workDir()/version.txt */ });
    s.step("open a logger that writes a file",     [&] { /* filePath = workDir()/app.log */ });
    s.step("parse the file: the error is logged",  [&] { /* ASSERT_FALSE(result), logger->log(...) */ });
    s.step("the log file has the error line",      [&] { /* after flush(), look in app.log */ });
}
```

- Each step prints `[step n] <name>`, and failure messages inside a step carry `step n: <name>`.
- When an `ASSERT_*` fails inside a step, the remaining steps print `[skip n]` and do not run. An `EXPECT_*` failure does not stop the next steps.
- A step is a lambda. Values the next step needs (`logger`) live in variables outside the steps.
- `s.workDir()` is a folder of its own per scenario: `out/build/<preset>/lessons/scenario_work/VersionFileFlow.BadVersionIsLogged/`. It is emptied at the start and **kept** at the end, so after a failure you can open the files.
- An `ASSERT_*` on another thread cannot stop the steps. Start and join threads inside one step and check in that step ([`tests/README.md`](/tests/README.md) §3).

**The lesson and `tests/` differ**: in this lesson the unit tests and the scenario run in one process. So this scenario does not touch the settings made once per process (`configureLogBuffers`, `ATUGCC_TRACE_OUT`, the crash dump target). The scenarios in `tests/` exist to set up such things from the start, so they run **one process per scenario** (`gtest_discover_tests` in B2).

| | This lesson | `tests/scenario/` |
|---|---|---|
| Program | one, `lesson_testing` | `atugcc_scenarios` |
| Processes | 13 tests in one process | one per scenario |
| CTest tests | one, `lesson.testing` | `scenario.<Suite>.<Name>` per scenario |
| Process-wide settings | not used | from the start in every scenario |

**Try it** 🌐💻: change what step 1 writes to `"1.2.3\n"`. It is a valid version, so step 3's `ASSERT_FALSE(result)` fails. 💻 Locally, open `version.txt` in the `workDir()` folder afterwards.

**What you see**: `Google Test trace:` at the end of the failure message names the step, and step 4 is `[skip 4]`. In the web the `ASSERT_FALSE` line of `scenario_version_file.cpp` gets a marker. Undo the change.
```text
[step 1] write a version file with a bad line
[step 2] open a logger that writes a file
[step 3] parse the file: the error is logged
<repo>\lessons\tracks\01_essentials\16_testing\scenario_version_file.cpp(71): error: Value of: result
  Actual: true
Expected: false
accepted: 1.2.3
Google Test trace:
<repo>\tests\scenario\scenario.hpp(73): step 3: parse the file: the error is logged

[skip 4] the log file has the error line
[  FAILED  ] VersionFileFlow.BadVersionIsLogged (12 ms)
```

### A7. Run options
Every GoogleTest program takes the same options. 💻 Locally, put them after the executable (`<exe>` = `out/build/<preset>/bin/lessons/lesson_testing`).

| Option | What it does |
|---|---|
| `--gtest_list_tests` | names only, no run (table rows with their values) |
| `--gtest_filter=<pattern>` | only names that match. `*` `?` wildcards, `:` for several, after `-` the ones to leave out |
| `--gtest_repeat=<n>` | repeat n times (`-1` forever). Finding a test that fails only sometimes |
| `--gtest_shuffle`, `--gtest_random_seed=<n>` | shuffle the order. The same seed gives the same order |
| `--gtest_break_on_failure` | make the debugger stop at the first failure |
| `--gtest_brief=1` | only failed tests and the summary |
| `--gtest_output=json:<file or folder/>` | results as JSON (`xml:` gives JUnit-style XML) |
| `--gtest_also_run_disabled_tests` | also the tests switched off by a name starting with `DISABLED_` |

Every option except `--gtest_list_tests` also comes as an environment variable: `--gtest_filter` is `GTEST_FILTER`, `--gtest_output` is `GTEST_OUTPUT`: a `GTEST_` prefix, upper case. Environment variables become the defaults before `main`, and command-line options win over them. `build.py --report` gets its result files through `GTEST_OUTPUT` (C).

**Try it** 💻:
```text
<exe> --gtest_list_tests
<exe> --gtest_filter=ParseVersion*
<exe> --gtest_filter=*-Table/*:VersionFileFlow.*
<exe> --gtest_filter=ReleaseListTest.* --gtest_repeat=2
<exe> --gtest_shuffle --gtest_random_seed=7
<exe> --gtest_brief=1
<exe> --gtest_filter=NewestVersion.* --gtest_output=json:out/one.json
```

**What you see**:
- The list: `# GetParam() = …` for each table row.
  ```text
  ReleaseListTest.
    NewestIsHighest
    SortsAscending
  ...
  Table/ParseVersionRejects.
    BadText/0  # GetParam() = ""
    BadText/1  # GetParam() = "1.2"
  ```
- A filter prints `Note: Google Test filter = …` first. `ParseVersion*` is 1 test (the rows of `ParseVersionRejects` do not match, since their suite name starts with `Table/…`); `*-Table/*:VersionFileFlow.*` is the 5 tests left without the table and the scenario.
- `--gtest_repeat=2`: `Repeating all tests (iteration 1) . . .`, then `(iteration 2)`.
- `--gtest_shuffle`: `Note: Randomizing tests' orders with a seed of 7 .` and then the shuffled order. Because the fixture is new for every test, it passes in any order.
- `--gtest_brief=1`: the lines of passed tests go away and the summary stays (the scenario's `[step n]` lines stay, since the lesson prints them itself).
- JSON: per test `file`, `line`, `status`, `result`, and a `failures` array on a failure; per suite the counts (`tests`, `failures`, `disabled`) and the time.

🌐 The web cannot pass program arguments, so try it in [`main.cpp`](main.cpp) on the line after `InitGoogleTest` (remove it afterwards):
```cpp
    ::testing::InitGoogleTest(&argc, argv);
    GTEST_FLAG_SET(filter, "ReleaseListTest.*");
```
The option name without `--gtest_` is the first argument of `GTEST_FLAG_SET`. In this place (after `InitGoogleTest`) only the options `RUN_ALL_TESTS` reads take effect: `filter`, `repeat`, `shuffle`, `random_seed`, `also_run_disabled_tests`, `list_tests`. `brief` and `output` are read inside `InitGoogleTest`, so they go on the line before it.

## B. CTest
GoogleTest runs the test cases **inside one program**. CTest (`ctest`, part of CMake) registers **programs (commands)** as tests and runs them. A command that ends with 0 passes; anything else fails. So GoogleTest programs, Python check scripts and lesson executables share one list.

### B1. Where to run it
- This project has test presets in `CMakePresets.json`: `ctest --preset <preset>` runs the tests of that build folder and shows the output of failed tests (`outputOnFailure`).
- 💻 Linux, WSL: straight from the shell, `ctest --preset linux-x64-debug …`.
- 💻 Windows: `ctest` is on PATH only in a VS developer prompt (Developer PowerShell for VS). In any other shell use `build.py`: it finds the developer environment itself and calls `ctest`.
- Build first: `ctest` does not build. `build.py --test`/`--label` build and then call `ctest`.
- 🌐 The web playground has no CTest (it runs the lesson executable directly).

### B2. How this project registers tests
CMake makes the CTest list. There are four ways.

1. **One per lesson** ([`lessons/CMakeLists.txt`](/lessons/CMakeLists.txt)): the lesson executable itself becomes the test `lesson.<id>`, with a time limit and a label.
   ```cmake
   add_test(NAME lesson.${_id} COMMAND ${ATUGCC_TEST_LAUNCHER} $<TARGET_FILE:lesson_${_id}>)
   set_tests_properties(lesson.${_id} PROPERTIES TIMEOUT 10 LABELS "lesson")
   ```
   So the 13 cases of this lesson are **one** test in CTest, `lesson.testing`. If any of them breaks, `lesson.testing` fails.
2. **All unit tests as one** ([`tests/CMakeLists.txt`](/tests/CMakeLists.txt)): `atugcc_tests` (about 140 cases) is one test, `AllTests`, label `unit`. Three self-checks of the step helper that fail on purpose (`ScenarioStep*`) are `unit` tests with a process of their own.
3. **One per case** (`tests/CMakeLists.txt`): after a build, `gtest_discover_tests` runs the program with `--gtest_list_tests` and makes a CTest test for each case. That is how the scenarios become `scenario.<Suite>.<Name>`, each running in its own process.
   ```cmake
   gtest_discover_tests(atugcc_scenarios
     TEST_PREFIX "scenario."
     WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
     DISCOVERY_TIMEOUT 30
     PROPERTIES ${ATUGCC_SCENARIO_PROPERTIES})
   ```
4. **Probes** (`tests/CMakeLists.txt`): checks that need a crash, a kill, a restart or a special environment. A probe program is registered with `add_test`, and usually a Python script runs it and checks the files it wrote (`CrashDump`, `LogMap`, `TraceStream` …).

A **label** is the kind of a test: `unit`, `scenario`, `probe` (checks that need a crash, an exit or a special environment), `lesson`, `long` (lessons that take long). One test can have several labels (`lesson;long`). The kinds are described in [`tests/README.md`](/tests/README.md) §1.

### B3. Picking
| Option | What it does |
|---|---|
| `-N` | list only, no run |
| `-R <regex>` / `-E <regex>` | only names that match / all but those |
| `-L <regex>` / `-LE <regex>` | only labels that match / all but those |

`-R` and `-L` take **regular expressions**. The `.` in `lesson.testing` matches any character, so to pick exactly one write `^lesson\.testing$`. `build.py --label <L>` is a build followed by `ctest -L <L>`, and it fails when no test matches (so a typo does not look like a pass).

**Try it** 💻:
```text
ctest --preset linux-x64-debug -N -L lesson
ctest --preset linux-x64-debug -N -L unit
ctest --preset linux-x64-debug -N -L scenario
ctest --preset linux-x64-debug -R "^lesson\.testing$"
```

**What you see**: `-N -L scenario` shows one test per scenario; `-N -L unit` shows `AllTests`, which holds all unit tests, and the three self-checks: 4 in all.
```text
Test project <repo>/out/build/linux-x64-debug
  Test #1: scenario.TracedStateMachine.EventsReachStreamInOrder
  Test #2: scenario.LoggedErrorFlow.ErrorFromTwoThreadsReachesFile

Total Tests: 2
```
```text
    Start 34: lesson.testing
1/1 Test #34: lesson.testing ...................   Passed    0.04 sec

100% tests passed out of 1

Label Time Summary:
lesson    =   0.04 sec*proc (1 test)
```

### B4. Looking at failures
| Option | What it does |
|---|---|
| `--output-on-failure` | shows the output of failed tests (this project's presets already turn it on) |
| `-V` | the command and output of every test |
| `--rerun-failed` | only the tests that failed last time |

The list of failed tests stays in the build folder's `Testing/Temporary/LastTestsFailed.log` (`--rerun-failed` reads it). All output is in `Testing/Temporary/LastTest.log`.

**Try it** 💻: make one expected value wrong as in A2 and build again (in a WSL or Linux shell: `python3 .agent/scripts/build.py --preset linux-x64-debug --target lesson_testing`). Then give the build folder directly instead of `--preset` (`--test-dir`, without the preset's `outputOnFailure`) to see the difference:
```text
ctest --test-dir out/build/linux-x64-debug -R "^lesson\.testing$"
ctest --test-dir out/build/linux-x64-debug -R "^lesson\.testing$" --output-on-failure
ctest --test-dir out/build/linux-x64-debug --rerun-failed
```

**What you see**: the first command shows only a `***Failed` line and the list at the end, the second the whole GoogleTest output (with A2's failure message), the third runs only `lesson.testing` again.
```text
The following tests FAILED:
	 34 - lesson.testing (Failed)                           lesson
```
Undo the change and build again.

### B5. Repeating, running side by side, time limits
| Option | What it does |
|---|---|
| `--repeat until-fail:<n>` | up to n times until it fails (finding a test that fails only sometimes) |
| `--repeat until-pass:<n>` | up to n times until it passes (getting past an occasional failure for now; find the cause separately) |
| `-j <n>` | n tests side by side |
| `--timeout <seconds>` | a time limit per test (a test's own `TIMEOUT` comes first) |

The `TIMEOUT` of a lesson test is 10 seconds for quick lessons and the manifest's `timeout` (300 seconds if not set) for long ones. Going over it fails the test as `***Timeout`.

`-j` is safe only when tests share no files, ports or global state. That is one reason scenarios get their own process and `workDir()`.

**Try it** 💻:
```text
ctest --preset linux-x64-debug -R "^lesson\.testing$" --repeat until-fail:3
ctest --preset linux-x64-debug -L scenario -j 2
```

**What you see**: the first command `Start`s the same test three times; in the second both scenarios start together (`Start 2` and `Start 1` come first, results in the order they finish).

## C. Test reports
Adding `--report` to `build.py` keeps the run's results as files: the test list, a JUnit XML per CTest step, a JSON per GoogleTest program (`GTEST_OUTPUT`), and a summary for people, `report.md`. The report is written even when tests fail, and the exit code is the same as without `--report`.

```text
py -3 .agent/scripts/build.py --preset windows-x64-debug --label lesson --report
```

The last line, `report: out/test-reports/<preset>/<date-time>/report.md`, is where the report is. Where this lesson appears in it:
- **Results by label**: `lesson.testing` counts as one test in the `lesson` row.
- **Failures**: when `lesson.testing` fails, the broken **case name** and its message are under it. Which of the 13 cases inside the one CTest test broke comes from the GoogleTest JSON.
- **GoogleTest cases**: the `lesson_testing.json` row (13 cases, the number failed).

`report.md` with A2's wrong expected value (part):
````markdown
## Results by label
| Label | Tests | Passed | Failed | Not run | Time (s) |
|---|---|---|---|---|---|
| lesson | 17 | 16 | 1 | 0 | 17.82 |

## Failures
### lesson.testing
- `ParseVersion.ReadsThreeNumbers`:
```
lessons/tracks/01_essentials/16_testing/test_version.cpp:36
Expected equality of these values:
  result->minor
    Which is: 2
  5u
    Which is: 5
```

## GoogleTest cases
| Program | Cases | Failed | Disabled |
|---|---|---|---|
| lesson_testing.json | 13 | 1 | 0 |
````

[`tests/README.md`](/tests/README.md) §4 explains every part of the report (Steps, Slowest tests, Inputs, and the order for following a failure).

**Three places to read a failure**
| Where | What you see |
|---|---|
| console output | everything. MSVC writes `file(line): error:`, Clang and GCC `file:line: Failure` |
| 🌐 web editor | a red marker and the message on the failed `ASSERT`/`EXPECT` line |
| 💻 `report.md` | the failed CTest tests of the whole run, the cases inside them, messages, times |

The web has no report. A report comes from a CTest run (`build.py` → `ctest`), and the web runs one lesson executable directly, without CTest ([KI-042](/docs/known_issues.md)).

## Exercises
1. **`EXPECT` and `ASSERT`, showing values** 🌐💻: do the "Try it" of A2 and A3 in turn. Then add an `operator<<` for `Version`, delete `PrintTo`, and check that the message still says `1.10.0` (GoogleTest uses either). Undo the changes.
2. **Breaking a scenario step** 🌐💻: do the "Try it" of A6, and 💻 locally open `version.txt` and `app.log` in `workDir()` (step 3 stopped, so `app.log` has no error line). Then 💻 run only the scenario: `<exe> --gtest_filter=VersionFileFlow.*`. Undo the change.
3. **Reading a report, and a new test** 💻: with one test broken as in A2, run `py -3 .agent/scripts/build.py --preset <preset> --label lesson --report` and find the case name and line under Failures in `report.md`, and the 1 failure of `lesson_testing.json` under GoogleTest cases. After undoing it, add one input that must be rejected to the `ParseVersionRejects` table (for example `" 1.2.3"`, a leading space), predict whether it passes, then run to check.

## Quick reference
**Macros**
| For | Write |
|---|---|
| one test | `TEST(Suite, Name) { … }` |
| tests that share setup | `class F : public ::testing::Test { protected: void SetUp() override; };` + `TEST_F(F, Name)` |
| a table test | `class P : public ::testing::TestWithParam<T> {};` + `TEST_P(P, Name)` + `INSTANTIATE_TEST_SUITE_P(Inst, P, ::testing::Values(…))`, `GetParam()` in the body |
| go on / stop | `EXPECT_*` / `ASSERT_*` |
| fail right away | `ADD_FAILURE()` (go on), `FAIL()` (stop), `GTEST_SKIP()` (mark as skipped) |
| attach a message | `EXPECT_EQ(a, b) << "…";` |
| name a part of the flow | `SCOPED_TRACE("…")` (this project's step helper uses it) |
| show values | `operator<<` or `PrintTo(const T&, std::ostream*)` in the same namespace |

**GoogleTest options** (except `--gtest_list_tests`, also as `GTEST_<UPPER CASE>` environment variables)
| Option | What it does |
|---|---|
| `--gtest_list_tests` | list |
| `--gtest_filter=A*:B.*-C.*` | pick and leave out |
| `--gtest_repeat=N`, `--gtest_shuffle`, `--gtest_random_seed=N` | repeat, shuffle |
| `--gtest_brief=1`, `--gtest_output=json:<path>` | short output, result file |
| `--gtest_break_on_failure` | stop in the debugger |

**CTest and `build.py`** (`<p>` = preset)
| I want to | Command |
|---|---|
| build and run everything | `py -3 .agent/scripts/build.py --preset <p> --test` |
| build and run one kind | `py -3 .agent/scripts/build.py --preset <p> --label lesson` |
| build, run and report | add `--report` to the command above |
| list | `ctest --preset <p> -N` (`-L <label>`, `-R <name>`) |
| run one | `ctest --preset <p> -R "^lesson\.testing$"` |
| run the failed ones again | `ctest --preset <p> --rerun-failed` |
| find an occasional failure | `ctest --preset <p> -R <name> --repeat until-fail:20` |
| side by side | `ctest --preset <p> -j 4` |

More: kinds of tests and reports [`tests/README.md`](/tests/README.md), source locations [05_source_location](../05_source_location/README.en.md), error values [04_error_expected](../04_error_expected/README.en.md).
