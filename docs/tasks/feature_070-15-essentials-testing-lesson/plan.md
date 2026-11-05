# Plan: 070-15 essentials 테스트 레슨과 레슨 빌드의 GoogleTest

- Spec: [/docs/specs/070_15_essentials_testing_lesson.md](/docs/specs/070_15_essentials_testing_lesson.md) (approved 2026-11-05, with the tutorial request of the same day: Assumption 18, AC-11)
- Branch: `feature/070-15-essentials-testing-lesson` (from `main` at `2e6293e`)

## Model assignment
Default split ([delegation.md](/.agent/rules/delegation.md) §1): agy `flash` writes the code, test and tool units; `cpp-reviewer` reviews ordinary units; the risky CMake unit gets codex `luna` (different family). The lead writes the doc units, the tutorial README pair included: it has to match the code and the real command output line by line (AC-11), which needs the whole task's context.

## Design

### Files
- [NEW] `cmake/atugcc_googletest.cmake`
- [MODIFY] `tests/CMakeLists.txt` (FetchContent block → include), `lessons/CMakeLists.txt` (`gtest` key)
- [NEW] `lessons/tracks/01_essentials/16_testing/` — `lesson.toml`, `main.cpp`, `version.hpp`, `test_version.cpp`, `scenario_version_file.cpp`, `README.md`, `README.en.md`
- [MODIFY] `tools/lessons.py`, `tools/test_lessons.py`
- [MODIFY] `web/server/runner.py`, `web/server/test_server.py`, `web/frontend/src/main.ts`, `web/frontend/src/api.ts`
- [MODIFY] `lessons/tags.toml`, `lessons/README.md`, `docs/tasks/lesson_candidates.md`, `tests/README.md`, `.agent/rules/test.md`, `.agent/rules/config.md`, `web/README.md`, `docs/cpp_evolution/source_location.md`, `docs/known_issues.md` (KI-042 already registered with the spec), `docs/tasks/agent_todo.md`

### CMake (spec §2.3)
- `cmake/atugcc_googletest.cmake`: `include_guard(GLOBAL)`, `include(FetchContent)`, the `FetchContent_Declare(googletest URL …v1.14.0.zip)`, `set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)`, `FetchContent_MakeAvailable(googletest)` moved verbatim from `tests/CMakeLists.txt`.
- `tests/CMakeLists.txt`: `include(${atugcc_SOURCE_DIR}/cmake/atugcc_googletest.cmake)` in place of the block.
- `lessons/CMakeLists.txt`: per manifest `if(_text MATCHES "(^|\n)gtest[ \t]*=[ \t]*true")` → include the same file (guarded), `target_link_libraries(lesson_<id> PRIVATE gtest)`, include dir `${atugcc_SOURCE_DIR}/tests/scenario`, `ATUGCC_SCENARIO_WORK_ROOT="${CMAKE_CURRENT_BINARY_DIR}/scenario_work"`, `ATUGCC_SANITIZED_BUILD` when `ATUGCC_SANITIZERS`. Header comment gets the `gtest` key.

