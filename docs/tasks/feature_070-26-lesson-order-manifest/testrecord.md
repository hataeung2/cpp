# Test record: 070-26 레슨 순서를 매니페스트로 옮기고 폴더 번호 제거

- Spec: [/docs/specs/070_26_lesson_order_manifest.md](/docs/specs/070_26_lesson_order_manifest.md)
- Plan: [plan.md](plan.md)
- Hosts: Windows 11 (MSVC, `windows-x64-debug`), WSL2 Ubuntu 24.04 (Clang 20, libstdc++ 14, `linux-x64-debug`). 2026-11-16.

## Runs
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R1 | before the move (code of `main`): `lessons.py index` and `practice.py status` saved to scratch files | — | 3 tracks, 21 lessons, 2 units; 53 practice files, all `same` | baseline |
| R2 | new `lessons.py check` on the numbered tree, before the move | ERRORs for every folder name and the missing file | 25 errors (21 lesson folders, 3 track folders, no `curriculum.toml`) | Pass |
| R3 | `migrate.py --dry-run`, then the real run | — | 24 folder names; 59 files, 321 replacements; 24 `git mv`; 24 practice folders moved, `state.json` 53 entries | done |
| R4 | after: `lessons.py check` | 0 errors | 0 errors, 0 warnings; 3 tracks, 21 lessons, 2 units | Pass |
| R5 | index order after vs. R1 (track ids without the number) | equal | equal; units 2 → 2 | Pass |
| R6 | `practice.py status` after vs. R1 (numbers removed from R1's paths) | equal, no `missing-origin` | equal; no `modified`, `both` or `missing-origin` line | Pass |
| R7 | numbered paths: (a) `git grep -nE "tracks/[0-9]{2}_\|\b[0-9]{2}_(essentials\|patterns\|oop_basics)\b" -- . ":!docs/tasks" ":!docs/specs" ":!docs/archive"`; (b) the same pattern inside `](…)` in `docs/specs`, `docs/archive` | (a) only the new rejection test, (b) 0 | (a) 2 lines, both `tools/test_lessons.py` `test_numbered_track_folder_is_rejected`; (b) 0 | Pass |
| R8 | `py -3 tools/test_lessons.py` | pass | 108 OK (10 new in `CurriculumTest`) | Pass |
| R9 | mutants of `apply_curriculum`: (a) lessons not sorted, (b) "listed under another track" check removed; restored afterwards | each fails a test | (a) 2 failures, (b) 1; restored: OK | Pass |
| R10 | `tools/test_exercises.py`, `tools/test_practice.py`, `.agent/scripts/test_agent_scripts.py`, `web/server/test_server.py` (no fixture) | pass | 32 OK, 23 OK, 163 OK, 99 OK (36 skipped without fixture) | Pass |
| R11 | `py -3 tools/test_playground.py` | pass | 27 OK | Pass |
| R12 | `npm --prefix web/frontend test` | pass | 13 files, 164 tests | Pass |
| R13 | `build.py --preset windows-x64-debug --test --report` | all pass, 0 warnings | 61 / 61, no `warning C`; `out/test-reports/windows-x64-debug/20261116-165021/` | Pass |
| R14 | `build.py --preset linux-x64-debug --test --report` (WSL) | all pass, 0 warnings | 61 / 61 incl. `PlaygroundServer`, no `warning` line; `out/test-reports/linux-x64-debug/20261116-165412/` | Pass |
| R15 | `lint_docs.py` | 0 errors | 0 errors, 0 warnings, 44 info (was 33: the new INFO lines are links inside sealed `docs/tasks/` records that point to the old folders) | Pass |

## AC evidence
| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | R4 (folder = id is an ERROR rule, R2 shows it firing), `Get-ChildItem lessons/tracks`: `essentials`, `oop_basics`, `patterns` | Pass |
| AC-2 | R5 (21 lessons, not 22: the spec miscounted, plan.md) | Pass |
| AC-3 | R8 `test_order_follows_the_file_not_the_folder_names` (order against name order, swap of two lines), `test_new_lesson_in_the_middle_of_the_list`; R9(a) | Pass |
| AC-4 | R8: `test_listed_lesson_without_folder`, `test_lesson_listed_twice`, `test_lesson_listed_under_another_track`, `test_folder_name_must_equal_the_lesson_id`, `test_unlisted_lesson_and_track_come_last_with_a_warning`, `test_missing_or_broken_file_falls_back_to_folder_names`, also `test_track_listed_without_folder_and_twice`, `test_numbered_track_folder_is_rejected`; R9(b) | Pass |
| AC-5 | R7 (the grep in two parts: plan.md explains why the spec's single command does not fit Assumption 7), R15 | Pass |
| AC-6 | R12, R13, R14 (every `lesson.<id>` and `exercises_verify` under the new paths) | Pass |
| AC-7 | R6; `practice/progress.json` not touched by the move (keyed by lesson id) | Pass |
| AC-8 | automatic part: R10 (`test_server.py`), R11, R14 `PlaygroundServer`. Manual check by the user: pending | pending |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U1, U3 | codex `luna` (medium, read-only) | `apply_curriculum` vs §2.1 and Assumptions 3–4, inputs that raise or drop a lesson; `migrate.py` token choice, missed reference forms, sealed files; code still depending on numbered folders | 1: `migrate.py` checked existing destinations for track moves only; a lesson target that already exists would fail a `git mv` after the text edits | lead (small): lesson targets are checked before anything moves; checked in a scratch tree (stops with `target exists`, nothing changed). The real run had no such target (R3) |
| U2, U4, U5 | `cpp-reviewer` | can a `CurriculumTest` pass trivially; docs vs Assumptions 1–5, 11; did fixture renames change what a test checks | Q1: `test_new_lesson_in_the_middle_of_the_list` ended in name order and had an unchecked first step; the fallback test could not tell a broken file from an empty one, and its track order equalled name order. Q2: none. Q3: `test_17` lost its lesson folder ≠ id case; `test_server.py` kept fixtures `02_b`, `03_c` | lead (small): middle test uses `zz` and checks both steps; fallback test lists an order unlike name order (3 tracks), checks the `TOML syntax error` finding and no "not listed" warning; `test_17` lesson folder `xl` with id `x`; server fixtures `b`, `c`. R16, R17 |

## Revision 1 — 2026-11-16 (review fixes)
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R16 | `tools/test_lessons.py`, `tools/test_practice.py`, `web/server/test_server.py` (no fixture) | pass | 108 OK, 23 OK, 99 OK (36 skipped) | Pass |
| R17 | mutant: tracks and lessons sorted by folder name only (curriculum ignored); restored afterwards | the order tests fail | 4 failures (middle, fallback, file-order, unlisted); restored: OK | Pass |
| R18 | `build.py --preset linux-x64-debug --test --label playground` (WSL, fixtures `b`, `c`) | pass | 1 / 1 passed (`PlaygroundServer`) | Pass |
