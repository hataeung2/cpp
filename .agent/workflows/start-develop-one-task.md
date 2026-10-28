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

4.  **Planning & Execution** (state `DEV`)
    -   Apply [impl.md](/.agent/rules/impl.md) before and during implementation.
    -   Write `plan.md` in the artifact directory:
        -   Files to create/modify (`[NEW]` / `[MODIFY]` / `[DELETE]`).
        -   C++20/23 features applied; when replacing a pre-C++20 pattern, the `docs/cpp_evolution/<feature>.md` page to write or update.
    -   Implement in this order:
        1.  **Public headers** (`include/atugcc/`): interfaces and concepts.
        2.  **Implementation** (`src/`).
        3.  **Tests** (`tests/`): GoogleTest cases, one per acceptance criterion at least.
        4.  **Samples** (`sample/`, `src/pattern/`): runnable examples if applicable.
    -   New source files: update the relevant `CMakeLists.txt`.
    -   Every document listed in the spec's **Documentation Updates** changes together with the code.

5.  **Verification** (state `TEST`)
    -   Build and test per [config.md](/.agent/rules/config.md) and [test.md](/.agent/rules/test.md): both compilers, zero warnings, full suite.
    -   Fill `testrecord.md`, including the acceptance-criteria evidence table.
    -   Failure: back to step 4 (state `DEV`); append the retry to `testrecord.md`, do not overwrite earlier attempts.

6.  **Completion & Reporting** (state `DONE`)
    -   Register every follow-up in [`/docs/known_issues.md`](/docs/known_issues.md) with a `KI-` id.
    -   Write `walkthrough.md`: result, reference to `testrecord.md`, follow-ups by `KI-` id.
    -   Update `agent_todo.md`: state `DONE`, short note, branch name, group `(k/n DONE)`.
    -   Commit: `<type>(NNN-SS): <summary>`.
