---
trigger: model_decision
description: When making or amending a specification
---

# Agent Rule: Task Specification Writing Guide (atugcc)

## 1. When to Write a Spec
When a task in [`/docs/tasks/agent_todo.md`](/docs/tasks/agent_todo.md) has no link to `/docs/specs/` (e.g., `- !BACKLOG | 021-01 | Factory Method`), draft a spec before writing any code.

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
