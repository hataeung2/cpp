# Test record: 070-03 essentials 트랙 커리큘럼

- Spec: [/docs/specs/070_03_essentials_curriculum.md](/docs/specs/070_03_essentials_curriculum.md)
- Plan: [plan.md](/docs/tasks/feature_070-03-essentials-curriculum/plan.md)
- Branch: `feature/070-03-essentials-curriculum`
- Hosts: Windows 11 (MSVC, VS 2026), WSL2 Ubuntu 24.04 (GCC 13.3)

Helper scripts used for evidence live in the lead's scratch area, outside the repository (rule: no helper scripts in the repo). What each one does is written next to its result.
- `comment_pairs.py`: every run of comment lines with Hangul (`//` and `/* */`) must be followed at once by a comment line without Hangul; `--code-same <rev>` also compares the file with `<rev>` after removing comments and blank lines. Negative check: on the HEAD version of `lambda_capture.hpp` (Korean-only comments) it reports 7 problems.
- `readme_pairs.py`: for each `README.md` under `lessons/` (not `lessons/README.md`), `README.en.md` exists and has the same number of headings, exercise items, code blocks and tables; every link in the English file to a README that has an English version points at `README.en.md`.
- `scan_output.py`: runs every `lesson_*` binary of a build in an empty temporary folder, fails on a non-zero exit code or on Hangul (U+AC00–U+D7A3, U+1100–U+11FF, U+3130–U+318F) in stdout or stderr.
- `ac8.mjs`: `playwright-core` 1.48.2 driving the installed Edge headless against `py -3 tools/playground.py --port 18781`, English page language set by an init script. It clicks every lesson and unit, checks the README panel (`h1` without Hangul, no `.readme-notice`), types five queries and takes the screenshots. It never edits or saves a file.

## Runs

