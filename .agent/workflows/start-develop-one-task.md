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
    -   **Compile**: Follow `/.agent/rules/config.md` to select configure/build presets and environment.
    -   **Testing**: See `/.agent/rules/config.md` for recommended `ctest` usage.
    -   Recommended (when `CMakePresets.json` and presets exist):
        -   Configure: `cmake --preset <configurePreset>`
        -   If the selected preset uses MSVC on Windows, initialize the MSVC environment before configure. Example:
            ```
            cmd.exe /c '"C:\Path\To\VsDevCmd.bat" -arch=x64 -host_arch=x64 && cmake --preset <configurePreset>'
            ```
        -   Build: `cmake --build --preset <buildPreset> --config <CMAKE_BUILD_TYPE>` (or `cmake --build --preset <buildPreset>` if the preset determines the config)
        -   Test: `ctest --test-dir "<binaryDir>" -C <CMAKE_BUILD_TYPE> --output-on-failure`
        -   If no suitable preset exists: do NOT run ad-hoc fallback commands. Create a configure preset and a matching build preset in `CMakePresets.json` instead. Example snippet:
                If no suitable preset exists: do NOT run ad-hoc fallback commands. Instead copy the example presets file from `.agent/rules/CMakePresets.example.json` to the project root as `CMakePresets.json` and edit it to match your environment.

                After adding or editing the preset file, run:
                - Configure: `cmake --preset <configurePreset>`
                - Build: `cmake --build --preset <buildPreset> --config <CMAKE_BUILD_TYPE>`
                - Test: `ctest --test-dir "<binaryDir>" -C <CMAKE_BUILD_TYPE> --output-on-failure`
                - Install to `dist`: `cmake --install "<binaryDir>" --prefix "${sourceDir}/dist/<config>" --config <CMAKE_BUILD_TYPE>`
                - Test: `ctest --test-dir "<binaryDir>" -C <CMAKE_BUILD_TYPE> --output-on-failure`
                - Prepare deployable `dist`: `python3 scripts/make_dist.py --binary-dir "<binaryDir>" --build-config <CMAKE_BUILD_TYPE>`
    -   Create `testrecord.md` to log detailed test execution.
    -   Create `walkthrough.md` to summarize the final results.
    -   Update `docs/tasks/agent_todo.md` status to `[x]` and include the branch name used.