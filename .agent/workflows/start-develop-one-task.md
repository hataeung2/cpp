---
description: Run one task from /docs/agent_todo.md end to end
---

# Agent Task Execution Workflow (atugcc — C++ Library/Framework)

1.  **Context Loading**
    -   Follow the boot sequence in [`/docs/agent_start_prompt.md`](/docs/agent_start_prompt.md).

2.  **Task Selection & Validation**
    -   **Budget first**: if `lint_docs.py --boot` starts with a `BUDGET:` line, propose a triage to the user before picking a task: for each open KI close (`dropped: <reason>` or the fixing task), DEFERRED (with its revisit condition), merge, or promote to a task; for the todo header, shorten the order section and remove finished items. The user decides; apply it by editing Status cells and running `archive_docs.py`. Limits: `BUDGET` in [`lint_docs.py`](/.agent/scripts/lint_docs.py) (spec 090-08).
    -   If the user named a task, use it. If it is not in `agent_todo.md`, add it with the next free ID in the right group (check `docs/archive/agent_todo_done.md` too: DONE tasks live there).
    -   Otherwise pick the first task in `agent_todo.md` whose state is `APPROVED`.
    -   **Check the spec** ([spec.md](/.agent/rules/spec.md)):
        -   **Lesson task** (the todo line links `/docs/specs/tracks/<track>.md`, [spec.md](/.agent/rules/spec.md) §6): continue when that track spec has `approved: <date>` and lists the task in `tasks`; otherwise ask the user to review the track spec. Never draft a spec for it. Then follow **Lesson tasks** below (L1–L4) instead of steps 4–6.
        -   No spec link: **STOP**. Draft the spec, set the state to `SPEC_DRAFT`, report to the user and **wait for approval**. Do not move on to another task.
        -   Spec with `approved: null`: ask the user to review it. Do not implement.
        -   Spec with `approved: <date>`: continue.

3.  **Environment Setup**
    -   Branch from `main`: `feature/NNN-SS-<slug>` (task ID first).
    -   Artifact directory: `/docs/tasks/feature_NNN-SS-<slug>/`.
    -   Set the task state to `DEV` in `agent_todo.md`.

4.  **Planning & Development** (state `DEV`)
    -   Apply [impl.md](/.agent/rules/impl.md) before and during implementation.
    -   **Plan** (lead): write `plan.md` in the artifact directory:
        -   Files to create/modify (`[NEW]` / `[MODIFY]` / `[DELETE]`).
        -   C++20/23 features applied; when replacing a pre-C++20 pattern, the `docs/cpp_evolution/<feature>.md` + `<feature>.en.md` pair to write or update ([impl.md](/.agent/rules/impl.md) §6).
        -   The **unit table** ([delegation.md](/.agent/rules/delegation.md) §9): one file × one change × one deliverable per unit, each with its Check, `Risky` flag and author. Design decisions are made here; a unit that still needs a judgment is not ready.
    -   **Unit order**: public headers (`include/atugcc/`) → implementation (`src/`, `detail/`) → tests (`tests/`, at least one per acceptance criterion) → samples (`sample/`, `src/pattern/`) → docs. New source files update the relevant `CMakeLists.txt`.
    -   **Run each unit** before starting the next:
        1.  The author writes it (delegation.md §1: agy `flash` for code, test and tool units, risky or not; the lead for doc units and `lead (small)` changes).
        2.  A first-pass reviewer who is not the author checks it (delegation.md §1: the fresh reviewer of §0 for ordinary units, the §6.2 chain for risky units); findings go back to the author, one round only (§6.3).
        3.  The lead's **per-unit check**: `git diff --stat` shows only the unit's files (revert anything else), the unit's `grep -c` counts and its narrow build/test pass.
        4.  Record the unit in the table: reviewer and findings, tokens printed by the runner, status (`done` or `failed: <reason>`).
    -   Every document listed in the spec's **Documentation Updates** is a doc unit of this task.
    -   Exit: every unit `done`, build has zero warnings on the preset used. State moves to `TEST`.

5.  **Verification** (state `TEST`, run by the lead as Tester)
    -   Expected results come from the spec's **Acceptance Criteria**, not from the tests written in step 4. For each `AC-n`, name the evidence ([test.md](/.agent/rules/test.md) §5).
    -   Read every unit's diff against the spec section it implements.
    -   Read the tests critically: a test that mirrors the implementation or cannot fail does not count. Missing tests are written here by the lead and get one review call ("does each test check its AC; can any pass trivially?").
    -   Build and test per [config.md](/.agent/rules/config.md) and [test.md](/.agent/rules/test.md): both compilers, zero warnings, full suite.
    -   Fill `testrecord.md`: runs, the AC evidence table and the Reviews section.
    -   Failure: back to step 4 (state `DEV`) as a **new unit**; the fix is not patched in the Tester stage. Append the attempt to `testrecord.md` as `## Revision N — YYYY-MM-DD`, never overwrite earlier attempts.

6.  **Integration & Completion** (state `DONE`)
    -   Merge into `main` without asking when every acceptance criterion is proven by automated evidence (builds, tests, lint, review findings resolved) and nothing needs the user's manual check; otherwise ask first (user decision 2026-10-28). Report what was merged and why no manual check was needed. Pushing is a separate decision. A conflict that needs more than choosing a side is a new unit.
    -   Re-run the full suite on the merged result.
    -   Check every document in the spec's **Documentation Updates** against the final code.
    -   Register every follow-up in [`/docs/known_issues.md`](/docs/known_issues.md) with a `KI-` id.
    -   Write `walkthrough.md`: result, reference to `testrecord.md`, follow-ups by `KI-` id, any `lead (fallback)` units.
    -   Update `agent_todo.md`: state `DONE`, short note, branch name, group `(k/n DONE)`.
    -   Then, run `py -3 .agent/scripts/archive_docs.py`: closed KIs, deferred KIs and DONE tasks move to the file of their status.
    -   `py -3 .agent/scripts/lint_docs.py` exits 0.
    -   Commit: `<type>(NNN-SS): <summary>`.

## Lesson tasks (spec 090-13)
Steps 1–3 as above. The record is `checklist.md` in the artifact directory, copied from [`/docs/specs/tracks/00_lesson_checklist.md`](/docs/specs/tracks/00_lesson_checklist.md); there is no `plan.md`, `testrecord.md` or `walkthrough.md`.
- **L1.** **Design** (state `DEV`): write the checklist's design section: steps, exercises (automatic or observation, with the reason), differences from the track spec row. A new topic, order or lesson, or a rule change, means: stop and amend the track spec for the user's approval. A change outside the lesson path's files ([spec.md](/.agent/rules/spec.md) §6) means: register it as a task or KI and set the lesson task `BLOCKED`.
- **L2.** **Write**: start from `py -3 tools/lessons.py new <track> <id>`. Authors per [delegation.md](/.agent/rules/delegation.md) §1 (lesson code is usually `lead (small)`); one fresh-reviewer round over code and both READMEs.
- **L3.** **Check** (state `TEST`): fill every checklist item with its evidence; an item that does not apply is `N/A: <reason>`. A failed item goes back to L2.
- **L4.** **Finish**: follow-ups as KIs, the track spec's state column, state `DONE` with the group count, `archive_docs.py`, `lint_docs.py` exit 0 (it refuses a `DONE` lesson task with an unchecked item), commit `feat(NNN-SS): <summary>`, merge into `main` without asking.
