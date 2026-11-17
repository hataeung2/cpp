# Test record: 090-13 Lesson path

- Spec: [/docs/specs/090_13_lesson_path.md](/docs/specs/090_13_lesson_path.md)
- Plan: [plan.md](plan.md)
- Host: Windows 11, Python 3.15 (`py -3`). No C++ change, so no preset build (spec §12).

## Runs
| # | What | Expected | Result | Verdict |
|---|---|---|---|---|
| R1 | `py -3 -m unittest discover -s .agent/scripts -p "test_*.py"` | all pass | 177 tests OK (163 before + 14 in `LintDocsTrackSpecTest`) | Pass |
| R2 | same for `tools` | all pass | 240 tests OK | Pass |
| R3 | same for `web/server` | all pass | 99 tests OK (36 skipped, as before) | Pass |
| R4 | mutation run: each of the 14 `report.add` calls of the new checks in `lint_docs.py` replaced by `pass`, one at a time, then `LintDocsTrackSpecTest` | the class fails every time | 14 / 14 fail (the two messages shared with `check_specs` were mutated in `check_track_specs` only) | Pass |
| R5 | `py -3 .agent/scripts/lint_docs.py` | exit 0 | 0 errors, 0 warnings, 44 info (the same 44 INFO as on `main`) | Pass |
| R6 | `py -3 .agent/scripts/sync_skills.py` then the gate's skill check | copies match | `.claude/skills/develop-task/SKILL.md`, `.agents/skills/develop-task/SKILL.md` written; gate 0 errors | Pass |
| R7 | `lint_docs.py --status` | 070-22 ~ 070-24 `BACKLOG` linking the track spec (not approved yet), no warning | `BACKLOG 33`, no lesson-task finding | Pass |

## Acceptance criteria
| AC | Evidence | Verdict |
|---|---|---|
| AC-1 | `test_clean_tree_and_states` (APPROVED, DEV, TEST, DONE with a full checklist: no ERROR, no WARN besides the archive reminder of DONE lines), `test_archived_done_lesson_task` | Pass |
| AC-2 | one test per §2.5 row: `test_not_in_tasks`, `test_tasks_lists_orphan_task_id`, `test_approved_null_with_approved_and_backlog`, `test_spec_draft_rejected_for_lesson_task`, `test_approved_and_backlog_warns`, `test_missing_frontmatter_key_and_no_frontmatter` (each key), `test_bad_approved_date`, `test_unknown_track` (also without `curriculum.toml`), `test_done_task_checklist` (no folder, folder without checklist, unchecked box on its file and line, patch folder not counted), `test_track_spec_not_linked`, `test_link_to_template_or_non_track_spec`; R4 | Pass |
| AC-3 | R1 (the 163 earlier tests unchanged and passing), `test_template_spec_produces_no_finding`, R5 | Pass |
| AC-4 | review of U1 (`cpp-reviewer`, two rounds, below): sections of §2.2 and items C1–C13 of §2.4; `grep -c "^- \[ \] \*\*C"` = 13 | Pass |
| AC-5 | review of U5 (`cpp-reviewer`, two rounds), R6 | Pass |
| AC-6 | review of U4 (`cpp-reviewer`, two rounds: 070-21 against the track spec), R5, R7 | Pass |
| AC-7 | the user reads and approves `docs/specs/tracks/oop_basics.md`; then `approved` date, 070-22 ~ 070-24 `APPROVED`, gate exit 0 | pending (user) |
| AC-8 | R1, R2, R3, R5 | Pass |

## Reviews
| Unit | Reviewer | Question | Findings | Resolution |
|---|---|---|---|---|
| U2 `lint_docs.py` | `cpp-reviewer` | every §2.5 row, AC-3, templates skipped, archive lines, 0/1/many folders | the `feature_<id>-*` glob also matched patch folders; with several folders one without `checklist.md` passed; a link to another existing file under `tracks/` skipped every check | fixed by the lead (folders matched by `TASK_DIR_RE` id, every own folder needs `checklist.md`, such a link is an ERROR); re-review: none |
| U3 tests | `cpp-reviewer` | levels and locations per row, AC-1 clean case, tests passing for a wrong reason | archive case untested; only `tasks` of the three keys tested; "has no frontmatter" and "approved must be null" fragments also occur in `check_specs` | three assertions added by the lead (archive test, each key with exact message on line 1 of the track spec, location filter); re-review: none |
| U1, U4, U5 docs | `cpp-reviewer` | AC-4, AC-6, AC-5 | template §2 lacked "출력", undeclared "실행 기록", C11 evidence short; track spec lost 070-21 details (tool list, UB cases, counters for resources, per-compiler classification, `uses`, §9 wrong-code rule) and its shared-unit sentence contradicted spec.md §6; workflow and skill put the lesson branch after "no spec: stop", step numbers clashed | all fixed by the lead; re-review: two cosmetic points (L1–L4 not a list, provenance sentence) fixed |
