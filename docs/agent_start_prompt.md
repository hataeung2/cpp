# atugcc — Agent Boot Sequence

You are the lead developer agent for **atugcc**, a C++20/23 framework library (core logging/dump modules, design-pattern visualizer, planned web playground).

> This file is the **single boot sequence** for every agent tool: Claude Code (`CLAUDE.md`), Codex and other tools (`AGENTS.md`), Antigravity (`.agent/`). Entry files point here; they do not keep their own list.

## Boot (read in order)
1. This file.
2. [`docs/tasks/agent_todo.md`](/docs/tasks/agent_todo.md): task IDs, states and the line grammar (header of that file).
3. [`docs/known_issues.md`](/docs/known_issues.md): OPEN items touching the area you will change.
4. The task's spec, if it has one.
5. Before writing code, propose a short plan that cites the task ID (`NNN-SS`).

Do **not** read every rule up front. Load a rule when its trigger applies:

| Trigger | Rule |
|---|---|
| Writing or amending a spec | [`.agent/rules/spec.md`](/.agent/rules/spec.md) |
| Writing code | [`.agent/rules/impl.md`](/.agent/rules/impl.md) |
| Configure / build / package | [`.agent/rules/config.md`](/.agent/rules/config.md) |
| Testing or verifying a change | [`.agent/rules/test.md`](/.agent/rules/test.md) |
| Splitting work into units, delegating, reviewing | [`.agent/rules/delegation.md`](/.agent/rules/delegation.md) |
| Generating, showing or drawing diagrams | [`.agent/rules/diagrams.md`](/.agent/rules/diagrams.md) |
| Running a task end to end | [`.agent/workflows/start-develop-one-task.md`](/.agent/workflows/start-develop-one-task.md) |

## Precedence
1. System and platform safety policies.
2. The user's explicit instruction in the current session.
3. The non-negotiable rules below.
4. `.agent/rules/`.
5. `.agent/workflows/`.

An unresolved conflict means STOP and ask the user.

## Non-negotiable rules
1. **No machine-specific paths** in committed files (no `C:/`, `Z:/`, `file:///`, no user home). Use project-relative paths; tool locations come from an env var (`VCPKG_ROOT`, `VSDEVCMD`) or a `<placeholder>`.
2. **Build only through `CMakePresets.json` presets.** No ad-hoc `cmake -S . -B build`. A missing preset is added to the presets file, not worked around.
3. **No implementation without an approved spec**: the spec frontmatter has `approved: <date>`, set only on the user's explicit approval.
4. **One task per branch** `feature/NNN-SS-<slug>`, started from `main`.
5. **Follow-ups go to `docs/known_issues.md`** with a `KI-` id, never only into a walkthrough.
6. **Unknown system error or rule conflict: STOP and ask.**

## Quick reference
| What | Where |
|---|---|
| Spec template | [`docs/specs/00_template.md`](/docs/specs/00_template.md) |
| Task artifacts | `docs/tasks/feature_NNN-SS-<slug>/` (`plan.md`, `testrecord.md`, `walkthrough.md`) |
| C++ evolution notes | `docs/cpp_evolution/<feature>.md` |
| Build presets | [`CMakePresets.json`](/CMakePresets.json) |
| Build / test (any host) | `py -3 .agent/scripts/build.py --preset <p> --test` (Linux: `python3`) |
| Task states, next task | `py -3 .agent/scripts/lint_docs.py --status` |
| Docs gate | `py -3 .agent/scripts/lint_docs.py` (exit 0 before a task is done) |
| Sub-agent call | `py -3 .agent/scripts/subagent_run.py --model <alias> --prompt-file <file>` |

Hooks in `.claude/settings.json` refuse ad-hoc CMake configure, commits on `main`, and machine paths written into repo files.

## Environment notes
- `git` reporting *dubious ownership* means the checkout was created under another Windows account. Pass `-c safe.directory=<repo>` per command; adding it globally is the user's decision.
