---
description: Run one task from /docs/tasks/agent_todo.md end to end
---

# Agent Task Execution Workflow (atugcc — C++ Library/Framework)

1.  **Context Loading**
    -   Follow the boot sequence in [`/docs/agent_start_prompt.md`](/docs/agent_start_prompt.md).

2.  **Task Selection & Validation**
    -   If the user named a task, use it. If it is not in `agent_todo.md`, add it with the next free ID in the right group.
    -   Otherwise pick the first task in `agent_todo.md` whose state is `APPROVED`.
    -   **Check the spec** ([spec.md](/.agent/rules/spec.md)):
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
        -   C++20/23 features applied; when replacing a pre-C++20 pattern, the `docs/cpp_evolution/<feature>.md` page to write or update.
        -   The **unit table** ([delegation.md](/.agent/rules/delegation.md) §9): one file × one change × one deliverable per unit, each with its Check, `Risky` flag and author. Design decisions are made here; a unit that still needs a judgment is not ready.
    -   **Unit order**: public headers (`include/atugcc/`) → implementation (`src/`, `detail/`) → tests (`tests/`, at least one per acceptance criterion) → samples (`sample/`, `src/pattern/`) → docs. New source files update the relevant `CMakeLists.txt`.
    -   **Run each unit** before starting the next:
        1.  The author writes it (delegation.md §1: lead for ordinary units, agy for risky ones).
        2.  A first-pass reviewer who is not the author checks it (delegation.md §1: `cpp-reviewer` or agy `flash` for ordinary units, the §6.2 chain for risky units); findings go back to the author, one round only (§6.3).
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
    -   Merge into `main` only when the user asks; a conflict that needs more than choosing a side is a new unit.
    -   Re-run the full suite on the merged result.
    -   Check every document in the spec's **Documentation Updates** against the final code.
    -   Register every follow-up in [`/docs/known_issues.md`](/docs/known_issues.md) with a `KI-` id.
    -   Write `walkthrough.md`: result, reference to `testrecord.md`, follow-ups by `KI-` id, any `lead (fallback)` units.
    -   Update `agent_todo.md`: state `DONE`, short note, branch name, group `(k/n DONE)`.
    -   `py -3 .agent/scripts/lint_docs.py` exits 0.
    -   Commit: `<type>(NNN-SS): <summary>`.
