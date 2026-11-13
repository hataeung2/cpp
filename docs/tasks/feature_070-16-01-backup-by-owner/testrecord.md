# Test record: 070-16-01 연습 백업을 레슨·유닛별 한 폴더에 모으기

- Spec: [/docs/specs/070_16_01_backup_by_owner.md](/docs/specs/070_16_01_backup_by_owner.md)
- Plan: [plan.md](plan.md)
- Hosts: Windows 11 (MSVC, `windows-x64-debug`), WSL2 Ubuntu (Clang 20, `linux-x64-debug`).

## Runs
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R1 | `py -3 tools/test_practice.py` (final code) | pass | 23 tests OK (was 15; `test_06`, `07`, `11` changed, `16`–`23` added) | Pass |
| R2 | mutation check of the new tests: (a) prune deletes the newest, (b) a stamp per file, (c) clock-back protection removed, (d) `-n` order reversed; `practice.py` restored afterwards | each makes a test fail | (a) 3 failures, (b) 1, (c) 3, (d) 1; restored copy: OK | Pass |
| R3 | AC-8 scenario in a scratch copy of the real `lessons/` (lesson `modules`, `main.cpp` + `geometry.cppm`, three edit-and-reset rounds, `Workspace.reset(lesson=)`) | 6 files in one folder | `practice/backup/lessons/modules/`: `geometry.<s>.cppm`, `geometry.<s+1>.cppm`, `geometry.<s+1>-2.cppm`, same for `main.cpp`; backup root holds only `lessons/` | Pass |
| R4 | `py -3 web/server/test_server.py` (Windows, no fixture) and `-k practice`, `-k files` | pass | OK (fixture runs skipped) | Pass |
| R5 | `build.py --preset linux-x64-debug --test --label playground` (final code, WSL) | `PlaygroundServer` passes | 1/1 passed (139.6 s); the same test passed in R7 before the last review fixes | Pass |
| R6 | `build.py --preset windows-x64-debug --test --report` | all pass, 0 warnings | 40/40 passed (run started before the last `practice.py` / test edits: they touch Python only) | Pass |
| R7 | `build.py --preset linux-x64-debug --test --report` | all pass | 40/40 passed incl. `PlaygroundServer` (137.7 s) | Pass |
| R8 | `cd web/frontend && npm test` | pass | 13 files, 164 tests | Pass |
| R9 | `py -3 tools/test_lessons.py`, `tools/test_exercises.py`, `tools/lessons.py check`, `lint_docs.py` | pass / 0 errors | 98 OK, 32 OK, 0 errors 0 warnings, 0 errors 0 warnings | Pass |

Note: `npm --prefix web/frontend test` from the repository root fails on this machine for every test file ("Vitest failed to find the current suite"); the same tests pass when run inside `web/frontend` (R8). No frontend file changed in this task. Registered as KI-052.

## AC evidence
| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | R1 `test_07`: `_stamp` patched with three different values; the two files of one lesson reset get one stamp (`main.20261112-103015.cpp`, `util.20261112-103015.hpp`), contents are the pre-reset edits, `backup` is `practice/backup/lessons/a`; R2(b) shows the test fails with a stamp per file | Pass |
| AC-2 | R1 `test_16` (unit reset → `units/u`, no `lessons/` folder), `test_07` (lesson reset makes no `units/` folder), `test_17` (lesson and unit with the same id `x`, unit folder `xx`, through the catalog) | Pass |
| AC-3 | R1 `test_11`: 12 resets of one file in one second keep `-3`…`-12` (not the plain-sort answer), the other file's backup survives; R2(a), (d) fail it | Pass |
| AC-4 | R1 `test_18` (dotted names, no extension, subfolder, timestamp-like part, newest 10 kept per group), `test_23` (subfolder source through `Workspace.reset`) | Pass |
| AC-5 | R1 `test_19`: KEEP_BACKUPS + 1 old-format folders stay untouched after 12 resets | Pass |
| AC-6 | R1 `test_06` (dropped source moved to `lessons/a/util.<s>.hpp`, gone from the copy), `test_22` (`move` takes the file, `finish()` reports the first owner) | Pass |
| AC-7 | R4, R5, R7 (`test_practice_reset_lesson` → `practice/backup/lessons/a` with the edited bytes, `test_practice_reset_unit_and_path` → `units/u` and `lessons/a`; the 403 list includes `practice/backup/lessons/a/main.20260101-000000.cpp`) | Pass |
| AC-8 | R3 (isolated copy of the real lessons; `practice/` of the user untouched; `git status` lists no `practice/` file) | Pass |
| AC-9 | `lessons/README.md` 되돌리기 항목, `web/README.md` (API row, practice bar) and `practice.py` docstring read against the code; R6–R9 | Pass |

## Reviews
| Unit | Reviewer | Findings | Handling |
|---|---|---|---|
| U1–U3 | `cpp-reviewer` (fresh reviewer; same family as the lead, no cross-family review: Python tooling, no risky C++ item) | no implementation bug; test gaps (constant stamp, mirrored names, count-only pruning test, no catalog / fallback / subfolder / clock-back test); `_unknown` fallback beyond the spec | fixed by the lead (small): `_unknown` replaced by `PracticeError`, tests rewritten and added (R1, R2) |
| fixes | `cpp-reviewer`, one round (delegation.md §6.3) | pruning equals "newest 10" and never deletes the new backup; `KEEP_BACKUPS == 1` slice edge; unit tests keyed by folder name = id; `test_19` with one old folder; `PracticeError` vs Assumption 6; extension-less name ending in a timestamp | `max(0, …)` slice; unit folder `xx`; 11 old folders; spec History entry for the one exception (Assumption 6) and the extension-less limitation; no third round |
