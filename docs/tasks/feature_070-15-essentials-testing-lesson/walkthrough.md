# Walkthrough: 070-15 essentials 테스트 레슨과 레슨 빌드의 GoogleTest

- Spec: [/docs/specs/070_15_essentials_testing_lesson.md](/docs/specs/070_15_essentials_testing_lesson.md)
- Plan: [plan.md](/docs/tasks/feature_070-15-essentials-testing-lesson/plan.md)
- Test record: [testrecord.md](/docs/tasks/feature_070-15-essentials-testing-lesson/testrecord.md) — all AC-1 – AC-11 pass

## Result
- GoogleTest is declared once, in [`cmake/atugcc_googletest.cmake`](/cmake/atugcc_googletest.cmake) (v1.14.0, unchanged); `tests/` and `lessons/` include it. A lesson with `gtest = true` in `lesson.toml` links `gtest` and gets the scenario step helper (`#include "scenario.hpp"`, `ATUGCC_SCENARIO_WORK_ROOT` under `out/build/<preset>/lessons/scenario_work`). The playground presets, which build no tests, now build GoogleTest for that lesson.
- `tools/lessons.py`: the `gtest` key (bool, compared with CMake's line regex), `uses` kind `test:` (→ `tests/`), ERROR for a gtest/gmock/`"scenario.hpp"` include without the key (lesson sources and used units), WARN for the key without `<gtest/gtest.h>` and for `"scenario.hpp"` without `test:`. 12 new tests.
- Web: the runner turns `<file>:<line>: Failure` lines of the program's stdout into `run.diagnostics`, which the editor marks like build errors; `GTEST_*` variables of the server's environment are removed before a run. No test report view (KI-042).
- New lesson `16_testing` (`testing`, tag `testing`): a version parser (`version.hpp`), unit tests (`TEST`, `EXPECT`/`ASSERT`, `TEST_P` table, `TEST_F` fixture, `PrintTo`), a four-step scenario with the project's step helper, and a `main` that shows what `gtest_main` does. 13 tests from 6 suites, identical on both hosts.
- The lesson README pair is a tutorial (user request 2026-11-05): A. GoogleTest (A1–A7), B. CTest (B1–B5: where to run it, how this project registers tests, picking, failures, repeat/parallel/timeouts), C. test reports, three exercises and a quick reference. Every command and try-it step was run; the excerpts are real output.

## Decisions during DEV
- Spec text aligned with the code after review (no behaviour change, spec History 2026-11-05): `EXPECT_EQ(*newer, (Version{1, 10, 0}))` instead of comparing an `Expected<Version>` (which GoogleTest prints as bytes); `gtest = "true"` is caught by the bool check, not the CMake comparison; AC-1 evidence command `index --out -`; three more tag aliases.
- The runner keeps only stdout for failure parsing, in a bounded window per failure (review of U6).
- The tutorial says where `GTEST_FLAG_SET` works: after `InitGoogleTest` only options read by `RUN_ALL_TESTS` (`filter`, `repeat`, `shuffle`, …); `brief` and `output` must come before it. Checked in the googletest source and by running both placements.

## Agents
Default split: agy flash wrote U2–U6; the lead wrote U1 (CMake), U7 (frontend) and the documents (the tutorial needed the real outputs); codex luna reviewed U1, `cpp-reviewer` reviewed U2–U10, each with one recheck of the lead's fixes. No `lead (fallback)` unit. Lead (small) changes are listed in the plan's unit table.

## Follow-ups
- KI-042 (new with the spec): the playground shows no per-case test results or test report.
- Not planned (spec §6): gmock in lessons, death tests, coverage, a `build.py` test-name option, offline configure.
