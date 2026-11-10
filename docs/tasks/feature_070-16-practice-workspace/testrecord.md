# Test record: 070-16 연습 작업 공간과 되돌리기

- Spec: [/docs/specs/070_16_practice_workspace.md](/docs/specs/070_16_practice_workspace.md)
- Plan: [plan.md](plan.md)
- Hosts: Windows 11 (MSVC, `windows-x64-debug`), WSL2 Ubuntu 24.04 (Clang 20.1.2, `linux-x64-debug`, `linux-x64-playground`). Browser checks: installed Edge, headless, through `playwright-core` 1.48.2 in a scratch folder (scripts `ac.mjs`, `ac10.mjs`, not committed), against `tools/playground.py --port 18783 --no-frontend-build`.

## Runs
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R1 | U1: hand-made copies of `lambda_capture` (+ unit), `modules`, `testing`; `build.py --target practice_<id>` on `windows-x64-debug` | 0 warnings, each runs | 3 targets exit 0, 0 warnings; `practice_lambda_capture` prints the copy's and the unit copy's edited lines, `lesson_lambda_capture` the originals; `practice_modules` exit 0 (same module name `modules.geometry` as `lesson_modules` in one build); `practice_testing` 13 tests passed | Pass |
| R2 | R1 on `linux-x64-debug` (WSL) | same | 3 targets exit 0, 0 warnings, all run exit 0 | Pass |
| R3 | new copy (`02_format_text`) made after the configure; `build.py --target practice_format_text` | found without a hand configure | `Re-running CMake`, target built | Pass |
| R4 | `ctest --preset linux-x64-debug -N` with copies, then with `practice/` moved away and rebuilt | same list | 35 and 35, `diff` empty | Pass |
| R5 | a copy made uncompilable (`this is not C++;`), `build.py --preset linux-x64-debug --test` | green; the broken target alone fails | exit 0, 35/35, no `practice_` target in the log; `--target practice_lambda_capture` alone exit 1 (`expected unqualified-id`) | Pass |
| R6 | `py -3 tools/test_practice.py` | pass | 15 tests OK | Pass |
| R7 | `python3 web/server/test_server.py` (WSL, no fixture) | pass | 70 tests OK (23 skipped: fixture runs, covered by R10) | Pass |
| R8 | `npm --prefix web/frontend run build`, `npm --prefix web/frontend test` | pass | build ok; 8 files, 86 tests | Pass |
| R9 | browser `ac.mjs` on a fresh `practice/` | 19 checks | 19/19 (below); first practice run 12.8 s (configure re-glob + build + run) | Pass |
| R10 | `build.py --preset linux-x64-debug --test --report out/test-reports/070-16-linux-full` | all pass | 35/35: unit 4, scenario 2, probe 12, lesson 17, long 2, playground 1 (`PlaygroundServer` with the fixture) | Pass |
| R11 | `build.py --preset windows-x64-debug --test --report out/test-reports/070-16-windows-full` | all pass, 0 warnings | exit 0: unit 4, scenario 2, probe 12, lesson 17, long 2 | Pass |
| R12 | browser `ac10.mjs` (GoogleTest failure in `testing`'s copy, Timings of `span_timing`) | marks on the copy | both pass | Pass |
| R13 | `py -3 tools/lessons.py check`, `py -3 tools/test_lessons.py`, `py -3 .agent/scripts/lint_docs.py` | 0 / pass / 0 | 0 errors 0 warnings; 91 OK; 0 errors 0 warnings | Pass |
| R14 | after R9 and R12: `git status --porcelain lessons` | no lesson source changed by the page | only the READMEs, intro and `CMakeLists.txt` this task edits | Pass |

Browser checks of R9 (`ac.mjs`): tabs are `practice/…` copies; default mode practice with the bar shown; editing the copy (Monaco replace) and Run shows `[reference] PRACTICE total`; origin bytes unchanged; copy saved; tab underlined; tree `✎`; ↺ dialog lists exactly the copy; after reset the copy equals the origin, the note names `practice/backup/<stamp>`, the editor shows the original; compare dialog shows the inserted line (`.line-insert`); original mode opens `lessons/…`, `body.mode-original`, bar hidden; mode kept after reload; in practice mode a `lessons/` README tab is 🔒; a compile error in the copy is marked on the copy's tab; "레슨 되돌리기" lists the lesson copy only and restores it; tree mark cleared.

## AC evidence
| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | R6 (`test_01`: copies byte for byte incl. CRLF, state with origin sha, all `same`; `test_03` hand copies recorded); R14 and `.gitignore` `/practice/` (`git status` never lists `practice/`) | Pass |
| AC-2 | R9 (edit → output, origin unchanged, 12.8 s, within the 120 s build limit); R7 `test_create_options_and_dispatch` (cwd = copy folder, `practice=True`), `test_build_command_names_the_practice_target` (`--target practice_a` / `lesson_a`) | Pass |
| AC-3 | R7 `FilesTest`: copy writable; `lesson.toml`, `unit.toml`, `LESSON.TOML`, `Unit.toml`, `state.json`, `backup/…`, new file → 403 and unchanged; symlinked folder 403 | Pass |
| AC-4 | R6 `test_07`–`test_11` (file / lesson / unit reset, `both` → `same`, deleted copy restored, 12 backups in one second → newest 10 by number); R7 `PracticeApiTest`; R9 file and lesson reset | Pass |
| AC-5 | R6 `test_04` (unmodified copy follows, modified becomes `both`), `test_05` (manifests follow); R9 compare dialog | Pass |
| AC-6 | R9 (default practice, original mode = `lessons/` tabs and `lesson_<id>` path, kept after reload); R8 `practice.test.ts` (storage blocked → practice); existing web tests unchanged and passing (R7, R8) | Pass |
| AC-7 | R1, R2 (`practice_lambda_capture`, `practice_modules`, `practice_testing` on both hosts, 0 warnings, run) | Pass |
| AC-8 | R4, R5 | Pass |
| AC-9 | R9 screenshots `1_practice_tabs.png`, `2_modified_and_run.png`, `3_reset_dialog.png`, `4_after_reset.png`, `5_diff.png`, `6_original_mode.png`, `7_error_on_copy.png` (scratch folder, viewed by the lead) | Pass |
| AC-10 | build diagnostics (R9), GoogleTest failure and Timings row (R12) land on the copy's tab; Events of `device_state_machine` point at `include/atugcc/pattern/state.hpp` (the library records them) and open that header | Pass |
| AC-11 | R7, R8, R10, R11, R13; §8 documents checked by a reviewer against the code (Reviews) | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1 | codex luna | CMake vs Assumptions 5, 16, 17 | none (two notes retract themselves) | — |
| U2 | cpp-reviewer | `practice.py` vs spec | 11: orphan copies hidden, unchecked state entries crash, `both` kept after reset, deleted copy not restored, `origin-changed` missing, CLI truthiness, unit handling differs, backup sort, empty backup folders, undocumented re-copy, plan names | lead rewrote the module (one `_follow`/`_file` for lessons and units); recheck: all fixed, 4 small new (unrecorded copy `both`, broken-state name clash, unreached unit copies hidden, `path` wrote state) → fixed by lead, checked in a scratch repo |
| U3 | cpp-reviewer | can each test fail | backup test passed with a plain name sort | test rewritten (12 backups in one second); it found a real bug (a pruned name reused) → fixed; the name-sort mutation now fails |
| U4–U6 | cpp-reviewer | write rules, status codes, locks, run target, tests | manifest names compared case-sensitively on `/mnt/c`; `OSError` dropped the connection; build target untested; empty unit list could pass; fixture could make copies in the real repo | `lower()` + test; one `_practice` helper with 500 on `OSError`; `_build` argv test; unit list asserted; fixture stubs `practice_start` |
| U5 | lead check | — | `practice` argument hid the module (`except practice.PracticeError`) | module-level `PracticeError` |
| U7–U10 | cpp-reviewer | page side of Assumptions 8–12, 14 | reset ignored `saveAll` (unsaved edits lost without backup), stale status across lessons, no lesson/mode check after reset, double reset, diff error closing another prompt, diff editable for a read-only copy, unused i18n key, weak `isPracticePath` test | all fixed by lead (small); the key is now the title of a 🔒 original tab |
| U8 | lead check | — | status not refreshed on save; two copies of the reset code | refresh on save; one `resetPractice` |
| U11 | cpp-reviewer | docs vs code, ko/en pairs, §8 | `origin-changed` listed for GET; README-link sentence wrong; `practice.test.ts` missing in Tests; unreached unit copies not followed by `status` | docs fixed; `status_all` follows unreached units (checked in a scratch repo) |
