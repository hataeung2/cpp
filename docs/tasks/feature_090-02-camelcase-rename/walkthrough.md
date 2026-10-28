# Walkthrough: 090-02 함수 명명 camelCase 통일

- Spec: [/docs/specs/090_02_camelcase_rename.md](/docs/specs/090_02_camelcase_rename.md) · Plan: [plan.md](./plan.md) · Tests: [testrecord.md](./testrecord.md)

## Result
All 41 project-defined snake_case function names are camelCase (`Tracer::recordMessage`, `formatDiagram`, concept requirement `onEvent`, observer `onNotify`, …). Names fixed by std/POSIX/Boost conventions and every string literal are unchanged, so program output is the same.

- Both presets build warning-free and pass; the test list is identical before and after.
- codex review of the diff: no findings.
- `naming_check.py` is now a permanent gate (test.md) and documents the exceptions.
- delegation.md §1 gained the `lead (scripted)` case for mechanical changes fixed by a spec (reason in plan.md).

## Follow-ups
- None. 020-04 can now add its API in camelCase only.
