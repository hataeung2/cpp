---
description: Start Develop One Function in /docs/tasks/agent_todo.md
---

# Agent Task Execution Workflow (atugcc — C++ Library/Framework)

1.  **Context Loading**
    -   READ `/.agent/rules/impl.md` (Implementation rules — C++ standards, naming, style).
    -   READ `/docs/tasks/agent_todo.md` to identify the target task.
    -   READ the task's linked Spec file if it exists.

2.  **Task Selection & Validation**
    -   Pick the highest priority task (incomplete top-down).
        -   **IF** user specifies the target task, pick it without using top-down.
    -   **CHECK SPECIFICATION (Rule from spec.md)**:
        -   **IF** task has `[Link](...)`: Proceed to Step 3.
        -   **IF** task has NO Link (e.g., `[ ] Task Name`):
            -   **STOP**. Do NOT write implementation code.
            -   Create draft spec: `docs/specs/XX_taskname.md` by reading `/.agent/rules/spec.md`.
            -   Link it in `docs/tasks/agent_todo.md`.
            -   Report to user and EXIT workflow.

3.  **Environment Setup (Mandatory)**
    -   Create Branch: `feature/<task-name>`.
    -   Create Artifact Dir: `/docs/tasks/feature_<task-name>/`.
    -   **PATH RULE**: ALWAYS use **Relative Paths** from project root (e.g., `/docs/...`, `/include/atugcc/...`). **NEVER** use absolute paths (e.g., `z:/...`).

4.  **Planning & Execution**
    -   **READ Rules**: MUST READ and apply the rules in `/.agent/rules/impl.md` before and during implementation.
    -   Create `plan.md` in the artifact directory summarizing:
        -   Files to create/modify (with `[NEW]` / `[MODIFY]` / `[DELETE]` markers).
        -   C++20/23 features being applied.
        -   If replacing a pre-C++20 pattern: note the evolution in `/docs/cpp_evolution/<feature>.md`.
    -   Implement the feature/fix following these priorities:
        1.  **Public headers** (`include/atugcc/`) — define interfaces and concepts.
        2.  **Implementation** (`src/`) — write the concrete implementations.
        3.  **Tests** (`tests/`) — write GoogleTest test cases.
        4.  **Samples** (`sample/`) — update or create runnable examples if applicable.
    -   **CMake**: If adding new files, update the relevant `CMakeLists.txt`.
    -   **Documentation**:
        -   Save artifacts in `docs/tasks/feature_<task-name>/`:
            -   `plan.md`: Implementation plan.
            -   `walkthrough.md`: Final results and verification.
            -   `testrecord.md`: Detailed test execution log.

5.  **Completion & Reporting**
    -   **Testing**: Run tests by reading `/.agent/rules/test.md`.
    // turbo
    -   Build: `cmake --build build --config Debug`
    // turbo
    -   Test: `cd build && ctest --output-on-failure -C Debug`
    -   Create `testrecord.md` to log detailed test execution.
    -   Create `walkthrough.md` to summarize the final results.
    -   Update `docs/tasks/agent_todo.md` status to `[x]` with branch name.