| # | Command | Result |
|---|---|---|
| R1 | `py -3 tools/test_lessons.py` | 71 tests OK (after U2 and the review fixes) |
| R2 | `py -3 tools/lessons.py check` | `0 error(s), 0 warning(s); 2 track(s), 8 lesson(s), 2 unit(s)` |
| R3 | `py -3 tools/lessons.py index` (tree order, also seen in R9) | essentials: `lambda_capture, format_text, error_expected, source_location, thread_and_log, log_recovery, span_timing`; patterns: `device_state_machine` |
| R4 | `py -3 .agent/scripts/build.py --preset windows-x64-debug --test` | build without warnings; `100% tests passed, 0 tests failed out of 21` (incl. `LessonConsoleCodePage` with the new expected line, 8 `lesson.*`). Lesson sources changed by the U7–U10 review fixes afterwards were rebuilt target by target without warnings and re-run (R6, R7) |
| R5 | `py -3 .agent/scripts/build.py --preset linux-x64-debug --test` (WSL) | build without warnings; `95% tests passed, 1 tests failed out of 21`: `PlaygroundServer` `LessonsApiTest.test_seed_lessons_and_units_are_listed` asserted the exact list of the 4 seed lessons. Fixed (test change, see Revision note below) |
| R5b | `ctest --preset linux-x64-debug -R 'PlaygroundServer\|lesson\.'` after the fix | `100% tests passed, 0 tests failed out of 9` (`PlaygroundServer` 133.9 s, 8 `lesson.*`). The other 12 tests passed in R5 and do not depend on the changed test file |
| R6 | `log_recovery` three runs in an empty folder, Windows (`windows-x64-debug`) | run 1 `nothing to recover (first run?)`; run 2 stderr `[atugcc] recovered 3 undelivered lines from pid …`, file header `ended without a clean exit; crash handler: no`, `3 undelivered lines … 2 delivered lines`, `step 3`–`step 5` `[undelivered]`; run 3 same for run 2's lines; afterwards `log/map` holds only one `.logmap`, no `recovered_*.log`; exit 0 each time |
| R7 | same on Linux (`linux-x64-debug`, WSL) | same results; afterwards `log/map` holds only `atugcc-<pid>-<time>.logmap` |
| R8 | `scan_output.py` on both build trees | Windows: 8 lessons OK (exit 0, 0 Hangul lines). Linux: 8 lessons OK. Both trees also held a stale binary not built from this repo state (`lesson_zz_probe` from this task's deleted design probe; on Linux also `lesson_tmp_probe` from 070-01 R8): deleted (`zz_probe`) or ignored, they are not lessons |
| R9 | `node ac8.mjs` (browser, English page) | all 8 lessons and 2 units: English `h1`, no Korean-only notice; searches `expected` → `error_expected`, `__LINE__` → `source_location`, `포맷` → `format_text`, `복구` → `log_recovery`, `std::format` → `format_text` (each `Lessons 1 · Units 0`); screenshots in [`screenshots/`](/docs/tasks/feature_070-03-essentials-curriculum/screenshots/) |
| R10 | `npm --prefix web/frontend run build`, `npm --prefix web/frontend test` | build OK; `Test Files 7 passed (7)`, `Tests 63 passed (63)` (no frontend change in this task) |
| R11 | `comment_pairs.py` on the 8 lesson `main.cpp` and 2 unit headers; `--code-same HEAD` on the 2 headers and `01_lambda_capture/main.cpp` | OK (10 files); the comment-only files have no code change |
| R12 | `readme_pairs.py .` | 10 pairs OK, no English file links to a Korean README that has an English version |
| R13 | `py -3 .agent/scripts/lint_docs.py` | `0 error(s), 0 warning(s)` |
| R14 | `source_location` output lines vs source | printed lines 105, 113, 50, 121, 128 (lesson) and 138 (Logger) are the lines of `LOG_HERE`, `logHere`, `logHere` in `startEngine`, `warn`, `logFormat`, `logger.log` |
| R15 | design probe before the plan (2026-11-03, throwaway lesson `99_probe`, deleted) | `std::_Exit(0)` after `configureLogBuffers({.drainInterval = 1000ms, .mappedDir})`: next run recovers the unflushed lines on Windows and Linux. `std::quick_exit` would not (clean exit for the Logger, `logger.hpp` contract) → spec Assumption 8 changed before implementation |

## Acceptance criteria

| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | R3, R9 (tree order); ids unchanged (`lesson.toml` diffs touch no `id`) | Pass |
| AC-2 | R4, R5 (both presets build without warnings, `lesson.*` smoke tests pass on both), outputs: R6–R8, R14 and the per-lesson outputs below | Pass |
| AC-3 | R6, R7 | Pass |
| AC-4 | R12; translation review (Reviews, U11/U12) with its fixes and re-check | Pass |
| AC-5 | R8 (output, both OSes), R11 (comment pairs) | Pass |
| AC-6 | R1: `HangulLiteralTest` (exact line lists; mutation-checked by the reviewer and the lead), `ReadmeEnTest`, `HangulLiteralCheckTest` | Pass |
| AC-7 | R2 | Pass |
| AC-8 | R9 | Pass |
| AC-9 | R4, R5 + R5b, R1, R10 | Pass |
| AC-10 | R13 | Pass |

### Lesson outputs (Windows, abridged where marked)
```text
== 1. positional arguments ==
idle -> run -> idle
== 2. width, fill, alignment ==
name       |  count |   share
-----------+--------+--------
alpha      |    120 |   60.0%
beta       |     50 |   25.0%
gamma      |     30 |   15.0%
== 3. integers and floating point ==
dec: 255, hex: 0xff, oct: 0377, bin: 000011111111
fixed: 3.142, exp: 3.141593e+00, padded:         3.14
== 4. user type ==
default: (1.5, -2.25)
precision: (1.5, -2.2)
== 5. std::format_to ==
buffer: [item 1] [item 2] [item 3] 
size: 27
== 6. runtime format string ==
runtime pattern: value = 42
format_error: Invalid format string.
```
```text
== 1. exceptions ==
parsePortThrowing("8080") -> 8080
parsePortThrowing("abc") threw: invalid_argument (invalid stoi argument)
parsePortThrowing("70000") threw: out_of_range (port out of range)
parsePortThrowing("") threw: invalid_argument (invalid stoi argument)
(steps 2 and 3: -> error InvalidArgument for abc, 70000, ""; port=8080 -> listen on :8080;
 port=80, host=example, port=x -> error InvalidArgument; port=x (with fallback) -> 8080)
```
```text
== 1. macro ==
[main.cpp:105 main] legacy macro logging
== 2. std::source_location default argument ==
[main.cpp:113 int __cdecl main(void)] called from main
[main.cpp:50 void __cdecl `anonymous-namespace'::startEngine(void)] engine starting
== 3. wrapper that forwards the location ==
[main.cpp:121 int __cdecl main(void)] warning: low memory
== 4. variadic: attach the location to the format string ==
[main.cpp:128 int __cdecl main(void)] server listening on 127.0.0.1:8080
== 5. atugcc::core::Logger does the same ==
<time> [INFO] [<repo>\lessons\tracks\01_essentials\05_source_location\main.cpp:138 int __cdecl main(void)] port 8080 ready
```

## Notes
- `PlaygroundServer` test change (R5): `web/server/test_server.py` `test_seed_lessons_and_units_are_listed` now checks that the four seed lessons are listed in this order, with other lessons allowed between them. The old exact list broke with every new lesson; the test's purpose (the seed lessons reach `/api/lessons` in track and folder order) is kept. Not listed in spec §8 because it is a test, not a document.
- `LessonConsoleCodePage` (090-06 AC-9): the expected screen line is now `══ State Transitions ══` (spec §2.3). It passed in R4. Not mutation-tested in this task: the claim that a non-UTF-8 console garbles it rests on U+2550 being three UTF-8 bytes that cp949 decodes to other characters, the same reasoning 090-06 used for the Korean line.
- U1 review: a file listed twice in one `sources` list gets its Hangul WARNs twice. The existing `#include` WARN behaves the same; not changed (`load()` does not reject duplicate entries, a separate matter).
- `log_recovery` timing (U10 review): after `flush()` the lesson waits 100 ms before writing `step 3`–`step 5`. The wait is not synchronization; under heavy load some of those lines may rarely reach the screen. Both READMEs and spec §4 say so. In R6 and R7 (six runs) all three lines were undelivered every time.

## Reviews

| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1+U2 | cpp-reviewer | `hangul_literals` vs §2.5; WARN level/location; can each test fail | code correct; duplicate WARN for a file listed twice; 4 tests pass with their rule removed (char literal, digit separator, `u8R`, identifier ending in R), Jamo U+1100 and exact line of the unit WARN untested | tests strengthened lead (small); re-check: 5/6 fail under mutation; the sixth replaced with the reviewer's counterexample and checked with the lead's own mutant (`token_before.endswith("R")` gives `[1]`, test expects `[]`); duplicate WARN left (Notes) |
| U4+U5 | cpp-reviewer | code unchanged except strings; English = Korean; Hangul left; line numbers | no code change; `LessonConsoleCodePage` expects the Korean heading; paragraph-form comments vs AC-5 wording; one wording ("Measuring time") | test expectation changed + spec §2.3/§8, 090-06 History; spec Assumption 12/AC-5 and plan allow paragraph pairs; wording fixed |
| U7–U9 | cpp-reviewer | plan conformance, correctness, false comments, bilingual, manifests | U7: P2905 wording, parse comment, `{:08b}` fill invisible, spec `{:.1f}`; U8: trailing characters threw `out_of_range`, 2 English comments, unreachable else, spec name `readLine`; U9: false "default argument forbidden after a pack", 2 loose comments, `logf` clashes with `::logf`, spec no-path rule | all fixed lead (small), spec §2.2/Assumption 7 aligned; re-check: all resolved, one spec line (`{:08b}`) left → fixed |
| U10 | codex luna (high) | §2.2/Assumption 8/§4 and the Logger contract | flush-triggered drain can take steps 3–5; recovered file deleted after an open/read failure; "Korean and English on one line" at 74 | 100 ms wait after flush, open/`bad()` checks lead (small); re-check: file handling resolved; timing narrowed but not synchronized → documented (Notes); the one-line claim not reproduced (lines are Korean-only, English on the next line; checked with `cat -A`) |
| U11+U12 | cpp-reviewer | English = Korean; README vs code; false claims; links | 2 translation drifts (thread_and_log "recommended when", log_recovery "next to the dump"); `_Exit` shown as covered like SIGKILL; pre-existing false claims: `std::visit` "branches at compile time", `std::thread` terminate "before the thread ends", printf cannot reorder, `std::print` "without a temporary string", `count`의 사본 | all fixed in both languages (Assumption 11), `format.md` wording too; re-check: all 7 resolved |
| U13 | cpp-reviewer (with the U11/U12 re-check) | false C++/library claims in `format.md`, evolution links, `lessons/README.md` | `format.md`: `printf("%s", int)` "crashes" stated as certain (it is undefined behaviour); nothing else | wording fixed lead (small) |

No cross-family review for U1–U9, U11–U13 beyond what delegation.md §1 asks (ordinary units: agy author, `cpp-reviewer` reviewer; lead-written doc and small units: `cpp-reviewer`). U10 (risky) had the codex review.
