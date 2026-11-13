# Walkthrough: 070-16-01 연습 백업을 레슨·유닛별 한 폴더에 모으기

- Spec: [/docs/specs/070_16_01_backup_by_owner.md](/docs/specs/070_16_01_backup_by_owner.md) (sub-spec of [070-16](/docs/specs/070_16_practice_workspace.md))
- Evidence: [testrecord.md](testrecord.md), plan: [plan.md](plan.md)

## Result
- Reset backups go to `practice/backup/lessons/<lesson id>/` and `practice/backup/units/<unit id>/` as `<name>.<YYYYMMDD-HHMMSS>[-n]<ext>`. All files of one reset share the stamp; the newest 10 backups of each file are kept (`KEEP_BACKUPS`, per file). Old `practice/backup/<stamp>/` folders are left alone.
- `tools/practice.py`: `_Backup` rewritten, `backup_name` / `parse_backup_name`, `Workspace._owners`. Web API shape, frontend and the reset behaviour are unchanged; `backup` in the reset response is now the owner folder.
- Tests: `tools/test_practice.py` 15 → 23, `web/server/test_server.py` reset tests and the 403 list updated. Docs: `lessons/README.md`, `web/README.md`, `practice.py` docstring, 070-16 History.
- Python only: no C++ source changed; both full suites pass (Windows 40/40, Linux 40/40).

## Decisions made during DEV (also in the spec History)
- A path that is neither in the catalog nor shaped like a lesson or unit copy raises `PracticeError` (Assumption 6 had promised a backup in every case; the only way to reach it is a hand-edited `state.json`).
- Pruning excludes the backup just made, so a clock set back cannot delete it.
- Known limitation: an extension-less file whose name ends in a timestamp-like part is grouped wrongly (no lesson source has that shape).
- `-2` sorts before the plain name in an alphabetical listing (`-` < `.`); the order used for pruning is numeric.

## Follow-ups
- KI-052: `npm --prefix web/frontend test` from the repository root fails on this machine (the tests pass inside `web/frontend`).

## Units
All four units written by the lead (small Python changes; delegation.md §1), reviewed by `cpp-reviewer` (same family as the lead; no cross-family review, recorded in testrecord). No `lead (fallback)` unit.
