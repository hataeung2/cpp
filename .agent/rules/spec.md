---
trigger: model_decision
description: When making or amending a specification or a track spec, or starting a lesson task
---

# Agent Rule: Task Specification Writing Guide (atugcc)

## 1. When to Write a Spec
When a task in [`/docs/agent_todo.md`](/docs/agent_todo.md) has no link to `/docs/specs/` (e.g., `- !BACKLOG | 021-01 | Factory Method`), draft a spec before writing any code.

## 2. Drafting the Spec
Create `/docs/specs/NNN_SS_<slug>.md` from the template [`/docs/specs/00_template.md`](/docs/specs/00_template.md).
- The file name, the frontmatter `id` (`NNN-SS`) and the branch (`feature/NNN-SS-<slug>`) carry the same task ID. ID grammar: header of `agent_todo.md`.
- A **new prerequisite task** found while writing gets the next free `SS` in its group and appears in `depends_on` / `unblocks`. Never use a patch number or a letter suffix for new work.
- Fill the frontmatter with `approved: null`. **Only the user's explicit approval sets it to a date.**

Guidelines per section:
- **Assumptions**: every decision the user did not specify, with the rejected alternative and why.
- **Objective**: the module, class or feature, and the reason it is needed.
- **Requirement Details**: public API surface (`include/atugcc/`), internal implementation, platform specifics.
- **C++ Standard Evolution**: the pre-C++20 approach and what C++20/23 improves; which features are used.
- **Edge Cases (CRITICAL)**: answer every checklist item; add domain-specific cases the user did not mention.
- **Acceptance Criteria**: numbered `AC-n`, each observable and testable, each with how it is verified. The Tester stage checks these.
- **Out of Scope**: what is excluded and which task or `KI-` id picks it up.
- **Documentation Updates**: every document the task changes (READMEs, `docs/cpp_evolution/`, rules, samples' comments), with section and change.
- **Context & References**: **project-relative** links only (e.g., `[RingBuffer](/include/atugcc/core/ring_buffer.hpp)`).
- **Implementation & Verification Plan**: step checklist; preset build and test commands; GoogleTest cases to write.

> Do not leave sections blank when the user omitted details. Propose the best C++ design, record it under Assumptions, and ask the user to review.

## 3. Post-Draft Actions (Mandatory)
1. **Link** the spec in `agent_todo.md` and set the state to `SPEC_DRAFT`:
   - Before: `- !BACKLOG | 021-01 | Factory Method`
   - After: `- !SPEC_DRAFT | 021-01 | [Factory Method](/docs/specs/021_01_factory_method.md)`
2. **Report** to the user that the spec is ready for review, listing the Assumptions.
3. **STOP & WAIT**: do not implement and do not move on to another task until the user approves.
4. **On approval**: set `approved: YYYY-MM-DD` and the state to `APPROVED`. A task past `SPEC_DRAFT` whose spec still has `approved: null` is an error.

## 4. Reopened / Amended Specs
- A completed spec that needs a fix or a new requirement is **not edited in place**. Create a sub-spec `NNN_SS_PP_<slug>.md` (task ID `NNN-SS-PP`), e.g. `020_02_01_console_utf8.md`.
- Patch numbers are only for amendments of an existing task. Separate new work is a new `SS`.
- The sub-spec states its relation to the original, the reason for reopening and what changes. The original spec gets an entry in its `History / Amendments`.
- `agent_todo.md` lists the patch as its own indented line under the original.
- New branch `feature/NNN-SS-PP-<slug>` and a new artifact directory. Its `plan.md` starts with:
  ```markdown
  ## Prior Round Reference
  - Original spec: [/docs/specs/...](/docs/specs/...)
  - Original artifacts: [/docs/tasks/feature_.../walkthrough.md](/docs/tasks/feature_.../walkthrough.md)
  - Reason for reopen: <brief reason>
  ```
- The original task's artifact directory is a sealed record: never write into it.

## 5. Legacy Numbering
Specs written before task 090-01 (`01_`–`10_`, `08_001_`, `08_002_`, `09_001_`) do not follow `NNN_SS`. They are **not renamed**; the todo line's link is the authoritative mapping. A legacy spec whose task is not `DONE` gets the frontmatter block when it is next touched.

## 6. Track Specs and Lesson Tasks (090-13)
Rule 3 is relaxed for lessons only: a **lesson task** needs no spec of its own when an approved **track spec** lists it.
- **Track spec**: `/docs/specs/tracks/<track>.md` from [`/docs/specs/tracks/00_template.md`](/docs/specs/tracks/00_template.md). Frontmatter `track` (a `[[track]]` id in `lessons/curriculum.toml`), `approved: null | YYYY-MM-DD`, `tasks: [NNN-SS, ...]`. It fixes the reader, the lesson form, the common rules (undefined behaviour, output stability, automatic vs observation exercises, evolution pages, tags) and the curriculum table (task, lesson id, topic, comparison, prerequisites, state). It does **not** fix a lesson's steps or exercises: the lead decides them in the lesson's checklist.
- **Living document**: unlike a task spec it is edited in place. A new row, a changed topic or order, or a changed rule needs the user's approval: the new date goes into `approved`, one line into `## History`. Rows added since the last approval stay `BACKLOG` until then. The lead changes only the state column on its own.
- **Lesson task**: the todo line links the track spec (todo Grammar). `BACKLOG` → `APPROVED` once the track spec is approved and lists it; no `SPEC_DRAFT`. One lesson per task.
- **Scope**: only the lesson's folder, a new unit used by that lesson only, its `lessons/curriculum.toml` line, `lessons/tags.toml`, link lines in other lessons' READMEs, the track and lesson lists (`lessons/README.md`, `intro.md`, `intro.en.md`, `docs/lesson_candidates.md`), the track spec's state column, todo, KI and archive files, and the checklist ([090-13](/docs/specs/090_13_lesson_path.md) §2.1). Pattern (021–024) and engine (060) tasks keep their own specs even for their lessons.
- **Record**: `docs/tasks/feature_NNN-SS-<slug>/checklist.md` copied from [`/docs/specs/tracks/00_lesson_checklist.md`](/docs/specs/tracks/00_lesson_checklist.md) replaces `plan.md`, `testrecord.md` and `walkthrough.md`. `DONE` only with every item checked (`N/A: <reason>` where an item does not apply); then merge without asking.
- **Stop**: a change outside the scope (library, tools, web, CMake, an existing unit) becomes its own task or KI and the lesson task is `BLOCKED`; a change to the track spec waits for the user's approval.
- The docs gate checks track spec frontmatter, todo lines against `tasks`, the approval state and the `DONE` checklists (`lint_docs.py`).
