# Plan: 090-13 Lesson path (track spec approved once, one lesson finished by a checklist)

- Spec: [/docs/specs/090_13_lesson_path.md](/docs/specs/090_13_lesson_path.md) (approved 2026-11-17)
- Branch: `feature/090-13-lesson-path` (from `main` at `8f6e2f0`, after 070-27)

## Design (spec §2)
- Track specs live in `docs/specs/tracks/<track>.md`; `00_*.md` there are templates and are not checked as track specs. Frontmatter (flat, `agent_common.read_frontmatter`): `track`, `approved`, `tasks: [NNN-SS, ...]` (task ids read with `ac.TASK_ID`).
- A task line whose spec link starts with `/docs/specs/tracks/` is a **lesson task**. `check_specs` handles it in its own branch: no `id` comparison, the §2.5 rules instead. Every other task line keeps today's checks unchanged (AC-3).
- Track ids come from `lessons/curriculum.toml` (`[[track]] id`), read with `tomllib`. A track spec in a tree without that file is an ERROR for its `track` key; trees without track specs (the existing tests) do not read the file.
- `DONE` lesson task: `docs/tasks/feature_<id>-*/checklist.md` must exist (one matching folder) and contain no line matching `^\s*- \[ \]`.
- No C++ change: no preset build (spec §12).

## Files
- [NEW] `docs/specs/tracks/00_template.md`, `docs/specs/tracks/00_lesson_checklist.md`, `docs/specs/tracks/oop_basics.md`
- [MODIFY] `.agent/scripts/lint_docs.py`, `.agent/scripts/test_agent_scripts.py`
- [MODIFY] `docs/agent_todo.md` (070-22 ~ 070-24 lines, Grammar), `docs/lesson_candidates.md`
- [MODIFY] `docs/agent_start_prompt.md`, `.agent/rules/spec.md`, `.agent/workflows/start-develop-one-task.md`, `.agent/skills/develop-task/SKILL.md` (+ copies by `sync_skills.py`), `lessons/README.md`

## Unit table
| Unit | File | Change (what, where, AC) | Check | Risky | Author | Reviewer | Tokens (in / out) | Status |
|---|---|---|---|---|---|---|---|---|
| U1 | `docs/specs/tracks/00_template.md`, `00_lesson_checklist.md` | track spec template (§2.2), lesson checklist template with C1–C13 (§2.4) (AC-4) | `grep -c "^- \[ \] \*\*C"` = 13; `lint_docs.py` links | no | lead | cpp-reviewer: §2 "출력" item missing, undeclared "실행 기록" section, C11 evidence short → fixed, re-review none | — | done |
| U2 | `.agent/scripts/lint_docs.py` | §2.5 checks in `check_specs` + track spec scan, docstring (AC-1, AC-2, AC-3) | existing tests pass; `lint_docs.py` on the repo exit 0 | no | agy flash; rewrite for readability lead (small) (broad `except`, a `00_` link passed silently) | cpp-reviewer: patch folders matched by the glob, folder without checklist ignored when another had one, links to other files under `tracks/` skipped every check → review fixes lead (small), re-review none | not captured (only the answer tail was kept) | done |
| U3 | `.agent/scripts/test_agent_scripts.py` | `LintDocsTrackSpecTest`, 13 tests, one per §2.5 row + clean case (AC-1, AC-2) | 176 tests pass; each of the 14 `report.add` of the new checks replaced by `pass` one at a time: the class fails 14/14 | no | agy flash; review fixes lead (small) | cpp-reviewer: archive line untested, only `tasks` of the three keys tested, two fragments shared with `check_specs` messages → three assertions added, re-review none | 189k / 41k | done |
| U4 | `docs/specs/tracks/oop_basics.md`, `docs/lesson_candidates.md`, `docs/agent_todo.md` | first track spec from 070-21 (Assumption 11), OOP table → link, 070-22 ~ 070-24 link the track spec, Grammar line (AC-6) | `lint_docs.py` exit 0 | no | lead | cpp-reviewer: 070-21 details lost (tool list, UB cases, counters, per-compiler exercises, `uses`, §9), shared-unit rule contradicted spec.md §6, unstated provenance → fixed, re-review none | — | done |
| U5 | spec §8 documents, `sync_skills.py` | rule 3, boot step 4, quick reference, trigger row, spec.md §6, workflow "Lesson tasks", skill step 2, `lessons/README.md` (AC-5) | `lint_docs.py` (skill copies) | no | lead | cpp-reviewer: lesson branch after the general "no spec: stop", step numbers clashing, L1–L4 not a list → fixed, re-review none | — | done |