### Lesson `testing` (spec §2.2)
Common lesson rules as 070-11 … 070-14: file header block, English output, a Korean comment line followed by its English line, camelCase functions, `kPascalCase` constants, no `using namespace` at file scope, exact includes, no platform `#ifdef`, exit 0 when unchanged.
- `version.hpp` (namespace `testing_lesson`; not `testing`, which is GoogleTest's): `struct Version { unsigned major{0}; unsigned minor{0}; unsigned patch{0}; auto operator<=>(const Version&) const = default; };` `inline std::string to_string(const Version&)` → `"1.2.3"`; `inline void PrintTo(const Version&, std::ostream*)`; `[[nodiscard]] inline atugcc::core::Expected<Version> parseVersion(std::string_view)`: split on `.`, exactly three parts, each non-empty and parsed whole by `std::from_chars` into `unsigned` (`ec != std::errc{}` or `ptr != end` → error), any error → `std::unexpected(CoreError::InvalidArgument)`; `[[nodiscard]] inline std::optional<Version> newestVersion(std::span<const Version>)` (`std::ranges::max`, empty → `std::nullopt`). `to_string` keeps its std/ADL name (naming_check exception list) — check `naming_check.py`; if it refuses, the name is `toString`.
- `test_version.cpp`: suites `ParseVersion` (`ReadsThreeNumbers`), `ParseVersionRejects` (`TEST_P BadText`, instance `Table`, values `"", "1.2", "1.2.3.4", "1.x.3", "-1.2.3", "1..3", "99999999999.0.0"`), `VersionOrder` (`ComparesNumbersNotText`), fixture `ReleaseListTest` (`SetUp` parses `"1.2.0", "1.10.0", "1.9.3"` into `std::vector<Version> releases_`, `FAIL()` on a parse error; `NewestIsHighest`, `SortsAscending`), `NewestVersion` (`EmptyListHasNone`).
- `scenario_version_file.cpp`: `VersionFileFlow.BadVersionIsLogged`, the four steps of spec §2.2 with the exact step names there.
- `main.cpp`: `InitGoogleTest` + `return RUN_ALL_TESTS();` with the comments of spec §2.2.

### `tools/lessons.py` (spec §2.4)
- `Lesson` gets `gtest: bool`; manifest key `gtest` must be a bool (ERROR otherwise, `line_of`).
- `check_cmake_view`: `CMAKE_GTEST = (?:^|\n)gtest[ \t]*=[ \t]*true`; mismatch with the TOML value → ERROR via `mismatch`.
- `uses` prefix `test:` → `tests/<path>`, missing file ERROR, prefix error message lists `test:`; `ref_files`/`index` map it.
- `check`: `GTEST_INCLUDE_RE` (`#include <gtest/…>` or `<gmock/…>`) and `SCENARIO_INCLUDE_RE` (`#include "scenario.hpp"`) over the lesson's sources and the files of its unit closure. Not `gtest` and any match → ERROR. `gtest` and no `<gtest/gtest.h>` in any source → WARN. `"scenario.hpp"` and no `test:scenario/scenario.hpp` in the `uses` closure → WARN.

### Web (spec §2.5)
- `runner.py`: in `_execute`, drop every `GTEST_*` key from `env`; run `_stream(..., keep_log=True)` and `run["diagnostics"] = parse_test_failures(outcome.log, self.root, job.lesson.path)`. `TEST_FAILURE_RE = ^(?P<file>[^:\n]+):(?P<line>\d+): Failure$` (re.M); message = the following lines up to a blank line, a line starting with `[` or `Google Test trace:`, at most 6 lines and 500 characters; `col` 1, `severity` `"error"`, at most `MAX_DIAGNOSTICS`.
- `test_server.py`: `parse_test_failures` cases (two failures, one with a trace line; a path outside the repository; the cap); the run environment without `GTEST_FILTER` (through a helper the env construction is moved into, if the fixture cannot show it).
- `api.ts`: `run` gets `diagnostics?: Diagnostic[]`; `main.ts`: `editor.setDiagnostics([...d.build.diagnostics, ...(d.run?.diagnostics ?? [])])`.

## Units

| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `cmake/atugcc_googletest.cmake`, `tests/CMakeLists.txt`, `lessons/CMakeLists.txt` (+ `16_testing/lesson.toml`, a one-test `main.cpp` stand-in) | shared googletest, `gtest` key (§2.3; AC-3) | configure + build `windows-x64-debug`, `linux-x64-debug`, `linux-x64-playground`; one `FetchContent_Declare(`; `--report` assigns `lesson_testing.json` (Assumption 12) | yes (three files change together) | lead (small) | codex luna: none | review 119k / 2k | done |
| U2 | `16_testing/version.hpp`, `test_version.cpp`, `main.cpp` | code under test, unit tests, main (§2.2; AC-2, AC-4) | build both presets 0 warnings; `lesson.testing` passes; `--gtest_list_tests` equal on both OSes | no | agy flash | cpp-reviewer: comment wording (gtest env vars are read before `main`, `gtest_main` also prints a line, TEST_P rows made in `InitGoogleTest`, Korean/English pairs), spec §2.2 VersionOrder text → review fixes lead (small); recheck: none | see agy log | done |
| U3 | `16_testing/scenario_version_file.cpp` | scenario (§2.2; AC-2, AC-4) | build both presets; `[step 1]`–`[step 4]` in the output | no | agy flash | lead: unused `parseResult` removed, lead (small); cpp-reviewer: that removal broke the file (closing `});` inside a comment), `flush()` comment said "disk", step 2 comment too broad → review fixes lead (small), rebuilt both presets; recheck: "once-per-process" → spec's "process-wide" (reviewer's wording) | see agy log | done |
| U4 | `tools/lessons.py` | `gtest`, `test:`, checks, index (§2.4; AC-1, AC-6) | `lessons.py check` 0/0; `index --out -` shows `tests/scenario/scenario.hpp` | no | agy flash | cpp-reviewer: no spec mismatch; wording (matched include text, lesson named in the unit WARN, top-level hint), an unrequested positional `index` argument → review fixes lead (small), positional reverted and spec AC-1 command → `index --out -`; recheck: none | see agy log | done |
| U5 | `tools/test_lessons.py` | one test per new rule (AC-6) | `py -3 tools/test_lessons.py` | no | agy flash | cpp-reviewer: no trivial pass; lines not asserted in 4 tests, one mismatch direction untested → review fixes lead (small): `onlyFinding`, line asserts, `[run]` case (12 tests, file 91 OK), spec §2.4 example fixed; recheck: none | see agy log | done |
| U6 | `web/server/runner.py`, `web/server/test_server.py` | `GTEST_*` env, failure markers (§2.5; AC-7) | `PlaygroundServer` | no | agy flash | cpp-reviewer: whole-log split per match, `splitlines`, stderr in the log, 3 test gaps → review fixes lead (small): 4096-char window, split on newline only, `_Collector.log_name` (stdout only), edge-case tests; recheck: none, optional stdout-only e2e gap closed (fixture writes a failure-shaped stderr line); `PlaygroundServer` passes | see agy log | done |
| U7 | `web/frontend/src/api.ts`, `main.ts` | merge run diagnostics (§2.5; AC-7) | `npm --prefix web/frontend test`, build | no | lead (small) | cpp-reviewer (with U6): import order → fixed; recheck: none | — | done |
| U8 | `16_testing/README.md` | tutorial, Korean (§2.2; AC-8, AC-11) | every command run (AC-11); lint | no | lead | cpp-reviewer: 9 accuracy points (printer order, `GTEST_FLAG_SET` after `InitGoogleTest`, env var for `list_tests`, JSON keys, per-test lines, 4 `unit` tests, probes missing, long timeout default, `protected:`) and 2 follow-along points (full `build.py` command, a Linux failure line) → fixed by lead, each new claim run; recheck: none | — | done |
| U9 | `16_testing/README.en.md` | tutorial, English (AC-8) | README pair counts; lint | no | lead | cpp-reviewer (with U8): translation none | — | done |
| U10 | `tags.toml`, `lessons/README.md`, `lesson_candidates.md`, `tests/README.md`, `test.md`, `config.md`, `web/README.md`, `source_location.md`, `known_issues.md` | §8 (AC-10) | `lint_docs.py` 0 | no | lead | cpp-reviewer: KI-042 Next contradicted the runner, network note only for one preset, test.md label wording, `ATUGCC_SANITIZED_BUILD` missing, redundant `CTest` alias / spec §2.6 → fixed by lead; recheck: none (spec History entry added for the DEV corrections) | — | done |
| U11 | `agent_todo.md` | states | lint | no | lead | — | — | |
