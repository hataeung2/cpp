# Walkthrough: 070-17 연습 과제 확인

## Result
README exercises now have machine-checked definitions, checked on every practice Run:
- `exercises.toml` in a lesson folder: id, title (two languages), declarative rules (`build`, `build_expect`, `exit`, `expect`, `forbid`, `source` with `has`/`lacks`), `fail_hint`, `hint`, `answer` (Markdown, two languages). No rule = an observation exercise the learner marks done.
- `tools/exercises.py`: one checker for the server and the CLI (`list`, `check <id> --preset`, `verify <id> --preset | --exe`), the progress record `practice/progress.json` (a pass stays recorded; clearing is per lesson).
- An automatic exercise passes only when a practice copy differs from its origin, and CTest `lesson.<id>.exercises_verify` proves the unchanged original passes none (an `expect` line the original already prints is caught: testrecord R5).
- `lessons.py check` validates the definitions (ERROR: schema, regex, unknown file, duplicate id; WARN: missing English, empty-matching regex, README "연습" count); the index carries each lesson's exercise count.
- Server: `done.exercises` / `exercisesError` on practice runs; `/api/exercises`, `/summary`, `/self`, `/clear`.
- Page: right-panel tab **연습** with ✓/✗/?/— per exercise, the failure reasons and `fail_hint`, hidden hints and answers, the observation box, **기록 지우기**, a news dot when a Run passes a new exercise, `passed/total` in the tree, and the original-mode notice.
- Pilot definitions for `lambda_capture`, `error_expected`, `testing` (13 exercises, 9 automatic); every compiler text in a rule was taken from real MSVC and Clang output, and every automatic exercise was solved by its answer on both compilers.

Evidence: [testrecord.md](testrecord.md) (both full suites 38/38, R1–R14, the AC-2 table, browser checks).

## Notes
- The CLI part of `tools/exercises.py` was shortened by the lead before review (one lesson lookup, one build and run helper instead of three and two copies). Review fixes are recorded in [plan.md](plan.md); no `lead (fallback)` unit.
- The Claude `cpp-reviewer` hit its usage limit; codex `luna` reviewed every unit instead (also another family than the author).
- `lambda_capture` exercise 2: the README says the dangling reference does not show in the build. On Clang 20 that holds only when the lambda goes through a variable (`return [&local]{…};` is a `-Wreturn-stack-address` error); the hint and answer say so. The README text is unchanged (spec §2.4: rules only).
- Testing wrote `practice/progress.json` and a few `practice/backup/` folders (the lead's resets of the pilot copies); the progress file was removed after the checks, the backups are ordinary reset backups.

## Follow-ups
- KI-050: on `windows-x64-debug` an uncaught exception's `abort()` dialog blocks unattended runs, so `error_expected` `remove_catch` reaches the time limit in `exercises.py check` (a person can click it; the web passes it).
- The remaining lessons' definitions are 070-20 (and `thread_and_log` 070-18), as planned.
