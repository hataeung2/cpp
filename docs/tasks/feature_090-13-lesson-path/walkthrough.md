# Walkthrough: 090-13 Lesson path

- Spec: [/docs/specs/090_13_lesson_path.md](/docs/specs/090_13_lesson_path.md) (approved 2026-11-17)
- Plan: [plan.md](plan.md), test record: [testrecord.md](testrecord.md)
- Branch: `feature/090-13-lesson-path`

## Result
Rule 3 is relaxed for lessons only. A lesson task has no spec of its own: its todo line links a track spec in `docs/specs/tracks/`, it starts once that track spec is approved and lists it in `tasks`, and it is finished when every item of its `checklist.md` (C1–C13) has evidence. Scope, stop conditions and the record are in [spec.md](/.agent/rules/spec.md) §6 and the workflow's "Lesson tasks" (L1–L4).
- Templates: [`00_template.md`](/docs/specs/tracks/00_template.md) (track spec), [`00_lesson_checklist.md`](/docs/specs/tracks/00_lesson_checklist.md) (lesson task record).
- First track spec: [`oop_basics.md`](/docs/specs/tracks/oop_basics.md), carrying the decisions of 070-21, approved by the user on 2026-11-17 (AC-7). 070-22, 070-23 and 070-24 are now `APPROVED` lesson tasks.
- Docs gate (`lint_docs.py`): track spec frontmatter, todo lines against `tasks` (archive lines included), approval state, no `SPEC_DRAFT`, `DONE` lesson tasks need `checklist.md` with no unchecked item in every folder of their own (patch folders excluded); 14 tests.
- `lesson_candidates.md` no longer keeps its own OOP table: the track spec is the source.

## Units
All five units `done` (plan.md). U2 and U3 were written by agy `flash`. The lead then made the fixes that came out of the readability pass and the reviews (`lead (small)`). No `lead (fallback)` units.

## Follow-ups
- KI-054 (DEFERRED): a script that runs checklist items C3–C8, to decide after two or three lesson tasks together with 070-28.
- Not a KI: reworking an existing lesson stays on the full path (spec §6); revisit in a new task if it becomes frequent.
