# Test record 070-27: 레슨·유닛 뼈대 생성

- Spec: [070_27_lesson_scaffold.md](/docs/specs/070_27_lesson_scaffold.md), plan: [plan.md](plan.md)
- Hosts: Windows 11 (MSVC, `windows-x64-debug`, Python 3.13), WSL2 Ubuntu 24.04 (Clang 20.1.2, libstdc++ 14, `linux-x64-debug`). 2026-11-17.

## Runs
| Run | Command | Expected | Actual | Result |
|---|---|---|---|---|
| R1 | `py -3 tools/test_lessons.py` | all pass | 147 OK (108 existing + 39 new) | Pass |
| R2 | mutations of `tools/lessons.py` (U4 author: 2, lead: 5): insert always at end; no `rmtree`; no duplicate-id check; no folder check; no `track.toml` check; no curriculum restore; fewer scanned files | each makes a test fail | each failed at least one test; file restored (`cmp`) | Pass |
| R3 | probe in the real tree: `lessons.py new-unit scaffold_probe_unit`, `lessons.py new oop_basics scaffold_probe --uses unit:scaffold_probe_unit --tags class`, one `#include` of the unit added to `main.cpp` | ERROR 0, only `[scaffold]` WARNs | 0 errors, 9 `[scaffold]` warnings (5 lesson files, 4 unit files) | Pass |
| R4 | `build.py --preset windows-x64-debug --test --report` (with the probe) | all pass, 0 warnings | 63 / 63, `lesson.scaffold_probe` and `.exercises_verify` passed, no `warning` line; `out/test-reports/windows-x64-debug/20261117-123157/` | Pass |
| R5 | `build.py --preset linux-x64-debug --test --report` (WSL, with the probe) | all lesson tests pass, 0 warnings | 62 / 63: `lesson.scaffold_probe` and `.exercises_verify` passed, no `warning` line; `PlaygroundServer` failed only on `test_seed_lessons_and_units_are_listed`, which pins the real repository's unit list (`jthread_worker`, `lambda_capture`) and saw the probe unit. Expected while the probe exists; `out/test-reports/linux-x64-debug/20261117-123157/` | Pass (see R6) |
| R6 | probe removed (folders deleted, its curriculum line removed: `git diff lessons/curriculum.toml` shows only the two comment lines of U6); `build.py --preset linux-x64-debug --test --label playground --report` | pass | 1 / 1 `PlaygroundServer`; `out/test-reports/linux-x64-debug/20261117-123836/` | Pass |
| R7 | `py -3 -m unittest discover -s <dir> -p "test_*.py"` for `tools`, `.agent/scripts`, `web/server` | all pass | 240 OK; 163 OK; 99 OK (36 skipped: Linux-only runner cases on Windows, as before) | Pass |
| R8 | `py -3 tools/lessons.py check`; `lessons.py index --out -` and `--out - index` | 0 errors, 0 warnings; same index | 0 / 0, 21 lessons, 2 units; both index forms print the same JSON | Pass |
| R9 | `py -3 .agent/scripts/lint_docs.py` | exit 0 | 0 errors, 0 warnings, 44 info | Pass |

## Acceptance criteria
| AC | Evidence |
|---|---|
| AC-1 | `NewLessonSuccessTest.test_new_lesson_success`: five files, ERROR 0, exactly one `[scaffold]` WARN per created file and no other finding, the lesson in `index`. R3 in the real tree |
| AC-2 | `NewLessonOptionsTest`: option values (title with `"` and `\`) read back with `tomllib`, tags and uses, no `[scaffold]` in the manifest, README titles; newline and `*/` in a title rejected |
| AC-3 | `CurriculumEditTest`: end / `--after` / `--before` order in `index`, original lines kept as a subsequence with one line added, last item without a comma (comment kept), CRLF kept, one-line array and items on the `[` / `]` lines refused |
| AC-4 | `NewLessonConditionsAndRollbackTest`: one test per §2.2 condition plus the plan's added ones (both `--after` and `--before`, stale entry, `*/`), each exit 1 with its own message and the file-and-folder snapshot unchanged; a failing lesson-file write and a curriculum write that fails half way both roll back; missing templates. R2 |
| AC-5 | `NewUnitTest`: four files, ERROR 0, one `[scaffold]` WARN per file, a lesson using the unit checks clean; duplicate id and existing folder exit 1 with nothing changed; a unit id equal to a lesson id is allowed |
| AC-6 | `ScaffoldWarnTest`: one WARN with the line number for a lesson source and a unit README, none for a file outside the scanned set, none in the real repository; R8 |
| AC-7 | R3, R4, R5 (lesson tests), R6 |
| AC-8 | R7, R9; full CTest suites R4, R5 + R6 |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1–U3 | cpp-reviewer | §2.1–§2.3, §4, AC-1..AC-6: conditions before writes, curriculum edit, rollback, `check` unchanged, generated lesson clean, CLI compatible, Python 3.11 | 7 mismatches: `--after`+`--before` exit 2; item on the `]`/`[` line inserted silently in the wrong place; `--out - index` broken; rollback only on `OSError`; `mkdir(parents=True)` leaves a parent; curriculum findings printed; WARN wording. Note: `*/` in a title | lead (small) fixed all, plus `*/` and non-UTF-8 text rejected, read-back check of the edited curriculum, `TEMPLATES` read at call time |
| U1–U3 fixes | cpp-reviewer (same) | the fixes, and new defects | none; leftover: a stale curriculum entry would be listed twice | lead (small) added the stale-entry condition (test in U4) |
| U4 | cpp-reviewer | does each AC have a test; can any pass trivially | 9 weak: condition tests that pass with their own check removed (no message asserted), snapshot without folders, curriculum restore untested, one WARN per file not pinned | lead (small) fixed: message per test, folders in the snapshot, half-written curriculum, file set per WARN, new test for a listed track without `track.toml`; R2 mutations |
| U4 fixes | cpp-reviewer (same) | the fixes | none | — |
| U6 | cpp-reviewer | do the docs match the final code; every §8 row done | none (notes: README step 3 lists check warnings without `[scaffold]`, which step 2 covers; spec AC-6 says 22 lessons, the tree has 21: plan Decisions) | — |

Cross-family review: the code units (U2, U4) were written by agy `flash` (Gemini) and reviewed by `cpp-reviewer` (Claude). The lead's fix diffs were reviewed by the same Claude reviewer (ordinary units, delegation.md §1).

Not checked: a run under Python 3.11 (3.13+ is installed on both hosts). The reviewer read the diff for 3.12+ APIs and found none; `Path.read_text(newline=)` (3.13) was replaced by `read_bytes().decode()` in U2.
