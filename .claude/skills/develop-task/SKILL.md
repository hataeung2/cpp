---
name: develop-task
description: Run one atugcc task end to end, by its task ID (NNN-SS) from docs/agent_todo.md - boot view, spec approval check, task branch, plan with a unit table, delegated units with cross-review, acceptance-criteria verification, archive, docs gate, merge. Use when asked to start, continue or finish a task, or to pick the next approved task.
---
<!-- generated from .agent/skills/develop-task/SKILL.md by .agent/scripts/sync_skills.py; edit the source -->
# Develop one atugcc task

The procedure is [`.agent/workflows/start-develop-one-task.md`](/.agent/workflows/start-develop-one-task.md). Follow it step by step; this skill only adds the commands and the stops in order.

1. Boot view: `py -3 .agent/scripts/lint_docs.py --boot` (Linux: `python3`). A first line starting `BUDGET:` means: propose a triage to the user before picking a task.
2. Pick the task the user named, or the first `APPROVED` one (`lint_docs.py --status`). Read its spec. `approved: null` or no spec: **stop** and follow [`.agent/rules/spec.md`](/.agent/rules/spec.md).
3. Branch `feature/NNN-SS-<slug>` from `main` in its own command (the commit guard judges a command line before it runs), artifact folder `docs/tasks/feature_NNN-SS-<slug>/`, state `DEV`.
4. `plan.md` with the unit table ([`.agent/rules/delegation.md`](/.agent/rules/delegation.md) §9). Who writes each unit is delegation.md §1 (sub-agent, `lead (small)`, `lead (scripted)`, doc units by the lead). Who the lead, the sub-agents and the reviewers are for the tool you run in: delegation.md §0. `subagent_run.py --kind <kind>` puts the sub-agent line and the project rules for the unit kind into every prompt (delegation.md §4); the prompt carries the design only.
5. Each unit: author → first-pass reviewer who is not the author (delegation.md §1, §6) → the lead's mechanical check (diff scope, `grep -c`, narrow build or test).
6. Verify against the spec's acceptance criteria ([`.agent/rules/test.md`](/.agent/rules/test.md)); write `testrecord.md`. A criterion that needs the user's manual check means: ask before merging.
7. Finish: register follow-ups (skill `add-known-issue`), `walkthrough.md`, state `DONE` with the group count, then `py -3 .agent/scripts/archive_docs.py`, then `py -3 .agent/scripts/lint_docs.py` exits 0, commit `<type>(NNN-SS): <summary>`, merge into `main` when the workflow allows it.
