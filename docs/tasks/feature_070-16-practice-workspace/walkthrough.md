# Walkthrough: 070-16 연습 작업 공간과 되돌리기

## Result
Lesson exercises now run on practice copies, so the originals under `lessons/` never change and the git tree stays clean:
- `practice/` (git-ignored) mirrors `lessons/`; a lesson copy holds `lesson.toml` and its sources, plus a shared copy of each unit it uses. `practice/state.json` keeps each copy's origin sha, so a copy is `same`, `modified`, `both` or `missing-origin`; unmodified copies follow a changed origin, manifests always follow.
- CMake builds every copy as `practice_<id>` (`bin/practice/`, practice include path first, `EXCLUDE_FROM_ALL`, no smoke test): a half-done exercise breaks neither the full build nor `ctest`.
- `tools/practice.py` (`start`, `status`, `reset`, `path`) is the one implementation; the web server uses the same module.
- Server: `/api/practice`, `/api/practice/start`, `/api/practice/reset`, `practice` on `/api/runs`; writes to copies only, never to their manifests, the state or the backups.
- Page: mode `연습` (default) / `원본 편집`; practice bar with ↺ (file), 레슨 되돌리기, 원본과 비교 (Monaco diff); tab underline / `⚠`, tree `✎`; resets list the files first and keep them in `practice/backup/` (newest 10).
- Docs: `lessons/README.md` "연습 공간", `web/README.md`, intro pages, `config.md`, and a reset note in the lesson READMEs that say "되돌립니다" (03, 04, 12, 15, 16).

Evidence: [testrecord.md](testrecord.md) (both full suites, 19 + 2 browser checks, tool and server tests).

## Notes
- `tools/practice.py` was rewritten by the lead after the first review (11 findings): the agy draft repeated the lesson and unit logic, and the fixes would have doubled. Recorded as review fixes in [plan.md](plan.md); no `lead (fallback)` unit.
- The review of the backup test found a real pruning bug (a freed bare stamp was reused and pruned at once); fixed before merge.
- Spec History records the DEV decisions (README note placement, `status_all`, tooltip for 🔒 originals, saving before a mode switch).

## Follow-ups
None. The next task in the A2 order is 070-17 (exercise checks on the practice runs).
